"""
Step 3: Simple Bouguer Anomaly Calculation
==========================================
Computes the Simple Bouguer Anomaly (SBA) from the Free Air Anomaly (FAA)
using harmonica's bouguer_correction, which handles land and marine points
automatically based on the sign of elevation.

Input:  output/gravity_clean.csv
Output: output/gravity_with_bouguer.csv
        output/03_bouguer_anomaly.png
"""

import matplotlib
matplotlib.use("Agg")

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import harmonica as hm

# ---------------------------------------------------------------------------
# 1. Load cleaned gravity data
# ---------------------------------------------------------------------------
# Anchor paths to script location
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
output_dir = os.path.join(project_root, "output")

INPUT_CSV = os.path.join(output_dir, "gravity_clean.csv")
OUTPUT_CSV = os.path.join(output_dir, "gravity_with_bouguer.csv")
OUTPUT_FIG = os.path.join(output_dir, "03_bouguer_anomaly.png")

# Check input file exists
if not os.path.exists(INPUT_CSV):
    sys.exit(f"ERROR: '{INPUT_CSV}' not found. Run scripts/01_data_loading_qc.py first.")

print("Loading gravity data from:", INPUT_CSV)
df = pd.read_csv(INPUT_CSV)
print(f"  Loaded {len(df):,} rows with columns: {df.columns.tolist()}")

# Validate required columns
REQUIRED_COLS = {"Elevation_m", "FAA", "Bujur", "Lintang"}
missing = REQUIRED_COLS - set(df.columns)
if missing:
    sys.exit(f"ERROR: Missing columns in input: {missing}")

# ---------------------------------------------------------------------------
# 2. Compute Simple Bouguer Anomaly
# ---------------------------------------------------------------------------
elevation = df["Elevation_m"].values  # numpy array; negative = marine
faa = df["FAA"].values                # Free Air Anomaly (mGal)

# harmonica.bouguer_correction handles land (positive elev) and marine
# (negative elev / bathymetry) automatically using the respective densities.
bouguer_corr = hm.bouguer_correction(
    elevation,
    density_crust=2670,
    density_water=1040,
)

simple_bouguer_anomaly = faa - bouguer_corr

# ---------------------------------------------------------------------------
# 3. Add new columns to dataframe
# ---------------------------------------------------------------------------
df["bouguer_correction"] = bouguer_corr
df["SBA"] = simple_bouguer_anomaly

# ---------------------------------------------------------------------------
# 4. Summary statistics
# ---------------------------------------------------------------------------
n_land   = int((elevation >= 0).sum())
n_marine = int((elevation < 0).sum())

print("\n--- Bouguer Correction Statistics ---")
print(f"  Min  : {bouguer_corr.min():.4f} mGal")
print(f"  Max  : {bouguer_corr.max():.4f} mGal")
print(f"  Mean : {bouguer_corr.mean():.4f} mGal")

print("\n--- Simple Bouguer Anomaly (SBA) Statistics ---")
print(f"  Min  : {simple_bouguer_anomaly.min():.4f} mGal")
print(f"  Max  : {simple_bouguer_anomaly.max():.4f} mGal")
print(f"  Mean : {simple_bouguer_anomaly.mean():.4f} mGal")

print(f"\n--- Point Counts ---")
print(f"  Land points   (elevation >= 0): {n_land:,}")
print(f"  Marine points (elevation <  0): {n_marine:,}")
print(f"  Total                         : {len(df):,}")

# ---------------------------------------------------------------------------
# 5. Save output CSV
# ---------------------------------------------------------------------------
os.makedirs(output_dir, exist_ok=True)
df.to_csv(OUTPUT_CSV, index=False)
print(f"\nSaved: {OUTPUT_CSV}  ({len(df):,} rows, {len(df.columns)} columns)")

# ---------------------------------------------------------------------------
# 6. Generate figure
# ---------------------------------------------------------------------------
lon = df["Bujur"].values
lat = df["Lintang"].values

# Symmetric colormap limits centred on zero for both panels
faa_lim = np.max(np.abs([faa.min(), faa.max()]))
sba_lim = np.max(np.abs([simple_bouguer_anomaly.min(), simple_bouguer_anomaly.max()]))

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle("Airborne Gravity — Bouguer Anomaly Processing", fontsize=13, fontweight="bold")

# Left: Free Air Anomaly
sc1 = axes[0].scatter(
    lon, lat, c=faa, cmap="RdBu_r",
    vmin=-faa_lim, vmax=faa_lim,
    s=1, linewidths=0,
)
plt.colorbar(sc1, ax=axes[0], label="mGal", shrink=0.85)
axes[0].set_title("Free Air Anomaly (mGal)")
axes[0].set_xlabel("Longitude")
axes[0].set_ylabel("Latitude")

# Right: Simple Bouguer Anomaly
sc2 = axes[1].scatter(
    lon, lat, c=simple_bouguer_anomaly, cmap="RdBu_r",
    vmin=-sba_lim, vmax=sba_lim,
    s=1, linewidths=0,
)
plt.colorbar(sc2, ax=axes[1], label="mGal", shrink=0.85)
axes[1].set_title("Simple Bouguer Anomaly (mGal)")
axes[1].set_xlabel("Longitude")
axes[1].set_ylabel("Latitude")

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig(OUTPUT_FIG, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved figure: {OUTPUT_FIG}")

print("\nStep 3 complete.")
