"""Full particle size distribution (PSD) prediction helpers.

The main pipeline predicts one number per burst (mean diameter, d50 or the
variance). The title of Egan's CS229 report refers to predicting particle size
distributions, so this module predicts the whole burst-averaged LISST curve
(32 log-spaced size bins) and scores it as a curve.

Representation: each curve is turned into volume fractions (bins sum to 1), so
the models learn the *shape* of the distribution, not the total concentration.

Models
- mean PSD:      average training curve (baseline, no inputs)
- RF (all bins): one multi-output random forest predicting all 32 fractions.
                 A forest averages training curves in each leaf, so every
                 prediction is a valid distribution (non-negative, sums to 1).
- linear (PCA):  centred log-ratio transform -> 3 principal components
                 (fitted on the training fold) -> ridge regression from the
                 standardised features -> back-transform to fractions.

Scores
- W1: Wasserstein-1 ("earth mover's") distance between predicted and observed
  curves on the log-diameter axis. exp(W1) reads as "the curve is off by a
  typical size factor of ..." (1.00 = perfect).
- W1 skill: 1 - mean W1(model) / mean W1(mean PSD). 0 = no better than the
  baseline curve, 1 = perfect.
- r2 of d10, d50, d90 read off the predicted curves.
"""
import json

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from . import load, models as M

PSD_CACHE = load.ROOT / "outputs" / "cache" / "psd_bins.parquet"
DIAS_CACHE = load.ROOT / "outputs" / "cache" / "psd_dias.json"
QUANTILES = {"d10": 0.10, "d50": 0.50, "d90": 0.90}
CLR_FLOOR = 1e-4     # added to fractions before the log-ratio (empty bins)
N_PCS = 3


def bin_cols(n):
    return [f"b{i:02d}" for i in range(n)]


def load_psd(path=None, dias_path=None):
    """Burst-averaged PSD table (season, tstart, b00..bNN) and bin diameters (um)."""
    path, dias_path = path or PSD_CACHE, dias_path or DIAS_CACHE
    return pd.read_parquet(path), np.asarray(json.loads(dias_path.read_text()), float)


def save_psd(table, dias, path=None, dias_path=None):
    path, dias_path = path or PSD_CACHE, dias_path or DIAS_CACHE
    table.to_parquet(path)
    dias_path.write_text(json.dumps([float(d) for d in dias]))


