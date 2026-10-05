"""Model inputs, estimators and time-blocked evaluation.

Evaluation never uses a random split. The default splitter holds out
contiguous time blocks (sklearn KFold without shuffling on time-sorted rows,
which is what RFECV's default cv=5 does, i.e. the setup EGAN22 Sec. 3.3 most
likely used), plus a 12-h purge so that training rows adjacent to a test
block (autocorrelation, and u_bar_4 which looks 4 h back) are removed.
"""
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import RFECV
from sklearn.linear_model import Lasso, LassoCV
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.svm import SVR

from . import load

CACHE = load.ROOT / "outputs" / "cache" / "features.parquet"

# Physics-only analogue of the EGAN22 candidate set (Sec. 3.3), minus the
# biology/optics features and mean SSC that are not in this dataset.
BASELINE = ["u_b", "u_bar", "u_bar_4", "epsilon", "T", "S"]
TARGET = "d_mean"
LOG_COLS = ("epsilon",)   # log10 for the linear/kernel models (user decision)
PURGE = pd.Timedelta(hours=12)


def load_table(path=CACHE):
    return pd.read_parquet(path)


def make_xy(df, season=None, regime=None, features=BASELINE, target=TARGET,
            block="1D"):
    """Return X, y, groups, frame for QC-passing rows with no missing inputs.

    groups = calendar-day index (used for the bootstrap over blocks).
    No gap filling: rows with any missing feature/target are dropped.
    """
    d = df[df.qc_adv == "ok"]
    if season is not None:
        d = d[d.season.isin([season] if isinstance(season, str) else season)]
    if regime is not None:
        d = d[d.regime == regime]
    d = d.dropna(subset=list(features) + [target]).sort_values("tstart")
    groups = d.tstart.dt.floor(block).factorize()[0]
    return d[list(features)].to_numpy(float), d[target].to_numpy(float), groups, d


# --------------------------------------------------------------------------
# Splitters
# --------------------------------------------------------------------------
def blocked_splits(times, n_splits=5, purge=PURGE):
    """Contiguous blocks over time-sorted rows; train rows within `purge` of
    the test block are dropped. Returns a list of (train_idx, test_idx)."""
    t = pd.to_datetime(pd.Series(times)).reset_index(drop=True)
    assert t.is_monotonic_increasing, "rows must be time-sorted"
    out = []
    for test in np.array_split(np.arange(len(t)), n_splits):
        lo, hi = t[test[0]] - purge, t[test[-1]] + purge
        train = np.where((t < lo) | (t > hi))[0]
        out.append((train, test))
    return out


def blocked_cv(n_splits=5):
    """Kept for compatibility: plain contiguous KFold (no purge)."""
    from sklearn.model_selection import KFold
    return KFold(n_splits=n_splits, shuffle=False)


# --------------------------------------------------------------------------
# Estimators
# --------------------------------------------------------------------------
def _log10_cols(X, idx=()):
    X = np.array(X, float, copy=True)
    idx = list(idx)
    X[:, idx] = np.log10(np.clip(X[:, idx], 1e-12, None))
    return X


def _log_cols(features):
    """Module-level function + kw_args so fitted pipelines can be pickled."""
    idx = [i for i, f in enumerate(features) if f in LOG_COLS]
    return FunctionTransformer(_log10_cols, kw_args={"idx": idx})


def lasso_pipe(features, alpha=0.1):
    return Pipeline([("log", _log_cols(features)), ("scale", StandardScaler()),
                     ("lasso", Lasso(alpha=alpha, max_iter=50000))])


def init_random_forest(seed=0):
    return RandomForestRegressor(n_estimators=500, min_samples_leaf=5,
                                 max_features="sqrt", n_jobs=-1,
                                 random_state=seed)


def svr_search(features, times):
    """SVR (RBF) tuned by an inner time-blocked CV on the training data only.
    Grid includes the class paper's choice (C=2048, epsilon=4)."""
    pipe = Pipeline([("log", _log_cols(features)), ("scale", StandardScaler()),
                     ("svr", SVR(kernel="rbf"))])
    grid = {"svr__C": [1, 10, 100, 1000, 2048], "svr__epsilon": [1, 4, 8],
            "svr__gamma": ["scale", 0.05]}
    return GridSearchCV(pipe, grid, cv=blocked_splits(times, 4), scoring="r2",
                        n_jobs=-1)


