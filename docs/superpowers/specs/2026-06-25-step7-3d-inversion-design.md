# Step 7: 3D Gravity Inversion — East Sulawesi Ophiolite (ESO)
**Date:** 2026-06-25
**Project:** Tugas Akhir — Airborne Gravity Processing Pipeline, Universitas Pertamina
**Author:** Zandu (Teknik Geofisika)

---

## 1. Objective

Recover the 3D subsurface density contrast distribution beneath the full airborne survey area using SimPEG gravity inversion, with the goal of identifying the geometry and depth extent of the East Sulawesi Ophiolite (ESO).

This step follows the **Pastore et al. 2016 (GJI) methodology framework** — forward/inverse modelling with dual-density scenarios and sensitivity analysis — applied with Sulawesi-local density values from Surono & Hartono 2013 and Kadarusman 2004. Pastore's Norway density values are NOT used.

---

## 2. Inputs

| File | Description |
|------|-------------|
| `output/cba_grid.nc` | Complete Bouguer Anomaly, 122×190 grid, 2km spacing, UTM Zone 51S |
| `output/dem_clipped_utm.tif` | BATNAS DEM, UTM Zone 51S — for surface topography |
| `topex120124_0-3.csv` | TOPEX satellite FAA — used as **independent validation only**, not inversion constraint |

---

## 3. Outputs

| File | Description |
|------|-------------|
| `output/07_density_model.npy` | 3D density contrast array (nCells,), kg/m³ |
| `output/07_mesh_params.json` | TensorMesh parameters (cell sizes, origin) for reconstruction |
| `output/07_predicted_cba.nc` | Predicted CBA grid from recovered model |
| `output/07_misfit_map.png` | Observed vs Predicted vs Misfit 3-panel map |
| `output/07_crosssections.png` | 12 N-S cross-sections (density + observed CBA profile) |
| `output/07_3d_viewer.html` | Standalone interactive 3D HTML viewer (PyVista export) |
| `notebooks/07_interactive_viewer.ipynb` | Full interactive Jupyter Notebook |

---

## 4. Architecture

Two deliverables:

### 4a. `scripts/07_3d_inversion.py`
Main inversion script — runs headless, saves all outputs to disk.

**Steps:**
1. Load CBA grid → extract observation coordinates and data
2. Build TensorMesh (full survey area)
3. Setup SimPEG gravity simulation (`simpeg.potential_fields.gravity.Simulation3DIntegral`)
4. Define data misfit + regularization + optimization
5. Run inversion (Tikhonov L2, beta cooling)
6. Save density model, mesh params, predicted CBA
7. Generate misfit map figure
8. Generate 12 N-S cross-section figures

### 4b. `notebooks/07_interactive_viewer.ipynb`
Interactive viewer — loads from disk, no recomputation.

**Cells:**
1. Load density model + mesh + CBA grids
2. 3D volume viewer (PyVista, exported to HTML)
3. Cross-section explorer (ipywidgets easting slider, 12 sections)
4. Observed vs Predicted map (ipywidgets toggle for TOPEX overlay)
5. Misfit statistics table + sensitivity summary

---

## 5. Mesh Design

**Domain:** Full survey area, UTM Zone 51S (EPSG:32751)
- Easting:  250,158 – 627,336 m (~377 km)
- Northing: 9,762,776 – 10,005,344 m (~243 km)
- Depth:    0 – 25,000 m (Moho per Surono & Hartono 2013)

**Cell sizes:**
- Horizontal: 4,000 m × 4,000 m → ~94 × 61 = 5,734 surface cells
- Vertical (25 layers, variable):
  - 0–2 km: 4 layers × 500 m
  - 2–5 km: 3 layers × 1,000 m
  - 5–10 km: 5 layers × 1,000 m
  - 10–25 km: 13 layers × ~1,154 m (uniform)
- **Total cells: ~143,350**

---

## 6. Inversion Setup

**Model parameter:** Density contrast Δρ (kg/m³) relative to background crust (2,670 kg/m³)

**Bounds:**
- Lower: −500 kg/m³ (sediment / water-saturated rock)
- Upper: +1,500 kg/m³ (fresh peridotite relative to background)

**Reference model:** 0 (uniform, no anomaly)

**Data uncertainty:** 42.8 mGal (RMSE from TOPEX validation, Step 5.5) — used as noise floor

**Regularization:** Tikhonov L2
- `Smallness` (alpha_s): penalizes deviation from reference model
- `SmoothnessFirstOrder` x, y, z (alpha_x, alpha_y, alpha_z): spatial smoothness
- Beta cooling: start_beta=1e4, cooling_factor=0.3, cooling_rate=2, n_iter=10

**Optimizer:** `InexactGaussNewton` (SimPEG default for gravity)

---

## 7. Density Framework

From Sulawesi-local sources only (per CLAUDE.md):

| Rock type | Density (kg/m³) | Δρ from background | Source |
|-----------|-----------------|---------------------|--------|
| Background crust | 2,670 | 0 | Standard |
| Sediment | 2,370 | −300 | Surono & Hartono 2013 |
| ESO — serpentinized (low) | 2,700–2,900 | +30 to +230 | Kadarusman 2004 + global lit. |
| ESO — reference | 2,970 | +300 | Surono & Hartono 2013 (PSG official) |
| ESO — fresh peridotite (high) | 3,100–3,300 | +430 to +630 | Kadarusman 2004 modal estimate |

Expected ESO geometry: thin sheet (~500 m or less), NOT deep-rooted funnel (per Surono & Hartono 2013 regional gravity 0–30 mGal evidence).

---

## 8. Cross-Sections

12 N-S cross-sections at evenly spaced eastings across the survey area:
- Spacing: ~(627,336 − 250,158) / 13 ≈ 29,014 m (~29 km apart)
- Each section: depth (0–25 km) vs northing, colored by Δρ
- Overlay: observed CBA profile along section
- Moho line at 25 km depth
- Layout: 4 rows × 3 columns figure

---

## 9. Interactive Notebook Features

| Cell | Feature | Tool |
|------|---------|------|
| 2 | 3D volume render, clip planes | PyVista + `trame` or HTML export |
| 3 | Cross-section selector | ipywidgets `IntSlider` (0–11) |
| 4 | Obs/Pred map, TOPEX toggle | ipywidgets `Checkbox` + matplotlib |
| 5 | RMSE, Pearson r, misfit table | pandas + markdown display |

---

## 10. Limitations (to state in manuscript)

1. **Non-uniqueness:** Gravity inversion is inherently non-unique. Many density distributions can fit the same data. Results are regularization-dependent.
2. **No seismic constraint:** Unlike Pastore 2016 (which used seismic refraction for depth control), this study relies on gravity + surface geology + CRUST1.0 Moho only.
3. **Mesh resolution:** 4km horizontal cells are coarser than the 2km CBA grid — fine-scale features smaller than ~8km may not be resolved.
4. **ESO geometry assumption:** Thin sheet expectation from regional gravity evidence (Surono & Hartono 2013) is used as a geological guide, not a hard model constraint.

---

## 11. Dependencies

New packages to install:
- `simpeg` (gravity inversion)
- `discretize` (TensorMesh)
- `pyvista` (3D visualization)
- `ipywidgets` (interactive notebook)
- `trame` or `pyvista[jupyter]` (PyVista in Jupyter)
