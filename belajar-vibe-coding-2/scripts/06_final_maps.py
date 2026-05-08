"""
Step 6: Final Maps
Produce publication-quality maps of FAA, CBA, DEM, and residual anomaly.

Inputs:
    output/faa_grid.nc       - Gridded FAA (UTM Zone 51S, EPSG:32751)
    output/cba_grid.nc       - Gridded CBA (UTM Zone 51S, EPSG:32751)
    output/dem_clipped.tif   - DEM in geographic coords (EPSG:4326)

Outputs:
    output/06_faa_anomaly_map.png
    output/06_cba_anomaly_map.png
    output/06_combined_report.png
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend before pyplot import
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import rioxarray
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from pyproj import Transformer
import verde as vd

# ─── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")

FAA_NC   = os.path.join(OUTPUT_DIR, "faa_grid.nc")
CBA_NC   = os.path.join(OUTPUT_DIR, "cba_grid.nc")
DEM_TIF  = os.path.join(OUTPUT_DIR, "dem_clipped.tif")

OUT_FAA      = os.path.join(OUTPUT_DIR, "06_faa_anomaly_map.png")
OUT_CBA      = os.path.join(OUTPUT_DIR, "06_cba_anomaly_map.png")
OUT_COMBINED = os.path.join(OUTPUT_DIR, "06_combined_report.png")

# ─── Input file checks ────────────────────────────────────────────────────────
for fpath in [FAA_NC, CBA_NC, DEM_TIF]:
    if not os.path.exists(fpath):
        print(f"ERROR: Input file not found: {fpath}")
        sys.exit(1)
    else:
        size_mb = os.path.getsize(fpath) / 1e6
        print(f"  Found: {os.path.basename(fpath)} ({size_mb:.2f} MB)")

# ─── Load data ────────────────────────────────────────────────────────────────
print("\nLoading FAA grid...")
faa_ds = xr.open_dataset(FAA_NC)
print(f"  FAA shape: {faa_ds['FAA'].shape}")

print("Loading CBA grid...")
cba_ds = xr.open_dataset(CBA_NC)
print(f"  CBA shape: {cba_ds['CBA'].shape}")

print("Loading DEM...")
dem = rioxarray.open_rasterio(DEM_TIF, masked=True).squeeze()
print(f"  DEM shape: {dem.shape}")
print(f"  DEM x: {float(dem.x.min()):.3f} to {float(dem.x.max()):.3f}")
print(f"  DEM y: {float(dem.y.min()):.3f} to {float(dem.y.max()):.3f}")

# C1: Verify northing is ascending (south to north) as expected
northing_vals = faa_ds.northing.values
if northing_vals[0] > northing_vals[-1]:
    print("WARNING: Northing axis is descending — flipping for correct map orientation")
    faa_ds = faa_ds.isel(northing=slice(None, None, -1))
    cba_ds = cba_ds.isel(northing=slice(None, None, -1))

# ─── Coordinate transformation: UTM 51S → Lon/Lat ────────────────────────────
print("\nConverting UTM coordinates to geographic...")
transformer = Transformer.from_crs("EPSG:32751", "EPSG:4326", always_xy=True)

east_2d, north_2d = np.meshgrid(faa_ds.easting.values, faa_ds.northing.values)
lon_flat, lat_flat = transformer.transform(east_2d.flatten(), north_2d.flatten())
lon_2d = lon_flat.reshape(east_2d.shape)
lat_2d = lat_flat.reshape(east_2d.shape)

# Data extent (padded slightly)
lon_min, lon_max = lon_2d.min(), lon_2d.max()
lat_min, lat_max = lat_2d.min(), lat_2d.max()
pad = 0.1
extent = [lon_min - pad, lon_max + pad, lat_min - pad, lat_max + pad]
print(f"  Extent: lon [{lon_min:.3f}, {lon_max:.3f}], lat [{lat_min:.3f}, {lat_max:.3f}]")

# ─── Symmetric colour limit helper ────────────────────────────────────────────
def sym_vlim(arr, pct=2):
    """Symmetric colormap limits using percentile clipping (2nd/98th)."""
    lim = max(abs(np.nanpercentile(arr, pct)), abs(np.nanpercentile(arr, 100 - pct)))
    return -lim, lim

# ─── Coastline helper (try 10m, fall back to 50m) ────────────────────────────
def add_coastlines(ax, resolution="10m"):
    try:
        ax.add_feature(
            cfeature.NaturalEarthFeature(
                "physical", "coastline", resolution,
                edgecolor="black", facecolor="none", linewidth=0.8
            )
        )
    except Exception:
        try:
            ax.add_feature(
                cfeature.NaturalEarthFeature(
                    "physical", "coastline", "50m",
                    edgecolor="black", facecolor="none", linewidth=0.8
                )
            )
        except Exception as e:
            print(f"  WARNING: Could not add coastlines: {e}")

def add_gridlines(ax):
    gl = ax.gridlines(
        draw_labels=True, linewidth=0.5, color="gray",
        alpha=0.7, linestyle="--"
    )
    gl.top_labels = False
    gl.right_labels = False
    return gl

# ─── FAA map ─────────────────────────────────────────────────────────────────
print("\nPlotting FAA map...")
faa_values = faa_ds["FAA"].values
faa_vmin, faa_vmax = sym_vlim(faa_values)

try:
    fig, ax = plt.subplots(
        1, 1, figsize=(10, 8),
        subplot_kw={"projection": ccrs.PlateCarree()}
    )
    ax.set_extent(extent, crs=ccrs.PlateCarree())

    pcm = ax.pcolormesh(
        lon_2d, lat_2d, faa_values,
        cmap="RdBu_r",
        vmin=faa_vmin, vmax=faa_vmax,
        transform=ccrs.PlateCarree(),
        shading="auto"
    )
    cbar = plt.colorbar(pcm, ax=ax, orientation="vertical", pad=0.02, shrink=0.85)
    cbar.set_label("mGal", fontsize=11)
    add_coastlines(ax)
    add_gridlines(ax)
    ax.set_title("Free Air Anomaly (mGal)", fontsize=14, fontweight="bold", pad=12)

    plt.tight_layout()
    plt.savefig(OUT_FAA, dpi=300, bbox_inches="tight")
    print(f"  Saved: {OUT_FAA}")
finally:
    plt.close("all")

# ─── CBA map ─────────────────────────────────────────────────────────────────
print("\nPlotting CBA map...")
cba_values = cba_ds["CBA"].values
cba_vmin, cba_vmax = sym_vlim(cba_values)

try:
    fig, ax = plt.subplots(
        1, 1, figsize=(10, 8),
        subplot_kw={"projection": ccrs.PlateCarree()}
    )
    ax.set_extent(extent, crs=ccrs.PlateCarree())

    pcm = ax.pcolormesh(
        lon_2d, lat_2d, cba_values,
        cmap="RdBu_r",
        vmin=cba_vmin, vmax=cba_vmax,
        transform=ccrs.PlateCarree(),
        shading="auto"
    )
    cbar = plt.colorbar(pcm, ax=ax, orientation="vertical", pad=0.02, shrink=0.85)
    cbar.set_label("mGal", fontsize=11)
    add_coastlines(ax)
    add_gridlines(ax)
    ax.set_title("Complete Bouguer Anomaly (mGal)", fontsize=14, fontweight="bold", pad=12)

    plt.tight_layout()
    plt.savefig(OUT_CBA, dpi=300, bbox_inches="tight")
    print(f"  Saved: {OUT_CBA}")
finally:
    plt.close("all")

# ─── Residual anomaly (CBA - regional trend) ─────────────────────────────────
print("\nComputing residual anomaly (CBA - regional trend)...")
cba_flat = cba_ds["CBA"].values.flatten()
coords_flat = (lon_2d.flatten(), lat_2d.flatten())

mask = ~np.isnan(cba_flat)
# Regional trend fitted in geographic coords (lon/lat) — adequate for this ~3° extent
trend = vd.Trend(degree=1)
trend.fit(
    coordinates=(coords_flat[0][mask], coords_flat[1][mask]),
    data=cba_flat[mask]
)
trend_grid = trend.predict(coordinates=(lon_2d.flatten(), lat_2d.flatten()))
trend_grid = trend_grid.reshape(cba_ds["CBA"].shape)
residual = cba_ds["CBA"].values - trend_grid
print(f"  Residual range: {np.nanmin(residual):.2f} to {np.nanmax(residual):.2f} mGal")

# ─── 4-panel combined report ─────────────────────────────────────────────────
print("\nPlotting 4-panel combined report...")

# DEM data
dem_lon = dem.x.values
dem_lat = dem.y.values
dem_data = dem.values

# Colour limits
res_vmin, res_vmax = sym_vlim(residual)
dem_vmin, dem_vmax = np.nanpercentile(dem_data, [2, 98])

try:
    fig = plt.figure(figsize=(18, 14))
    proj = ccrs.PlateCarree()

    panel_labels = ["(a)", "(b)", "(c)", "(d)"]
    titles = [
        "Topography / Bathymetry (m)",
        "Free Air Anomaly (mGal)",
        "Complete Bouguer Anomaly (mGal)",
        "Residual Anomaly (CBA − Regional Trend, mGal)",
    ]

    axes = []
    for i in range(4):
        ax = fig.add_subplot(2, 2, i + 1, projection=proj)
        axes.append(ax)

    # ── Panel (a): DEM ────────────────────────────────────────────────────────────
    ax = axes[0]
    ax.set_extent(extent, crs=proj)
    dem_lon_2d, dem_lat_2d = np.meshgrid(dem_lon, dem_lat)
    pcm_dem = ax.pcolormesh(
        dem_lon_2d, dem_lat_2d, dem_data,
        cmap="terrain",
        vmin=dem_vmin, vmax=dem_vmax,
        transform=proj,
        shading="auto"
    )
    cbar_dem = plt.colorbar(pcm_dem, ax=ax, orientation="vertical", pad=0.02, shrink=0.85)
    cbar_dem.set_label("m", fontsize=9)
    add_coastlines(ax)
    add_gridlines(ax)
    ax.set_title(f"{panel_labels[0]} {titles[0]}", fontsize=11, fontweight="bold")

    # ── Panel (b): FAA ────────────────────────────────────────────────────────────
    ax = axes[1]
    ax.set_extent(extent, crs=proj)
    pcm_faa = ax.pcolormesh(
        lon_2d, lat_2d, faa_values,
        cmap="RdBu_r",
        vmin=faa_vmin, vmax=faa_vmax,
        transform=proj,
        shading="auto"
    )
    cbar_faa = plt.colorbar(pcm_faa, ax=ax, orientation="vertical", pad=0.02, shrink=0.85)
    cbar_faa.set_label("mGal", fontsize=9)
    add_coastlines(ax)
    add_gridlines(ax)
    ax.set_title(f"{panel_labels[1]} {titles[1]}", fontsize=11, fontweight="bold")

    # ── Panel (c): CBA ────────────────────────────────────────────────────────────
    ax = axes[2]
    ax.set_extent(extent, crs=proj)
    pcm_cba = ax.pcolormesh(
        lon_2d, lat_2d, cba_values,
        cmap="RdBu_r",
        vmin=cba_vmin, vmax=cba_vmax,
        transform=proj,
        shading="auto"
    )
    cbar_cba = plt.colorbar(pcm_cba, ax=ax, orientation="vertical", pad=0.02, shrink=0.85)
    cbar_cba.set_label("mGal", fontsize=9)
    add_coastlines(ax)
    add_gridlines(ax)
    ax.set_title(f"{panel_labels[2]} {titles[2]}", fontsize=11, fontweight="bold")

    # ── Panel (d): Residual ───────────────────────────────────────────────────────
    ax = axes[3]
    ax.set_extent(extent, crs=proj)
    pcm_res = ax.pcolormesh(
        lon_2d, lat_2d, residual,
        cmap="RdBu_r",
        vmin=res_vmin, vmax=res_vmax,
        transform=proj,
        shading="auto"
    )
    cbar_res = plt.colorbar(pcm_res, ax=ax, orientation="vertical", pad=0.02, shrink=0.85)
    cbar_res.set_label("mGal", fontsize=9)
    add_coastlines(ax)
    add_gridlines(ax)
    ax.set_title(f"{panel_labels[3]} {titles[3]}", fontsize=11, fontweight="bold")

    plt.suptitle(
        "Airborne Gravity Survey — Central Sulawesi, Indonesia",
        fontsize=14, fontweight="bold", y=0.98
    )
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(OUT_COMBINED, dpi=300, bbox_inches="tight")
    print(f"  Saved: {OUT_COMBINED}")
finally:
    plt.close("all")

# ─── Verify outputs ──────────────────────────────────────────────────────────
print("\n=== Output verification ===")
all_ok = True
for fpath in [OUT_FAA, OUT_CBA, OUT_COMBINED]:
    if os.path.exists(fpath):
        size_kb = os.path.getsize(fpath) / 1e3
        print(f"  OK  {os.path.basename(fpath)} ({size_kb:.1f} KB)")
    else:
        print(f"  MISSING  {os.path.basename(fpath)}")
        all_ok = False

if all_ok:
    print("\nStep 6 complete — all output maps produced successfully.")
else:
    print("\nStep 6 FAILED — some outputs are missing.")
    sys.exit(1)
