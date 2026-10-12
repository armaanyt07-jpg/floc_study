"""Predict floc size for a single burst using the saved pooled models.

Usage:
    from src.predict import predict_one
    predict_one(dict(u_b=0.06, u_bar=0.02, u_bar_4=-0.05, epsilon=2e-5, T=19.0, S=25.0))

Inputs must be computed exactly as in src/features.py (15-cmab ADV burst,
CTD T and S). Inputs outside the training range are reported, because a
random forest cannot extrapolate (it saturates at the edge of the training data).
"""
import numpy as np
import joblib

from . import load

MODEL_PATH = load.ROOT / "outputs" / "models" / "floc_models.joblib"


def predict_one(row, path=MODEL_PATH):
    bundle = joblib.load(path)
    meta = bundle["meta"]
    F = meta["features"]
    missing = [f for f in F if f not in row or row[f] is None or not np.isfinite(row[f])]
    if missing:
        raise ValueError(f"missing inputs (no gap filling): {missing}")
    x = np.array([[float(row[f]) for f in F]])
    out_of_range = {f: (row[f], meta["train_min"][f], meta["train_max"][f]) for f in F
                    if not meta["train_min"][f] <= row[f] <= meta["train_max"][f]}
    cols = [F.index(f) for f in meta["lasso_selected"]]
    return dict(d_mean_rf_um=float(bundle["rf"].predict(x)[0]),
                d_mean_lasso_um=float(bundle["lasso"].predict(x[:, cols])[0]),
                out_of_training_range=out_of_range)
