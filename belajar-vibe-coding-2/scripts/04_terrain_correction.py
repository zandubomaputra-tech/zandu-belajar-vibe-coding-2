"""
Step 4: Terrain Correction and Complete Bouguer Anomaly
=======================================================
Computes the gravitational effect of terrain (topography/bathymetry) using a
prism layer built from the DEM (reference=0, surface=terrain), then subtracts
it from FAA to produce the Complete Bouguer Anomaly (CBA).

harmonica.prism_layer.gravity(field="g_z") sign convention:
  - Mass ABOVE observation point: g_z < 0  (downward pull in g_z convention)
  - Mass BELOW observation point: g_z > 0  (upward relative contribution)

The prism layer (reference=0 to terrain surface) already encapsulates the full
Bouguer slab effect at the station elevation. Therefore the Bouguer slab
correction (bouguer_correction) must NOT be subtracted separately — it would
double-count. The correct formula is:

CBA = FAA - terrain_effect

This is equivalent to CBA = SBA + TC in classical geophysics, where the prism
layer naturally combines both the Bouguer slab and terrain residual corrections.

Inputs:
    output/gravity_with_bouguer.csv  -- gravity data with SBA
    output/dem_clipped_utm.tif       -- DEM in UTM Zone 51S (EPSG:32751)

Outputs:
    output/gravity_with_cba.csv
    output/04_terrain_correction.png
"""

import matplotlib
matplotlib.use("Agg")

import os
import sys
import numpy as np
import pandas as pd
import rioxarray
import harmonica as hm
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
output_dir = os.path.join(project_root, "output")

INPUT_CSV = os.path.join(output_dir, "gravity_with_bouguer.csv")
INPUT_DEM = os.path.join(output_dir, "dem_clipped_utm.tif")
OUTPUT_CSV = os.path.join(output_dir, "gravity_with_cba.csv")
OUTPUT_FIG = os.path.join(output_dir, "04_terrain_correction.png")

# ---------------------------------------------------------------------------
# I1 - Input file existence checks
# ---------------------------------------------------------------------------
for path, label in [
    (INPUT_DEM, "Step 2 (02_dem_preparation.py)"),
    (INPUT_CSV, "Step 3 (03_bouguer_anomaly.py)"),
]:
    if not os.path.exists(path):
        sys.exit(f"ERROR: '{path}' not found. Run {label} first.")

# ---------------------------------------------------------------------------
# 1. Load DEM
# ---------------------------------------------------------------------------
print("Loading DEM:", INPUT_DEM)
dem = rioxarray.open_rasterio(INPUT_DEM, masked=True).squeeze()
print(f"  DEM shape (y, x): {dem.shape}  CRS: {dem.rio.crs}")
print(f"  Resolution: {dem.rio.resolution()}")

# ---------------------------------------------------------------------------
# 2. Downsample DEM (factor 10 → ~1850 m spacing, ~43K prisms)
# ---------------------------------------------------------------------------
COARSEN_FACTOR = 10
print(f"\nDownsampling DEM by factor {COARSEN_FACTOR} ...")
dem_coarse = dem.coarsen(x=COARSEN_FACTOR, y=COARSEN_FACTOR, boundary="trim").mean(skipna=True)
print(f"  Coarse DEM shape (y, x): {dem_coarse.shape}")
print(f"  Effective resolution: ~{abs(dem.rio.resolution()[0]) * COARSEN_FACTOR:.0f} m")

# ---------------------------------------------------------------------------
# 3. Extract coordinate arrays (1D) and surface (2D)
# ---------------------------------------------------------------------------
easting = dem_coarse.x.values    # 1D, shape (nx,)
northing = dem_coarse.y.values   # 1D, shape (ny,)
surface = dem_coarse.values      # 2D, shape (ny, nx)

# Raster convention: northing decreases (top=north). harmonica.prism_layer
# requires northing to be monotonically INCREASING (south-to-north order).
# Flip northing axis and corresponding surface rows.
if northing[1] < northing[0]:
    print("  Flipping northing to ascending order (south-to-north).")
    northing = northing[::-1]
    surface = surface[::-1, :]

