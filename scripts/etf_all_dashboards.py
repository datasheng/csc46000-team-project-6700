"""
Group 6700 — SPY vs QQQ: All Three Dashboard PNGs + CSVs for Tableau
Generates:
  dashboard1_returns.png / csv_dashboard1_cumulative_returns.csv
  dashboard2_risk.png   / csv_dashboard2_risk_metrics.csv / csv_dashboard2_drawdown.csv
  dashboard3_ab.png     / csv_dashboard3_ab_returns.csv / csv_dashboard3_ab_summary.csv
Requirements: pip install yfinance pandas numpy matplotlib scipy
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy import stats
from datetime import datetime

DARK   = "#1a1a2e"
PANEL  = "#0d0d1a"
SPINE  = "#333355"
MUTED  = "#aaaaaa"
STAMP  = "#555577"
colors = {"SPY": "#4fc3f7", "QQQ": "#ff8a65"}
ts     = datetime.now().strftime("%Y-%m-%d %H:%M")

# ── 1. Pull & clean data ──────────────────────────────────────────────────────
print("Pulling SPY and QQQ data...")
tickers = ["SPY", "QQQ"]
raw     = yf.download(tickers, period="3y", interval="1d",
                      auto_adjust=True, progress=False)
prices  = raw["Close"].dropna()
prices.index = pd.to_datetime(prices.index)
returns     = prices.pct_change().dropna()
cumulative  = (1 + returns).cumprod()

# ── 2. KPI helpers ────────────────────────────────────────────────────────────
TD = 252
RF = 0.05

def sharpe(r): return round((r.mean()*TD - RF) / (r.std()*np.sqrt(TD)), 4)
def ann_ret(r): return round(r.mean()*TD*100, 2)
def ann_vol(r): return round(r.std()*np.sqrt(TD)*100, 2)
def max_dd(c):
    dd = (c - c.cummax()) / c.cummax()
    return round(dd.min()*100, 2)

kpis = pd.DataFrame({
    "Ann Return (%)": [ann_ret(returns[t]) for t in tickers],
    "Ann Vol (%)":    [ann_vol(returns[t]) for t in tickers],
    "Sharpe":         [sharpe(returns[t])  for t in tickers],
    "Max DD (%)":     [max_dd(cumulative[t]) for t in tickers],
}, index=tickers)
print(kpis.to_string())

# ── 3. A/B portfolios ─────────────────────────────────────────────────────────
returns["Strategy_A_6040"] = returns["SPY"]*0.60 + returns["QQQ"]*0.40
returns["Strategy_B_5050"] = returns["SPY"]*0.50 + returns["QQQ"]*0.50
cum_ab = (1 + returns[["Strategy_A_6040","Strategy_B_5050"]]).cumprod()

t_stat, p_val = stats.ttest_ind(
    returns["Strategy_A_6040"], returns["Strategy_B_5050"]
)
sig = "Statistically significant" if p_val < 0.05 else "Not significant"

# ── HELPER: common axis styling ───────────────────────────────────────────────
def style_ax(ax, title):
    ax.set_facecolor(PANEL)
    ax.set_title(title, color="white", fontsize=10, pad=6)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.spines[:].set_color(SPINE)
    for lbl in ax.get_xticklabels() + ax.get_yticklabels():
        lbl.set_color(MUTED)

def stamp(fig, label):
    fig.text(0.97, 0.01,
             f"{label} | Generated {ts} | Data: yfinance",
             ha="right", va="bottom", color=STAMP, fontsize=7)

# ════════════════════════════════════════════════════════════════════════════
# CSV EXPORTS FOR TABLEAU
# ════════════════════════════════════════════════════════════════════════════

# --- Dashboard 1 CSV: long-format cumulative returns (Date, Ticker, Cumulative_Return_Pct) ---
# Tableau works best with long/tall format — one row per date per ticker
d1_spy = pd.DataFrame({
    "Date": cumulative.index,
    "Ticker": "SPY",
    "Cumulative_Return_Pct": (cumulative["SPY"] * 100 - 100).round(4)
})
d1_qqq = pd.DataFrame({
    "Date": cumulative.index,
    "Ticker": "QQQ",
    "Cumulative_Return_Pct": (cumulative["QQQ"] * 100 - 100).round(4)
})
d1_csv = pd.concat([d1_spy, d1_qqq], ignore_index=True).sort_values("Date")
d1_csv.to_csv("csv_dashboard1_cumulative_returns.csv", index=False)
print("Saved: csv_dashboard1_cumulative_returns.csv")

# --- Dashboard 2 CSV A: risk summary table (one row per ticker) ---
d2_risk = pd.DataFrame({
    "Ticker":          tickers,
    "Ann_Return_Pct":  [ann_ret(returns[t]) for t in tickers],
    "Ann_Vol_Pct":     [ann_vol(returns[t]) for t in tickers],
    "Sharpe_Ratio":    [sharpe(returns[t])  for t in tickers],
    "Max_Drawdown_Pct":[max_dd(cumulative[t]) for t in tickers],
})
d2_risk.to_csv("csv_dashboard2_risk_metrics.csv", index=False)
print("Saved: csv_dashboard2_risk_metrics.csv")

# --- Dashboard 2 CSV B: daily drawdown series (long format) ---
dd_rows = []
for t in tickers:
    dd = (cumulative[t] - cumulative[t].cummax()) / cumulative[t].cummax() * 100
    for date, val in zip(dd.index, dd.values):
        dd_rows.append({"Date": date, "Ticker": t, "Drawdown_Pct": round(val, 4)})
d2_dd_csv = pd.DataFrame(dd_rows).sort_values("Date")
d2_dd_csv.to_csv("csv_dashboard2_drawdown.csv", index=False)
print("Saved: csv_dashboard2_drawdown.csv")

# --- Dashboard 3 CSV A: A/B cumulative returns (long format) ---
ab_map = {
    "Strategy_A_6040": "Strategy A: 60% SPY / 40% QQQ",
    "Strategy_B_5050": "Strategy B: 50% SPY / 50% QQQ"
}
ab_rows = []
for col, label in ab_map.items():
    for date, val in zip(cum_ab.index, (cum_ab[col]*100-100).values):
        ab_rows.append({"Date": date, "Strategy": label,
                        "Cumulative_Return_Pct": round(val, 4)})
d3_ab_csv = pd.DataFrame(ab_rows).sort_values("Date")
d3_ab_csv.to_csv("csv_dashboard3_ab_returns.csv", index=False)
print("Saved: csv_dashboard3_ab_returns.csv")

# --- Dashboard 3 CSV B: summary stats + t-test results ---
d3_summary = pd.DataFrame({
    "Strategy":        ["Strategy A: 60/40", "Strategy B: 50/50"],
    "Final_Value_USD": [round(cum_ab[s].iloc[-1]*50000, 2)
                        for s in ["Strategy_A_6040","Strategy_B_5050"]],
    "Total_Return_Pct":[round(cum_ab[s].iloc[-1]*100-100, 4)
                        for s in ["Strategy_A_6040","Strategy_B_5050"]],
    "T_Statistic":     [round(t_stat, 4), round(t_stat, 4)],
    "P_Value":         [round(p_val, 4),  round(p_val, 4)],
    "Significant":     [sig, sig],
})
d3_summary.to_csv("csv_dashboard3_ab_summary.csv", index=False)
print("Saved: csv_dashboard3_ab_summary.csv")

# ── HELPER: common axis styling ───────────────────────────────────────────────

# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD 1 — Returns Comparison
# ════════════════════════════════════════════════════════════════════════════
fig1, ax = plt.subplots(figsize=(13, 6), facecolor=DARK)
fig1.suptitle("Dashboard 1 — Returns Comparison  |  Group 6700  |  CSc 46000",
              color="white", fontsize=13, fontweight="bold")
style_ax(ax, "SPY vs QQQ — Cumulative Return (3 Years)")
for t in tickers:
    ax.plot(cumulative.index, cumulative[t]*100-100,
            label=t, color=colors[t], linewidth=1.8)
ax.set_ylabel("Total Return (%)", color=MUTED, fontsize=9)
ax.yaxis.label.set_color(MUTED)
ax.axhline(0, color=SPINE, linewidth=0.8, linestyle="--")
ax.legend(facecolor=DARK, edgecolor=SPINE, labelcolor="white", fontsize=9)
for t in tickers:
    final = round(cumulative[t].iloc[-1]*100-100, 1)
    ax.annotate(f"{t}: +{final}%",
                xy=(cumulative.index[-1], cumulative[t].iloc[-1]*100-100),
                xytext=(10, 0), textcoords="offset points",
                color=colors[t], fontsize=8, va="center")
plt.tight_layout(rect=[0, 0.03, 1, 0.95])
stamp(fig1, "Dashboard 1")
fig1.savefig("dashboard1_returns.png", dpi=150, bbox_inches="tight", facecolor=DARK)
print("Saved: dashboard1_returns.png")

# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD 2 — Risk Charts
# ════════════════════════════════════════════════════════════════════════════
fig2 = plt.figure(figsize=(14, 8), facecolor=DARK)
fig2.suptitle("Dashboard 2 — Risk Analysis  |  Group 6700  |  CSc 46000",
              color="white", fontsize=13, fontweight="bold")
gs2 = gridspec.GridSpec(2, 2, figure=fig2, hspace=0.5, wspace=0.35,
                        left=0.07, right=0.97, top=0.91, bottom=0.08)

axA = fig2.add_subplot(gs2[0, 0])
style_ax(axA, "Annualized Volatility (%)")
vols = [ann_vol(returns[t]) for t in tickers]
bars = axA.bar(tickers, vols, color=[colors[t] for t in tickers],
               alpha=0.85, edgecolor="none", width=0.4)
for bar, v in zip(bars, vols):
    axA.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.2,
             f"{v}%", ha="center", color="white", fontsize=9)

axB = fig2.add_subplot(gs2[0, 1])
style_ax(axB, "Sharpe Ratio (higher = better)")
sharpes = [sharpe(returns[t]) for t in tickers]
bars = axB.bar(tickers, sharpes, color=[colors[t] for t in tickers],
               alpha=0.85, edgecolor="none", width=0.4)
for bar, v in zip(bars, sharpes):
    axB.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.01,
             f"{v}", ha="center", color="white", fontsize=9)

axC = fig2.add_subplot(gs2[1, :])
style_ax(axC, "Drawdown from Peak (%)")
for t in tickers:
    dd = (cumulative[t] - cumulative[t].cummax()) / cumulative[t].cummax() * 100
    axC.fill_between(dd.index, dd, 0, alpha=0.35, color=colors[t])
    axC.plot(dd.index, dd, color=colors[t], linewidth=1, label=t)
    axC.annotate(f"Max: {round(dd.min(),1)}%",
                 xy=(dd.idxmin(), dd.min()),
                 xytext=(0, -18), textcoords="offset points",
                 color=colors[t], fontsize=8, ha="center")
axC.set_ylabel("Drawdown %", color=MUTED, fontsize=9)
axC.yaxis.label.set_color(MUTED)
axC.legend(facecolor=DARK, edgecolor=SPINE, labelcolor="white", fontsize=9)

stamp(fig2, "Dashboard 2")
fig2.savefig("dashboard2_risk.png", dpi=150, bbox_inches="tight", facecolor=DARK)
print("Saved: dashboard2_risk.png")

# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD 3 — A/B Performance
# ════════════════════════════════════════════════════════════════════════════
fig3 = plt.figure(figsize=(14, 8), facecolor=DARK)
fig3.suptitle("Dashboard 3 — A/B Strategy Comparison  |  Group 6700  |  CSc 46000",
              color="white", fontsize=13, fontweight="bold")
gs3 = gridspec.GridSpec(2, 2, figure=fig3, hspace=0.5, wspace=0.35,
                        left=0.07, right=0.97, top=0.91, bottom=0.08)

ab_colors = {"Strategy_A_6040": "#a78bfa", "Strategy_B_5050": "#34d399"}
ab_labels = {"Strategy_A_6040": "Strategy A: 60% SPY / 40% QQQ",
             "Strategy_B_5050": "Strategy B: 50% SPY / 50% QQQ"}

axD = fig3.add_subplot(gs3[0, :])
style_ax(axD, "Cumulative Return — Strategy A vs Strategy B")
for s in ["Strategy_A_6040", "Strategy_B_5050"]:
    axD.plot(cum_ab.index, cum_ab[s]*100-100,
             label=ab_labels[s], color=ab_colors[s], linewidth=1.8)
axD.set_ylabel("Total Return (%)", color=MUTED, fontsize=9)
axD.yaxis.label.set_color(MUTED)
axD.axhline(0, color=SPINE, linewidth=0.8, linestyle="--")
axD.legend(facecolor=DARK, edgecolor=SPINE, labelcolor="white", fontsize=9)
for s in ["Strategy_A_6040", "Strategy_B_5050"]:
    final = round(cum_ab[s].iloc[-1]*100-100, 1)
    axD.annotate(f"+{final}%",
                 xy=(cum_ab.index[-1], cum_ab[s].iloc[-1]*100-100),
                 xytext=(8, 0), textcoords="offset points",
                 color=ab_colors[s], fontsize=8, va="center")

axE = fig3.add_subplot(gs3[1, 0])
style_ax(axE, "Final Value of $50,000 Investment")
final_vals = [round(cum_ab[s].iloc[-1]*50000, 0)
              for s in ["Strategy_A_6040","Strategy_B_5050"]]
bars = axE.bar(["A: 60/40", "B: 50/50"], final_vals,
               color=[ab_colors["Strategy_A_6040"], ab_colors["Strategy_B_5050"]],
               alpha=0.85, edgecolor="none", width=0.4)
for bar, v in zip(bars, final_vals):
    axE.text(bar.get_x()+bar.get_width()/2, bar.get_height()+200,
             f"${v:,.0f}", ha="center", color="white", fontsize=9)
axE.set_ylabel("Portfolio Value ($)", color=MUTED, fontsize=9)
axE.yaxis.label.set_color(MUTED)

axF = fig3.add_subplot(gs3[1, 1])
axF.set_facecolor(PANEL)
axF.axis("off")
axF.text(0.5, 0.75, "Statistical Test (T-test)",
         ha="center", color="white", fontsize=11,
         fontweight="bold", transform=axF.transAxes)
axF.text(0.5, 0.55, f"t-statistic: {round(t_stat, 4)}",
         ha="center", color=MUTED, fontsize=10, transform=axF.transAxes)
axF.text(0.5, 0.38, f"p-value: {round(p_val, 4)}",
         ha="center", color=MUTED, fontsize=10, transform=axF.transAxes)
result_color = "#34d399" if p_val < 0.05 else "#ff8a65"
axF.text(0.5, 0.18, sig,
         ha="center", color=result_color, fontsize=11,
         fontweight="bold", transform=axF.transAxes)

stamp(fig3, "Dashboard 3")
fig3.savefig("dashboard3_ab.png", dpi=150, bbox_inches="tight", facecolor=DARK)
print("Saved: dashboard3_ab.png")
print("\nDone. All PNGs and CSVs saved.")