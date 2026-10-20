/* =============================================================================
   12 Customer Report  ·  MySQL 8.0 改写版
   原文件: 03_scripts/12_report_customers.sql
   方言差异:
     - IF OBJECT_ID(...) IS NOT NULL DROP VIEW  ->  DROP VIEW IF EXISTS
     - GO 批次分隔符  ->  删除 (MySQL 无批次概念)
     - DATEDIFF(year, birthdate, GETDATE())  ->  YEAR(CURDATE()) - YEAR(birthdate)
     - DATEDIFF(month, a, b)  ->  PERIOD_DIFF(DATE_FORMAT(b,'%Y%m'), DATE_FORMAT(a,'%Y%m'))
     - 整数除法: SQL Server 的 int / int 会截断小数 (8249/3 = 2749),
       MySQL 的 / 返回小数; 为保证与官方报表数值一致, 这里用 DIV 复现截断行为。
   ============================================================================= */

USE gold;

DROP VIEW IF EXISTS gold.report_customers;

CREATE VIEW gold.report_customers AS

WITH base_query AS (
/*---------------------------------------------------------------------------
1) Base Query: Retrieves core columns from tables
---------------------------------------------------------------------------*/
SELECT
    f.order_number,
    f.product_key,
    f.order_date,
    f.sales_amount,
    f.quantity,
    c.customer_key,
    c.customer_number,
    CONCAT(c.first_name, ' ', c.last_name)      AS customer_name,
    YEAR(CURDATE()) - YEAR(c.birthdate)         AS age
FROM gold.fact_sales f
LEFT JOIN gold.dim_customers c
    ON c.customer_key = f.customer_key
WHERE order_date IS NOT NULL
),

customer_aggregation AS (
/*---------------------------------------------------------------------------
2) Customer Aggregations: Summarizes key metrics at the customer level
---------------------------------------------------------------------------*/
SELECT
    customer_key,
    customer_number,
    customer_name,
    age,
    COUNT(DISTINCT order_number) AS total_orders,
    SUM(sales_amount)            AS total_sales,
    SUM(quantity)                AS total_quantity,
    COUNT(DISTINCT product_key)  AS total_products,
    MAX(order_date)              AS last_order_date,
    PERIOD_DIFF(DATE_FORMAT(MAX(order_date), '%Y%m'),
                DATE_FORMAT(MIN(order_date), '%Y%m')) AS lifespan
FROM base_query
GROUP BY
    customer_key,
    customer_number,
    customer_name,
    age
)
SELECT
    customer_key,
    customer_number,
    customer_name,
    age,
    CASE
        WHEN age IS NULL           THEN 'n/a'
        WHEN age < 20              THEN 'Under 20'
        WHEN age BETWEEN 20 AND 29 THEN '20-29'
        WHEN age BETWEEN 30 AND 39 THEN '30-39'
        WHEN age BETWEEN 40 AND 49 THEN '40-49'
        ELSE '50 and above'
    END AS age_group,
    CASE
        WHEN lifespan >= 12 AND total_sales >  5000 THEN 'VIP'
        WHEN lifespan >= 12 AND total_sales <= 5000 THEN 'Regular'
        ELSE 'New'
    END AS customer_segment,
    last_order_date,
    PERIOD_DIFF(DATE_FORMAT(CURDATE(), '%Y%m'),
                DATE_FORMAT(last_order_date, '%Y%m')) AS recency,
    total_orders,
    total_sales,
    total_quantity,
    total_products,
    lifespan,
    -- Compute average order value (AOV)
    CASE WHEN total_orders = 0 THEN 0
         ELSE total_sales DIV total_orders
    END AS avg_order_value,
    -- Compute average monthly spend
    CASE WHEN lifespan = 0 THEN total_sales
         ELSE total_sales DIV lifespan
    END AS avg_monthly_spend
FROM customer_aggregation;
