"""
Group 6700 — loaders.py
Jacob Li — Database loader functions.

Each function takes a Pandas DataFrame and inserts it into the correct MySQL table.
The team calls these functions from their own scripts — they don't touch MySQL directly.

Usage:
    from loaders import load_prices, load_daily_metrics, load_monte_carlo, load_ab_results, load_predictions

Requirements:
    pip install sqlalchemy pymysql pandas
"""

import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime


def _clean_nan(df: pd.DataFrame) -> pd.DataFrame:
    """Replace all NaN values with None so pymysql/MySQL accepts them."""
    return df.astype(object).where(pd.notna(df), other=None)

# ── Database connection ───────────────────────────────────────────────────────
# Reads from environment or uses Docker defaults
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "etf_user")
DB_PASS = os.getenv("DB_PASS", "group6700")
DB_NAME = os.getenv("DB_NAME", "etf_db")

def get_engine():
    url = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(url)


# ── Loader 1: prices (Diana calls this) ──────────────────────────────────────
def load_prices(df: pd.DataFrame):
    """
    Insert raw OHLCV prices into the prices table.
    Expected columns: date, ticker, open, high, low, close, volume
    Duplicate (date, ticker) pairs are ignored — append-only, no overwrites.

    Example:
        df = pd.DataFrame({
            'date': ['2024-01-02'], 'ticker': ['SPY'],
            'open': [470.1], 'high': [472.3], 'low': [469.0],
            'close': [471.5], 'volume': [82000000]
        })
        load_prices(df)
    """
    engine = get_engine()
    df = df.copy()
    df = _clean_nan(df)
    df['date'] = pd.to_datetime(df['date']).dt.date

    # to_sql doesn't handle composite primary key conflicts on its own
    # so we use INSERT IGNORE via raw SQL for duplicate safety
    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT IGNORE INTO prices (date, ticker, open, high, low, close, volume)
                VALUES (:date, :ticker, :open, :high, :low, :close, :volume)
            """), row.to_dict())

    print(f"[load_prices] Inserted {len(df)} rows into prices table.")


# ── Loader 2: daily_metrics (Jacob computes and loads this) ──────────────────
def load_daily_metrics(df: pd.DataFrame):
    """
    Insert computed daily metrics into daily_metrics table.
    Expected columns: date, ticker, daily_return, cumulative_return,
                      rolling_volatility, drawdown

    This is called internally by Jacob's transform pipeline,
    not directly by the DS team.
    """
    engine = get_engine()
    df = df.copy()
    df = _clean_nan(df)
    df['date'] = pd.to_datetime(df['date']).dt.date

    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT IGNORE INTO daily_metrics
                    (date, ticker, daily_return, cumulative_return, rolling_volatility, drawdown)
                VALUES
                    (:date, :ticker, :daily_return, :cumulative_return, :rolling_volatility, :drawdown)
            """), row.to_dict())

    print(f"[load_daily_metrics] Inserted {len(df)} rows into daily_metrics table.")