print(f"\n  Easting  range: {easting.min():.0f} – {easting.max():.0f} m")
print(f"  Northing range: {northing.min():.0f} – {northing.max():.0f} m")
print(f"  Elevation range: {np.nanmin(surface):.1f} – {np.nanmax(surface):.1f} m")
print(f"  NaN count in surface: {np.isnan(surface).sum()}")

# Handle NaNs: replace with 0 (sea level) if any — keeps prism layer complete.
# This avoids masking issues; prisms at 0 contribute near-zero effect.
n_nan = np.isnan(surface).sum()
if n_nan > 0:
    print(f"  Replacing {n_nan} NaN elevation values with 0 (sea level).")
    surface = np.where(np.isnan(surface), 0.0, surface)

# ---------------------------------------------------------------------------
# 4. Build density array (2D, same shape as surface)
#    Land (elev > 0): crustal density 2670 kg/m³
#    Ocean (elev <= 0): density contrast = 2670 - 1040 = 1630 kg/m³
#
#    Density verdict: large-grid infinite-slab test confirms that 1630 kg/m³
#    (the rock-water density contrast) is correct for marine prisms.  When
#    surface < 0 the prism models the rock-equivalent column (seafloor to sea
#    level).  Using the contrast (1630) instead of the full crust density
#    (2670) keeps the terrain_effect equivalent to the classical Bouguer slab
#    (hm.bouguer_correction) for flat marine terrain, so CBA ≈ SBA there.
#    Using 2670 for marine prisms overcorrects by ~137 mGal per 3163 m depth.
# ---------------------------------------------------------------------------
density = np.where(surface > 0, 2670.0, 2670.0 - 1040.0)
print(f"\n  Density stats — min: {density.min():.0f}  max: {density.max():.0f} kg/m³")

# ---------------------------------------------------------------------------
# 5. Create prism layer
#    hm.prism_layer expects 1D coordinate arrays and 2D surface/density arrays.
# ---------------------------------------------------------------------------
print("\nBuilding prism layer ...")
prisms = hm.prism_layer(
    coordinates=(easting, northing),
    surface=surface,
    reference=0,
    properties={"density": density},
)
print(f"  Prism layer dataset:\n{prisms}")

# ---------------------------------------------------------------------------
# 6. Load gravity data and prepare observation coordinates
# ---------------------------------------------------------------------------
print("\nLoading gravity data:", INPUT_CSV)
df = pd.read_csv(INPUT_CSV)
print(f"  Loaded {len(df):,} rows with columns: {df.columns.tolist()}")

# Observation coordinates in UTM (same CRS as DEM): (easting, northing, upward)
obs_easting = df["UTM_X"].values
obs_northing = df["UTM_Y"].values
obs_upward = df["Elevation_m"].values  # Height above reference (sea level)
obs_coords = (obs_easting, obs_northing, obs_upward)

# ---------------------------------------------------------------------------
# 7. Compute terrain gravitational effect (forward model)
#    Attempt full computation; fall back to batching if MemoryError.
# ---------------------------------------------------------------------------
print("\nComputing terrain gravitational effect ...")
BATCH_SIZE = 5000

def compute_terrain_effect_batched(prisms_ds, coordinates, batch_size):
    """Compute terrain gravity in batches to avoid memory errors."""
    east, north, up = coordinates
    n_total = len(east)
    results = []
    n_batches = (n_total + batch_size - 1) // batch_size
    for i in range(n_batches):
        start = i * batch_size
        end = min(start + batch_size, n_total)
        batch_coords = (east[start:end], north[start:end], up[start:end])
        batch_result = prisms_ds.prism_layer.gravity(batch_coords, field="g_z")
        results.append(batch_result)
        if (i + 1) % 5 == 0 or (i + 1) == n_batches:
            print(f"  Batch {i+1}/{n_batches}  (points {start}–{end-1})")
    return np.concatenate(results)

print(f"  Using batched computation (batch_size={BATCH_SIZE}) ...")
terrain_effect = compute_terrain_effect_batched(prisms, obs_coords, BATCH_SIZE)
print("  Batched computation complete.")

