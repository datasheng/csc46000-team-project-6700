# Architecture

## Pipeline Flow
```
Alpha Vantage API ─┐
                   ├──▶ Python (pandas, numpy) ──▶ MySQL ──▶ Tableau (live)
yFinance         ──┘                              │
                                                  └──▶ FastAPI ──▶ Web Front-End
```

## Layers
| Layer | Module | Owner |
|-------|--------|-------|
| Extract | `src/extractors/alpha_vantage.py` | Diana |
| Extract | `src/extractors/yfinance_extract.py` | Diana |
| Transform | `src/transform/metrics.py` | Mohmed |
| Model: Sharpe + Monte Carlo | `src/models/sharpe.py`, `monte_carlo.py` | Karthikeya |
| Model: A/B test | `src/models/ab_test.py` | Edison |
| Model: Custom ML/DL | `src/models/ml_model.py` | Nick |
| Database | `src/db/schema.sql`, `loaders.py` | Jacob |
| API | `src/api/main.py` | Jacob |
| Web Front-End | `web/` | Mohmed |
| Tableau | `tableau/` | All (paired) |

## Data Model (preliminary — Jacob owns final)
- `prices(date, ticker, open, high, low, close, adj_close, volume)` — primary key (date, ticker)
- `daily_metrics(date, ticker, daily_return, cum_return, rolling_vol_30d, drawdown)`
- `monte_carlo_results(run_id, allocation_qqq_pct, expected_return, volatility, sharpe, p5, p50, p95)`
- `ab_test_results(strategy_name, mean_return, std_return, sharpe, t_stat, p_value)`
- `ml_predictions(date, ticker, model_name, predicted_return, actual_return, error)`
