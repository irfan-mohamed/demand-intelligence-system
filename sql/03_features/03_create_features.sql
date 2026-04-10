-- Feature Tables

CREATE SCHEMA IF NOT EXISTS feature_layer;

DROP TABLE IF EXISTS feature_layer.abc_xyz;

-- abc-xyz classifier (revenue - demand)

CREATE TABLE feature_layer.abc_xyz AS
WITH product_stats AS (
    SELECT
        product_id,
        SUM(total_quantity * avg_selling_price) AS total_revenue,
        AVG(total_quantity) AS mean_daily_qty,
        STDDEV(total_quantity) AS std_daily_qty,
        STDDEV(total_quantity) / NULLIF(AVG(total_quantity), 0) AS cov
    FROM core_layer.sales_daily
    GROUP BY product_id
),
revenue_cumulative AS (
    SELECT
        product_id,
        total_revenue,
        mean_daily_qty,
        std_daily_qty,
        cov,
        SUM(total_revenue) OVER () AS grand_total,
        SUM(total_revenue) OVER (
            ORDER BY total_revenue DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_revenue
    FROM product_stats
)
SELECT
    product_id,
    total_revenue,
    mean_daily_qty,
    std_daily_qty,
    COALESCE(cov, 0) AS cov,
    CASE
        WHEN cumulative_revenue / NULLIF(grand_total,0) <= 0.80 THEN 'A'
        WHEN cumulative_revenue / NULLIF(grand_total,0) <= 0.95 THEN 'B'
        ELSE 'C'
    END AS abc_class,
    CASE
        WHEN COALESCE(cov,0) < 0.5 THEN 'X'
        WHEN COALESCE(cov,0) < 1.0 THEN 'Y'
        ELSE 'Z'
    END AS xyz_class,
    CASE
        WHEN cumulative_revenue / NULLIF(grand_total,0) <= 0.80 THEN 'A'
        WHEN cumulative_revenue / NULLIF(grand_total,0) <= 0.95 THEN 'B'
        ELSE 'C'
    END ||
    CASE
        WHEN COALESCE(cov,0) < 0.5 THEN 'X'
        WHEN COALESCE(cov,0) < 1.0 THEN 'Y'
        ELSE 'Z'
    END AS abc_xyz_class
FROM revenue_cumulative;

CREATE INDEX idx_abcxyz_product ON feature_layer.abc_xyz (product_id);

-- Geographic demand index

DROP TABLE IF EXISTS feature_layer.geo_demand_index;

CREATE TABLE feature_layer.geo_demand_index AS
WITH national AS (
    SELECT product_id, AVG(total_quantity) AS national_avg
    FROM core_layer.sales_daily
    GROUP BY product_id
),
city_level AS (
    SELECT product_id, city_name, AVG(total_quantity) AS city_avg
    FROM core_layer.sales_daily_city
    GROUP BY product_id, city_name
)
SELECT
    c.product_id,
    c.city_name,
    c.city_avg,
    n.national_avg,
    c.city_avg / NULLIF(n.national_avg, 0) AS geo_demand_index
FROM city_level c
JOIN national n USING (product_id);

-- ML Features

DROP TABLE IF EXISTS feature_layer.ml_features;

CREATE TABLE feature_layer.ml_features AS
WITH lagged AS (
    SELECT
        sd.sale_date,
        sd.product_id,
        sd.total_quantity,
        COALESCE(AVG(sd.total_quantity) OVER (
        PARTITION BY sd.product_id
        ORDER BY sd.sale_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ), 0) AS product_avg_qty,
        sd.avg_selling_price,
        sd.total_discount,
        sd.avg_landing_cost,
        sd.avg_margin_pct,
        sd.has_discount,
        sd.discount_rate,
        sd.num_orders,
        sd.num_cities,
        EXTRACT(DOW FROM sd.sale_date)::int AS day_of_week,
        EXTRACT(MONTH FROM sd.sale_date)::int AS month,
        EXTRACT(YEAR FROM sd.sale_date)::int AS year,
        EXTRACT(DOY FROM sd.sale_date)::int AS day_of_year,
        EXTRACT(WEEK FROM sd.sale_date)::int AS week_of_year,
        CASE 
            WHEN EXTRACT(DOW FROM sd.sale_date) IN (0,6) THEN 1 ELSE 0 
        END AS is_weekend,
        COALESCE(LAG(sd.total_quantity,  1) OVER w, 0) AS qty_lag1,
        COALESCE(LAG(sd.total_quantity,  7) OVER w, 0) AS qty_lag7,
        COALESCE(LAG(sd.total_quantity, 14) OVER w, 0) AS qty_lag14,
        COALESCE(LAG(sd.total_quantity, 28) OVER w, 0) AS qty_lag28,
        COALESCE(LAG(sd.avg_selling_price, 1) OVER w, 0) AS price_lag1,
        COALESCE(LAG(sd.avg_selling_price, 7) OVER w, 0) AS price_lag7,
        COALESCE(LAG(sd.has_discount, 1)  OVER w, 0) AS discount_lag1,
        COALESCE(LAG(sd.discount_rate, 1) OVER w, 0) AS discount_rate_lag1,
        COALESCE(AVG(sd.total_quantity) OVER (
            PARTITION BY sd.product_id ORDER BY sd.sale_date
            ROWS BETWEEN 6  PRECEDING AND 1 PRECEDING), 0) AS rolling_mean_7,
        COALESCE(AVG(sd.total_quantity) OVER (
            PARTITION BY sd.product_id ORDER BY sd.sale_date
            ROWS BETWEEN 13 PRECEDING AND 1 PRECEDING), 0) AS rolling_mean_14,
        COALESCE(AVG(sd.total_quantity) OVER (
            PARTITION BY sd.product_id ORDER BY sd.sale_date
            ROWS BETWEEN 29 PRECEDING AND 1 PRECEDING), 0) AS rolling_mean_30,
        COALESCE(STDDEV(sd.total_quantity) OVER (
            PARTITION BY sd.product_id ORDER BY sd.sale_date
            ROWS BETWEEN 6  PRECEDING AND 1 PRECEDING), 0) AS rolling_std_7,
        COALESCE(STDDEV(sd.total_quantity) OVER (
            PARTITION BY sd.product_id ORDER BY sd.sale_date
            ROWS BETWEEN 29 PRECEDING AND 1 PRECEDING), 0) AS rolling_std_30,
        COALESCE(MAX(sd.total_quantity) OVER (
            PARTITION BY sd.product_id ORDER BY sd.sale_date
            ROWS BETWEEN 29 PRECEDING AND 1 PRECEDING), 0) AS rolling_max_30,
        (sd.avg_selling_price - LAG(sd.avg_selling_price,1) OVER w) / NULLIF(LAG(sd.avg_selling_price,1) OVER w, 0) AS price_change_pct
    FROM core_layer.sales_daily sd
    WINDOW w AS (PARTITION BY sd.product_id ORDER BY sd.sale_date)
)
SELECT
    l.*,
    p.l0_category_id,
    p.l1_category_id,
    p.l2_category_id,
    p.brand_name,
    (l.sale_date - p.first_sale_date) AS product_age_days,
    az.abc_class,
    az.xyz_class,
    az.abc_xyz_class,
    az.cov AS demand_cov
FROM lagged l
JOIN core_layer.products p USING (product_id)
JOIN feature_layer.abc_xyz az USING (product_id)
WHERE l.qty_lag28 IS NOT NULL;