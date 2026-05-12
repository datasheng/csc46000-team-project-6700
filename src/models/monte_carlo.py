"""
Karthikeya Reddy B — Sharpe Ratio, Monte Carlo & Risk Metrics

Analyzes SPY and QQQ over a 3-year window and simulates 5-year
portfolio outcomes for a $50,000 investment.

This module calculates:
    - Sharpe ratio for SPY vs QQQ
    - 10,000-path Monte Carlo simulation over 5-year horizon
    - Allocation grid search: 0–100% QQQ in 5% increments
    - Drawdown analysis including 95th percentile worst-case

Example Usage:

    import yfinance as yf
    from src.models.monte_carlo import run_monte_carlo

    prices = yf.download(
        ["SPY", "QQQ"],
        period="3y",
        auto_adjust=True,
        progress=False
    )["Close"]

    returns = prices.pct_change().dropna()

    results = run_monte_carlo(returns)

    print(results["summary"])
"""

import numpy as np
import pandas as pd


INITIAL_INVESTMENT = 50_000
TRADING_DAYS = 252
HORIZON_DAYS = 1260        # 5 years
N_SIMULATIONS = 10_000
RISK_FREE_RATE = 0.0425    # ~4.25% annualized (approx current T-bill)
RANDOM_SEED = 42


# ---------------------------------------------------------------------------
# Sharpe Ratio
# ---------------------------------------------------------------------------

def compute_sharpe(returns: pd.Series, risk_free_rate: float = RISK_FREE_RATE) -> float:
    """
    Compute annualized Sharpe ratio for a daily return series.

    Args:
        returns: daily return series for one asset
        risk_free_rate: annualized risk-free rate (default ~4.25%)

    Returns:
        Annualized Sharpe ratio as a float.
    """
    daily_rf = risk_free_rate / TRADING_DAYS
    excess = returns - daily_rf
    if excess.std() == 0:
        return 0.0
    return float((excess.mean() / excess.std()) * np.sqrt(TRADING_DAYS))


# ---------------------------------------------------------------------------
# Drawdown
# ---------------------------------------------------------------------------

def compute_drawdown(returns: pd.Series) -> dict:
    """
    Compute drawdown statistics for a daily return series.

    Args:
        returns: daily return series for one asset

    Returns:
        Dictionary with:
            - drawdown_series: full drawdown series
            - max_drawdown: worst peak-to-trough loss (negative float)
            - drawdown_pct95: 95th percentile worst-case drawdown
    """
    cumulative = (1 + returns).cumprod()
    rolling_max = cumulative.cummax()
    drawdown_series = (cumulative - rolling_max) / rolling_max

    return {
        "drawdown_series": drawdown_series,
        "max_drawdown": float(drawdown_series.min()),
        "drawdown_pct95": float(drawdown_series.quantile(0.05)),  # 5th pct of negatives = 95th worst
    }


# ---------------------------------------------------------------------------
# Monte Carlo
# ---------------------------------------------------------------------------

def run_monte_carlo(
    returns: pd.DataFrame,
    n_simulations: int = N_SIMULATIONS,
    horizon_days: int = HORIZON_DAYS,
    allocation_qqq: float = 0.50,
) -> dict:
    """
    Run Monte Carlo simulation for a blended SPY/QQQ portfolio.

    Args:
        returns: DataFrame with columns SPY and QQQ (daily returns)
        n_simulations: number of simulation paths (default 10,000)
        horizon_days: trading days to simulate (default 1260 = 5 years)
        allocation_qqq: fraction allocated to QQQ (default 0.50)

    Returns:
        Dictionary with:
            - simulation_paths: (horizon_days x n_simulations) array of portfolio values
            - final_values: array of final portfolio values across simulations
            - percentile_5: 5th percentile final value (worst-case)
            - percentile_50: median final value
            - percentile_95: 95th percentile final value (best-case)
            - prob_profit: probability of ending above initial investment
    """
    allocation_spy = 1.0 - allocation_qqq

    portfolio_returns = (
        returns["SPY"] * allocation_spy + returns["QQQ"] * allocation_qqq
    )

    mu = portfolio_returns.mean()
    sigma = portfolio_returns.std()

    rng = np.random.default_rng(RANDOM_SEED)
    daily_shocks = rng.normal(loc=mu, scale=sigma, size=(horizon_days, n_simulations))

    # Build cumulative value paths
    paths = np.ones((horizon_days + 1, n_simulations)) * INITIAL_INVESTMENT
    for t in range(1, horizon_days + 1):
        paths[t] = paths[t - 1] * (1 + daily_shocks[t - 1])

    final_values = paths[-1]

    return {
        "simulation_paths": paths,
        "final_values": final_values,
        "percentile_5": float(np.percentile(final_values, 5)),
        "percentile_50": float(np.percentile(final_values, 50)),
        "percentile_95": float(np.percentile(final_values, 95)),
        "prob_profit": float(np.mean(final_values > INITIAL_INVESTMENT)),
    }


