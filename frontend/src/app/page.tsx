import { api } from "@/lib/api";
import Link from "next/link";

export default async function OverviewPage() {
  let kpis = null;
  let best = null;
  try {
    [kpis, best] = await Promise.all([api.kpis(), api.bestAlloc()]);
  } catch {
    // API not running — show empty state
  }

  const cards = [
    { href: "/allocator",      label: "Allocator",      desc: "Pick your SPY/QQQ split and see projected outcomes from 10,000 Monte Carlo paths." },
    { href: "/risk",           label: "Risk Profile",   desc: "Cumulative returns, rolling volatility, and drawdown for SPY and QQQ over 3 years." },
    { href: "/ab-comparison",  label: "A/B Test",       desc: "60/40 vs 50/50 strategy comparison with t-test significance and business recommendation." },
    { href: "/ml-predictions", label: "ML Predictions", desc: "LSTM/XGBoost model predictions vs actual returns with walk-forward validation." },
  ];

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-4xl font-bold tracking-tight">$50K Asset Allocator</h1>
        <p className="mt-2 text-gray-400 text-lg">
          SPY vs QQQ — data-driven allocation analysis for retail investors.
        </p>
      </div>

      {kpis && kpis.length > 0 && (
        <div>
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
            3-Year Performance
          </h2>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {kpis.map((k) => (
              <div key={k.ticker} className="bg-gray-900 rounded-xl p-5 border border-gray-800">
                <div className="text-xs text-gray-500 mb-1 uppercase tracking-wider">{k.ticker}</div>
                <div className={`text-3xl font-bold ${k.total_return_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {k.total_return_pct >= 0 ? "+" : ""}{k.total_return_pct}%
                </div>
                <div className="text-xs text-gray-400 mt-1">Total Return</div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-400">
                  <div>
                    <div className="text-white font-medium">{k.ann_return_pct}%</div>
                    <div>Ann. Return</div>
                  </div>
                  <div>
                    <div className="text-white font-medium">{k.avg_volatility_pct}%</div>
                    <div>Avg Vol</div>
                  </div>
                  <div className="col-span-2">
                    <div className="text-red-400 font-medium">{k.max_drawdown_pct}%</div>
                    <div>Max Drawdown</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {best && best[0] && (
        <div className="bg-blue-950/50 border border-blue-800 rounded-xl p-5 flex items-center justify-between">
          <div>
            <div className="text-xs text-blue-400 uppercase tracking-wider mb-1">Optimal Allocation (Highest Sharpe)</div>
            <div className="text-2xl font-bold">
              {best[0].spy_pct}% SPY / {best[0].qqq_pct}% QQQ
            </div>
            <div className="text-sm text-gray-400 mt-1">
              Expected return: <span className="text-white">{(best[0].expected_return * 100).toFixed(1)}%</span>
              {" · "}Sharpe: <span className="text-white">{best[0].sharpe_ratio.toFixed(2)}</span>
              {" · "}Median outcome from $50k:{" "}
              <span className="text-emerald-400">${best[0].median_outcome.toLocaleString()}</span>
            </div>
          </div>
          <Link href="/allocator" className="text-sm text-blue-400 hover:text-blue-300 transition-colors whitespace-nowrap ml-6">
            Explore →
          </Link>
        </div>
      )}

      <div>
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">
          Dashboard Pages
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {cards.map((c) => (
            <Link
              key={c.href}
              href={c.href}
              className="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-gray-600 transition-colors group"
            >
              <div className="font-semibold text-white group-hover:text-blue-400 transition-colors mb-1">
                {c.label} →
              </div>
              <div className="text-sm text-gray-400">{c.desc}</div>
            </Link>
          ))}
        </div>
      </div>

      {!kpis && (
        <div className="text-sm text-yellow-500 bg-yellow-950/30 border border-yellow-800 rounded-lg px-4 py-3">
          API not reachable. Make sure Docker is running and{" "}
          <code className="font-mono">python api.py</code> is started on port 5000.
        </div>
      )}
    </div>
  );
}
