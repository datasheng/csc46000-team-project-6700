"""yFinance extractor — supplemental price + dividend data.

Owner: Diana Lucero

yFinance does not require an API key. It scrapes/wraps Yahoo Finance,
so it occasionally rate-limits or returns empty frames; we add light retry.

Usage:
    from src.extractors.yfinance_extract import fetch_yfinance_history
    df = fetch_yfinance_history("SPY", period="3y")
"""

from __future__ import annotations

import logging
import time
from typing import Literal

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

Period = Literal["1mo", "3mo", "6mo", "1y", "2y", "3y", "5y", "10y", "max"]
Interval = Literal["1d", "1wk", "1mo"]


class YFinanceError(Exception):
    """Raised when yFinance returns an empty/invalid response."""


def fetch_yfinance_history(
    ticker: str,
    period: Period = "3y",
    interval: Interval = "1d",
    retries: int = 3,
    backoff_sec: float = 5.0,
) -> pd.DataFrame:
    """Fetch historical price + dividend data for a ticker via yFinance.

    Args:
        ticker: e.g. "SPY", "QQQ"
        period: lookback window (default 3y to match the 3-year analysis)
        interval: bar size (default daily)
        retries: number of retries on empty response
        backoff_sec: wait time between retries

    Returns:
        DataFrame with columns:
            ticker, open, high, low, close, adj_close, volume, dividends, stock_splits
        indexed by date (descending).
    """
    last_error: str | None = None
    for attempt in range(1, retries + 1):
        try:
            tk = yf.Ticker(ticker)
            df = tk.history(period=period, interval=interval, auto_adjust=False)
        except Exception as exc:  # yfinance raises plain Exceptions
            last_error = str(exc)
            logger.warning(
                "yFinance attempt %d failed for %s: %s", attempt, ticker, exc
            )
            time.sleep(backoff_sec)
            continue

        if df is None or df.empty:
            last_error = "empty dataframe returned"
            logger.warning("yFinance returned empty frame for %s (attempt %d)", ticker, attempt)
            time.sleep(backoff_sec)
            continue

        df = df.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "volume",
                "Dividends": "dividends",
                "Stock Splits": "stock_splits",
                "Capital Gains": "capital_gains",
            }
        )
        # Catch-all: any future yfinance columns get normalized to snake_case
        # so the downstream transform layer doesn't break on new releases.
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
        # yfinance sometimes returns a tz-aware DatetimeIndex; normalize to naive UTC.
        if df.index.tz is not None:
            df.index = df.index.tz_convert("UTC").tz_localize(None)
        df.index.name = "date"
        df.insert(0, "ticker", ticker.upper())
        df = df.sort_index(ascending=False)
        return df

    raise YFinanceError(
        f"Exhausted {retries} retries fetching {ticker}. Last error: {last_error}"
    )


def fetch_many(tickers: list[str], period: Period = "3y") -> pd.DataFrame:
    """Fetch multiple tickers and return a single concatenated DataFrame."""
    frames = [fetch_yfinance_history(t, period=period) for t in tickers]
    return pd.concat(frames).sort_values(["ticker", "date"], ascending=[True, False])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = fetch_yfinance_history("SPY", period="1mo")
    print(df.head())
    print(f"\n{len(df)} rows fetched for SPY")
