# Airborne Gravity Data Processing Project

## Project Overview
Process airborne gravity data to produce gravity anomaly maps using Python (Harmonica + Fatiando a Terra ecosystem), following workflow concepts from Geosoft's Oasis Montaj.

## Architecture
- **Architect**: Antigravity (Gemini) — designs the processing pipeline and reviews results
- **Builder**: Claude Code — implements the Python scripts following the implementation plan

## Current Task: Build Presentation
Phase 1 (Steps 1–6) gravity processing is COMPLETE. All scripts are in `scripts/01-06*.py` and outputs in `output/`.
**Current task**: Build an academic HTML presentation of results. See `docs/implementation_plan.md`.

## Phase 1 Outputs (in `output/`)
| File | Description |
|------|-------------|
| `gravity_clean.csv` | QC'd gravity data with outlier flags (48,806 rows) |
| `gravity_with_bouguer.csv` | + bouguer_correction, SBA columns |
| `gravity_with_cba.csv` | + terrain_correction, CBA columns |
| `dem_clipped.tif` | DEM in EPSG:4326 |
| `dem_clipped_utm.tif` | DEM in EPSG:32751 (UTM 51S) |
| `faa_grid.nc` | FAA gridded at 2km, height 2600m |
| `cba_grid.nc` | CBA gridded at 2km, height 2600m |
| `01_qc_report.png` | QC figure (4 subplots) |
| `02_dem_preview.png` | DEM preview with stations |
| `03_bouguer_anomaly.png` | FAA vs SBA comparison |
| `04_terrain_correction.png` | Terrain correction + SBA + CBA |
| `05_gridded_maps.png` | Scattered vs gridded (2×2) |
| `06_faa_anomaly_map.png` | Final FAA map with coastlines |
| `06_cba_anomaly_map.png` | Final CBA map with coastlines |
| `06_combined_report.png` | 4-panel: DEM, FAA, CBA, Residual |

## Key Data Stats
- 48,806 points: 16,167 land (33%), 32,639 marine (67%)
- Region: Central Sulawesi, 120.8°–124.1°E, 2.1°S–0°N
- FAA: -149.12 to +240.63 mGal
- CBA: -52.96 to +177.84 mGal (std 37.0)
- SBA std: 38.8, CBA std: 37.0 (terrain correction made it smoother ✓)

## Python Environment
Python 3.12.10 with: harmonica 0.7.0, verde 1.9.0, boule, pyproj 3.7.2, numpy, pandas, xarray, scipy, matplotlib, rasterio, rioxarray, plotly, cartopy, pygmt, xrft

## Constraints
- Do NOT modify existing scripts in `scripts/01-06*.py`
- Use `output/` for all outputs
- The presentation HTML must be self-contained (images as base64)
