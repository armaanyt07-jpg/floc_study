# Predicting Floc Size in South San Francisco Bay

ML Mini Project, Team 7

Can the size of suspended mud particles ("flocs") be predicted from wave and current
measurements alone? This project builds a Random Forest on public field data from South
San Francisco Bay and compares it with two earlier studies by the same research group:

- **Journal paper:** Egan, G., Chang, G., Manning, A. J., Monismith, S., & Fringer, O. (2022).
  *On the variability of floc characteristics in a shallow estuary.* JGR Oceans, 127,
  e2021JC018343. https://doi.org/10.1029/2021JC018343
- **Class paper:** Egan, G. *Machine learning for predicting sediment particle size
  distributions.* Stanford CS229 project report (Random Forest and SVR).

Floc size controls how fast mud settles (settling speed grows with diameter squared), so it
decides where sediment and the pollutants attached to it end up. It is rarely measured and
varies about threefold within a season.

## Results

| Setup | r² (ours) | Reference |
|---|---|---|
| Class-paper setup (all seasons, random 70/30 split, RF, d50) | 0.60 | Class paper: 0.81 |
| Class-paper SVR (C = 2048, epsilon = 4), d50 | 0.53 | Class paper: 0.76 |
| Our 6 features, all seasons, held-out time blocks | **0.34** (95% CI 0.15 to 0.49) | Accuracy on unseen time periods |
| One season at a time, held-out time blocks | below 0 | No skill within a season |
| Predicting an unseen season | -0.1 to -4.6 | Fails on new conditions |
| LASSO fitted on its own data (journal protocol) | 0.17 to 0.43 | Journal paper: 0.15 to 0.65 |

r² is the share of floc-size variation explained: 1 is perfect, 0 is no better than
guessing the average.

**What drives floc size:** the tidal current 4 hours earlier (larger flocs arrive from
upstream) and wave velocity (waves break flocs apart), matching the journal paper.
Turbulence adds almost nothing, and salinity is weak within a season.

**Why our scores are lower than the papers':** the public archive has no biology sensors
(particle type, chlorophyll), the laser sizer sits at a different height and platform, and a
random split of hourly data lets the model see the neighbours of every test hour. Details in
[outputs/report.md](outputs/report.md) and [outputs/paper_comparison.md](outputs/paper_comparison.md).

## Quick start (live demo)

The cached feature table is included, so the model runs without downloading the raw data.

```bash
python3.12 -m venv ven
ven/bin/pip install -r requirements.txt
ven/bin/python run_random_forest.py
```

`run_random_forest.py` trains the Random Forest, prints our scores next to both papers and
saves `outputs/tables/random_forest_comparison.csv`.
Options: `--trees 32` (class-paper tree count), `--target d50` or `--target sigma2`.

## Full pipeline from raw data

1. **Download the data** (about 800 MB of the 2.5 GB archive, fetched with HTTP range requests
   into `Data/`):

   ```bash
   ven/bin/python download_data.py
   ```

   If the server refuses range requests, download `NonVectrinoData.zip` from
   https://purl.stanford.edu/wv787xr0534 and run `ven/bin/python download_data.py path/to/NonVectrinoData.zip`.

2. **Build the feature table** (about 30 s):

   ```bash
   ven/bin/python build_features.py
   ```

3. **Run the models:**

   ```bash
   ven/bin/python run_random_forest.py                      # main demo
   ven/bin/python scripts/run_all_models.py                 # LASSO, RF, SVR, ablations, robustness (about 3 min)
   ven/bin/python scripts/compare_evaluation_methods.py     # random vs time-blocked vs in-sample
   ven/bin/python scripts/make_figures.py                   # figures in outputs/figures/
   ```

4. **Predict the full size distribution** (all 32 LISST bins instead of one size number).
   Needs the LISST files in `Data/` (`ven/bin/python download_data.py --lisst-only` fetches just those):

   ```bash
   ven/bin/python build_psd.py               # caches the burst-averaged curves in outputs/cache/
   ven/bin/python run_psd_prediction.py      # scores, outputs/tables/psd_scores.csv and two figures
   ven/bin/python -m pytest tests            # unit tests
   ```

## Project layout

```
build_features.py          raw .mat files -> outputs/cache/features.parquet
run_random_forest.py       main demo: Random Forest vs both papers
build_psd.py               LISST curves (32 bins) per burst -> outputs/cache/psd_bins.parquet
run_psd_prediction.py      predicts the whole size distribution and scores it as a curve
download_data.py           fetches only the needed files from the archive
src/
  load.py                  .mat loading, MATLAB time conversion
  features.py              LISST target, wave/current/turbulence features, QC, regimes
  models.py                time-blocked splits, LASSO + RFECV, RF, SVR, scoring
  predict.py               predict one burst with saved models, with training-range checks
  psd.py                   size-distribution curves, models and curve scores
tests/
  test_psd.py              tests for src/psd.py
scripts/
  inspect_raw_data.py      file contents, time ranges, overlap checks
  run_all_models.py        every model, season and regime, ablations, robustness
  compare_evaluation_methods.py   why random splits look better than they are
  make_figures.py          scatter, importance and time-series figures
outputs/
  cache/features.parquet   one row per hourly burst (1,666 rows)
  tables/, figures/        results
  report.md                full methods, results and assumptions
  paper_comparison.md      side by side with the published paper
deliverables/
  Floc_Size_Prediction_Slides.pptx
  Floc_Size_Prediction_Writeup.pdf
  source/                  scripts that rebuild the slides and the PDF
```

## Method in brief

- **Target:** volume-weighted mean floc diameter from the LISST laser sizer, averaged over each
  14-minute burst. Saturated optics (transmission below 0.1) are dropped and isolated
  edge-bin spikes are removed (the journal paper's 40% rule).
- **Features:** wave orbital velocity (from the velocity spectrum, checked against linear wave
  theory), tidal current now and 4 hours earlier, turbulence dissipation, temperature,
  salinity. Gaps are never filled.
- **Evaluation:** contiguous multi-day blocks held out with a 12-hour gap, plus
  leave-one-season-out, alongside each paper's own protocol. Day-level bootstrap intervals.

All assumptions and data issues found along the way are listed in
[outputs/report.md](outputs/report.md), section 8.

## Rebuilding the deliverables

```bash
ven/bin/python deliverables/source/build_writeup.py
npm install pptxgenjs && node deliverables/source/build_slides.js
```

The committed `.pptx` is the final version. A rebuild produces the same slides with Office's
default colour theme.

## Data and licence

Field data: Egan, G., Cowherd, M., Scheu, K., Spada, F., Manning, A., Jones, C., Chang, G.,
Fringer, O., & Monismith, S. (2019). *South San Francisco Bay boundary layer and sediment dynamics
field data.* Stanford Digital Repository. https://purl.stanford.edu/wv787xr0534.
Collected under NSF award OCE-1736668.

The data are licensed under
[CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/). The derived feature table
`outputs/cache/features.parquet` and the result tables in `outputs/` are shared under the same
licence.
