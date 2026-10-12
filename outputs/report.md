# Predicting floc size from physics-only features: results

Data: NSF OCE-1736668 South San Francisco Bay, platform P2. Target = burst-averaged
volume-weighted mean floc diameter `d_mean` from the LISST at **35 cmab** (the paper used 15 cmab
on the optics platform ~30 m away, so this is *not* an exact replication). Features from the
15-cmab ADV (8 Hz) and CTDs. All numbers are reproducible with `build_features.py`, `run_random_forest.py` and `scripts/`; tables in
`outputs/tables/`, figures in `outputs/figures/`.

"EGAN22" = Egan et al. (2022) JGR Oceans. "Class paper" = Egan, CS229 report.

## 1. Summary

| Question | Answer |
|---|---|
| Do physics-only features reach the journal paper's r² (0.15–0.65)? | **Only in-sample** (LASSO in-sample r² 0.17–0.29 per season, 0.43 pooled; `diag_protocols.csv`), which is how EGAN22 Table 1 reports r². Under time-blocked testing, single-season models score **r² ≤ 0** except two regime subsets (Winter-advection RF 0.32 / SVR 0.39; Spring-resuspension LASSO 0.61, n=43). |
| Do they reach the class paper's r² (0.75–0.81)? | **No.** A random 70/30 split (the class-paper protocol) gives 0.33–0.47 per season and 0.64 pooled with these features. Most of that comes from the random split, which puts neighbouring (strongly autocorrelated) hours in the training set. |
| Best result on unseen time periods | Pooled across seasons, time-blocked CV: **RF r² = 0.34 [95% CI 0.15, 0.49]**, SVR 0.31, LASSO 0.27 (RMSE ≈ 20 µm vs 25 µm for the mean). |
| Will it generalise to future conditions? | **Not reliably.** Most of the pooled skill is the *seasonal level* of d, which the model reads off T and S (T,S alone: r² 0.29). Leave-one-season-out, the closest test of new conditions, fails (r² −0.1 to −4.6; biases of 25–40 µm). Within-season, the physics only tracks tide- and wave-scale changes, not multi-day level shifts. |
| Most reliable predictors | `u_bar_4` (4-h lagged current, +) and `u_b` (wave orbital velocity, −), consistent with EGAN22. ε and salinity are weak within a season. |

## 2. Model accuracy (time-blocked CV, out-of-fold)

5 contiguous time blocks per season (15 for pooled), 12-h purge between train and test.
95% CIs from a bootstrap over whole days. Regime "M" subsets with n<40 were skipped.
From `tables/r2_by_season_regime.csv`.

| Season | Regime | n | LASSO+RFECV | RF | SVR | train mean | persistence (1 h)* |
|---|---|---|---|---|---|---|---|
| Summer | all | 427 | −0.14 | −0.33 | −0.24 | −0.20 | 0.72 |
| Summer | R | 42 | −0.17 | −0.18 | −0.02 | −0.09 | 0.31 |
| Summer | A | 290 | −0.51 | −0.22 | −0.45 | −0.18 | 0.73 |
| Summer | M | 52 | −0.12 | −0.17 | −0.09 | −0.07 | 0.66 |
| Winter | all | 406 | −0.12 | −0.52 | −0.37 | −0.14 | 0.49 |
| Winter | R | 84 | −0.25 | −0.25 | −0.11 | −0.12 | 0.50 |
| Winter | A | 212 | 0.06 | **0.32** [0.16, 0.39] | **0.39** [0.18, 0.47] | −0.13 | 0.58 |
| Spring | all | 287 | −0.24 | −0.14 | −0.20 | −0.05 | 0.67 |
| Spring | R | 43 | **0.61** [0.14, 0.74] | 0.32 | 0.16 | −0.21 | 0.54 |
| Spring | A | 111 | −0.30 | −0.15 | −0.50 | −0.21 | 0.62 |
| **Pooled** | all | 1120 | 0.27 [0.14, 0.38] | **0.34** [0.15, 0.49] | 0.31 [0.16, 0.43] | −0.09 | 0.81 |

