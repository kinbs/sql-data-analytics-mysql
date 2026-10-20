# 这个项目在本机是怎么跑通的

原仓库 `DataWithBaraa/sql-data-analytics-project` 是纯 SQL Server（T-SQL）项目。
本机没有 SQL Server、没有管理员权限、Docker 的 WSL 被安全策略禁用，因此改用
**本机已在运行的 MySQL 8.0.44** 作为执行引擎，数据模型与分析逻辑保持原样，只做方言改写。

## 结果一览

| 项 | 状态 |
|:--|:--|
| gold 三张表 | 18,484 / 295 / 60,398 行，与 CSV 完全一致 |
| 01~13 脚本 | 全部执行通过，零报错 |
| report_customers | 18,482 行 × 15 列 |
| report_products | 130 行 × 16 列 |
| 与官方快照对账 | 客户报表 11/14 列、产品报表 14/15 列**逐字节一致**；仅 age / recency 随「今天」变化，偏移恒为 21 个月 |

分析结论见 `05_outputs/analysis_report.html`（用浏览器打开）。

## 目录

```
03_scripts/            原始 T-SQL 脚本，未改动
04_mysql/              MySQL 改写版（每个文件头注明方言映射）
05_outputs/            执行结果、报表导出、对账结果、HTML 报告
06_validate.py         与官方快照逐列对账
07_build_report.py     生成 HTML 报告（数字现场查库）
01_datasets/           原始数据（CSV + .bak），未改动
```

## 复跑

MySQL 只允许从 `secure_file_priv` 指向的目录读文件，先查再放：

```sql
SHOW VARIABLES LIKE 'secure_file_priv';
```

把 `01_datasets/csv-files/` 下的
`gold.dim_customers.csv`、`gold.dim_products.csv`、`gold.fact_sales.csv`
复制到那个目录，然后把 `04_mysql/00_init_database_mysql.sql` 里三条 `LOAD DATA`
的路径改成该目录。这是唯一需要按本机修改的地方。

```bash
export MYSQL_PWD='你的口令'      # 不要写进任何文件
# 如果 mysql 不在 PATH 里，再指定： export MYSQL_BIN='/path/to/mysql.exe'

cd 04_mysql
mysql -u root < 00_init_database_mysql.sql
for f in 0[1-9]_*.sql 1[0-3]_*.sql; do
  mysql -u root gold < "$f" > "../05_outputs/${f%_mysql.sql}.txt"
done
cd ..
python 06_validate.py     # 与官方快照对账
python 07_build_report.py # 重新生成 HTML 报告
```

导出报表：

```bash
mysql -u root gold --batch --default-character-set=utf8mb4 \
  -e "SELECT * FROM report_customers ORDER BY customer_key" > ../05_outputs/report_customers.tsv
```

## 以后如果装了 SQL Server 2022

还原 `01_datasets/DataWarehouseAnalytics.bak`，或直接跑原始的 `03_scripts/00_init_database.sql`，
然后把 `03_scripts/` 下的脚本原样执行即可——那套文件一份都没动过。

## 已知数据缺陷（原仓库自带）

- 客户姓名双重编码乱码（`Andrés` 存成 `Andr┬®s`），官方快照 CSV 里也一样
- 19 行订单缺 `order_date`，其中 2 位客户全部订单无日期，被 `IS NOT NULL` 过滤
- 17 位客户缺生日，`age` 为 NULL、`age_group` 记为 `n/a`
- 存在 110 岁的出生日期
- 7 个产品缺 `category` / `subcategory`
