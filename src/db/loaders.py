"""
Database loaders — push model results to MySQL.

Owners:
    - Karthikeya: load_monte_carlo
    (Jacob will add remaining loaders on merge)
"""

import pandas as pd
from sqlalchemy import create_engine


def load_monte_carlo(grid_df: pd.DataFrame, engine) -> None:
    """
    Load Monte Carlo + allocation grid results into MySQL.

    Args:
        grid_df: DataFrame from allocation_grid_search() with columns:
            allocation_qqq, allocation_spy, expected_annual_return,
            annual_volatility, sharpe_ratio, final_value_median,
            final_value_pct5, final_value_pct95
        engine: SQLAlchemy engine connected to etf_db

    Usage:
        from sqlalchemy import create_engine
        from src.db.loaders import load_monte_carlo
        from src.models.monte_carlo import allocation_grid_search

        engine = create_engine("mysql+pymysql://etf_user:group6700@localhost:3306/etf_db")
        results = run_full_analysis(returns)
        load_monte_carlo(results["grid_search"], engine)
    """
    grid_df.to_sql(
        name="monte_carlo_results",
        con=engine,
        if_exists="append",
        index=False,
    )
    print(f"[load_monte_carlo] Inserted {len(grid_df)} rows into monte_carlo_results.")