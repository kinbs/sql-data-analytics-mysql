# MySQL 8.0 移植版说明

[DataWithBaraa / sql-data-analytics-project](https://github.com/DataWithBaraa/sql-data-analytics-project)
是纯 SQL Server（T-SQL）项目：`BULK INSERT`、`DATETRUNC`、`TOP n`、`sys.databases`，
外加一个需要 **SQL Server 2022+** 才能还原的 `.bak`。

没有 SQL Server、装不了或不想装的时候，整个项目就没法跑。这个仓库把 14 个分析脚本改写成 MySQL 8 可执行的版本，
**数据模型、分析逻辑、输出结果全部保持原样**，并用上游自带的官方快照做逐列对账来证明等价性。
原始的 `03_scripts/` 一份未动。

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

## 两处不能想当然的方言陷阱

其余改写大多是机械替换（`TOP` → `LIMIT`、去掉 `GO`、`IF OBJECT_ID` → `DROP VIEW IF EXISTS`），
但下面两条一旦搞错，数字会静悄悄地变错。

**① `DATEDIFF` 不等于 `TIMESTAMPDIFF`**

SQL Server 的 `DATEDIFF(MONTH, a, b)` 数的是**跨过的月份边界数**，不看日；MySQL 的
`TIMESTAMPDIFF(MONTH, a, b)` 数的是**满月数**。2021-01-20 → 2021-02-10，前者得 1，后者得 0。
直接替换会让一大批客户的 lifespan 少一个月。

等价写法是 `PERIOD_DIFF(DATE_FORMAT(b,'%Y%m'), DATE_FORMAT(a,'%Y%m'))`，用 YYMM 相减。
`DATEDIFF(YEAR, ...)` 同理，用 `YEAR(b) - YEAR(a)`。

**② `int / int` 在 SQL Server 会截断**

`8249 / 3` 在 T-SQL 里是 `2749`，在 MySQL 里是 `2749.6667`。报表的 `avg_order_value`、
`avg_monthly_spend` 都用到这个除法，所以移植版用 `DIV` 复现截断，才能和参考数值对上。

## 以后如果装了 SQL Server 2022

还原 `01_datasets/DataWarehouseAnalytics.bak`，或直接跑原始的 `03_scripts/00_init_database.sql`，
然后把 `03_scripts/` 下的脚本原样执行即可——那套文件一份都没动过。

## 已知数据缺陷（原仓库自带，非移植引入）

- 客户姓名双重编码乱码（`Andrés` 存成 `Andr┬®s`），官方快照 CSV 里也一样
- 19 行订单缺 `order_date`，其中 2 位客户全部订单无日期，被 `IS NOT NULL` 过滤
- 17 位客户缺生日，`age` 为 NULL、`age_group` 记为 `n/a`
- 存在 110 岁的出生日期
- 7 个产品缺 `category` / `subcategory`

## 归属与许可

数据、项目设计、原始 T-SQL 脚本均来自 **Baraa Khatib Salkini**
（[DataWithBaraa/sql-data-analytics-project](https://github.com/DataWithBaraa/sql-data-analytics-project)，MIT）。
原始 README 保留为 [UPSTREAM_README.md](UPSTREAM_README.md)，[LICENSE](LICENSE) 未作改动。
MySQL 改写、对账脚本与报告生成器同样以 MIT 发布。
