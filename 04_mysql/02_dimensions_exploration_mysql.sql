/* =============================================================================
   02 Dimensions Exploration  ·  MySQL 8.0 改写版
   原文件: 03_scripts/02_dimensions_exploration.sql
   方言差异: 仅需 USE gold (原 T-SQL 靠 USE 切库, 这里 database 即 schema)。
   ============================================================================= */

USE gold;

-- Retrieve a list of unique countries from which customers originate
SELECT DISTINCT
    country
FROM gold.dim_customers
ORDER BY country;

-- Retrieve a list of unique categories, subcategories, and products
SELECT DISTINCT
    category,
    subcategory,
    product_name
FROM gold.dim_products
ORDER BY category, subcategory, product_name;
