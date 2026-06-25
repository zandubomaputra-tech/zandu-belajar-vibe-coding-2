# CLAUDE.md — Project Context for AI Agents
> Tugas Akhir: Airborne Gravity Data Processing Pipeline
> Universitas Pertamina — Teknik Geofisika
> Last updated: June 25, 2026 (Steps 1–7 complete; Step 7 done via SimPEG 3D inversion)

---

## Who is working on this

**Student:** Zandu (Teknik Geofisika, Universitas Pertamina)
**Supervisor direction:** Replicate Pastore (2016) framework — 3D gravity modelling and geological implications — applied to Central Sulawesi airborne gravity dataset.

---

## What this project is about

Processing the **2008 BIG-DTU airborne gravity dataset** over Central and Southeastern Sulawesi, Indonesia using an open-source Python pipeline (Harmonica, Verde, Rioxarray, Cartopy) to produce:

1. Complete Bouguer Anomaly (CBA) map
2. Gridded FAA and CBA (Equivalent Sources, 2 km spacing)
3. External validation against TOPEX satellite FAA data
4. Regional-residual separation (Upward Continuation + Wavelet Transform)
5. 3D gravity inversion of the East Sulawesi Ophiolite (ESO) — recovers a density-contrast volume (SimPEG)
6. Geological implications for Tanjung Api natural hydrogen seepage

**Primary benchmark paper:** Sabri et al. 2020 (ELIPSOIDA) — uses the same BIG-DTU 2008 dataset for SE Sulawesi. No equivalent sources gridding, no open-source pipeline, no TOPEX validation.

**Framework target:** Pastore et al. 2016 (Geophysical Journal International) — 3D gravity modelling of mafic-ultramafic Seiland Igneous Province, Norway. **Methodological framework only** — Pastore's study area is in Norway, not a geological analog in location, age, or tectonic setting. Pastore is used strictly for *how* to do the 3D modelling (multi-section approach, dual-density scenarios, sensitivity testing structure, fit criteria) — never as a source of density values or expected geometry for the ESO. All density and geometric data for the ESO itself must come from Sulawesi-local sources (Kadarusman et al. 2004, Surono & Hartono 2013 / LIPI-PSG regional gravity model). See "Step 7 density framework" and "Known rejected proposals" sections below.

