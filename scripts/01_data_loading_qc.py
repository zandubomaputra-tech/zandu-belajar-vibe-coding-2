"""
Step 1: Data Loading and Quality Control
Airborne Gravity Data Processing Pipeline

Loads gravity_filled.csv, performs QC checks, generates a QC figure,
and saves cleaned data with outlier flags.
"""

import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend for file output
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_CSV = os.path.join(PROJECT_ROOT, "gravity_filled.csv")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "gravity_clean.csv")
OUTPUT_FIG = os.path.join(OUTPUT_DIR, "01_qc_report.png")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------------------------
print("=" * 60)
print("STEP 1: DATA LOADING & QUALITY CONTROL")
print("=" * 60)

print(f"\nLoading: {INPUT_CSV}")
try:
    df = pd.read_csv(INPUT_CSV)
except FileNotFoundError:
    sys.exit(f"ERROR: Input file not found: {INPUT_CSV}")
print(f"Loaded {len(df):,} rows, {len(df.columns)} columns.")

REQUIRED_COLS = {"Bujur", "Lintang", "FAA", "Elevation_m", "UTM_X", "UTM_Y"}
missing = REQUIRED_COLS - set(df.columns)
if missing:
    sys.exit(f"ERROR: Input CSV is missing required columns: {missing}")

# ---------------------------------------------------------------------------
# 2. QC checks
# ---------------------------------------------------------------------------

# 2a. Shape, dtypes, statistics
print("\n--- Shape ---")
print(f"Rows: {df.shape[0]:,}   Columns: {df.shape[1]}")

print("\n--- Column dtypes ---")
print(df.dtypes.to_string())

print("\n--- Descriptive Statistics ---")
print(df.describe().to_string())

# 2b. NaN counts
print("\n--- NaN / Null counts per column ---")
nan_counts = df.isnull().sum()
print(nan_counts.to_string())
total_nan = nan_counts.sum()
print(f"Total NaN cells: {total_nan}")

# 2c. Duplicate coordinates
dup_mask = df.duplicated(subset=["Bujur", "Lintang"], keep=False)
n_dup_rows = dup_mask.sum()
n_dup_pairs = df[dup_mask].groupby(["Bujur", "Lintang"]).ngroups if n_dup_rows > 0 else 0
print(f"\n--- Duplicate coordinate pairs (Bujur+Lintang) ---")
print(f"Rows involved in duplicates: {n_dup_rows}")
print(f"Distinct duplicate coordinate pairs: {n_dup_pairs}")

# 2d. FAA outlier detection via IQR (3*IQR rule)
print("\n--- FAA Outlier Detection (IQR method, threshold = 3*IQR) ---")
Q1 = df["FAA"].quantile(0.25)
Q3 = df["FAA"].quantile(0.75)
IQR = Q3 - Q1
lower_fence = Q1 - 3 * IQR
upper_fence = Q3 + 3 * IQR
print(f"Q1 = {Q1:.4f} mGal,  Q3 = {Q3:.4f} mGal,  IQR = {IQR:.4f} mGal")
print(f"Lower fence: {lower_fence:.4f} mGal")
print(f"Upper fence: {upper_fence:.4f} mGal")

n_outliers_raw = ((df["FAA"] < lower_fence) | (df["FAA"] > upper_fence)).sum()
print(f"Outliers detected (raw): {n_outliers_raw} ({100 * n_outliers_raw / len(df):.2f}% of data)")

# 2e. Geographic extent
print("\n--- Geographic Extent ---")
print(f"Longitude (Bujur):  {df['Bujur'].min():.4f}° to {df['Bujur'].max():.4f}°E")
print(f"Latitude  (Lintang):{df['Lintang'].min():.4f}° to {df['Lintang'].max():.4f}°N")

# ---------------------------------------------------------------------------
# 3. QC Figure
# ---------------------------------------------------------------------------
print("\nGenerating QC figure ...")

fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle("Airborne Gravity Data — QC Report (Step 1)", fontsize=14, fontweight="bold")

# (a) Scatter: lon vs lat colored by FAA
ax = axes[0, 0]
sc = ax.scatter(
    df["Bujur"], df["Lintang"],
    c=df["FAA"], cmap="RdBu_r",
    s=1, linewidths=0, alpha=0.6
)
cbar = fig.colorbar(sc, ax=ax)
cbar.set_label("FAA (mGal)")
ax.set_xlabel("Longitude (°E)")
ax.set_ylabel("Latitude (°N)")
ax.set_title("(a) Free Air Anomaly (FAA)")

# (b) Histogram of FAA
ax = axes[0, 1]
ax.hist(df["FAA"].dropna(), bins=80, color="steelblue", edgecolor="white", linewidth=0.3)
ax.axvline(lower_fence, color="red", linestyle="--", linewidth=1, label=f"Lower fence ({lower_fence:.1f})")
ax.axvline(upper_fence, color="red", linestyle="--", linewidth=1, label=f"Upper fence ({upper_fence:.1f})")
ax.set_xlabel("FAA (mGal)")
ax.set_ylabel("Count")
ax.set_title("(b) FAA Distribution")
ax.legend(fontsize=8)

# (c) Scatter: lon vs lat colored by Elevation_m
ax = axes[1, 0]
sc2 = ax.scatter(
    df["Bujur"], df["Lintang"],
    c=df["Elevation_m"], cmap="terrain",
    s=1, linewidths=0, alpha=0.6
)
cbar2 = fig.colorbar(sc2, ax=ax)
cbar2.set_label("Elevation (m)")
ax.set_xlabel("Longitude (°E)")
ax.set_ylabel("Latitude (°N)")
ax.set_title("(c) Elevation (m)")

# (d) Histogram of Elevation_m
ax = axes[1, 1]
ax.hist(df["Elevation_m"].dropna(), bins=80, color="saddlebrown", edgecolor="white", linewidth=0.3)
ax.set_xlabel("Elevation (m)")
ax.set_ylabel("Count")
ax.set_title("(d) Elevation Distribution")

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig(OUTPUT_FIG, dpi=150, bbox_inches="tight")
plt.close()
print(f"Figure saved: {OUTPUT_FIG}")

# ---------------------------------------------------------------------------
# 4. Save cleaned data with outlier flag
# ---------------------------------------------------------------------------
print("\nSaving cleaned CSV ...")

# Drop rows where key gravity/position columns are NaN
df_clean = df.dropna(subset=["Bujur", "Lintang", "FAA", "Elevation_m"]).copy()
rows_dropped = len(df) - len(df_clean)
print(f"Rows dropped (NaN): {rows_dropped}")

# Compute outlier mask on cleaned data
outlier_mask = (df_clean["FAA"] < lower_fence) | (df_clean["FAA"] > upper_fence)
df_clean["outlier_flag"] = outlier_mask.astype(int)

df_clean.to_csv(OUTPUT_CSV, index=False)
print(f"Cleaned data saved: {OUTPUT_CSV}")
print(f"  Rows in output: {len(df_clean):,}  (outlier_flag=1: {df_clean['outlier_flag'].sum()})")

print("\n" + "=" * 60)
print("STEP 1 COMPLETE")
print("=" * 60)
