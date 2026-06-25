# Results & Discussion — DRAFT
> Airborne Gravity Processing + 3D Inversion of the East Sulawesi Ophiolite
> Generated 2026-06-25 from actual pipeline outputs. **This is a draft for the student to review, refine, and paste into the TA template.** Figure numbers, geological-map specifics, and Tanjung Api H₂ details are marked `[FILL]` where they need your input or sources I haven't read.

---

## 4. Results

### 4.1 Complete Bouguer Anomaly (CBA)

The terrain correction was computed with a 3D prism layer (Harmonica) over the full 48,806-point airborne dataset, using a land density of 2,670 kg/m³ and an ocean density contrast of 1,630 kg/m³. The resulting terrain effect ranges from −258.6 to +258.5 mGal. After subtraction (`CBA = FAA − terrain_effect`), the point-wise **Complete Bouguer Anomaly ranges from −53.0 to +177.8 mGal (mean 50.9, std 37.0 mGal)** [Fig. `[FILL]` — Step 4 panel].

This range is consistent with Sabri et al. (2020), who reported −70.4 to +119.7 mGal (mean 41.1, std 27.5) over the adjacent SE Sulawesi area using the same BIG-DTU 2008 dataset. The slightly wider range here reflects the larger survey footprint and the full 48,806-point coverage retained (0 outliers under the IQR×3 criterion), versus Sabri's aggressively decimated 3,537-point subset.

### 4.2 Gridded anomaly fields (Equivalent Sources)

FAA and CBA were gridded onto a 2 km mesh (122 × 190 cells) using Equivalent Sources at a prediction height of 2,600 m. The dense solver triggered the expected `MemoryError` fallback to the gradient-boosted `EquivalentSourcesGB` implementation. The gridded fields span **FAA −114.3 to +236.2 mGal** and **CBA −37.3 to +130.4 mGal (mean 55.0 mGal)** [Fig. `[FILL]` — Step 5 / Step 6 maps]. A parameter sensitivity test (depth ∈ {5, 10, 15} km, damping ∈ {1, 10, 100}) confirmed depth = 10 km, damping = 10 as a stable reference; alternative combinations differed from it by only 6.6–12.1 mGal RMS, justifying the chosen parameters.

### 4.3 External validation against TOPEX satellite gravity

Gridded airborne FAA was interpolated to 43,621 TOPEX satellite FAA points; 25,284 fell within the survey footprint. The two independent systems agree well:

| Metric | Value |
|--------|-------|
| Pearson correlation (r) | **0.917** |
| RMSE | 42.8 mGal |
| Mean bias (airborne − TOPEX) | +2.5 mGal |

The high correlation confirms the airborne CBA is spatially reliable. The RMSE reflects cross-system differences in resolution and measurement altitude and is **not** a measure of the airborne data's internal precision (an important distinction carried into the inversion; see §5.5).

### 4.4 Regional–residual separation

Regional and residual fields were separated by two independent methods following Pramudya et al. (2025): FFT upward continuation (UC) to 10 km, and a 2D discrete wavelet transform (DWT, Daubechies-4, level 4). The two methods agree strongly on the **regional component (Pearson r = 0.949)**, exceeding Pramudya's reported r = 0.81. The **residual agreement is lower (r = 0.557)** [Fig. `[FILL]` — Step 6, 4-panel UC vs DWT]. This is an expected consequence of survey scale: the present survey is roughly 18× larger in area than Pramudya's Muria study, so UC and DWT respond differently across the much broader band of residual wavelengths. We report this as a methodological limitation rather than an error.

### 4.5 Three-dimensional density inversion

The full CBA grid was inverted for a 3D density-contrast volume using SimPEG (`Simulation3DIntegral` + Tikhonov L2 `WeightedLeastSquares`) on a `discretize.TensorMesh` of **152,775 cells** (4 km horizontal cells; variable vertical cells from 500 m near surface to ~1,154 m at depth; base at the 25 km Moho). Density bounds of −500 to +1,500 kg/m³ (relative to a 2,670 kg/m³ background) were enforced with a projected Gauss–Newton optimizer, and depth/sensitivity weighting was applied.

The inversion converged over 15 β-cooling iterations to an **excellent data fit**:

| Metric | Value |
|--------|-------|
| Observed vs predicted CBA, Pearson r | **0.996** |
| Full-grid RMSE | **2.64 mGal** |
| Recovered density contrast | **−500 to +458 kg/m³** (mean +75, std 73) |
| 99th percentile contrast | +246 kg/m³ |
| Cells at a bound (railing) | 2 of 152,775 (≈ 0.001%) |

The RMSE of 2.64 mGal is below the < 5 mGal benchmark of Pastore et al. (2016), and the near-absence of bound-railing indicates the bounds were not artificially limiting the solution [Fig. `[FILL]` — `07_misfit_map.png`, observed/predicted/misfit].

**Depth distribution of recovered density** [Fig. `[FILL]` — `07_crosssections.png`, 12 N–S sections]. The highest-amplitude positive contrasts (+350 to +458 kg/m³) are concentrated in the **shallowest 0–5 km**, with peak values of +458, +455 and +450 kg/m³ at ~1.7, 0.6 and 2.9 km depth. Below ~5 km the recovered density transitions to a **diffuse, low-amplitude positive background** whose layer-mean rises gradually from ~+55 kg/m³ near surface to ~+115 kg/m³ at the Moho (the fraction of positive cells rises from 0.73 to 0.97 with depth). The interpretation of this shallow-vs-deep partition is developed in §5.3.