\* Persistence uses the measured floc size one hour earlier. It is a reference only, because a
prediction made from a single burst would not have it, but it shows that d is strongly autocorrelated.

Negative r² means worse than predicting the test block's own mean. With contiguous blocks this
happens easily: the mean floc size shifts by 20–40 µm between weeks (see `figures/timeseries_rf_oof.png`),
and the physics features don't explain those shifts.

**Leave-one-season-out** (train on two seasons, test on the third; `tables/r2_leave_one_season_out.csv`):

| Held-out season | LASSO | RF | SVR | train mean | RF bias (µm) |
|---|---|---|---|---|---|
| Summer | −1.35 | −0.12 | −2.27 | −0.01 | −3 |
| Winter | −4.80 | −3.85 | −4.51 | −4.69 | +25 |
| Spring | −13.2 | −4.57 | −4.18 | −2.71 | −39 |

Seasonal mean d differs (Summer 84, Winter 65, Spring 105 µm) and no physics feature predicts that
level for an unseen season. This is the main obstacle to a model that works years later.

## 3. Feature selection vs the journal paper

**LASSO + RFECV, paper-style in-sample table** (`tables/lasso_rfecv_selection.json`; −Δr² = drop in
in-sample r² when the feature is removed; features with −Δr² < 0.02 eliminated, as in EGAN22 §3.3):

| Subset | n | in-sample r² | selected (−Δr², sign) | EGAN22 Table 1 (same subset) |
|---|---|---|---|---|
| Summer R | 42 | 0.00 | none | u_b (−) 0.38, ū₄ (+) 0.13; r² 0.51 |
| Summer A | 290 | 0.00 | none | u_b (−) 0.16, ū (+); r² 0.15 |
| Summer M | 52 | 0.22 | u_b (−) 0.10, ū (+) 0.07, ū₄ (−) 0.03 | ū₄ (+), u_b (−), ū (+), S (+); r² 0.33 |
| Winter R | 84 | 0.00 | none | u_b (−) 0.26, ū₄ (+) 0.10; r² 0.45 |
| Winter A | 212 | 0.30 | ū₄ (+) 0.17, S (+) 0.05 | c̄ (−), ū₄ (+), u_b (−), a450/a676; r² 0.50 |
| Spring R | 43 | 0.79 | u_b (−) 0.32, ū₄ (+) 0.10, ū (−) 0.04 | T (+), Chl-a (+), u_b (−); r² 0.46 |
| Spring A | 111 | 0.18 | ū₄ (+) 0.09, S (+) 0.07 | T, Chl-a, a450/a676, c̄; r² 0.15 |
| Summer all | 427 | 0.24 | S (+), T (+), u_b (−) ≈0.13 each | n/a |
| Winter all | 406 | 0.11 | ū₄ (+) 0.11 | n/a |
| Pooled | 1120 | 0.41 | T (+) 0.22, S (−) 0.19, u_b (−) 0.04 | n/a |

"none" = the blocked-CV LASSO chose a penalty large enough to zero every coefficient, i.e. no
feature generalised across time blocks in that subset. The pooled in-sample r² here (0.41) uses
that blocked-CV penalty; §1 and §5 quote 0.43, from a penalty chosen by shuffled CV, the setup the
journal paper most likely used.

**RF permutation importance** (drop in out-of-fold r² when a feature is shuffled;
`tables/rf_permutation_importance.csv`, `figures/rf_importance.png`):

| Feature | Summer | Winter | Spring | Pooled | EGAN22 finding |
|---|---|---|---|---|---|
| u_bar_4 | **0.15** | **0.18** | **0.14** | **0.16** | consistent positive predictor |
| u_b | **0.18** | 0.10 | 0.01 | 0.13 | most reliable, negative |
| u_bar | 0.01 | 0.11 | −0.12 | 0.05 | minor |
| S | −0.08 | 0.07 | 0.04 | 0.05 | marginal |
| T | 0.01 | 0.02 | 0.01 | 0.05 | important in spring (biology proxy) |
| epsilon | 0.01 | 0.00 | 0.02 | 0.01 | not selected |

