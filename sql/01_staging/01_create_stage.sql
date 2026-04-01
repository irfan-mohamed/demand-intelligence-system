
-- 01_create_staging.sql

CREATE SCHEMA IF NOT EXISTS staging_layer;

-- 1. PRODUCTS CLEANED

DROP TABLE IF EXISTS staging_layer.products_cleaned;

CREATE TABLE staging_layer.products_cleaned AS
SELECT
    product_id::int AS product_id,
    LOWER(TRIM(product_name)) AS product_name,
    LOWER(TRIM(unit)) AS unit,
    LOWER(TRIM(product_type)) AS product_type,
    COALESCE(LOWER(TRIM(brand_name)), 'unknown') AS brand_name,
    COALESCE(LOWER(TRIM(manufacturer_name)), 'unknown') AS manufacturer_name,
    LOWER(TRIM(l0_category)) AS l0_category,
    LOWER(TRIM(l1_category)) AS l1_category,
    LOWER(TRIM(l2_category)) AS l2_category,
    l0_category_id::int AS l0_category_id,
    l1_category_id::int AS l1_category_id,
    l2_category_id::int AS l2_category_id

FROM raw_layer.products
WHERE product_id IS NOT NULL;

CREATE INDEX idx_pc_product_id ON staging_layer.products_cleaned(product_id);

-- 2. SALES CLEANED

DROP TABLE IF EXISTS staging_layer.sales_cleaned;

CREATE TABLE staging_layer.sales_cleaned AS
SELECT
    date_::date AS sale_date,
    TRIM(city_name) AS city_name,
    order_id::bigint AS order_id,
    cart_id::bigint AS cart_id,
    dim_customer_key::bigint AS customer_key,
    product_id::int AS product_id,
    procured_quantity::int AS quantity,
    unit_selling_price::numeric(14,4) AS selling_price,
    total_discount_amount::numeric(14,4) AS discount_amount,
    total_weighted_landing_price::numeric(14,4) AS landing_cost,
    (unit_selling_price - total_weighted_landing_price)::numeric(14,4) AS gross_margin,
    CASE
        WHEN unit_selling_price > 0
        THEN ((unit_selling_price - total_weighted_landing_price)
              / unit_selling_price)::numeric(8,4)
        ELSE NULL
    END AS margin_pct
FROM raw_layer.sales
WHERE
    date_ IS NOT NULL
    AND product_id IS NOT NULL
    AND procured_quantity > 0
    AND unit_selling_price >= 0
    AND total_weighted_landing_price >= 0;

CREATE INDEX idx_sc_product_date ON staging_layer.sales_cleaned (product_id, sale_date);
CREATE INDEX idx_sc_date ON staging_layer.sales_cleaned (sale_date);
