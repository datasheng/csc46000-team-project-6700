"use client";

import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import type { Metric } from "@/lib/api";

interface Props {
  spy: Metric[];
  qqq: Metric[];
}

// Merge SPY and QQQ arrays by date into one array for Recharts
function merge(spy: Metric[], qqq: Metric[]) {
  const qqqMap = new Map(qqq.map((r) => [r.date, r]));
  return spy.map((s) => {
    const q = qqqMap.get(s.date);
    return {
      date: s.date.slice(0, 7), // YYYY-MM for axis
      spy_cum: s.cumulative_return,
      qqq_cum: q?.cumulative_return ?? null,
      spy_vol: s.rolling_volatility != null ? s.rolling_volatility * 100 : null,
      qqq_vol: q?.rolling_volatility != null ? q.rolling_volatility * 100 : null,
      spy_dd: s.drawdown != null ? s.drawdown * 100 : null,
      qqq_dd: q?.drawdown != null ? q.drawdown * 100 : null,
    };
  });
}

const axisStyle = { fill: "#9ca3af", fontSize: 11 };
const gridStyle = { stroke: "#1f2937" };
const tooltipStyle = { background: "#111827", border: "1px solid #374151", borderRadius: 8 };

export default function RiskCharts({ spy, qqq }: Props) {
  const data = merge(spy, qqq);

  // Sample every 5 points to keep the chart performant
  const sampled = data.filter((_, i) => i % 5 === 0);

  return (
    <div className="space-y-6">
      {/* Cumulative Return */}
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
          Cumulative Return
        </h2>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={sampled}>
            <CartesianGrid strokeDasharray="3 3" {...gridStyle} />
            <XAxis dataKey="date" tick={axisStyle} interval={Math.floor(sampled.length / 6)} />
            <YAxis tickFormatter={(v) => `${((v - 1) * 100).toFixed(0)}%`} tick={axisStyle} />
            <Tooltip
              contentStyle={tooltipStyle}
              labelStyle={{ color: "#f9fafb" }}
              formatter={(v, name) => [`${((Number(v) - 1) * 100).toFixed(1)}%`, String(name)]}
            />
            <Legend wrapperStyle={{ color: "#9ca3af", fontSize: 12 }} />
            <Line type="monotone" dataKey="spy_cum" name="SPY" stroke="#60a5fa" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="qqq_cum" name="QQQ" stroke="#fb923c" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Rolling Volatility */}
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
          Rolling 21-Day Volatility (Annualized)
        </h2>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={sampled}>
            <CartesianGrid strokeDasharray="3 3" {...gridStyle} />
            <XAxis dataKey="date" tick={axisStyle} interval={Math.floor(sampled.length / 6)} />
            <YAxis tickFormatter={(v) => `${v.toFixed(0)}%`} tick={axisStyle} />
            <Tooltip
              contentStyle={tooltipStyle}
              labelStyle={{ color: "#f9fafb" }}
              formatter={(v, name) => [`${Number(v).toFixed(1)}%`, String(name)]}
            />
            <Legend wrapperStyle={{ color: "#9ca3af", fontSize: 12 }} />
            <Line type="monotone" dataKey="spy_vol" name="SPY Vol" stroke="#60a5fa" strokeWidth={1.5} dot={false} />
            <Line type="monotone" dataKey="qqq_vol" name="QQQ Vol" stroke="#fb923c" strokeWidth={1.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Drawdown */}
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
          Drawdown (%)
        </h2>
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={sampled}>
            <CartesianGrid strokeDasharray="3 3" {...gridStyle} />
            <XAxis dataKey="date" tick={axisStyle} interval={Math.floor(sampled.length / 6)} />
            <YAxis tickFormatter={(v) => `${v.toFixed(0)}%`} tick={axisStyle} />
            <Tooltip
              contentStyle={tooltipStyle}
              labelStyle={{ color: "#f9fafb" }}
              formatter={(v, name) => [`${Number(v).toFixed(2)}%`, String(name)]}
            />
            <Legend wrapperStyle={{ color: "#9ca3af", fontSize: 12 }} />
            <Area type="monotone" dataKey="spy_dd" name="SPY DD" stroke="#60a5fa" fill="#60a5fa" fillOpacity={0.15} strokeWidth={1.5} dot={false} />
            <Area type="monotone" dataKey="qqq_dd" name="QQQ DD" stroke="#fb923c" fill="#fb923c" fillOpacity={0.15} strokeWidth={1.5} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
