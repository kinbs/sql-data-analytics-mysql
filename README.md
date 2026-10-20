# sql-data-analytics-mysql

A **MySQL 8.0 port** of [DataWithBaraa / sql-data-analytics-project](https://github.com/DataWithBaraa/sql-data-analytics-project) —
the SQL Server analytics project (exploratory data analysis → advanced analytics → two reports).

Same data model, same 14 analyses, **provably identical results**. It just runs on MySQL instead of requiring
SQL Server 2022 and a `.bak` restore.

> 中文说明见 [README.zh-CN.md](README.zh-CN.md)。

---

## Why a port

The original is pure T-SQL: `BULK INSERT`, `DATETRUNC`, `TOP n`, `sys.databases`, and a backup file that
needs **SQL Server 2022+** to restore. If you don't have SQL Server (or can't install it), the whole project
is closed to you. MySQL 8 is far easier to get running — it's one download, or it's already installed.

So the 14 scripts were rewritten for MySQL, and the results were verified against the official snapshots
that ship with the upstream repo. The originals are **untouched** in `03_scripts/`.

## Results

| Item | Result |
|:--|:--|
| `gold` tables rebuilt from CSV | 18,484 customers · 295 products · 60,398 sales rows |
| Scripts `01`–`13` | all execute, zero errors |
| `report_customers` | 18,482 rows × 15 columns |
| `report_products` | 130 rows × 16 columns |
| **Reconciliation vs official snapshots** | customer report **11 of 14 columns identical**, product report **14 of 15 identical**, **0 unexplained mismatches** |

The only columns that differ are `age` and `recency` — they're computed from *today's* date, and the official
snapshots were generated around 2025-01. The offset is **exactly 21 months on every one of the 18,482 rows**
(min = max = median), which is the proof that the difference comes from the clock, not from the logic.

The generated analysis report lives at [`05_outputs/analysis_report.html`](05_outputs/analysis_report.html).
GitHub shows it as source — download it and open it in a browser to see it rendered.

## Layout

```
03_scripts/            original T-SQL, untouched
04_mysql/              the MySQL 8 rewrite — each file states its dialect mapping in the header
05_outputs/            execution output, report exports, reconciliation log, HTML report
06_validate.py         reconciles both reports against the official CSVs, column by column
07_build_report.py     regenerates the HTML analysis report (queries the DB live)
01_datasets/           original data (CSV + .bak), untouched
```

## Quickstart

MySQL only reads files from the directory named by `secure_file_priv`:

```sql
SHOW VARIABLES LIKE 'secure_file_priv';
```

Copy the three `gold.*.csv` files from `01_datasets/csv-files/` into that directory, then point the three
`LOAD DATA` statements in `04_mysql/00_init_database_mysql.sql` at it. **That is the only machine-specific edit.**

```bash
export MYSQL_PWD='your-password'      # never commit this
export MYSQL_BIN='/path/to/mysql'     # only if mysql isn't on PATH

cd 04_mysql
mysql -u root < 00_init_database_mysql.sql
for f in 0[1-9]_*.sql 1[0-3]_*.sql; do
  mysql -u root gold < "$f" > "../05_outputs/${f%_mysql.sql}.txt"
done
cd ..
python 06_validate.py       # reconcile against the official snapshots
python 07_build_report.py   # rebuild 05_outputs/analysis_report.html
```

## The two dialect traps worth knowing

Most of the rewrite is mechanical (`TOP` → `LIMIT`, `GO` batches dropped, `IF OBJECT_ID` → `DROP VIEW IF EXISTS`).
Two things are not, and both silently produce wrong numbers if you get them wrong.

**1. `DATEDIFF` is not `TIMESTAMPDIFF`.**

SQL Server's `DATEDIFF(MONTH, a, b)` counts **month boundaries crossed** and ignores the day. MySQL's
`TIMESTAMPDIFF(MONTH, a, b)` counts **complete months elapsed**. For 2021-01-20 → 2021-02-10 the first returns 1,
the second returns 0. Swapping them shaves a month off a large share of customer lifespans.

The equivalent is `PERIOD_DIFF(DATE_FORMAT(b,'%Y%m'), DATE_FORMAT(a,'%Y%m'))` — subtract YYMM values.
Same for `DATEDIFF(YEAR, ...)` → `YEAR(b) - YEAR(a)`.

**2. `int / int` truncates in SQL Server, but not in MySQL.**

`8249 / 3` is `2749` in T-SQL and `2749.6667` in MySQL. The reports use this division for `avg_order_value`
and `avg_monthly_spend`, so the port uses `DIV` to reproduce the truncation and match the reference numbers.

## About the data

The upstream CSVs have their own defects, faithfully preserved (they're in the official snapshots too):
customer names are double-encoded mojibake (`Andrés` stored as `Andr┬®s`), 19 order rows have no `order_date`
(two customers have no dated orders at all, which is why the report has 18,482 rows and not 18,484),
17 customers have no birthdate, and one birthdate implies an age of 110.

## Attribution

Data, project design and the original T-SQL scripts: **Baraa Khatib Salkini** —
[DataWithBaraa/sql-data-analytics-project](https://github.com/DataWithBaraa/sql-data-analytics-project), MIT.
The original README is preserved as [UPSTREAM_README.md](UPSTREAM_README.md); the MIT licence is unchanged in [LICENSE](LICENSE).

The MySQL rewrite, the reconciliation harness and the report generator are released under the same MIT licence.
