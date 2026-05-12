"""Custom ML/DL model — LSTM + XGBoost return forecasters.

Owner: Nick Kontonicolaou (extra credit — ML/DL component)

Two models trained with expanding-window walk-forward validation:
  LSTM     : 2-layer PyTorch sequence model trained on 30-day windows (DL)
  XGBoost  : gradient-boosted tabular model with lag features (ML baseline)

Both write to the ml_predictions table schema:
    date, ticker, model_name, predicted_return, actual_return, error

Standalone usage (no DB or API key required):
    python -m src.models.ml_model --ticker SPY QQQ --model lstm
    python -m src.models.ml_model --ticker SPY QQQ --model xgboost
    python -m src.models.ml_model --ticker SPY QQQ --model both --save-csv
"""

from __future__ import annotations

import argparse
import logging
import math
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import StandardScaler
from scipy.stats import spearmanr

logger = logging.getLogger(__name__)

# ── Walk-forward config ─────────────────────────────────────────────────────
MIN_TRAIN_DAYS = 252    # ~1 year initial training window
STEP_DAYS      = 21     # re-fit every ~1 month
SEQUENCE_LEN   = 30     # LSTM lookback (trading days)

# ── LSTM hyperparameters ────────────────────────────────────────────────────
HIDDEN_SIZE = 64
NUM_LAYERS  = 2
DROPOUT     = 0.2
EPOCHS      = 50
BATCH_SIZE  = 32
LR          = 1e-3

# ── Optional imports ────────────────────────────────────────────────────────
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    _TORCH = True
except ImportError:
    _TORCH = False
    logger.warning("PyTorch not installed — LSTM unavailable. Run: pip install torch")

try:
    import xgboost as xgb
    _XGB = True
except ImportError:
    _XGB = False
    logger.warning("XGBoost not installed. Run: pip install xgboost")


# ─────────────────────────────────────────────────────────────────────────────
# Feature Engineering
# ─────────────────────────────────────────────────────────────────────────────

FEATURE_COLS = [
    "daily_return", "log_return",
    "vol_5d", "vol_20d",
    "mom_5d", "mom_20d",
    "rsi_14",
    "volume_change", "price_range",
]


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicator features and a next-day return target.

    Accepts any OHLCV DataFrame with columns: open, high, low, close, volume.
    Returns the same DataFrame (sorted ascending) with FEATURE_COLS appended
    and a 'target' column = next-day daily return.
    """
    df = df.copy().sort_index(ascending=True)
    close  = df["close"]
    volume = df["volume"]

    df["daily_return"]  = close.pct_change()
    df["log_return"]    = np.log(close / close.shift(1))
    df["vol_5d"]        = df["daily_return"].rolling(5).std()
    df["vol_20d"]       = df["daily_return"].rolling(20).std()
    df["mom_5d"]        = close.pct_change(5)
    df["mom_20d"]       = close.pct_change(20)

    # RSI (14-period) — avoids division-by-zero when all gains or all losses
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    df["volume_change"] = volume.pct_change()
    df["price_range"]   = (df["high"] - df["low"]) / close

    # Target: next-day return (shift -1 so last row is NaN — no lookahead)
    df["target"] = df["daily_return"].shift(-1)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# LSTM
# ─────────────────────────────────────────────────────────────────────────────

if _TORCH:
    class _LSTMNet(nn.Module):
        def __init__(self, n_features: int) -> None:
            super().__init__()
            self.lstm = nn.LSTM(
                input_size=n_features,
                hidden_size=HIDDEN_SIZE,
                num_layers=NUM_LAYERS,
                dropout=DROPOUT,
                batch_first=True,
            )
            self.fc = nn.Linear(HIDDEN_SIZE, 1)

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            out, _ = self.lstm(x)
            return self.fc(out[:, -1, :]).squeeze(-1)


def _build_sequences(
    X: np.ndarray, y: np.ndarray, seq_len: int
) -> tuple[np.ndarray, np.ndarray]:
    """Slide a window across X to produce (n, seq_len, features) input arrays."""
    xs, ys = [], []
    for i in range(seq_len, len(X)):
        xs.append(X[i - seq_len : i])
        ys.append(y[i])
    return np.array(xs, dtype=np.float32), np.array(ys, dtype=np.float32)


class LSTMForecaster:
    """PyTorch LSTM trained on rolling 30-day windows of technical features."""

    def __init__(self, seq_len: int = SEQUENCE_LEN) -> None:
        if not _TORCH:
            raise ImportError("PyTorch required. Run: pip install torch")
        self.seq_len = seq_len
        self.scaler: StandardScaler = StandardScaler()
        self.model: "_LSTMNet | None" = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        X_scaled = self.scaler.fit_transform(X)
        Xs, ys   = _build_sequences(X_scaled, y, self.seq_len)
        if len(Xs) == 0:
            raise ValueError(f"Need > {self.seq_len} training rows to build sequences.")

        self.model = _LSTMNet(n_features=X.shape[1])
        optimizer  = torch.optim.Adam(self.model.parameters(), lr=LR)
        criterion  = nn.MSELoss()
        dataset    = TensorDataset(torch.from_numpy(Xs), torch.from_numpy(ys))
        loader     = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

        self.model.train()
        for _ in range(EPOCHS):
            for xb, yb in loader:
                optimizer.zero_grad()
                criterion(self.model(xb), yb).backward()
                optimizer.step()

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict for the last (len(X) - seq_len) time steps."""
        if self.model is None:
            raise RuntimeError("Call fit() before predict().")
        X_scaled = self.scaler.transform(X)
        Xs, _    = _build_sequences(X_scaled, np.zeros(len(X_scaled)), self.seq_len)
        self.model.eval()
        with torch.no_grad():
            return self.model(torch.from_numpy(Xs)).numpy()


