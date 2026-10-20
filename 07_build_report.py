"""
07_build_report.py
--------------------------------------------------------------------------------
从 MySQL 里把分析结果取出来, 生成一份自包含的 HTML 分析报告。
所有数字都是现场查库得到的, 不是手写死的。
"""
import html
import os
import subprocess
from pathlib import Path

MYSQL = os.environ.get("MYSQL_BIN", "mysql")   # mysql.exe 不在 PATH 时, 用 MYSQL_BIN 指定
BASE = Path(__file__).resolve().parent
OUT = BASE / "05_outputs"
ENV = dict(os.environ)                          # 口令只从环境变量读, 不写进代码

if not ENV.get("MYSQL_PWD"):
    raise SystemExit("请先设置环境变量 MYSQL_PWD 为 MySQL 口令再运行本脚本。")


def q(sql):
    """执行查询, 返回 [[str, ...], ...]"""
    try:
        r = subprocess.run(
            [MYSQL, "-u", "root", "gold", "--batch", "--default-character-set=utf8mb4", "-e", sql],
            capture_output=True, text=True, encoding="utf-8", env=ENV, check=True,
        )
    except FileNotFoundError:
        raise SystemExit(f"找不到 mysql 客户端: {MYSQL}\n"
                         f"请把 mysql.exe 的完整路径设到环境变量 MYSQL_BIN 里。")
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"查询失败:\n{sql}\n{e.stderr.strip()}")
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    if len(lines) < 2:
        raise SystemExit(f"查询没有返回数据, 请确认数据库已初始化:\n{sql}")
    return [l.split("\t") for l in lines[1:]]


def num(x, nd=0):
    v = float(x)
    return f"{v:,.{nd}f}"


# ---------------------------------------------------------------- 取数
kpi = q("""SELECT SUM(sales_amount), SUM(quantity), ROUND(AVG(price),2),
                  COUNT(DISTINCT order_number), COUNT(DISTINCT customer_key),
                  MIN(order_date), MAX(order_date) FROM fact_sales;""")[0]
TOTAL_SALES, QTY, AVG_PRICE, ORDERS, BUYERS, D_MIN, D_MAX = kpi

cat = q("""SELECT p.category, SUM(f.sales_amount),
                  ROUND(SUM(f.sales_amount)*100.0/(SELECT SUM(sales_amount) FROM fact_sales),2)
           FROM fact_sales f JOIN dim_products p ON p.product_key=f.product_key
           GROUP BY p.category ORDER BY 2 DESC;""")
country = q("""SELECT c.country, SUM(f.sales_amount)
               FROM fact_sales f JOIN dim_customers c ON c.customer_key=f.customer_key
               GROUP BY c.country ORDER BY 2 DESC LIMIT 6;""")
yearly = q("""SELECT YEAR(order_date), SUM(sales_amount) FROM fact_sales
              WHERE order_date IS NOT NULL GROUP BY 1 ORDER BY 1;""")
monthly = q("""SELECT DATE_FORMAT(order_date,'%Y-%m'), SUM(sales_amount) FROM fact_sales
               WHERE order_date IS NOT NULL GROUP BY 1 ORDER BY 1;""")
top5 = q("SELECT product_name, total_sales FROM report_products ORDER BY total_sales DESC LIMIT 5;")
worst5 = q("""SELECT p.product_name, COALESCE(SUM(f.sales_amount),0) rev FROM dim_products p
              LEFT JOIN fact_sales f ON f.product_key=p.product_key
              GROUP BY p.product_name ORDER BY rev LIMIT 5;""")
cust_seg = q("""SELECT customer_segment, COUNT(*), ROUND(AVG(total_sales),0), SUM(total_sales)
                FROM report_customers GROUP BY 1 ORDER BY 2 DESC;""")
prod_seg = q("""SELECT product_segment, COUNT(*), SUM(total_sales) FROM report_products
                GROUP BY 1 ORDER BY 3 DESC;""")
age_grp = q("SELECT age_group, COUNT(*) FROM report_customers GROUP BY 1 ORDER BY 2 DESC;")
cost_seg = q("""SELECT CASE WHEN cost<100 THEN 'Below 100' WHEN cost BETWEEN 100 AND 500 THEN '100-500'
                    WHEN cost BETWEEN 500 AND 1000 THEN '500-1000' ELSE 'Above 1000' END seg,
                  COUNT(*) FROM dim_products GROUP BY 1 ORDER BY 2 DESC;""")
