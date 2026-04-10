"""
demand_forecaster.py

Trains three lightGBM quantile models: Q10, Q50, Q90.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pickle
import numpy as np
import pandas as pd
import lightgbm as lgb

from sklearn.metrics import mean_absolute_error, mean_squared_error
from src.utils.db import run_query

TARGET = "total_quantity"

QUANTILES = {
    "q10": 0.10,
    "q50": 0.50,
    "q90": 0.90
}

# Features
FEATURES = [
    "day_of_week", "month", "is_weekend", "week_of_year",
    "qty_lag1", "qty_lag7",
    "rolling_mean_7", "rolling_std_7",
    "avg_selling_price", "discount_rate", "has_discount", "price_change_pct",
    "product_avg_qty",
    "product_id", "l1_category_id", "l2_category_id",
    "product_age_days"
]

# Parameters
LGB_PARAMS = {
    "n_estimators": 300,
    "learning_rate": 0.03,
    "num_leaves": 128,
    "max_depth": 10,
    "min_child_samples": 20,
    "subsample": 0.8,
    "colsample_bytree": 0.7,
    "random_state": 42,
    "n_jobs": -1
}


# Load Data

def load_data():
    print("Loading data...")

    df = run_query("""
        SELECT * 
        FROM feature_layer.ml_features
        ORDER BY product_id, sale_date
    """)

    df["sale_date"] = pd.to_datetime(df["sale_date"])

    print(f"Loaded {len(df):,} rows")
    return df


# Train - Test Split
def split_data(df):

    split_date = df["sale_date"].max() - pd.Timedelta(days=30)

    train_idx = df["sale_date"] <= split_date
    test_idx  = df["sale_date"] > split_date

    X = df[FEATURES].fillna(0)
    y = df[TARGET]

    X_tr, X_te = X[train_idx], X[test_idx]
    y_tr, y_te = y[train_idx], y[test_idx]

    return X_tr, X_te, y_tr, y_te


# Evaluation

def evaluate(y_true, y_pred, label):

    mae  = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = np.mean(np.abs((y_true - y_pred) / np.where(y_true == 0, 1, y_true))) * 100

    print(f"[{label}] MAE={mae:.2f} RMSE={rmse:.2f} MAPE={mape:.2f}%")

    return {"model": label, "mae": mae, "rmse": rmse, "mape": mape}


# Training

def train(df):

    X_tr, X_te, y_tr, y_te = split_data(df)

    # Log Transformation
    y_tr_log = np.log1p(y_tr)

    models = {}
    preds  = {}

    for name, alpha in QUANTILES.items():

        print(f"Training LightGBM {name} (alpha={alpha})")

        model = lgb.LGBMRegressor(
            objective="quantile",
            alpha=alpha,
            **LGB_PARAMS
        )

        model.fit(X_tr, y_tr_log)

        models[name] = model

        # Predict and convertion from log to back
        pred_log = model.predict(X_te)
        preds[name] = np.expm1(pred_log)

    # Evaluate median model
    evals = []
    evals.append(evaluate(y_te, preds["q50"], "LightGBM Q50"))

    # Coverage check
    coverage = ((y_te >= preds["q10"]) & (y_te <= preds["q90"])).mean()
    print(f"80% interval coverage: {coverage:.2%}")

    return models, pd.DataFrame(evals)


# saving models
def save(models, evals):

    os.makedirs("models", exist_ok=True)

    for name, model in models.items():
        path = f"models/demand_forecaster_{name}.pkl"

        with open(path, "wb") as f:
            pickle.dump(model, f)

        print(f"Saved {path}")

    evals.to_csv("models/demand_evaluation.csv", index=False)

    print("\n Model Evaluation")
    print(evals)


# Load Models
def load_models():

    models = {}

    for name in QUANTILES.keys():
        path = f"models/demand_forecaster_{name}.pkl"

        if os.path.exists(path):
            with open(path, "rb") as f:
                models[name] = pickle.load(f)

    return models


if __name__ == "__main__":
    df = load_data()
    models, evals = train(df)
    save(models, evals)
    print("Quantile demand forecasting complete.")