"""
Step 2: DEM Preparation
- Open both BATNAS GeoTIFF tiles
- Assign CRS EPSG:4326 to each (tiles have no embedded CRS)
- Merge the two tiles into a seamless DEM
- Clip merged DEM to survey extent with buffer
- Reproject clipped DEM to UTM Zone 51S (EPSG:32751)
- Save output files and generate preview figure
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")  # headless backend before importing pyplot
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rioxarray
from rasterio.enums import Resampling
from rioxarray.merge import merge_arrays

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

TILE_N = os.path.join(PROJECT_DIR, "BATNAS_120E-125E_000-05N_MSL_v1.5.tif")
TILE_S = os.path.join(PROJECT_DIR, "BATNAS_120E-125E_05S-000_MSL_v1.5.tif")
GRAVITY_CSV = os.path.join(OUTPUT_DIR, "gravity_clean.csv")

for p in [TILE_N, TILE_S]:
    if not os.path.exists(p):
        sys.exit(f"ERROR: Input tile not found: {p}")

OUT_MERGED = os.path.join(OUTPUT_DIR, "dem_merged.tif")
OUT_CLIPPED = os.path.join(OUTPUT_DIR, "dem_clipped.tif")
OUT_UTM = os.path.join(OUTPUT_DIR, "dem_clipped_utm.tif")
OUT_PREVIEW = os.path.join(OUTPUT_DIR, "02_dem_preview.png")

# Survey clip bounds (with buffer)
MINX, MINY, MAXX, MAXY = 120.5, -2.5, 124.5, 0.5

# ---------------------------------------------------------------------------
# 1. Open tiles and assign CRS
# ---------------------------------------------------------------------------
print("Opening DEM tiles...")
tile_n = rioxarray.open_rasterio(TILE_N, masked=True)
tile_s = rioxarray.open_rasterio(TILE_S, masked=True)

print(f"  North tile shape: {tile_n.shape}, bounds: {tile_n.rio.bounds()}")
print(f"  South tile shape: {tile_s.shape}, bounds: {tile_s.rio.bounds()}")

print("Assigning CRS EPSG:4326 to both tiles...")
tile_n = tile_n.rio.write_crs("EPSG:4326", inplace=True)
tile_s = tile_s.rio.write_crs("EPSG:4326", inplace=True)

# ---------------------------------------------------------------------------
# 2. Merge tiles
# ---------------------------------------------------------------------------
print("Merging tiles...")
merged = merge_arrays([tile_n, tile_s])
print(f"  Merged shape: {merged.shape}, bounds: {merged.rio.bounds()}")

print(f"Saving merged DEM to {OUT_MERGED}...")
merged.rio.to_raster(OUT_MERGED)

# ---------------------------------------------------------------------------
# 3. Clip to survey region
# ---------------------------------------------------------------------------
print(f"Clipping merged DEM to lon [{MINX}, {MAXX}], lat [{MINY}, {MAXY}]...")
clipped = merged.rio.clip_box(minx=MINX, miny=MINY, maxx=MAXX, maxy=MAXY)
print(f"  Clipped shape: {clipped.shape}, bounds: {clipped.rio.bounds()}")

# Basic stats on clipped DEM
elev = clipped.values.squeeze()
valid = elev[~np.isnan(elev)]
print(f"  Elevation range: {valid.min():.2f} to {valid.max():.2f} m")
print(f"  Mean elevation: {valid.mean():.2f} m")

print(f"Saving clipped DEM to {OUT_CLIPPED}...")
clipped = clipped.rio.write_nodata(np.nan)
clipped.rio.to_raster(OUT_CLIPPED)

# ---------------------------------------------------------------------------
# 4. Reproject to UTM Zone 51S (EPSG:32751)
# ---------------------------------------------------------------------------
print("Reprojecting clipped DEM to UTM Zone 51S (EPSG:32751)...")
clipped_utm = clipped.rio.reproject("EPSG:32751", resampling=Resampling.bilinear)
print(f"  UTM shape: {clipped_utm.shape}, bounds: {clipped_utm.rio.bounds()}")

utm_bounds = clipped_utm.rio.bounds()
print(f"  UTM extent: X [{utm_bounds[0]:.0f}, {utm_bounds[2]:.0f}] m, "
      f"Y [{utm_bounds[1]:.0f}, {utm_bounds[3]:.0f}] m")

print(f"Saving UTM DEM to {OUT_UTM}...")
clipped_utm.rio.to_raster(OUT_UTM)

# ---------------------------------------------------------------------------
# 5. Load gravity stations for overlay
# ---------------------------------------------------------------------------
print("Loading gravity stations for preview...")
try:
    grav = pd.read_csv(GRAVITY_CSV)
except FileNotFoundError:
    sys.exit(f"ERROR: Gravity CSV not found: {GRAVITY_CSV}")
# Column names from CLAUDE.md: Bujur=lon, Lintang=lat
lon_col = "Bujur"
lat_col = "Lintang"
if lon_col not in grav.columns:
    # fallback if columns differ
    lon_col = grav.columns[0]
    lat_col = grav.columns[1]
    print(f"  Warning: Using columns '{lon_col}' and '{lat_col}' for lon/lat")

# ---------------------------------------------------------------------------
# 6. Generate preview figure
# ---------------------------------------------------------------------------
print("Generating preview figure...")
elev_2d = clipped.values.squeeze()
x_coords = clipped.x.values
y_coords = clipped.y.values

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Common colormap range
vmin, vmax = np.nanpercentile(elev_2d, [2, 98])

# Left panel: DEM elevation
im = axes[0].pcolormesh(
    x_coords, y_coords, elev_2d,
    cmap="terrain", vmin=vmin, vmax=vmax,
    shading="auto"
)
plt.colorbar(im, ax=axes[0], label="Elevation (m)", fraction=0.046, pad=0.04)
axes[0].set_title("DEM Elevation (Geographic)")
axes[0].set_xlabel("Longitude (°E)")
axes[0].set_ylabel("Latitude (°N)")
axes[0].set_aspect("equal")

# Right panel: DEM with gravity stations overlaid
im2 = axes[1].pcolormesh(
    x_coords, y_coords, elev_2d,
    cmap="terrain", vmin=vmin, vmax=vmax,
    shading="auto"
)
plt.colorbar(im2, ax=axes[1], label="Elevation (m)", fraction=0.046, pad=0.04)
axes[1].scatter(
    grav[lon_col], grav[lat_col],
    s=0.5, c="red", alpha=0.5, linewidths=0, label="Gravity stations"
)
axes[1].set_title("DEM with Gravity Stations")
axes[1].set_xlabel("Longitude (°E)")
axes[1].set_ylabel("Latitude (°N)")
axes[1].set_aspect("equal")
axes[1].legend(loc="upper right", markerscale=10, fontsize=8)

plt.tight_layout()
plt.savefig(OUT_PREVIEW, dpi=150)
plt.close()
print(f"  Preview saved to {OUT_PREVIEW}")

# ---------------------------------------------------------------------------
# 7. Verification summary
# ---------------------------------------------------------------------------
print("\n=== Output File Summary ===")
for fpath in [OUT_MERGED, OUT_CLIPPED, OUT_UTM, OUT_PREVIEW]:
    size = os.path.getsize(fpath) if os.path.exists(fpath) else 0
    status = "OK" if size > 0 else "MISSING or EMPTY"
    print(f"  {os.path.basename(fpath)}: {size:,} bytes — {status}")

print("\n=== Clipped DEM Stats ===")
print(f"  Shape: {clipped.shape}")
print(f"  Resolution: {clipped.rio.resolution()}")
print(f"  Bounds (geographic): {clipped.rio.bounds()}")
print(f"  Elevation range: {valid.min():.2f} to {valid.max():.2f} m")
print(f"  Valid pixels: {len(valid):,} / {elev_2d.size:,}")

print("\n=== UTM DEM Extent ===")
print(f"  Shape: {clipped_utm.shape}")
print(f"  Bounds (EPSG:32751): {clipped_utm.rio.bounds()}")

print("\nStep 2 complete.")