# --------------------------------------------------------------------------
# LASSO + RFECV, mirroring EGAN22 Sec. 3.3 / Table 1
# --------------------------------------------------------------------------
def lasso_rfecv(X, y, times, features, min_drop=0.02):
    """1) LassoCV (blocked) picks alpha on all features; 2) RFECV with that
    LASSO (blocked CV, r2); 3) drop features whose removal lowers the
    in-sample LASSO r2 by < 0.02 (EGAN22). Returns dict with selected
    features, in-sample r2, -delta r2 and coefficient sign per feature."""
    splits = blocked_splits(times)
    pre = Pipeline([("log", _log_cols(features)), ("scale", StandardScaler())])
    Z = pre.fit_transform(X)
    alpha = LassoCV(cv=splits, max_iter=50000).fit(Z, y).alpha_
    rfe = RFECV(Lasso(alpha=alpha, max_iter=50000), cv=splits, scoring="r2",
                min_features_to_select=1).fit(Z, y)
    sel = [i for i, k in enumerate(rfe.support_) if k]

    def r2_of(cols):
        if not cols:
            return 0.0
        m = Lasso(alpha=alpha, max_iter=50000).fit(Z[:, cols], y)
        return r2_score(y, m.predict(Z[:, cols]))

    while len(sel) > 1:
        base = r2_of(sel)
        drops = {c: base - r2_of([k for k in sel if k != c]) for c in sel}
        worst = min(drops, key=drops.get)
        if drops[worst] >= min_drop:
            break
        sel.remove(worst)
    base = r2_of(sel)
    m = Lasso(alpha=alpha, max_iter=50000).fit(Z[:, sel], y)
    rows = []
    for j, c in enumerate(sel):
        rows.append(dict(feature=features[c],
                         neg_delta_r2=base - r2_of([k for k in sel if k != c]),
                         sign="+" if m.coef_[j] > 0 else ("-" if m.coef_[j] < 0 else "0")))
    rows.sort(key=lambda r: -r["neg_delta_r2"])
    return dict(alpha=alpha, selected=[features[c] for c in sel],
                r2_insample=base if sel else 0.0, table=rows,
                rfecv_support=[features[i] for i, k in enumerate(rfe.support_) if k])


# --------------------------------------------------------------------------
# Out-of-fold evaluation
# --------------------------------------------------------------------------
def oof_predict(make_model, X, y, splits):
    """Out-of-fold predictions; make_model(train_idx) -> unfitted estimator."""
    pred = np.full(len(y), np.nan)
    for tr, te in splits:
        m = make_model(tr)
        m.fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    return pred


def scores(y, p, groups, n_boot=1000, seed=0):
    """Pooled OOF r2 and RMSE, with a 95% bootstrap CI resampling whole days."""
    ok = np.isfinite(p)
    y, p, groups = y[ok], p[ok], groups[ok]
    r2, rmse = r2_score(y, p), np.sqrt(mean_squared_error(y, p))
    rng = np.random.default_rng(seed)
    ug = np.unique(groups)
    idx_by_g = {g: np.where(groups == g)[0] for g in ug}
    boots = []
    for _ in range(n_boot):
        idx = np.concatenate([idx_by_g[g] for g in rng.choice(ug, len(ug))])
        if np.var(y[idx]) > 0:
            boots.append(r2_score(y[idx], p[idx]))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return dict(r2=r2, r2_lo=lo, r2_hi=hi, rmse=rmse, n=int(ok.sum()))


def persistence(frame):
    """Previous burst's d (1 h earlier) as prediction: a with-history
    reference only; a standalone future entry would not have it."""
    s = frame.set_index("hour")[TARGET]
    return frame["hour"].sub(pd.Timedelta(hours=1)).map(s).to_numpy(float)
