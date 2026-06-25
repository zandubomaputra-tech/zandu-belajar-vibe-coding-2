"""
Step 5: Gridding — Equivalent Sources interpolation of FAA and CBA.

Inputs:
    output/gravity_with_cba.csv

Outputs:
    output/faa_grid.nc
    output/cba_grid.nc
    output/05_gridded_maps.png
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
import harmonica as hm
import verde as vd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
INPUT_CSV = os.path.join(PROJECT_DIR, "output", "gravity_with_cba.csv")
OUT_FAA_NC = os.path.join(PROJECT_DIR, "output", "faa_grid.nc")
OUT_CBA_NC = os.path.join(PROJECT_DIR, "output", "cba_grid.nc")
OUT_FIG = os.path.join(PROJECT_DIR, "output", "05_gridded_maps.png")

# ---------------------------------------------------------------------------
# Input check
# ---------------------------------------------------------------------------
if not os.path.isfile(INPUT_CSV):
    print(f"ERROR: Input file not found: {INPUT_CSV}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
print("Loading data ...")
df = pd.read_csv(INPUT_CSV)

# Drop outliers for gridding if outlier_flag exists, otherwise use all points
if "outlier_flag" in df.columns:
    df_clean = df[df["outlier_flag"] == 0].copy()
else:
    df_clean = df.copy()
print(f"  Total points: {len(df)}, clean (non-outlier): {len(df_clean)}")

easting  = df_clean["UTM_X"].values
northing = df_clean["UTM_Y"].values
elevation = df_clean["Elevation_m"].values
faa_vals  = df_clean["FAA"].values
cba_vals  = df_clean["CBA"].values

# ---------------------------------------------------------------------------
# Survey region (UTM, with 5 km buffer)
# ---------------------------------------------------------------------------
region = (
    easting.min()  - 5000,
    easting.max()  + 5000,
    northing.min() - 5000,
    northing.max() + 5000,
)
print(f"  UTM region: E {region[0]:.0f}–{region[1]:.0f}, N {region[2]:.0f}–{region[3]:.0f}")

coordinates = (easting, northing, elevation)

# ---------------------------------------------------------------------------
# Helper: fit equivalent sources (with MemoryError fallback)
# ---------------------------------------------------------------------------
def fit_eqs(coords, values, label="field"):
    """Fit EquivalentSources; fall back to EquivalentSourcesGB on MemoryError."""
    print(f"\n  Fitting EquivalentSources for {label} ...")
    try:
        eqs = hm.EquivalentSources(damping=10, depth=10000)
        eqs.fit(coords, values)
        print("    EquivalentSources fit complete.")
    except MemoryError:
        print("    MemoryError — switching to EquivalentSourcesGB ...")
        eqs = hm.EquivalentSourcesGB(damping=10, depth=10000, window_size=50000, random_state=42)
        eqs.fit(coords, values)
        print("    EquivalentSourcesGB fit complete.")
    return eqs

# ---------------------------------------------------------------------------
# Grid coordinates (2 km spacing, height = 2000 m)
# ---------------------------------------------------------------------------
print("\nCreating grid coordinates (2 km spacing, height 2600 m) ...")
grid_coords = vd.grid_coordinates(region=region, spacing=2000, extra_coords=2600)
grid_east  = grid_coords[0]   # 2-D array
grid_north = grid_coords[1]   # 2-D array

east_1d  = np.unique(grid_east)
north_1d = np.unique(grid_north)
n_east   = len(east_1d)
n_north  = len(north_1d)
print(f"  Grid shape: {n_north} northing × {n_east} easting  ({n_north * n_east:,} cells)")

# ---------------------------------------------------------------------------
# FAA gridding
# ---------------------------------------------------------------------------
eqs_faa = fit_eqs(coordinates, faa_vals, label="FAA")

print("  Predicting FAA on grid ...")
faa_2d = eqs_faa.predict(grid_coords)

os.makedirs(os.path.dirname(OUT_FAA_NC), exist_ok=True)

ds_faa = xr.Dataset(
    {"FAA": (["northing", "easting"], faa_2d)},
    coords={"northing": north_1d, "easting": east_1d},
)
ds_faa["FAA"].attrs = {"units": "mGal", "long_name": "Free Air Anomaly"}
ds_faa["northing"].attrs = {"units": "m", "standard_name": "projection_y_coordinate"}
ds_faa["easting"].attrs = {"units": "m", "standard_name": "projection_x_coordinate"}
ds_faa.attrs = {
    "crs": "EPSG:32751 (UTM Zone 51S)",
    "grid_spacing_m": 2000,
    "prediction_height_m": 2600,
    "source": "EquivalentSourcesGB, harmonica 0.7"
}
ds_faa.to_netcdf(OUT_FAA_NC)
print(f"  Saved: {OUT_FAA_NC}")
print(f"  FAA grid range: {faa_2d.min():.2f} – {faa_2d.max():.2f} mGal")

# ---------------------------------------------------------------------------
# CBA gridding
# ---------------------------------------------------------------------------
eqs_cba = fit_eqs(coordinates, cba_vals, label="CBA")

print("  Predicting CBA on grid ...")
cba_2d = eqs_cba.predict(grid_coords)

os.makedirs(os.path.dirname(OUT_CBA_NC), exist_ok=True)

ds_cba = xr.Dataset(
    {"CBA": (["northing", "easting"], cba_2d)},
    coords={"northing": north_1d, "easting": east_1d},
)
ds_cba["CBA"].attrs = {"units": "mGal", "long_name": "Complete Bouguer Anomaly"}
ds_cba["northing"].attrs = {"units": "m", "standard_name": "projection_y_coordinate"}
ds_cba["easting"].attrs = {"units": "m", "standard_name": "projection_x_coordinate"}
ds_cba.attrs = {
    "crs": "EPSG:32751 (UTM Zone 51S)",
    "grid_spacing_m": 2000,
    "prediction_height_m": 2600,
    "source": "EquivalentSourcesGB, harmonica 0.7"
}
ds_cba.to_netcdf(OUT_CBA_NC)
print(f"  Saved: {OUT_CBA_NC}")
print(f"  CBA grid range: {cba_2d.min():.2f} – {cba_2d.max():.2f} mGal")

# ---------------------------------------------------------------------------
# Stats summary
# ---------------------------------------------------------------------------
print("\n=== Grid Summary ===")
print(f"  Grid shape (northing × easting): {n_north} × {n_east}")
print(f"  FAA grid : {faa_2d.min():.2f} to {faa_2d.max():.2f} mGal")
print(f"  CBA grid : {cba_2d.min():.2f} to {cba_2d.max():.2f} mGal")

# ---------------------------------------------------------------------------
# Figure: 2×2 subplots
# ---------------------------------------------------------------------------
print("\nGenerating figure ...")

fig, axes = plt.subplots(2, 2, figsize=(16, 14))

# Symmetric colour limits based on percentile for robustness
def sym_vlim(arr, pct=2):
    lo = np.nanpercentile(arr, pct)
    hi = np.nanpercentile(arr, 100 - pct)
    vabs = max(abs(lo), abs(hi))
    return -vabs, vabs

faa_vmin, faa_vmax = sym_vlim(faa_vals)
cba_vmin, cba_vmax = sym_vlim(cba_vals)

cmap = "RdBu_r"

# --- Top-left: FAA scatter ---
ax = axes[0, 0]
sc = ax.scatter(easting / 1e3, northing / 1e3, c=faa_vals, s=1,
                cmap=cmap, vmin=faa_vmin, vmax=faa_vmax, rasterized=True)
plt.colorbar(sc, ax=ax, label="FAA (mGal)")
ax.set_title("FAA — Raw Scatter")
ax.set_xlabel("Easting (km)")
ax.set_ylabel("Northing (km)")
ax.set_aspect("equal")

# --- Top-right: FAA gridded ---
ax = axes[0, 1]
pm = ax.pcolormesh(east_1d / 1e3, north_1d / 1e3, faa_2d,
                   cmap=cmap, vmin=faa_vmin, vmax=faa_vmax, shading="auto")
plt.colorbar(pm, ax=ax, label="FAA (mGal)")
ax.set_title("FAA — Gridded (Equivalent Sources, 2 km)")
ax.set_xlabel("Easting (km)")
ax.set_ylabel("Northing (km)")
ax.set_aspect("equal")

# --- Bottom-left: CBA scatter ---
ax = axes[1, 0]
sc = ax.scatter(easting / 1e3, northing / 1e3, c=cba_vals, s=1,
                cmap=cmap, vmin=cba_vmin, vmax=cba_vmax, rasterized=True)
plt.colorbar(sc, ax=ax, label="CBA (mGal)")
ax.set_title("CBA — Raw Scatter")
ax.set_xlabel("Easting (km)")
ax.set_ylabel("Northing (km)")
ax.set_aspect("equal")

# --- Bottom-right: CBA gridded ---
ax = axes[1, 1]
pm = ax.pcolormesh(east_1d / 1e3, north_1d / 1e3, cba_2d,
                   cmap=cmap, vmin=cba_vmin, vmax=cba_vmax, shading="auto")
plt.colorbar(pm, ax=ax, label="CBA (mGal)")
ax.set_title("CBA — Gridded (Equivalent Sources, 2 km)")
ax.set_xlabel("Easting (km)")
ax.set_ylabel("Northing (km)")
ax.set_aspect("equal")

fig.suptitle("Airborne Gravity Gridding — FAA and CBA (UTM Zone 51S)", fontsize=14)
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig(OUT_FIG, dpi=150)
plt.close()
print(f"  Saved: {OUT_FIG}")

print("\nDone.")
