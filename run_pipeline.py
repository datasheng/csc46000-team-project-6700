"""
Group 6700 — run_pipeline.py
Jacob Li — Main pipeline script.

Run this to pull live data from yFinance, compute all metrics,
and load everything into MySQL via loaders.py.

Requirements:
    pip install yfinance pandas numpy sqlalchemy pymysql scipy
    
Usage:
    python run_pipeline.py
"""

import yfinance as yf
import pandas as pd
import numpy as np
from scipy import stats
from loaders import (
    load_prices,
    load_daily_metrics,
    load_monte_carlo,
    load_ab_results,
    get_engine
)
from sqlalchemy import text

# ── Config ────────────────────────────────────────────────────────────────────
TICKERS       = ["SPY", "QQQ"]
PERIOD        = "3y"
TRADING_DAYS  = 252
RISK_FREE     = 0.05
INITIAL       = 50000
ROLLING_WIN   = 21  # ~1 month

print("=" * 60)
print("Group 6700 — ETF Pipeline Starting")
print("=" * 60)

# ── 1. Extract ────────────────────────────────────────────────────────────────
print("\n[1/5] Pulling data from yFinance...")
raw    = yf.download(TICKERS, period=PERIOD, interval="1d",
                     auto_adjust=True, progress=False)
prices = raw["Close"].dropna()
prices.index = pd.to_datetime(prices.index)

volume_raw = raw["Volume"].dropna()

print(f"      Got {len(prices)} trading days for {TICKERS}")

# ── 2. Load raw prices ────────────────────────────────────────────────────────
print("\n[2/5] Loading raw prices into MySQL...")
price_rows = []
for ticker in TICKERS:
    for date, close in prices[ticker].items():
        vol = volume_raw[ticker].get(date, None)
        price_rows.append({
            "date":   date.date(),
            "ticker": ticker,
            "open":   None,
            "high":   None,
            "low":    None,
            "close":  round(float(close), 4),
            "volume": int(vol) if pd.notna(vol) else None
        })

prices_df = pd.DataFrame(price_rows)
load_prices(prices_df)

# ── 3. Compute and load daily metrics ─────────────────────────────────────────
print("\n[3/5] Computing metrics and loading daily_metrics...")
returns    = prices.pct_change().dropna()
cumulative = (1 + returns).cumprod()

metric_rows = []
for ticker in TICKERS:
    ret = returns[ticker]
    cum = cumulative[ticker]
    rolling_vol = ret.rolling(ROLLING_WIN).std() * np.sqrt(TRADING_DAYS)
    drawdown    = (cum - cum.cummax()) / cum.cummax()

    for date in ret.index:
        metric_rows.append({
            "date":               date.date(),
            "ticker":             ticker,
            "daily_return":       round(float(ret[date]), 6),
            "cumulative_return":  round(float(cum[date]), 6),
            "rolling_volatility": round(float(rolling_vol[date]), 6) if pd.notna(rolling_vol[date]) else None,
            "drawdown":           round(float(drawdown[date]), 6),
        })

metrics_df = pd.DataFrame(metric_rows)
metrics_df = metrics_df.where(pd.notna(metrics_df), other=None)
load_daily_metrics(metrics_df)

# ── 4. Monte Carlo allocation grid ────────────────────────────────────────────
print("\n[4/5] Running Monte Carlo allocation grid...")
mc_rows = []

for qqq_pct in range(0, 105, 5):
    spy_pct = 100 - qqq_pct
    w_qqq   = qqq_pct / 100
    w_spy   = spy_pct / 100

    # Portfolio daily returns for this allocation
    port_ret = returns["SPY"] * w_spy + returns["QQQ"] * w_qqq

    # Annualized stats
    ann_ret = port_ret.mean() * TRADING_DAYS
    ann_vol = port_ret.std()  * np.sqrt(TRADING_DAYS)
    sharpe  = round((ann_ret - RISK_FREE) / ann_vol, 6) if ann_vol > 0 else 0

    # Monte Carlo — 10,000 paths over 5 years
    n_paths = 10000
    n_days  = TRADING_DAYS * 5
    daily_mean = port_ret.mean()
    daily_std  = port_ret.std()

    sim = np.random.normal(daily_mean, daily_std, (n_days, n_paths))
    final_vals = INITIAL * np.prod(1 + sim, axis=0)

    median_outcome  = round(float(np.median(final_vals)), 2)
    worst_case_p95  = round(float(np.percentile(final_vals, 5)), 2)

    mc_rows.append({
        "qqq_pct":        qqq_pct,
        "spy_pct":        spy_pct,
        "expected_return": round(ann_ret, 6),
        "volatility":     round(ann_vol, 6),
        "sharpe_ratio":   sharpe,
        "worst_case_p95": worst_case_p95,
        "median_outcome": median_outcome,
    })

mc_df = pd.DataFrame(mc_rows)
load_monte_carlo(mc_df)
print(f"      Ran {len(mc_rows)} allocation scenarios (0-100% QQQ in 5% steps)")

# ── 5. A/B Test ───────────────────────────────────────────────────────────────
print("\n[5/5] Running A/B test and loading results...")

returns["Strategy_A_6040"] = returns["SPY"] * 0.60 + returns["QQQ"] * 0.40
returns["Strategy_B_5050"] = returns["SPY"] * 0.50 + returns["QQQ"] * 0.50

cum_ab = (1 + returns[["Strategy_A_6040", "Strategy_B_5050"]]).cumprod()

ab_rows = []
for date in returns.index:
    for strat, col in [("A_6040", "Strategy_A_6040"), ("B_5050", "Strategy_B_5050")]:
        ab_rows.append({
            "date":              date.date(),
            "strategy":          strat,
            "portfolio_value":   round(float(cum_ab[col][date] * INITIAL), 2),
            "cumulative_return": round(float(cum_ab[col][date]), 6),
            "daily_return":      round(float(returns[col][date]), 6),
        })

ab_df = pd.DataFrame(ab_rows)

# T-test
t_stat, p_val = stats.ttest_ind(
    returns["Strategy_A_6040"],
    returns["Strategy_B_5050"]
)

strategy_a_final = round(float(cum_ab["Strategy_A_6040"].iloc[-1] * INITIAL), 2)
strategy_b_final = round(float(cum_ab["Strategy_B_5050"].iloc[-1] * INITIAL), 2)

sig = "statistically significant" if p_val < 0.05 else "not statistically significant"
recommendation = (
    f"Based on our 3-year analysis of SPY vs QQQ, the difference between a 60/40 "
    f"and 50/50 allocation is {sig} (p={round(p_val,4)}). "
    f"Strategy A (60% SPY / 40% QQQ) grew $50,000 to ${strategy_a_final:,.2f}, "
    f"while Strategy B (50% SPY / 50% QQQ) grew to ${strategy_b_final:,.2f}. "
    f"Given QQQ's higher Sharpe ratio but greater volatility, we recommend the "
    f"60/40 split for risk-averse retail investors seeking balanced exposure."
)

load_ab_results(
    df=ab_df,
    t_stat=t_stat,
    p_val=p_val,
    strategy_a_final=strategy_a_final,
    strategy_b_final=strategy_b_final,
    recommendation=recommendation
)

# ── Done ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("Pipeline complete! All tables loaded.")
print("=" * 60)

# Quick summary
engine = get_engine()
with engine.connect() as conn:
    for table in ["prices", "daily_metrics", "monte_carlo_results", "ab_test_results"]:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        print(f"  {table}: {count} rows")

print("\nTableau is ready — refresh your data source to see the data.")
