/* =============================================================================
   08 Cumulative Analysis  ·  MySQL 8.0 改写版
   原文件: 03_scripts/08_cumulative_analysis.sql
   方言差异:
     - DATETRUNC(month, d)  ->  CAST(DATE_FORMAT(d, '%Y-%m-01') AS DATE)
     - DATETRUNC(year,  d)  ->  CAST(DATE_FORMAT(d, '%Y-01-01') AS DATE)
     - 窗口函数 SUM()/AVG() OVER (...) 语法两边一致, 原样保留。
   ============================================================================= */

USE gold;

-- Calculate the total sales per month
-- and the running total that restarts every year
SELECT
    order_date,
    total_sales,
    SUM(total_sales) OVER (PARTITION BY YEAR(order_date) ORDER BY order_date) AS running_total_sales
FROM
(
    SELECT
        CAST(DATE_FORMAT(order_date, '%Y-%m-01') AS DATE) AS order_date,
        SUM(sales_amount)                                 AS total_sales
    FROM gold.fact_sales
    WHERE order_date IS NOT NULL
    GROUP BY CAST(DATE_FORMAT(order_date, '%Y-%m-01') AS DATE)
) t;

-- Calculate the total sales per year
-- and the running total of sales over time
SELECT
    order_date,
    total_sales,
    SUM(total_sales) OVER (ORDER BY order_date) AS running_total_sales,
    AVG(avg_price) OVER (ORDER BY order_date)   AS moving_average_price
FROM
(
    SELECT
        CAST(DATE_FORMAT(order_date, '%Y-01-01') AS DATE) AS order_date,
        SUM(sales_amount)                                 AS total_sales,
        AVG(price)                                        AS avg_price
    FROM gold.fact_sales
    WHERE order_date IS NOT NULL
    GROUP BY CAST(DATE_FORMAT(order_date, '%Y-01-01') AS DATE)
) t;