# ── Loader 3: monte_carlo_results (Karthikeya calls this) ────────────────────
def load_monte_carlo(df: pd.DataFrame):
    """
    Insert Monte Carlo allocation grid results.
    Expected columns: qqq_pct, spy_pct, expected_return, volatility,
                      sharpe_ratio, worst_case_p95, median_outcome

    Example:
        df has 21 rows (0% to 100% QQQ in 5% increments)
        load_monte_carlo(df)
    """
    engine = get_engine()
    df = df.copy()
    df = _clean_nan(df)

    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT IGNORE INTO monte_carlo_results
                    (qqq_pct, spy_pct, expected_return, volatility,
                     sharpe_ratio, worst_case_p95, median_outcome)
                VALUES
                    (:qqq_pct, :spy_pct, :expected_return, :volatility,
                     :sharpe_ratio, :worst_case_p95, :median_outcome)
            """), row.to_dict())

    print(f"[load_monte_carlo] Inserted {len(df)} rows into monte_carlo_results table.")


# ── Loader 4: ab_test_results (Edison calls this) ────────────────────────────
def load_ab_results(df: pd.DataFrame, t_stat: float, p_val: float,
                    strategy_a_final: float, strategy_b_final: float,
                    recommendation: str = ""):
    """
    Insert daily A/B portfolio values AND the t-test summary.
    df expected columns: date, strategy, portfolio_value, cumulative_return, daily_return
    strategy values should be: 'A_6040' or 'B_5050'

    Example:
        load_ab_results(
            df=ab_daily_df,
            t_stat=-0.0118,
            p_val=0.99,
            strategy_a_final=68500.00,
            strategy_b_final=70200.00,
            recommendation="Based on our analysis..."
        )
    """
    engine = get_engine()
    df = df.copy()
    df = _clean_nan(df)
    df['date'] = pd.to_datetime(df['date']).dt.date

    # Insert daily rows
    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT IGNORE INTO ab_test_results
                    (date, strategy, portfolio_value, cumulative_return, daily_return)
                VALUES
                    (:date, :strategy, :portfolio_value, :cumulative_return, :daily_return)
            """), row.to_dict())

    # Insert summary row
    significant = 1 if p_val < 0.05 else 0
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO ab_test_summary
                (t_statistic, p_value, significant,
                 strategy_a_final, strategy_b_final, recommendation)
            VALUES
                (:t_stat, :p_val, :significant,
                 :strategy_a_final, :strategy_b_final, :recommendation)
        """), {
            "t_stat": round(t_stat, 6),
            "p_val": round(p_val, 6),
            "significant": significant,
            "strategy_a_final": strategy_a_final,
            "strategy_b_final": strategy_b_final,
            "recommendation": recommendation
        })

    print(f"[load_ab_results] Inserted {len(df)} daily rows + summary into ab_test tables.")


# ── Loader 5: ml_predictions (Nick calls this) ───────────────────────────────
def load_predictions(df: pd.DataFrame):
    """
    Insert ML model predictions into ml_predictions table.
    Expected columns: date, ticker, predicted_return, actual_return, model_type

    Example:
        df = pd.DataFrame({
            'date': ['2024-01-02', '2024-01-02'],
            'ticker': ['SPY', 'QQQ'],
            'predicted_return': [0.0012, 0.0018],
            'actual_return': [0.0010, 0.0021],
            'model_type': ['LSTM', 'LSTM']
        })
        load_predictions(df)
    """
    engine = get_engine()
    df = df.copy()
    df = _clean_nan(df)
    df['date'] = pd.to_datetime(df['date']).dt.date

    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(text("""
                INSERT IGNORE INTO ml_predictions
                    (date, ticker, predicted_return, actual_return, model_type)
                VALUES
                    (:date, :ticker, :predicted_return, :actual_return, :model_type)
            """), row.to_dict())

    print(f"[load_predictions] Inserted {len(df)} rows into ml_predictions table.")


# ── Transform + load pipeline (Jacob runs this after Diana extracts) ─────────
def run_transform_and_load(prices_df: pd.DataFrame):
    """
    Takes raw prices DataFrame from Diana's extractor,
    computes all daily metrics, and loads both tables.
    Call this from your main pipeline script.
    """
    import numpy as np

    df = prices_df.copy()
    df = df.sort_values(['ticker', 'date'])
    df['date'] = pd.to_datetime(df['date'])

    results = []
    ROLLING_WINDOW = 21  # ~1 month of trading days

    for ticker, group in df.groupby('ticker'):
        group = group.set_index('date').sort_index()
        daily_ret = group['close'].pct_change()
        cum_ret = (1 + daily_ret).cumprod()
        rolling_vol = daily_ret.rolling(ROLLING_WINDOW).std() * np.sqrt(252)
        drawdown = (cum_ret - cum_ret.cummax()) / cum_ret.cummax()

        for date in group.index:
            results.append({
                'date': date,
                'ticker': ticker,
                'daily_return': round(daily_ret.get(date, None), 6) if pd.notna(daily_ret.get(date, None)) else None,
                'cumulative_return': round(cum_ret.get(date, None), 6) if pd.notna(cum_ret.get(date, None)) else None,
                'rolling_volatility': round(rolling_vol.get(date, None), 6) if pd.notna(rolling_vol.get(date, None)) else None,
                'drawdown': round(drawdown.get(date, None), 6) if pd.notna(drawdown.get(date, None)) else None,
            })

    metrics_df = pd.DataFrame(results)
    load_daily_metrics(metrics_df)
    print("[run_transform_and_load] Transform + load complete.")
