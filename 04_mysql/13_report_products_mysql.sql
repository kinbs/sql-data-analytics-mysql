/* =============================================================================
   13 Product Report  ·  MySQL 8.0 改写版
   原文件: 03_scripts/13_report_products.sql
   方言差异:
     - IF OBJECT_ID(...) IS NOT NULL DROP VIEW  ->  DROP VIEW IF EXISTS
     - GO 批次分隔符  ->  删除
     - DATEDIFF(MONTH, a, b)  ->  PERIOD_DIFF(DATE_FORMAT(b,'%Y%m'), DATE_FORMAT(a,'%Y%m'))
     - CAST(x AS FLOAT)  ->  CAST(x AS DOUBLE)
     - 整数除法用 DIV 复现 SQL Server 截断行为 (165375/49 = 3375)。
   ============================================================================= */

USE gold;

DROP VIEW IF EXISTS gold.report_products;

CREATE VIEW gold.report_products AS

WITH base_query AS (
/*---------------------------------------------------------------------------
1) Base Query: Retrieves core columns from fact_sales and dim_products
---------------------------------------------------------------------------*/
    SELECT
        f.order_number,
        f.order_date,
        f.customer_key,
        f.sales_amount,
        f.quantity,
        p.product_key,
        p.product_name,
        p.category,
        p.subcategory,
        p.cost
    FROM gold.fact_sales f
    LEFT JOIN gold.dim_products p
        ON f.product_key = p.product_key
    WHERE order_date IS NOT NULL  -- only consider valid sales dates
),

product_aggregations AS (
/*---------------------------------------------------------------------------
2) Product Aggregations: Summarizes key metrics at the product level
---------------------------------------------------------------------------*/
SELECT
    product_key,
    product_name,
    category,
    subcategory,
    cost,
    PERIOD_DIFF(DATE_FORMAT(MAX(order_date), '%Y%m'),
                DATE_FORMAT(MIN(order_date), '%Y%m'))            AS lifespan,
    MAX(order_date)                                                 AS last_sale_date,
    COUNT(DISTINCT order_number)                                    AS total_orders,
    COUNT(DISTINCT customer_key)                                    AS total_customers,
    SUM(sales_amount)                                               AS total_sales,
    SUM(quantity)                                                   AS total_quantity,
    ROUND(AVG(CAST(sales_amount AS DOUBLE) / NULLIF(quantity, 0)), 1) AS avg_selling_price
FROM base_query

GROUP BY
    product_key,
    product_name,
    category,
    subcategory,
    cost
)

/*---------------------------------------------------------------------------
  3) Final Query: Combines all product results into one output
---------------------------------------------------------------------------*/
SELECT
    product_key,
    product_name,
    category,
    subcategory,
    cost,
    last_sale_date,
    PERIOD_DIFF(DATE_FORMAT(CURDATE(), '%Y%m'),
                DATE_FORMAT(last_sale_date, '%Y%m')) AS recency_in_months,
    CASE
        WHEN total_sales >  50000 THEN 'High-Performer'
        WHEN total_sales >= 10000 THEN 'Mid-Range'
        ELSE 'Low-Performer'
    END AS product_segment,
    lifespan,
    total_orders,
    total_sales,
    total_quantity,
    total_customers,
    avg_selling_price,
    -- Average Order Revenue (AOR)
    CASE
        WHEN total_orders = 0 THEN 0
        ELSE total_sales DIV total_orders
    END AS avg_order_revenue,

    -- Average Monthly Revenue
    CASE
        WHEN lifespan = 0 THEN total_sales
        ELSE total_sales DIV lifespan
    END AS avg_monthly_revenue

FROM product_aggregations;
