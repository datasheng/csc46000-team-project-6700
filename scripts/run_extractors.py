"""End-to-end extractor runner — pulls SPY + QQQ from both APIs.

Owner: Diana Lucero

This is the handoff point for Mohmed's transform layer. It produces
two pandas DataFrames in the canonical shape the rest of the pipeline
expects:

    primary_df:    one row per (date, ticker), columns =
                   [ticker, open, high, low, close, volume]
    supplement_df: one row per (date, ticker), columns =
                   [ticker, open, high, low, close, adj_close, volume,
                    dividends, stock_splits]

Run:
    python -m scripts.run_extractors                     # default 3y, both tickers
    python -m scripts.run_extractors --period 1y         # shorter window
    python -m scripts.run_extractors --tickers SPY,QQQ   # override tickers
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Tuple

import pandas as pd
from dotenv import load_dotenv

from src.extractors.alpha_vantage import fetch_many as av_fetch_many
from src.extractors.yfinance_extract import fetch_many as yf_fetch_many

load_dotenv()
logger = logging.getLogger(__name__)


def run(
    tickers: list[str],
    period: str = "3y",
    av_outputsize: str = "full",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Pull both APIs and return (alpha_vantage_df, yfinance_df).

    Args:
        tickers: list of ticker strings, e.g. ["SPY", "QQQ"]
        period: yFinance lookback window
        av_outputsize: "compact" (100 days) or "full" (~20+ years)
    """
    logger.info("Fetching Alpha Vantage daily OHLCV for %s", tickers)
    av_df = av_fetch_many(tickers, outputsize=av_outputsize)
    logger.info("Alpha Vantage: %d rows fetched", len(av_df))

    logger.info("Fetching yFinance supplemental data for %s", tickers)
    yf_df = yf_fetch_many(tickers, period=period)
    logger.info("yFinance: %d rows fetched", len(yf_df))

    return av_df, yf_df


def _summary(df: pd.DataFrame, name: str) -> None:
    print(f"\n=== {name} ===")
    print(f"Rows: {len(df):,}")
    print(f"Tickers: {sorted(df['ticker'].unique())}")
    if not df.empty:
        print(f"Date range: {df.index.min().date()} → {df.index.max().date()}")
    print(f"Columns: {list(df.columns)}")
    print("\nLatest rows:")
    print(df.head().to_string())


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SPY/QQQ extractors end-to-end.")
    parser.add_argument(
        "--tickers",
        default=os.getenv("TICKERS", "SPY,QQQ"),
        help="Comma-separated tickers (default from .env or SPY,QQQ)",
    )
    parser.add_argument(
        "--period",
        default="3y",
        help="yFinance lookback period (default 3y)",
    )
    parser.add_argument(
        "--av-outputsize",
        choices=["compact", "full"],
        default="compact",
        help="Alpha Vantage outputsize (default compact to conserve quota)",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if not tickers:
        print("ERROR: no tickers provided", file=sys.stderr)
        return 1

    try:
        av_df, yf_df = run(
            tickers=tickers,
            period=args.period,
            av_outputsize=args.av_outputsize,
        )
    except Exception as exc:  # noqa: BLE001 — top-level CLI handler
        logger.error("Extractor run failed: %s", exc, exc_info=True)
        return 1

    _summary(av_df, "Alpha Vantage")
    _summary(yf_df, "yFinance")
    print("\nReady for handoff to transform layer (src/transform/) — Mohmed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
