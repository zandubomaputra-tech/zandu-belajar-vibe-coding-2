"""
Step 7: 3D Gravity Inversion — East Sulawesi Ophiolite (ESO)
=============================================================
Input  : output/cba_grid.nc
Output : output/07_density_model.npy
         output/07_mesh_params.json
         output/07_predicted_cba.nc
         output/07_misfit_map.png
         output/07_crosssections.png
"""

import matplotlib
matplotlib.use("Agg")

import os, sys, json, gc
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pyproj import Transformer
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import discretize
import simpeg
from simpeg import (maps, data_misfit, regularization,
                    optimization, inverse_problem, directives, inversion)
from simpeg.potential_fields import gravity as grav_sim

# -- Paths ---------------------------------------------------------------------
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR   = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CBA_NC         = os.path.join(OUTPUT_DIR, "cba_grid.nc")
OUT_MODEL_NPY  = os.path.join(OUTPUT_DIR, "07_density_model.npy")
OUT_MESH_JSON  = os.path.join(OUTPUT_DIR, "07_mesh_params.json")
OUT_PRED_NC    = os.path.join(OUTPUT_DIR, "07_predicted_cba.nc")
OUT_MISFIT_PNG = os.path.join(OUTPUT_DIR, "07_misfit_map.png")
OUT_XSEC_PNG   = os.path.join(OUTPUT_DIR, "07_crosssections.png")

# -- Constants -----------------------------------------------------------------
RHO_BACKGROUND = 2670.0    # kg/m3 background crust
NOISE_FLOOR    = 42.8      # mGal (TOPEX RMSE from Step 5.5)
DENSITY_LB     = -500.0    # kg/m3 lower bound density contrast
DENSITY_UB     = 1500.0    # kg/m3 upper bound density contrast
OBS_HEIGHT     = 2600.0    # m -- prediction height from Step 5
MOHO_DEPTH     = 25_000.0  # m -- Surono & Hartono 2013
SUBSAMPLE_STEP = 3         # every Nth row/col for inversion data

print("=" * 65)
print("STEP 7: 3D GRAVITY INVERSION -- ESO")
print("=" * 65)

# -- [1] Load CBA grid ---------------------------------------------------------
print("\n[1] Loading CBA grid ...")
ds = xr.open_dataset(CBA_NC)
if ds.northing.values[0] > ds.northing.values[-1]:
    ds = ds.isel(northing=slice(None, None, -1))

easting_1d  = ds.easting.values    # (190,)
northing_1d = ds.northing.values   # (122,)
cba_2d      = ds["CBA"].values     # (122, 190)

east_2d, north_2d = np.meshgrid(easting_1d, northing_1d)
rx_locs_full = np.c_[
    east_2d.ravel(),
    north_2d.ravel(),
    np.full(east_2d.size, OBS_HEIGHT)
]
cba_full = cba_2d.ravel()
print(f"    Full grid: {len(cba_full):,} points")

# -- [2] Subsample for inversion -----------------------------------------------
print(f"\n[2] Subsampling every {SUBSAMPLE_STEP}rd point ...")
idx_r = np.arange(0, len(northing_1d), SUBSAMPLE_STEP)
idx_c = np.arange(0, len(easting_1d),  SUBSAMPLE_STEP)
rr, cc = np.meshgrid(idx_r, idx_c, indexing="ij")
flat_idx    = (rr * len(easting_1d) + cc).ravel()
rx_locs_sub = rx_locs_full[flat_idx]
dobs        = cba_full[flat_idx].copy()
print(f"    Inversion data points: {len(dobs):,}")

# -- [3] Build TensorMesh ------------------------------------------------------
print("\n[3] Building TensorMesh ...")
pad = 4000.0
e_min = easting_1d.min()  - pad;  e_max = easting_1d.max()  + pad
n_min = northing_1d.min() - pad;  n_max = northing_1d.max() + pad
z_bot = -MOHO_DEPTH

hx = np.full(int(np.ceil((e_max - e_min) / 4000)), 4000.0)
hy = np.full(int(np.ceil((n_max - n_min) / 4000)), 4000.0)
hz = np.r_[
    500  * np.ones(4),    # 0-2 km
    1000 * np.ones(3),    # 2-5 km
    1000 * np.ones(5),    # 5-10 km
    1154 * np.ones(13),   # 10-25 km
]

origin = np.array([e_min, n_min, z_bot])
mesh   = discretize.TensorMesh([hx, hy, hz], origin=origin)
print(f"    Mesh shape  : {mesh.shape_cells}")
print(f"    Total cells : {mesh.n_cells:,}")
print(f"    Mesh bounds E: {mesh.origin[0]:.0f} -- {mesh.origin[0]+mesh.h[0].sum():.0f} m")
print(f"    Mesh bounds N: {mesh.origin[1]:.0f} -- {mesh.origin[1]+mesh.h[1].sum():.0f} m")
print(f"    Mesh bounds Z: {mesh.origin[2]:.0f} -- {mesh.origin[2]+mesh.h[2].sum():.0f} m")

# Active cells: all cells (whole mesh is the model domain)
active_cells = np.ones(mesh.n_cells, dtype=bool)
nC = int(active_cells.sum())

# -- [4] Save mesh params ------------------------------------------------------
mesh_params = {
    "hx": hx.tolist(),
    "hy": hy.tolist(),
    "hz": hz.tolist(),
    "origin": origin.tolist(),
    "n_cells": int(mesh.n_cells),
    "shape_cells": list(mesh.shape_cells),
}
with open(OUT_MESH_JSON, "w") as f:
    json.dump(mesh_params, f, indent=2)
print(f"\n[4] Saved mesh params: {OUT_MESH_JSON}")
