"""
Step 7 Figures: Load inversion outputs from disk and generate result figures.
==============================================================================
This standalone script regenerates figures WITHOUT re-running the 40-min inversion.

Inputs  (all already on disk):
  output/07_density_model.npy   -- recovered density contrast, shape (152775,) in kg/m3
  output/07_mesh_params.json    -- TensorMesh rebuild params
  output/07_predicted_cba.nc   -- CBA_predicted (northing, easting)
  output/cba_grid.nc            -- CBA observed (northing, easting)

Outputs:
  output/07_misfit_map.png      -- 3-panel: Observed | Predicted | Misfit
  output/07_crosssections.png   -- 12 N-S cross-sections (4x3)
"""

import matplotlib
matplotlib.use("Agg")

import os, sys, json
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pyproj import Transformer
from scipy.interpolate import RegularGridInterpolator
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import discretize

# -- Paths ---------------------------------------------------------------------
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR   = os.path.join(PROJECT_ROOT, "output")

CBA_NC        = os.path.join(OUTPUT_DIR, "cba_grid.nc")
MODEL_NPY     = os.path.join(OUTPUT_DIR, "07_density_model.npy")
MESH_JSON     = os.path.join(OUTPUT_DIR, "07_mesh_params.json")
PRED_NC       = os.path.join(OUTPUT_DIR, "07_predicted_cba.nc")
OUT_MISFIT    = os.path.join(OUTPUT_DIR, "07_misfit_map.png")
OUT_XSEC      = os.path.join(OUTPUT_DIR, "07_crosssections.png")

MOHO_DEPTH_KM = 25.0   # Surono & Hartono 2013

print("=" * 65)
print("STEP 7 FIGURES -- standalone loader")
print("=" * 65)

# -- [1] Load inversion outputs -----------------------------------------------
print("\n[1] Loading inversion outputs ...")

recovered_model_kgm3 = np.load(MODEL_NPY)
print(f"    density model shape : {recovered_model_kgm3.shape}")
print(f"    density range       : {recovered_model_kgm3.min():.2f} to {recovered_model_kgm3.max():.2f} kg/m3")

with open(MESH_JSON) as f:
    p = json.load(f)
mesh = discretize.TensorMesh(
    [np.array(p["hx"]), np.array(p["hy"]), np.array(p["hz"])],
    origin=np.array(p["origin"])
)
print(f"    mesh.shape_cells    : {mesh.shape_cells}")
print(f"    mesh.nC             : {mesh.nC}")

# -- [2] Load CBA grids -------------------------------------------------------
print("\n[2] Loading CBA grids ...")

ds_obs  = xr.open_dataset(CBA_NC)
ds_pred = xr.open_dataset(PRED_NC)

northing_1d = ds_obs.northing.values
easting_1d  = ds_obs.easting.values

# Apply northing-ascending flip if needed (for both datasets consistently)
if northing_1d[0] > northing_1d[-1]:
    print("    Flipping northing to ascending order ...")
    northing_1d = northing_1d[::-1]
    cba_obs_2d  = ds_obs["CBA"].values[::-1, :]
    cba_pred_2d = ds_pred["CBA_predicted"].values[::-1, :]
else:
    cba_obs_2d  = ds_obs["CBA"].values
    cba_pred_2d = ds_pred["CBA_predicted"].values

print(f"    northing: {northing_1d[0]:.0f} .. {northing_1d[-1]:.0f}  (n={len(northing_1d)})")
print(f"    easting : {easting_1d[0]:.0f} .. {easting_1d[-1]:.0f}  (n={len(easting_1d)})")
print(f"    CBA obs  range: {np.nanmin(cba_obs_2d):.2f} to {np.nanmax(cba_obs_2d):.2f} mGal")
print(f"    CBA pred range: {np.nanmin(cba_pred_2d):.2f} to {np.nanmax(cba_pred_2d):.2f} mGal")

# -- [3] Compute misfit -------------------------------------------------------
misfit_arr = cba_obs_2d - cba_pred_2d
rmse_full  = np.sqrt(np.nanmean(misfit_arr**2))
print(f"\n[3] Misfit statistics:")
print(f"    RMSE (full grid)    : {rmse_full:.2f} mGal")
print(f"    Misfit range        : {np.nanmin(misfit_arr):.2f} to {np.nanmax(misfit_arr):.2f} mGal")

