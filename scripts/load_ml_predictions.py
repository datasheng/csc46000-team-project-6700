import pandas as pd
import sys
sys.path.append('.')
from src.db.loaders import load_predictions

files = [
    'ml_predictions_SPY_lstm.csv',
    'ml_predictions_SPY_xgboost.csv',
    'ml_predictions_QQQ_lstm.csv',
    'ml_predictions_QQQ_xgboost.csv'
]

dfs = []
for f in files:
    df = pd.read_csv(f)
    df = df.rename(columns={'model_name': 'model_type'})
    # clean up the date column - remove the time part
    df['date'] = pd.to_datetime(df['date']).dt.date
    dfs.append(df)

combined = pd.concat(dfs, ignore_index=True)
print(f"Loading {len(combined)} predictions...")
load_predictions(combined)
print("Done — ML predictions loaded.")