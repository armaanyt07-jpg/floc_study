# Published paper vs our project — side by side

**Paper:** Egan et al. (2022), "On the Variability of Floc Characteristics in a Shallow Estuary",
JGR Oceans. Called "the paper" below.
**Class paper:** Egan's CS229 report (Random Forest + SVR). Included where it matters.
**Ours:** this project (`outputs/report.md` has the full detail).

---

## 0. The 30-second version

| | The paper | Us |
|---|---|---|
| Goal | Understand *what drives* floc size (an explanation study) | *Predict* floc size from physics only (a forecasting study) |
| Inputs | Physics + biology + sediment concentration (11 candidates) | Physics only (6 features) |
| How r² was measured | On the same data the model was fitted to ("in-sample") | On time periods the model never saw ("out-of-sample") |
| Headline r² | 0.15–0.65 | In-sample 0.17–0.43 (comparable to the paper); out-of-sample 0.34 pooled, ≤ 0 within a single season |
| Main drivers found | Waves break flocs (−), lagged tide brings bigger flocs (+), biology in spring | **Same physical drivers**; biology can't be tested (no data) |
| Verdict | Explains part of the variability | Agrees with the paper's physics, but physics alone is **not enough to forecast** floc size reliably |

**In one sentence:** we reproduce the paper's physics findings, but its r² numbers answer
"how well does the model fit this data?", while ours answer "how well does it predict new
data?". The second question is much harder, and the answer is "only weakly".

---

## 1. Plain-language glossary

