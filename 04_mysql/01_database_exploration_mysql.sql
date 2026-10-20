/* =============================================================================
   01 Database Exploration  ·  MySQL 8.0 改写版
   原文件: 03_scripts/01_database_exploration.sql
   方言差异:
     - 原脚本靠 "当前数据库" 隐式限定范围; MySQL 的 INFORMATION_SCHEMA 是全局的,
       因此显式加 TABLE_SCHEMA = 'gold' 限定, 语义与原脚本一致。
   ============================================================================= */

USE gold;

-- Retrieve a list of all tables in the database
SELECT
    TABLE_CATALOG,
    TABLE_SCHEMA,
    TABLE_NAME,
    TABLE_TYPE
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'gold';

-- Retrieve all columns for a specific table (dim_customers)
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    CHARACTER_MAXIMUM_LENGTH
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'gold'
  AND TABLE_NAME   = 'dim_customers';