Agreement with EGAN22: **u_b and lagged current dominate; ε doesn't help; salinity is weak within a
season.** The class paper's "salinity is the top feature" is not reproduced. Salinity (and T) only
matter when seasons are pooled, where they act as a season label.

Disagreement: in Summer the lagged current correlates *negatively* with d (r = −0.23), against
EGAN22's positive sign. This could be the 35 vs 15 cmab height or the different platform.

## 4. Ablations (`tables/ablations.csv`, out-of-fold r², same rows within each season)

| Variant | Summer RF | Winter RF | Spring RF | Pooled RF | Pooled LASSO |
|---|---|---|---|---|---|
| baseline (6 features) | −0.34 | −0.03 | 0.13 | 0.36 | 0.16 |
| − u_bar_4 | −0.45 | −0.24 | 0.13 | 0.32 | 0.17 |
| − S | −0.19 | 0.02 | 0.01 | 0.32 | 0.07 |
| + regime one-hot (leaky†) | −0.24 | 0.05 | 0.16 | 0.37 | 0.16 |
| + ampmean (uncalibrated backscatter) | −0.14 | 0.01 | 0.11 | 0.39 | 0.06 |

† The regime label uses the next 12 h of LISST beam attenuation, so it isn't available for a
prediction made from a single burst. It gave no meaningful gain.

Removing `u_bar_4` hurts in Summer and Winter, matching EGAN22. Removing S hurts the pooled and
Spring models but *helps* Summer and Winter, which is the season-label effect again.

## 5. Why the numbers differ from the papers (diagnostics)

`tables/diag_protocols.csv`, `tables/diag_feature_sets.csv`

| Set | RF time-blocked | RF random 70/30 | LASSO in-sample |
|---|---|---|---|
| Summer | −0.33 | 0.33 | 0.25 |
| Winter | −0.52 | 0.48 | 0.29 |
| Spring | −0.14 | 0.45 | 0.17 |
| Pooled | 0.34 | 0.64 | 0.43 |

1. **Random split inflation.** Hourly floc size is strongly autocorrelated (1-h persistence r²
   0.5–0.8). A random split puts the neighbouring hours of every test point in the training set.
   That alone moves r² from ≤0 to 0.3–0.6. The class paper's 0.81 used this protocol, plus biology
   features that track the slow (multi-day) changes.
2. **In-sample vs out-of-sample.** EGAN22 Table 1 r² values are regression fits on the data
   used for selection, not held-out scores. Our in-sample LASSO (0.17–0.29 per season, 0.43 pooled) sits in the lower half of
   their 0.15–0.65 range, which is reasonable given we lack Chl-a, absorption ratios and mean SSC.
3. **T and S act as clocks.** Within Winter, T and S alone score −0.61 time-blocked but +0.18 on a
   random split: they drift slowly, so a forest uses them to find the "same week" in training.
   The hydrodynamic trio (u_b, ū, ū₄) alone is the best time-blocked Winter model (RF 0.13).
4. **Different measurement.** 35 cmab at P2 vs 15 cmab on the optics platform; 1-min LISST
   averaged over the ADV burst vs hourly samples.

## 6. Robustness to noise and drift (pooled model; `tables/robustness_pooled.csv`)

| Perturbation applied to test inputs | RF r² | LASSO r² |
|---|---|---|
| none | 0.34 | 0.27 |
| white noise, 10% / 25% / 50% of feature sd | 0.33 / 0.30 / 0.25 | 0.27 / 0.25 / 0.18 |
| T +1 °C | 0.33 | 0.26 |
| S −2 PSU | 0.36 | 0.25 |
| velocity gain +10% | 0.34 | 0.27 |
| ε ×2 | 0.32 | 0.27 |

Within the range of the training data the models degrade gracefully with sensor noise and modest
drift. The real risk for a future entry is **leaving the training range or the seasonal pattern**,
which is what leave-one-season-out shows. `src/predict.py` therefore reports every input outside
the training range alongside the prediction (a random forest cannot extrapolate; it flattens at
the edge of what it saw).

