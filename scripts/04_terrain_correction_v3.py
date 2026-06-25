"""
Step 4 (v3): Terrain Correction and Complete Bouguer Anomaly
=============================================================
Input  : gravity_filled.csv
         dem_clipped_utm.tif  (UTM Zone 51S, EPSG:32751)

Formula:
    CBA = FAA - terrain_effect

    terrain_effect dihitung dengan 3D prism layer (Harmonica)
    - Land  (elev > 0) : density 2670 kg/m³
    - Ocean (elev <= 0): density 1630 kg/m³ (kontras: 2670 - 1040)

Output : output/gravity_with_cba.csv
         output/04_terrain_correction.png
"""

import matplotlib
matplotlib.use("Agg")

import os
import sys
import gc
import numpy as np
import pandas as pd
import rioxarray
import harmonica as hm
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

INPUT_CSV  = os.path.join(PROJECT_ROOT, "gravity_filled.csv")
INPUT_DEM  = os.path.join(PROJECT_ROOT, "output", "dem_clipped_utm.tif")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "gravity_with_cba.csv")
OUTPUT_FIG = os.path.join(OUTPUT_DIR, "04_terrain_correction.png")

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 65)
print("STEP 4 (v3): TERRAIN CORRECTION + COMPLETE BOUGUER ANOMALY")
print("=" * 65)

# ---------------------------------------------------------------------------
# Input checks
# ---------------------------------------------------------------------------
for path in [INPUT_CSV, INPUT_DEM]:
    if not os.path.exists(path):
        sys.exit(f"\nERROR: File tidak ditemukan:\n  {path}")

# ---------------------------------------------------------------------------
# 1. Load DEM
# ---------------------------------------------------------------------------
print("\n[1] Loading DEM ...")
dem = rioxarray.open_rasterio(INPUT_DEM, masked=True).squeeze()
print(f"    Shape    : {dem.shape}")
print(f"    CRS      : {dem.rio.crs}")
print(f"    Resolusi : {dem.rio.resolution()}")

# ---------------------------------------------------------------------------
# 2. Downsample DEM (factor 10 → ~1850 m)
# ---------------------------------------------------------------------------
COARSEN_FACTOR = 10
print(f"\n[2] Downsampling DEM (factor {COARSEN_FACTOR}) ...")
dem_coarse = dem.coarsen(x=COARSEN_FACTOR, y=COARSEN_FACTOR, boundary="trim").mean(skipna=True)
print(f"    Coarse shape     : {dem_coarse.shape}")
print(f"    Efektif resolusi : ~{abs(dem.rio.resolution()[0]) * COARSEN_FACTOR:.0f} m")

# ---------------------------------------------------------------------------
# 3. Extract coordinate arrays
# ---------------------------------------------------------------------------
easting  = dem_coarse.x.values
northing = dem_coarse.y.values
surface  = dem_coarse.values

# Flip northing ke ascending jika perlu
if northing[1] < northing[0]:
    print("    Flipping northing ke ascending.")
    northing = northing[::-1]
    surface  = surface[::-1, :]

print(f"\n    Easting  : {easting.min():.0f} – {easting.max():.0f} m")
print(f"    Northing : {northing.min():.0f} – {northing.max():.0f} m")
print(f"    Elevasi  : {np.nanmin(surface):.1f} – {np.nanmax(surface):.1f} m")

# Replace NaN dengan 0 (sea level)
n_nan = np.isnan(surface).sum()
if n_nan > 0:
    print(f"    Replacing {n_nan:,} NaN → 0 (sea level).")
    surface = np.where(np.isnan(surface), 0.0, surface)

# ---------------------------------------------------------------------------
# 4. Density array
# ---------------------------------------------------------------------------
density = np.where(surface > 0, 2670.0, 1630.0)
n_land  = (surface > 0).sum()
n_ocean = (surface <= 0).sum()
print(f"\n[3] Density array:")
print(f"    Land  (elev > 0)  : {n_land:,} prisms @ 2670 kg/m³")
print(f"    Ocean (elev <= 0) : {n_ocean:,} prisms @ 1630 kg/m³")

# ---------------------------------------------------------------------------
# 5. Prism layer
# ---------------------------------------------------------------------------
print("\n[4] Building prism layer ...")
prisms = hm.prism_layer(
    coordinates=(easting, northing),
    surface=surface,
    reference=0,
    properties={"density": density},
)
print(f"    Total prisms : ~{len(easting) * len(northing):,}")

# ---------------------------------------------------------------------------
# 6. Load gravity data
# ---------------------------------------------------------------------------
print(f"\n[5] Loading gravity data ...")
df = pd.read_csv(INPUT_CSV)
print(f"    Loaded  : {len(df):,} rows")
print(f"    Columns : {df.columns.tolist()}")

REQUIRED = {"FAA", "UTM_X", "UTM_Y", "Elevation_m"}
missing  = REQUIRED - set(df.columns)
if missing:
    sys.exit(f"ERROR: Kolom tidak ditemukan: {missing}")