# -- [4] UTM -> lonlat for cartopy maps ---------------------------------------
transformer = Transformer.from_crs("EPSG:32751", "EPSG:4326", always_xy=True)
east_2d_g, north_2d_g = np.meshgrid(easting_1d, northing_1d)
lon_flat, lat_flat = transformer.transform(east_2d_g.ravel(), north_2d_g.ravel())
lon_2d = lon_flat.reshape(east_2d_g.shape)
lat_2d = lat_flat.reshape(east_2d_g.shape)
lon_min, lon_max = lon_2d.min(), lon_2d.max()
lat_min, lat_max = lat_2d.min(), lat_2d.max()
extent = [lon_min - 0.1, lon_max + 0.1, lat_min - 0.1, lat_max + 0.1]

# -- [5] Misfit map (3-panel) -------------------------------------------------
print("\n[5] Generating misfit map ...")

def sym_vlim(arr, pct=2):
    """Symmetric colour limits from percentile."""
    lo = np.nanpercentile(arr, pct)
    hi = np.nanpercentile(arr, 100 - pct)
    lim = max(abs(lo), abs(hi))
    return -lim, lim

obs_vmin, obs_vmax   = sym_vlim(cba_obs_2d)
mis_vmin, mis_vmax   = sym_vlim(misfit_arr)

try:
    fig, axes = plt.subplots(1, 3, figsize=(20, 7),
                             subplot_kw={"projection": ccrs.PlateCarree()})
    panels = [
        (cba_obs_2d,  "RdBu_r",  obs_vmin, obs_vmax, "Observed CBA (mGal)"),
        (cba_pred_2d, "RdBu_r",  obs_vmin, obs_vmax, "Predicted CBA (mGal)"),
        (misfit_arr,  "coolwarm", mis_vmin, mis_vmax,
         f"Misfit (obs - pred, mGal)  RMSE={rmse_full:.1f}"),
    ]
    for ax, (data, cmap, vmin, vmax, title) in zip(axes, panels):
        ax.set_extent(extent, crs=ccrs.PlateCarree())
        pcm = ax.pcolormesh(
            lon_2d, lat_2d, data,
            cmap=cmap, vmin=vmin, vmax=vmax,
            transform=ccrs.PlateCarree(), shading="auto"
        )
        plt.colorbar(pcm, ax=ax, shrink=0.85, pad=0.02).set_label("mGal", fontsize=9)
        try:
            ax.add_feature(cfeature.NaturalEarthFeature(
                "physical", "coastline", "10m",
                edgecolor="black", facecolor="none", linewidth=0.8
            ))
        except Exception:
            pass
        gl = ax.gridlines(draw_labels=True, linewidth=0.5, color="gray",
                          alpha=0.6, linestyle="--")
        gl.top_labels   = False
        gl.right_labels = False
        ax.set_title(title, fontsize=11, fontweight="bold")
    fig.suptitle(
        "Step 7: 3D Gravity Inversion -- Observed / Predicted / Misfit\n"
        "Central Sulawesi, Indonesia",
        fontsize=13, fontweight="bold"
    )
    plt.tight_layout()
    plt.savefig(OUT_MISFIT, dpi=150, bbox_inches="tight")
    print(f"    Saved: {OUT_MISFIT}")
finally:
    plt.close("all")

# -- [6] Reconstruct 3D density volume ----------------------------------------
print("\n[6] Reconstructing 3D density volume ...")

# Full mesh, active_cells were all True in the inversion => reshape directly
density_3d = recovered_model_kgm3.reshape(mesh.shape_cells, order="F")
# mesh.shape_cells = (nCx, nCy, nCz), x=easting, y=northing, z=up
print(f"    density_3d shape    : {density_3d.shape}  (nx, ny, nz)")

# Mesh cell centers
cc         = mesh.cell_centers
cc_east    = cc[:, 0].reshape(mesh.shape_cells, order="F")[:, 0, 0]   # easting centers
cc_north   = cc[:, 1].reshape(mesh.shape_cells, order="F")[0, :, 0]   # northing centers
cc_depth_z = cc[:, 2].reshape(mesh.shape_cells, order="F")[0, 0, :]   # z (up-positive)
cc_depth   = -cc_depth_z                                                # depth (positive down)