# --------------------------------------------------------------------------
# Curve arithmetic
# --------------------------------------------------------------------------
def volume_fractions(V):
    """Rows of volume concentration -> fractions summing to 1 (NaN bins = 0,
    the same convention as features.psd_stats)."""
    v = np.where(np.isnan(V), 0.0, np.asarray(V, float))
    v = np.clip(v, 0.0, None)
    tot = v.sum(1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        return v / tot


def mean_diameter(F, dias):
    return (F * dias).sum(1)


def quantile_diameter(F, dias, q):
    """Diameter below which a fraction q of the volume lies, interpolated in
    log d on the cumulative curve (same method as features.psd_stats d50)."""
    cum = np.cumsum(F, 1)
    logd = np.log(dias)
    return np.array([np.exp(np.interp(q, c, logd)) for c in cum])


def wasserstein_log(F, G, dias):
    """Row-wise Wasserstein-1 distance between two sets of curves on the
    ln(d) axis: integral of |CDF_F - CDF_G| d ln(d)."""
    dx = np.diff(np.log(dias))
    diff = np.abs(np.cumsum(F, 1) - np.cumsum(G, 1))[:, :-1]
    return (diff * dx).sum(1)


def clr(F):
    L = np.log(F + CLR_FLOOR)
    return L - L.mean(1, keepdims=True)


def inv_clr(Z):
    """Inverse of clr(): F + floor is proportional to exp(Z) and F sums to 1,
    so F = (1 + n*floor) * softmax(Z) - floor (clipped at 0, renormalised)."""
    E = np.exp(Z - Z.max(1, keepdims=True))
    S = E / E.sum(1, keepdims=True)
    F = np.clip((1 + CLR_FLOOR * Z.shape[1]) * S - CLR_FLOOR, 0, None)
    return F / F.sum(1, keepdims=True)


# --------------------------------------------------------------------------
# Models (fit on X, F; predict curves)
# --------------------------------------------------------------------------
class MeanPSD:
    """Baseline: the average training curve, whatever the inputs."""

    def fit(self, X, F):
        self.f_ = F.mean(0)
        return self

    def predict(self, X):
        return np.tile(self.f_, (len(X), 1))


class ForestPSD:
    """Multi-output random forest on the fractions (repo's RF settings)."""

    def __init__(self, seed=0):
        self.seed = seed

    def fit(self, X, F):
        self.rf_ = M.init_random_forest(self.seed).fit(X, F)
        return self

    def predict(self, X):
        F = np.clip(self.rf_.predict(X), 0, None)
        return F / F.sum(1, keepdims=True)


class LinearPCAPSD:
    """Ridge regression onto the first principal components of the
    centred log-ratio curves; PCA is fitted on the training fold only."""

    def __init__(self, features, n_pcs=N_PCS, alpha=1.0):
        self.features, self.n_pcs, self.alpha = features, n_pcs, alpha

    def fit(self, X, F):
        self.pca_ = PCA(self.n_pcs).fit(clr(F))
        S = self.pca_.transform(clr(F))
        self.reg_ = Pipeline([("log", M._log_cols(self.features)),
                              ("scale", StandardScaler()),
                              ("ridge", Ridge(alpha=self.alpha))]).fit(X, S)
        return self

    def predict(self, X):
        return inv_clr(self.pca_.inverse_transform(self.reg_.predict(X)))


def model_factories(features):
    return {"mean PSD": lambda: MeanPSD(),
            "linear (PCA)": lambda: LinearPCAPSD(features),
            "RF (all bins)": lambda: ForestPSD()}


def oof_curves(make_model, X, F, splits):
    """Out-of-fold predicted curves (rows not in any test block stay NaN)."""
    P = np.full_like(F, np.nan)
    for tr, te in splits:
        P[te] = make_model().fit(X[tr], F[tr]).predict(X[te])
    return P


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------
def curve_scores(F, P, P_base, dias, groups, n_boot=1000, seed=0):
    """W1, W1 skill vs the baseline curves (with a 95% CI from a bootstrap
    over whole days) and r2 of d10/d50/d90 and the mean diameter."""
    ok = np.isfinite(P).all(1) & np.isfinite(P_base).all(1)
    F, P, P_base, groups = F[ok], P[ok], P_base[ok], groups[ok]
    w = wasserstein_log(F, P, dias)
    wb = wasserstein_log(F, P_base, dias)
    out = dict(n=int(ok.sum()), W1_mean=w.mean(), size_factor=np.exp(w.mean()),
               W1_skill=1 - w.mean() / wb.mean())
    rng = np.random.default_rng(seed)
    ug = np.unique(groups)
    idx_by_g = {g: np.where(groups == g)[0] for g in ug}
    boots = []
    for _ in range(n_boot):
        idx = np.concatenate([idx_by_g[g] for g in rng.choice(ug, len(ug))])
        boots.append(1 - w[idx].mean() / wb[idx].mean())
    out["W1_skill_lo"], out["W1_skill_hi"] = np.percentile(boots, [2.5, 97.5])
    for name, q in QUANTILES.items():
        out[f"r2_{name}"] = r2_score(quantile_diameter(F, dias, q),
                                     quantile_diameter(P, dias, q))
    out["r2_d_mean"] = r2_score(mean_diameter(F, dias), mean_diameter(P, dias))
    return out


def bin_r2(F, P):
    """r2 of each bin's volume fraction (bins with no variance -> NaN)."""
    ok = np.isfinite(P).all(1)
    return np.array([r2_score(F[ok, j], P[ok, j]) if np.var(F[ok, j]) > 0 else np.nan
                     for j in range(F.shape[1])])
