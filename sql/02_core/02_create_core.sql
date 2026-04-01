--- core tables (aggregated tables.)

-- daily products sales aggregation

CREATE SCHEMA IF NOT EXISTS core_layer;

DROP TABLE IF EXISTS core_layer.sales_daily;

CREATE TABLE core_layer.sales_daily AS
SELECT
    sale_date,
    product_id,
    SUM(quantity) AS total_quantity,
    AVG(selling_price) AS avg_selling_price,
    MIN(selling_price) AS min_selling_price,
    MAX(selling_price) AS max_selling_price,
    SUM(discount_amount) AS total_discount,
    AVG(landing_cost) AS avg_landing_cost,
    AVG(gross_margin) AS avg_gross_margin,
    AVG(margin_pct) AS avg_margin_pct,
    COUNT(DISTINCT order_id) AS num_orders,
    COUNT(DISTINCT customer_key) AS num_customers,
    COUNT(DISTINCT city_name) AS num_cities,
    CASE WHEN SUM(discount_amount) > 0 THEN 1 ELSE 0 END AS has_discount,
    SUM(discount_amount)/ NULLIF(SUM(selling_price * quantity), 0) AS discount_rate
FROM staging_layer.sales_cleaned
GROUP BY sale_date, product_id;

CREATE INDEX idx_sd_product_date ON core_layer.sales_daily (product_id, sale_date);

-- daily sales on different cities.

DROP TABLE IF EXISTS core_layer.sales_daily_city;

CREATE TABLE core_layer.sales_daily_city AS
SELECT
    sale_date,
    product_id,
    city_name,
    SUM(quantity) AS total_quantity,
    AVG(selling_price) AS avg_selling_price,
    SUM(discount_amount) AS total_discount,
    COUNT(DISTINCT order_id) AS num_orders,
    COUNT(DISTINCT customer_key) AS num_customers
FROM staging_layer.sales_cleaned
GROUP BY sale_date, product_id, city_name;

-- daily price change on product

DROP TABLE IF EXISTS core_layer.price_history;

CREATE TABLE core_layer.price_history AS
SELECT
    sale_date,
    product_id,
    AVG(selling_price) AS avg_price,
    MIN(selling_price) AS min_price,
    MAX(selling_price) AS max_price,
    AVG(landing_cost) AS avg_cost,
    AVG(margin_pct) AS margin_pct,
    SUM(discount_amount) / NULLIF(SUM(selling_price * quantity), 0) AS discount_rate,
    CASE WHEN SUM(discount_amount) > 0 THEN 1 ELSE 0 END AS has_discount
FROM staging_layer.sales_cleaned
GROUP BY sale_date, product_id;

-- products table (information on  products)

DROP TABLE IF EXISTS core_layer.products;

CREATE TABLE core_layer.products AS
SELECT
    p.product_id,
    p.product_name,
    p.unit,
    p.product_type,
    p.brand_name,
    p.manufacturer_name,
    p.l0_category,
    p.l1_category,
    p.l2_category,
    p.l0_category_id,
    p.l1_category_id,
    p.l2_category_id,
    s.first_sale_date,
    s.last_sale_date,
    s.active_days,
    s.total_revenue,
    s.avg_daily_qty
FROM staging_layer.products_cleaned p
LEFT JOIN (
    SELECT
        product_id,
        MIN(sale_date) AS first_sale_date,
        MAX(sale_date) AS last_sale_date,
        COUNT(DISTINCT sale_date) AS active_days,
        SUM(total_quantity * avg_selling_price) AS total_revenue,
        AVG(total_quantity) AS avg_daily_qty
    FROM core_layer.sales_daily
    GROUP BY product_id
) s USING (product_id);