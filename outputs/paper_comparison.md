# Comparison with the published paper

**Journal paper:** Egan et al. (2022), "On the Variability of Floc Characteristics in a Shallow
Estuary", JGR Oceans. Called "the paper" below.
**Class paper:** Egan's CS229 report (Random Forest and SVR), included where relevant.
**This project:** full details in `outputs/report.md`.

## 0. Summary

| | The paper | This project |
|---|---|---|
| Goal | Explain what drives floc size | Predict floc size from physical measurements only |
| Inputs | Physics, biology and sediment concentration (11 candidates) | Physics only (6 features) |
| How r² is measured | On the data the model was fitted to (in-sample) | On time periods the model has not seen (out-of-sample), plus in-sample for comparison |
| Reported r² | 0.15 to 0.65 | In-sample 0.17 to 0.43; out-of-sample 0.34 pooled, 0 or below within a single season |
| Main drivers | Waves reduce floc size, the tide 4 h earlier increases it, biology matters in spring | The same physical drivers; biology cannot be tested (no data) |
| Conclusion | Explains part of the variability | Agrees with the paper's physics; physics alone does not forecast floc size reliably |

The paper's r² measures how well a model fits the data it was built on. This project also
measures how well a model predicts new data, which is harder and gives lower numbers.

## 1. Glossary

| Term | Meaning |
|---|---|
| **Floc, floc size (d)** | Fine mud particles stick together into loose clumps (flocs). Their size (µm) controls how fast mud settles. This is the quantity predicted. |
| **LISST** | Laser instrument that measures the particle size distribution every minute. |
| **ADV** | Acoustic current meter, 8 samples per second, 15 cm above the bed. Source of the wave and current features. |
| **CTD** | Temperature and salinity sensor. |
| **u_b** | Wave orbital velocity: how strongly waves move the water near the bed. Strong waves can break flocs. |
| **ū (u_bar)** | Mean tidal current (+ = flood tide, water coming in). |
| **ū₄ (u_bar_4)** | The tidal current 4 hours earlier. The paper found that sediment arriving now was set in motion about 4 h earlier upstream. |
| **ε (epsilon)** | Turbulence dissipation: the amount of small-scale mixing. |
| **T, S** | Water temperature and salinity. |
| **Chl-a, absorption ratios** | Biology measurements (algae, organic matter). Used by the paper; not available here. |
| **c̄ (SSC)** | Suspended sediment concentration. The paper used a calibrated version; not available here. |
| **Regime R / A / M** | Resuspension (mud stirred up locally by waves), Advection (mud carried in by the tide), Mixed. |
| **r²** | Share of the variation in floc size a model explains. 1 is perfect, 0 is no better than predicting the average, below 0 is worse than the average. |
| **In-sample, out-of-sample** | In-sample: scored on the data used to build the model. Out-of-sample: scored on data held back. |
| **Random split, time-blocked split** | Random split: test hours are scattered among training hours, so the model has seen the hours on either side of each test hour. Time-blocked: whole multi-day stretches are held out, which is closer to real forecasting. |
| **LASSO + RFECV** | A linear model that sets unhelpful features to zero, followed by recursive removal of features to find the best set. The paper's method. |
| **Random Forest (RF), SVR** | Two non-linear models, used in the class paper. |

## 2. Data and setup

| | The paper | This project | Effect |
|---|---|---|---|
| Location | South San Francisco Bay shoals, platforms P1 and P1O | Same campaigns, platform P2 (the public dataset) | Some: a different site means a somewhat different sediment supply. |
| Seasons | Summer 2018, Winter 2019, Spring 2019 | Same | None |
| LISST height | 15 cm above the bed | 35 cm above the bed | Probably minor: the paper found 15 and 45 cm similar. |
| LISST sampling | Once per hour | Every minute, averaged over each 14-min ADV burst | Each data point here is less noisy. |
| Platform layout | LISST about 30 m from the current meters | Same platform | None |
| Rows per season (all regimes) | Summer 443, Winter 570, Spring 331 (sum of Table 1 N) | Summer 427, Winter 406, Spring 287 | Similar size |
| Biology data (Chl-a, absorption) | Yes | No: not in the public archive or the second linked dataset | Large, especially in spring |
| Calibrated SSC | Yes | No (an uncalibrated acoustic backscatter proxy is tested separately) | Moderate |
| Salinity source | CTD on the instrument frame about 30 m from the optics platform | CTD at P1, 1.2 km away (the P2 salinity sensor failed) | Minor: salinity changes slowly |

