r"""build_index.py — 生成 Pages 站点首页 problems/index.html（按日期倒序的题目卡片）"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "problems" / "index.html"

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>每日英文题面 · 目录</title>
<script>
try { var _d = JSON.parse(localStorage.getItem('eqp1.dark')); if (_d === true || (_d === null && window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches)) document.documentElement.classList.add('dark'); } catch (e) {}
</script>
<style>
:root{--fg:#1c2733;--bg:#f6f7f9;--card:#fff;--line:#dde3ea;--dim:#8a94a0;--acc:#e8720c;color-scheme:light}
:root.dark{--fg:#cdd3da;--bg:#24262b;--card:#2c2f35;--line:#3c4048;--dim:#8f97a3;--acc:#f0932f;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;color:var(--fg);background:var(--bg);
  font-family:"Segoe UI",system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
main{max-width:720px;margin:0 auto;padding:28px 20px 70px}
h1{font-size:20px;margin:0 0 4px}
.sub{color:var(--dim);font-size:13px;margin-bottom:18px}
.card{display:flex;align-items:baseline;gap:10px;background:var(--card);border:1px solid var(--line);
  border-radius:10px;padding:12px 16px;margin-bottom:10px;text-decoration:none;color:inherit;flex-wrap:wrap}
.card:hover{border-color:var(--acc)}
.card .date{color:var(--dim);font-size:13px;min-width:86px}
.card b{font-size:15.5px;font-weight:600}
.card .rt{margin-left:auto;background:var(--acc);color:#fff;border-radius:6px;padding:0 8px;
  font-size:12px;font-weight:600}
.card .tg{width:100%;color:var(--dim);font-size:12px}
footer{margin-top:26px;color:var(--dim);font-size:12px;text-align:center}
</style>
</head>
<body>
<main>
<h1>每日英文题面</h1>
<div class="sub">A statement a day keeps the WA away · rating 1400–1800 · 点击进入题面与生词页</div>
__ROWS__
<footer>由 scripts/build_index.py 生成于 __GEN__</footer>
</main>
</body>
</html>
"""


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    base = ROOT / "problems"
    rows = []
    for d in sorted(base.iterdir(), reverse=True):
        m = d / "meta.json"
        if not d.is_dir() or not m.exists() or not (d / "page.html").exists():
            continue
        try:
            meta = json.loads(m.read_text(encoding="utf-8"))
        except Exception:
            continue
        tags = " ".join("#" + t for t in meta.get("tags", [])[:5])
        rows.append(
            f'<a class="card" href="{d.name}/page.html">'
            f'<span class="date">{meta["date"]}</span><b>{meta["name"]}</b>'
            f'<span class="rt">{meta["rating"]}</span>'
            f'<span class="tg">{tags}</span></a>')

    html = TEMPLATE.replace("__ROWS__", "\n".join(rows)).replace(
        "__GEN__", time.strftime("%Y-%m-%d %H:%M"))
    OUT.write_text(html, encoding="utf-8")
    print(f"[ok] index：{len(rows)} 天 → {OUT}")


if __name__ == "__main__":
    main()
