"use client";

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import type { ABResult } from "@/lib/api";

interface Props {
  results: ABResult[];
}

export default function ABCharts({ results }: Props) {
  // Merge A and B into one array per date
  const aMap = new Map(results.filter((r) => r.strategy === "A_6040").map((r) => [r.date, r]));
  const bRows = results.filter((r) => r.strategy === "B_5050");

  const data = bRows.map((b) => {
    const a = aMap.get(b.date);
    return {
      date: b.date.slice(0, 7),
      A_6040: a?.portfolio_value ?? null,
      B_5050: b.portfolio_value,
    };
  }).filter((_, i) => i % 5 === 0); // sample every 5 days

  return (
    <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
        Portfolio Value Over Time ($50k initial)
      </h2>
      <ResponsiveContainer width="100%" height={340}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 11 }} interval={Math.floor(data.length / 6)} />
          <YAxis
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
            tick={{ fill: "#9ca3af", fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
            labelStyle={{ color: "#f9fafb" }}
            formatter={(v, name) => [`$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}`, String(name)]}
          />
          <Legend wrapperStyle={{ color: "#9ca3af", fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="A_6040"
            name="Strategy A (60/40)"
            stroke="#60a5fa"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="B_5050"
            name="Strategy B (50/50)"
            stroke="#fb923c"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
