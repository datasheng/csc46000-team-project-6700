"""
scripts/load_monte_carlo.py
Load Karthikeya's Monte Carlo allocation grid into MySQL.

Usage:
    python scripts/load_monte_carlo.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf
import pandas as pd
from sqlalchemy import text

from src.models.monte_carlo import allocation_grid_search
from src.db.loaders import load_monte_carlo, get_engine

# ── 1. Pull data ──────────────────────────────────────────────────────────────
print("Pulling SPY + QQQ (3y) from yFinance...")
prices = yf.download(
    ["SPY", "QQQ"], period="3y", auto_adjust=True, progress=False
)["Close"].dropna()
returns = prices.pct_change().dropna()
print(f"  {len(returns)} trading days loaded.")

# ── 2. Run Karthikeya's model ─────────────────────────────────────────────────
print("\nRunning allocation_grid_search()...")
karthikeya_df = allocation_grid_search(returns)
print(f"  {len(karthikeya_df)} allocation scenarios computed (0-100% QQQ, 5% steps).")

# ── 3. Snapshot existing DB rows ─────────────────────────────────────────────
engine = get_engine()
with engine.connect() as conn:
    existing = pd.read_sql(
        "SELECT qqq_pct, spy_pct, expected_return, volatility, sharpe_ratio, "
        "worst_case_p95, median_outcome FROM monte_carlo_results ORDER BY qqq_pct",
        conn
    )

rows_before = len(existing)
print(f"\nRows currently in monte_carlo_results: {rows_before}")

# ── 4. Load (INSERT IGNORE — won't overwrite existing rows) ──────────────────
print("\nLoading into MySQL...")
load_monte_carlo(karthikeya_df)

with engine.connect() as conn:
    rows_after = conn.execute(
        text("SELECT COUNT(*) FROM monte_carlo_results")
    ).scalar()

inserted = rows_after - rows_before
print(f"Rows inserted: {inserted}  (total now: {rows_after})")

# ── 5. Compare Karthikeya vs DB ───────────────────────────────────────────────
print("\n" + "=" * 65)
print("COMPARISON: Karthikeya's model vs. database")
print("=" * 65)

if existing.empty:
    print("  DB was empty — Karthikeya's values are now the source of truth.")
else:
    # Cast DB types to float for clean comparison
    db = existing.copy()
    for col in ["expected_return", "volatility", "sharpe_ratio",
                "worst_case_p95", "median_outcome"]:
        db[col] = db[col].astype(float)

    merged = karthikeya_df.merge(db, on=["qqq_pct", "spy_pct"], suffixes=("_new", "_db"))

    numeric_cols = ["expected_return", "volatility", "sharpe_ratio",
                    "worst_case_p95", "median_outcome"]

    diffs = []
    for _, row in merged.iterrows():
        for col in numeric_cols:
            new_val = row[f"{col}_new"]
            db_val  = row[f"{col}_db"]
            if abs(new_val - db_val) > 1e-4:
                diffs.append({
                    "qqq_pct": int(row["qqq_pct"]),
                    "column":  col,
                    "karthikeya": round(new_val, 6),
                    "in_db":      round(db_val,  6),
                    "delta":      round(new_val - db_val, 6),
                })

    if not diffs:
        print("  No meaningful differences — Karthikeya's model matches the DB.")
    else:
        print(f"  {len(diffs)} value(s) differ (tolerance 1e-4):\n")
        diff_df = pd.DataFrame(diffs)
        print(diff_df.to_string(index=False))
        print("\n  Note: differences are likely due to risk-free rate")
        print("  (Karthikeya: 4.25%  vs  Jacob's pipeline: 5.0%)")
        print("  and/or fixed random seed (42) vs unseeded simulation.")
        print("\n  DB rows were NOT overwritten (INSERT IGNORE).")
        print("  Run with --force to replace existing rows if desired.")

print("=" * 65)
print("\nDone.")
