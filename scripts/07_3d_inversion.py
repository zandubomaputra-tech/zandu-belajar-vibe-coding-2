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
DENSITY_LB_GCC = DENSITY_LB / 1000.0   # -0.5 g/cc — SimPEG gravity expects density in g/cc
DENSITY_UB_GCC = DENSITY_UB / 1000.0   # +1.5 g/cc — SimPEG gravity expects density in g/cc
OBS_HEIGHT     = 2600.0    # m -- prediction height from Step 5
MOHO_DEPTH     = 25_000.0  # m -- Surono & Hartono 2013
SUBSAMPLE_STEP = 4         # every Nth row/col for inversion data (increased from 3 due to MemoryError at 3)

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

# -- [5] Setup SimPEG gravity simulation ───────────────────────────────────────
print("\n[5] Setting up SimPEG gravity simulation ...")

# API notes (SimPEG 0.25.2):
#   - InjectActiveCells(mesh, active_cells, value_inactive) -- positional
#   - Simulation3DIntegral accepts active_cells= kwarg (ind_active removed in v0.24)
#   - Density model must be in g/cc (NOT kg/m3); 1 g/cc = 1000 kg/m3
#   - gz is the UPWARD component (z-up right-hand system):
#       positive density below receiver  --> negative gz
#       observed CBA (downward-positive) --> dobs = -CBA_mGal for SimPEG
actmap = maps.InjectActiveCells(mesh, active_cells, 0.0)

# Subsampled receivers for inversion
rxList_sub   = [grav_sim.Point(rx_locs_sub, components=["gz"])]
srcField_sub = grav_sim.SourceField(receiver_list=rxList_sub)
survey_sub   = grav_sim.Survey(srcField_sub)

simulation = grav_sim.Simulation3DIntegral(
    mesh,
    survey=survey_sub,
    rhoMap=actmap,
    active_cells=active_cells,
    store_sensitivities="ram",
)
print(f"    Simulation ready: {len(dobs):,} data points x {nC:,} active cells")

# Full-grid simulation for prediction after inversion
rxList_full   = [grav_sim.Point(rx_locs_full, components=["gz"])]
srcField_full = grav_sim.SourceField(receiver_list=rxList_full)
survey_full   = grav_sim.Survey(srcField_full)

simulation_full = grav_sim.Simulation3DIntegral(
    mesh,
    survey=survey_full,
    rhoMap=actmap,
    active_cells=active_cells,
    store_sensitivities="forward_only",
)
print(f"    Full-grid simulation ready: {len(cba_full):,} points")

# -- [6] Data object ───────────────────────────────────────────────────────────
print("\n[6] Creating data object ...")

# Sign convention adaptation:
# CBA observed data is downward-positive mGal; SimPEG gz is upward-positive.
# Negate CBA so that dobs matches SimPEG's gz convention (dense body -> negative gz).
dobs_simpeg     = -dobs           # negate: CBA(+) -> gz(-) for SimPEG
noise_floor_arr = np.full(len(dobs_simpeg), NOISE_FLOOR)
data_object     = simpeg.data.Data(
    survey_sub,
    dobs=dobs_simpeg,
    noise_floor=noise_floor_arr,
)
print(f"    Data range (SimPEG gz): {dobs_simpeg.min():.2f} to {dobs_simpeg.max():.2f} mGal")
print(f"    Noise floor: {NOISE_FLOOR} mGal")

# ── [7] Define inversion components ──────────────────────────────────────────
print("\n[7] Setting up inversion components ...")

# Data misfit: use data_object directly (already holds negated CBA as gz)
# Convention: dobs_simpeg = -CBA, so L2DataMisfit compares simulation.gz to -CBA
dmis = data_misfit.L2DataMisfit(data=data_object, simulation=simulation)

# Regularization: WeightedLeastSquares (API-checked for SimPEG 0.25.2)
# Param names confirmed: active_cells=, reference_model=, alpha_s=, alpha_x/y/z=
reg = regularization.WeightedLeastSquares(
    mesh,
    active_cells=active_cells,
    alpha_s=1e-4,
    alpha_x=1.0,
    alpha_y=1.0,
    alpha_z=1.0,
    reference_model=np.zeros(nC),
)

