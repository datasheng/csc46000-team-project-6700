"use client";

import { useState } from "react";
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from "recharts";
import type { MonteCarloRow } from "@/lib/api";

interface Props {
  rows: MonteCarloRow[];
  bestQqqPct: number | null;
}

const fmt = (v: number) => `$${v.toLocaleString()}`;
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

export default function AllocatorChart({ rows, bestQqqPct }: Props) {
  const [selected, setSelected] = useState<MonteCarloRow | null>(
    bestQqqPct !== null ? (rows.find((r) => r.qqq_pct === bestQqqPct) ?? null) : null
  );

  const data = rows.map((r) => ({
    ...r,
    label: `${r.qqq_pct}%`,
    expected_return_pct: r.expected_return * 100,
    volatility_pct: r.volatility * 100,
  }));

  return (
    <div className="space-y-6">
      {/* Main chart */}
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
          Median Outcome & Sharpe by QQQ Allocation
        </h2>
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart data={data} onClick={(e) => { if (e?.activeIndex != null) setSelected(rows[e.activeIndex as number]); }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis dataKey="label" tick={{ fill: "#9ca3af", fontSize: 11 }} label={{ value: "QQQ %", position: "insideBottom", offset: -2, fill: "#6b7280", fontSize: 11 }} />
            <YAxis yAxisId="left" tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} tick={{ fill: "#9ca3af", fontSize: 11 }} />
            <YAxis yAxisId="right" orientation="right" tickFormatter={(v) => v.toFixed(2)} tick={{ fill: "#9ca3af", fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
              labelStyle={{ color: "#f9fafb", fontWeight: 600 }}
              formatter={(val, name) => {
                const n = Number(val);
                const s = String(name);
                if (s === "Median Outcome" || s === "Worst Case (P5)") return [fmt(n), s];
                if (s === "Sharpe Ratio") return [n.toFixed(3), s];
                return [n, s];
              }}
            />
            <Legend wrapperStyle={{ color: "#9ca3af", fontSize: 12 }} />
            {bestQqqPct !== null && (
              <ReferenceLine yAxisId="left" x={`${bestQqqPct}%`} stroke="#34d399" strokeDasharray="4 4" label={{ value: "Best", fill: "#34d399", fontSize: 11 }} />
            )}
            <Bar yAxisId="left" dataKey="median_outcome" name="Median Outcome" fill="#3b82f6" opacity={0.8} radius={[3, 3, 0, 0]} />
            <Bar yAxisId="left" dataKey="worst_case_p95" name="Worst Case (P5)" fill="#ef4444" opacity={0.5} radius={[3, 3, 0, 0]} />
            <Line yAxisId="right" type="monotone" dataKey="sharpe_ratio" name="Sharpe Ratio" stroke="#f59e0b" strokeWidth={2} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
        <p className="text-xs text-gray-500 mt-2 text-center">Click any bar to see details below</p>
      </div>

      {/* Detail card */}
      {selected && (
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-700 grid grid-cols-2 gap-6 md:grid-cols-4">
          <Stat label="Allocation" value={`${selected.spy_pct}% SPY / ${selected.qqq_pct}% QQQ`} />
          <Stat label="Expected Return" value={pct(selected.expected_return)} highlight />
          <Stat label="Volatility" value={pct(selected.volatility)} />
          <Stat label="Sharpe Ratio" value={selected.sharpe_ratio.toFixed(3)} highlight />
          <Stat label="Median Outcome" value={fmt(selected.median_outcome)} highlight />
          <Stat label="Worst Case (P5)" value={fmt(selected.worst_case_p95)} />
        </div>
      )}

      {/* Table */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase tracking-wider">
              <th className="px-4 py-3 text-left">QQQ %</th>
              <th className="px-4 py-3 text-left">SPY %</th>
              <th className="px-4 py-3 text-right">Exp. Return</th>
              <th className="px-4 py-3 text-right">Volatility</th>
              <th className="px-4 py-3 text-right">Sharpe</th>
              <th className="px-4 py-3 text-right">Median ($50k)</th>
              <th className="px-4 py-3 text-right">Worst Case</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.qqq_pct}
                onClick={() => setSelected(r)}
                className={`border-b border-gray-800/50 cursor-pointer transition-colors hover:bg-gray-800 ${
                  r.qqq_pct === bestQqqPct ? "bg-emerald-950/30" : ""
                } ${selected?.qqq_pct === r.qqq_pct ? "bg-gray-800" : ""}`}
              >
                <td className="px-4 py-2 font-mono">{r.qqq_pct}%</td>
                <td className="px-4 py-2 font-mono">{r.spy_pct}%</td>
                <td className="px-4 py-2 text-right">{pct(r.expected_return)}</td>
                <td className="px-4 py-2 text-right">{pct(r.volatility)}</td>
                <td className={`px-4 py-2 text-right font-mono ${r.qqq_pct === bestQqqPct ? "text-emerald-400 font-bold" : ""}`}>
                  {r.sharpe_ratio.toFixed(3)}
                </td>
                <td className="px-4 py-2 text-right">{fmt(r.median_outcome)}</td>
                <td className="px-4 py-2 text-right text-red-400">{fmt(r.worst_case_p95)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div>
      <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</div>
      <div className={`text-lg font-semibold ${highlight ? "text-white" : "text-gray-300"}`}>{value}</div>
    </div>
  );
}