# ─────────────────────────────────────────────────────────────────────────────
# XGBoost
# ─────────────────────────────────────────────────────────────────────────────

def _add_lag_features(X: np.ndarray, n_lags: int) -> np.ndarray:
    """Prepend lag-1 … lag-n columns to X. Leading rows become NaN."""
    parts = [X]
    for lag in range(1, n_lags + 1):
        lagged = np.full_like(X, np.nan)
        lagged[lag:] = X[:-lag]
        parts.append(lagged)
    return np.hstack(parts)


class XGBoostForecaster:
    """XGBoost regressor with lag-feature engineering as the ML baseline."""

    def __init__(self, n_lags: int = 5) -> None:
        if not _XGB:
            raise ImportError("XGBoost required. Run: pip install xgboost")
        self.n_lags = n_lags
        self.scaler = StandardScaler()
        self.model  = xgb.XGBRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbosity=0,
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        Xl    = _add_lag_features(X, self.n_lags)
        valid = ~np.isnan(Xl).any(axis=1) & ~np.isnan(y)
        self.scaler.fit(Xl[valid])
        self.model.fit(self.scaler.transform(Xl[valid]), y[valid])

    def predict(self, X: np.ndarray) -> np.ndarray:
        Xl    = _add_lag_features(X, self.n_lags)
        valid = ~np.isnan(Xl).any(axis=1)
        preds = np.full(len(X), np.nan)
        if valid.any():
            preds[valid] = self.model.predict(self.scaler.transform(Xl[valid]))
        return preds


# ─────────────────────────────────────────────────────────────────────────────
# Walk-forward Validation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class WFResult:
    dates:     list = field(default_factory=list)
    predicted: list = field(default_factory=list)
    actual:    list = field(default_factory=list)


def walk_forward_validate(
    df:         pd.DataFrame,
    model_type: Literal["lstm", "xgboost"] = "lstm",
    min_train:  int = MIN_TRAIN_DAYS,
    step:       int = STEP_DAYS,
) -> WFResult:
    """Expanding-window walk-forward validation.

    For each fold the model trains on all data up to `train_end` and
    predicts the next `step` days. The window then expands by `step`.
    This mirrors realistic deployment: no future data ever leaks into training.

    Args:
        df:         OHLCV DataFrame (any interval; must contain open/high/low/close/volume).
        model_type: "lstm" or "xgboost"
        min_train:  number of rows in the initial training window (~1 year of daily data).
        step:       number of rows per test fold (~1 month).

    Returns:
        WFResult with aligned dates / predicted / actual lists.
    """
    feat_df = engineer_features(df).dropna(subset=FEATURE_COLS + ["target"])
    X       = feat_df[FEATURE_COLS].values.astype(np.float32)
    y       = feat_df["target"].values.astype(np.float32)
    dates   = feat_df.index

    result    = WFResult()
    train_end = min_train

    while train_end + step <= len(X):
        test_slice  = slice(train_end, train_end + step)
        test_dates  = dates[test_slice]
        y_test      = y[test_slice]

        try:
            if model_type == "lstm":
                m = LSTMForecaster()
                m.fit(X[:train_end], y[:train_end])
                # Pass last seq_len training rows + test window for context
                ctx   = X[train_end - SEQUENCE_LEN : train_end + step]
                preds = m.predict(ctx)          # shape: (step,)

            else:  # xgboost
                m = XGBoostForecaster()
                m.fit(X[:train_end], y[:train_end])
                # Prepend n_lags training rows so every test-window row has
                # valid lag history — no NaN predictions dropped by evaluate()
                ctx       = X[max(0, train_end - m.n_lags) : train_end + step]
                preds_all = m.predict(ctx)
                preds     = preds_all[-step:]

        except Exception as exc:  # noqa: BLE001
            logger.warning("Fold at train_end=%d failed (%s): %s",
                           train_end, model_type, exc)
            train_end += step
            continue

        result.dates.extend(test_dates.tolist())
        result.predicted.extend(preds.tolist())
        result.actual.extend(y_test.tolist())
        train_end += step

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Output Formatting & Metrics
# ─────────────────────────────────────────────────────────────────────────────

