"""
elasticity_model.py

Estimates price elasticity using log-log regression.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pickle
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from src.utils.db import run_query

MIN_OBS = 50


# Loading Data

def load_data():
    print("Loading data...")

    df = run_query("""
        SELECT
            product_id,
            sale_date,
            total_quantity,
            avg_selling_price,
            discount_rate,
            has_discount,
            qty_lag1,
            rolling_mean_7,
            day_of_week,
            month,
            l1_category_id
        FROM feature_layer.ml_features
        ORDER BY sale_date, product_id
    """)

    df["sale_date"] = pd.to_datetime(df["sale_date"])

    print(f"Loaded {len(df):,} rows")
    return df


# Preprocessing

def preprocess(df):

    # Log transform
    df["log_qty"] = np.log1p(df["total_quantity"])
    df["log_price"] = np.log1p(df["avg_selling_price"])

    return df

# Features Building

def build_features(group):

    # Base features
    X = pd.DataFrame({
        "log_price": group["log_price"],
        "discount_rate": group["discount_rate"].fillna(0),
        "has_discount": group["has_discount"],
        "qty_lag1": group["qty_lag1"].fillna(0),
        "rolling_mean_7": group["rolling_mean_7"].fillna(0),
    })

    # One-hot encode categorical features
    dow_dummies = pd.get_dummies(group["day_of_week"], prefix="dow", drop_first=True)
    month_dummies = pd.get_dummies(group["month"], prefix="month", drop_first=True)

    X = pd.concat([X, dow_dummies, month_dummies], axis=1)

    return X


# Training Model
def train_elasticity(df):

    results = {}

    for cat_id, group in df.groupby("l1_category_id"):

        if len(group) < MIN_OBS:
            continue

        X = build_features(group)
        y = group["log_qty"]

        model = LinearRegression()
        model.fit(X, y)

        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)

        elasticity = float(model.coef_[0])

        results[int(cat_id)] = {
            "model": model,
            "elasticity": round(elasticity, 4),
            "r2": round(r2, 4),
            "n_obs": len(group),
            "feature_names": list(X.columns)
        }

        print(
            f"cat={cat_id}, elasticity={elasticity:+.3f} "
            f"R²={r2:.3f}, n={len(group)}"
        )

    print(f"\nTrained {len(results)} category models")
    return results


# elasticity classification

def classify_elasticity(e):

    if e > 0.1:
        return "positive_or_invalid"

    if e > -0.2:
        return "inelastic"

    if e > -1:
        return "moderate"

    return "elastic"


# Model Saving
def save_results(results):

    os.makedirs("models", exist_ok=True)

    # Save full model dictionary
    with open("models/elasticity_model.pkl", "wb") as f:
        pickle.dump(results, f)

    print("Saved models/elasticity_model.pkl")

    # Summary table
    summary = pd.DataFrame([
        {
            "l1_category_id": cat,
            "price_elasticity": v["elasticity"],
            "elasticity_label": classify_elasticity(v["elasticity"]),
            "r2": v["r2"],
            "n_obs": v["n_obs"]
        }
        for cat, v in results.items()
    ]).sort_values("price_elasticity")

    summary.to_csv("models/elasticity_summary.csv", index=False)

    print("Saved models/elasticity_summary.csv")


# Loading Elasticity Model
def load_elasticity():

    with open("models/elasticity_model.pkl", "rb") as f:
        return pickle.load(f)

if __name__ == "__main__":

    df = load_data()
    df = preprocess(df)

    results = train_elasticity(df)

    save_results(results)

    print("Elasticity modeling complete.")