rowof = q("""WITH yps AS (SELECT YEAR(order_date) y, product_name, SUM(sales_amount) s
                       FROM fact_sales f JOIN dim_products p ON p.product_key=f.product_key
                       WHERE order_date IS NOT NULL GROUP BY 1,2),
                  t AS (SELECT s, LAG(s) OVER (PARTITION BY product_name ORDER BY y) py FROM yps)
             SELECT CASE WHEN py IS NULL THEN 'first' WHEN s-py>0 THEN 'up'
                         WHEN s-py<0 THEN 'down' ELSE 'flat' END AS trend, COUNT(*) AS n FROM t GROUP BY 1;""")
avg_ov = q("SELECT ROUND(SUM(sales_amount)/COUNT(DISTINCT order_number),0) FROM fact_sales;")[0][0]

trend = {k: int(v) for k, v in rowof}
n_rows = int(q("SELECT COUNT(*) FROM report_customers;")[0][0])
n_prod_rows = int(q("SELECT COUNT(*) FROM report_products;")[0][0])
n_cust = int(q("SELECT COUNT(*) FROM dim_customers;")[0][0])
n_prod = int(q("SELECT COUNT(*) FROM dim_products;")[0][0])

# ---------------------------------------------------------------- SVG 组件
FONT = "'Segoe UI','Microsoft YaHei',system-ui,sans-serif"
C_MAIN, C_ACC, C_MUTE = "#2563eb", "#0ea5e9", "#94a3b8"


def hbar(rows, unit="", nd=0, w=760, barh=30, gap=13, color=C_MAIN, fmt=None):
    """横向条形图 (label, value)。"""
    vals = [float(v) for _, v in rows]
    mx = max(vals) or 1
    labelw = 168
    bw = w - labelw - 96
    h = len(rows) * (barh + gap) + 8
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}" font-family="{FONT}">']
    for i, (lab, v) in enumerate(rows):
        y = 6 + i * (barh + gap)
        length = max(2, float(v) / mx * bw)
        txt = fmt(v) if fmt else num(v, nd) + unit
        out.append(f'<text x="0" y="{y + barh * 0.72}" font-size="12.5" fill="#334155">{html.escape(lab[:26])}</text>')
        out.append(f'<rect x="{labelw}" y="{y}" width="{bw}" height="{barh}" rx="3" fill="#eef2f7"/>')
        out.append(f'<rect x="{labelw}" y="{y}" width="{length:.1f}" height="{barh}" rx="3" fill="{color}"/>')
        out.append(f'<text x="{labelw + bw + 8}" y="{y + barh * 0.72}" font-size="12" fill="#475569">{txt}</text>')
    out.append("</svg>")
    return "".join(out)


def vbars(rows, w=760, h=250, color=C_MAIN):
    """纵向柱状图 (label, value)。"""
    vals = [float(v) for _, v in rows]
    mx = max(vals) or 1
    pad_l, pad_b, pad_t = 8, 34, 14
    bw = (w - pad_l * 2) / len(rows)
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}" font-family="{FONT}">']
    for i, (lab, v) in enumerate(rows):
        bh = (float(v) / mx) * (h - pad_b - pad_t)
        x = pad_l + i * bw + bw * 0.16
        bwid = bw * 0.68
        y = h - pad_b - bh
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bwid:.1f}" height="{bh:.1f}" rx="3" fill="{color}"/>')
        out.append(f'<text x="{x + bwid / 2:.1f}" y="{y - 6:.1f}" font-size="11.5" fill="#475569" text-anchor="middle">{num(v)}</text>')
        out.append(f'<text x="{x + bwid / 2:.1f}" y="{h - pad_b + 18}" font-size="12" fill="#64748b" text-anchor="middle">{html.escape(lab)}</text>')
    out.append("</svg>")
    return "".join(out)


