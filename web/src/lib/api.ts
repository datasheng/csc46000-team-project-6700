const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export interface KPI {
  ticker: string;
  ann_return_pct: number;
  avg_volatility_pct: number;
  max_drawdown_pct: number;
  total_return_pct: number;
}

export interface Metric {
  date: string;
  ticker: string;
  daily_return: number;
  cumulative_return: number;
  rolling_volatility: number;
  drawdown: number;
}

export interface MonteCarloRow {
  qqq_pct: number;
  spy_pct: number;
  expected_return: number;
  volatility: number;
  sharpe_ratio: number;
  worst_case_p95: number;
  median_outcome: number;
}

export interface ABResult {
  date: string;
  strategy: string;
  portfolio_value: number;
  cumulative_return: number;
  daily_return: number;
}

export interface ABSummary {
  t_statistic: number;
  p_value: number;
  significant: number;
  strategy_a_final: number;
  strategy_b_final: number;
  recommendation: string;
}

export interface Prediction {
  date: string;
  ticker: string;
  predicted_return: number;
  actual_return: number;
  model_name: string;
}

export const api = {
  kpis:        ()             => get<KPI[]>("/kpis"),
  metrics:     (ticker: string) => get<Metric[]>(`/metrics?ticker=${ticker}`),
  monteCarlo:  ()             => get<MonteCarloRow[]>("/monte-carlo"),
  bestAlloc:   ()             => get<MonteCarloRow[]>("/monte-carlo/best"),
  abResults:   ()             => get<ABResult[]>("/ab-results"),
  abSummary:   ()             => get<ABSummary[]>("/ab-summary"),
  predictions: (model?: string) =>
    get<Prediction[]>(model ? `/predictions?model_name=${model}` : "/predictions"),
};
