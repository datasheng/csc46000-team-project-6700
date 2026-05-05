# Web Front-End — Mohmed Bemat (Extra Credit)

State-of-the-art web app that surfaces the project results live.

## Suggested Stack
- **Framework:** Next.js (React) + Tailwind CSS
- **Charts:** Recharts or Plotly.js
- **Hosting:** Vercel (free tier)
- **Data source:** Calls FastAPI endpoints exposed by `src/api/main.py` (Jacob)

## Pages to Build
1. **Allocator** — slider for QQQ:SPY split (0–100%) → projected outcome
2. **Risk Profile** — volatility, drawdown, Sharpe ratio cards
3. **A/B Comparison** — 60/40 vs equal-weight visualization
4. **ML Predictions** — Nick's custom model output overlay

## Coordination
- API contract lives in `/docs/api_contract.md` — keep in sync with Jacob
- Use the same color palette across web + Tableau dashboards for visual consistency