def predictions_to_df(
    result:     WFResult,
    ticker:     str,
    model_name: str,
) -> pd.DataFrame:
    """Format a WFResult into the ml_predictions MySQL table schema."""
    predicted = np.array(result.predicted, dtype=float)
    actual    = np.array(result.actual,    dtype=float)
    return pd.DataFrame({
        "date":             result.dates,
        "ticker":           ticker.upper(),
        "model_name":       model_name,
        "predicted_return": predicted,
        "actual_return":    actual,
        "error":            predicted - actual,
    }).set_index("date")


def evaluate(preds_df: pd.DataFrame) -> dict:
    """Compute RMSE, MAE, directional accuracy, and information coefficient.

    These are the four metrics Nick presents in the 3:30–4:30 slot.
    """
    p    = preds_df["predicted_return"].values
    a    = preds_df["actual_return"].values
    mask = ~(np.isnan(p) | np.isnan(a))
    p, a = p[mask], a[mask]

    rmse    = math.sqrt(mean_squared_error(a, p))
    mae     = float(np.mean(np.abs(p - a)))
    dir_acc = float(np.mean(np.sign(p) == np.sign(a)))
    ic, _   = spearmanr(p, a)

    return {
        "rmse":                   round(rmse,    6),
        "mae":                    round(mae,     6),
        "directional_accuracy":   round(dir_acc, 4),
        "information_coefficient": round(float(ic), 4),
        "n_predictions":          int(mask.sum()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Top-level Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def run(
    tickers:    list[str] = ("SPY", "QQQ"),
    model_type: Literal["lstm", "xgboost", "both"] = "both",
    period:     str = "3y",
) -> dict[str, pd.DataFrame]:
    """Fetch data via yFinance, run walk-forward validation, return predictions.

    This is the function Jacob's DB loader should call to populate ml_predictions.

    Returns:
        dict keyed by "{ticker}_{model_name}", each value is a DataFrame
        in the ml_predictions table schema.
    """
    import yfinance as yf  # local import so DB/API paths don't require it

    models = ["lstm", "xgboost"] if model_type == "both" else [model_type]
    results: dict[str, pd.DataFrame] = {}

    for ticker in tickers:
        logger.info("Fetching %s (%s)…", ticker, period)
        raw = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False)
        if raw is None or raw.empty:
            logger.error("No data returned for %s — skipping.", ticker)
            continue
        raw.columns = [c.lower().replace(" ", "_") for c in raw.columns]
        if raw.index.tz is not None:
            raw.index = raw.index.tz_convert("UTC").tz_localize(None)
        raw = raw.sort_index(ascending=True)

        for mtype in models:
            logger.info("Running %s walk-forward for %s…", mtype.upper(), ticker)
            wf = walk_forward_validate(raw, model_type=mtype)  # type: ignore[arg-type]
            if not wf.dates:
                logger.warning("No predictions produced for %s/%s.", ticker, mtype)
                continue

            preds_df = predictions_to_df(wf, ticker, mtype)
            metrics  = evaluate(preds_df)
            logger.info(
                "%s %s — RMSE: %.5f | DirAcc: %.1f%% | IC: %.4f | n=%d",
                ticker, mtype.upper(),
                metrics["rmse"],
                metrics["directional_accuracy"] * 100,
                metrics["information_coefficient"],
                metrics["n_predictions"],
            )
            results[f"{ticker}_{mtype}"] = preds_df

    return results


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="Nick's ML/DL walk-forward model for SPY/QQQ return forecasting."
    )
    parser.add_argument("--ticker",   nargs="+", default=["SPY", "QQQ"])
    parser.add_argument("--model",    choices=["lstm", "xgboost", "both"], default="both")
    parser.add_argument("--period",   default="3y", help="yFinance lookback (e.g. 3y, 5y)")
    parser.add_argument("--save-csv", action="store_true",
                        help="Write ml_predictions_{ticker}_{model}.csv")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    all_results = run(
        tickers=args.ticker,
        model_type=args.model,
        period=args.period,
    )

    for key, df in all_results.items():
        metrics = evaluate(df)
        ticker, mname = key.rsplit("_", 1)
        print(f"\n{'='*55}")
        print(f"  {ticker} — {mname.upper()}  Walk-Forward Results")
        print(f"{'='*55}")
        print(f"  {'RMSE':<30} {metrics['rmse']}")
        print(f"  {'MAE':<30} {metrics['mae']}")
        print(f"  {'Directional Accuracy':<30} {metrics['directional_accuracy']:.1%}")
        print(f"  {'Information Coefficient':<30} {metrics['information_coefficient']}")
        print(f"  {'Predictions':<30} {metrics['n_predictions']}")
        if args.save_csv:
            path = f"ml_predictions_{ticker}_{mname}.csv"
            df.reset_index().to_csv(path, index=False)
            print(f"\n  Saved → {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
