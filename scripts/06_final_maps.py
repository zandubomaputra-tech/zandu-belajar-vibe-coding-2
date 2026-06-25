"""
Step 6 (v2): Final Maps + Regional-Residual Separation
=======================================================
Regional-residual separation method (Pramudya et al. 2025):
  1. Upward Continuation (UC) — FFT-based
       Regional_UC  = CBA continued upward to UC_HEIGHT_M
       Residual_UC  = CBA - Regional_UC
  2. Discrete Wavelet Transform (DWT) — 2D DWT via PyWavelets
       Regional_DWT = approximation coefficients reconstructed
       Residual_DWT = detail coefficients reconstructed
  3. Validation: Pearson correlation UC vs DWT (both regional and residual)

Inputs:
    output/faa_grid.nc
    output/cba_grid.nc
    output/dem_clipped.tif

Outputs:
    output/06_faa_anomaly_map.png
    output/06_cba_anomaly_map.png
    output/06_regional_residual.png
    output/06_combined_report.png
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import rioxarray
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from pyproj import Transformer
from scipy.stats import pearsonr
import pywt

# ─── Parameters ───────────────────────────────────────────────────────────────
# Upward continuation height (m).
# Pramudya 2025 used 15,000 m for an ~86×70 km area.
# Our survey is ~244×380 km (much larger), so we use 20,000 m to capture
# the same relative long-wavelength regional component.
UC_HEIGHT_M = 10_000

# DWT parameters
DWT_WAVELET = "db4"   # Daubechies 4 — standard for potential field data
DWT_LEVEL   = 4       # decomposition level (grid 122x190 supports up to ~4)

# ─── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR  = os.path.join(PROJECT_DIR, "output")

FAA_NC  = os.path.join(OUTPUT_DIR, "faa_grid.nc")
CBA_NC  = os.path.join(OUTPUT_DIR, "cba_grid.nc")
DEM_TIF = os.path.join(OUTPUT_DIR, "dem_clipped.tif")

OUT_FAA      = os.path.join(OUTPUT_DIR, "06_faa_anomaly_map.png")
OUT_CBA      = os.path.join(OUTPUT_DIR, "06_cba_anomaly_map.png")
OUT_REGSEP   = os.path.join(OUTPUT_DIR, "06_regional_residual.png")
OUT_COMBINED = os.path.join(OUTPUT_DIR, "06_combined_report.png")

# ─── Input checks ─────────────────────────────────────────────────────────────
print("=" * 65)
print("STEP 6 (v2): FINAL MAPS + REGIONAL-RESIDUAL SEPARATION")
print("=" * 65)

for fpath in [FAA_NC, CBA_NC, DEM_TIF]:
    if not os.path.exists(fpath):
        print(f"ERROR: Input file not found: {fpath}")
        sys.exit(1)
    size_mb = os.path.getsize(fpath) / 1e6
    print(f"  Found: {os.path.basename(fpath)} ({size_mb:.2f} MB)")

# ─── Load data ────────────────────────────────────────────────────────────────
print("\nLoading grids...")
faa_ds = xr.open_dataset(FAA_NC)
cba_ds = xr.open_dataset(CBA_NC)
print(f"  FAA shape: {faa_ds['FAA'].shape}")
print(f"  CBA shape: {cba_ds['CBA'].shape}")

print("Loading DEM...")
dem = rioxarray.open_rasterio(DEM_TIF, masked=True).squeeze()
print(f"  DEM shape: {dem.shape}")

# Ensure northing is ascending
if faa_ds.northing.values[0] > faa_ds.northing.values[-1]:
    print("  Flipping northing to ascending.")
    faa_ds = faa_ds.isel(northing=slice(None, None, -1))
    cba_ds = cba_ds.isel(northing=slice(None, None, -1))

# ─── Coordinate transform: UTM 51S → lon/lat ─────────────────────────────────
print("\nConverting UTM to geographic coordinates...")
transformer = Transformer.from_crs("EPSG:32751", "EPSG:4326", always_xy=True)
east_2d, north_2d = np.meshgrid(faa_ds.easting.values, faa_ds.northing.values)
lon_flat, lat_flat = transformer.transform(east_2d.flatten(), north_2d.flatten())
lon_2d = lon_flat.reshape(east_2d.shape)
lat_2d = lat_flat.reshape(east_2d.shape)

lon_min, lon_max = lon_2d.min(), lon_2d.max()
lat_min, lat_max = lat_2d.min(), lat_2d.max()
pad    = 0.1
extent = [lon_min - pad, lon_max + pad, lat_min - pad, lat_max + pad]
print(f"  Extent: lon [{lon_min:.3f}, {lon_max:.3f}], lat [{lat_min:.3f}, {lat_max:.3f}]")

faa_values = faa_ds["FAA"].values
cba_values = cba_ds["CBA"].values

# Grid spacing in meters (uniform 2 km grid)
SPACING_M = 2000.0

# ─── Helper functions ─────────────────────────────────────────────────────────
def sym_vlim(arr, pct=2):
    lim = max(abs(np.nanpercentile(arr, pct)), abs(np.nanpercentile(arr, 100 - pct)))
    return -lim, lim

def add_coastlines(ax, resolution="10m"):
    for res in (resolution, "50m"):
        try:
            ax.add_feature(cfeature.NaturalEarthFeature(
                "physical", "coastline", res,
                edgecolor="black", facecolor="none", linewidth=0.8
            ))
            return
        except Exception:
            continue
    print("  WARNING: Could not add coastlines.")

def add_gridlines(ax):
    gl = ax.gridlines(draw_labels=True, linewidth=0.5, color="gray",
                      alpha=0.7, linestyle="--")
    gl.top_labels = False
    gl.right_labels = False

def plot_map(ax, lon, lat, data, cmap, vmin, vmax, title, cbar_label):
    pcm = ax.pcolormesh(lon, lat, data, cmap=cmap, vmin=vmin, vmax=vmax,
                        transform=ccrs.PlateCarree(), shading="auto")
    cbar = plt.colorbar(pcm, ax=ax, orientation="vertical", pad=0.02, shrink=0.85)
    cbar.set_label(cbar_label, fontsize=9)
    add_coastlines(ax)
    add_gridlines(ax)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    return pcm

# ─── Upward Continuation (FFT-based) ─────────────────────────────────────────
def upward_continuation(grid_2d, spacing_m, height_m):
    """
    FFT-based upward continuation.
    Filter: H(k) = exp(-|k| * height_m), where k is radial wavenumber (rad/m).
    NaN cells are filled with the grid mean before FFT and restored after.
    """
    nan_mask  = np.isnan(grid_2d)
    fill_val  = np.nanmean(grid_2d)
    grid_fill = np.where(nan_mask, fill_val, grid_2d)

    nrow, ncol = grid_2d.shape
    kx = 2 * np.pi * np.fft.fftfreq(ncol, d=spacing_m)
    ky = 2 * np.pi * np.fft.fftfreq(nrow, d=spacing_m)
    KX, KY = np.meshgrid(kx, ky)
    K = np.sqrt(KX**2 + KY**2)

    F         = np.fft.fft2(grid_fill)
    F_cont    = F * np.exp(-K * height_m)
    continued = np.real(np.fft.ifft2(F_cont))
    continued[nan_mask] = np.nan
    return continued

# ─── Discrete Wavelet Transform (2D DWT) ─────────────────────────────────────
def dwt_regional_residual(grid_2d, wavelet=DWT_WAVELET, level=DWT_LEVEL):
    """
    2D DWT regional-residual separation.
    Regional = approximation coefficients only (low-frequency).
    Residual = original - regional (high-frequency details).
    """
    nan_mask  = np.isnan(grid_2d)
    fill_val  = np.nanmean(grid_2d)
    grid_fill = np.where(nan_mask, fill_val, grid_2d)

    coeffs = pywt.wavedec2(grid_fill, wavelet=wavelet, level=level)

    # Zero out all detail coefficients → reconstruct regional only
    coeffs_reg = [coeffs[0]] + [
        (np.zeros_like(d[0]), np.zeros_like(d[1]), np.zeros_like(d[2]))
        for d in coeffs[1:]
    ]
    regional = pywt.waverec2(coeffs_reg, wavelet=wavelet)
    regional = regional[:grid_2d.shape[0], :grid_2d.shape[1]]

    residual = grid_fill - regional
    regional[nan_mask] = np.nan
    residual[nan_mask] = np.nan
    return regional, residual

# ─── Run regional-residual separation ────────────────────────────────────────
print(f"\n[1] Upward Continuation (height = {UC_HEIGHT_M/1000:.0f} km) ...")
regional_uc  = upward_continuation(cba_values, SPACING_M, UC_HEIGHT_M)
residual_uc  = cba_values - regional_uc
print(f"    Regional UC  : {np.nanmin(regional_uc):.2f} to {np.nanmax(regional_uc):.2f} mGal")
print(f"    Residual UC  : {np.nanmin(residual_uc):.2f} to {np.nanmax(residual_uc):.2f} mGal")

print(f"\n[2] Discrete Wavelet Transform (wavelet={DWT_WAVELET}, level={DWT_LEVEL}) ...")
regional_dwt, residual_dwt = dwt_regional_residual(cba_values)
print(f"    Regional DWT : {np.nanmin(regional_dwt):.2f} to {np.nanmax(regional_dwt):.2f} mGal")
print(f"    Residual DWT : {np.nanmin(residual_dwt):.2f} to {np.nanmax(residual_dwt):.2f} mGal")

# Pearson validation (UC vs DWT) — following Pramudya 2025
valid = ~(np.isnan(regional_uc) | np.isnan(regional_dwt) |
          np.isnan(residual_uc) | np.isnan(residual_dwt))
r_reg, _ = pearsonr(regional_uc[valid].ravel(), regional_dwt[valid].ravel())
r_res, _ = pearsonr(residual_uc[valid].ravel(), residual_dwt[valid].ravel())

print(f"\n=== Validation: UC vs DWT (Pramudya 2025 method) ===")
print(f"    Pearson r (Regional) : {r_reg:.4f}  (Pramudya ref: 0.81)")
print(f"    Pearson r (Residual) : {r_res:.4f}  (Pramudya ref: 0.98)")

# ─── FAA map ─────────────────────────────────────────────────────────────────
print("\nPlotting FAA map...")
faa_vmin, faa_vmax = sym_vlim(faa_values)
try:
    fig, ax = plt.subplots(1, 1, figsize=(10, 8),
                           subplot_kw={"projection": ccrs.PlateCarree()})
    plot_map(ax, lon_2d, lat_2d, faa_values, "RdBu_r",
             faa_vmin, faa_vmax, "Free Air Anomaly (mGal)", "mGal")
    plt.tight_layout()
    plt.savefig(OUT_FAA, dpi=300, bbox_inches="tight")
    print(f"  Saved: {OUT_FAA}")
finally:
    plt.close("all")

# ─── CBA map ─────────────────────────────────────────────────────────────────
print("\nPlotting CBA map...")
cba_vmin, cba_vmax = sym_vlim(cba_values)
try:
    fig, ax = plt.subplots(1, 1, figsize=(10, 8),
                           subplot_kw={"projection": ccrs.PlateCarree()})
    plot_map(ax, lon_2d, lat_2d, cba_values, "RdBu_r",
             cba_vmin, cba_vmax, "Complete Bouguer Anomaly (mGal)", "mGal")
    plt.tight_layout()
    plt.savefig(OUT_CBA, dpi=300, bbox_inches="tight")
    print(f"  Saved: {OUT_CBA}")
finally:
    plt.close("all")

# ─── Regional-Residual 4-panel comparison ────────────────────────────────────
print("\nPlotting regional-residual comparison (4-panel)...")
reg_vmin, reg_vmax = sym_vlim(np.concatenate([regional_uc[valid], regional_dwt[valid]]))
res_vmin, res_vmax = sym_vlim(np.concatenate([residual_uc[valid], residual_dwt[valid]]))

try:
    fig = plt.figure(figsize=(18, 14))
    proj = ccrs.PlateCarree()

    panels = [
        (regional_uc,  "RdBu_r", reg_vmin, reg_vmax,
         f"(a) Regional — Upward Continuation ({UC_HEIGHT_M/1000:.0f} km)", "mGal"),
        (residual_uc,  "RdBu_r", res_vmin, res_vmax,
         "(b) Residual — Upward Continuation", "mGal"),
        (regional_dwt, "RdBu_r", reg_vmin, reg_vmax,
         f"(c) Regional — DWT ({DWT_WAVELET}, level {DWT_LEVEL})", "mGal"),
        (residual_dwt, "RdBu_r", res_vmin, res_vmax,
         "(d) Residual — DWT", "mGal"),
    ]

    for i, (data, cmap, vmin, vmax, title, cbar_lbl) in enumerate(panels):
        ax = fig.add_subplot(2, 2, i + 1, projection=proj)
        plot_map(ax, lon_2d, lat_2d, data, cmap, vmin, vmax, title, cbar_lbl)

    fig.suptitle(
        f"Regional-Residual Separation — Central Sulawesi\n"
        f"UC vs DWT Validation: r(regional)={r_reg:.3f}, r(residual)={r_res:.3f}",
        fontsize=13, fontweight="bold", y=0.98
    )
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(OUT_REGSEP, dpi=300, bbox_inches="tight")
    print(f"  Saved: {OUT_REGSEP}")
finally:
    plt.close("all")

# ─── 4-panel combined report (DEM / FAA / CBA / Residual_UC) ─────────────────
print("\nPlotting 4-panel combined report...")
dem_lon  = dem.x.values
dem_lat  = dem.y.values
dem_data = dem.values
dem_vmin, dem_vmax = np.nanpercentile(dem_data, [2, 98])

try:
    fig  = plt.figure(figsize=(18, 14))
    proj = ccrs.PlateCarree()

    # Panel (a): DEM
    ax = fig.add_subplot(2, 2, 1, projection=proj)
    ax.set_extent(extent, crs=proj)
    dem_lon_2d, dem_lat_2d = np.meshgrid(dem_lon, dem_lat)
    pcm = ax.pcolormesh(dem_lon_2d, dem_lat_2d, dem_data, cmap="terrain",
                        vmin=dem_vmin, vmax=dem_vmax,
                        transform=proj, shading="auto")
    plt.colorbar(pcm, ax=ax, pad=0.02, shrink=0.85).set_label("m", fontsize=9)
    add_coastlines(ax)
    add_gridlines(ax)
    ax.set_title("(a) Topography / Bathymetry (m)", fontsize=11, fontweight="bold")

    # Panel (b): FAA
    ax = fig.add_subplot(2, 2, 2, projection=proj)
    plot_map(ax, lon_2d, lat_2d, faa_values, "RdBu_r",
             faa_vmin, faa_vmax, "(b) Free Air Anomaly (mGal)", "mGal")

    # Panel (c): CBA
    ax = fig.add_subplot(2, 2, 3, projection=proj)
    plot_map(ax, lon_2d, lat_2d, cba_values, "RdBu_r",
             cba_vmin, cba_vmax, "(c) Complete Bouguer Anomaly (mGal)", "mGal")

    # Panel (d): Residual (UC method — primary)
    ax = fig.add_subplot(2, 2, 4, projection=proj)
    plot_map(ax, lon_2d, lat_2d, residual_uc, "RdBu_r",
             res_vmin, res_vmax,
             f"(d) Residual Anomaly — UC {UC_HEIGHT_M/1000:.0f} km (mGal)", "mGal")

    fig.suptitle("Airborne Gravity Survey — Central Sulawesi, Indonesia",
                 fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(OUT_COMBINED, dpi=300, bbox_inches="tight")
    print(f"  Saved: {OUT_COMBINED}")
finally:
    plt.close("all")

# ─── Verify outputs ──────────────────────────────────────────────────────────
print("\n=== Output verification ===")
all_ok = True
for fpath in [OUT_FAA, OUT_CBA, OUT_REGSEP, OUT_COMBINED]:
    if os.path.exists(fpath):
        size_kb = os.path.getsize(fpath) / 1e3
        print(f"  OK  {os.path.basename(fpath)} ({size_kb:.1f} KB)")
    else:
        print(f"  MISSING  {os.path.basename(fpath)}")
        all_ok = False

print("\n=== Summary ===")
print(f"  UC height         : {UC_HEIGHT_M/1000:.0f} km")
print(f"  DWT wavelet/level : {DWT_WAVELET} / {DWT_LEVEL}")
print(f"  r regional UC/DWT : {r_reg:.4f}")
print(f"  r residual UC/DWT : {r_res:.4f}")

if all_ok:
    print("\nStep 6 complete — all output maps produced successfully.")
else:
    print("\nStep 6 FAILED — some outputs are missing.")
    sys.exit(1)