# ---------------------------------------------------------------------------
# 8. Compute Complete Bouguer Anomaly
#
#    Sign convention of hm.prism_layer.gravity(field="g_z"):
#      g_z < 0 for mass ABOVE obs point; g_z > 0 for mass BELOW obs point.
#
#    The prism layer (reference=0, surface=terrain) models the SAME mass column
#    as the Bouguer slab, so bouguer_correction is already included in
#    terrain_effect. Double-subtracting bouguer_correction amplifies anomalies.
#
#    Correct formula: CBA = FAA - terrain_effect
#    (removes the full Bouguer + terrain effect in one step)
# ---------------------------------------------------------------------------
faa = df["FAA"].values
bouguer_corr = df["bouguer_correction"].values  # not used in CBA formula (prism model replaces Bouguer slab entirely)
sba = df["SBA"].values

CBA = faa - terrain_effect

# ---------------------------------------------------------------------------
# 9. Add results to dataframe
# ---------------------------------------------------------------------------
df["terrain_correction"] = terrain_effect
df["CBA"] = CBA

# ---------------------------------------------------------------------------
# 10. Print diagnostics
# ---------------------------------------------------------------------------
print("\n--- Terrain Effect Statistics ---")
print(f"  Min  : {terrain_effect.min():.4f} mGal")
print(f"  Max  : {terrain_effect.max():.4f} mGal")
print(f"  Mean : {terrain_effect.mean():.4f} mGal")
print(f"  Std  : {terrain_effect.std():.4f} mGal")

print("\n--- Complete Bouguer Anomaly (CBA) Statistics ---")
print(f"  Min  : {CBA.min():.4f} mGal")
print(f"  Max  : {CBA.max():.4f} mGal")
print(f"  Mean : {CBA.mean():.4f} mGal")
print(f"  Std  : {CBA.std():.4f} mGal")

print("\n--- Smoothness Comparison (SBA vs CBA) ---")
print(f"  SBA std: {sba.std():.4f} mGal")
print(f"  CBA std: {CBA.std():.4f} mGal")
if CBA.std() < sba.std():
    print("  CBA is smoother than SBA (as expected).")
else:
    print("  WARNING: CBA is NOT smoother than SBA — review terrain correction sign/magnitude.")

# ---------------------------------------------------------------------------
# 11. Save output CSV
# ---------------------------------------------------------------------------
os.makedirs(output_dir, exist_ok=True)
df.to_csv(OUTPUT_CSV, index=False)
print(f"\nSaved: {OUTPUT_CSV}  ({len(df):,} rows, {len(df.columns)} columns)")

# ---------------------------------------------------------------------------
# 12. Generate figure: 3 side-by-side subplots
# ---------------------------------------------------------------------------
lon = df["Bujur"].values
lat = df["Lintang"].values

fig, axes = plt.subplots(1, 3, figsize=(18, 6))
fig.suptitle("Step 4: Terrain Correction and Complete Bouguer Anomaly", fontsize=13, fontweight="bold")

# Left: Terrain correction (viridis)
sc0 = axes[0].scatter(lon, lat, c=terrain_effect, cmap="viridis", s=1, linewidths=0)
plt.colorbar(sc0, ax=axes[0], label="mGal", shrink=0.85)
axes[0].set_title("Terrain Correction (mGal)")
axes[0].set_xlabel("Longitude")
axes[0].set_ylabel("Latitude")

# Middle: SBA (RdBu_r, symmetric)
sba_lim = np.max(np.abs([sba.min(), sba.max()]))
sc1 = axes[1].scatter(lon, lat, c=sba, cmap="RdBu_r", vmin=-sba_lim, vmax=sba_lim, s=1, linewidths=0)
plt.colorbar(sc1, ax=axes[1], label="mGal", shrink=0.85)
axes[1].set_title("Simple Bouguer Anomaly (mGal)")
axes[1].set_xlabel("Longitude")
axes[1].set_ylabel("Latitude")

# Right: CBA (RdBu_r, symmetric)
cba_lim = np.max(np.abs([CBA.min(), CBA.max()]))
sc2 = axes[2].scatter(lon, lat, c=CBA, cmap="RdBu_r", vmin=-cba_lim, vmax=cba_lim, s=1, linewidths=0)
plt.colorbar(sc2, ax=axes[2], label="mGal", shrink=0.85)
axes[2].set_title("Complete Bouguer Anomaly (mGal)")
axes[2].set_xlabel("Longitude")
axes[2].set_ylabel("Latitude")

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig(OUTPUT_FIG, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved figure: {OUTPUT_FIG}")

print("\nStep 4 complete.")
