"""Run the random forest on the cached feature table and compare with the papers.

    ven/bin/python run_random_forest.py                 # everything, default settings
    ven/bin/python run_random_forest.py --trees 32      # class-paper tree count everywhere

Needs outputs/cache/features.parquet (built by build_features.py).

Each row trains a random forest on one subset of the data and scores it on data it
did not train on, using one of three ways of holding data out:
  random 70/30          test hours scattered among training hours (class-paper method;
                        optimistic because neighbouring hours are nearly identical)
  time-blocked          whole multi-day stretches held out, 12 h gap (honest forecast test)
  leave-one-season-out  train on two seasons, test on the third (new-conditions test)
"""
import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from src import load, models as M  # noqa: E402

warnings.filterwarnings("ignore")

SEASONS = list(load.SEASONS)
# Class paper (CS229): RF, all seasons pooled, random 70/30 split, top-4 features
# (S, u_b, n_p, T). n_p is not in the public data, so its available features are used.
CLASS_PAPER_FEATURES = ["S", "u_b", "T", "u_bar"]
CLASS_PAPER_R2 = {"d50": 0.81, "sigma2": 0.75}
# Journal paper (Egan et al. 2022, Table 1): LASSO, in-sample r2, range over regimes.
JOURNAL_R2 = {"Summer": "0.15-0.51", "Winter": "0.45-0.65", "Spring": "0.15-0.46"}


def make_forest(trees, seed=0):
    return RandomForestRegressor(n_estimators=trees, min_samples_leaf=5,
                                 max_features="sqrt", n_jobs=-1, random_state=seed)


def class_paper_forest(trees=32, seed=0):
    """Class paper: scikit-learn RandomForestRegressor defaults, 32 trees."""
    return RandomForestRegressor(n_estimators=trees, n_jobs=-1, random_state=seed)


def class_paper_svr_r2(X, y, repeats=10):
    """Class paper SVR: C=2048, epsilon=4, 70% train / 15% CV / 15% test.
    Features are standardised (the paper doesn't say; SVR needs it)."""
    r2s, rmses = [], []
    for seed in range(repeats):
        Xa, Xr, ya, yr = train_test_split(X, y, test_size=0.3, random_state=seed)
        _, Xt, _, yt = train_test_split(Xr, yr, test_size=0.5, random_state=seed)
        m = make_pipeline(StandardScaler(), SVR(C=2048, epsilon=4)).fit(Xa, ya)
        p = m.predict(Xt)
        r2s.append(r2_score(yt, p))
        rmses.append(np.sqrt(mean_squared_error(yt, p)))
    return np.mean(r2s), np.mean(rmses)


def random_split_r2(X, y, trees, repeats=10, forest=None):
    forest = forest or make_forest
    r2s, rmses = [], []
    for seed in range(repeats):
        Xa, Xb, ya, yb = train_test_split(X, y, test_size=0.3, random_state=seed)
        p = forest(trees, seed).fit(Xa, ya).predict(Xb)
        r2s.append(r2_score(yb, p))
        rmses.append(np.sqrt(mean_squared_error(yb, p)))
    return np.mean(r2s), np.mean(rmses)


def time_blocked_r2(X, y, frame, trees, n_blocks):
    splits = M.blocked_splits(frame.tstart, n_blocks)
    p = M.oof_predict(lambda tr: make_forest(trees), X, y, splits)
    return r2_score(y, p), np.sqrt(mean_squared_error(y, p))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--trees", type=int, default=500, help="number of trees (class paper used 32)")
    ap.add_argument("--target", default="d_mean", choices=["d_mean", "d50", "sigma2"],
                    help="floc size measure for our rows (default: mean diameter, as in the journal paper)")
    args = ap.parse_args()

    df = M.load_table()
    feats = M.BASELINE
    rows = []

    def add(test, data, method, X, y, r2, rmse, paper="", paper_r2=""):
        rows.append({"test": test, "data": data, "hold-out method": method, "n": len(y),
                     "our r2": round(r2, 2), "our RMSE (um)": round(rmse, 1),
                     "paper": paper, "paper r2": paper_r2})

    # 1) Class-paper setup, as close as the public data allows
    for tgt in ("d50", "sigma2"):
        X, y, _, _ = M.make_xy(df, season=SEASONS, features=CLASS_PAPER_FEATURES, target=tgt)
        r2, rmse = random_split_r2(X, y, 32, forest=class_paper_forest)
        add(f"class-paper RF ({tgt}, 32 trees)", "all seasons", "random 70/30", X, y, r2, rmse,
            "class paper RF", CLASS_PAPER_R2[tgt])
        if tgt == "d50":  # epsilon=4 is in um, so only meaningful for d50
            r2, rmse = class_paper_svr_r2(X, y)
            add("class-paper SVR (d50, C=2048, eps=4)", "all seasons", "random 70/15/15", X, y,
                r2, rmse, "class paper SVR", 0.76)

    # 2) Our features, each season and pooled, random vs time-blocked
    for season in SEASONS + ["All seasons"]:
        ss = SEASONS if season == "All seasons" else season
        X, y, _, fr = M.make_xy(df, season=ss, features=feats, target=args.target)
        nb = 15 if season == "All seasons" else 5
        r2, rmse = random_split_r2(X, y, args.trees)
        add("our features", season, "random 70/30", X, y, r2, rmse)
        r2, rmse = time_blocked_r2(X, y, fr, args.trees, nb)
        add("our features", season, "time-blocked", X, y, r2, rmse,
            "journal (LASSO, in-sample)" if season in JOURNAL_R2 else "",
            JOURNAL_R2.get(season, ""))

    # 3) Leave one season out
    for test_season in SEASONS:
        Xtr, ytr, _, _ = M.make_xy(df, season=[s for s in SEASONS if s != test_season],
                                   features=feats, target=args.target)
        Xte, yte, _, _ = M.make_xy(df, season=test_season, features=feats, target=args.target)
        p = make_forest(args.trees).fit(Xtr, ytr).predict(Xte)
        add("our features", f"predict {test_season}", "leave-one-season-out", Xte, yte,
            r2_score(yte, p), np.sqrt(mean_squared_error(yte, p)))

    out = pd.DataFrame(rows)
    path = ROOT / "outputs" / "tables" / "random_forest_comparison.csv"
    out.to_csv(path, index=False)
    pd.set_option("display.width", 200, "display.max_colwidth", 40)
    print(f"Random forest: {args.trees} trees, features {feats}, target {args.target}\n")
    print(out.to_string(index=False))
    print(f"\nSaved -> {path.relative_to(ROOT)}")
    print("Note: sigma2 is defined differently from the class paper (our values are ~1000s um^2, "
          "theirs 50-200), so compare its r2 only loosely.")


if __name__ == "__main__":
    main()