---

## 5. Discussion

### 5.1 Data quality and benchmark consistency

The pipeline retains all 48,806 airborne points (0 outliers) and reproduces a CBA field consistent in range and character with the regional benchmark of Sabri et al. (2020), while adding three elements absent from that work: Equivalent-Sources gridding, external TOPEX validation (r = 0.917), and a full 3D inversion. The algebraic equivalence between this project's prism-layer terrain correction and Sabri's split Bouguer-plus-terrain formula independently confirms the decision to skip a standalone simple-Bouguer step.

### 5.2 Geological interpretation of the recovered density

The recovered density-contrast volume images a series of **positive anomalies consistent with the East Sulawesi Ophiolite (ESO)**. The peak contrast of **+458 kg/m³** corresponds to an absolute density of ~3,128 kg/m³, which sits at the **fresh / less-altered peridotite** end of the adopted Sulawesi-local density framework (Kadarusman et al. 2004 modal estimate; Surono & Hartono 2013 PSG value of 2,970 kg/m³ ≈ +300 kg/m³ contrast). The bulk of the high-amplitude cells fall in the +300 to +458 kg/m³ range, consistent with a **fresh-to-moderately-serpentinized ultramafic body** — matching Kadarusman et al.'s petrographic description of the ESO as moderately serpentinized and tectonically dismembered, rather than a single coherent intrusion. `[FILL: tie specific high-density lobes to mapped ESO outcrops / arms using the Sulawesi geological map.]`

### 5.3 Shallow ophiolite vs. the diffuse deep component (the thin-sheet question)

Surono & Hartono (2013) infer from the regional 0–30 mGal anomaly belt that the ESO is a **near-surface sheet rooting to ~500 m or less**, not a deep-rooted mass. The inversion offers partial support and an important caveat:

- **In favour of the thin-sheet model:** the *high-amplitude, localized* density anomalies — the features most plausibly representing the ophiolite proper — are concentrated in the **shallowest few kilometres** (peak +458 kg/m³ at ~0.6–2.9 km). The amplitude of these localized bodies falls off sharply below ~5 km.
- **Caveat (inversion artifact, not geology):** the *diffuse, low-amplitude* positive background that increases toward the Moho is best read as a **regularization / non-uniqueness artifact** rather than a real deep ultramafic root. With no seismic constraint and depth weighting applied, a smooth deep positive mass is a low-cost way for the inversion to satisfy the long-wavelength regional field. It should **not** be interpreted as evidence for a 9–17 km Pastore-type funnel root, and the manuscript should say so explicitly.

The honest summary: the inversion is **consistent with a shallow, laterally extensive ophiolite** carrying the resolvable high-density signal, while deeper structure is poorly constrained by gravity alone. `[FILL: confirm this reading against the actual 07_crosssections.png — which sections show the shallowest, strongest lobes?]`

### 5.4 Implications for the Tanjung Api natural-hydrogen system

`[FILL — student to complete from Satyana 2024 / Sanjaya et al. 2024, which I have not read in detail.]` Suggested framing: a shallow, fresh-to-serpentinized ultramafic body is exactly the lithology associated with natural H₂ generation (serpentinization of Fe-bearing ultramafics). If the recovered high-density shallow anomalies spatially coincide with the Tanjung Api seepage area `[verify on the residual/density maps]`, the gravity result provides an independent geophysical expression of the ultramafic source rock implicated in the H₂ system.

### 5.5 Limitations

1. **Non-uniqueness.** Gravity inversion is inherently non-unique; the recovered density distribution is one of many that fit the data and is regularization-dependent. This manifests as the diffuse deep component (§5.3) and as a low correlation (~0.15) between *column-integrated* density and surface CBA — even though the *predicted CBA map* matches the observed map almost perfectly (r = 0.996). The two numbers measure different things and both should be reported: the data are fit excellently; the depth distribution is not uniquely resolved.
2. **No seismic constraint.** Unlike Pastore et al. (2016), whose SIP model was constrained by deep seismic refraction, this study relies on gravity plus surface geology and a regional Moho estimate only. Depth/density trade-offs cannot be independently broken.
3. **Noise-floor choice.** The inversion data uncertainty was set to ~3 mGal (the CBA grid precision, consistent with Pastore's misfit benchmark), **not** the 42.8 mGal TOPEX cross-validation RMSE. Using the latter caused severe under-fitting; this choice is the single most influential inversion parameter and is documented as such.
4. **Mesh resolution.** The 4 km horizontal cells are coarser than the 2 km CBA grid, so features smaller than ~8 km are not resolved.

---

### Reporting checklist for the student
- [ ] Insert figure numbers and confirm each `[FILL]` against the actual PNGs / 3D viewer.
- [ ] Complete §5.4 (Tanjung Api H₂) from your H₂ references.
- [ ] Cross-check the §5.3 shallow-vs-deep reading against `07_crosssections.png`.
- [ ] Confirm absolute-density conversions if you prefer to report absolute (contrast + 2,670) rather than contrast.
- [ ] One sentence in Methods on the 4-run inversion tuning (noise floor 42.8 → 3.0 mGal was decisive).
