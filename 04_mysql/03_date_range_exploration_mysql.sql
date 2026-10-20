/* =============================================================================
   03 Date Range Exploration  ·  MySQL 8.0 改写版
   原文件: 03_scripts/03_date_range_exploration.sql
   方言差异:
     - DATEDIFF(YEAR, a, b)  ->  YEAR(b) - YEAR(a)
       SQL Server 的 DATEDIFF 数的是 "跨越的年份边界数", 不看月份/日期;
       MySQL 的 TIMESTAMPDIFF 数的是 "满年数", 两者结果会差 1。
       为了与 SQL Server 结果完全一致, 这里用 YEAR 相减。
     - GETDATE()  ->  CURDATE()
   ============================================================================= */

USE gold;

-- Determine the first and last order date and the total duration in months
SELECT
    MIN(order_date) AS first_order_date,
    MAX(order_date) AS last_order_date,
    TIMESTAMPDIFF(MONTH,
                  DATE_FORMAT(MIN(order_date), '%Y-%m-01'),
                  DATE_FORMAT(MAX(order_date), '%Y-%m-01')) AS order_range_months
FROM gold.fact_sales;

-- Find the youngest and oldest customer based on birthdate
SELECT
    MIN(birthdate)                     AS oldest_birthdate,
    YEAR(CURDATE()) - YEAR(MIN(birthdate)) AS oldest_age,
    MAX(birthdate)                     AS youngest_birthdate,
    YEAR(CURDATE()) - YEAR(MAX(birthdate)) AS youngest_age
FROM gold.dim_customers;
