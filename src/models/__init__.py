"""Modeling layer.

Owners:
    - Karthikeya: Sharpe ratio, Monte Carlo simulation
    - Edison: A/B test (60/40 vs equal-weight) + bootstrap + t-test
    - Nick: Custom ML/DL model (extra credit)
"""
from src.models.monte_carlo import run_full_analysis, run_monte_carlo, compute_sharpe, compute_drawdown, allocation_grid_search
from src.models.ab_test import run_ab_test