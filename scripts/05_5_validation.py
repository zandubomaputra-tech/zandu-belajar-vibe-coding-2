"""
Step 5.5: Sensitivity Analysis and TOPEX Validation
===================================================
Tasks:
  1. Sensitivity Analysis: Vary Equivalent Sources depth (5000, 10000, 15000 m)
     and damping (1, 10, 100) on CBA data. Plot a 3x3 grid of gridded CBA maps
     and compute standard deviations to quantify sensitivity.
  2. TOPEX Validation: Interpolate gridded FAA from equivalent sources to
     43,621 TOPEX satellite points, compute correlation, RMSE, and bias,
     and generate a publication-quality scatter plot.

Inputs:
  - output/gravity_with_cba.csv
  - output/faa_grid.nc
  - topex120124_0-3.csv

Outputs:
  - output/05_5_sensitivity_analysis.png
  - output/05_5_topex_validation.png
"""

import os
import sys
import gc
import numpy as np
import pandas as pd
import xarray as xr
import harmonica as hm
import verde as vd
import matplotlib.pyplot as plt
from pyproj import Transformer
from scipy.stats import pearsonr

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR   = os.path.join(PROJECT_ROOT, "output")

INPUT_CSV     = os.path.join(OUTPUT_DIR, "gravity_with_cba.csv")
FAA_NC        = os.path.join(OUTPUT_DIR, "faa_grid.nc")
TOPEX_CSV     = os.path.join(PROJECT_ROOT, "topex120124_0-3.csv")

OUT_SENS_FIG  = os.path.join(OUTPUT_DIR, "05_5_sensitivity_analysis.png")
OUT_VAL_FIG   = os.path.join(OUTPUT_DIR, "05_5_topex_validation.png")

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 65)
print("STEP 5.5: SENSITIVITY ANALYSIS AND TOPEX VALIDATION")
print("=" * 65)

# Verify inputs
for path in [INPUT_CSV, FAA_NC, TOPEX_CSV]:
    if not os.path.exists(path):
        sys.exit(f"\nERROR: File tidak ditemukan:\n  {path}")

# ---------------------------------------------------------------------------
# 1. Sensitivity Analysis (Vary depth and damping)
# ---------------------------------------------------------------------------
print("\n[1] Running Equivalent Sources Sensitivity Analysis ...")
df_cba = pd.read_csv(INPUT_CSV)
easting = df_cba["UTM_X"].values
northing = df_cba["UTM_Y"].values
elevation = df_cba["Elevation_m"].values
cba_vals = df_cba["CBA"].values

coordinates = (easting, northing, elevation)

# Define region of survey with 5 km buffer
region = (
    easting.min()  - 5000,
    easting.max()  + 5000,
    northing.min() - 5000,
    northing.max() + 5000,
)

# Grid coordinates for prediction (2 km spacing, prediction height = 2600 m)
grid_coords = vd.grid_coordinates(region=region, spacing=2000, extra_coords=2600)
east_1d  = np.unique(grid_coords[0])
north_1d = np.unique(grid_coords[1])

depths = [5000, 10000, 15000]
dampings = [1, 10, 100]

fig, axes = plt.subplots(3, 3, figsize=(18, 16), sharex=True, sharey=True)
fig.suptitle(
    "Sensitivity Analysis: Effect of Depth and Damping on CBA Grid (mGal)\n"
    "Airborne Gravity — Central Sulawesi",
    fontsize=16, fontweight="bold", y=0.96
)

results = {}

for idp, depth in enumerate(depths):
    for idm, damping in enumerate(dampings):
        print(f"    Testing depth = {depth:5d} m, damping = {damping:3d} ...")
        
        # Use EquivalentSourcesGB to avoid MemoryError
        eqs = hm.EquivalentSourcesGB(
            damping=damping,
            depth=depth,
            window_size=50000,
            random_state=42
        )
        eqs.fit(coordinates, cba_vals)
        cba_grid = eqs.predict(grid_coords)
        
        # Save reference grid for stats (depth=10000, damping=10)
        results[(depth, damping)] = cba_grid
        
        # Plot on corresponding axes
        ax = axes[idp, idm]
        pm = ax.pcolormesh(
            east_1d / 1e3, north_1d / 1e3, cba_grid,
            cmap="RdBu_r", vmin=-40, vmax=130, shading="auto"
        )
        ax.set_title(f"Depth: {depth} m | Damping: {damping}", fontsize=11, fontweight="bold")
        ax.set_aspect("equal")
        
        # Labels
        if idp == 2:
            ax.set_xlabel("Easting (km)")
        if idm == 0:
            ax.set_ylabel("Northing (km)")
            
        # Add colorbar for each plot
        plt.colorbar(pm, ax=ax, shrink=0.7, label="mGal")
        
        # Free memory
        del eqs
        gc.collect()

plt.tight_layout(rect=[0, 0, 1, 0.94])
plt.savefig(OUT_SENS_FIG, dpi=150, bbox_inches="tight")
plt.close()
print(f"  Saved sensitivity plot: {OUT_SENS_FIG}")

# Print standard deviation tables relative to reference grid (10000, 10)
ref_grid = results[(10000, 10)]
print("\n=== Sensitivity Grid Statistics (Difference from Reference Grid [10km, 10]) ===")
print(f"{'Depth (m)':<10} | {'Damping':<8} | {'Min Diff (mGal)':<16} | {'Max Diff (mGal)':<16} | {'RMS Diff (mGal)':<16}")
print("-" * 75)
for depth in depths:
    for damping in dampings:
        diff = results[(depth, damping)] - ref_grid
        min_d = np.nanmin(diff)
        max_d = np.nanmax(diff)
        rms_d = np.sqrt(np.nanmean(diff**2))
        print(f"{depth:<10d} | {damping:<8d} | {min_d:<16.4f} | {max_d:<16.4f} | {rms_d:<16.4f}")

