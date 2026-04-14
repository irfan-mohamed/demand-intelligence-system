"""
Decision engine helps in model decisions.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import math
import numpy as np
import pandas as pd
from src.utils.db import run_query
from src.models.elasticity_model import load_elasticity
from src.models.demand_forecaster import load_models, FEATURES

# Configs
CLASS_MULTIPLIERS = {
    "A": {"X": 1.5, "Y": 1.3, "Z": 1.2},
    "B": {"X": 1.3, "Y": 1.2, "Z": 1.1},
    "C": {"X": 1.2, "Y": 1.1, "Z": 1.0},
}
LEAD_TIME_DAYS = 5

# Load Models
def load_prediction_models():
    print("Loading Models....")
    demand_models = load_models()
    elasticity_model = load_elasticity()

    return {
        "q10": demand_models['q10'],
        "q50": demand_models["q50"],
        "q90": demand_models["q90"],
        "elasticity": elasticity_model
    }

# Getting Data Features
def get_latest_features(product_id: int):
    df = run_query(f"""
        SELECT *
        FROM feature_layer.ml_features
        WHERE product_id = {product_id}
        ORDER BY sale_date DESC
        LIMIT 1
    """)
    return df

# Predicting Demand
def predict_demand(models, features):
    X = features[FEATURES].fillna(0)

    q10 = max(0, float(np.expm1(models["q10"].predict(X)[0])))
    q50 = max(0, float(np.expm1(models["q50"].predict(X)[0])))
    q90 = max(0, float(np.expm1(models["q90"].predict(X)[0])))

    return q10, q50, q90

# Elasticity Prediction
def predict_elasticity(models, category_id:int):
    elasticity_data = models["elasticity"]
    if category_id in elasticity_data:
        return elasticity_data[category_id]["elasticity"]

# Adjusted Demand
def adjust_demand(q50, elasticity, upcoming_discount):
    if upcoming_discount and elasticity < -0.5:
        return q50 * (1 + abs(elasticity) * 0.2)

    return q50

# Decision Engine
def decision_recommendation(product_id, models, upcoming_discount = False):
    features = get_latest_features(product_id)

    if features.empty:
        return {"No Data For The Product {product_id}"}

    row = features.iloc[0]
    print(row)
    prediction_date = features["sale_date"].max() + pd.Timedelta(days =1)
    # Forecast Demand
    q10, q50, q90 = predict_demand(models, features)

    # Elasticity
    cat_id = int(row.get("l1_category_id", 0))
    elasticity = predict_elasticity(models, cat_id)

    # Adjusted Demand
    adj_q50 = adjust_demand(q50, elasticity, upcoming_discount)

    # ABC-XYZ Classified
    abc = str(row.get("abc_class", "B"))
    xyz = str(row.get("xyz_class", "Y"))

    multiplier = CLASS_MULTIPLIERS.get(abc, {}).get(xyz, 1.2)

    # Safety Stock
    uncertainty = max(q90 - q50, q50 * 0.1)
    safety_stock = uncertainty * multiplier

    # Reorder Point
    reorder_point = (adj_q50 * LEAD_TIME_DAYS) + safety_stock

    reorder_qty = reorder_point # Need to substract inventory stock data

    if q10 * LEAD_TIME_DAYS > reorder_point:
        urgency = "CRITICAL"
    elif q50 * LEAD_TIME_DAYS > reorder_point:
        urgency = "HIGH"
    elif q50 > 0:
        urgency = "MEDIUM"
    else:
        urgency = "LOW"

    return {
        "product_id": product_id,
        "prediction_date": prediction_date,
        "reorder_qty": math.ceil(reorder_qty),
        "safety_stock": math.ceil(safety_stock),
        "demand_q10": round(q10, 2),
        "demand_q50": round(q50, 2),
        "demand_q90": round(q90, 2),
        "adjusted_demand": round(adj_q50, 2),
        "price_elasticity": round(elasticity, 4),
        "abc_xyz": f"{abc}{xyz}",
        "urgency" : urgency
    }

# Batch Recommendation
def batch_decisions(product_ids, models):

    results = []

    for pid in product_ids:
        try:
            res = decision_recommendation(pid, models)
            results.append(res)
        except Exception as e:
            print(f"Error for {pid}: {e}")

    return pd.DataFrame(results)

if __name__ == "__main__":

    models = load_prediction_models()