# Optimizer: ProjectedGNCG enforces g/cc bounds via projected gradient.
# Bounds in g/cc (DENSITY_LB_GCC=-0.5, DENSITY_UB_GCC=+1.5) — NOT kg/m3.
# API-checked: ProjectedGNCG(lower=, upper=, cg_maxiter=, maxIter= via **kwargs)
opt = optimization.ProjectedGNCG(
    maxIter=20,
    lower=DENSITY_LB_GCC,
    upper=DENSITY_UB_GCC,
    cg_maxiter=20,
)
print(f"    Optimizer: ProjectedGNCG (bounds enforced)")
print(f"    Bounds: [{DENSITY_LB_GCC}, {DENSITY_UB_GCC}] g/cc  "
      f"= [{DENSITY_LB:.0f}, {DENSITY_UB:.0f}] kg/m3")

inv_prob = inverse_problem.BaseInvProblem(dmis, reg, opt)

# Standard SimPEG potential-field L2 directive stack (verified against SimPEG 0.25.2)
# API adaptations vs task spec:
#   - every_iteration=False confirmed correct param name for UpdateSensitivityWeights
#   - UpdatePreconditioner has no required init params (update_every_iteration is optional)
#   - SaveOutputEveryIteration: task spec says save_txt=False -> maps internally to on_disk=False
#   - beta0_ratio=1.0 (less aggressive start than previous 10.0 -> allows model to fit)
#   - coolingFactor=2, coolingRate=1 (reduce beta every iteration -> faster model growth)
sensitivity_weights = directives.UpdateSensitivityWeights(every_iteration=False)
starting_beta       = directives.BetaEstimate_ByEig(beta0_ratio=1.0)
beta_schedule       = directives.BetaSchedule(coolingFactor=2, coolingRate=1)
update_jacobi       = directives.UpdatePreconditioner()
target_misfit       = directives.TargetMisfit(chifact=1.0)
save_output         = directives.SaveOutputEveryIteration(save_txt=False)

# ORDER: sensitivity weights first, then beta estimate, schedule, save, preconditioner, target
directives_list = [
    sensitivity_weights,
    starting_beta,
    beta_schedule,
    save_output,
    update_jacobi,
    target_misfit,
]

inv = inversion.BaseInversion(inv_prob, directiveList=directives_list)

print("    Inversion configured (depth-weighted directive stack).")

# ── [8] Run inversion ─────────────────────────────────────────────────────────
print("\n[8] Running inversion (this may take 10-60 min) ...")
print(f"    SUBSAMPLE_STEP = {SUBSAMPLE_STEP}")
print(f"    Inversion data points: {len(dobs):,}")
print(f"    Active cells: {nC:,}")

# Starting model: zero density contrast everywhere (g/cc)
m0 = np.zeros(nC)
recovered_model_gcc = inv.run(m0)

# Convert recovered model from g/cc to kg/m3 for reporting
recovered_model_kgm3 = recovered_model_gcc * 1000.0
print(f"\n    Recovered model range (g/cc): {recovered_model_gcc.min():.4f} to {recovered_model_gcc.max():.4f} g/cc")
print(f"    Recovered model range (kg/m3): {recovered_model_kgm3.min():.2f} to {recovered_model_kgm3.max():.2f} kg/m3")
print(f"    Mean density contrast: {recovered_model_kgm3.mean():.4f} kg/m3")

# ── [9] Save density model in kg/m3 ──────────────────────────────────────────
# Spec: 07_density_model.npy must be in kg/m3
np.save(OUT_MODEL_NPY, recovered_model_kgm3)
print(f"\n[9] Saved density model (kg/m3): {OUT_MODEL_NPY}")
print(f"    Shape: {recovered_model_kgm3.shape}")

# ── [10] Predict full-grid CBA + save ─────────────────────────────────────────
print("\n[10] Predicting CBA on full grid ...")
# Forward prediction uses g/cc model (SimPEG internal unit)
pred_full_gz = simulation_full.dpred(recovered_model_gcc)
# Negate gz back to CBA convention (downward-positive, observed CBA sign)
pred_cba_2d  = (-pred_full_gz).reshape(len(northing_1d), len(easting_1d))
print(f"    Predicted CBA range: {pred_cba_2d.min():.2f} to {pred_cba_2d.max():.2f} mGal")

