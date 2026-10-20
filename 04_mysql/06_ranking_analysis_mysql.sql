/* =============================================================================
   06 Ranking Analysis  ·  MySQL 8.0 改写版
   原文件: 03_scripts/06_ranking_analysis.sql
   方言差异:
     - SELECT TOP n ... ORDER BY x  ->  SELECT ... ORDER BY x LIMIT n
       (TOP 在 SELECT 列表前, LIMIT 在语句最末, 位置不同, 逐条调整)
   ============================================================================= */

USE gold;

-- Which 5 products Generating the Highest Revenue?
-- Simple Ranking
SELECT
    p.product_name,
    SUM(f.sales_amount) AS total_revenue
FROM gold.fact_sales f
LEFT JOIN gold.dim_products p
    ON p.product_key = f.product_key
GROUP BY p.product_name
ORDER BY total_revenue DESC
LIMIT 5;

-- Complex but Flexibly Ranking Using Window Functions
SELECT *
FROM (
    SELECT
        p.product_name,
        SUM(f.sales_amount)                             AS total_revenue,
        RANK() OVER (ORDER BY SUM(f.sales_amount) DESC) AS rank_products
    FROM gold.fact_sales f
    LEFT JOIN gold.dim_products p
        ON p.product_key = f.product_key
    GROUP BY p.product_name
) AS ranked_products
WHERE rank_products <= 5;

-- What are the 5 worst-performing products in terms of sales?
SELECT
    p.product_name,
    SUM(f.sales_amount) AS total_revenue
FROM gold.fact_sales f
LEFT JOIN gold.dim_products p
    ON p.product_key = f.product_key
GROUP BY p.product_name
ORDER BY total_revenue
LIMIT 5;

-- Starting from the fact table shows only products that sold at least once.
-- Start from the dimension to include the products that never sold (the real worst performers).
SELECT
    p.product_name,
    COALESCE(SUM(f.sales_amount), 0) AS total_revenue
FROM gold.dim_products p
LEFT JOIN gold.fact_sales f
    ON p.product_key = f.product_key
GROUP BY p.product_name
ORDER BY total_revenue
LIMIT 5;

-- Find the top 10 customers who have generated the highest revenue
SELECT
    c.customer_key,
    c.first_name,
    c.last_name,
    SUM(f.sales_amount) AS total_revenue
FROM gold.fact_sales f
LEFT JOIN gold.dim_customers c
    ON c.customer_key = f.customer_key
GROUP BY
    c.customer_key,
    c.first_name,
    c.last_name
ORDER BY total_revenue DESC
LIMIT 10;

-- The 3 customers with the fewest orders placed
SELECT
    c.customer_key,
    c.first_name,
    c.last_name,
    COUNT(DISTINCT order_number) AS total_orders
FROM gold.fact_sales f
LEFT JOIN gold.dim_customers c
    ON c.customer_key = f.customer_key
GROUP BY
    c.customer_key,
    c.first_name,
    c.last_name
ORDER BY total_orders
LIMIT 3;

-- Many customers share the lowest number of orders, so TOP 3 picks three of them at random.
-- Rank them instead to see every customer at the lowest level.
SELECT *
FROM (
    SELECT
        c.customer_key,
        c.first_name,
        c.last_name,
        COUNT(DISTINCT f.order_number)                        AS total_orders,
        RANK() OVER (ORDER BY COUNT(DISTINCT f.order_number)) AS rank_orders
    FROM gold.fact_sales f
    LEFT JOIN gold.dim_customers c
        ON c.customer_key = f.customer_key
    GROUP BY
        c.customer_key,
        c.first_name,
        c.last_name
) AS ranked_customers
WHERE rank_orders = 1;
