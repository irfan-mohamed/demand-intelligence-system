"""
main.py file the fastapi interface
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from src.decision_engine.decision_engine import get_latest_features, load_prediction_models, predict_demand, predict_elasticity, decision_recommendation

app = FastAPI(
    title = "Demand Intelligence API"
)

models = load_prediction_models()

class ForecastResponse(BaseModel):
    product_id : int
    demand_q10 : float
    demand_q50 : float
    demand_q90 : float
    interval_width : float

class ElasticityResponse(BaseModel):
    category_id : int
    elasticity : float

class SegmentResponse(BaseModel):
    product_id : int
    abc_class : str
    xyz_class : str
    abc_xyz_class : str
    demand_cov : float

class RecommendationResponse(BaseModel):
    product_id : int
    reorder_qty : float
    safety_stock : float
    demand_q10 : float
    demand_q50 : float
    demand_q90 : float
    adjusted_demand : float
    price_elasticity : float
    abc_xyz : str    

@app.get("/")
def root():
    return {"status": "ok", "message": "Demand Intelligence API Running"}

@app.get("/forecast/{product_id}", response_model = ForecastResponse)
def forecast(product_id: int):
    features = get_latest_features(product_id)
    if features.empty:
        raise HTTPException(status_code = 404, detail = "Product Not Found")

    q10, q50, q90 = predict_demand(models, features)
    return ForecastResponse(
        product_id = product_id,
        demand_q10 = round(q10, 2),
        demand_q50 = round(q50, 2),
        demand_q90 = round(q90, 2),
        interval_width = round((q90 - q50), 2)
    )
        
@app.get("/elasticity/{category_id}", response_model = ElasticityResponse)
def elasticity(category_id: int):
    elasticity = predict_elasticity(models, category_id)
    if not elasticity :
        raise HTTPException(status_code = 404, detail = "l1_category_id Not Found")
    return ElasticityResponse(
        category_id = category_id,
        elasticity = elasticity
    )

@app.get("/segment/{product_id}", response_model= SegmentResponse)
def segment(product_id: int):
    features = get_latest_features(product_id)
    if features.empty :
        raise HTTPException(status_code = 404, detail = "No Product ID found")
    row = features.iloc[0]
    return SegmentResponse(
        product_id = product_id,
        abc_class = row.get("abc_class"),
        xyz_class = row.get("xyz_class"),
        abc_xyz_class = row.get("abc_xyz_class"),
        demand_cov = row.get("demand_cov")
    )

@app.get("/recommendation/{product_id}", response_model = RecommendationResponse)
def recommendation(product_id: int, upcoming_discount: bool = False):
    result = decision_recommendation(product_id, models, upcoming_discount)
    if not result:
        raise HTTPException(status_code = 404, detail = "No Product Id Found")
    return RecommendationResponse(
        product_id = product_id,
        reorder_qty = result['reorder_qty'],
        safety_stock = result['safety_stock'],
        demand_q10 = result['demand_q10'],
        demand_q50 = result['demand_q50'],
        demand_q90 = result['demand_q90'],
        adjusted_demand = result['adjusted_demand'],
        price_elasticity = result['price_elasticity'],
        abc_xyz = result['abc_xyz']
    )