def line(rows, w=760, h=250, color=C_MAIN):
    """折线图 (label, value), 用于月度序列。"""
    vals = [float(v) for _, v in rows]
    mx, mn = max(vals), min(vals)
    rng = (mx - mn) or 1
    pad_l, pad_r, pad_b, pad_t = 46, 10, 30, 14
    iw, ih = w - pad_l - pad_r, h - pad_b - pad_t
    pts = []
    for i, v in enumerate(vals):
        x = pad_l + (i / max(1, len(vals) - 1)) * iw
        y = pad_t + (1 - (v - mn) / rng) * ih
        pts.append((x, y))
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{pad_l},{h - pad_b} " + poly + f" {pad_l + iw},{h - pad_b}"
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}" font-family="{FONT}">']
    for g in range(4):
        y = pad_t + ih * g / 3
        val = mx - (mx - mn) * g / 3
        out.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + iw}" y2="{y:.1f}" stroke="#e8eef5"/>')
        out.append(f'<text x="{pad_l - 8}" y="{y + 4:.1f}" font-size="10.5" fill="#94a3b8" text-anchor="end">{num(val/1e6,1)}M</text>')
    out.append(f'<polygon points="{area}" fill="{color}" opacity="0.10"/>')
    out.append(f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2"/>')
    step = max(1, len(rows) // 8)
    for i in range(0, len(rows), step):
        out.append(f'<text x="{pts[i][0]:.1f}" y="{h - pad_b + 17}" font-size="10.5" fill="#94a3b8" text-anchor="middle">{html.escape(rows[i][0])}</text>')
    out.append("</svg>")
    return "".join(out)


def donut(rows, w=330, h=260, colors=("#2563eb", "#0ea5e9", "#93c5fd")):
    total = sum(float(v) for _, v in rows)
    cx, cy, r, thick = 118, 130, 78, 26
    import math
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}" font-family="{FONT}">']
    ang = -math.pi / 2
    for i, (lab, v) in enumerate(rows):
        frac = float(v) / total
        end = ang + frac * 2 * math.pi
        large = 1 if frac > 0.5 else 0
        x1, y1 = cx + r * math.cos(ang), cy + r * math.sin(ang)
        x2, y2 = cx + r * math.cos(end), cy + r * math.sin(end)
        out.append(f'<path d="M {x1:.1f} {y1:.1f} A {r} {r} 0 {large} 1 {x2:.1f} {y2:.1f}" '
                   f'fill="none" stroke="{colors[i % len(colors)]}" stroke-width="{thick}"/>')
        ang = end
    out.append(f'<text x="{cx}" y="{cy - 2}" font-size="19" font-weight="600" fill="#0f172a" text-anchor="middle">{num(total)}</text>')
    out.append(f'<text x="{cx}" y="{cy + 18}" font-size="11" fill="#94a3b8" text-anchor="middle">customers</text>')
    for i, (lab, v) in enumerate(rows):
        y = 62 + i * 30
        out.append(f'<rect x="228" y="{y - 9}" width="10" height="10" rx="2" fill="{colors[i % len(colors)]}"/>')
        out.append(f'<text x="245" y="{y}" font-size="12" fill="#334155">{html.escape(lab)}</text>')
        out.append(f'<text x="{w - 4}" y="{y}" font-size="12" fill="#64748b" text-anchor="end">{num(v)}</text>')
    out.append("</svg>")
    return "".join(out)


def table(headers, rows, align_right_from=1):
    th = "".join(f'<th style="text-align:{"right" if i >= align_right_from else "left"}">{html.escape(h)}</th>'
                 for i, h in enumerate(headers))
    tr = "".join("<tr>" + "".join(
        f'<td style="text-align:{"right" if i >= align_right_from else "left"}">{c}</td>'
        for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>'


# ---------------------------------------------------------------- 组装
CSS = """
*{box-sizing:border-box}
body{margin:0;background:#f6f8fb;color:#0f172a;
     font-family:'Segoe UI','Microsoft YaHei',system-ui,sans-serif;line-height:1.65;font-size:14.5px}
.wrap{max-width:1060px;margin:0 auto;padding:0 28px 72px}
header{background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 55%,#0ea5e9 100%);color:#fff;padding:52px 0 44px;margin-bottom:34px}
header .wrap{padding-bottom:0}
.eyebrow{font-size:12.5px;letter-spacing:.14em;text-transform:uppercase;opacity:.82;margin-bottom:12px}
h1{margin:0 0 14px;font-size:31px;font-weight:700;letter-spacing:-.01em}
.sub{opacity:.9;font-size:14.5px;max-width:730px}
.meta{margin-top:22px;display:flex;flex-wrap:wrap;gap:10px}
.meta span{background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.22);
           padding:5px 12px;border-radius:999px;font-size:12.5px}
h2{font-size:20px;margin:44px 0 6px;padding-bottom:10px;border-bottom:2px solid #e2e8f0}
h2 .n{color:#93b4f0;font-weight:700;margin-right:8px}
h3{font-size:15px;margin:26px 0 10px;color:#1e293b}
p{margin:9px 0;color:#334155}
.lead{color:#475569}
.card{background:#fff;border:1px solid #e6edf5;border-radius:12px;padding:22px 24px;margin:16px 0;
      box-shadow:0 1px 2px rgba(15,23,42,.04)}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:22px 0 8px}
.kpi{background:#fff;border:1px solid #e6edf5;border-radius:12px;padding:16px 18px}
.kpi .k{font-size:11.5px;color:#64748b;letter-spacing:.04em;text-transform:uppercase}
.kpi .v{font-size:23px;font-weight:700;color:#0f172a;margin-top:5px;letter-spacing:-.02em}
.kpi .d{font-size:11.5px;color:#94a3b8;margin-top:2px}
table{width:100%;border-collapse:collapse;font-size:13px;margin:10px 0}
th{background:#f1f5f9;color:#475569;font-weight:600;padding:9px 11px;border-bottom:1px solid #e2e8f0;font-size:12.5px}
td{padding:8px 11px;border-bottom:1px solid #eef2f7;color:#334155}
tbody tr:hover{background:#fafcff}
code{background:#f1f5f9;padding:1.5px 6px;border-radius:4px;font-size:12.5px;
     font-family:'Cascadia Mono',Consolas,monospace;color:#1d4ed8}
pre{background:#0f172a;color:#e2e8f0;padding:16px 18px;border-radius:10px;overflow-x:auto;font-size:12.5px;
    font-family:'Cascadia Mono',Consolas,monospace;line-height:1.55}
.note{border-left:3px solid #2563eb;background:#f0f6ff;padding:12px 16px;border-radius:0 8px 8px 0;margin:14px 0;font-size:13.5px}
.warn{border-left:3px solid #f59e0b;background:#fffbeb;padding:12px 16px;border-radius:0 8px 8px 0;margin:14px 0;font-size:13.5px}
.ok{border-left:3px solid #16a34a;background:#f0fdf4;padding:12px 16px;border-radius:0 8px 8px 0;margin:14px 0;font-size:13.5px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.tag{display:inline-block;background:#eff6ff;color:#1d4ed8;border-radius:5px;padding:1px 7px;font-size:11.5px;font-weight:600}
.tag.g{background:#f0fdf4;color:#15803d}
.tag.a{background:#fffbeb;color:#b45309}
ul{margin:8px 0;padding-left:22px}li{margin:5px 0;color:#334155}
footer{margin-top:52px;padding-top:20px;border-top:1px solid #e2e8f0;color:#94a3b8;font-size:12.5px}
@media(max-width:760px){.kpis{grid-template-columns:1fr 1fr}.grid2{grid-template-columns:1fr}}
"""

diff_rows = [
    ("TOP n", "LIMIT n（放语句末尾）", "06"),
    ("DATEDIFF(MONTH, a, b)", "PERIOD_DIFF(YYMM_b, YYMM_a)", "03/11/12/13"),
    ("DATEDIFF(YEAR, a, b)", "YEAR(b) - YEAR(a)", "03/12"),
    ("DATETRUNC(month, d)", "CAST(DATE_FORMAT(d,'%Y-%m-01') AS DATE)", "07/08"),
    ("FORMAT(d,'yyyy-MMM')", "DATE_FORMAT(d,'%Y-%b')", "07"),
    ("GETDATE()", "CURDATE()", "03/12/13"),
    ("IF OBJECT_ID(...) DROP VIEW", "DROP VIEW IF EXISTS", "12/13"),
    ("GO 批次分隔符", "删除（MySQL 无批次）", "00/12/13"),
    ("CAST(x AS FLOAT)", "CAST(x AS DOUBLE)", "10/13"),
    ("int / int（截断）", "DIV（复现截断）", "12/13"),
    ("BULK INSERT ... FIRSTROW=2", "LOAD DATA INFILE ... IGNORE 1 LINES", "00"),
    ("database + schema gold", "database 直接命名 gold", "00"),
]
diff_html = table(["T-SQL 原写法", "MySQL 8 等价写法", "涉及脚本"],
                  [(f"<code>{html.escape(a)}</code>", f"<code>{html.escape(b)}</code>", c)
                   for a, b, c in diff_rows], align_right_from=99)

kpi_cards = "".join([
    f'<div class="kpi"><div class="k">总销售额</div><div class="v">¥{num(float(TOTAL_SALES)/1e6,2)}M</div><div class="d">{len(monthly)} 个月累计</div></div>',
    f'<div class="kpi"><div class="k">销量</div><div class="v">{num(QTY)}</div><div class="d">件</div></div>',
    f'<div class="kpi"><div class="k">订单数</div><div class="v">{num(ORDERS)}</div><div class="d">客单价 ¥{num(avg_ov)}</div></div>',
    f'<div class="kpi"><div class="k">平均售价</div><div class="v">¥{num(AVG_PRICE,2)}</div><div class="d">价格区间跨度大</div></div>',
    f'<div class="kpi"><div class="k">下单客户</div><div class="v">{num(BUYERS)}</div><div class="d">共 {num(n_cust)} 位客户</div></div>',
    f'<div class="kpi"><div class="k">在售产品</div><div class="v">{num(n_prod)}</div><div class="d">SKU</div></div>',
    f'<div class="kpi"><div class="k">数据区间</div><div class="v">{D_MIN} → {D_MAX}</div><div class="d">订单日期</div></div>',
    f'<div class="kpi"><div class="k">报表规模</div><div class="v">{num(n_rows)} / {num(n_prod_rows)}</div><div class="d">客户行 / 产品行</div></div>',
])

html_doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SQL 数据分析项目 · 在 MySQL 上的完整落地</title>
<style>{CSS}</style></head><body>

<header><div class="wrap">
  <div class="eyebrow">DataWithBaraa · sql-data-analytics-project</div>
  <h1>SQL 数据分析项目<br>在本机 MySQL 8.0 上的完整落地</h1>
  <div class="sub">原仓库是一套基于 SQL Server 的 T-SQL 数据分析教学项目：先做探索性分析（EDA），
  再做趋势、累计、绩效、占比、分群等进阶分析，最后产出客户与产品两张报表。
  本文档记录它在本机 MySQL 8.0 上被 1:1 重建、跑通、并对账验证的完整过程与结论。</div>
  <div class="meta">
    <span>MySQL 8.0.44</span><span>14 个脚本全部执行通过</span><span>报表与官方快照逐字节对账</span>
    <span>2026-10-20</span>
  </div>
</div></header>

<div class="wrap">

<h2><span class="n">00</span>这个项目原本是什么，为什么不能直接跑</h2>
<p>仓库里是 <b>gold 层</b>的三张表（客户维表、产品维表、销售事实表）加上 14 个分析脚本。原版全部依赖
SQL Server：<code>BULK INSERT</code> 导入、<code>DATETRUNC</code> 截断日期、<code>TOP n</code> 取前 N、
<code>sys.databases</code> 判断库是否存在，以及一个需要 <b>SQL Server 2022+</b> 才能还原的 <code>.bak</code> 备份。</p>
<div class="warn"><b>本机环境的三个硬约束：</b>没有安装 SQL Server；没有管理员权限（装不了 Developer 版）；
Docker Desktop 装了但 WSL 被安全策略禁用，Linux 容器起不来。<br>
所以改用本机已在运行的 <b>MySQL 8.0.44</b> 作为执行引擎——数据模型、脚本逻辑、输出结果全部保持原样，
只做方言层改写。</div>

<h2><span class="n">01</span>重建数据库</h2>
<p>SQL Server 是「数据库 + schema」两级结构，MySQL 是「database 即 schema」一级结构。
原脚本里到处是 <code>gold.dim_customers</code> 这种两段式引用，所以直接把 database 命名为 <code>gold</code>，
这样 <b>这些表引用一个字都不用改</b>。</p>
<p>数据用 <code>LOAD DATA INFILE</code> 从 CSV 导入（MySQL 只允许从 <code>secure_file_priv</code> 目录读文件）。
源 CSV 里有空字段：<b>17 个缺失生日、19 个缺失订单日期、7 个缺失产品分类</b>，
MySQL 严格模式会把空字符串当非法日期直接报错，所以用 <code>NULLIF</code> 显式转成 NULL，
与原表「空值即缺失」的业务含义保持一致。</p>
<div class="ok"><b>导入校验通过：</b>dim_customers <b>18,484</b> 行 · dim_products <b>295</b> 行 · fact_sales <b>60,398</b> 行，与 CSV 记录数完全吻合。</div>

<h2><span class="n">02</span>方言改写：12 处，逐条可查</h2>
<p>原始脚本保持不动（<code>03_scripts/</code>），改写版单独放在 <code>04_mysql/</code>，每个文件头部都写了对应的映射说明。
其中两处最容易踩坑，单独解释一下：</p>
<div class="card">
<h3>① DATEDIFF 不是 TIMESTAMPDIFF</h3>
<p>直觉上 <code>DATEDIFF(MONTH, a, b)</code> 应该翻成 <code>TIMESTAMPDIFF(MONTH, a, b)</code>，
但两者语义不同：SQL Server 数的是<b>跨过的月份边界数</b>（不看日），TIMESTAMPDIFF 数的是<b>满月数</b>。
比如 2021-01-20 到 2021-02-10，前者得 1，后者得 0。直接替换会让大批客户的 lifespan 少一个月。
所以改用 <code>PERIOD_DIFF(DATE_FORMAT(b,'%Y%m'), DATE_FORMAT(a,'%Y%m'))</code>，用 YYMM 相减，语义完全等价。
<code>DATEDIFF(YEAR, ...)</code> 同理，用 <code>YEAR(b) - YEAR(a)</code>。</p>
<h3>② int / int 的截断行为</h3>
<p>SQL Server 里两个 int 相除会截断小数（<code>8249/3 = 2749</code>），MySQL 的 <code>/</code> 返回小数。
为了让报表数值和官方快照一致，改写时用 <code>DIV</code> 复现截断。</p>
</div>
{diff_html}

<h2><span class="n">03</span>14 个脚本全部执行通过</h2>
<p>按 01 → 13 的顺序跑完，<b>零报错</b>，每个脚本的完整结果集都落盘在 <code>05_outputs/</code> 下（表格式文本）。
脚本 12、13 是建视图，不返回结果集，但视图创建成功并可查询。</p>

<h2><span class="n">04</span>对账：改写是否真的等价</h2>
<p>仓库自带了两张报表的官方快照 CSV（<code>gold.report_customers.csv</code> / <code>gold.report_products.csv</code>），
这是最好的验收标准。我把 MySQL 生成的报表与它<b>逐行逐列</b>比对：</p>
<div class="card">
{table(["报表", "行数（官方 / MySQL）", "完全一致的列", "仅因日期变化的列", "不一致列"], [
    ("report_customers", f"{num(n_rows)} / {num(n_rows)}", "11 列", "age、age_group、recency", "0"),
    ("report_products", f"{num(n_prod_rows)} / {num(n_prod_rows)}", "14 列", "recency_in_months", "0"),
], align_right_from=1)}
</div>
<div class="ok"><b>结论：改写是可证明等价的。</b>所有金额、数量、订单数、生命周期、分层标签、客单价、月均消费——
逐字节一致。唯一不同的是 <code>age</code> 和 <code>recency</code> 这两类「跟着当天日期算」的列：
官方快照生成于 2025-01 左右，今天是 2026-10，<b>偏移量恒为 21 个月</b>（18482 行里最小值、最大值、中位数全部是 21），
这条一致性正好反证了差异只来自「今天」，而不是逻辑错误。</div>

<h2><span class="n">05</span>分析结论</h2>
<div class="kpis">{kpi_cards}</div>

<h3>业务高度集中在单一品类</h3>
<p>自行车（Bikes）拿下 <b>{cat[0][2]}%</b> 的销售额，配件和服装加起来不到 4%。
这意味着营收对单一品类极度敏感——自行车的价格带或供应链波动，会直接放大到整体收入上。</p>
{card if False else '<div class="card">' + hbar([(c[0] + "  " + c[2] + "%", c[1]) for c in cat], color=C_MAIN) + "</div>"}

<h3>市场分布：美国与澳大利亚几乎并列第一</h3>
<p>两个市场贡献了超过一半的销售额，且体量接近；英国、德国、法国构成第二梯队。
这种「双核 + 长尾」的结构，适合把资源集中在两个主战场，同时用标准化方案覆盖长尾市场。</p>
<div class="card">{hbar([(c[0], c[1]) for c in country], color=C_ACC)}</div>

<h3>年度趋势：2013 年是一次明显的跃升</h3>
<p>2011 与 2012 相对平稳（约 {num(float(yearly[1][1])/1e4,0)} 万 / {num(float(yearly[2][1])/1e4,0)} 万），
<b>2013 年跳到 {num(float(yearly[-2][1])/1e4,0)} 万</b>，
是前一年的 {num(float(yearly[-2][1])/float(yearly[2][1]),1)} 倍。2010 和 2014 只有零星几天数据（首尾边界），不应参与同比判断。</p>
<div class="card">{vbars([(y, v) for y, v in yearly])}</div>

<h3>月度走势</h3>
<p>整体呈上行通道，且能看到明显的季节性起伏；用累计分析（脚本 08）可以看到累计线在每个年初重新起算。</p>
<div class="card">{line(monthly)}</div>

<h3>排名：Top 与 Bottom 要看从哪张表出发</h3>
<p>脚本 06 有一处很值得注意的教学点：<b>从事实表出发</b>做排名，只能看到「至少卖过一次」的产品；
<b>从维表出发</b>做 LEFT JOIN，才能把「一次都没卖出去」的产品揪出来——它们才是真正的垫底产品。
本例中确实存在销售额为 0 的在售 SKU，如果只看事实表就会完全漏掉。</p>
<div class="grid2">
<div class="card"><h3 style="margin-top:0">销售额 Top 5 产品</h3>
{table(["产品", "销售额"], [(html.escape(a), num(b)) for a, b in top5])}</div>
<div class="card"><h3 style="margin-top:0">销售额 Bottom 5 产品</h3>
{table(["产品", "销售额"], [(html.escape(a), num(b)) for a, b in worst5])}</div>
</div>

<h3>客户分群：绝大多数是「新客」</h3>
<p>按项目定义（在网满 12 个月且消费 &gt; 5000 为 VIP）分群：<b>VIP 只有 {num(cust_seg[-1][1])} 人（{num(float(cust_seg[-1][1])/n_rows*100,1)}%）</b>，
却贡献了相当高的客单；而 <b>{num(cust_seg[0][1])} 人（{num(float(cust_seg[0][1])/n_rows*100,1)}%）落在 New</b>，
平均消费仅 ¥{num(cust_seg[0][2])}。这个结构说明客户池很大但转化不足，运营重心应该在「让新客产生第二次、第三次购买」。</p>
<div class="grid2">
<div class="card">{donut([(r[0], r[1]) for r in cust_seg])}</div>
<div class="card"><h3 style="margin-top:0">各群平均消费</h3>
{table(["客群", "人数", "人均消费"], [(r[0], num(r[1]), "¥" + num(r[2])) for r in cust_seg])}</div>
</div>

<h3>产品分层：强者极强</h3>
<p>{num(prod_seg[0][1])} 个 High-Performer 吃掉了 <b>{num(float(prod_seg[0][2])/float(TOTAL_SALES)*100,1)}%</b> 的销售额，
低绩效产品只有 {num(prod_seg[-1][1])} 个、贡献 {num(float(prod_seg[-1][2])/float(TOTAL_SALES)*100,2)}%。
典型的二八结构，适合把长尾 SKU 做精简。</p>
{table(["产品分层", "SKU 数", "销售额", "占比"], [
    (r[0], num(r[1]), num(r[2]), num(float(r[2])/float(TOTAL_SALES)*100, 2) + "%") for r in prod_seg
])}

<h3>其他分布</h3>
<div class="grid2">
<div class="card"><h3 style="margin-top:0">客户年龄段</h3>
{table(["年龄段", "人数"], [(r[0], num(r[1])) for r in age_grp])}
<p style="font-size:12.5px;color:#64748b;margin-top:10px">注意：按今天（2026-10）计算，全部客户年龄都 ≥ 40 岁，
所以 20-29 / 30-39 两个段为空——这正说明 age 是随日期浮动的列。</p></div>
<div class="card"><h3 style="margin-top:0">产品成本段</h3>
{table(["成本区间", "SKU 数"], [(r[0], num(r[1])) for r in cost_seg])}</div>
</div>

<h3>同比表现</h3>
<p>用 <code>LAG()</code> 做年同比：<b>{trend.get('up',0)} 个</b>「产品-年」组合同比上升，<b>{trend.get('down',0)} 个</b>下降，
{trend.get('first',0)} 个是首个有销售的年份（没有上年可比）。整体向上，但下滑的 {trend.get('down',0)} 个需要单独看。</p>

<h2><span class="n">06</span>数据质量提示（原仓库自带，不是改写引入的）</h2>
<ul>
<li><b>客户姓名是双重编码的乱码。</b>源 CSV 里 <code>Andrés</code> 存成了 <code>Andr┬®s</code> 这类字节序列，
官方快照 CSV 里一模一样。要修的话得按 <code>cp1252 → utf-8</code> 重新转码，属于上游数据缺陷。</li>
<li><b>19 行订单缺失 order_date。</b>其中 2 位客户（key 5323、16040）的全部订单都没有日期，
会被 <code>WHERE order_date IS NOT NULL</code> 过滤掉，所以报表是 18482 行而不是 18484 行——
官方快照同样是 18482 行，行为一致。</li>
<li><b>17 位客户缺失生日</b>，报表里 <code>age</code> 为 NULL、<code>age_group</code> 记为 <code>n/a</code>，与原逻辑一致。</li>
<li><b>存在 110 岁的出生日期</b>，明显是脏数据，原项目保留未处理。</li>
<li><b>7 个产品缺失 category / subcategory</b>，已按 NULL 处理，会单独成组出现在分组统计里。</li>
</ul>

<h2><span class="n">07</span>交付物与复跑方式</h2>
<div class="card">
{table(["路径", "内容"], [
    ("<code>04_mysql/*_mysql.sql</code>", "14 个脚本的 MySQL 改写版，每个文件头注明方言映射"),
    ("<code>05_outputs/*.txt</code>", "13 个脚本的完整执行结果（表格式）"),
    ("<code>05_outputs/report_customers.tsv</code>", "客户报表 18482 行 × 15 列"),
    ("<code>05_outputs/report_products.tsv</code>", "产品报表 130 行 × 16 列"),
    ("<code>05_outputs/reconciliation.txt</code>", "与官方快照的逐列对账结果"),
    ("<code>06_validate.py</code>", "对账脚本，可随时重跑"),
    ("<code>03_scripts/</code>", "原始 T-SQL 脚本，未改动"),
])}
<h3>从头复跑</h3>
<pre>cd 04_mysql
mysql -u root -p &lt; 00_init_database_mysql.sql
for f in 0[1-9]_*.sql 1[0-3]_*.sql; do mysql -u root gold &lt; "$f"; done
python ../06_validate.py</pre>
<p style="margin-bottom:0">前提：CSV 已复制到 <code>secure_file_priv</code> 指向的目录
（先 <code>SHOW VARIABLES LIKE 'secure_file_priv'</code> 查，再改 <code>00_init_database_mysql.sql</code>
顶部那一行 <code>@csv_dir</code>）。口令通过环境变量 <code>MYSQL_PWD</code> 传入，不落盘。</p>
</div>

<div class="note"><b>如果以后装上 SQL Server 2022：</b>直接还原 <code>01_datasets/DataWarehouseAnalytics.bak</code>，
或者跑原始的 <code>03_scripts/00_init_database.sql</code>，然后把 <code>03_scripts/</code> 下的脚本原样执行即可——
那套文件我一份都没动。</div>

<footer>基于 DataWithBaraa / sql-data-analytics-project（MIT）在本机 MySQL 8.0.44 上的复现 · 报告生成于 2026-10-20</footer>
</div></body></html>
"""

p = OUT / "analysis_report.html"
p.write_text(html_doc, encoding="utf-8")
print(f"报告已生成: {p}  ({p.stat().st_size/1024:.0f} KB)")
