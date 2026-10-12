"""Tests for the size-distribution helpers (src/psd.py).

    ven/bin/python -m pytest tests
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import models as M, psd  # noqa: E402

# 32 log-spaced bins over the LISST-200X range
DIAS = np.geomspace(1.2, 400, 32)


def lognormal_curves(medians, width=0.5):
    """Volume fractions of log-normal curves with the given volume medians."""
    z = (np.log(DIAS)[None, :] - np.log(np.asarray(medians, float))[:, None]) / width
    return psd.volume_fractions(np.exp(-0.5 * z ** 2))


def test_volume_fractions_sum_to_one_and_ignore_nan():
    V = np.array([[1.0, np.nan, 3.0], [0.0, 2.0, 2.0]])
    F = psd.volume_fractions(V)
    assert np.allclose(F.sum(1), 1)
    assert F[0, 1] == 0 and np.isclose(F[0, 2], 0.75)


def test_quantiles_of_lognormal():
    F = lognormal_curves([20, 80])
    d50 = psd.quantile_diameter(F, DIAS, 0.5)
    assert np.allclose(d50, [20, 80], rtol=0.1)
    d10, d90 = (psd.quantile_diameter(F, DIAS, q) for q in (0.1, 0.9))
    assert np.all(d10 < d50) and np.all(d50 < d90)


def test_clr_round_trip():
    F = lognormal_curves([10, 50, 150])
    assert np.allclose(psd.inv_clr(psd.clr(F)), F, atol=1e-10)


def test_wasserstein_log():
    F = lognormal_curves([30, 30])
    assert np.allclose(psd.wasserstein_log(F, F, DIAS), 0)
    # a single-bin curve moved one bin to the right costs one bin width in ln(d)
    A, B = np.zeros((1, 32)), np.zeros((1, 32))
    A[0, 10], B[0, 11] = 1, 1
    dx = np.log(DIAS[11] / DIAS[10])
    assert np.isclose(psd.wasserstein_log(A, B, DIAS)[0], dx)
    # further apart -> larger distance
    G = lognormal_curves([30, 120])
    w = psd.wasserstein_log(F, G, DIAS)
    assert w[0] < 1e-12 < w[1]


@pytest.mark.parametrize("name", ["mean PSD", "linear (PCA)", "RF (all bins)"])
def test_models_return_valid_curves_and_learn(name):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(300, len(M.BASELINE)))
    X[:, M.BASELINE.index("epsilon")] = 10 ** rng.uniform(-7, -4, 300)
    med = np.exp(np.log(60) + 0.5 * X[:, 0])        # u_b sets the floc size
    F = lognormal_curves(med)
    tr, te = np.arange(200), np.arange(200, 300)
    P = psd.model_factories(M.BASELINE)[name]().fit(X[tr], F[tr]).predict(X[te])
    assert P.shape == F[te].shape
    assert np.all(P >= 0) and np.allclose(P.sum(1), 1)
    if name != "mean PSD":
        base = psd.MeanPSD().fit(X[tr], F[tr]).predict(X[te])
        s = psd.curve_scores(F[te], P, base, DIAS, np.arange(100) // 10, n_boot=50)
        assert s["W1_skill"] > 0.5 and s["r2_d50"] > 0.5


def test_cached_curves_match_feature_table():
    """The cached curves reproduce d_mean in features.parquet exactly."""
    if not psd.PSD_CACHE.exists():
        pytest.skip("run build_psd.py first")
    table, dias = psd.load_psd()
    df = M.load_table().merge(table, on=["season", "tstart"]).dropna(subset=["d_mean"])
    F = psd.volume_fractions(df[psd.bin_cols(len(dias))].to_numpy())
    assert np.allclose(psd.mean_diameter(F, dias), df.d_mean, atol=1e-6)
