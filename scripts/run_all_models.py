"""Task 5: LASSO+RFECV, RF, SVR with time-blocked evaluation, baselines,
ablations, leave-one-season-out, noise robustness, final pooled models."""
import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import load, models as M  # noqa: E402

warnings.filterwarnings("ignore")
OUT = load.ROOT / "outputs"
TAB = OUT / "tables"
(OUT / "models").mkdir(parents=True, exist_ok=True)
df = M.load_table()
F = M.BASELINE
MIN_N, MIN_DAYS = 40, 5


def lasso_factory(X, y, times, feats):
    """In-fold LASSO+RFECV: selection is redone on each training fold."""
    def make(tr):
        res = M.lasso_rfecv(X[tr], y[tr], times[tr], feats)
        cols = [feats.index(f) for f in res["selected"]]
        pipe = M.lasso_pipe([feats[c] for c in cols], res["alpha"])
        return _Sub(pipe, cols)
    return make


class _Sub:
    """Wrap an estimator so it only sees a column subset."""
    def __init__(self, est, cols):
        self.est, self.cols = est, cols

    def fit(self, X, y):
        self.est.fit(X[:, self.cols], y)
        return self

    def predict(self, X):
        return self.est.predict(X[:, self.cols])


def evaluate(frame, X, y, groups, feats, splits, which=("lasso", "rf", "svr")):
    times = frame.tstart.to_numpy()
    res = {}
    if "lasso" in which:
        res["LASSO+RFECV"] = M.oof_predict(lasso_factory(X, y, times, feats), X, y, splits)
    if "rf" in which:
        res["RF"] = M.oof_predict(lambda tr: M.init_random_forest(), X, y, splits)
    if "svr" in which:
        res["SVR"] = M.oof_predict(lambda tr: M.svr_search(feats, times[tr]), X, y, splits)
    res["train mean"] = M.oof_predict(lambda tr: _Mean(), X, y, splits)
    res["persistence (1 h)"] = M.persistence(frame)
    return {k: M.scores(y, p, groups) | {"pred": p} for k, p in res.items()}


class _Mean:
    def fit(self, X, y):
        self.m = y.mean()
        return self

    def predict(self, X):
        return np.full(len(X), self.m)


rows, lasso_tables, oof_store = [], [], []

# ---------------------------------------------------------------- per season / regime
subsets = [(s, r) for s in load.SEASONS for r in (None, "R", "A", "M")]
subsets.append((list(load.SEASONS), None))
for s, r in subsets:
    sname = "Pooled" if isinstance(s, list) else s
    X, y, g, fr = M.make_xy(df, season=s, regime=r)
    rname = r or "all"
    ndays = len(np.unique(g))
    if len(y) < MIN_N or ndays < MIN_DAYS:
        rows.append(dict(season=sname, regime=rname, model="(skipped)", n=len(y)))
        print(f"skip {sname}/{rname}: n={len(y)}, days={ndays}")
        continue
    nsplit = 15 if sname == "Pooled" else 5
    splits = M.blocked_splits(fr.tstart, nsplit)
    lt = M.lasso_rfecv(X, y, fr.tstart.to_numpy(), F)   # full-data, paper-style table
    lasso_tables.append(dict(season=sname, regime=rname, n=len(y), **lt))
    ev = evaluate(fr, X, y, g, F, splits)
    for k, v in ev.items():
        rows.append(dict(season=sname, regime=rname, model=k,
                         **{q: v[q] for q in ("n", "r2", "r2_lo", "r2_hi", "rmse")}))
        if r is None:
            oof_store.append(pd.DataFrame(dict(season=fr.season.to_numpy(), tstart=fr.tstart.to_numpy(),
                                               model=k, y=y, pred=v["pred"])))
    print(f"{sname}/{rname}: n={len(y)}  " + "  ".join(f"{k}={v['r2']:.2f}" for k, v in ev.items()))

res = pd.DataFrame(rows)
res.to_csv(TAB / "r2_by_season_regime.csv", index=False)
pd.concat(oof_store).to_parquet(OUT / "cache" / "oof_predictions.parquet")
with open(TAB / "lasso_rfecv_selection.json", "w") as fh:
    json.dump(lasso_tables, fh, indent=1, default=float)