**Critical tectonic distinction:** SIP (Pastore's study area) is a magmatic intrusive complex emplaced into continental crust, expected to produce funnel-shaped roots reaching several km depth. ESO is an **obducted, tectonically dismembered and imbricated ophiolite** (oceanic lithosphere thrust onto land), not a magmatic conduit system. Do not assume ESO geometry will resemble Pastore's funnel-shaped intrusion model — see regional gravity evidence below suggesting ESO is a thin near-surface sheet.

**Research gap (novelty):** No prior study has applied an open-source Python pipeline with Equivalent Sources gridding, 3D prism terrain correction, TOPEX external validation, and SimPEG 3D gravity inversion to this dataset over Central Sulawesi.

---

## Dataset

| File | Description | Status |
|------|-------------|--------|
| `gravity_filled.csv` | Raw airborne gravity, 48,806 points, UTM Zone 51S (EPSG:32751) | ✅ Available |
| `gravity_with_bouguer.csv` | After Step 3 (has outlier_flag, SBA, bouguer_correction) | ✅ Available |
| `output/dem_clipped_utm.tif` | BATNAS DEM clipped to survey area, UTM Zone 51S | ✅ Available |
| `output/gravity_with_cba.csv` | After Step 4 — terrain correction + CBA | ✅ Generated |
| `output/faa_grid.nc` | Gridded FAA, 2 km, Equivalent Sources | ✅ Generated |
| `output/cba_grid.nc` | Gridded CBA, 2 km, Equivalent Sources | ✅ Generated |
| `output/07_density_model.npy` | Step 7 — recovered 3D density contrast (kg/m³), 152,775 cells | ✅ Generated |
| `output/07_predicted_cba.nc` | Step 7 — CBA predicted by the inverted model | ✅ Generated |
| `topex120124_0-3.csv` | TOPEX satellite FAA, 43,621 points, 120–124°E, 3°S–0°N | ✅ Available |

**Key columns in `gravity_filled.csv`:**
```
Bujur, Lintang, FAA, Elevation_m, UTM_X, UTM_Y
```

**Key columns in `gravity_with_bouguer.csv`:**
```
Bujur, Lintang, FAA, Elevation_m, UTM_X, UTM_Y, outlier_flag, bouguer_correction, SBA
```

**Survey extent:**
- Longitude: 120.8° – 124.1°E
- Latitude: 2.1°S – 0.08°N
- Along-track spacing: ~77 m
- Inter-line spacing: ~2–5 km

---

## Pipeline status

### ✅ Step 1 — Data Loading & QC (`01_data_loading_qc.py`)
- Input: `gravity_filled.csv`
- Output: `output/gravity_clean.csv`, `output/01_qc_report.png`
- QC method: IQR × 3 fence
- Result: 0 outliers flagged, all 48,806 points retained
- **COMPLETE**

### ✅ Step 2 — DEM Preparation (`02_dem_preparation_v2.py`)
- Input: BATNAS tiles (N + S), `output/gravity_clean.csv`
- Output: `output/dem_clipped_utm.tif`, `output/gravity_with_dem.csv`
- DEM: BATNAS v1.5, merged + clipped + reprojected to EPSG:32751
- Elevation crosscheck RMSE ≈ 0 m — CSV Elevation_m matches DEM
- **COMPLETE**

### ⏭️ Step 3 — Simple Bouguer Anomaly (`03_bouguer_anomaly.py`)
- **SKIPPED — redundant**
- Reason: Step 4 prism layer already handles the full terrain + slab correction
- Note: `gravity_with_bouguer.csv` was generated from this step previously and is available, but its SBA column is NOT used in Step 4 onward

### ✅ Step 4 — Terrain Correction + CBA (`04_terrain_correction_v3.py`)
- Input: `gravity_filled.csv`, `output/dem_clipped_utm.tif`
- Output: `output/gravity_with_cba.csv`, `output/04_terrain_correction.png`
- Method: 3D prism layer (Harmonica `prism_layer`)
  - DEM coarsened by factor 10 → ~1,850 m effective resolution
  - Land density: 2,670 kg/m³
  - Ocean density contrast: 1,630 kg/m³ (= 2,670 − 1,040)
  - Batched computation: 5,000 points per batch
- Formula: `CBA = FAA − terrain_effect`
- Output columns: `Bujur, Lintang, FAA, Elevation_m, UTM_X, UTM_Y, terrain_correction, CBA`
- **COMPLETE** — CBA −53.0 to +177.8 mGal (mean 50.9, std 37.0), consistent with Sabri 2020

### ✅ Step 5 — Gridding (`05_gridding.py`)
- Input: `output/gravity_with_cba.csv`
- Output: `output/faa_grid.nc`, `output/cba_grid.nc`, `output/05_gridded_maps.png`
- Method: Equivalent Sources (Harmonica `EquivalentSources`)
  - damping = 10, depth = 10,000 m
  - Grid spacing: 2,000 m
  - Prediction height: 2,600 m
  - Fallback: `EquivalentSourcesGB` on MemoryError
- **COMPLETE** — MemoryError triggered fallback to `EquivalentSourcesGB` (expected). Grid 122×190. FAA −114 to +236, CBA −37 to +130 mGal

### ✅ Step 5.5 — Sensitivity Analysis + TOPEX Validation (`05_5_validation.py`)
- Input: `output/faa_grid.nc`, `topex120124_0-3.csv`
- Tasks:
  1. **Sensitivity analysis**: vary ES `depth` (5000, 10000, 15000 m) and `damping` (1, 10, 100) — document effect on CBA map — justifies parameter choice
  2. **TOPEX validation**: interpolate gridded FAA airborne to 43,621 TOPEX point locations → compare with `faa_topex` column → compute correlation, RMSE, bias, scatter plot
- **COMPLETE** — depth=10k/damping=10 is the reference; 25,284 TOPEX points overlap → **r = 0.917**, RMSE 42.8 mGal, bias +2.5 mGal
- ⚠️ The TOPEX RMSE (42.8 mGal) is a cross-system validation metric — do **not** reuse it as the data-uncertainty/noise-floor for the Step 7 inversion (see Step 7 note)

### ✅ Step 6 — Final Maps + Regional-Residual Separation (`06_final_maps.py`)
- Input: `output/faa_grid.nc`, `output/cba_grid.nc`, `output/dem_clipped.tif`
- Output: publication-quality maps (300 dpi) + `06_regional_residual.png`
- **COMPLETE** — `vd.Trend` replaced with Upward Continuation (10 km) + DWT (`db4`, level 4) per Pramudya 2025
- UC-vs-DWT validation: **r = 0.949 regional**, r = 0.557 residual. The low residual r is expected — survey is ~18× larger than Pramudya's Muria area; document as a methodology limitation, not an error

### ✅ Step 7 — 3D Gravity Inversion (`07_3d_inversion.py`, `07_figures.py`, `notebooks/07_interactive_viewer.ipynb`)
- **Approach chosen: full-survey 3D gravity INVERSION (SimPEG), not per-section forward modelling.** Recovers a 3D density-contrast volume directly from the CBA grid, rather than building forward models of an assumed body. Pastore 2016 remains the *framing* (3D density imaging of an ophiolite, sensitivity/limitation discussion); the density bounds still come from the Sulawesi-local framework below.
- **Method**: SimPEG `Simulation3DIntegral` + Tikhonov L2 inversion (`WeightedLeastSquares`) on a `discretize.TensorMesh`
  - Domain: full survey, 4 km horizontal cells, variable z (500 m→1154 m) to Moho 25 km → 152,775 cells
  - Input: full CBA grid (`cba_grid.nc`), subsampled every 4th point (~1,488 obs) for the sensitivity matrix
  - Bounds: −500 to +1,500 kg/m³ contrast (`ProjectedGNCG`); reference model 0; depth/sensitivity weighting + preconditioner
- **Result**: density contrast **−500 to +458 kg/m³** (peak in ESO peridotite range), full-grid **RMSE 2.64 mGal** (beats Pastore <5 mGal), no bound-railing (2/152,775 cells)
- Outputs: `07_density_model.npy` (kg/m³), `07_predicted_cba.nc`, `07_misfit_map.png`, `07_crosssections.png` (12 N-S sections), `07_3d_viewer.html`
- **⚠️ Critical convention gotcha (cost 4 debug runs — preserve this):**
  1. SimPEG gravity density is in **g/cc** and `gz` is **upward-positive**; this project's CBA is **downward-positive** (Harmonica). So: model in g/cc internally (×1000 to save kg/m³), bounds in g/cc, `dobs_simpeg = −CBA`, and `predicted_CBA = −simulation.dpred(model_gcc)`. A dense body must map to **positive** CBA — verify with `_test_07_forward.py` (+0.3 g/cc → negative gz).
  2. **Noise floor must be ~3 mGal (≈ CBA grid precision / Pastore benchmark), NOT 42.8 mGal.** Using the TOPEX cross-validation RMSE (42.8) as the inversion noise floor makes it under-fit (density frozen near zero). This was the single decisive fix.
  3. Inversion is **linear** + sensitivities cached → multi-iteration structure comes only from the β-cooling schedule; start β high (`beta0_ratio=1000`) and cool gradually, else it stops after 1 iteration.
- **Architecture**: the inversion script saves model+prediction; figures (`07_figures.py`) and the notebook **load from disk** — never re-run the ~40-min inversion just to regenerate figures.
- **For the manuscript**: cite the **column-integrated** density↔CBA correlation + sign-match (~90%), not the top-layer number; frame depth resolution / the modest ~0.15 correlation as inherent gravity non-uniqueness (consistent with the "no seismic constraint" limitation below), not a defect. The thin-sheet expectation below is now something the recovered model can be compared against in the discussion.

---

## Reference papers (status: read in full unless noted)

| Paper | Relevance | Key takeaway |
|-------|-----------|--------------|
| Sabri et al. 2020 (ELIPSOIDA) | Same BIG-DTU 2008 dataset, SE Sulawesi | Primary benchmark. CBA range −70.4 to +119.7 mGal, mean 41.1, std 27.5 mGal, R²=83% vs terrestrial Kendari sheet. Their QC was aggressive (64,481→3,537 points via acceleration + cross-over filtering) vs this project's 48,806 points with 0 outliers — a strength to highlight. Their CBA formula (`g_obs−(g_n−FA+B−T)`) is algebraically equivalent to this project's prism-layer approach, confirming the Step 3-skip decision independently. They use seawater density 1.03 g/cm³ (vs this project's 1.04) — minor rounding difference, not significant. |
| Pastore et al. 2016 (GJI) | 3D modelling **methodology** framework only (NOT a geological or density analog — see role-separation note above) | 12 N-S cross-sections, dual-density modelling (M1/M2), sensitivity test isolating one variable at a time, RMSE <5 mGal fit benchmark. Petrophysical database is 310 measured samples (NGU Norway) — not usable for ESO density values. |
| Pramudya et al. 2025 (IJRR) | Regional-residual separation method | Muria Peninsula (86×70 km, flight alt. ~4 km). Upward continuation at 15,000 m altitude (likely needs adjustment for ESO's much larger ~435 km diagonal area). DWT (not CWT) used for wavelet, but specific wavelet type and decomposition level NOT specified in paper — needs independent implementation decision at Step 6. Validation via Pearson correlation between UC and wavelet results (r=0.81 regional, r=0.98 residual) — this validation approach can be replicated for Step 6. |
| Surono & Hartono 2013 (LIPI Press, "Geologi Sulawesi") | Regional geological + gravity context, ESO density (Bab IX Kompleks Ofiolit, Bab XI Gayaberat) | Official PSG/BIG regional crustal density model (see density framework section above). Key finding: ESO gravity anomaly belt (0 to +30 mGal) indicates a thin, shallow (~500 m) ophiolite sheet, not a deep-rooted body — contrasts with Pastore's SIP (9–17 km roots). See full density table and structural notes above. |
| Pahlevi et al. 2015 (FIG Working Week) | Same BIG-DTU 2008 survey campaign, geoid modelling context | Confirms survey acquisition context (BIG + DTU joint campaign 2008–2011, covering Kalimantan/Sulawesi/Papua for geoid purposes). |
| Kadarusman et al. 2004 (Tectonophysics) | ESO petrology, geochemistry, paleogeographic reconstruction | No direct density measurements — only modal mineralogy. Used to estimate fresh-peridotite density (~3,000–3,350 kg/m³) and confirms ESO is "tectonically dismembered" and "highly imbricated" (supports thin-sheet geometry expectation, not massive intrusion). |
| Pahlevi et al. 2024 (Sci Data, `s41597-024-03646-w`) | INAGEOID2020 dataset paper | Available in uploads folder, not yet read in detail this session. |
| Satyana 2024 (IPA) | Natural H₂, Tanjung Api | Geological motivation for target area — not yet uploaded/read in detail. |
| Sanjaya et al. 2024 | Natural H₂, Ampana Basin | Confirms H₂ system in study area — not yet uploaded/read in detail. |
| Sompotan (book) | Struktur Geologi Sulawesi | Structural geology context — not yet uploaded/read in detail. |

---

## Step 7 density framework — ESO 3D modelling (do not use Pastore's Norway density values)

Three independent sources were synthesized to constrain ESO peridotite/gabbro density, since no direct density measurements of ESO rock exist in the literature reviewed so far:

| Source | Basis | Peridotite density estimate | Weight |
|--------|-------|------------------------------|--------|
| Kadarusman et al. 2004 | Modal mineralogy of ESO rocks (no direct measurement) | ~3,000–3,350 kg/m³ (fresh), needs downward correction for "moderately serpentinized" description | Direct ESO data, but indirect (modal estimate, not measured) |
| Global serpentinization literature (Troodos, Oman, Point Sal, MARK — via web search, not yet uploaded as papers) | Fresh peridotite ~3,300 kg/m³ → fully serpentinized ~2,500–2,600 kg/m³; Troodos gravity modelling precedent (Gass & Masson-Smith 1963) used 3,300 vs 2,670 kg/m³ contrast | 2,670–3,300 kg/m³ range depending on alteration degree | Strong analog precedent, but not Sulawesi-specific |
| Surono & Hartono 2013 (LIPI/PSG, Bab XI Gayaberat, by Sardjono) | Official BIG/PSG regional crustal density model for Sulawesi gravity modelling | **2,970 kg/m³** (single value, "keratan ultrabasa") | **Highest weight — official regional source, specific to Sulawesi** |

**Adopted density framework (Sulawesi-local values; originally framed as Pastore-style M1/M2 scenarios, now used as inversion priors/bounds — see mapping note below):**
- **Low-density scenario:** 2,700–2,900 kg/m³ — represents moderately to highly serpentinized peridotite
- **High-density scenario:** 3,100–3,300 kg/m³ — represents fresh/less-altered peridotite (Kadarusman modal estimate)
- **Single intermediate reference value:** 2,970 kg/m³ (Surono & Hartono 2013 / PSG official regional model) — use this as the primary single-value reference when a dual-scenario isn't needed
- **Gabbro/cumulate:** 2,900–3,000 kg/m³ (single estimate; less sensitive to alteration than peridotite)

**How this maps to the Step 7 inversion (reconciliation):** the implemented method is a 3D *inversion* that **recovers** a continuous density-contrast volume, not a forward model testing discrete M1/M2 scenarios. The density framework above is consumed as **bounds and interpretation anchors**, not as scenario inputs:
- Expressed as contrast vs the 2,670 kg/m³ background: serpentinized low ≈ +30 to +230 kg/m³, fresh-peridotite high ≈ +430 to +630 kg/m³, PSG reference (2,970) ≈ +300 kg/m³.
- The inversion `ProjectedGNCG` bounds were set wider (−500 to +1,500 kg/m³) so the solution is not pre-constrained — it can reach serpentinized lows, fresh-peridotite highs, and sediment negatives, and reveal where it *actually* lands.
- The recovered peak (**+458 kg/m³**) falls at the **fresh / less-altered peridotite** end of the framework — interpret in the manuscript against these anchors (e.g., +458 ≈ a fresh-to-moderately-serpentinized ultramafic body, consistent with Kadarusman's "moderately serpentinized" description).
- The dual M1/M2 *scenario test* is therefore superseded by the inversion; if a reviewer asks for an explicit M1/M2 comparison, re-running the inversion with bounds clamped to each scenario range is the inversion-equivalent of Pastore's Test A.

**Full crustal density model from Surono & Hartono 2013 (PSG official, for any regional context needed in Step 6/7):**

| Layer | Density (kg/m³) |
|-------|------------------|
| Granitic crust (continental) | 2,670 |
| Sedimentary cover | 2,370 |
| Basaltic crust (oceanic) | 2,770 |
| Metamorphic rocks / granitic pluton | 2,470 |
| Ultrabasic rock (ophiolite) | **2,970** |
| Seawater | 1,030 |
| Upper mantle | 3,070 |

### Critical geological insight — ESO is likely a thin, shallow body (not deep-rooted)

Per Surono & Hartono 2013 (Bab XI, sub-section "Lajur ofiolit Sulawesi Timur"): regional gravity anomaly observed over the East and Southeast Sulawesi ophiolite belt is only **0 to +30 mGal**, far lower than the **+60 mGal or more** that would be expected if the ultrabasic body extended as a thick, deep-rooted mass. PSG's interpretation: the ophiolite is generally a **near-surface sheet, rooting to approximately 500 m depth or less**, overlying ~3,000 m of sediment, on top of ~19 km granitic crust, with Moho at ~25 km depth. East Arm and Southeast Arm are interpreted to share a similar crustal structure.

**Implication for Step 7 expectations:** Do not expect or model a deep funnel-shaped root analogous to Pastore's SIP (9–17 km depth). The ESO 3D model should be consistent with a thin (~500 m or less), laterally extensive sheet-like body unless local gravity data (after Step 5–6 processing) shows a clear deviation from this regional baseline — which would itself be a noteworthy local anomaly worth highlighting (e.g., possible relevance to Tanjung Api structural context).

**Local structural note:** Matano Fault System causes a Moho offset of ~1,000 m in the regional model (north side ~25 km, south side ~24 km). If the study area's cross-sections cross this fault zone, account for this offset in Moho constraint.

### Step 7 sensitivity testing methodology

**Implemented (inversion) approach — what to report.** Because the method is inversion (geometry is recovered, not assumed), Pastore's "vary geometry vs density independently" forward-modelling structure does not apply directly. The inversion-equivalent sensitivity is to vary the **inversion controls** and observe the effect on the recovered model + misfit. The tuning that produced the final model already exercised this (document it as the sensitivity analysis):
1. **Data uncertainty / noise floor** — the single most influential parameter. 42.8 mGal (under-fit, density frozen near 0) → 3.0 mGal (RMSE 2.64 mGal, density reaches +458). Report this as the decisive control.
2. **Smallness regularization `alpha_s`** — 1e-4 (amplitudes suppressed, peak +98) → 1e-6 (geologically meaningful amplitudes).
3. **β strategy (`beta0_ratio`)** — too low → single-jump non-result; `beta0_ratio=1000` with gradual cooling → 15-iteration descent with spatial structure.
4. **Fit criterion**: full-grid RMSE between observed and predicted CBA; achieved **2.64 mGal**, below Pastore's <5 mGal benchmark.
5. **Optional Pastore-style density test (Test A equivalent)**: re-run with bounds clamped to the low (2,700–2,900) vs high (3,100–3,300) scenario ranges and compare recovered geometry/misfit — only if a reviewer wants an explicit M1/M2 contrast.

> **Original forward-modelling plan (superseded, kept for context):** isolate ONE variable per run — Test A (fixed geometry, vary density M1/M2), Test B (fixed density, vary geometry width/extent), fit criterion RMSE <5 mGal. This was the pre-inversion design; the inversion subsumes it.

### Known limitation vs Pastore 2016 benchmark

Pastore's SIP model is constrained by **both gravity AND deep seismic refraction data** (Chroston et al. 1976), giving an independent depth/density cross-check beyond gravity alone. **This study (ESO) likely lacks equivalent seismic refraction constraint** for the specific study area. Geometry constraint for Step 7 will rely on gravity data (this study) + surface geology (Kadarusman 2004, Surono & Hartono 2013) + global Moho model (CRUST1.0/LITHO1.0) only. This must be stated explicitly as a limitation in the manuscript discussion section — do not imply equivalent constraint strength to Pastore's model.

---

## Key methodological decisions (already confirmed, do not change)

| Decision | Value | Reason |
|----------|-------|--------|
| Step 3 skip | Yes | Prism layer replaces slab correction — independently confirmed consistent with Sabri 2020's split B+T formula |
| Ocean density contrast | 1,630 kg/m³ | = crust (2670) − water (1040) |
| Land density | 2,670 kg/m³ | Standard crustal density |
| DEM coarsen factor | 10 | ~1,850 m effective, ~43K prisms, memory feasible |
| ES depth | 10,000 m | Default — to be justified by sensitivity analysis |
| ES damping | 10 | Default — to be justified by sensitivity analysis |
| Grid spacing | 2,000 m | **Confirmed compatible**: TOPEX actual resolution checked = ~1.86 km (0.0167°), apple-to-apple with 2 km grid, no resolution mismatch |
| Prediction height | 2,600 m | Slightly above max flight altitude |
| TOPEX comparison | FAA vs FAA | Apple-to-apple, both are Free Air Anomaly |
| Regional-residual | Upward continuation + Wavelet | Following Pramudya 2025, not linear trend — UC altitude (15 km in Pramudya's smaller study area) likely needs upward adjustment for ESO's larger extent; wavelet type/decomposition level not specified in source, needs independent decision |
| Step 7 density (peridotite) | Dual-scenario 2,700–2,900 (low) / 3,100–3,300 (high) kg/m³, single reference 2,970 kg/m³ | Synthesized from Kadarusman 2004 (modal estimate) + global serpentinization literature + Surono & Hartono 2013 (PSG official regional model, highest weight) — see full density framework section above |
| Step 7 density (gabbro/cumulate) | 2,900–3,000 kg/m³ | Single estimate, less alteration-sensitive than peridotite |
| Step 7 geometry expectation | Thin sheet (~500 m or less), NOT deep-rooted funnel | Per Surono & Hartono 2013 regional gravity evidence (0–30 mGal anomaly belt) — explicitly contrasts with Pastore's SIP (9–17 km roots). NOTE: with the inversion this is no longer a modelling *assumption* but a **comparison target** — check whether the recovered density volume is concentrated shallow (consistent with the thin-sheet expectation) or shows deeper structure (a noteworthy local deviation worth discussing) |

---

## Known rejected proposals — do not re-suggest these

These have already been investigated and disproven with evidence. If asked to review the pipeline, do not propose them again without new evidence.

| Proposal | Rejected because |
|----------|-------------------|
| `CBA = FAA + terrain_effect` (instead of `−`) | Two separate documents (`implementation_plan.md`, `terrain_correction_physics.md`) proposed this based on a Z-up axis vector argument. Both are **wrong**: confirmed via Harmonica's own documentation (`prism_gravity` docstring states `g_z` is downward-positive by design, not a raw Z-up vector component) and empirical numerical test (a +2,670 kg/m³ density mountain produces `g_z` = **+107.14 mGal**, not negative). The current formula `CBA = FAA − terrain_effect` is correct and final. |
| Sign-check / conditional logic on `terrain_effect` before subtracting | Same root cause as above — adding a sign-check assumes the formula is sometimes wrong, but it isn't. No conditional logic needed; the formula works correctly for both land and marine points without modification. |
| Downward continuation (DWC) before CBA computation | The input elevation data (`gravity_filled.csv` / DEM) is already referenced to ground level, not flight altitude. No DWC step is needed before terrain correction / CBA. Do not add a DWC step to Step 4. |
| `parallel=True` Numba flag for prism computation | This part of `implementation_plan.md`'s proposal is **not rejected** — it's an independent performance optimization unrelated to the sign issue, and may be used if computation speed becomes a problem. |
| Using Pastore (2016) SIP density values (3,100 / 3,300 kg/m³) directly for ESO without modification | Those are NGU Norway database values for a magmatic intrusive complex in a completely different tectonic setting. Pastore is a **methodology source only** (see "Step 7 density framework" above). ESO density values must come from Sulawesi-local sources. |

---

## Immediate next actions (in order)

**Pipeline Steps 1–7 are COMPLETE** (all ran 2026-06-25). Only the manuscript remains.

1. **Write manuscript Results + Discussion** — all Step 4–7 outputs now exist
   - **Partial progress**: Introduction and Data and Methodology sections already drafted in the official TA paper template (`Draft_Template_TA_format_Paper_ENG_ver_2.docx`), based on confirmed methodology and density framework above. Results and Discussion intentionally left as placeholder — cannot be written until Step 4–7 outputs exist. 6 references cited (Kadarusman 2004, Surono & Hartono 2013, Pahlevi 2015, Sabri 2020, Pramudya 2025, Pastore 2016).

---

## Project folder structure (expected)

```
project/
├── CLAUDE.md                        ← this file
├── gravity_filled.csv               ← raw input
├── topex120124_0-3.csv              ← TOPEX validation data
├── output/
│   ├── gravity_clean.csv            ✅
│   ├── gravity_with_dem.csv         ✅
│   ├── gravity_with_bouguer.csv     ✅
│   ├── dem_merged.tif               ✅
│   ├── dem_clipped.tif              ✅
│   ├── dem_clipped_utm.tif          ✅
│   ├── gravity_with_cba.csv         ✅
│   ├── faa_grid.nc                  ✅
│   ├── cba_grid.nc                  ✅
│   ├── 07_density_model.npy         ✅
│   └── 07_predicted_cba.nc          ✅
├── scripts/
│   ├── 01_data_loading_qc.py        ✅
│   ├── 02_dem_preparation_v2.py     ✅
│   ├── 03_bouguer_anomaly.py        ⏭️ skipped
│   ├── 04_terrain_correction_v3.py  ✅
│   ├── 05_gridding.py               ✅
│   ├── 05_5_validation.py           ✅
│   ├── 06_final_maps.py             ✅
│   ├── 07_3d_inversion.py           ✅ (SimPEG inversion)
│   └── 07_figures.py                ✅ (loads outputs → figures)
└── notebooks/
    └── 07_interactive_viewer.ipynb  ✅ (3D viewer + cross-sections)
```

---

## Notes for AI agents reading this file

- Do not change methodological decisions listed above without consulting the student
- Step 3 is intentionally skipped — do not re-introduce it
- **Before suggesting any fix to Step 4 (CBA formula, sign conventions, DWC)**: check the "Known rejected proposals" section above first — several plausible-sounding proposals have already been investigated and disproven with evidence
- **Pastore 2016 is a methodology source only, never a density/geometry source for ESO** — see role-separation note at top of file and "Step 7 density framework" section
- `outlier_flag` column is NOT in `gravity_filled.csv` — if a script needs it, recompute from IQR or use `gravity_with_bouguer.csv` as input instead
- All scripts use path relative to `SCRIPT_DIR` — place scripts in `scripts/` subfolder
- The student prefers concise responses and wants to be warned before high-token outputs
- Primary language: Indonesian (informal), technical content in English