obs_coords = (df["UTM_X"].values, df["UTM_Y"].values, df["Elevation_m"].values)

# ---------------------------------------------------------------------------
# 7. Terrain effect (batched)
# ---------------------------------------------------------------------------
print(f"\n[6] Computing terrain effect (batched) ...")
BATCH_SIZE = 5000
n_total    = len(df)
n_batches  = (n_total + BATCH_SIZE - 1) // BATCH_SIZE
results    = []

for i in range(n_batches):
    start = i * BATCH_SIZE
    end   = min(start + BATCH_SIZE, n_total)
    batch = (
        obs_coords[0][start:end],
        obs_coords[1][start:end],
        obs_coords[2][start:end],
    )
    results.append(prisms.prism_layer.gravity(batch, field="g_z"))
    if (i + 1) % 2 == 0 or (i + 1) == n_batches:
        print(f"    Batch {i+1:3d}/{n_batches}  (titik {start:,}–{end-1:,})")

terrain_effect = np.concatenate(results)
print("    Selesai.")

# ---------------------------------------------------------------------------
# 8. CBA
# ---------------------------------------------------------------------------
faa = df["FAA"].values
CBA = faa - terrain_effect

df["terrain_correction"] = terrain_effect
df["CBA"]                = CBA

# ---------------------------------------------------------------------------
# 9. Diagnostics
# ---------------------------------------------------------------------------
print("\n--- Terrain Effect ---")
print(f"    Min  : {terrain_effect.min():.4f} mGal")
print(f"    Max  : {terrain_effect.max():.4f} mGal")
print(f"    Mean : {terrain_effect.mean():.4f} mGal")
print(f"    Std  : {terrain_effect.std():.4f} mGal")

print("\n--- CBA ---")
print(f"    Min  : {CBA.min():.4f} mGal")
print(f"    Max  : {CBA.max():.4f} mGal")
print(f"    Mean : {CBA.mean():.4f} mGal")
print(f"    Std  : {CBA.std():.4f} mGal")

# ---------------------------------------------------------------------------
# 10. Save CSV
# ---------------------------------------------------------------------------
# Free large intermediates before CSV write — prism layer exhausts RAM
del prisms, dem, dem_coarse, surface, density, easting, northing, obs_coords, results
gc.collect()

df.to_csv(OUTPUT_CSV, index=False)
print(f"\n[7] Saved: {OUTPUT_CSV}")
print(f"    Rows    : {len(df):,}")
print(f"    Columns : {df.columns.tolist()}")

# ---------------------------------------------------------------------------
# 11. Figure: 3 panel
# ---------------------------------------------------------------------------
print("\n[8] Generating figure ...")

lon = df["Bujur"].values
lat = df["Lintang"].values

def sym_vlim(arr, pct=2):
    lim = max(abs(np.nanpercentile(arr, pct)),
              abs(np.nanpercentile(arr, 100 - pct)))
    return -lim, lim

fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.suptitle(
    "Step 4: Terrain Correction & Complete Bouguer Anomaly\n"
    "Airborne Gravity — Central Sulawesi, Indonesia",
    fontsize=13, fontweight="bold"
)

# Panel 1: Terrain Correction
sc0 = axes[0].scatter(lon, lat, c=terrain_effect, cmap="viridis",
                       s=1, linewidths=0, rasterized=True)
plt.colorbar(sc0, ax=axes[0], label="mGal", shrink=0.85)
axes[0].set_title("(a) Terrain Correction (mGal)")
axes[0].set_xlabel("Longitude (°E)")
axes[0].set_ylabel("Latitude (°N)")

# Panel 2: FAA
faa_vmin, faa_vmax = sym_vlim(faa)
sc1 = axes[1].scatter(lon, lat, c=faa, cmap="RdBu_r",
                       vmin=faa_vmin, vmax=faa_vmax,
                       s=1, linewidths=0, rasterized=True)
plt.colorbar(sc1, ax=axes[1], label="mGal", shrink=0.85)
axes[1].set_title("(b) Free Air Anomaly (mGal)")
axes[1].set_xlabel("Longitude (°E)")

# Panel 3: CBA
cba_vmin, cba_vmax = sym_vlim(CBA)
sc2 = axes[2].scatter(lon, lat, c=CBA, cmap="RdBu_r",
                       vmin=cba_vmin, vmax=cba_vmax,
                       s=1, linewidths=0, rasterized=True)
plt.colorbar(sc2, ax=axes[2], label="mGal", shrink=0.85)
axes[2].set_title("(c) Complete Bouguer Anomaly (mGal)")
axes[2].set_xlabel("Longitude (°E)")

plt.tight_layout(rect=[0, 0, 1, 0.93])
plt.savefig(OUTPUT_FIG, dpi=150, bbox_inches="tight")
plt.close()
print(f"    Saved: {OUTPUT_FIG}")

print("\n" + "=" * 65)
print("STEP 4 COMPLETE")
print(f"  Output CSV : {OUTPUT_CSV}")
print(f"  Output Fig : {OUTPUT_FIG}")
print("=" * 65)
