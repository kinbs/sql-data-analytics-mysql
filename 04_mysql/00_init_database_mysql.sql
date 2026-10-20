/* =============================================================
   00_init_database  ·  MySQL 8.0 版本
   -------------------------------------------------------------
   对应原文件: 03_scripts/00_init_database.sql  (T-SQL / SQL Server)

   方言差异说明:
   1. SQL Server 是 "数据库 DataWarehouseAnalytics + schema gold" 两级结构,
      MySQL 是 "database = schema" 一级结构。
      因此这里直接建一个名为 `gold` 的 database,
      这样原脚本里的 `gold.dim_customers` 这类两段式引用可以原样使用。
   2. BULK INSERT ... FIRSTROW = 2  ->  LOAD DATA INFILE ... IGNORE 1 LINES
      MySQL 服务器只允许从 secure_file_priv 指向的目录读文件
      (用 SHOW VARIABLES LIKE 'secure_file_priv'; 查看)。
      所以先把这个目录下的三个 CSV 找到/复制过去,
      再把下面三条 LOAD DATA 的路径改成那个目录 —— 这是本文件唯一需要按本机改的地方。
   3. nvarchar(50) -> VARCHAR(50); tinyint 保持 TINYINT UNSIGNED。
   ============================================================= */

DROP DATABASE IF EXISTS gold;
CREATE DATABASE gold
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;
USE gold;

CREATE TABLE dim_customers (
    customer_key   INT,
    customer_id    INT,
    customer_number VARCHAR(50),
    first_name     VARCHAR(50),
    last_name      VARCHAR(50),
    country        VARCHAR(50),
    marital_status VARCHAR(50),
    gender         VARCHAR(50),
    birthdate      DATE,
    create_date    DATE
) ENGINE = InnoDB;

CREATE TABLE dim_products (
    product_key    INT,
    product_id     INT,
    product_number VARCHAR(50),
    product_name   VARCHAR(50),
    category_id    VARCHAR(50),
    category       VARCHAR(50),
    subcategory    VARCHAR(50),
    maintenance    VARCHAR(50),
    cost           INT,
    product_line   VARCHAR(50),
    start_date     DATE
) ENGINE = InnoDB;

CREATE TABLE fact_sales (
    order_number  VARCHAR(50),
    product_key   INT,
    customer_key  INT,
    order_date    DATE,
    shipping_date DATE,
    due_date      DATE,
    sales_amount  INT,
    quantity      TINYINT UNSIGNED,
    price         INT
) ENGINE = InnoDB;

-- -------------------------------------------------------------
-- 导入数据
-- -------------------------------------------------------------
/* 源 CSV 中存在空字段 (birthdate 17 个 / order_date 19 个 / category 等 7 个),
   MySQL 严格模式会把 '' 当作非法日期报错, 所以这里用 @变量 + NULLIF 转成 NULL,
   与 SQL Server 端 "空值即缺失" 的业务含义保持一致。 */

LOAD DATA INFILE 'D:/MySQL/MySQL Server 8.0/Uploads/gold.dim_customers.csv'
INTO TABLE dim_customers
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(customer_key, customer_id, customer_number, first_name, last_name,
 country, marital_status, gender, @birthdate, @create_date)
SET birthdate   = NULLIF(@birthdate, ''),
    create_date = NULLIF(@create_date, '');

LOAD DATA INFILE 'D:/MySQL/MySQL Server 8.0/Uploads/gold.dim_products.csv'
INTO TABLE dim_products
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(product_key, product_id, product_number, product_name, category_id,
 @category, @subcategory, @maintenance, @cost, product_line, @start_date)
SET category    = NULLIF(@category, ''),
    subcategory = NULLIF(@subcategory, ''),
    maintenance = NULLIF(@maintenance, ''),
    cost        = NULLIF(@cost, ''),
    start_date  = NULLIF(@start_date, '');

LOAD DATA INFILE 'D:/MySQL/MySQL Server 8.0/Uploads/gold.fact_sales.csv'
INTO TABLE fact_sales
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(order_number, product_key, customer_key, @order_date, @shipping_date, @due_date,
 @sales_amount, @quantity, @price)
SET order_date    = NULLIF(@order_date, ''),
    shipping_date = NULLIF(@shipping_date, ''),
    due_date      = NULLIF(@due_date, ''),
    sales_amount  = NULLIF(@sales_amount, ''),
    quantity      = NULLIF(@quantity, ''),
    price         = NULLIF(@price, '');

-- -------------------------------------------------------------
-- 校验: 行数应与 CSV 行数 - 1 一致 (18484 / 295 / 60398)
-- -------------------------------------------------------------
SELECT 'dim_customers' AS table_name, COUNT(*) AS rows_loaded FROM dim_customers
UNION ALL SELECT 'dim_products', COUNT(*) FROM dim_products
UNION ALL SELECT 'fact_sales',   COUNT(*) FROM fact_sales;
