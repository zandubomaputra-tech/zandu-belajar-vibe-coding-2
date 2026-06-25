# CBA Sign Convention — Why `CBA = FAA + terrain_effect` Is Rejected

> **Status: REJECTED.** The correct formula, already implemented in `04_terrain_correction_v3.py`, is:
> ```
> CBA = FAA − terrain_effect
> ```
> This document exists so that any future AI agent, contributor, or reviewer who encounters a proposal to flip this sign can be pointed here instead of re-litigating the issue from scratch.

---

## 1. What is being rejected

Two separate documents have proposed changing the sign in the CBA formula:

1. **`implementation_plan.md`** — proposes `CBA = faa + terrain_effect`, justified by a claim that Harmonica's Z-up coordinate system makes `g_z` (stored as `terrain_effect`) negative for masses below the sensor.
2. **`terrain_correction_physics.md`** — makes the same proposal with a more elaborate physics narrative: that because Harmonica is "Z-up," the gravitational pull of terrain below the aircraft is a downward vector, which in a Z-up system is negative, so `g_z` is "always negative," and adding it is equivalent to subtracting its magnitude.

Both documents reach the same wrong conclusion via the same wrong premise. Both also recommend hardcoding the formula (correctly, as a design choice) rather than using runtime sign-checks — but the formula they hardcode is the wrong one.

---

## 2. The authoritative source: Harmonica's own documentation

Harmonica's `prism_gravity` / `prism_layer` documentation states, verbatim:

> *"the `g_z` field returns the **downward component** of the gravitational acceleration so that **positive density contrasts produce positive anomalies**."*

This single sentence is sufficient to invalidate the premise of both documents. Harmonica does **not** return a raw Z-up Cartesian vector component where "up" is positive and "down" is negative. It deliberately **redefines** `g_z` as the downward-positive component — this is a documented convention choice by the library authors, specifically so that the output behaves the way geophysicists expect: a mass excess below you produces a *positive* gravity reading, full stop. The Z-up/Z-down argument made in `terrain_correction_physics.md` describes how a generic Cartesian physics vector would behave, not how Harmonica's `g_z` output is actually defined.

---

## 3. Empirical verification

Documentation claims can in principle be mis-read, so this was also tested directly with a controlled numerical example using the actual `prism_gravity` function:

- **Setup:** a prism representing a mountain, density contrast **+2,670 kg/m³** (the same land density used throughout this pipeline), positioned below the observation point — i.e., the exact physical scenario described in both rejected documents.
- **Result:** `g_z` = **+107.14 mGal** — positive, not negative.

This is the same scenario `terrain_correction_physics.md` uses in its own worked example (a mountain attracting the aircraft downward), and it produces the opposite sign from what that document claims. The empirical result matches the documentation exactly: positive density contrast → positive anomaly.

---

## 4. Claim-by-claim breakdown

| Claim made in the rejected documents | What is actually true |
|---|---|
| "Harmonica uses a Z-up coordinate system, so `g_z` is negative for masses below the sensor" | Harmonica's `g_z` is explicitly documented as the **downward-positive** component, not a raw Z-up vector projection. The premise misapplies a generic vector-convention argument to a function that does not follow that convention. |
| "`terrain_effect` will **always** be negative" | False as a general statement, and false for this pipeline's standard case. For any point where the prism layer represents a positive density contrast (land, density +2,670 kg/m³), `g_z` is positive. Empirically confirmed: **+107.14 mGal** for a mountain, not negative. |
| "Adding `terrain_effect` is mathematically equivalent to `FAA − \|terrain_effect\|`" | This equivalence only holds if `terrain_effect` is in fact negative. Since the premise is false, the equivalence does not hold for this pipeline. Applying it produces `FAA + |terrain_effect|`, not `FAA − |terrain_effect|`. |
| "Hardcode the formula instead of using a runtime sign-check" | This part of the reasoning is sound practice — sign-checks based on a possibly-noisy mean are fragile, as `terrain_correction_physics.md` correctly points out. But sound reasoning was used to justify hardcoding the **wrong** formula. The fix is to hardcode `CBA = FAA − terrain_effect`, not to add conditional logic. |

---

## 5. Why this matters: consequence if the rejected formula were applied

If `CBA = FAA + terrain_effect` were implemented as proposed, the effect would be the **opposite** of a terrain correction:

- At a mountain point, `terrain_effect` is large and positive (e.g., +107 mGal in the test case above).
- `FAA + terrain_effect` **adds** this value to the Free-Air Anomaly instead of removing it.
- The resulting "CBA" would be *more* correlated with topography than the FAA it started from, not less — the exact opposite of what a Bouguer/terrain correction is supposed to achieve.
- Over the East Sulawesi Ophiolite's highland areas, this would systematically inflate the anomaly in a way that tracks elevation rather than subsurface density, contaminating every downstream step (gridding, regional-residual separation, and the Step 7 3D model) with a topography-correlated artifact.

---

## 6. What remains valid from these documents

Not everything in `implementation_plan.md` should be discarded. The proposal to pass `parallel=True` to `prisms.prism_layer.gravity(batch, field="g_z", parallel=True)` for Numba-accelerated computation is **independent of the sign issue** and is safe to adopt if computation speed becomes a bottleneck. It has nothing to do with the formula's correctness and is not part of this rejection.

The other item in `implementation_plan.md` — updating Step 4's status in `CLAUDE.md` to `✅ COMPLETE` after running the script — is also not itself wrong as a process step, but it must only happen after Step 4 is actually run successfully with the **correct** formula; it should not be done as part of applying this rejected sign change.

---

## 7. Final verdict

- **Formula in use, confirmed correct:** `CBA = FAA − terrain_effect`, as implemented in `04_terrain_correction_v3.py`. No change needed.
- **Both `implementation_plan.md` and `terrain_correction_physics.md` are rejected** on the specific point of flipping the CBA sign or adding sign-check logic.
- **Basis for rejection:** Harmonica's own documentation (`g_z` is downward-positive by design) plus a direct empirical test (+2,670 kg/m³ mountain → `g_z` = +107.14 mGal, positive).
- If a future agent or collaborator proposes this same sign flip again — even with a fresh-sounding physics argument — the premise should be checked against Section 2 and Section 3 of this document before any code is changed.
