"""
Edison Florian — A/B Test & Statistical Validation

Compares two SPY/QQQ portfolio strategies:

Strategy A:
    60% SPY / 40% QQQ

Strategy B:
    50% SPY / 50% QQQ

This module calculates:
    - daily portfolio returns
    - cumulative portfolio growth
    - final value of a $50,000 investment
    - t-test for statistical significance
    - bootstrap confidence interval
    - business recommendation
"""

"""
Example Usage:

import yfinance as yf
from src.models.ab_test import run_ab_test

prices = yf.download(
    ["SPY", "QQQ"],
    period="3y",
    auto_adjust=True,
    progress=False
)["Close"]

returns = prices.pct_change().dropna()

results = run_ab_test(returns)

print(results["summary"])
"""

import numpy as np
import pandas as pd
from scipy import stats


INITIAL_INVESTMENT = 50_000
TRADING_DAYS = 252
BOOTSTRAP_SAMPLES = 1000


def build_ab_portfolios(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Create Strategy A and Strategy B from SPY and QQQ daily returns.

    Expected input columns:
        SPY
        QQQ
    """

    df = returns.copy()

    df["Strategy_A_6040"] = df["SPY"] * 0.60 + df["QQQ"] * 0.40
    df["Strategy_B_5050"] = df["SPY"] * 0.50 + df["QQQ"] * 0.50

    return df


def run_ab_test(returns: pd.DataFrame) -> dict:
    """
    Run A/B portfolio analysis.

    Returns a dictionary containing:
        - daily results
        - summary results
        - t-test
        - bootstrap confidence interval
        - recommendation
    """

    df = build_ab_portfolios(returns)

    cumulative = (1 + df[["Strategy_A_6040", "Strategy_B_5050"]]).cumprod()

    strategy_a_final = float(cumulative["Strategy_A_6040"].iloc[-1] * INITIAL_INVESTMENT)
    strategy_b_final = float(cumulative["Strategy_B_5050"].iloc[-1] * INITIAL_INVESTMENT)

    strategy_a_vol = float(df["Strategy_A_6040"].std() * np.sqrt(TRADING_DAYS))
    strategy_b_vol = float(df["Strategy_B_5050"].std() * np.sqrt(TRADING_DAYS))

    strategy_a_ann_return = float(df["Strategy_A_6040"].mean() * TRADING_DAYS)
    strategy_b_ann_return = float(df["Strategy_B_5050"].mean() * TRADING_DAYS)

    t_stat, p_value = stats.ttest_ind(
        df["Strategy_A_6040"],
        df["Strategy_B_5050"],
        equal_var=False,
    )

    bootstrap_diffs = []

    for _ in range(BOOTSTRAP_SAMPLES):
        sample = df.sample(n=len(df), replace=True)

        diff = (
            sample["Strategy_A_6040"].mean()
            - sample["Strategy_B_5050"].mean()
        )

        bootstrap_diffs.append(diff)

    ci_lower = float(np.percentile(bootstrap_diffs, 2.5))
    ci_upper = float(np.percentile(bootstrap_diffs, 97.5))

    significant = bool(p_value < 0.05)

    if not significant and strategy_a_vol < strategy_b_vol:
        recommendation = (
            "Although Strategy B produced a slightly higher final value, the "
            "difference was not statistically significant. Since Strategy A has "
            "lower volatility, the 60/40 allocation is the safer recommendation "
            "for risk-aware investors."
        )
    elif significant and strategy_b_final > strategy_a_final:
        recommendation = (
            "Strategy B produced a higher final value and the difference was "
            "statistically significant. This supports the 50/50 allocation for "
            "investors willing to accept higher QQQ exposure."
        )
    else:
        recommendation = (
            "The strategies performed similarly. Investors should choose based "
            "on their risk tolerance and desired QQQ exposure."
        )

    daily_results = pd.DataFrame({
        "date": df.index,
        "strategy_a_daily_return": df["Strategy_A_6040"].values,
        "strategy_b_daily_return": df["Strategy_B_5050"].values,
        "strategy_a_cumulative_return": cumulative["Strategy_A_6040"].values,
        "strategy_b_cumulative_return": cumulative["Strategy_B_5050"].values,
        "strategy_a_portfolio_value": cumulative["Strategy_A_6040"].values * INITIAL_INVESTMENT,
        "strategy_b_portfolio_value": cumulative["Strategy_B_5050"].values * INITIAL_INVESTMENT,
    })

    summary = {
        "strategy_a_final_value": round(strategy_a_final, 2),
        "strategy_b_final_value": round(strategy_b_final, 2),
        "strategy_a_annualized_return": round(strategy_a_ann_return, 6),
        "strategy_b_annualized_return": round(strategy_b_ann_return, 6),
        "strategy_a_volatility": round(strategy_a_vol, 6),
        "strategy_b_volatility": round(strategy_b_vol, 6),
        "t_statistic": round(float(t_stat), 6),
        "p_value": round(float(p_value), 6),
        "significant": significant,
        "bootstrap_ci_lower": round(ci_lower, 8),
        "bootstrap_ci_upper": round(ci_upper, 8),
        "recommendation": recommendation,
    }

    return {
        "daily_results": daily_results,
        "summary": summary,
    }