"""Task 6 figures: OOF scatter per season/model, RF importance, OOF time series."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import r2_score  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import load  # noqa: E402

OUT = load.ROOT / "outputs"
FIG = OUT / "figures"
FIG.mkdir(parents=True, exist_ok=True)

# reference palette (dataviz skill), first three slots validate all-pairs
SEASON_COL = {"Summer": "#2a78d6", "Winter": "#eb6834", "Spring": "#1baf7a"}
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"figure.facecolor": SURF, "axes.facecolor": SURF,
                     "axes.edgecolor": INK2, "axes.labelcolor": INK, "text.color": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": 0.8, "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False})

oof = pd.read_parquet(OUT / "cache" / "oof_predictions.parquet")
oof = oof[oof.season.isin(load.SEASONS)]
models = ["LASSO+RFECV", "RF", "SVR"]

# 1) scatter: rows = model, cols = season (per-season fits)
fig, axes = plt.subplots(3, 3, figsize=(9, 9), sharex=True, sharey=True)
lim = (20, 200)
for i, m in enumerate(models):
    for j, s in enumerate(load.SEASONS):
        ax = axes[i, j]
        d = oof[(oof.model == m) & (oof.season == s)].dropna()
        # per-season rows only (exclude rows that came from the pooled fit)
        d = d.drop_duplicates(subset=["tstart"], keep="first")
        ax.plot(lim, lim, color=INK2, lw=1, ls="--", zorder=1)
        ax.scatter(d.y, d.pred, s=10, color=SEASON_COL[s], alpha=.6, lw=0, zorder=2)
        ax.text(.04, .93, f"r² = {r2_score(d.y, d.pred):.2f}  (n={len(d)})",
                transform=ax.transAxes, color=INK, fontsize=8.5)
        ax.set_xlim(lim); ax.set_ylim(lim)
        if i == 0:
            ax.set_title(s, color=INK, fontsize=10)
        if j == 0:
            ax.set_ylabel(f"{m}\npredicted d (µm)")
        if i == 2:
            ax.set_xlabel("observed d (µm)")
fig.suptitle("Out-of-fold predictions, time-blocked CV (5 contiguous blocks, 12 h purge)",
             fontsize=10, color=INK)
fig.tight_layout()
fig.savefig(FIG / "scatter_oof_by_season.png", dpi=150)

# 2) RF permutation importance per season
imp = pd.read_csv(OUT / "tables" / "rf_permutation_importance.csv")
feats = imp.feature.unique()
fig, axes = plt.subplots(1, 4, figsize=(11, 3), sharey=True)
for ax, s in zip(axes, list(load.SEASONS) + ["Pooled"]):
    d = imp[imp.season == s].set_index("feature").loc[feats]
    col = SEASON_COL.get(s, "#4a3aa7")
    ax.barh(range(len(feats)), d.perm_importance_r2, color=col, height=.6)
    for k, (v, sg) in enumerate(zip(d.perm_importance_r2, d.corr_sign)):
        ax.text(max(v, 0) + .005, k, sg, va="center", color=INK2, fontsize=8)
    ax.axvline(0, color=INK2, lw=.8)
    ax.set_title(s, fontsize=10)
    ax.set_yticks(range(len(feats)), feats)
    ax.set_xlabel("drop in OOF r² when permuted")
axes[0].invert_yaxis()
fig.suptitle("Random-forest permutation importance (sign = correlation with d)", fontsize=10)
fig.tight_layout()
fig.savefig(FIG / "rf_importance.png", dpi=150)

# 3) OOF time series, RF per season
fig, axes = plt.subplots(3, 1, figsize=(11, 7))
for ax, s in zip(axes, load.SEASONS):
    d = oof[(oof.model == "RF") & (oof.season == s)].drop_duplicates("tstart").sort_values("tstart")
    ax.plot(d.tstart, d.y, color=INK2, lw=1, label="observed")
    ax.plot(d.tstart, d.pred, color=SEASON_COL[s], lw=1.6, label="RF out-of-fold")
    ax.set_ylabel("d (µm)")
    ax.set_title(s, fontsize=10, loc="left")
    ax.legend(loc="upper right", frameon=False, fontsize=8)
fig.tight_layout()
fig.savefig(FIG / "timeseries_rf_oof.png", dpi=150)
print("figures ->", FIG)
