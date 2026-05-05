"""Tests for the yFinance extractor.

Owner: Diana Lucero

We mock yf.Ticker so tests run offline without hitting Yahoo Finance.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.extractors.yfinance_extract import (
    YFinanceError,
    fetch_yfinance_history,
    fetch_many,
)


def _make_yf_dataframe(empty: bool = False, tz_aware: bool = True) -> pd.DataFrame:
    if empty:
        return pd.DataFrame()
    idx = pd.to_datetime(["2026-05-04", "2026-05-01", "2026-04-30"])
    if tz_aware:
        idx = idx.tz_localize("America/New_York")
    return pd.DataFrame(
        {
            "Open": [720.07, 721.25, 714.63],
            "High": [722.12, 724.87, 719.79],
            "Low": [714.99, 720.47, 710.44],
            "Close": [718.01, 720.65, 718.66],
            "Adj Close": [718.01, 720.65, 718.66],
            "Volume": [51950558, 43049849, 67240949],
            "Dividends": [0.0, 0.0, 0.0],
            "Stock Splits": [0.0, 0.0, 0.0],
        },
        index=idx,
    )


def _make_mock_ticker(df: pd.DataFrame) -> MagicMock:
    tk = MagicMock()
    tk.history.return_value = df
    return tk


# ─── Happy path ──────────────────────────────────────────────


@patch("src.extractors.yfinance_extract.yf.Ticker")
def test_fetch_returns_normalized_dataframe(mock_ticker_cls):
    mock_ticker_cls.return_value = _make_mock_ticker(_make_yf_dataframe())

    df = fetch_yfinance_history("SPY", period="1mo")

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    # Lowercase, snake_case columns
    expected_cols = {
        "ticker", "open", "high", "low", "close",
        "adj_close", "volume", "dividends", "stock_splits",
    }
    assert expected_cols.issubset(set(df.columns))
    assert df.index.name == "date"
    # Sorted descending
    assert df.index[0] > df.index[-1]


@patch("src.extractors.yfinance_extract.yf.Ticker")
def test_timezone_is_stripped(mock_ticker_cls):
    mock_ticker_cls.return_value = _make_mock_ticker(_make_yf_dataframe(tz_aware=True))
    df = fetch_yfinance_history("SPY")
    assert df.index.tz is None, "Expected naive datetime index after normalization"


@patch("src.extractors.yfinance_extract.yf.Ticker")
def test_naive_index_passes_through(mock_ticker_cls):
    mock_ticker_cls.return_value = _make_mock_ticker(_make_yf_dataframe(tz_aware=False))
    df = fetch_yfinance_history("SPY")
    assert df.index.tz is None


@patch("src.extractors.yfinance_extract.yf.Ticker")
def test_ticker_uppercased(mock_ticker_cls):
    mock_ticker_cls.return_value = _make_mock_ticker(_make_yf_dataframe())
    df = fetch_yfinance_history("spy")
    assert (df["ticker"] == "SPY").all()


# ─── Retry / failure handling ───────────────────────────────


@patch("src.extractors.yfinance_extract.time.sleep", return_value=None)
@patch("src.extractors.yfinance_extract.yf.Ticker")
def test_empty_frame_triggers_retry_then_succeeds(mock_ticker_cls, _mock_sleep):
    empty_tk = _make_mock_ticker(_make_yf_dataframe(empty=True))
    good_tk = _make_mock_ticker(_make_yf_dataframe())
    mock_ticker_cls.side_effect = [empty_tk, good_tk]

    df = fetch_yfinance_history("SPY", retries=3, backoff_sec=0)
    assert len(df) == 3
    assert mock_ticker_cls.call_count == 2


@patch("src.extractors.yfinance_extract.time.sleep", return_value=None)
@patch("src.extractors.yfinance_extract.yf.Ticker")
def test_persistent_empty_raises(mock_ticker_cls, _mock_sleep):
    mock_ticker_cls.return_value = _make_mock_ticker(_make_yf_dataframe(empty=True))
    with pytest.raises(YFinanceError, match="Exhausted"):
        fetch_yfinance_history("SPY", retries=2, backoff_sec=0)


@patch("src.extractors.yfinance_extract.time.sleep", return_value=None)
@patch("src.extractors.yfinance_extract.yf.Ticker")
def test_exception_from_yfinance_triggers_retry(mock_ticker_cls, _mock_sleep):
    failing_tk = MagicMock()
    failing_tk.history.side_effect = Exception("Yahoo throttled")
    good_tk = _make_mock_ticker(_make_yf_dataframe())
    mock_ticker_cls.side_effect = [failing_tk, good_tk]

    df = fetch_yfinance_history("SPY", retries=3, backoff_sec=0)
    assert len(df) == 3


# ─── fetch_many ──────────────────────────────────────────────


@patch("src.extractors.yfinance_extract.yf.Ticker")
def test_fetch_many_concatenates(mock_ticker_cls):
    mock_ticker_cls.return_value = _make_mock_ticker(_make_yf_dataframe())
    df = fetch_many(["SPY", "QQQ"], period="1mo")
    assert set(df["ticker"]) == {"SPY", "QQQ"}
    assert len(df) == 6  # 3 rows x 2 tickers
