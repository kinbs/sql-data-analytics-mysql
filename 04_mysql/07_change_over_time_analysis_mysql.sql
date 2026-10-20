/* =============================================================================
   07 Change Over Time Analysis  ·  MySQL 8.0 改写版
   原文件: 03_scripts/07_change_over_time_analysis.sql
   方言差异:
     - DATETRUNC(month, d)  ->  CAST(DATE_FORMAT(d, '%Y-%m-01') AS DATE)
       MySQL 没有 DATETRUNC, 用格式化回每月 1 号再转回 DATE, 结果同 SQL Server。
     - FORMAT(d, 'yyyy-MMM')  ->  DATE_FORMAT(d, '%Y-%b')
       .NET 格式串换成 MySQL 格式符; %b = Jan..Dec 三字母月份。
   ============================================================================= */

USE gold;

-- Analyse sales performance over time
-- Quick Date Functions
SELECT
    YEAR(order_date)             AS order_year,
    MONTH(order_date)            AS order_month,
    SUM(sales_amount)            AS total_sales,
    COUNT(DISTINCT customer_key) AS total_customers,
    SUM(quantity)                AS total_quantity
FROM gold.fact_sales
WHERE order_date IS NOT NULL
GROUP BY YEAR(order_date), MONTH(order_date)
ORDER BY YEAR(order_date), MONTH(order_date);

-- DATETRUNC()
SELECT
    CAST(DATE_FORMAT(order_date, '%Y-%m-01') AS DATE) AS order_date,
    SUM(sales_amount)            AS total_sales,
    COUNT(DISTINCT customer_key) AS total_customers,
    SUM(quantity)                AS total_quantity
FROM gold.fact_sales
WHERE order_date IS NOT NULL
GROUP BY CAST(DATE_FORMAT(order_date, '%Y-%m-01') AS DATE)
ORDER BY CAST(DATE_FORMAT(order_date, '%Y-%m-01') AS DATE);

-- FORMAT()
-- Note: FORMAT() returns text, so ORDER BY sorts the months alphabetically
-- (Apr, Aug, Dec...), not in time order
SELECT
    DATE_FORMAT(order_date, '%Y-%b') AS order_date,
    SUM(sales_amount)              AS total_sales,
    COUNT(DISTINCT customer_key)   AS total_customers,
    SUM(quantity)                  AS total_quantity
FROM gold.fact_sales
WHERE order_date IS NOT NULL
GROUP BY DATE_FORMAT(order_date, '%Y-%b')
ORDER BY DATE_FORMAT(order_date, '%Y-%b');