# ---------------------------------------------------------------------------
# Allocation Grid Search
# ---------------------------------------------------------------------------

def allocation_grid_search(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Search across 0–100% QQQ allocations in 5% increments.

    Args:
        returns: DataFrame with columns SPY and QQQ (daily returns)

    Returns:
        DataFrame with columns:
            allocation_qqq, allocation_spy, expected_annual_return,
            annual_volatility, sharpe_ratio, final_value_median,
            final_value_pct5, final_value_pct95
    """
    rows = []

    for qqq_pct in range(0, 101, 5):
        qqq_w = qqq_pct / 100
        spy_w = 1.0 - qqq_w

        port_returns = returns["SPY"] * spy_w + returns["QQQ"] * qqq_w

        ann_return = float(port_returns.mean() * TRADING_DAYS)
        ann_vol = float(port_returns.std() * np.sqrt(TRADING_DAYS))
        sharpe = compute_sharpe(port_returns)

        mc = run_monte_carlo(returns, allocation_qqq=qqq_w)

        rows.append({
            "allocation_qqq": qqq_pct,
            "allocation_spy": 100 - qqq_pct,
            "expected_annual_return": round(ann_return, 6),
            "annual_volatility": round(ann_vol, 6),
            "sharpe_ratio": round(sharpe, 4),
            "final_value_median": round(mc["percentile_50"], 2),
            "final_value_pct5": round(mc["percentile_5"], 2),
            "final_value_pct95": round(mc["percentile_95"], 2),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_full_analysis(returns: pd.DataFrame) -> dict:
    """
    Run all Karthikeya metrics: Sharpe, Monte Carlo, grid search, drawdown.

    Args:
        returns: DataFrame with columns SPY and QQQ (daily returns)

    Returns:
        Dictionary with all results.
    """

    # Sharpe
    spy_sharpe = compute_sharpe(returns["SPY"])
    qqq_sharpe = compute_sharpe(returns["QQQ"])

    # Drawdown
    spy_dd = compute_drawdown(returns["SPY"])
    qqq_dd = compute_drawdown(returns["QQQ"])

    # Monte Carlo at 50/50 (default)
    mc_results = run_monte_carlo(returns, allocation_qqq=0.50)

    # Grid search
    grid = allocation_grid_search(returns)

    summary = {
        "spy_sharpe": round(spy_sharpe, 4),
        "qqq_sharpe": round(qqq_sharpe, 4),
        "spy_max_drawdown": round(spy_dd["max_drawdown"], 4),
        "qqq_max_drawdown": round(qqq_dd["max_drawdown"], 4),
        "qqq_drawdown_pct95": round(qqq_dd["drawdown_pct95"], 4),
        "mc_median_final_value": round(mc_results["percentile_50"], 2),
        "mc_pct5_final_value": round(mc_results["percentile_5"], 2),
        "mc_pct95_final_value": round(mc_results["percentile_95"], 2),
        "mc_prob_profit": round(mc_results["prob_profit"], 4),
    }

    return {
        "summary": summary,
        "grid_search": grid,
        "spy_drawdown_series": spy_dd["drawdown_series"],
        "qqq_drawdown_series": qqq_dd["drawdown_series"],
        "mc_final_values": mc_results["final_values"],
    }


if __name__ == "__main__":
    import yfinance as yf

    prices = yf.download(
        ["SPY", "QQQ"],
        period="3y",
        auto_adjust=True,
        progress=False,
    )["Close"]

    returns = prices.pct_change().dropna()
    results = run_full_analysis(returns)

    print("\n=== SUMMARY ===")
    for k, v in results["summary"].items():
        print(f"  {k}: {v}")

    print("\n=== ALLOCATION GRID (top 5 by Sharpe) ===")
    print(results["grid_search"].sort_values("sharpe_ratio", ascending=False).head())