## 7. Secondary targets (RF, time-blocked; `tables/r2_secondary_targets.csv`)

d50: Summer −0.30, Winter −0.62, Spring −0.12, Pooled 0.33. σ²: −0.16 / −0.20 / 0.06 / 0.28.
Same picture as the mean diameter.

## 8. Methods and assumptions (all choices that the papers left open)

- **LISST QC:** dropped minutes with transmission tau < 0.1, because the optics are saturated there.
  EGAN22 gives no tau threshold. Bursts with mean tau < 0.3 and bursts within 3 days before a cleaning
  are flagged, not dropped. Removing them did not improve skill (`diag_protocols.csv`).
- **Scintillation (EGAN22 §2.2):** a bin among the 5 smallest/largest that is ≥40% above *both*
  neighbours (outermost bin: an abrupt kink) is removed. Removing the whole tail beyond a spike
  instead clips real coarse flocs (in 39% of Summer and 65% of Spring minutes), gives per-minute
  medians (60 / 61 / 48 µm) far below EGAN22 Fig. 1, and leaves no model with skill (pooled RF r²
  −0.04). The isolated-spike rule gives medians of 83 / 62 / 106 µm, which match Fig. 1. **The results
  depend strongly on this target-cleaning choice.**
- **Target:** volume-weighted arithmetic mean of the burst-averaged PSD (≥7 good minutes per 14-min burst).
- **u_b:** √(2·Σ wave-band (S_uu+S_vv)·df), wave band = [0.5, 2]·f_peak of the ADV pressure spectrum.
  It agrees with linear wave theory from the same pressure sensor (r = 0.95–0.97). EGAN22 defers this
  method to earlier papers.
- **u_bar:** signed burst mean of velmaj (+ = flood, verified against rising water, r = 0.55–0.70).
  **u_bar_4:** the burst 4 h earlier, matched by timestamp.
- **ε:** inertial-subrange fit of S_ww over 1.5–3.5 Hz with the wave-advected speed ⟨|u_h|^{2/3}⟩.
  This is a simplification of Feddersen et al. (2007). 69–87% of bursts have a slope within [−2.2, −1.1].
- **Despiking:** Goring & Nikora (2002) phase-space method, about 1–1.5% of samples replaced.
- **T** from the P2 CTD (co-located; r = 0.95 with P1). **S** from P1, because P2 salinity is unusable.
- **Regime (EGAN22 §3.2):** forward 12-h windows; resuspension if r²(c,u_b) > 1.2·r²(c,ū₄), and vice
  versa for advection. Used only to split the data. Our split is advection-heavy (Summer 68% vs 45%
  in EGAN22).
- **ADV QC:** bursts with >10% NaN (correlation < 30) dropped. Rows kept per step are in `tables/qc_counts.csv`.
- **Differences from the dataset documentation:** ADV `press` is not in dbar (≈0.061 m per unit against CTD depth);
  Spring P2 CTD has no depth; low-correlation ADV samples are NaN rather than interpolated; LISST
  has an undocumented `zsc` variable. The second dataset in EGAN22's data statement
  (purl sh883gp0753) contains benthic images, and the main archive has no optics/biology files.
- **Hyperparameters:** RF 500 trees, min_samples_leaf 5, max_features √p (fixed). SVR (RBF) tuned
  per training fold by an inner time-blocked grid search that includes the class paper's
  C=2048, ε=4. LASSO on standardized features with log10 ε.

## 9. What would most likely improve a model meant to last

1. **Biology and sediment features** (Chl-a, absorption ratios, calibrated SSC), the variables
   EGAN22 needed in spring, are what move the multi-day level of d. They are not in this archive.
2. **More seasons and years.** With three deployments of about three weeks of usable data each, the model sees three seasonal levels;
   it cannot learn what sets the level. Each extra deployment is worth more than any algorithm change.
3. **Recalibrating the level online.** If even an occasional floc size measurement is available,
   use the physics model for hour-to-hour changes and re-estimate the level periodically.
   Persistence-type information is by far the strongest signal in the data.
