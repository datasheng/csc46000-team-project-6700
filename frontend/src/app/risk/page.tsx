import { api } from "@/lib/api";
import RiskCharts from "./RiskCharts";

export default async function RiskPage() {
  let spy = null;
  let qqq = null;
  try {
    [spy, qqq] = await Promise.all([api.metrics("SPY"), api.metrics("QQQ")]);
  } catch {
    // API offline
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Risk Profile</h1>
        <p className="mt-1 text-gray-400">
          3-year daily metrics — cumulative return, rolling volatility, and drawdown.
        </p>
      </div>

      {spy && qqq ? (
        <RiskCharts spy={spy} qqq={qqq} />
      ) : (
        <div className="text-yellow-500 text-sm">API not reachable — start the backend first.</div>
      )}
    </div>
  );
}
