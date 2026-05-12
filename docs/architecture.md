# Architecture & Workflow

Owner: Diana Lucero. Diagrams render natively on GitHub — no external image hosting needed.

## 1. End-to-End Pipeline (Data Flow)

```mermaid
flowchart LR
    AV[Alpha Vantage API<br/>daily OHLCV] -->|HTTPS| EXT[Python Extractors<br/>src/extractors/]
    YF[yFinance<br/>price + dividends] -->|HTTPS| EXT

    EXT -->|pandas DataFrames| TX[Transform Layer<br/>src/transform/<br/>returns, volatility, drawdown]
    TX --> DB[(MySQL<br/>src/db/)]

    DB --> M1[Sharpe + Monte Carlo<br/>src/models/]
    DB --> M2[A/B Test<br/>60/40 vs equal-weight]
    DB --> M3[Custom ML/DL Model<br/>extra credit]

    M1 --> DB
    M2 --> DB
    M3 --> DB

    DB -->|live connection| TBL[Tableau Dashboards<br/>3 dashboards]
    DB --> API[FastAPI Service<br/>src/api/]
    API --> WEB[Web Front-End<br/>web/ — extra credit]

    classDef extractor fill:#dbeafe,stroke:#1e40af,color:#1e3a8a
    classDef python fill:#fef3c7,stroke:#a16207,color:#713f12
    classDef storage fill:#dcfce7,stroke:#166534,color:#14532d
    classDef bi fill:#fce7f3,stroke:#a21caf,color:#701a75
    classDef extra fill:#fee2e2,stroke:#b91c1c,color:#7f1d1d

    class AV,YF extractor
    class EXT,TX,M1,M2,API python
    class DB storage
    class TBL bi
    class M3,WEB extra
```

## 2. ETL Sequence

```mermaid
sequenceDiagram
    autonumber
    participant Cron as scheduler/manual trigger
    participant Ext as Extractors (Diana)
    participant AV as Alpha Vantage
    participant YF as yFinance
    participant Tx as Transform (Mohmed)
    participant DB as MySQL (Jacob)
    participant Mdl as Models (Karthikeya/Edison/Nick)
    participant Tbl as Tableau / Web

    Cron->>Ext: run_extractors()
    Ext->>AV: GET TIME_SERIES_DAILY (SPY, QQQ)
    AV-->>Ext: JSON OHLCV
    Ext->>YF: Ticker.history(period=3y)
    YF-->>Ext: DataFrame (price, dividends)
    Ext->>Tx: clean_df
    Tx->>Tx: compute returns, volatility, drawdown
    Tx->>DB: INSERT prices, daily_metrics
    Mdl->>DB: SELECT prices
    Mdl->>Mdl: Sharpe / Monte Carlo / A/B / ML
    Mdl->>DB: INSERT monte_carlo_results, ab_test_results, ml_predictions
    Tbl->>DB: live connection (refresh every demo)
```

## 3. Use Case Diagram (Stakeholders)

```mermaid
flowchart TB
    subgraph Actors
        Investor((Retail Investor<br/>$50K to allocate))
        Advisor((Financial Advisor))
        Analyst((Data Analyst<br/>internal team))
    end

    subgraph System[SPY vs QQQ Allocator]
        UC1[View SPY vs QQQ<br/>cumulative returns]
        UC2[Compare risk-adjusted<br/>performance Sharpe]
        UC3[Find optimal QQQ:SPY<br/>split for $50K]
        UC4[See worst-case<br/>drawdown 95th pct]
        UC5[Compare 60/40 vs<br/>equal-weight A/B]
        UC6[Get ML-predicted<br/>forward return]
        UC7[Refresh data live<br/>during meeting]
    end

    Investor --> UC1
    Investor --> UC3
    Investor --> UC4
    Advisor --> UC2
    Advisor --> UC3
    Advisor --> UC5
    Advisor --> UC6
    Analyst --> UC7
    Analyst --> UC1
    Analyst --> UC2
```

## 4. Data Model (MySQL — Jacob will refine)

```mermaid
erDiagram
    PRICES ||--o{ DAILY_METRICS : derives
    PRICES ||--o{ ML_PREDICTIONS : feeds
    PRICES {
        date date PK
        string ticker PK
        decimal open
        decimal high
        decimal low
        decimal close
        decimal adj_close
        bigint volume
        decimal dividends
    }
    DAILY_METRICS {
        date date PK
        string ticker PK
        decimal daily_return
        decimal cum_return
        decimal rolling_vol_30d
        decimal drawdown
    }
    MONTE_CARLO_RESULTS {
        int run_id PK
        decimal allocation_qqq_pct
        decimal expected_return
        decimal volatility
        decimal sharpe
        decimal p5
        decimal p50
        decimal p95
        timestamp run_at
    }
    AB_TEST_RESULTS {
        string strategy_name PK
        decimal mean_return
        decimal std_return
        decimal sharpe
        decimal t_stat
        decimal p_value
        timestamp run_at
    }
    ML_PREDICTIONS {
        date date PK
        string ticker PK
        string model_name PK
        decimal predicted_return
        decimal actual_return
        decimal error
    }
```

## 5. Layer Ownership

| Layer | Module | Owner | Status |
|-------|--------|-------|--------|
| Extract — Alpha Vantage | `src/extractors/alpha_vantage.py` | Diana | done |
| Extract — yFinance | `src/extractors/yfinance_extract.py` | Diana | done |
| Extract — orchestrator | `scripts/run_extractors.py` | Diana | done |
| Transform | `src/transform/metrics.py` | Mohmed | pending |
| Database — schema | `src/db/schema.sql` | Jacob | pending |
| Database — loaders | `src/db/loaders.py` | Jacob | pending |
| Model — Sharpe + Monte Carlo | `src/models/sharpe.py`, `monte_carlo.py` | Karthikeya | pending |
| Model — A/B test | `src/models/ab_test.py` | Edison | pending |
| Model — Custom ML/DL | `src/models/ml_model.py` | Nick (extra credit) | done |
| API service | `src/api/main.py` | Jacob | pending |
| Web Front-End | `web/` | Mohmed (extra credit) | pending |
| Tableau Dashboards | `tableau/*.twb` | All (paired) | pending |