# Save predicted CBA as NetCDF
ds_pred = xr.Dataset(
    {"CBA_predicted": (["northing", "easting"], pred_cba_2d)},
    coords={"northing": northing_1d, "easting": easting_1d},
)
ds_pred["CBA_predicted"].attrs = {
    "units": "mGal",
    "long_name": "Predicted CBA from 3D Tikhonov inversion",
    "sign_convention": "downward-positive (same as observed CBA)",
}
ds_pred.to_netcdf(OUT_PRED_NC)
print(f"    Saved predicted CBA: {OUT_PRED_NC}")

# ── Misfit stats + geology sanity check ───────────────────────────────────────
cba_obs_2d = cba_full.reshape(len(northing_1d), len(easting_1d))
misfit_arr = cba_obs_2d - pred_cba_2d
rmse_full  = float(np.sqrt(np.nanmean(misfit_arr**2)))

print(f"\n=== Inversion Results ===")
print(f"    Full-grid RMSE (obs - pred): {rmse_full:.4f} mGal")
print(f"    Target: <5 mGal (Pastore 2016 benchmark)")

# Geology sanity check: positive recovered density should coincide with positive CBA
# Dense body (positive density contrast) -> positive Bouguer anomaly
# Build 3D density volume and check 2D signature at surface layer
density_3d = recovered_model_kgm3.reshape(mesh.shape_cells, order="F")
# Max density projection onto surface (top z-layer = last index in z for F-order)
density_surface_max = density_3d[:, :, -1].T  # shape: (ny, nx)

# Resize to match CBA grid if needed
cba_flat_test  = cba_obs_2d.ravel()
# Use flattened full density max-projection resampled to grid
nx_mesh = mesh.shape_cells[0]
ny_mesh = mesh.shape_cells[1]
# Coarse check: correlate sign of max density (top-layer) with CBA grid sign
# Resample CBA grid to mesh XY resolution for sign check
from scipy.interpolate import RegularGridInterpolator
interp_cba = RegularGridInterpolator(
    (northing_1d, easting_1d), cba_obs_2d,
    method='linear', bounds_error=False, fill_value=np.nan
)
mesh_centers_x = mesh.cell_centers[:, 0].reshape(mesh.shape_cells, order='F')[:, :, -1].ravel()  # top layer x
mesh_centers_y = mesh.cell_centers[:, 1].reshape(mesh.shape_cells, order='F')[:, :, -1].ravel()  # top layer y
pts = np.c_[mesh_centers_y, mesh_centers_x]  # (northing, easting)
cba_at_mesh     = interp_cba(pts)
density_top     = density_3d[:, :, -1].ravel(order='F')   # top layer, all xy cells

valid = ~np.isnan(cba_at_mesh)
if valid.sum() > 10:
    # Pearson correlation between top-layer density and CBA sign
    corr = float(np.corrcoef(density_top[valid], cba_at_mesh[valid])[0, 1])
    pos_density_pos_cba = float(np.mean(
        (density_top[valid] > 0) == (cba_at_mesh[valid] > 0)
    ))
    print(f"\n=== Geology Sanity Check ===")
    print(f"    Pearson corr (top-layer density vs observed CBA): {corr:.4f}")
    print(f"    % cells where sign(density) == sign(CBA): {pos_density_pos_cba*100:.1f}%")
    if corr > 0.3 and pos_density_pos_cba > 0.55:
        print("    PASS: Positive density correlates with positive CBA — sign chain correct.")
    elif corr > 0:
        print("    MARGINAL: Weak positive correlation — review sign chain if RMSE is poor.")
    else:
        print("    WARN: Negative correlation — possible sign chain issue!")
else:
    print("\n    Sanity check skipped (insufficient overlap between mesh and CBA grid).")

print("\n=== Step 7 Complete ===")
print(f"    Density model : {OUT_MODEL_NPY}")
print(f"    Predicted CBA : {OUT_PRED_NC}")
print(f"    Mesh params   : {OUT_MESH_JSON}")