## 3. How floc size was computed

| Step | The paper (§2.2) | This project |
|---|---|---|
| Size measure | Mean diameter from the volume distribution | Same (volume-weighted mean) |
| Spike removal | "Spikes of 40% or greater across consecutive size bins" in the 5 smallest and 5 largest bins | Same rule, applied to isolated spikes (one bin at least 40% above its neighbours) |
| Low-quality optics | Not stated | Minutes with transmission below 0.1 (saturated sensor) dropped; 0.1 to 0.3 flagged |
| Biofouling | Instruments cleaned; not modelled | Bursts within 3 days before a cleaning flagged, not dropped |
| Typical floc size | Fig. 1: Summer about 80 to 100, Winter about 70, Spring 100 to 200 µm | Medians: Summer 83, Winter 62, Spring 106 µm (consistent) |

## 4. Features

| Feature | Paper | This project | How it is computed here |
|---|---|---|---|
| u_b (waves) | ✔ | ✔ | From the ADV velocity spectrum in the wave band; checked against linear wave theory (r ≈ 0.95) |
| ū (current) | ✔ | ✔ | Burst-mean current along the main tidal axis, + = flood (checked against the rising tide) |
| ū₄ (lagged current) | ✔ | ✔ | Current from the burst 4 h earlier, matched by time |
| ε (turbulence) | ✔ | ✔ | Fit to the turbulence spectrum (a simpler form of the paper's method) |
| T | ✔ | ✔ | Same-platform CTD |
| S | ✔ | ✔ | P1 CTD |
| Chl-a | ✔ | ✘ | Not available |
| 3 absorption ratios | ✔ | ✘ | Not available |
| c̄ (SSC) | ✔ | ✘ (proxy tested separately) | n/a |
| **Total** | **11** | **6** | |

## 5. Regime split

Same rule as the paper: over each 12-hour window, is sediment concentration better explained by
the waves (R) or by the lagged tide (A)? Mixed (M) if neither is better by 20%.

| Season | Paper R / A / M | This project R / A / M (labelled bursts) |
|---|---|---|
| Summer | 40% / 45% / 15% | 11% / 76% / 14% |
| Winter | 47% / 45% / 7% | 26% / 66% / 8% |
| Spring | 29% / 57% / 14% | 24% / 61% / 15% |

This site and height are much more advection-dominated than the paper's, especially in summer.
The resuspension groups are therefore small (42 to 84 rows) and their results are uncertain.

## 6. Method

| | The paper | Class paper | This project |
|---|---|---|---|
| Models | LASSO + RFECV | Random Forest, SVR | All three |
| Scoring | No held-out test; Table 1 r² is the regression fit | Random 70/30 split of hourly data | Contiguous multi-day blocks held out, with a 12 h gap between training and test data |
| Fitted separately by | Season and regime | All data together | Season and regime, plus all seasons pooled |
| Additional test | n/a | n/a | Train on two seasons, predict the third |
| Feature elimination | Drop a feature if removing it lowers r² by less than 0.02 | RF importance, keep the top 4 | Same as the paper |

## 7. LASSO results by season and regime

The paper's r² is in-sample (Table 1). Shown alongside: this project's in-sample r² (same type)
and its best out-of-sample r² (best of LASSO, RF and SVR on held-out time blocks).
Signs: (+) larger flocs when the feature increases, (−) smaller.

| Season, regime | Paper: selected features (−Δr²) | Paper r² (in-sample) | This project: selected features | In-sample r² | Best out-of-sample r² |
|---|---|---|---|---|---|
| **Summer R** | u_b (−) .38, ū₄ (+) .13 | 0.51 | none selected | 0.00 | −0.02 |
| **Summer A** | u_b (−) .16, ū (+) .02 | 0.15 | none selected | 0.00 | −0.22 |
| **Summer M** | ū₄ (+) .26, u_b (−) .17, ū (+) .06, S (+) .03 | 0.33 | u_b (−) .10, ū (+) .07, ū₄ (−) .03 | 0.22 | −0.09 |
| **Winter R** | u_b (−) .26, ū₄ (+) .10 | 0.45 | none selected | 0.00 | −0.11 |
| **Winter A** | c̄ (−) .09, ū₄ (+) .07, u_b (−) .03, a450/a676 (+) .03 | 0.50 | ū₄ (+) .17, S (+) .05 | 0.30 | **0.39** |
| **Winter M** | u_b (−) .17, ū (−) .06, ū₄ (+) .04, a676/a650, Chl-a | 0.65 | too few rows (27) | n/a | n/a |
| **Spring R** | **T (+) .42, Chl-a (+) .23**, u_b (−) .07 | 0.46 | u_b (−) .32, ū₄ (+) .10, ū (−) .04 | 0.79* | **0.61*** |
| **Spring A** | T (+) .11, Chl-a (+) .09, a450/a676, c̄ | 0.15 | ū₄ (+) .09, S (+) .07 | 0.18 | −0.15 |
| **Spring M** | Chl-a (+) .11, T (+) .11, c̄ (+) .04, u_b (−) .03 | 0.25 | too few rows (28) | n/a | n/a |

\* Only 43 rows over 8 days, so the uncertainty is wide (95% CI 0.14 to 0.74).
"None selected": the LASSO set every coefficient to zero, because no feature helped predict
held-out days.

- Where there is enough data, the same physical features appear with the same signs: waves (−),
  lagged tide (+). Winter A and Spring R match most closely.
- The paper's spring subsets, where biology dominates, cannot be reproduced without those
  measurements.
- Several resuspension subsets select no features, partly because they are small.

## 8. Feature importance

| Feature | Paper (Table 1 and text) | Class paper (RF importance for d50) | This project (RF permutation importance, all seasons) |
|---|---|---|---|
| u_b (waves) | Most reliable, negative | 2nd (0.06) | 1st or 2nd, negative |
| ū₄ (lagged tide) | Consistent, positive | not used | 1st or 2nd, positive |
| ū (current) | Minor | last (0.03) | Minor |
| T | Important in spring only (biology proxy) | joint 3rd (0.05) | Weak within a season; matters only when seasons are pooled |
| S | Marginal | 1st (0.72) | Weak within a season; matters only when seasons are pooled |
| ε | Not selected | not used | Near zero |
| Chl-a, absorption | Important in spring | weak | not available |

This project agrees with the paper (waves and lagged tide) and not with the class paper's
salinity-first ranking. That ranking is probably an artefact: salinity changes slowly over each
deployment, so with a random split it tells the model which week a sample came from.

## 9. Effect of the scoring method on r²

Same data and features, all seasons pooled, scored four ways:

| Scoring method | Model | r² |
|---|---|---|
| In-sample fit (the paper's method) | LASSO | 0.43 |
| Random 70/30 split (the class paper's method) | Random Forest | 0.64 |
| Held-out time blocks | Random Forest | **0.34** |
| Train on two seasons, predict the third | Random Forest | **−0.1 to −4.6** |

Within a single season, held-out time blocks give 0 or below for every model.

The paper's 0.15 to 0.65 and the class paper's 0.81 are correct for their methods; those methods
measure an easier task. Scored the paper's way, this project falls in the lower half of the
paper's range, as expected with 6 of its 11 inputs.

## 10. Conclusions compared

| Topic | The paper | This project |
|---|---|---|
| Waves break flocs | Yes, strongest in resuspension periods | Confirmed in Summer and Winter (r = −0.27, −0.30) and in the Spring resuspension subset; near zero across Spring as a whole (r = −0.02) |
| The lagged tide brings larger flocs from upstream | Yes | Confirmed in Winter and Spring (r = +0.43, +0.37); opposite sign in Summer at this site (r = −0.23) |
| Biology matters in spring | Yes (T, Chl-a) | Cannot be tested: no biology data |
| Turbulence (ε) predicts floc size | No | Agrees: no improvement |
| Salinity | Marginal | Agrees with the paper; disagrees with the class paper |
| Can floc size be predicted? | Not addressed | Only weakly from physics: about a third of the variation across seasons, mostly the seasonal level; little within a season; no skill for an unseen season |

## 11. Implications

1. The pipeline reproduces the paper's physical findings, which supports the way the features and
   the target are computed.
2. A forecasting model based only on physics is not yet reliable. It follows the tide-to-tide
   changes but misses multi-day shifts in floc size, which are probably driven by biology and by
   where the sediment comes from.
3. For a model that stays accurate over years, new data will help more than a new algorithm:
   biology and sediment sensors, more deployments, or occasional direct floc-size measurements to
   correct the model's baseline.
