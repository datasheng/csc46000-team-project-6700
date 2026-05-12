import { api } from "@/lib/api";
import MLChart from "./MLChart";

export default async function MLPage() {
  let predictions = null;
  try {
    predictions = await api.predictions();
  } catch {
    // API offline
  }

  const isEmpty = !predictions || predictions.length === 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">ML Predictions</h1>
        <p className="mt-1 text-gray-400">
          LSTM and XGBoost predicted returns vs actual — walk-forward validation.
        </p>
      </div>

      {isEmpty ? (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-10 text-center">
          <div className="text-gray-400 text-lg font-medium mb-2">No predictions yet</div>
          <div className="text-gray-500 text-sm">
            Waiting for ML predictions to be loaded into the database.
          </div>
        </div>
      ) : (
        <MLChart predictions={predictions!} />
      )}
    </div>
  );
}
