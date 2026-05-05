"""Tests for the Alpha Vantage extractor.

Owner: Diana Lucero

We don't hit the live API in tests — we mock requests.get so the test
suite runs offline, fast, and doesn't burn through the 25 req/day quota.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.extractors.alpha_vantage import (
    AlphaVantageError,
    fetch_daily_ohlcv,
    fetch_many,
)

# A minimal but realistic Alpha Vantage payload (truncated to 2 days).
SAMPLE_PAYLOAD = {
    "Meta Data": {
        "1. Information": "Daily Prices",
        "2. Symbol": "SPY",
    },
    "Time Series (Daily)": {
        "2026-05-04": {
            "1. open": "720.0700",
            "2. high": "722.1200",
            "3. low": "714.9900",
            "4. close": "718.0100",
            "5. volume": "51950558",
        },
        "2026-05-01": {
            "1. open": "721.2500",
            "2. high": "724.8700",
            "3. low": "720.4700",
            "4. close": "720.6500",
            "5. volume": "43049849",
        },
    },
}


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch):
    """Ensure ALPHA_VANTAGE_API_KEY is always set during tests."""
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "TEST_KEY")


def _make_response(payload: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


# ─── Happy path ──────────────────────────────────────────────


@patch("src.extractors.alpha_vantage.requests.get")
def test_fetch_daily_ohlcv_returns_clean_dataframe(mock_get):
    mock_get.return_value = _make_response(SAMPLE_PAYLOAD)

    df = fetch_daily_ohlcv("SPY", outputsize="compact")

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == ["ticker", "open", "high", "low", "close", "volume"]
    assert df.index.name == "date"
    assert pd.api.types.is_datetime64_any_dtype(df.index)
    assert (df["ticker"] == "SPY").all()
    # Sorted descending (latest first)
    assert df.index[0] > df.index[-1]
    # Numeric types
    assert df["close"].dtype == float
    assert df["volume"].dtype == "int64"


@patch("src.extractors.alpha_vantage.requests.get")
def test_fetch_daily_ohlcv_uppercases_ticker(mock_get):
    mock_get.return_value = _make_response(SAMPLE_PAYLOAD)
    df = fetch_daily_ohlcv("spy")
    assert (df["ticker"] == "SPY").all()


# ─── Error handling ──────────────────────────────────────────


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    with pytest.raises(AlphaVantageError, match="ALPHA_VANTAGE_API_KEY not set"):
        fetch_daily_ohlcv("SPY")


@patch("src.extractors.alpha_vantage.requests.get")
def test_api_error_message_raises(mock_get):
    mock_get.return_value = _make_response(
        {"Error Message": "Invalid API call"}
    )
    with pytest.raises(AlphaVantageError, match="API error"):
        fetch_daily_ohlcv("BADTICKER")


@patch("src.extractors.alpha_vantage.requests.get")
def test_unexpected_payload_raises(mock_get):
    mock_get.return_value = _make_response({"unexpected": "shape"})
    with pytest.raises(AlphaVantageError, match="Unexpected payload"):
        fetch_daily_ohlcv("SPY")


# ─── Rate-limit retry behavior ──────────────────────────────


@patch("src.extractors.alpha_vantage.time.sleep", return_value=None)
@patch("src.extractors.alpha_vantage.requests.get")
def test_rate_limit_note_triggers_retry_then_succeeds(mock_get, _mock_sleep):
    rate_limited = _make_response(
        {"Note": "Thank you for using Alpha Vantage! Our standard API rate limit is..."}
    )
    success = _make_response(SAMPLE_PAYLOAD)
    mock_get.side_effect = [rate_limited, success]

    df = fetch_daily_ohlcv("SPY", retries=3, backoff_sec=0)
    assert len(df) == 2
    assert mock_get.call_count == 2


@patch("src.extractors.alpha_vantage.time.sleep", return_value=None)
@patch("src.extractors.alpha_vantage.requests.get")
def test_persistent_rate_limit_eventually_raises(mock_get, _mock_sleep):
    mock_get.return_value = _make_response({"Note": "rate limited"})
    with pytest.raises(AlphaVantageError, match="Exhausted"):
        fetch_daily_ohlcv("SPY", retries=2, backoff_sec=0)
    assert mock_get.call_count == 2


# ─── fetch_many ──────────────────────────────────────────────


@patch("src.extractors.alpha_vantage.time.sleep", return_value=None)
@patch("src.extractors.alpha_vantage.requests.get")
def test_fetch_many_concatenates_tickers(mock_get, _mock_sleep):
    mock_get.return_value = _make_response(SAMPLE_PAYLOAD)
    df = fetch_many(["SPY", "QQQ"])
    assert set(df["ticker"]) == {"SPY", "QQQ"}
    assert len(df) == 4  # 2 days x 2 tickers
