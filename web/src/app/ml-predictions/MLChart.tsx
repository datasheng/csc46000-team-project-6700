"use client";

import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import type { Prediction } from "@/lib/api";

interface Props {
  predictions: Prediction[];
}

type ChartRow = { date: string; predicted: number; actual: number };
type Model = "lstm" | "xgboost";

function toChartRows(preds: Prediction[], ticker: string, model: Model): ChartRow[] {
  return preds
    .filter((p) => p.ticker === ticker && p.model_type.toLowerCase() === model)
    .filter((_, i) => i % 3 === 0)
    .map((p) => ({
      date:      p.date.slice(0, 10),
      predicted: parseFloat((p.predicted_return * 100).toFixed(4)),
      actual:    parseFloat((p.actual_return * 100).toFixed(4)),
    }));
}

export default function MLChart({ predictions }: Props) {
  const [model, setModel] = useState<Model>("lstm");

  const spyData = toChartRows(predictions, "SPY", model);
  const qqqData = toChartRows(predictions, "QQQ", model);

  return (
    <div className="space-y-6">
      {/* Model toggle */}
      <div className="flex gap-2">
        {(["lstm", "xgboost"] as Model[]).map((m) => (
          <button
            key={m}
            onClick={() => setModel(m)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              model === m
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-400 hover:text-white"
            }`}
          >
            {m.toUpperCase()}
          </button>
        ))}
      </div>

      {spyData.length > 0 && <Chart title={`SPY — Predicted vs Actual Return (${model.toUpperCase()})`} data={spyData} />}
      {qqqData.length > 0 && <Chart title={`QQQ — Predicted vs Actual Return (${model.toUpperCase()})`} data={qqqData} />}
    </div>
  );
}

function Chart({ title, data }: { title: string; data: ChartRow[] }) {
  return (
    <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</h2>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis
            dataKey="date"
            tick={{ fill: "#9ca3af", fontSize: 11 }}
            interval={Math.floor(data.length / 6)}
          />
          <YAxis
            tickFormatter={(v) => `${(v as number).toFixed(2)}%`}
            tick={{ fill: "#9ca3af", fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }}
            labelStyle={{ color: "#f9fafb" }}
            formatter={(v) => [`${Number(v).toFixed(3)}%`]}
          />
          <Legend wrapperStyle={{ color: "#9ca3af", fontSize: 12 }} />
          <Line type="monotone" dataKey="predicted" name="Predicted" stroke="#a78bfa" strokeWidth={1.5} dot={false} />
          <Line type="monotone" dataKey="actual" name="Actual" stroke="#34d399" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
