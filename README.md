# Demand Intelligence System

## Problem Statement
Retail inventory decisions are difficult when demand is volatile, prices change frequently, and products respond differently to discounts. Static reorder rules often lead to stockouts, overstocking, and missed revenue opportunities.

This project builds a Demand Intelligence System that helps answer three operational questions:

1. How much demand should we expect for a product in the near term?
2. How sensitive is that product category to price changes and discounts?
3. How much inventory should be reordered, with what safety stock, and how urgent is the action?

The system combines forecasting, price elasticity estimation, and inventory decision logic into a single pipeline and exposes predictions through a FastAPI service.

## Folder Structure
```text
Inventory ML System/
├── api/
│   └── main.py
├── config/
│   └── config.py
├── data/
│   └── raw/
│       └── products.csv
├── models/
│   ├── demand_evaluation.csv
│   ├── demand_forecaster_q10.pkl
│   ├── demand_forecaster_q50.pkl
│   ├── demand_forecaster_q90.pkl
│   ├── elasticity_model.pkl
│   └── elasticity_summary.csv
├── notebooks/
│   ├── demand_forecasting_eda.ipynb
│   ├── eda_on_raw_data.ipynb
│   └── elasticity_forecasting_eda.ipynb
├── sql/
│   ├── 01_staging/
│   │   └── 01_create_stage.sql
│   ├── 02_core/
│   │   └── 02_create_core.sql
│   └── 03_features/
│       └── 03_create_features.sql
├── src/
│   ├── decision_engine/
│   │   └── decision_engine.py
│   ├── models/
│   │   ├── demand_forecaster.py
│   │   └── elasticity_model.py
│   └── utils/
│       └── db.py
├── requirement.txt
└── run_pipeline.py
```

## Dataset
The project is built on retail product and transaction data.

### Available data in the project
- `data/raw/products.csv`
  - Product master data
  - Includes product hierarchy such as `product_id`, `product_name`, `brand_name`, `l0_category`, `l1_category`, `l2_category`, and category IDs

### Expected database tables
The SQL pipeline expects raw data to be loaded into PostgreSQL tables:
- `raw_layer.products`
- `raw_layer.sales`

### Key fields used across the pipeline
- Product information: product ID, product name, brand, category hierarchy
- Sales information: sale date, quantity, selling price, discount amount, landing cost
- Geography: city name
- Customer and order identifiers

### Engineered dataset
The final ML dataset is created in `feature_layer.ml_features` and includes:
- Time features: `day_of_week`, `month`, `week_of_year`, `is_weekend`
- Lag features: `qty_lag1`, `qty_lag7`, `qty_lag14`, `qty_lag28`
- Rolling features: moving averages, standard deviations, rolling maximums
- Price and promotion features: average selling price, discount rate, discount flags, price change percentage
- Product metadata: category IDs, brand, product age
- Inventory segmentation: `abc_class`, `xyz_class`, `abc_xyz_class`, demand coefficient of variation

## Approach
The system is designed as a layered analytics pipeline.

### 1. Data preparation
The SQL pipeline transforms raw retail data into three layers:
- **Staging layer**
  - Cleans products and sales records
  - Standardizes text fields
  - Filters invalid quantities and prices
- **Core layer**
  - Builds daily product-level sales aggregates
  - Creates city-level sales aggregates
  - Builds price history and product summary tables
- **Feature layer**
  - Creates ABC-XYZ segmentation
  - Computes geographic demand index
  - Builds machine learning features for forecasting and pricing analysis

### 2. Demand forecasting
A quantile forecasting approach is used to estimate uncertainty in demand instead of only predicting a single value.

The system predicts:
- `Q10`: low-demand scenario
- `Q50`: median expected demand
- `Q90`: high-demand scenario

This helps the business estimate both expected demand and risk bounds for inventory planning.

### 3. Price elasticity modeling
The project estimates category-level price elasticity using log-log regression.  
This measures how demand changes when price changes.

The elasticity output is used to classify categories into:
- `elastic`
- `moderate`
- `inelastic`
- `positive_or_invalid`

This is useful for understanding whether discounts are likely to materially increase demand.

### 4. Decision engine
The decision engine combines:
- demand forecast intervals
- elasticity estimates
- discount effect adjustments
- ABC-XYZ classification multipliers
- lead time assumptions

It then produces:
- reorder quantity
- safety stock
- adjusted demand
- urgency level

### 5. API layer
A FastAPI service exposes the intelligence system through endpoints for:
- demand forecast
- elasticity lookup
- segmentation lookup
- reorder recommendation

## Model Used

### Demand Forecasting Model
- **Algorithm**: LightGBM Regressor
- **Objective**: Quantile regression
- **Models trained**:
  - `demand_forecaster_q10.pkl`
  - `demand_forecaster_q50.pkl`
  - `demand_forecaster_q90.pkl`

### Forecasting target
- `total_quantity`

### Forecasting features
- Calendar features
- Lag demand features
- Rolling statistical features
- Price and discount features
- Product/category identifiers
- Product age

### Elasticity Model
- **Algorithm**: Linear Regression
- **Method**: Log-log regression
- **Granularity**: Category level (`l1_category_id`)

This model estimates the elasticity coefficient for each category with sufficient observations.

## Results

### Demand forecasting result
Saved evaluation from `models/demand_evaluation.csv`:

- **Model**: LightGBM Q50
- **MAE**: 14.01
- **RMSE**: 97.06
- **MAPE**: 40.59%

### Elasticity modeling result
Saved summary from `models/elasticity_summary.csv`:

- **Category models trained**: 194
- **Average R²**: 0.6530
- **Minimum R²**: 0.1207
- **Maximum R²**: 0.8996

### Elasticity label distribution
- **Elastic**: 5 categories
- **Moderate**: 73 categories
- **Inelastic**: 108 categories
- **Positive or invalid**: 8 categories

### Output artifacts
Generated model and summary files:
- `models/demand_forecaster_q10.pkl`
- `models/demand_forecaster_q50.pkl`
- `models/demand_forecaster_q90.pkl`
- `models/demand_evaluation.csv`
- `models/elasticity_model.pkl`
- `models/elasticity_summary.csv`

## How to Run the Project

### 1. Create and activate a virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install -r requirement.txt
```

### 3. Configure PostgreSQL connection
Update the database settings in `config/config.py`:

- host
- port
- database
- user
- password
- 
The project expects a PostgreSQL database with raw tables loaded under:

`raw_layer.products`
`raw_layer.sales`

### 4. Run the SQL feature pipeline
```bash
python run_pipeline.py
```
This creates the feature tables used by the ML models.

### 5. Train the demand forecasting model
```bash
python src/models/demand_forecaster.py
```

### 6. Train the elasticity model
```bash
python src/models/elasticity_model.py
```
### 7. Start the API
```bash
uvicorn api.main:app --reload
```

### 8. Available API endpoints
- GET /
- GET /forecast/{product_id}
- GET /elasticity/{category_id}
- GET /segment/{product_id}
- GET /recommendation/{product_id}
```bash
http://127.0.0.1:8000/forecast/476763
```

## Project Summary
This project is an end-to-end retail demand intelligence system that combines:

- SQL-based data engineering
- quantile demand forecasting
- category-level price elasticity estimation
- inventory recommendation logic
- FastAPI deployment
- 
Its main goal is to support smarter replenishment decisions by making demand, uncertainty, and pricing response visible in one system.
