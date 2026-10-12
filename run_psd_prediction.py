"""Predict the whole floc size distribution (32 LISST bins), not just one size number.

    ven/bin/python run_psd_prediction.py              # tables + figures
    ven/bin/python run_psd_prediction.py --no-figures

Needs outputs/cache/features.parquet and outputs/cache/psd_bins.parquet (build_psd.py).

Models (src/psd.py): the average training curve (baseline), a linear model on the
first 3 principal components of the curve shape, and one random forest that
predicts all 32 bins at once. Same 6 physics features and the same hold-out
methods as run_random_forest.py:
  time-blocked          whole multi-day stretches held out, 12 h gap
  leave-one-season-out  train on two seasons, test on the third

Scores (per held-out burst, then averaged):
  W1 skill      how much closer the predicted curve is to the measured one than the
                baseline curve is (0 = no better than the baseline, 1 = perfect)
  size factor   exp(mean W1): typical factor by which the predicted curve is
                shifted along the size axis (1.00 = perfect)
  r2 d10/d50/d90  r2 of the 10th/50th/90th volume percentile read off the curves
"""
import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from src import load, models as M, psd  # noqa: E402

warnings.filterwarnings("ignore")

SEASONS = list(load.SEASONS)
TABLES = ROOT / "outputs" / "tables"
FIGS = ROOT / "outputs" / "figures"


def season_data(df, season, cols):
    """X, volume fractions, day groups and frame for one season (or a list)."""
    X, _, groups, fr = M.make_xy(df, season=season, features=M.BASELINE, target="d_mean")
    F = psd.volume_fractions(fr[cols].to_numpy())
    ok = np.isfinite(F).all(1)
    return X[ok], F[ok], groups[ok], fr[ok]


def evaluate(df, cols, dias):
    rows, pooled = [], None
    factories = psd.model_factories(M.BASELINE)

    def add(data, method, F, curves, groups):
        for name, P in curves.items():
            s = psd.curve_scores(F, P, curves["mean PSD"], dias, groups)
            rows.append({"data": data, "hold-out method": method, "model": name, **s})

    # 1) time-blocked, each season and pooled
    for season in SEASONS + ["All seasons"]:
        ss = SEASONS if season == "All seasons" else season
        X, F, groups, fr = season_data(df, ss, cols)
        splits = M.blocked_splits(fr.tstart, 15 if season == "All seasons" else 5)
        curves = {n: psd.oof_curves(f, X, F, splits) for n, f in factories.items()}
        add(season, "time-blocked", F, curves, groups)
        if season == "All seasons":
            pooled = (F, curves, fr)

    # 2) leave one season out
    for test in SEASONS:
        Xtr, Ftr, _, _ = season_data(df, [s for s in SEASONS if s != test], cols)
        Xte, Fte, gte, _ = season_data(df, test, cols)
        curves = {n: f().fit(Xtr, Ftr).predict(Xte) for n, f in factories.items()}
        add(f"predict {test}", "leave-one-season-out", Fte, curves, gte)
    return pd.DataFrame(rows), pooled


def make_figures(pooled, dias):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # same look as scripts/make_figures.py; model colours = categorical slots 1, 2
    INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    COL = {"linear (PCA)": "#2a78d6", "RF (all bins)": "#eb6834"}
    plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF,
                         "axes.edgecolor": INK2, "axes.labelcolor": INK, "text.color": INK,
                         "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True,
                         "grid.color": GRID, "grid.linewidth": 0.8, "font.size": 9,
                         "axes.spines.top": False, "axes.spines.right": False})
    F, curves, fr = pooled
    FIGS.mkdir(parents=True, exist_ok=True)

    # 1) measured vs predicted curves for a small-, typical- and large-floc burst
    d50 = psd.quantile_diameter(F, dias, 0.5)
    picks = [np.argsort(d50)[int(q * (len(d50) - 1))] for q in (0.1, 0.5, 0.9)]
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.4), sharey=True)
    for ax, i, title in zip(axes, picks, ("small flocs (10th pct of d50)",
                                          "typical (median d50)",
                                          "large flocs (90th pct of d50)")):
        ax.plot(dias, 100 * F[i], color=INK, lw=2, label="measured")
        ax.plot(dias, 100 * curves["mean PSD"][i], color=INK2, lw=1.5, ls="--",
                label="mean PSD (baseline)")
        for name, c in COL.items():
            ax.plot(dias, 100 * curves[name][i], color=c, lw=2, label=name)
        ax.set_xscale("log")
        ax.set_title(f"{title}\n{fr.season.iloc[i]} {fr.tstart.iloc[i]:%d %b %Y %H:%M}",
                     fontsize=9)
        ax.set_xlabel("diameter (µm)")
    axes[0].set_ylabel("volume fraction per bin (%)")
    axes[0].legend(frameon=False, fontsize=8, loc="upper left")
    fig.suptitle("Held-out bursts (time-blocked, all seasons pooled)", fontsize=10)
    fig.tight_layout()
    fig.savefig(FIGS / "psd_examples.png", dpi=150)
    plt.close(fig)

    # 2) r2 of each bin's volume fraction
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.axhline(0, color=INK2, lw=1)
    rows = {"diameter_um": dias}
    for name, c in COL.items():
        r2 = psd.bin_r2(F, curves[name])
        rows[name] = r2
        ax.plot(dias, r2, color=c, lw=2, marker="o", ms=4, label=name)
    ax.set_xscale("log")
    lo = np.nanmin([rows[n] for n in COL]) - 0.05
    ax.set_ylim(max(-1, lo), 1)
    ax.set_xlabel("diameter (µm)")
    ax.set_ylabel("r² of the bin's volume fraction" + (" (cut at −1)" if lo < -1 else ""))
    ax.set_title("Which sizes are predictable (time-blocked, all seasons pooled)",
                 fontsize=10)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGS / "psd_bin_r2.png", dpi=150)
    plt.close(fig)
    pd.DataFrame(rows).round(3).to_csv(TABLES / "psd_bin_r2.csv", index=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--no-figures", action="store_true", help="skip the figures")
    args = ap.parse_args()

    table, dias = psd.load_psd()
    cols = psd.bin_cols(len(dias))
    df = M.load_table().merge(table, on=["season", "tstart"], how="left")

    out, pooled = evaluate(df, cols, dias)
    show = out[["data", "hold-out method", "model", "n", "W1_skill", "W1_skill_lo",
                "W1_skill_hi", "size_factor", "r2_d10", "r2_d50", "r2_d90", "r2_d_mean"]]
    TABLES.mkdir(parents=True, exist_ok=True)
    path = TABLES / "psd_scores.csv"
    show.round(3).to_csv(path, index=False)
    pd.set_option("display.width", 220, "display.max_columns", 20)
    print(f"Full size-distribution prediction, features {M.BASELINE}, "
          f"{len(dias)} bins ({dias[0]:.1f} to {dias[-1]:.0f} um)\n")
    print(show.round(2).to_string(index=False))
    print(f"\nSaved -> {path.relative_to(ROOT)}")
    if not args.no_figures:
        make_figures(pooled, dias)
        print("Figures -> outputs/figures/psd_examples.png, psd_bin_r2.png")


if __name__ == "__main__":
    main()
