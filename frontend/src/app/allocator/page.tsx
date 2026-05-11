import { api } from "@/lib/api";
import AllocatorChart from "./AllocatorChart";

export default async function AllocatorPage() {
  let rows = null;
  let best = null;
  try {
    [rows, best] = await Promise.all([api.monteCarlo(), api.bestAlloc()]);
  } catch {
    // API offline
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Allocator</h1>
        <p className="mt-1 text-gray-400">
          10,000-path Monte Carlo over 5 years. Each point is one SPY/QQQ split.
        </p>
      </div>

      {best && best[0] && (
        <div className="bg-emerald-950/40 border border-emerald-800 rounded-xl p-4 text-sm">
          <span className="text-emerald-400 font-semibold">Best allocation by Sharpe: </span>
          {best[0].spy_pct}% SPY / {best[0].qqq_pct}% QQQ — Sharpe{" "}
          <span className="font-mono">{best[0].sharpe_ratio.toFixed(3)}</span>, median outcome{" "}
          <span className="text-emerald-400 font-semibold">${best[0].median_outcome.toLocaleString()}</span> from $50k over 5 years.
        </div>
      )}

      {rows ? (
        <AllocatorChart rows={rows} bestQqqPct={best?.[0]?.qqq_pct ?? null} />
      ) : (
        <div className="text-yellow-500 text-sm">API not reachable — start the backend first.</div>
      )}
    </div>
  );
}
