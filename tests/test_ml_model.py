"""Tests for Nick's ML/DL model module.

All tests use synthetic OHLCV data — no API keys, no network calls,
no GPU required. XGBoost is tested end-to-end; LSTM tests are skipped
if PyTorch is not installed.

Run:
    pytest tests/test_ml_model.py -v
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.models.ml_model import (
    FEATURE_COLS,
    WFResult,
    XGBoostForecaster,
    _add_lag_features,
    _build_sequences,
    engineer_features,
    evaluate,
    predictions_to_df,
    walk_forward_validate,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_ohlcv(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """Synthetic daily OHLCV with a mild upward drift."""
    rng   = np.random.default_rng(seed)
    dates = pd.date_range("2021-01-01", periods=n, freq="B")
    price = 400.0 * np.cumprod(1 + rng.normal(0.0003, 0.01, n))
    noise = rng.uniform(0.998, 1.002, n)
    return pd.DataFrame(
        {
            "open":   price * noise,
            "high":   price * rng.uniform(1.001, 1.015, n),
            "low":    price * rng.uniform(0.985, 0.999, n),
            "close":  price,
            "volume": rng.integers(1_000_000, 10_000_000, n).astype(float),
        },
        index=dates,
    )


# ─── Feature Engineering ──────────────────────────────────────────────────────

def test_engineer_features_has_all_cols():
    df  = _make_ohlcv()
    out = engineer_features(df)
    missing = [c for c in FEATURE_COLS + ["target"] if c not in out.columns]
    assert not missing, f"Missing columns: {missing}"


def test_engineer_features_no_lookahead():
    """Target is next-day return — the very last row must be NaN."""
    df  = _make_ohlcv()
    out = engineer_features(df)
    assert pd.isna(out["target"].iloc[-1]), "Last target row should be NaN (no future data)"


def test_engineer_features_preserves_row_count():
    df  = _make_ohlcv(n=300)
    out = engineer_features(df)
    assert len(out) == 300


def test_engineer_features_sorted_ascending():
    df  = _make_ohlcv().sort_index(ascending=False)  # feed in descending order
    out = engineer_features(df)
    assert out.index.is_monotonic_increasing


# ─── Sequence Builder ─────────────────────────────────────────────────────────

def test_build_sequences_output_shapes():
    n, f, seq = 100, 5, 10
    X = np.random.randn(n, f).astype(np.float32)
    y = np.random.randn(n).astype(np.float32)
    Xs, ys = _build_sequences(X, y, seq)
    assert Xs.shape == (n - seq, seq, f)
    assert ys.shape == (n - seq,)


def test_build_sequences_window_content():
    X = np.arange(20).reshape(20, 1).astype(np.float32)
    y = np.zeros(20, dtype=np.float32)
    Xs, _ = _build_sequences(X, y, seq_len=5)
    # First sequence should be rows 0–4, target at row 5
    np.testing.assert_array_equal(Xs[0, :, 0], [0, 1, 2, 3, 4])


# ─── Lag Features ─────────────────────────────────────────────────────────────

def test_add_lag_features_shape():
    X  = np.random.randn(50, 3)
    Xl = _add_lag_features(X, n_lags=4)
    assert Xl.shape == (50, 3 * 5)  # original + 4 lags


def test_add_lag_features_leading_nan():
    X  = np.ones((10, 2))
    Xl = _add_lag_features(X, n_lags=3)
    # Row 0: all lag columns NaN (no history yet for any lag)
    assert np.isnan(Xl[0, 2:]).all()
    # Row 2: lag-1 and lag-2 are valid; only lag-3 columns are still NaN
    assert not np.isnan(Xl[2, 2:4]).any()  # lag-1 valid
    assert not np.isnan(Xl[2, 4:6]).any()  # lag-2 valid
    assert np.isnan(Xl[2, 6:]).all()        # lag-3 still NaN
    # Row 3: all lags have sufficient history — no NaN anywhere
    assert not np.isnan(Xl[3]).any()


# ─── XGBoost Forecaster ───────────────────────────────────────────────────────

def test_xgboost_fit_predict_shapes():
    rng = np.random.default_rng(0)
    n, f = 300, len(FEATURE_COLS)
    X = rng.standard_normal((n, f)).astype(np.float32)
    y = rng.standard_normal(n).astype(np.float32)

    m = XGBoostForecaster(n_lags=3)
    m.fit(X[:250], y[:250])
    preds = m.predict(X[250:])
    assert preds.shape == (50,)


def test_xgboost_predictions_are_finite():
    df = _make_ohlcv(n=350)
    feat_df = engineer_features(df).dropna(subset=FEATURE_COLS + ["target"])
    X = feat_df[FEATURE_COLS].values.astype(np.float32)
    y = feat_df["target"].values.astype(np.float32)
    from src.models.ml_model import _add_lag_features
    Xl = _add_lag_features(X, n_lags=5)

    m = XGBoostForecaster()
    m.fit(Xl[:280], y[:280])
    preds = m.predict(Xl[280:])
    finite = preds[~np.isnan(preds)]
    assert len(finite) > 0
    assert np.all(np.isfinite(finite))


# ─── Walk-Forward Validation ──────────────────────────────────────────────────

def test_xgboost_walk_forward_produces_predictions():
    df     = _make_ohlcv(n=420)
    result = walk_forward_validate(df, model_type="xgboost", min_train=252, step=21)
    assert len(result.dates) > 0, "Walk-forward produced no predictions"
    assert len(result.predicted) == len(result.dates)
    assert len(result.actual)    == len(result.dates)


def test_walk_forward_date_monotone():
    df     = _make_ohlcv(n=420)
    result = walk_forward_validate(df, model_type="xgboost", min_train=252, step=21)
    dates  = pd.DatetimeIndex(result.dates)
    assert dates.is_monotonic_increasing


def test_walk_forward_no_data_leakage():
    """Predicted dates must all fall after min_train rows of the feature DataFrame."""
    df      = _make_ohlcv(n=420)
    feat_df = engineer_features(df).dropna(subset=FEATURE_COLS + ["target"])
    cutoff  = feat_df.index[252]  # first test date should be >= this

    result = walk_forward_validate(df, model_type="xgboost", min_train=252, step=21)
    assert pd.Timestamp(result.dates[0]) >= cutoff


@pytest.mark.skipif(
    not __import__("importlib").util.find_spec("torch"),
    reason="PyTorch not installed",
)
def test_lstm_walk_forward_produces_predictions():
    df     = _make_ohlcv(n=420)
    result = walk_forward_validate(df, model_type="lstm", min_train=252, step=21)
    assert len(result.dates) > 0


# ─── Output Formatting ────────────────────────────────────────────────────────

def test_predictions_to_df_schema():
    result = WFResult(
        dates=pd.date_range("2023-01-01", periods=5).tolist(),
        predicted=[0.001, -0.002,  0.003, -0.001,  0.002],
        actual=   [0.002, -0.001,  0.001, -0.003,  0.004],
    )
    df       = predictions_to_df(result, "SPY", "xgboost")
    required = {"ticker", "model_name", "predicted_return", "actual_return", "error"}
    assert required.issubset(df.columns)
    assert df["ticker"].iloc[0]     == "SPY"
    assert df["model_name"].iloc[0] == "xgboost"
    assert df.index.name            == "date"


def test_predictions_to_df_error_calculation():
    result = WFResult(
        dates=[pd.Timestamp("2023-01-01")],
        predicted=[0.005],
        actual=   [0.003],
    )
    df = predictions_to_df(result, "QQQ", "lstm")
    assert abs(df["error"].iloc[0] - 0.002) < 1e-9


# ─── Metrics ──────────────────────────────────────────────────────────────────

def test_evaluate_keys():
    rng    = np.random.default_rng(7)
    result = WFResult(
        dates=pd.date_range("2023-01-01", periods=100).tolist(),
        predicted=rng.normal(0, 0.01, 100).tolist(),
        actual=   rng.normal(0, 0.01, 100).tolist(),
    )
    df      = predictions_to_df(result, "SPY", "xgboost")
    metrics = evaluate(df)
    for key in ("rmse", "mae", "directional_accuracy", "information_coefficient",
                "n_predictions"):
        assert key in metrics


def test_evaluate_directional_accuracy_bounds():
    rng    = np.random.default_rng(9)
    result = WFResult(
        dates=pd.date_range("2023-01-01", periods=200).tolist(),
        predicted=rng.normal(0, 0.01, 200).tolist(),
        actual=   rng.normal(0, 0.01, 200).tolist(),
    )
    df      = predictions_to_df(result, "SPY", "xgboost")
    metrics = evaluate(df)
    assert 0.0 <= metrics["directional_accuracy"] <= 1.0


def test_evaluate_perfect_prediction():
    vals   = [0.01, -0.005, 0.003, -0.002, 0.008]
    result = WFResult(
        dates=pd.date_range("2023-01-01", periods=5).tolist(),
        predicted=vals,
        actual=vals,
    )
    df      = predictions_to_df(result, "SPY", "xgboost")
    metrics = evaluate(df)
    assert metrics["rmse"]                 == pytest.approx(0.0, abs=1e-9)
    assert metrics["directional_accuracy"] == pytest.approx(1.0)
