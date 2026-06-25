"""
Step 2 (v2): DEM Preparation + Elevation Crosscheck
====================================================
- Merge & clip BATNAS DEM tiles
- Reproject to UTM Zone 51S
- Sample DEM elevation at each gravity station coordinate
- Crosscheck: compare CSV Elevation_m vs DEM elevation
- Flag points with large discrepancies
- Output gravity CSV with DEM elevation + validation columns
- Generate diagnostic figures
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import rioxarray
from rasterio.enums import Resampling
from rioxarray.merge import merge_arrays

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR  = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR   = os.path.join(PROJECT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

TILE_N       = os.path.join(PROJECT_DIR, "BATNAS_120E-125E_000-05N_MSL_v1.5.tif")
TILE_S       = os.path.join(PROJECT_DIR, "BATNAS_120E-125E_05S-000_MSL_v1.5.tif")
GRAVITY_CSV  = os.path.join(OUTPUT_DIR,  "gravity_clean.csv")

OUT_MERGED   = os.path.join(OUTPUT_DIR, "dem_merged.tif")
OUT_CLIPPED  = os.path.join(OUTPUT_DIR, "dem_clipped.tif")
OUT_UTM      = os.path.join(OUTPUT_DIR, "dem_clipped_utm.tif")
OUT_CSV      = os.path.join(OUTPUT_DIR, "gravity_with_dem.csv")
OUT_FIG1     = os.path.join(OUTPUT_DIR, "02_dem_preview.png")
OUT_FIG2     = os.path.join(OUTPUT_DIR, "02_elevation_crosscheck.png")

# Survey clip bounds with buffer
MINX, MINY, MAXX, MAXY = 120.5, -2.5, 124.5, 0.5

# Crosscheck threshold: flag points where |CSV_elev - DEM_elev| > threshold (m)
DIFF_THRESHOLD = 50.0   # meter

print("=" * 65)
print("STEP 2 (v2): DEM PREPARATION + ELEVATION CROSSCHECK")
print("=" * 65)

# ---------------------------------------------------------------------------
# 1. Open tiles & assign CRS
# ---------------------------------------------------------------------------
for p in [TILE_N, TILE_S, GRAVITY_CSV]:
    if not os.path.exists(p):
        sys.exit(f"ERROR: File not found: {p}")

print("\n[1] Opening BATNAS tiles...")
tile_n = rioxarray.open_rasterio(TILE_N, masked=True)
tile_s = rioxarray.open_rasterio(TILE_S, masked=True)
print(f"    North tile shape : {tile_n.shape}  bounds: {tile_n.rio.bounds()}")
print(f"    South tile shape : {tile_s.shape}  bounds: {tile_s.rio.bounds()}")

print("    Assigning CRS EPSG:4326 to both tiles...")
tile_n = tile_n.rio.write_crs("EPSG:4326", inplace=True)
tile_s = tile_s.rio.write_crs("EPSG:4326", inplace=True)

# ---------------------------------------------------------------------------
# 2. Merge tiles
# ---------------------------------------------------------------------------
print("\n[2] Merging tiles...")
merged = merge_arrays([tile_n, tile_s])
print(f"    Merged shape : {merged.shape}  bounds: {merged.rio.bounds()}")
merged.rio.to_raster(OUT_MERGED)
print(f"    Saved: {OUT_MERGED}")

# ---------------------------------------------------------------------------
# 3. Clip to survey region
# ---------------------------------------------------------------------------
print(f"\n[3] Clipping to survey bounds [{MINX},{MINY}] - [{MAXX},{MAXY}]...")
clipped = merged.rio.clip_box(minx=MINX, miny=MINY, maxx=MAXX, maxy=MAXY)
clipped = clipped.rio.write_nodata(np.nan)
clipped.rio.to_raster(OUT_CLIPPED)
elev_arr = clipped.values.squeeze()
valid_px  = elev_arr[~np.isnan(elev_arr)]
print(f"    Clipped shape  : {clipped.shape}")
print(f"    Elevation range: {valid_px.min():.2f} to {valid_px.max():.2f} m")
print(f"    Mean elevation : {valid_px.mean():.2f} m")
print(f"    Saved: {OUT_CLIPPED}")

# ---------------------------------------------------------------------------
# 4. Reproject to UTM Zone 51S
# ---------------------------------------------------------------------------
print("\n[4] Reprojecting to UTM Zone 51S (EPSG:32751)...")
clipped_utm = clipped.rio.reproject("EPSG:32751", resampling=Resampling.bilinear)
clipped_utm.rio.to_raster(OUT_UTM)
print(f"    UTM shape  : {clipped_utm.shape}")
print(f"    UTM bounds : {clipped_utm.rio.bounds()}")
print(f"    Saved: {OUT_UTM}")

# ---------------------------------------------------------------------------
# 5. Load gravity stations
# ---------------------------------------------------------------------------
print("\n[5] Loading gravity stations...")
df = pd.read_csv(GRAVITY_CSV)
print(f"    Loaded {len(df):,} rows")

# ---------------------------------------------------------------------------
# 6. Sample DEM elevation at each gravity station (bilinear interpolation)
# ---------------------------------------------------------------------------
print("\n[6] Sampling DEM elevation at each gravity station...")

# Build a small xarray Dataset for sampling
# rioxarray.sel with method="nearest" is fast for point sampling
x_coords = clipped.x.values   # longitude array
y_coords = clipped.y.values   # latitude array
dem_data  = clipped.values.squeeze()  # 2D elevation array

def sample_dem_at_points(dem_2d, x_arr, y_arr, lon_pts, lat_pts):
    """
    Bilinear interpolation of DEM values at arbitrary lon/lat points.
    Returns array of sampled elevations (NaN if outside DEM extent).
    """
    from scipy.interpolate import RegularGridInterpolator

    # y_arr may be descending (north-up raster) — need ascending for interpolator
    if y_arr[0] > y_arr[-1]:
        dem_flipped = dem_2d[::-1, :]
        y_sorted    = y_arr[::-1]
    else:
        dem_flipped = dem_2d
        y_sorted    = y_arr

    # Replace NaN with mean for interpolation (edge handling)
    dem_fill = np.where(np.isnan(dem_flipped), np.nanmean(dem_flipped), dem_flipped)

    interp = RegularGridInterpolator(
        (y_sorted, x_arr), dem_fill,
        method="linear", bounds_error=False, fill_value=np.nan
    )
    pts = np.column_stack([lat_pts, lon_pts])
    return interp(pts)

sampled_elev = sample_dem_at_points(
    dem_data, x_coords, y_coords,
    df["Bujur"].values, df["Lintang"].values
)

df["DEM_elev_m"] = sampled_elev
n_sampled = (~np.isnan(sampled_elev)).sum()
print(f"    Successfully sampled: {n_sampled:,} / {len(df):,} points")

# ---------------------------------------------------------------------------
# 7. Crosscheck: CSV Elevation_m vs DEM elevation
# ---------------------------------------------------------------------------
print("\n[7] Crosschecking CSV Elevation_m vs DEM elevation...")

df["elev_diff_m"] = df["Elevation_m"] - df["DEM_elev_m"]

diff        = df["elev_diff_m"].dropna()
rmse        = np.sqrt((diff ** 2).mean())
mae         = diff.abs().mean()
bias        = diff.mean()
std_diff    = diff.std()

print(f"\n    --- Crosscheck Statistics ---")
print(f"    Bias (mean diff CSV - DEM) : {bias:+.4f} m")
print(f"    Std of difference          : {std_diff:.4f} m")
print(f"    MAE                        : {mae:.4f} m")
print(f"    RMSE                       : {rmse:.4f} m")
print(f"    Min diff                   : {diff.min():.4f} m")
print(f"    Max diff                   : {diff.max():.4f} m")

# Flag large discrepancies
df["elev_flag"] = (df["elev_diff_m"].abs() > DIFF_THRESHOLD).astype(int)
n_flagged = df["elev_flag"].sum()
pct_flagged = 100 * n_flagged / len(df)
print(f"\n    Threshold for flagging     : ±{DIFF_THRESHOLD} m")
print(f"    Flagged points             : {n_flagged:,} ({pct_flagged:.2f}%)")

# Interpretation
print("\n    --- Interpretation ---")
if abs(bias) < 10 and rmse < 50:
    print("    ✅ CSV Elevation_m closely matches DEM — data is RELIABLE")
    print("       Safe to use Elevation_m directly in Bouguer correction.")
elif abs(bias) < 50 and rmse < 150:
    print("    ⚠️  Moderate discrepancy detected.")
    print("       CSV Elevation_m may be flight altitude, not surface elevation.")
    print("       Consider using DEM_elev_m for Bouguer correction.")
else:
    print("    ❌ Large discrepancy! CSV Elevation_m likely = flight altitude.")
    print("       Use DEM_elev_m for Bouguer correction in Step 3.")

# Decide which elevation to use
if abs(bias) < 50:
    df["Elevation_final"] = df["Elevation_m"]
    elev_source = "CSV Elevation_m"
else:
    df["Elevation_final"] = df["DEM_elev_m"]
    elev_source = "DEM_elev_m"
print(f"\n    → Recommended elevation for Step 3: [{elev_source}]")
print(f"      (stored in column 'Elevation_final')")

# ---------------------------------------------------------------------------
# 8. Save output CSV
# ---------------------------------------------------------------------------
df.to_csv(OUT_CSV, index=False)
print(f"\n[8] Saved: {OUT_CSV}  ({len(df):,} rows, {len(df.columns)} columns)")
print(f"    New columns added: DEM_elev_m, elev_diff_m, elev_flag, Elevation_final")

# ---------------------------------------------------------------------------
# 9. Figure 1 — DEM Preview with gravity stations
# ---------------------------------------------------------------------------
print("\n[9] Generating figures...")

x_c = clipped.x.values
y_c = clipped.y.values

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle("Step 2 — DEM Preview", fontsize=13, fontweight="bold")

vmin, vmax = np.nanpercentile(dem_data, [2, 98])

im1 = axes[0].pcolormesh(x_c, y_c, dem_data, cmap="terrain",
                          vmin=vmin, vmax=vmax, shading="auto")
plt.colorbar(im1, ax=axes[0], label="Elevation (m)")
axes[0].set_title("BATNAS DEM (clipped)")
axes[0].set_xlabel("Longitude (°E)")
axes[0].set_ylabel("Latitude (°N)")

im2 = axes[1].pcolormesh(x_c, y_c, dem_data, cmap="terrain",
                          vmin=vmin, vmax=vmax, shading="auto")
plt.colorbar(im2, ax=axes[1], label="Elevation (m)")
axes[1].scatter(df["Bujur"], df["Lintang"], s=0.5, c="red",
                alpha=0.5, linewidths=0, label="Gravity stations")
axes[1].set_title("DEM + Gravity Stations")
axes[1].set_xlabel("Longitude (°E)")
axes[1].legend(loc="upper right", markerscale=10, fontsize=8)

plt.tight_layout()
plt.savefig(OUT_FIG1, dpi=150, bbox_inches="tight")
plt.close()
print(f"    Saved: {OUT_FIG1}")

# ---------------------------------------------------------------------------
# 10. Figure 2 — Elevation Crosscheck Diagnostic
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(2, 2, figsize=(14, 11))
fig.suptitle("Step 2 — Elevation Crosscheck: CSV vs DEM", fontsize=13, fontweight="bold")

valid_mask = ~(df["DEM_elev_m"].isna() | df["Elevation_m"].isna())
csv_e = df.loc[valid_mask, "Elevation_m"].values
dem_e = df.loc[valid_mask, "DEM_elev_m"].values
diff_v = df.loc[valid_mask, "elev_diff_m"].values
lon_v  = df.loc[valid_mask, "Bujur"].values
lat_v  = df.loc[valid_mask, "Lintang"].values

# (a) Scatter: CSV vs DEM (1:1 line)
ax = axes[0, 0]
ax.scatter(dem_e, csv_e, s=0.5, alpha=0.3, c="steelblue", linewidths=0)
lim_min = min(dem_e.min(), csv_e.min())
lim_max = max(dem_e.max(), csv_e.max())
ax.plot([lim_min, lim_max], [lim_min, lim_max], "r-", lw=1.2, label="1:1 line")
ax.set_xlabel("DEM Elevation (m)")
ax.set_ylabel("CSV Elevation_m (m)")
ax.set_title("(a) CSV vs DEM Elevation (1:1 scatter)")
ax.legend(fontsize=8)
ax.text(0.05, 0.92, f"Bias={bias:+.1f} m\nRMSE={rmse:.1f} m",
        transform=ax.transAxes, fontsize=8,
        bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7))

# (b) Histogram of differences
ax = axes[0, 1]
ax.hist(diff_v, bins=80, color="steelblue", edgecolor="white", linewidth=0.3)
ax.axvline(0, color="black", lw=1, linestyle="--", label="Zero")
ax.axvline(bias, color="red", lw=1.2, linestyle="-", label=f"Bias={bias:+.1f} m")
ax.axvline(DIFF_THRESHOLD, color="orange", lw=1, linestyle=":", label=f"+{DIFF_THRESHOLD} m threshold")
ax.axvline(-DIFF_THRESHOLD, color="orange", lw=1, linestyle=":")
ax.set_xlabel("CSV Elevation − DEM Elevation (m)")
ax.set_ylabel("Count")
ax.set_title("(b) Distribution of Elevation Difference")
ax.legend(fontsize=8)

# (c) Spatial map of elevation difference
ax = axes[1, 0]
diff_lim = np.nanpercentile(np.abs(diff_v), 98)
sc = ax.scatter(lon_v, lat_v, c=diff_v, cmap="RdBu_r",
                vmin=-diff_lim, vmax=diff_lim, s=1, linewidths=0)
plt.colorbar(sc, ax=ax, label="CSV − DEM (m)")
ax.set_title("(c) Spatial Pattern of Elevation Difference")
ax.set_xlabel("Longitude (°E)")
ax.set_ylabel("Latitude (°N)")

# (d) Spatial map of flagged points
ax = axes[1, 1]
colors = np.where(df.loc[valid_mask, "elev_flag"].values == 1, "red", "steelblue")
ax.scatter(lon_v, lat_v, c=colors, s=1, linewidths=0, alpha=0.6)
from matplotlib.lines import Line2D
legend_els = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor='steelblue', markersize=6, label=f'OK ({(~df["elev_flag"].astype(bool)).sum():,})'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=6, label=f'Flagged (>{DIFF_THRESHOLD}m): {n_flagged:,}'),
]
ax.legend(handles=legend_els, fontsize=8, loc="upper right")
ax.set_title(f"(d) Flagged Points (|diff| > {DIFF_THRESHOLD} m)")
ax.set_xlabel("Longitude (°E)")
ax.set_ylabel("Latitude (°N)")

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig(OUT_FIG2, dpi=150, bbox_inches="tight")
plt.close()
print(f"    Saved: {OUT_FIG2}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 65)
print("STEP 2 (v2) COMPLETE — Summary")
print("=" * 65)
print(f"  DEM merged             : {OUT_MERGED}")
print(f"  DEM clipped (geo)      : {OUT_CLIPPED}")
print(f"  DEM clipped (UTM)      : {OUT_UTM}")
print(f"  Gravity + DEM CSV      : {OUT_CSV}")
print(f"  DEM preview figure     : {OUT_FIG1}")
print(f"  Crosscheck figure      : {OUT_FIG2}")
print(f"\n  Crosscheck result:")
print(f"    Bias   = {bias:+.2f} m")
print(f"    RMSE   = {rmse:.2f} m")
print(f"    Flagged= {n_flagged:,} ({pct_flagged:.1f}%)")
print(f"    → Use column [Elevation_final] = [{elev_source}] in Step 3")
print("=" * 65)
