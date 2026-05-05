# SPY vs QQQ — $50K Asset Allocator

CSC 46000 — Group 6700 — Spring 2026 — Prof. Sheng Chen

End-to-end data science pipeline that compares SPY and QQQ ETFs to recommend the optimal QQQ:SPY allocation for a $50,000 investment. Live data flows from public APIs through Python and MySQL into Tableau dashboards and a web front-end.

## Core Questions
1. Does QQQ outperform SPY over 3 years on a risk-adjusted basis?
2. What's the optimal QQQ:SPY split for $50K?

## Architecture
```
Alpha Vantage API ─┐
                   ├──▶ Python (pandas) ──▶ MySQL ──▶ Tableau (live)
yFinance         ──┘                          │
                                              └──▶ FastAPI ──▶ Web Front-End
```

## Tech Stack
Python (pandas, numpy, scikit-learn, xgboost) · MySQL · FastAPI · Tableau Desktop · Next.js + Tailwind (web front-end) · GitHub Classroom

## Team
| Member | Role |
|--------|------|
| Diana Lucero | Backend / Pipeline — API extraction & repo lead |
| Jacob Li | Backend / Pipeline — Database + FastAPI service |
| Mohmed Bemat | Backend / Pipeline — Web front-end (extra credit) |
| Nick Kontonicolaou | Data Science — Custom ML/DL model (extra credit) |
| Karthikeya Reddy B | Data Science — Sharpe ratio + Monte Carlo |
| Edison Florian | Data Science — A/B test + statistical validation |

## Repo Layout
```
spy-qqq-allocator/
├── src/
│   ├── extractors/       # Alpha Vantage + yFinance (Diana)
│   ├── transform/        # daily/cumulative returns, vol, drawdown (Mohmed)
│   ├── models/           # Sharpe, Monte Carlo, A/B, ML
│   ├── db/               # MySQL schema + loaders (Jacob)
│   └── api/              # FastAPI service (Jacob)
├── web/                  # Next.js front-end (Mohmed — extra credit)
├── tableau/              # .twb / .twbx workbooks
├── docs/                 # architecture, diagrams, API contract
└── tests/
```

## Setup

### 1. Clone the repo
```bash
git clone <github-classroom-url>
cd spy-qqq-allocator
```

### 2. Python environment
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment variables
```bash
cp .env.example .env
# Edit .env and add your Alpha Vantage API key + MySQL credentials
```
Get a free Alpha Vantage key at https://www.alphavantage.co/support/#api-key.

### 4. MySQL setup (see `src/db/`)
```bash
mysql -u root -p < src/db/schema.sql
```

### 5. Run the pipeline
```bash
python -m src.extractors.alpha_vantage     # smoke-test extractor
# (full ETL orchestrator coming — Mohmed)
```

### 6. Run the API
```bash
uvicorn src.api.main:app --reload
```

## Mandatory Project Rules
- **No flat files.** All data via live APIs.
- **Tableau live connection** required for dashboards.
- **Everyone commits** — graded on equal contribution. Aim for 5–10 meaningful commits per person.

## Extra Credit Targets
- Custom ML/DL model (Nick)
- State-of-the-art web front-end (Mohmed)

## Deliverables
- 3 Tableau dashboards (Returns, Risk, A/B + ML)
- 1 statistical model + business recommendation
- 7-min recorded demo (Part A — 60%)
- 8-min live executive briefing + 7-min Q&A (Part B — 40%)