| Term | Meaning |
|---|---|
| **Floc / floc size (d)** | Mud particles stick together into fluffy clumps ("flocs"). Their size (µm) controls how fast mud settles. This is what we predict. |
| **LISST** | Laser instrument that measures the particle size distribution every minute. |
| **ADV** | Acoustic current meter, 8 samples/s, 15 cm above the bed. Gives the wave and current features. |
| **CTD** | Temperature and salinity sensor. |
| **u_b** | Wave orbital velocity: how hard waves shake the water near the bed. Strong waves can break flocs. |
| **ū (u_bar)** | Mean tidal current (+ = flood tide, water coming in). |
| **ū₄ (u_bar_4)** | The tidal current 4 hours earlier. The paper found sediment arriving now was set in motion about 4 h ago upstream. |
| **ε (epsilon)** | Turbulence dissipation: how much small-scale stirring there is. |
| **T, S** | Water temperature and salinity. |
| **Chl-a, absorption ratios** | Biology measures (algae, organic matter). The paper had them; we don't. |
| **c̄ (SSC)** | Suspended sediment concentration (how muddy the water is). The paper had a calibrated version; we don't. |
| **Regime R / A / M** | Resuspension (mud stirred up locally by waves) / Advection (mud carried in by the tide) / Mixed. |
| **r²** | Share of the ups and downs in floc size the model explains. 1 = perfect, 0 = no better than always guessing the average, **negative = worse than guessing the average**. |
| **In-sample vs out-of-sample** | In-sample = scored on the data used to build the model (easy, optimistic). Out-of-sample = scored on data held back (honest, harder). |
| **Random split vs time-blocked split** | Random split: test hours are scattered among training hours, so the model has seen the hour before and after each test hour (it "peeks"). Time-blocked: whole multi-day stretches are held out, closer to real forecasting. |
| **LASSO + RFECV** | A linear model that automatically switches off unhelpful features, followed by a step that removes features one at a time and keeps the best set. The paper's method. |
| **Random Forest (RF), SVR** | Two flexible non-linear models (the class paper's methods). |

---

## 2. Data and setup

| | The paper | Us | Does it matter? |
|---|---|---|---|
| Location | South SF Bay shoals, platforms "P1 / P1O" | Same campaigns, platform **P2** (the public dataset) | Some. A different spot means slightly different sediment supply. |
| Seasons | Summer 2018, Winter 2019, Spring 2019 | Same | — |
| LISST height | **15 cm** above bed | **35 cm** above bed | Some. The paper says 15 vs 45 cm looked similar, so probably minor. |
| LISST sampling | Once per hour | Every minute, averaged over each 14-min ADV burst | Ours is less noisy per data point. |
| Platform layout | LISST ~30 m from the current meters | Same platform | — |
| Rows used per season (all regimes) | Summer 443, Winter 570, Spring 331 (sum of Table 1 N) | Summer 427, Winter 406, Spring 287 | Similar size. |
| Biology data (Chl-a, absorption) | Yes | **No.** Not in the public archive; we checked both linked datasets. | **Yes, a lot**, especially in spring. |
| Calibrated SSC | Yes | No (only an uncalibrated echo-strength proxy, tested separately) | Moderate. |
| Salinity source | CTD on the same platform | CTD at P1, 1.2 km away (the P2 salinity sensor failed) | Minor. Salinity changes slowly. |

---

## 3. How the target (floc size) was computed

| Step | The paper (§2.2) | Us |
|---|---|---|
| Size measure | Mean diameter from the volume distribution | Same (volume-weighted mean) |
| Spike removal | "Spikes ≥40% across consecutive bins in the 5 smallest / 5 largest bins" | Same rule, read as *isolated* spikes (one bin ≥40% above its neighbours) |
| Low-quality optics | Not stated | Dropped minutes with transmission < 0.1 (saturated sensor). Flagged 0.1–0.3. |
| Biofouling | Instruments cleaned; not modelled | Bursts within 3 days before a cleaning are flagged (not dropped) |
| Resulting typical floc size | Fig. 1: Summer ~80–100, Winter ~70, Spring ~100–200 µm | Medians: Summer 83, Winter 62, Spring 106 µm (**consistent**) |

> Note: our first spike rule also cut everything beyond a spike, which removed real large flocs and
> pushed Spring down to ~48 µm. We corrected it to match the paper. See `report.md` §8.

---

## 4. Features

| Feature | Paper | Us | How we computed it |
|---|---|---|---|
| u_b (waves) | ✔ | ✔ | From the ADV velocity spectrum in the wave band; cross-checked with wave theory (r ≈ 0.95) |
| ū (current) | ✔ | ✔ | Burst-mean current along the main tidal axis, + = flood (verified against the rising tide) |
| ū₄ (lagged current) | ✔ | ✔ | Current from the burst 4 h earlier, matched by time |
| ε (turbulence) | ✔ | ✔ | Turbulence spectrum fit (simplified version of the paper's method) |
| T | ✔ | ✔ | Same-platform CTD |
| S | ✔ | ✔ | P1 CTD |
| Chl-a | ✔ | ✘ | Not available |
| 3 absorption ratios | ✔ | ✘ | Not available |
| c̄ (SSC) | ✔ | ✘ (proxy tested separately) | — |
| **Total** | **11** | **6** | |

---

## 5. Regime split (resuspension / advection / mixed)

Same rule as the paper: over each 12-hour window, is sediment concentration better explained
by the waves (R) or by the lagged tide (A)? Mixed (M) if neither wins by 20%.

| Season | Paper R / A / M | Ours R / A / M (labelled bursts) |
|---|---|---|
| Summer | 40% / 45% / 15% | 11% / 76% / 14% |
| Winter | 47% / 45% / 7% | 26% / 66% / 8% |
| Spring | 29% / 57% / 14% | 24% / 61% / 15% |

**Difference:** our site/height looks much more "advection" (tide-carried mud) than the paper's,
especially in summer. This leaves our resuspension groups small (42–84 rows), so their results
are fragile.

---

## 6. Method

| | The paper | Class paper | Us |
|---|---|---|---|
| Models | LASSO + RFECV | Random Forest, SVR | All three |
| Data split for scoring | Not a held-out test. Table 1 r² is the regression fit itself. | Random 70/30 split of hourly data | Contiguous multi-day blocks held out, with 12 h gaps removed between train and test |
| Fit separately by | Season × regime | All data together | Season × regime, plus all seasons pooled |
| Extra stress test | — | — | Train on 2 seasons, predict the 3rd |
| Feature elimination rule | Drop if removing it lowers r² by < 0.02 | RF importance, keep top 4 | Same as the paper |

---

## 7. Results side by side: LASSO, season × regime

"Paper r²" is in-sample (from the paper's Table 1). For a fair comparison we show **our in-sample
r²** (same type) and **our honest out-of-sample r²** (best of LASSO/RF/SVR on held-out time blocks).
Signs in brackets: (+) bigger flocs when the feature goes up, (−) smaller.

| Season · Regime | Paper: selected features (−Δr²) | Paper r² (in-sample) | Our selected features | Our r² in-sample | Our best r² out-of-sample |
|---|---|---|---|---|---|
| **Summer · R** | u_b (−) .38, ū₄ (+) .13 | 0.51 | none survived | 0.00 | −0.02 |
| **Summer · A** | u_b (−) .16, ū (+) .02 | 0.15 | none survived | 0.00 | −0.22 |
| **Summer · M** | ū₄ (+) .26, u_b (−) .17, ū (+) .06, S (+) .03 | 0.33 | u_b (−) .10, ū (+) .07, ū₄ (−) .03 | 0.22 | −0.09 |
| **Winter · R** | u_b (−) .26, ū₄ (+) .10 | 0.45 | none survived | 0.00 | −0.11 |
| **Winter · A** | c̄ (−) .09, ū₄ (+) .07, u_b (−) .03, a450/a676 (+) .03 | 0.50 | ū₄ (+) .17, S (+) .05 | 0.30 | **0.39** |
| **Winter · M** | u_b (−) .17, ū (−) .06, ū₄ (+) .04, a676/a650, Chl-a | 0.65 | too few rows (27) | — | — |
| **Spring · R** | **T (+) .42, Chl-a (+) .23**, u_b (−) .07 | 0.46 | u_b (−) .32, ū₄ (+) .10, ū (−) .04 | 0.79* | **0.61*** |
| **Spring · A** | T (+) .11, Chl-a (+) .09, a450/a676, c̄ | 0.15 | ū₄ (+) .09, S (+) .07 | 0.18 | −0.15 |
| **Spring · M** | Chl-a (+) .11, T (+) .11, c̄ (+) .04, u_b (−) .03 | 0.25 | too few rows (28) | — | — |

\* Only 43 rows over 8 days, so the uncertainty is wide (95% CI 0.14–0.74).
"None survived" = the LASSO switched off every feature, because none of them helped predict
held-out days.

**How to read this:**
- Where we have enough data, **the same physical features show up with the same signs**:
  waves (−), lagged tide (+). Winter·A and Spring·R are the clearest matches.
- The paper's subsets where **biology dominates** (all of spring) can't be reproduced, because we
  don't have those measurements.
- Several of our resuspension subsets select nothing, partly because they're small (our site is
  more advection-dominated).

---

## 8. Which features matter most

| Feature | Paper (Table 1 + text) | Class paper (RF importance for d50) | Ours (RF permutation importance, all seasons) |
|---|---|---|---|
| u_b (waves) | **#1 most reliable**, negative | #2 (0.06) | **#1–2**, negative |
| ū₄ (lagged tide) | Consistent positive | not used | **#1–2**, positive |
| ū (current) | Minor | last (0.03) | Minor |
| T | Important **in spring only** (biology proxy) | #4 (0.05) | Weak within a season; matters only when seasons are pooled |
| S | Marginal | **#1 (0.72)** | Weak within a season; matters only when seasons are pooled |
| ε | Not selected | not used | Near zero |
| Chl-a / absorption | Important in spring | weak | not available |

**Takeaway:** we agree with the paper (waves + lagged tide), and **disagree with the class paper**,
whose salinity-first result appears to be an artefact. Salinity changes slowly over the deployment,
so with a random split it acts like a "clock" that tells the model which week a sample came from.

---

## 9. Why our headline numbers look lower: the r² ladder

Same data and features, scored four ways (all seasons pooled, Random Forest):

| How it's scored | r² | Like… |
|---|---|---|
| In-sample LASSO fit (the paper's style) | 0.43 | Grading a student on the homework they copied |
| Random 70/30 split (the class paper's style) | 0.64 | Grading on questions that are near-copies of the homework |
| Held-out time blocks (ours) | **0.34** | Grading on next week's exam |
| Train on two seasons, predict the third (ours) | **−0.1 to −4.6** | Grading on a different subject |

And within a single season, held-out blocks give **≤ 0** for every model.

So the paper's 0.15–0.65 and the class paper's 0.81 are **not wrong**; they measure an easier
thing. If our features are scored the paper's way, we land in the lower half of its range, which
is expected given we have 6 of its 11 inputs.

---

## 10. Conclusions side by side

| Topic | The paper concludes | We find |
|---|---|---|
| Waves break flocs | Yes, strongest in resuspension periods | **Confirmed** (negative u_b effect in every season except where data are thin) |
| Lagged tide brings larger flocs from upstream | Yes | **Confirmed in Winter and Spring**; opposite sign in Summer at our site |
| Biology matters in spring | Yes (T, Chl-a) | Can't test; no biology data. Spring is where our physics-only model is weakest overall. |
| Turbulence (ε) predicts floc size | No | **Agree**: no help |
| Salinity | Marginal | **Agree** with the paper; disagree with the class paper |
| Can floc size be *predicted*? | Not the paper's question | **Only weakly from physics.** About a third of the variance across seasons, mostly via the seasonal level; little within a season; fails for an unseen season. |

---

## 11. What this means for you

1. **The science checks out.** Our pipeline reproduces the paper's physical story, which is a good
   sign that features and target are computed sensibly.
2. **A forecasting model built only on physics is not ready.** It tracks the tide-to-tide ups and
   downs, but misses multi-day shifts in floc size. Those shifts are probably caused by biology and
   by where the mud comes from, which we don't measure.
3. **For a model that lasts years, the biggest wins are new data, not new algorithms:**
   biology/sediment sensors, more deployments, or an occasional real floc-size measurement to
   re-anchor the model.
