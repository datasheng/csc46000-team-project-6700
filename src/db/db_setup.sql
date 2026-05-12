-- Group 6700 — SPY vs QQQ — MySQL Schema
-- This file runs automatically when Docker starts the container for the first time

CREATE DATABASE IF NOT EXISTS etf_db;
USE etf_db;

-- ── Table 1: prices ───────────────────────────────────────────────────────────
-- Raw daily OHLCV data pulled by Diana's extractors (Alpha Vantage + yFinance)
-- Composite primary key on (date, ticker) prevents duplicate entries
CREATE TABLE IF NOT EXISTS prices (
    date        DATE         NOT NULL,
    ticker      VARCHAR(10)  NOT NULL,
    open        DECIMAL(10,4),
    high        DECIMAL(10,4),
    low         DECIMAL(10,4),
    close       DECIMAL(10,4),
    volume      BIGINT,
    PRIMARY KEY (date, ticker)
);

-- ── Table 2: daily_metrics ────────────────────────────────────────────────────
-- Jacob's computed transforms from the prices table
-- daily_return, cumulative_return, rolling_volatility, drawdown
-- Used by Tableau Dashboard 1 (returns) and Dashboard 2 (risk)
CREATE TABLE IF NOT EXISTS daily_metrics (
    date                DATE         NOT NULL,
    ticker              VARCHAR(10)  NOT NULL,
    daily_return        DECIMAL(10,6),
    cumulative_return   DECIMAL(10,6),
    rolling_volatility  DECIMAL(10,6),
    drawdown            DECIMAL(10,6),
    PRIMARY KEY (date, ticker)
);

-- ── Table 3: monte_carlo_results ──────────────────────────────────────────────
-- Karthikeya's output: allocation grid search (0-100% QQQ in 5% increments)
-- One row per allocation percentage with expected return, volatility, Sharpe
CREATE TABLE IF NOT EXISTS monte_carlo_results (
    qqq_pct             INT          NOT NULL,   -- e.g. 0, 5, 10 ... 100
    spy_pct             INT          NOT NULL,   -- 100 - qqq_pct
    expected_return     DECIMAL(10,6),
    volatility          DECIMAL(10,6),
    sharpe_ratio        DECIMAL(10,6),
    worst_case_p95      DECIMAL(10,6),           -- 95th percentile worst drawdown
    median_outcome      DECIMAL(12,2),           -- median final portfolio value from $50k
    PRIMARY KEY (qqq_pct)
);

-- ── Table 4: ab_test_results ──────────────────────────────────────────────────
-- Edison's output: daily portfolio values for Strategy A (60/40) and B (50/50)
-- Plus summary row with t-test result
CREATE TABLE IF NOT EXISTS ab_test_results (
    date                DATE         NOT NULL,
    strategy            VARCHAR(20)  NOT NULL,   -- 'A_6040' or 'B_5050'
    portfolio_value     DECIMAL(12,2),           -- value of $50k invested
    cumulative_return   DECIMAL(10,6),
    daily_return        DECIMAL(10,6),
    PRIMARY KEY (date, strategy)
);

-- Separate table for the t-test summary (one row total)
CREATE TABLE IF NOT EXISTS ab_test_summary (
    id                  INT          NOT NULL AUTO_INCREMENT,
    t_statistic         DECIMAL(10,6),
    p_value             DECIMAL(10,6),
    significant         TINYINT(1),              -- 1 = yes, 0 = no
    strategy_a_final    DECIMAL(12,2),           -- final value of $50k in Strategy A
    strategy_b_final    DECIMAL(12,2),
    recommendation      TEXT,                    -- Edison's business recommendation paragraph
    PRIMARY KEY (id)
);

-- ── Table 5: ml_predictions ───────────────────────────────────────────────────
-- Nick's output: predicted returns per date per ticker from LSTM/XGBoost
CREATE TABLE IF NOT EXISTS ml_predictions (
    date                DATE         NOT NULL,
    ticker              VARCHAR(10)  NOT NULL,
    predicted_return    DECIMAL(10,6),
    actual_return       DECIMAL(10,6),           -- for walk-forward validation comparison
    model_type          VARCHAR(20),             -- 'LSTM', 'XGBoost', etc.
    PRIMARY KEY (date, ticker, model_type)
);
