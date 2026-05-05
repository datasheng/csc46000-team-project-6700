"""Alpha Vantage extractor — pulls daily OHLCV for ETF tickers (SPY, QQQ).

Owner: Diana Lucero

Usage:
    from src.extractors.alpha_vantage import fetch_daily_ohlcv
    df = fetch_daily_ohlcv("SPY")
    df = fetch_daily_ohlcv("QQQ", outputsize="full")

API docs: https://www.alphavantage.co/documentation/#daily
Free tier: 25 requests/day, 5 requests/minute. Plan accordingly.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Literal

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
DEFAULT_TIMEOUT_SEC = 30


class AlphaVantageError(Exception):
    """Raised when the Alpha Vantage API returns an error or unexpected payload."""


def _get_api_key() -> str:
    key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not key:
        raise AlphaVantageError(
            "ALPHA_VANTAGE_API_KEY not set. Copy .env.example to .env and add your key."
        )
    return key


def fetch_daily_ohlcv(
    ticker: str,
    outputsize: Literal["compact", "full"] = "compact",
    retries: int = 3,
    backoff_sec: float = 15.0,
) -> pd.DataFrame:
    """Fetch daily OHLCV time series for a ticker from Alpha Vantage.

    Args:
        ticker: e.g. "SPY", "QQQ"
        outputsize: "compact" (last 100 days) or "full" (~20+ years)
        retries: how many times to retry on rate-limit / transient errors
        backoff_sec: wait time between retries (Alpha Vantage free tier
            allows 5 requests/minute, so 15s is a safe floor)

    Returns:
        DataFrame indexed by date (descending) with columns:
            ticker, open, high, low, close, volume

    Raises:
        AlphaVantageError: if the API returns a recognizable error or
            we exhaust retries.
    """
    api_key = _get_api_key()
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": ticker,
        "outputsize": outputsize,
        "apikey": api_key,
        "datatype": "json",
    }

    last_error: str | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(
                ALPHA_VANTAGE_BASE_URL,
                params=params,
                timeout=DEFAULT_TIMEOUT_SEC,
            )
            resp.raise_for_status()
            payload = resp.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = f"network/parse error: {exc}"
            logger.warning("Alpha Vantage attempt %d failed: %s", attempt, last_error)
            time.sleep(backoff_sec)
            continue

        # Alpha Vantage returns 200 OK even on logical errors — inspect payload.
        if "Error Message" in payload:
            raise AlphaVantageError(f"API error for {ticker}: {payload['Error Message']}")
        if "Note" in payload or "Information" in payload:
            # Rate-limited — back off and retry.
            last_error = payload.get("Note") or payload.get("Information")
            logger.warning(
                "Alpha Vantage rate-limited on attempt %d: %s", attempt, last_error
            )
            time.sleep(backoff_sec)
            continue

        ts = payload.get("Time Series (Daily)")
        if not ts:
            raise AlphaVantageError(
                f"Unexpected payload shape for {ticker}: keys={list(payload.keys())}"
            )

        df = (
            pd.DataFrame.from_dict(ts, orient="index")
            .rename(
                columns={
                    "1. open": "open",
                    "2. high": "high",
                    "3. low": "low",
                    "4. close": "close",
                    "5. volume": "volume",
                }
            )
            .astype(float)
        )
        df.index = pd.to_datetime(df.index)
        df.index.name = "date"
        df["volume"] = df["volume"].astype("int64")
        df.insert(0, "ticker", ticker.upper())
        df = df.sort_index(ascending=False)
        return df

    raise AlphaVantageError(
        f"Exhausted {retries} retries fetching {ticker}. Last error: {last_error}"
    )


def fetch_many(
    tickers: list[str], outputsize: Literal["compact", "full"] = "compact"
) -> pd.DataFrame:
    """Fetch multiple tickers and return a single concatenated DataFrame.

    Honors free-tier rate limit by sleeping 15s between requests.
    """
    frames: list[pd.DataFrame] = []
    for i, t in enumerate(tickers):
        if i > 0:
            time.sleep(15)  # respect 5 req/min limit
        frames.append(fetch_daily_ohlcv(t, outputsize=outputsize))
    return pd.concat(frames).sort_values(["ticker", "date"], ascending=[True, False])


if __name__ == "__main__":
    # Quick smoke test: python -m src.extractors.alpha_vantage
    logging.basicConfig(level=logging.INFO)
    df = fetch_daily_ohlcv("SPY", outputsize="compact")
    print(df.head())
    print(f"\n{len(df)} rows fetched for SPY")