# ---------------------------------------------------------------- leave-one-season-out
loso = []
for test in load.SEASONS:
    tr_s = [s for s in load.SEASONS if s != test]
    Xtr, ytr, _, ftr = M.make_xy(df, season=tr_s)
    Xte, yte, gte, fte = M.make_xy(df, season=test)
    times = ftr.tstart.to_numpy()
    preds = {
        "LASSO+RFECV": lasso_factory(Xtr, ytr, times, F)(np.arange(len(ytr))).fit(Xtr, ytr).predict(Xte),
        "RF": M.init_random_forest().fit(Xtr, ytr).predict(Xte),
        "SVR": M.svr_search(F, times).fit(Xtr, ytr).predict(Xte),
        "train mean": np.full(len(yte), ytr.mean()),
    }
    for k, p in preds.items():
        sc = M.scores(yte, p, gte)
        loso.append(dict(test_season=test, model=k, **sc,
                         bias=float(np.mean(p - yte))))
    print(f"LOSO test={test}: " + "  ".join(f"{d['model']}={d['r2']:.2f}" for d in loso[-4:]))
pd.DataFrame(loso).to_csv(TAB / "r2_leave_one_season_out.csv", index=False)

# ---------------------------------------------------------------- ablations
abl = []
variants = {
    "baseline": F,
    "- u_bar_4": [f for f in F if f != "u_bar_4"],
    "- S": [f for f in F if f != "S"],
    "+ ampmean (backscatter proxy)": F + ["ampmean"],
    "+ regime one-hot (leaky)": F + ["reg_R", "reg_A"],
}
df_ab = df.copy()
df_ab["reg_R"] = (df_ab.regime == "R").astype(float).where(df_ab.regime.notna())
df_ab["reg_A"] = (df_ab.regime == "A").astype(float).where(df_ab.regime.notna())
for s in list(load.SEASONS) + ["Pooled"]:
    ss = list(load.SEASONS) if s == "Pooled" else s
    nsplit = 15 if s == "Pooled" else 5
    for name, feats in variants.items():
        # compare on identical rows: regime ablation needs regime-labelled rows
        X, y, g, fr = M.make_xy(df_ab, season=ss, features=feats)
        _, _, _, fr_common = M.make_xy(df_ab, season=ss, features=F + ["reg_R", "ampmean"])
        keep = fr.index.isin(fr_common.index)
        X, y, g, fr = X[keep], y[keep], g[keep], fr[keep]
        splits = M.blocked_splits(fr.tstart, nsplit)
        ev = evaluate(fr, X, y, g, feats, splits, which=("lasso", "rf"))
        for k in ("LASSO+RFECV", "RF"):
            abl.append(dict(season=s, variant=name, model=k, n=ev[k]["n"],
                            r2=ev[k]["r2"], r2_lo=ev[k]["r2_lo"], r2_hi=ev[k]["r2_hi"]))
    print(f"ablations {s} done")
pd.DataFrame(abl).to_csv(TAB / "ablations.csv", index=False)

# ---------------------------------------------------------------- RF permutation importance (OOF)
imp = []
for s in list(load.SEASONS) + ["Pooled"]:
    ss = list(load.SEASONS) if s == "Pooled" else s
    X, y, g, fr = M.make_xy(df, season=ss)
    acc = np.zeros(len(F))
    splits = M.blocked_splits(fr.tstart, 15 if s == "Pooled" else 5)
    for tr, te in splits:
        m = M.init_random_forest().fit(X[tr], y[tr])
        pi = permutation_importance(m, X[te], y[te], n_repeats=20, random_state=0,
                                    scoring="r2", n_jobs=-1)
        acc += pi.importances_mean * len(te)
    acc /= len(y)
    sign = [np.sign(np.corrcoef(X[:, j], y)[0, 1]) for j in range(len(F))]
    for f, a, sg in zip(F, acc, sign):
        imp.append(dict(season=s, feature=f, perm_importance_r2=a,
                        corr_sign="+" if sg > 0 else "-"))
pd.DataFrame(imp).to_csv(TAB / "rf_permutation_importance.csv", index=False)