# Clean up sensitivity arrays
del results, ref_grid
gc.collect()

# ---------------------------------------------------------------------------
# 2. TOPEX Validation
# ---------------------------------------------------------------------------
print("\n[2] Running TOPEX Validation ...")

# Load FAA grid NetCDF
ds_faa = xr.open_dataset(FAA_NC)
print(f"    Airborne FAA grid loaded. Shape: {ds_faa['FAA'].shape}")

# Load TOPEX satellite CSV
df_topex = pd.read_csv(TOPEX_CSV)
print(f"    Loaded TOPEX data: {len(df_topex):,} points.")
print(f"    Columns: {df_topex.columns.tolist()}")

# Project TOPEX Coordinates (lon/lat EPSG:4326) to UTM Zone 51S (EPSG:32751)
print("    Projecting TOPEX coordinates to UTM ...")
transformer = Transformer.from_crs("EPSG:4326", "EPSG:32751", always_xy=True)
topex_east, topex_north = transformer.transform(df_topex["lon"].values, df_topex["lat"].values)

# Add projected coordinates to DataFrame
df_topex["UTM_X"] = topex_east
df_topex["UTM_Y"] = topex_north

# Create xarray query arrays
query_east = xr.DataArray(topex_east, dims="points")
query_north = xr.DataArray(topex_north, dims="points")

# Interpolate airborne FAA grid to TOPEX point locations
print("    Interpolating airborne FAA to TOPEX coordinates ...")
faa_interpolated = ds_faa["FAA"].interp(
    easting=query_east,
    northing=query_north,
    method="linear"
).values

df_topex["faa_airborne"] = faa_interpolated

# Filter out points that are outside the airborne survey coverage (where interpolated value is NaN)
df_valid = df_topex.dropna(subset=["faa_airborne"]).copy()
print(f"    Overlapping points inside survey area: {len(df_valid):,} (out of {len(df_topex):,})")

if len(df_valid) == 0:
    sys.exit("ERROR: Tidak ada data TOPEX yang bertumpang tindih dengan area survey.")

# Calculate statistics
airborne_faa = df_valid["faa_airborne"].values
topex_faa = df_valid["faa_topex"].values

r_coeff, _ = pearsonr(airborne_faa, topex_faa)
rmse = np.sqrt(np.mean((airborne_faa - topex_faa)**2))
bias = np.mean(airborne_faa - topex_faa)
std_residual = np.std(airborne_faa - topex_faa)

print("\n=== TOPEX Validation Statistics ===")
print(f"  Pearson Correlation (r) : {r_coeff:.4f}")
print(f"  RMSE                    : {rmse:.4f} mGal")
print(f"  Mean Bias (Air - TOPEX) : {bias:.4f} mGal")
print(f"  Std. Dev of Residuals   : {std_residual:.4f} mGal")

# ---------------------------------------------------------------------------
# Generate validation plot
# ---------------------------------------------------------------------------
print("\n[3] Generating validation figures ...")
fig, ax = plt.subplots(figsize=(8, 7))

# Density scatter plot
sc = ax.scatter(
    topex_faa, airborne_faa,
    c=np.abs(airborne_faa - topex_faa),
    cmap="viridis", s=1, alpha=0.6, rasterized=True
)
plt.colorbar(sc, ax=ax, label="Absolute difference (mGal)")

# 1:1 Line
min_val = min(topex_faa.min(), airborne_faa.min())
max_val = max(topex_faa.max(), airborne_faa.max())
ax.plot([min_val, max_val], [min_val, max_val], "r--", linewidth=1.5, label="1:1 Reference Line")

# Regression Fit Line
slope, intercept = np.polyfit(topex_faa, airborne_faa, 1)
fit_line = slope * np.array([min_val, max_val]) + intercept
ax.plot([min_val, max_val], fit_line, "b-", linewidth=1.5, label=f"Linear Fit (y = {slope:.2f}x + {intercept:.2f})")

ax.set_xlabel("TOPEX Satellite FAA (mGal)", fontsize=11)
ax.set_ylabel("Airborne Gridded FAA (mGal)", fontsize=11)
ax.set_title("TOPEX Satellite vs. Airborne FAA Validation\nCentral Sulawesi, Indonesia", fontsize=12, fontweight="bold")
ax.grid(True, linestyle="--", alpha=0.5)
ax.legend(loc="upper left")

# Stats box
stats_text = (
    f"Points: {len(df_valid):,}\n"
    f"Correlation (r): {r_coeff:.4f}\n"
    f"RMSE: {rmse:.2f} mGal\n"
    f"Bias: {bias:.2f} mGal\n"
    f"Std. Dev: {std_residual:.2f} mGal"
)
props = dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray')
ax.text(0.65, 0.05, stats_text, transform=ax.transAxes, fontsize=10,
        verticalalignment='bottom', bbox=props)

plt.tight_layout()
plt.savefig(OUT_VAL_FIG, dpi=300, bbox_inches="tight")
plt.close()
print(f"  Saved validation plot: {OUT_VAL_FIG}")

print("\n" + "=" * 65)
print("STEP 5.5 COMPLETE")
print(f"  Sensitivity map: {OUT_SENS_FIG}")
print(f"  Validation plot: {OUT_VAL_FIG}")
print("=" * 65)
