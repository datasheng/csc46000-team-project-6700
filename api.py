"""
Group 6700 — api.py
Jacob Li — Flask REST API

Exposes MySQL data as JSON endpoints for Mohmed's React frontend.
All endpoints return JSON. CORS is enabled so the frontend can call from any origin.

Requirements:
    pip install flask flask-cors sqlalchemy pymysql

Usage:
    python api.py
    Server runs on http://localhost:5000

Endpoints:
    GET /health                          — check if API is running
    GET /prices                          — raw closing prices (SPY + QQQ)
    GET /prices?ticker=SPY               — filter by ticker
    GET /metrics                         — all daily metrics
    GET /metrics?ticker=QQQ              — filter by ticker
    GET /monte-carlo                     — all 21 allocation scenarios
    GET /monte-carlo?qqq_pct=40          — specific allocation lookup
    GET /ab-results                      — daily A/B portfolio values
    GET /ab-results?strategy=A_6040      — filter by strategy
    GET /ab-summary                      — t-test result + recommendation
    GET /predictions                     — ML predictions (populated by Nick)
    GET /predictions?ticker=SPY          — filter by ticker
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import text
from loaders import get_engine

app = Flask(__name__)
CORS(app)  # Allow React frontend to call from any origin

def query(sql, params=None):
    """Run a SELECT query and return results as a list of dicts."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
    return rows

def serialize(rows):
    """Convert date objects to strings for JSON serialization."""
    import datetime
    cleaned = []
    for row in rows:
        clean_row = {}
        for k, v in row.items():
            if isinstance(v, (datetime.date, datetime.datetime)):
                clean_row[k] = v.isoformat()
            else:
                clean_row[k] = v
        cleaned.append(clean_row)
    return cleaned

# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    """Quick check to confirm API and DB are both up."""
    try:
        rows = query("SELECT COUNT(*) as count FROM prices")
        return jsonify({
            "status": "ok",
            "prices_rows": rows[0]["count"]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ── Prices ────────────────────────────────────────────────────────────────────
@app.route("/prices")
def get_prices():
    """
    Raw closing prices for SPY and QQQ.
    Optional query param: ?ticker=SPY or ?ticker=QQQ
    """
    ticker = request.args.get("ticker")
    if ticker:
        rows = query(
            "SELECT date, ticker, close, volume FROM prices WHERE ticker = :ticker ORDER BY date ASC",
            {"ticker": ticker.upper()}
        )
    else:
        rows = query(
            "SELECT date, ticker, close, volume FROM prices ORDER BY date ASC, ticker ASC"
        )
    return jsonify(serialize(rows))

# ── Daily metrics ─────────────────────────────────────────────────────────────
@app.route("/metrics")
def get_metrics():
    """
    Daily computed metrics: return, cumulative return, volatility, drawdown.
    Optional query param: ?ticker=SPY or ?ticker=QQQ
    """
    ticker = request.args.get("ticker")
    if ticker:
        rows = query(
            """SELECT date, ticker, daily_return, cumulative_return, 
                      rolling_volatility, drawdown
               FROM daily_metrics 
               WHERE ticker = :ticker 
               ORDER BY date ASC""",
            {"ticker": ticker.upper()}
        )
    else:
        rows = query(
            """SELECT date, ticker, daily_return, cumulative_return,
                      rolling_volatility, drawdown
               FROM daily_metrics 
               ORDER BY date ASC, ticker ASC"""
        )
    return jsonify(serialize(rows))

# ── Monte Carlo ───────────────────────────────────────────────────────────────
@app.route("/monte-carlo")
def get_monte_carlo():
    """
    Allocation grid: expected return, volatility, Sharpe, worst case, median outcome.
    Optional query param: ?qqq_pct=40 for a specific allocation
    Returns all 21 scenarios (0-100% QQQ in 5% steps) if no param given.
    """
    qqq_pct = request.args.get("qqq_pct")
    if qqq_pct:
        rows = query(
            """SELECT qqq_pct, spy_pct, expected_return, volatility,
                      sharpe_ratio, worst_case_p95, median_outcome
               FROM monte_carlo_results
               WHERE qqq_pct = :qqq_pct""",
            {"qqq_pct": int(qqq_pct)}
        )
    else:
        rows = query(
            """SELECT qqq_pct, spy_pct, expected_return, volatility,
                      sharpe_ratio, worst_case_p95, median_outcome
               FROM monte_carlo_results
               ORDER BY qqq_pct ASC"""
        )
    return jsonify(serialize(rows))

# ── Best allocation ───────────────────────────────────────────────────────────
@app.route("/monte-carlo/best")
def get_best_allocation():
    """
    Returns the single allocation with the highest Sharpe ratio.
    This is the core business recommendation endpoint.
    """
    rows = query(
        """SELECT qqq_pct, spy_pct, expected_return, volatility,
                  sharpe_ratio, worst_case_p95, median_outcome
           FROM monte_carlo_results
           ORDER BY sharpe_ratio DESC
           LIMIT 1"""
    )
    return jsonify(serialize(rows))

# ── A/B results ───────────────────────────────────────────────────────────────
@app.route("/ab-results")
def get_ab_results():
    """
    Daily portfolio values for Strategy A (60/40) and Strategy B (50/50).
    Optional query param: ?strategy=A_6040 or ?strategy=B_5050
    """
    strategy = request.args.get("strategy")
    if strategy:
        rows = query(
            """SELECT date, strategy, portfolio_value, cumulative_return, daily_return
               FROM ab_test_results
               WHERE strategy = :strategy
               ORDER BY date ASC""",
            {"strategy": strategy}
        )
    else:
        rows = query(
            """SELECT date, strategy, portfolio_value, cumulative_return, daily_return
               FROM ab_test_results
               ORDER BY date ASC, strategy ASC"""
        )
    return jsonify(serialize(rows))

# ── A/B summary ───────────────────────────────────────────────────────────────
@app.route("/ab-summary")
def get_ab_summary():
    """
    T-test result, final portfolio values, and business recommendation.
    Returns one row.
    """
    rows = query(
        """SELECT t_statistic, p_value, significant,
                  strategy_a_final, strategy_b_final, recommendation
           FROM ab_test_summary
           ORDER BY id DESC
           LIMIT 1"""
    )
    return jsonify(serialize(rows))

# ── ML predictions ────────────────────────────────────────────────────────────
@app.route("/predictions")
def get_predictions():
    """
    ML model predictions (populated by Nick).
    Optional query params: ?ticker=SPY, ?model_type=LSTM
    Returns empty list until Nick loads his model results.
    """
    ticker     = request.args.get("ticker")
    model_type = request.args.get("model_type")

    sql    = """SELECT date, ticker, predicted_return, actual_return, model_type
                FROM ml_predictions WHERE 1=1"""
    params = {}

    if ticker:
        sql += " AND ticker = :ticker"
        params["ticker"] = ticker.upper()
    if model_type:
        sql += " AND model_type = :model_type"
        params["model_type"] = model_type

    sql += " ORDER BY date ASC, ticker ASC"
    rows = query(sql, params)
    return jsonify(serialize(rows))

# ── KPI summary ───────────────────────────────────────────────────────────────
@app.route("/kpis")
def get_kpis():
    """
    High level KPI summary per ticker — annualized return, vol, Sharpe, max drawdown.
    Computed on the fly from daily_metrics.
    Useful for Mohmed's summary cards at the top of the dashboard.
    """
    rows = query(
        """SELECT 
               ticker,
               ROUND(AVG(daily_return) * 252 * 100, 2)              AS ann_return_pct,
               ROUND(AVG(rolling_volatility) * 100, 2)              AS avg_volatility_pct,
               ROUND(MIN(drawdown) * 100, 2)                        AS max_drawdown_pct,
               ROUND(MAX(cumulative_return) * 100 - 100, 2)         AS total_return_pct
           FROM daily_metrics
           WHERE rolling_volatility IS NOT NULL
           GROUP BY ticker"""
    )
    return jsonify(serialize(rows))

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("Group 6700 — ETF API starting on http://localhost:5000")
    print("=" * 50)
    print("Endpoints:")
    print("  GET /health")
    print("  GET /prices?ticker=SPY")
    print("  GET /metrics?ticker=QQQ")
    print("  GET /monte-carlo")
    print("  GET /monte-carlo/best")
    print("  GET /ab-results")
    print("  GET /ab-summary")
    print("  GET /predictions")
    print("  GET /kpis")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)
