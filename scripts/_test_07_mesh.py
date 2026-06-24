import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import xarray as xr
import discretize

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CBA_NC = os.path.join(PROJECT_ROOT, "output", "cba_grid.nc")

# -- Load CBA -----------------------------------------------------------------
ds = xr.open_dataset(CBA_NC)
easting_1d  = ds.easting.values   # (190,)
northing_1d = ds.northing.values  # (122,)
cba_2d      = ds["CBA"].values    # (122, 190)

east_2d, north_2d = np.meshgrid(easting_1d, northing_1d)
height_2d = np.full_like(east_2d, 2600.0)

# Flatten
rx_locs_full = np.c_[east_2d.ravel(), north_2d.ravel(), height_2d.ravel()]
cba_full     = cba_2d.ravel()

# -- Subsample every 3rd point ------------------------------------------------
idx_row = np.arange(0, 122, 3)
idx_col = np.arange(0, 190, 3)
row_2d, col_2d = np.meshgrid(idx_row, idx_col, indexing="ij")
flat_idx = (row_2d * 190 + col_2d).ravel()

rx_locs_sub = rx_locs_full[flat_idx]
dobs        = cba_full[flat_idx]

# -- Build TensorMesh ---------------------------------------------------------
e_min, e_max = easting_1d.min()  - 4000, easting_1d.max()  + 4000
n_min, n_max = northing_1d.min() - 4000, northing_1d.max() + 4000
z_bottom, z_top = -25_000, 0

hx = np.full(int(np.ceil((e_max - e_min) / 4000)), 4000.0)
hy = np.full(int(np.ceil((n_max - n_min) / 4000)), 4000.0)
hz = np.r_[
    500  * np.ones(4),   # 0-2 km
    1000 * np.ones(3),   # 2-5 km
    1000 * np.ones(5),   # 5-10 km
    1154 * np.ones(13),  # 10-25 km  (1154x13 approx 15,000 m)
]  # defined bottom->top (z-up), total = 25,002 m approx 25 km

origin = np.array([e_min, n_min, z_bottom])
mesh   = discretize.TensorMesh([hx, hy, hz], origin=origin)

# -- Assertions ---------------------------------------------------------------
assert mesh.n_cells > 100_000, f"Too few cells: {mesh.n_cells}"
assert mesh.n_cells < 300_000, f"Too many cells: {mesh.n_cells}"
assert not np.any(np.isnan(dobs)), "NaN in subsampled dobs"
assert rx_locs_sub.shape[1] == 3, "rx_locs_sub must have 3 columns"
assert len(dobs) == len(rx_locs_sub), "dobs length mismatch"
# All observation points must be inside mesh XY extent
assert np.all(rx_locs_sub[:, 0] >= mesh.origin[0])
assert np.all(rx_locs_sub[:, 0] <= mesh.origin[0] + mesh.h[0].sum())
assert np.all(rx_locs_sub[:, 1] >= mesh.origin[1])
assert np.all(rx_locs_sub[:, 1] <= mesh.origin[1] + mesh.h[1].sum())

print(f"mesh.n_cells = {mesh.n_cells:,}")
print(f"Subsampled data points: {len(dobs):,}")
print(f"Full data points: {len(cba_full):,}")
print("PASS: mesh and data checks OK")
