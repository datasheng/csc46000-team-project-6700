"""
Group 6700 — SPY vs QQQ Pipeline Proof of Data Flow
Run this to generate a screenshot-ready output showing live data is flowing.
Requirements: pip install yfinance pandas numpy matplotlib
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from datetime import datetime

# ── 1. Pull live data (no API key needed) ────────────────────────────────────
print("Pulling SPY and QQQ data from Yahoo Finance...")
tickers = ["SPY", "QQQ"]
raw = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)

# ── 2. Clean & transform ─────────────────────────────────────────────────────
prices = raw["Close"].dropna()
prices.index = pd.to_datetime(prices.index)

# Daily returns
returns = prices.pct_change().dropna()

# Cumulative returns (starts at 1.0)
cumulative = (1 + returns).cumprod()

# ── 3. Compute KPIs ──────────────────────────────────────────────────────────
trading_days = 252
risk_free_rate = 0.05  # ~current approx

def sharpe_ratio(ret_series, rf=risk_free_rate, periods=trading_days):
    excess = ret_series.mean() * periods - rf
    vol = ret_series.std() * np.sqrt(periods)
    return round(excess / vol, 4)

def annualized_return(ret_series, periods=trading_days):
    return round(ret_series.mean() * periods * 100, 2)

def annualized_vol(ret_series, periods=trading_days):
    return round(ret_series.std() * np.sqrt(periods) * 100, 2)

def max_drawdown(cum_series):
    roll_max = cum_series.cummax()
    drawdown = (cum_series - roll_max) / roll_max
    return round(drawdown.min() * 100, 2)

kpis = pd.DataFrame({
    "Annualized Return (%)": [annualized_return(returns[t]) for t in tickers],
    "Annualized Vol (%)":    [annualized_vol(returns[t]) for t in tickers],
    "Sharpe Ratio":          [sharpe_ratio(returns[t]) for t in tickers],
    "Max Drawdown (%)":      [max_drawdown(cumulative[t]) for t in tickers],
    "Total Return (%)":      [round((cumulative[t].iloc[-1] - 1) * 100, 2) for t in tickers],
}, index=tickers)

print("\n── KPI Summary ──────────────────────────────────────────────────")
print(kpis.to_string())

# ── 4. Sample of raw dataframe (for screenshot proof) ────────────────────────
print("\n── Sample: Last 5 rows of cleaned price data ────────────────────")
print(prices.tail(5).to_string())

print("\n── Sample: Daily returns (last 5 rows) ──────────────────────────")
print(returns.tail(5).round(6).to_string())

# ── 5. Build the "proof of data flow" figure ─────────────────────────────────
fig = plt.figure(figsize=(14, 9), facecolor="#1a1a2e")
fig.suptitle(
    "Group 6700 — SPY vs QQQ: Data Pipeline Proof  |  CSc 46000",
    fontsize=14, color="white", fontweight="bold", y=0.98
)

gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35,
                       left=0.07, right=0.97, top=0.91, bottom=0.08)

colors = {"SPY": "#4fc3f7", "QQQ": "#ff8a65"}

# -- Panel 1: Cumulative returns line chart -----------------------------------
ax1 = fig.add_subplot(gs[0, :])
ax1.set_facecolor("#0d0d1a")
for t in tickers:
    ax1.plot(cumulative.index, cumulative[t], label=t,
             color=colors[t], linewidth=1.8)
ax1.set_title("Cumulative Return — 3 Years", color="white", fontsize=11, pad=8)
ax1.set_ylabel("Growth of $1", color="#aaaaaa", fontsize=9)
ax1.tick_params(colors="#aaaaaa", labelsize=8)
ax1.spines[:].set_color("#333355")
ax1.legend(facecolor="#1a1a2e", edgecolor="#333355", labelcolor="white",
           fontsize=9, loc="upper left")
ax1.yaxis.label.set_color("#aaaaaa")

# -- Panel 2: KPI bar chart ---------------------------------------------------
ax2 = fig.add_subplot(gs[1, 0])
ax2.set_facecolor("#0d0d1a")
metrics = ["Annualized Return (%)", "Annualized Vol (%)", "Sharpe Ratio"]
x = np.arange(len(metrics))
w = 0.3
for i, t in enumerate(tickers):
    vals = [kpis.loc[t, m] for m in metrics]
    bars = ax2.bar(x + (i - 0.5) * w, vals, w, label=t,
                   color=colors[t], alpha=0.85, edgecolor="none")
    for bar, val in zip(bars, vals):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                 f"{val}", ha="center", va="bottom", color="white", fontsize=7)
ax2.set_xticks(x)
ax2.set_xticklabels(["Ann. Return\n(%)", "Ann. Vol\n(%)", "Sharpe\nRatio"],
                    color="#aaaaaa", fontsize=8)
ax2.tick_params(colors="#aaaaaa", labelsize=8)
ax2.set_title("Key Risk/Return Metrics", color="white", fontsize=10, pad=6)
ax2.spines[:].set_color("#333355")
ax2.legend(facecolor="#1a1a2e", edgecolor="#333355", labelcolor="white",
           fontsize=8, loc="upper right")

# -- Panel 3: Drawdown chart --------------------------------------------------
ax3 = fig.add_subplot(gs[1, 1])
ax3.set_facecolor("#0d0d1a")
for t in tickers:
    roll_max = cumulative[t].cummax()
    dd = (cumulative[t] - roll_max) / roll_max * 100
    ax3.fill_between(dd.index, dd, 0, alpha=0.4, color=colors[t])
    ax3.plot(dd.index, dd, color=colors[t], linewidth=1, label=t)
ax3.set_title("Drawdown (%)", color="white", fontsize=10, pad=6)
ax3.set_ylabel("Drawdown %", color="#aaaaaa", fontsize=9)
ax3.tick_params(colors="#aaaaaa", labelsize=8)
ax3.spines[:].set_color("#333355")
ax3.legend(facecolor="#1a1a2e", edgecolor="#333355", labelcolor="white",
           fontsize=8)

# Timestamp watermark
fig.text(0.97, 0.01, f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} | Data: yfinance",
         ha="right", va="bottom", color="#555577", fontsize=7)

plt.savefig("etf_proof_of_data_flow.png", dpi=150, bbox_inches="tight",
            facecolor=fig.get_facecolor())
print("\nSaved: etf_proof_of_data_flow.png")
print("── Done. Paste this image into your slides as proof of data flow. ──")

prices.to_csv("spy_qqq_prices.csv")