r"""build_stats.py — 聚合 problems/*/words.json 生成总词表页面 problems/stats.html

口径（2026-11-07 定案）：
- 只聚合**每日生词表**（已过阈值筛选的词），不是题面全文——介词永远不会霸榜；
- 排序按「出现天数」优先（一天出现十次只计一天），其次总次数，再按 Zipf（更罕见在前）；
- 「已认识」过滤在浏览器端做（读 eqp1.known），保持队友各自独立；
- bf（阈值外保底词）也计入，带「补」标记。

用法：python scripts/build_stats.py （CI 在 build_index 之后调用）
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "problems"
OUT = BASE / "stats.html"

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>总词表 · statement-a-day</title>
<script>
try { var _d = JSON.parse(localStorage.getItem('eqp1.dark')); if (_d === true || (_d === null && window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches)) document.documentElement.classList.add('dark'); } catch (e) {}
</script>
<style>
:root{--fg:#1c2733;--bg:#f6f7f9;--card:#fff;--line:#dde3ea;--dim:#8a94a0;--acc:#e8720c;
  --gbg:#e4e8ee;--gfg:#5a6472;--track:#c9cfd8;color-scheme:light}
:root.dark{--fg:#cdd3da;--bg:#24262b;--card:#2c2f35;--line:#3c4048;--dim:#8f97a3;--acc:#f0932f;
  --gbg:#3a3f47;--gfg:#a8b0ba;--track:#4a4f58;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;color:var(--fg);background:var(--bg);
  font-family:"Segoe UI",system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
main{max-width:860px;margin:0 auto;padding:28px 20px 70px}
h1{font-size:20px;margin:0 0 4px}
.sub{color:var(--dim);font-size:13px;margin-bottom:14px}
.sub a{color:var(--acc);text-decoration:none}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px;align-items:center}
.toolbar button{border:1px solid var(--line);background:var(--card);border-radius:8px;
  padding:5px 12px;font-size:13px;cursor:pointer;color:var(--fg)}
.toolbar button:hover{border-color:var(--acc);color:var(--acc)}
.toolbar button.on{border-color:var(--acc);color:var(--acc)}
.toolbar input{border:1px solid var(--line);background:var(--card);border-radius:8px;
  padding:5px 12px;font-size:13px;color:var(--fg);width:170px}
.toolbar input:focus{outline:1px solid var(--acc)}
#sum{color:var(--dim);font-size:12px;margin:2px 0 10px}
#defbox{border:1px solid var(--line);border-radius:8px;background:var(--card);
  padding:10px 14px;font-size:14px;line-height:1.7;color:var(--defg,#3d4b5c);margin-bottom:12px}
#defbox:empty{display:none}
:root.dark #defbox{color:var(--fg)}
.switch{position:fixed;top:16px;right:18px;z-index:9;cursor:pointer;line-height:0}
.switch input{position:absolute;opacity:0;width:0;height:0}
.switch .track{display:inline-block;width:42px;height:24px;border-radius:999px;
  background:var(--track);position:relative;transition:background .2s}
.switch .track::after{content:"";position:absolute;top:3px;left:3px;width:18px;height:18px;
  border-radius:50%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.25);transition:left .2s}
.switch input:checked + .track{background:var(--acc)}
.switch input:checked + .track::after{left:21px}
.switch input:focus-visible + .track{outline:2px solid var(--acc);outline-offset:2px}
table{width:100%;border-collapse:collapse;font-size:14px;background:var(--card);
  border:1px solid var(--line);border-radius:10px;overflow:hidden}
th{color:var(--dim);font-size:12px;font-weight:600;text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}
td{padding:7px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
tr:last-child td{border-bottom:0}
tbody tr{cursor:pointer}
tbody tr:hover{background:var(--bg)}
tbody tr.kn td{opacity:.45}
tbody tr.kn td b{text-decoration:line-through}
td b{font-weight:600}
td .zh{color:var(--dim);font-size:12.5px;overflow:hidden;text-overflow:ellipsis;max-width:330px;display:block;white-space:nowrap}
td a{color:var(--acc);text-decoration:none}
.tagchip{border:1px solid var(--line);border-radius:4px;font-size:10px;color:var(--gfg);
  padding:0 4px;margin-right:2px}
td.n{font-variant-numeric:tabular-nums;color:var(--dim)}
td.n b2{color:var(--fg);font-weight:600}
footer{margin-top:26px;color:var(--dim);font-size:12px;text-align:center}
.footlinks a{color:var(--dim);text-decoration:none;text-transform:uppercase;letter-spacing:.12em}
.footlinks a:hover{color:var(--acc)}
.footlinks span{opacity:.5;margin:0 8px}
</style>
</head>
<body>
<main>
<label class="switch" title="深色 / 浅色模式">
  <input type="checkbox" id="chk-dark" aria-label="深色模式">
  <span class="track"></span>
</label>
<h1>总词表统计</h1>
<div class="sub">A statement a day keeps the WA away · 口径：每日生词表按出现天数聚合，一天出现十次只计一天 · <a href="index.html">← 目录</a></div>
<div class="toolbar">
  <input id="q" type="search" placeholder="搜索单词…">
  <button data-k="days" class="on">按天数</button>
  <button data-k="total">按总次数</button>
  <button data-k="zipf">按 Zipf</button>
  <button id="btn-hk" class="on">隐藏已认识：开</button>
</div>
<div id="sum"></div>
<div id="defbox"></div>
<table>
<thead><tr><th>词</th><th>天数</th><th>总次数</th><th>Zipf</th><th>标签</th><th>释义（ECDICT）</th><th>最近出现</th></tr></thead>
<tbody id="tb"></tbody>
</table>
<footer>
<nav class="footlinks">
<a href="https://github.com/Lucky-Xiaoxin" target="_blank" rel="noopener">GitHub</a><span>/</span><a href="mailto:yggdya@163.com">Email</a><span>/</span><a href="https://lucky-xiaoxin.github.io/xin-s-blog/" target="_blank" rel="noopener">Blog</a>
</nav>
<div style="margin-top:6px">由 scripts/build_stats.py 生成于 __GEN__</div>
</footer>
</main>
<script>
const ROWS = __ROWS__;
const DAYS = __DAYS__;
const $ = s => document.querySelector(s);
const LS = {
  get(k, d) { try { return JSON.parse(localStorage.getItem('eqp1.' + k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem('eqp1.' + k, JSON.stringify(v)); } catch {} }
};
let known = new Set(LS.get('known', []));
let hideKnown = LS.get('stathide', true);
let sortKey = LS.get('statsort', 'days');
let q = '';

const CMP = {
  days: (a, b) => b.days - a.days || b.total - a.total || a.zipf - b.zipf,
  total: (a, b) => b.total - a.total || b.days - a.days || a.zipf - b.zipf,
  zipf: (a, b) => a.zipf - b.zipf || b.days - a.days,
};

function render() {
  const tbody = $('#tb');
  tbody.innerHTML = '';
  const list = ROWS
    .filter(e => !q || e.word.includes(q))
    .filter(e => !hideKnown || !known.has(e.word))
    .sort(CMP[sortKey]);
  for (const e of list) {
    const tr = document.createElement('tr');
    if (known.has(e.word)) tr.className = 'kn';
    tr.innerHTML =
      '<td><b>' + e.word + '</b>' + (e.bf ? ' <u style="color:var(--dim);font-size:10px">补</u>' : '') + '</td>' +
      '<td class="n"><b2>' + e.days + '</b2></td>' +
      '<td class="n">' + e.total + '</td>' +
      '<td class="n">' + e.zipf.toFixed(2) + '</td>' +
      '<td>' + (e.tags || '').split(' ').filter(Boolean).slice(0, 2).map(t => '<span class="tagchip">' + t.toUpperCase() + '</span>').join('') + '</td>' +
      '<td><span class="zh" title="' + (e.trans || '').replace(/"/g, '&quot;') + '">' + (e.trans || '—') + '</span></td>' +
      '<td><a href="' + e.last_dir + '/page.html">' + e.last_date + '</a></td>';
    tr.onclick = () => {
      const box = $('#defbox');
      const tags = (e.tags || '').split(' ').filter(Boolean).slice(0, 3)
        .map(t => '<span class="tagchip">' + t.toUpperCase() + '</span>').join('');
      box.innerHTML = '<b>' + e.word + '</b> <i style="color:var(--dim)">' + (e.phon || '') + '</i> ' + tags +
        ' — 出现 ' + e.days + ' 天 / 共 ' + e.total + ' 次<br>' + (e.trans || 'ECDICT 子集里没有这个词的释义') +
        ' <a href="' + e.last_dir + '/page.html">→ 最近出现：' + e.last_date + '</a>';
    };
    tbody.appendChild(tr);
  }
  const kn = ROWS.filter(e => known.has(e.word)).length;
  $('#sum').textContent = '共 ' + ROWS.length + ' 词 · 覆盖 ' + DAYS + ' 天 · 已标记认识 ' + kn + ' 词' +
    (hideKnown ? '（已隐藏）' : '');
  document.querySelectorAll('.toolbar button[data-k]').forEach(b =>
    b.classList.toggle('on', b.dataset.k === sortKey));
  $('#btn-hk').textContent = '隐藏已认识：' + (hideKnown ? '开' : '关');
}

document.querySelectorAll('.toolbar button[data-k]').forEach(b =>
  b.onclick = () => { sortKey = b.dataset.k; LS.set('statsort', sortKey); render(); });
$('#btn-hk').onclick = () => { hideKnown = !hideKnown; LS.set('stathide', hideKnown); render(); };
$('#q').oninput = e => { q = e.target.value.trim().toLowerCase(); render(); };

let dark = LS.get('dark', null);
if (dark === null) dark = !!(window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches);
function applyTheme() {
  document.documentElement.classList.toggle('dark', dark);
  $('#chk-dark').checked = dark;
}
$('#chk-dark').onchange = e => { dark = e.target.checked; LS.set('dark', dark); applyTheme(); };
applyTheme();

render();
</script>
<footer></footer>
</body>
</html>
"""


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    agg: dict = {}
    days = 0
    for d in sorted(BASE.iterdir()):
        m, wf = d / "meta.json", d / "words.json"
        if not d.is_dir() or not m.exists() or not wf.exists():
            continue
        try:
            meta = json.loads(m.read_text(encoding="utf-8"))
            words = json.loads(wf.read_text(encoding="utf-8"))
        except Exception:
            continue
        date = meta.get("date", d.name[:10])
        days += 1
        for w in words:
            e = agg.setdefault(w["word"], {
                "word": w["word"], "days": 0, "total": 0,
                "zipf": 9.9, "bf": False, "phon": "", "trans": "", "tags": "",
                "last_dir": d.name, "last_date": date,
            })
            e["days"] += 1
            e["total"] += w.get("count", 1)
            e["zipf"] = min(e["zipf"], w.get("zipf", 9.9))
            e["bf"] = e["bf"] or bool(w.get("bf"))
            e["phon"] = e["phon"] or w.get("phon", "")
            e["trans"] = e["trans"] or w.get("trans", "")
            e["tags"] = e["tags"] or w.get("tags", "")
            if d.name >= e["last_dir"]:
                e["last_dir"], e["last_date"] = d.name, date

    rows = sorted(agg.values(), key=lambda e: (-e["days"], -e["total"], e["zipf"]))
    html = (TEMPLATE
            .replace("__ROWS__", json.dumps(rows, ensure_ascii=False))
            .replace("__DAYS__", str(days))
            .replace("__GEN__", time.strftime("%Y-%m-%d %H:%M")))
    OUT.write_text(html, encoding="utf-8")
    print(f"[ok] stats：{len(rows)} 词 / {days} 天 → {OUT}")


if __name__ == "__main__":
    main()
