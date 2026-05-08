# Design: Academic Gravity Processing Presentation

**Date**: 2026-05-08
**Status**: Approved by user

## What We're Building

A single self-contained `output/presentation.html` built by `scripts/build_presentation.py`.

- **Engine**: Reveal.js 5.1.0 from CDN (no npm required)
- **Images**: All output PNGs embedded as base64 data URIs
- **14 slides**: Title → Outline → Intro → Survey Data → Methodology → QC → DEM → Bouguer → Terrain → Gridding → FAA map → CBA map → Combined → Conclusions
- **Style**: Inter/Fira Code fonts, dark navy headers, dark gradient title/conclusion slide, 1280×720
- **Format confirmed**: HTML (not .pptx)

## Full Spec

See [docs/implementation_plan.md](../implementation_plan.md) — written by architect Antigravity. All slide content, CSS rules, Reveal.js config, and build script requirements are specified there.

## Confirmed Present

All 8 required PNGs exist in `output/`:
`01_qc_report.png`, `02_dem_preview.png`, `03_bouguer_anomaly.png`, `04_terrain_correction.png`,
`05_gridded_maps.png`, `06_faa_anomaly_map.png`, `06_cba_anomaly_map.png`, `06_combined_report.png`