# ---------------------------------------------------------------- secondary targets
sec = []
for tgt in ("d50", "sigma2"):
    for s in list(load.SEASONS) + ["Pooled"]:
        ss = list(load.SEASONS) if s == "Pooled" else s
        X, y, g, fr = M.make_xy(df, season=ss, target=tgt)
        splits = M.blocked_splits(fr.tstart, 15 if s == "Pooled" else 5)
        p = M.oof_predict(lambda tr: M.init_random_forest(), X, y, splits)
        sec.append(dict(target=tgt, season=s, model="RF", **M.scores(y, p, g)))
pd.DataFrame(sec).to_csv(TAB / "r2_secondary_targets.csv", index=False)

# ---------------------------------------------------------------- noise / drift robustness (pooled)
X, y, g, fr = M.make_xy(df, season=list(load.SEASONS))
splits = M.blocked_splits(fr.tstart, 15)
sd = X.std(0)
perturb = {
    "none": lambda Xt, rng: Xt,
    "white noise 10% of sd": lambda Xt, rng: Xt + rng.normal(0, .10 * sd, Xt.shape),
    "white noise 25% of sd": lambda Xt, rng: Xt + rng.normal(0, .25 * sd, Xt.shape),
    "white noise 50% of sd": lambda Xt, rng: Xt + rng.normal(0, .50 * sd, Xt.shape),
    "T +1.0 C (warming / sensor offset)": lambda Xt, rng: Xt + np.eye(len(F))[F.index("T")] * 1.0,
    "S -2 PSU (fresher / drift)": lambda Xt, rng: Xt - np.eye(len(F))[F.index("S")] * 2.0,
    "velocity gain +10% (u_b, u_bar, u_bar_4)": lambda Xt, rng: Xt * np.where(
        np.isin(F, ["u_b", "u_bar", "u_bar_4"]), 1.1, 1.0),
    "epsilon x2": lambda Xt, rng: Xt * np.where(np.array(F) == "epsilon", 2.0, 1.0),
}
rob = []
times = fr.tstart.to_numpy()
fitted = []
for tr, te in splits:
    fitted.append((te, M.init_random_forest().fit(X[tr], y[tr]),
                   lasso_factory(X, y, times, F)(tr).fit(X[tr], y[tr])))
for name, fn in perturb.items():
    rng = np.random.default_rng(0)
    pr, pl = np.full(len(y), np.nan), np.full(len(y), np.nan)
    for te, rf, la in fitted:
        Xt = fn(X[te].copy(), rng)
        Xt[:, F.index("epsilon")] = np.clip(Xt[:, F.index("epsilon")], 1e-9, None)
        pr[te], pl[te] = rf.predict(Xt), la.predict(Xt)
    for k, p in (("RF", pr), ("LASSO+RFECV", pl)):
        rob.append(dict(perturbation=name, model=k, **M.scores(y, p, g, n_boot=200)))
pd.DataFrame(rob).to_csv(TAB / "robustness_pooled.csv", index=False)

# ---------------------------------------------------------------- final deployable models
Xall, yall, _, frall = M.make_xy(df, season=list(load.SEASONS))
rf_final = M.init_random_forest().fit(Xall, yall)
lt_final = M.lasso_rfecv(Xall, yall, frall.tstart.to_numpy(), F)
cols = [F.index(f) for f in lt_final["selected"]]
la_final = M.lasso_pipe(lt_final["selected"], lt_final["alpha"]).fit(Xall[:, cols], yall)
meta = dict(features=F, target=M.TARGET, units=dict(u_b="m/s", u_bar="m/s (+ = flood)",
            u_bar_4="m/s", epsilon="W/kg", T="degC", S="PSU", d_mean="um"),
            train_min=dict(zip(F, Xall.min(0))), train_max=dict(zip(F, Xall.max(0))),
            n_train=int(len(yall)), lasso_selected=lt_final["selected"],
            lasso_alpha=float(lt_final["alpha"]),
            train_period="2018-07-18..2019-05-10, P2 South SF Bay, LISST 35 cmab")
joblib.dump(dict(rf=rf_final, lasso=la_final, meta=meta), OUT / "models" / "floc_models.joblib")
print("saved outputs/models/floc_models.joblib")
