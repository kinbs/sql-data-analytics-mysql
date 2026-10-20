/* =============================================================================
   10 Part-to-Whole Analysis  ·  MySQL 8.0 改写版
   原文件: 03_scripts/10_part_to_whole_analysis.sql
   方言差异:
     - CAST(x AS FLOAT)  ->  CAST(x AS DOUBLE)   (MySQL 无 FLOAT 目标类型的等价语义)
     - MySQL 的 / 本身返回小数, 百分比计算与 SQL Server 一致。
   ============================================================================= */

USE gold;

-- Which categories contribute the most to overall sales?
WITH category_sales AS (
    SELECT
        p.category,
        SUM(f.sales_amount) AS total_sales
    FROM gold.fact_sales f
    LEFT JOIN gold.dim_products p
        ON p.product_key = f.product_key
    GROUP BY p.category
)
SELECT
    category,
    total_sales,
    SUM(total_sales) OVER ()                                                 AS overall_sales,
    ROUND((CAST(total_sales AS DOUBLE) / SUM(total_sales) OVER ()) * 100, 2) AS percentage_of_total
FROM category_sales
ORDER BY total_sales DESC;
