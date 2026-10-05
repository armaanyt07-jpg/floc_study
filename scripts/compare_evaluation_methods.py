"""Diagnostics explaining the gap between our r2 and the two papers.

(a) correlation vs r2 of the OOF predictions (offsets between time blocks?)
(b) sensitivity: drop biofouling-flagged and tau<0.3 bursts
(c) random 70/30 split (class-paper protocol) -- INVALID for hourly data,
    shown only to quantify how much a random split inflates r2
(d) paper-style in-sample LASSO r2 (Table 1 reports in-sample r2)
(e) do T and S act as "clocks"? feature sets under blocked vs random split
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LassoCV
from sklearn.metrics import r2_score
from sklearn.model_selection import KFold, train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import load, models as M  # noqa: E402

warnings.filterwarnings("ignore")
TAB = load.ROOT / "outputs" / "tables"
df = M.load_table()
F = M.BASELINE
SETS = [(s, s) for s in load.SEASONS] + [("Pooled", list(load.SEASONS))]

# (a)
oof = pd.read_parquet(load.ROOT / "outputs" / "cache" / "oof_predictions.parquet")
rows = []
for name, _ in SETS:
    for m in ("LASSO+RFECV", "RF", "SVR"):
        d = oof[(oof.model == m)]
        d = d[d.season == name] if name != "Pooled" else d.iloc[-0:]
        if name != "Pooled":
            d = d.drop_duplicates("tstart", keep="first")
        else:  # pooled-fit rows are the second copy of each timestamp
            d = d.drop_duplicates("tstart", keep="last")
        d = d.dropna()
        rows.append(dict(set=name, model=m, pearson_r=np.corrcoef(d.y, d.pred)[0, 1],
                         r2=r2_score(d.y, d.pred)))
a = pd.DataFrame(rows)
print("(a) OOF Pearson r vs r2\n", a.round(3).to_string(index=False))

# (b) + (c) + (d)
out = []
for name, ss in SETS:
    for filt in ("all rows", "no biofoul, tau>=0.3"):
        d = df if filt == "all rows" else df[~df.biofoul_flag & ~df.tau_flag_lt0p3]
        X, y, g, fr = M.make_xy(d, season=ss)
        if len(y) < 60:
            continue
        nsp = 15 if name == "Pooled" else 5
        sp = M.blocked_splits(fr.tstart, nsp)
        p = M.oof_predict(lambda tr: M.init_random_forest(), X, y, sp)
        rec = dict(set=name, rows=filt, n=len(y), rf_blocked_r2=M.scores(y, p, g, 200)["r2"])
        # (c) random 70/30, 10 repeats
        rr = []
        for seed in range(10):
            Xa, Xb, ya, yb = train_test_split(X, y, test_size=.3, random_state=seed)
            rr.append(r2_score(yb, M.init_random_forest(seed).fit(Xa, ya).predict(Xb)))
        rec["rf_random70_30_r2"] = np.mean(rr)
        # (d) in-sample LASSO with alpha from shuffled KFold (likely paper setup)
        pre = M.lasso_pipe(F)[:-1]
        Z = pre.fit_transform(X)
        las = LassoCV(cv=KFold(5, shuffle=True, random_state=0), max_iter=50000).fit(Z, y)
        rec["lasso_insample_r2"] = r2_score(y, las.predict(Z))
        rec["lasso_nonzero"] = ",".join(f"{f}({'+' if c > 0 else '-'})" for f, c in zip(F, las.coef_) if c != 0)
        out.append(rec)
b = pd.DataFrame(out)
print("\n(b,c,d)\n", b.round(3).to_string(index=False))
a.to_csv(TAB / "diag_oof_corr.csv", index=False)
b.to_csv(TAB / "diag_protocols.csv", index=False)

# (e) feature sets: do T and S act as 'clocks' that inflate random-split r2?
sets = {"hydro: u_b,u_bar,u_bar_4": ["u_b", "u_bar", "u_bar_4"],
        "hydro + eps": ["u_b", "u_bar", "u_bar_4", "epsilon"],
        "T,S only": ["T", "S"], "all 6": M.BASELINE}
rows = []
for name, ss in SETS:
    for fs_name, fs in sets.items():
        X, y, g, fr = M.make_xy(df, season=ss, features=fs)
        sp = M.blocked_splits(fr.tstart, 15 if name == "Pooled" else 5)
        rf_b = M.scores(y, M.oof_predict(lambda tr: M.init_random_forest(), X, y, sp), g, 200)["r2"]
        la_b = M.scores(y, M.oof_predict(lambda tr: M.lasso_pipe(fs, 0.5), X, y, sp), g, 200)["r2"]
        rr = np.mean([r2_score(yb, M.init_random_forest(k).fit(Xa, ya).predict(Xb))
                      for k in range(5)
                      for Xa, Xb, ya, yb in [train_test_split(X, y, test_size=.3, random_state=k)]])
        rows.append(dict(set=name, features=fs_name, rf_blocked=rf_b, lasso_a0p5_blocked=la_b, rf_random=rr))
e = pd.DataFrame(rows)
e.to_csv(TAB / "diag_feature_sets.csv", index=False)
print("\n(e) feature sets\n", e.round(3).to_string(index=False))