print(f"    easting  range: {cc_east.min()/1e3:.1f} to {cc_east.max()/1e3:.1f} km")
print(f"    northing range: {cc_north.min()/1e3:.1f} to {cc_north.max()/1e3:.1f} km")
print(f"    depth    range: {cc_depth.min()/1e3:.1f} to {cc_depth.max()/1e3:.1f} km (positive-down)")

# -- [7] 12 N-S cross-sections ------------------------------------------------
print("\n[7] Generating 12 N-S cross-sections ...")

# 12 evenly spaced section indices along easting axis
section_easting_indices = np.linspace(0, len(cc_east) - 1, 12, dtype=int)

# CBA interpolator on the observed grid
cba_interp = RegularGridInterpolator(
    (northing_1d, easting_1d), cba_obs_2d,
    method="linear", bounds_error=False, fill_value=np.nan
)

# Density display range: vmin=-200, vmax=460 (model spans -500..+458 kg/m3)
# Using robust range to emphasise the relevant ESO ophiolite signal
DENS_VMIN, DENS_VMAX = -200, 460

fig = plt.figure(figsize=(22, 16))
gs  = gridspec.GridSpec(4, 3, figure=fig, hspace=0.45, wspace=0.40)

for panel_idx, sec_idx in enumerate(section_easting_indices):
    ax       = fig.add_subplot(gs[panel_idx // 3, panel_idx % 3])
    sec_east = cc_east[sec_idx]

    # Density cross-section: shape (nCy, nCz)
    dens_sec = density_3d[sec_idx, :, :]   # (ny, nz)

    pm = ax.pcolormesh(
        cc_north / 1e3, cc_depth / 1e3, dens_sec.T,
        cmap="RdBu_r", vmin=DENS_VMIN, vmax=DENS_VMAX, shading="auto"
    )
    plt.colorbar(pm, ax=ax, shrink=0.6, label="kg/m3", pad=0.02)

    # Moho dashed line
    ax.axhline(y=MOHO_DEPTH_KM, color="black", linewidth=1.5,
               linestyle="--", label=f"Moho ({MOHO_DEPTH_KM:.0f} km)")

    # CBA profile overlay on twin y-axis
    query_north  = cc_north
    query_east   = np.full_like(query_north, sec_east)
    cba_prof     = cba_interp(np.c_[query_north, query_east])
    ax2 = ax.twinx()
    ax2.plot(query_north / 1e3, cba_prof, "k-", linewidth=1.0, alpha=0.8)
    ax2.set_ylabel("CBA (mGal)", fontsize=7, color="black")
    ax2.tick_params(axis="y", labelsize=6)

    ax.set_xlabel("Northing (km)", fontsize=8)
    ax.set_ylabel("Depth (km)", fontsize=8)
    ax.invert_yaxis()
    ax.set_title(
        f"Section {panel_idx + 1}: E={sec_east / 1e3:.0f} km",
        fontsize=9, fontweight="bold"
    )
    ax.tick_params(labelsize=7)

fig.suptitle(
    "Step 7: N-S Cross-Sections -- Density Contrast (kg/m3) & CBA Profile\n"
    "Central Sulawesi, Indonesia  |  vmin=-200 vmax=460 kg/m3",
    fontsize=13, fontweight="bold"
)
plt.savefig(OUT_XSEC, dpi=150, bbox_inches="tight")
plt.close("all")
print(f"    Saved: {OUT_XSEC}")

# -- Summary ------------------------------------------------------------------
misfit_sz = os.path.getsize(OUT_MISFIT)
xsec_sz   = os.path.getsize(OUT_XSEC)

print("\n" + "=" * 65)
print("STEP 7 FIGURES COMPLETE")
print(f"  Misfit map     : {OUT_MISFIT}  ({misfit_sz/1024:.0f} KB)")
print(f"  Cross-sections : {OUT_XSEC}  ({xsec_sz/1024:.0f} KB)")
print(f"  Full RMSE      : {rmse_full:.2f} mGal")
print(f"  Density range  : {recovered_model_kgm3.min():.2f} to {recovered_model_kgm3.max():.2f} kg/m3")
print(f"  Display range  : vmin={DENS_VMIN}  vmax={DENS_VMAX} kg/m3")
print("=" * 65)
