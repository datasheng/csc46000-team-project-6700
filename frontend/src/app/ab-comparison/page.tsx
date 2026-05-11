import { api } from "@/lib/api";
import ABCharts from "./ABCharts";

export default async function ABPage() {
  let results = null;
  let summary = null;
  try {
    [results, summary] = await Promise.all([api.abResults(), api.abSummary()]);
  } catch {
    // API offline
  }

  const s = summary?.[0];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">A/B Test</h1>
        <p className="mt-1 text-gray-400">
          Strategy A (60% SPY / 40% QQQ) vs Strategy B (50% SPY / 50% QQQ) — $50,000 initial investment.
        </p>
      </div>

      {s && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatCard label="Strategy A Final" value={`$${s.strategy_a_final.toLocaleString()}`} color="blue" />
          <StatCard label="Strategy B Final" value={`$${s.strategy_b_final.toLocaleString()}`} color="orange" />
          <StatCard label="p-value" value={s.p_value.toFixed(4)} color={s.significant ? "red" : "gray"} />
          <StatCard
            label="Significant?"
            value={s.significant ? "Yes (p < 0.05)" : "No (p ≥ 0.05)"}
            color={s.significant ? "red" : "gray"}
          />
        </div>
      )}

      {s?.recommendation && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 text-sm text-gray-300 leading-relaxed">
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Business Recommendation</div>
          {s.recommendation}
        </div>
      )}

      {results ? (
        <ABCharts results={results} />
      ) : (
        <div className="text-yellow-500 text-sm">API not reachable — start the backend first.</div>
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  const colors: Record<string, string> = {
    blue:   "text-blue-400",
    orange: "text-orange-400",
    red:    "text-red-400",
    gray:   "text-gray-300",
  };
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</div>
      <div className={`text-xl font-bold ${colors[color]}`}>{value}</div>
    </div>
  );
}
