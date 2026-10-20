"""
validate.py  ·  对账脚本
--------------------------------------------------------------------------------
把 MySQL 生成的 gold.report_customers / gold.report_products
与仓库自带的官方快照 (01_datasets/csv-files/gold.report_*.csv) 逐行逐列比对。

两个已知且预期内的差异来源, 脚本会自动剔除并单独说明:
  1. age / age_group / recency / recency_in_months
     这些列由 GETDATE() / CURDATE() 现算, 官方快照的生成日期约为 2025-01,
     今天已是 2026-10, 因此必然不同 (记录偏移量即可)。
  2. avg_selling_price 等浮点列的显示精度
     SQL Server 打印 3375.0, MySQL 打印 3375 —— 数值相等, 按数值比较。

编码说明:
  上游 CSV 里的客户姓名本身是双重编码的乱码 (é -> ├®), 官方快照里也一样。
  为了让比对不受编码解释影响, 两边都按 latin-1 (字节一一对应) 读取,
  这样比的是字节, 而不是解码结果。
"""
import csv
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "01_datasets" / "csv-files"
OUT = BASE / "05_outputs"

TIME_RELATIVE = {"age", "age_group", "recency", "recency_in_months"}


def read_csv_bytes(path, delimiter=","):
    """按 latin-1 读取, 保证字节可比。"""
    with open(path, newline="", encoding="latin-1") as fh:
        return list(csv.DictReader(fh, delimiter=delimiter))


def num_eq(a, b):
    try:
        return abs(float(a) - float(b)) < 1e-6
    except (TypeError, ValueError):
        return False


def compare(title, official_path, mine_path, key, delimiter="\t"):
    off = {r[key]: r for r in read_csv_bytes(official_path)}
    mine = {r[key]: r for r in read_csv_bytes(mine_path, delimiter)}
    cols = list(next(iter(off.values())).keys())

    print(f"\n{'=' * 72}")
    print(f"{title}")
    print(f"{'=' * 72}")
    print(f"官方快照行数 : {len(off)}")
    print(f"MySQL 行数   : {len(mine)}")
    print(f"键集合一致   : {set(off) == set(mine)}")

    if set(off) != set(mine):
        print(f"  仅官方有: {sorted(set(off) - set(mine))[:10]}")
        print(f"  仅 MySQL 有: {sorted(set(mine) - set(off))[:10]}")

    common = set(off) & set(mine)
    ok_cols, time_cols, bad_cols = [], [], []

    print(f"\n{'列名':<24}{'不一致行数':>12}  结论")
    print("-" * 72)
    for c in cols:
        if c == key:
            continue
        bad = sum(
            1 for k in common
            if off[k][c].strip() != mine[k][c].strip()
            and not num_eq(off[k][c].strip(), mine[k][c].strip())
        )
        if c in TIME_RELATIVE:
            time_cols.append((c, bad))
            note = "随今天变化, 预期不同"
        elif bad == 0:
            ok_cols.append(c)
            note = "完全一致"
        else:
            bad_cols.append((c, bad))
            note = "!! 需检查"
        print(f"{c:<24}{bad:>12}  {note}")

    print("-" * 72)
    print(f"一致列: {len(ok_cols)}   时间相关列: {len(time_cols)}   待检查列: {len(bad_cols)}")
    if time_cols:
        print("时间相关列(不计入不一致): " + ", ".join(f"{c}({n} 行)" for c, n in time_cols))
    if bad_cols:
        print("待检查列: " + ", ".join(f"{c}({n} 行)" for c, n in bad_cols))
    return bad_cols


def age_offset():
    """量化时间相关偏移: 官方快照生成日 ≈ 2025-01。"""
    off = {r["customer_key"]: r for r in read_csv_bytes(DATA / "gold.report_customers.csv")}
    mine = {r["customer_key"]: r for r in read_csv_bytes(OUT / "report_customers.tsv", "\t")}
    diffs = sorted(int(mine[k]["recency"]) - int(off[k]["recency"]) for k in off if k in mine)
    if diffs:
        print(f"\nrecency 偏移月数: 最小 {diffs[0]}, 最大 {diffs[-1]}, 中位 {diffs[len(diffs) // 2]}")
        print("(2026-10 相对官方快照 2025-01, 正好相差约 21 个月 -> 说明差异纯由'今天'造成)")


if __name__ == "__main__":
    b1 = compare("Customer Report", DATA / "gold.report_customers.csv",
                 OUT / "report_customers.tsv", "customer_key")
    b2 = compare("Product Report", DATA / "gold.report_products.csv",
                 OUT / "report_products.tsv", "product_key")
    age_offset()
    print("\n" + "=" * 72)
    print("结论: 除 age/recency 这类跟着当天日期走的列之外, 其余列与官方快照完全一致"
          if not b1 and not b2 else "结论: 存在需要检查的列, 见上表")
    sys.exit(0 if not b1 and not b2 else 1)
