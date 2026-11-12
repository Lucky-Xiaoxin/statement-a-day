#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
fetch_daily.py — 每日一题英文题面阅读工具（MVP v0.2）

流程：Codeforces API 选一道 rating ∈ [--min-rating, --max-rating] 的题（排除已 solve、
以前出过的）→ 抓题面 HTML → 清洗（去 header/样例、$$$ LaTeX 转 \( \)、图片绝对化）
→ wordfreq 频率过滤出生词表（不足 --min-words 用阈值外罕词补足）→ ECDICT 子集
补充中文释义/音标 → 生成自包含 page.html（点词标"我认识"，内文淡黄高亮，
已知词存浏览器 localStorage，队友各自独立）。

用法：
    python scripts/fetch_daily.py                    # 今天的题（当天重跑幂等）
    python scripts/fetch_daily.py --date 2026-11-01  # 补卡某天
    python scripts/fetch_daily.py --handle xxx       # 排除已 solve 的题
    python scripts/fetch_daily.py --zipf 3.0         # 放宽词频阈值（生词更多）
    python scripts/fetch_daily.py --min-words 0      # 关闭保底补充

依赖：Python 3.10+ 与 wordfreq（pip install wordfreq），其余全部标准库。
首次使用先跑 scripts/build_dict.py 构建离线释义子集（data/ecdict-subset.json）。
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import tempfile
import urllib.parse
import urllib.request
import urllib.error
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "problems"
DICT_PATH = ROOT / "data" / "ecdict-subset.json"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) eqp-study-tool/0.2",
    "Accept-Encoding": "identity",
}

# 章节骨架词，不属于题面内容
STOP = {
    "input", "output", "examples", "example", "note", "statement", "problem",
    "time", "memory", "limit", "standard",
}


# ---------------------------------------------------------------- HTTP ----

def http_get(url: str, *, as_json: bool = False, retries: int = 3, timeout: int = 30):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            return json.loads(data.decode("utf-8")) if as_json else data
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (403, 503) and i < retries - 1:
                time.sleep(2 * (i + 1))
                continue
            raise RuntimeError(f"HTTP {e.code}：{url}（Codeforces 可能在防爬，稍后重试）") from e
        except Exception as e:  # 网络抖动重试
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"请求失败：{url}（{last}）")


def get_problemset() -> dict:
    """全题库列表，本地缓存 6 小时，避免每次都拉 2MB+。"""
    cache = Path(tempfile.gettempdir()) / "eqp_problemset.json"
    if cache.exists() and time.time() - cache.stat().st_mtime < 6 * 3600:
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except Exception:
            pass
    data = http_get("https://codeforces.com/api/problemset.problems", as_json=True)
    if data.get("status") != "OK":
        raise RuntimeError("problemset.problems 返回异常")
    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def get_solved(handle: str) -> set:
    """已 solve 的 (contestId, index) 集合；失败则降级为空集。"""
    url = ("https://codeforces.com/api/user.status?handle="
           + urllib.parse.quote(handle) + "&from=1&count=100000")
    try:
        data = http_get(url, as_json=True)
        if data.get("status") != "OK":
            return set()
        return {
            (s["problem"]["contestId"], s["problem"]["index"])
            for s in data.get("result", [])
            if s.get("verdict") == "OK" and "contestId" in s.get("problem", {})
        }
    except Exception as e:
        print(f"[warn] 拉取做题记录失败，忽略：{e}")
        return set()


# ---------------------------------------------------------------- 选题 ----

def pick_problem(lo: int, hi: int, solved: set, date_key: str, used: set) -> dict:
    ps = get_problemset().get("result", {}).get("problems", [])
    cands = [
        p for p in ps
        if p.get("rating") and lo <= p["rating"] <= hi
        and (p["contestId"], p["index"]) not in solved
        and (p["contestId"], p["index"]) not in used
    ]
    if not cands:
        raise RuntimeError("候选池为空：放宽 rating 区间或调整排除条件")
    # 种子 = 日期 + 区间：同一台机器当天重跑结果一致（幂等）
    return random.Random(f"{date_key}|{lo}-{hi}").choice(cands)


# ---------------------------------------------------------------- 清洗 ----

DIV_TOKEN = re.compile(r"<div\b[^>]*>|</div\s*>", re.I)


def find_div_block(html: str, class_name: str):
    """返回平衡匹配的 <div class="...class_name...">...</div> 的 (start, end)。"""
    for m in re.finditer(r"<div\b[^>]*>", html):
        cm = re.search(r'class="([^"]*)"', m.group(0))
        if not cm or class_name not in cm.group(1).split():
            continue
        depth = 1
        for t in DIV_TOKEN.finditer(html, m.end()):
            if t.group(0).startswith("</"):
                depth -= 1
                if depth == 0:
                    return m.start(), t.end()
            else:
                depth += 1
        return m.start(), len(html)
    return None


def remove_div_block(html: str, class_name: str) -> str:
    span = find_div_block(html, class_name)
    return html[: span[0]] + html[span[1]:] if span else html


def clean_statement(raw: str) -> tuple[str, str, str]:
    """返回 (题目标题, 展示用 body_html, 取词用 plain_text)。"""
    span = find_div_block(raw, "problem-statement")
    if not span:
        raise RuntimeError("页面里没找到题面：可能被反爬页挡住，或页面结构变化")
    doc = raw[span[0]: span[1]]

    title = ""
    tspan = find_div_block(doc, "title")
    if tspan:
        title = unescape(re.sub(r"<[^>]+>", " ", doc[tspan[0]: tspan[1]])).strip()

    doc = remove_div_block(doc, "header")        # 时间/内存限制等固定 chrome
    doc = remove_div_block(doc, "sample-tests")  # 样例（不参与取词）
    doc = re.sub(r"<script\b.*?</script>", " ", doc, flags=re.S | re.I)
    doc = re.sub(r"<style\b.*?</style>", " ", doc, flags=re.S | re.I)
    doc = re.sub(r"\son\w+=\"[^\"]*\"", "", doc, flags=re.I)

    # Codeforces 行内公式约定：$$$...$$$ → \( ... \)；展示块 $$$$...$$$$ → \[ ... \]
    doc = re.sub(r"\$\$\$\$(.+?)\$\$\$\$", r"\\[\1\\]", doc, flags=re.S)
    doc = re.sub(r"\$\$\$(.+?)\$\$\$", r"\\(\1\\)", doc, flags=re.S)

    def abs_img(m: re.Match) -> str:
        src = m.group(1)
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = "https://codeforces.com" + src
        return m.group(0).replace(m.group(1), src)

    doc = re.sub(r"<img[^>]*\ssrc=\"([^\"]+)\"", abs_img, doc)
    body_html = doc

    text = re.sub(r"\\\[.*?\\\]", " ", body_html, flags=re.S)  # 公式段不参与取词
    text = re.sub(r"\\\(.*?\\\)", " ", text, flags=re.S)
    text = re.sub(r"<pre\b.*?</pre>", " ", text, flags=re.S | re.I)
    text = unescape(re.sub(r"<[^>]+>", " ", text))
    return title, body_html, text


# ---------------------------------------------------------------- 取词 ----

def merge_plurals(entries: list) -> list:
    """permutation / permutations 这类单复数对合并成一条（保留单数形式）。"""
    by_w = {d["word"]: dict(d) for d in entries}
    for d in entries:
        w = d["word"]
        if w.endswith("s") and w[:-1] in by_w:
            s = by_w[w[:-1]]
            s["count"] += d["count"]
            s["zipf"] = min(s["zipf"], d["zipf"])
            del by_w[w]
    return sorted(by_w.values(), key=lambda d: (d["zipf"], -d["count"]))


def extract_words(text: str, min_zipf: float, min_words: int = 5, cap: int = 60) -> list:
    from wordfreq import zipf_frequency

    # 缩写展开，避免 doesn't 被拆成碎片
    text = re.sub(r"(?i)n't\b", " not", text)
    text = re.sub(r"(?i)'(re|ve|ll|m|d)\b", r" \1", text)

    toks_lower = re.findall(r"[A-Za-z]+", text.lower())
    toks_raw = set(re.findall(r"[A-Za-z]+", text))
    freq: dict = {}
    for w in toks_lower:
        if len(w) < 2 or w in STOP:
            continue
        freq[w] = freq.get(w, 0) + 1

    cand = []
    for w, c in freq.items():
        # 只以大写形式出现的词大概率是人名（Alice/Bob/Bessie），跳过
        if w not in toks_raw and w.capitalize() in toks_raw:
            continue
        z = zipf_frequency(w, "en") or zipf_frequency(w.rstrip("s"), "en") or 0.0
        cand.append({"word": w, "zipf": round(z, 2), "count": c})
    cand = merge_plurals(cand)
    cand.sort(key=lambda d: (d["zipf"], -d["count"]))

    main = [d for d in cand if d["zipf"] < min_zipf][:cap]
    picked = {d["word"] for d in main}
    if min_words > 0:
        for d in cand:  # 保底：不足 min_words 用阈值外最罕的词补足
            if len(main) >= min_words:
                break
            if d["word"] in picked:
                continue
            main.append(dict(d, bf=1))
            picked.add(d["word"])
    return main


# ---------------------------------------------------------------- 释义 ----

def load_dict() -> dict:
    if not DICT_PATH.exists():
        print("[warn] 未找到 data/ecdict-subset.json：先跑一次 scripts/build_dict.py，页面将没有释义")
        return {"w": {}}
    try:
        return json.loads(DICT_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[warn] 释义子集解析失败，忽略：{e}")
        return {"w": {}}


def enrich_words(words: list, d: dict) -> list:
    wm = d.get("w", {})
    for x in words:
        e = wm.get(x["word"])
        if not e:
            continue
        base = wm.get(e.get("0", ""), e)  # 本词条没释义时回退到原形
        if base.get("p"):
            x["phon"] = base["p"]
        if base.get("t"):
            x["trans"] = base["t"]
        if base.get("g"):
            x["tags"] = base["g"]
    return words


# ---------------------------------------------------------------- 高亮 ----

def highlight_words(html: str, words: list) -> str:
    """题面内文给生词加淡黄底；跳过标签/公式/代码段；保底补充的常见词不高亮。"""
    ws = sorted({d["word"] for d in words if not d.get("bf")}, key=len, reverse=True)
    if not ws:
        return html
    pat = re.compile(r"\b(" + "|".join(re.escape(w) for w in ws) + r")(?:'s|es|s)?\b", re.I)

    def wrap_text(seg: str) -> str:
        out = []
        for piece in re.split(r"(&[A-Za-z]+;|&#\d+;)", seg):
            if piece.startswith("&") and piece.endswith(";"):
                out.append(piece)  # 不碰 HTML 实体
            else:
                out.append(pat.sub(
                    lambda m: '<mark class="vw" data-w="' + m.group(1).lower() + '">'
                              + m.group(0) + "</mark>",
                    piece))
        return "".join(out)

    parts = re.split(
        r"(<[^>]+>|\\\[.*?\\\]|\\\(.*?\\\)|<pre\b.*?</pre>|<code\b.*?</code>)",
        html, flags=re.S | re.I)
    return "".join(
        p if p.startswith("<") or p.startswith("\\") else wrap_text(p)
        for p in parts)


# ---------------------------------------------------------------- 译文 ----

# 非官方 Google 翻译接口：无 key、无注册；国内本地不可达（预期），CI 构建机（境外）可用。
GOOGLE_TURL = ("https://translate.googleapis.com/translate_a/single"
               "?client=gtx&sl=en&tl=zh-CN&dt=t&q=")

BLOCK_RE = re.compile(r"<(p|li)\b[^>]*>(.*?)</\1>", re.S | re.I)

# 简单 LaTeX → Unicode 文本（喂给翻译接口，让译文里出现 x₁、10⁵、≤ 而不是 [式]）
SUP_TAB = str.maketrans("0123456789+-=ni()", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼ⁿⁱ⁽⁾")
SUB_TAB = str.maketrans("0123456789+-=aeikmnoprstuvxh()", "₀₁₂₃₄₅₆₇₈₉₊₋₌ₐₑᵢₖₘₙₒₚᵣₛₜᵤᵥₓₕ₍₎")
_TEX_WORDS = [
    (r"\ldots", "…"), (r"\dots", "…"), (r"\times", "×"), (r"\cdot", "·"),
    (r"\leq", "≤"), (r"\le", "≤"), (r"\geq", "≥"), (r"\ge", "≥"),
    (r"\neq", "≠"), (r"\ne", "≠"), (r"\pm", "±"), (r"\div", "÷"),
    (r"\infty", "∞"), (r"\rightarrow", "→"), (r"\to", "→"), (r"\sum", "Σ"),
    (r"\bmod", " mod "), (r"\mod", " mod "), (r"\left", ""), (r"\right", ""),
    (r"\%", "%"), (r"\$", "$"), (r"\,", " "), (r"\;", " "), (r"\!", ""),
]


def tex_to_text(s: str) -> str | None:
    """简单行内 LaTeX → 可读 Unicode 文本；含复杂结构（残余 \\ 或 {}）时返回 None。"""
    s = s.strip()
    for cmd, txt in sorted(_TEX_WORDS, key=lambda kv: -len(kv[0])):  # 长命令优先，防 \left 被 \le 截胡
        s = s.replace(cmd, txt)
    s = re.sub(r"\^\{([^{}]*)\}|\^([A-Za-z0-9])",
               lambda m: (m.group(1) or m.group(2)).translate(SUP_TAB), s)
    s = re.sub(r"_\{([^{}]*)\}|_([A-Za-z0-9])",
               lambda m: (m.group(1) or m.group(2)).translate(SUB_TAB), s)
    if "\\" in s or "{" in s or "}" in s:
        return None  # \frac 之类的复杂结构，转不动 → [式]
    return s.strip() or None


def google_translate(text: str) -> str | None:
    try:
        url = GOOGLE_TURL + urllib.parse.quote(text)
        data = json.loads(http_get(url, retries=1, timeout=12).decode("utf-8", "replace"))
        return "".join(seg[0] for seg in data[0] if seg and seg[0]) or None
    except Exception:
        return None


def translate_blocks(body_html: str, pre_zh: list | None = None) -> tuple[str, list]:
    """给 <p>/<li> 块注入 data-ti 并逐段机翻，返回 (新 html, [zh 或 None, ...])。
    pre_zh 非空时直接复用已有译文（trans.json），不再调接口。
    整体失败时返回原文 + []（页面自动隐藏译文按钮）。"""
    blocks: list = []

    def tag_block(m: re.Match) -> str:
        tag, inner = m.group(1), m.group(2)

        def math_txt(mm: re.Match) -> str:
            return " " + (tex_to_text(mm.group(1) or mm.group(2)) or "[式]") + " "

        text = re.sub(r"\\\((.*?)\\\)|\\\[(.*?)\\\]", math_txt, inner, flags=re.S)
        text = unescape(re.sub(r"<[^>]+>", " ", text))
        text = re.sub(r"\s+", " ", text).strip()
        i = len(blocks)
        blocks.append(text)
        return m.group(0).replace("<" + tag, f'<{tag} data-ti="{i}"', 1)

    html = BLOCK_RE.sub(tag_block, body_html)
    if pre_zh is not None and len(pre_zh) == len(blocks):
        return html, list(pre_zh)
    todo = [i for i, t in enumerate(blocks) if 3 <= len(t) <= 3500 and re.search(r"[A-Za-z]", t)]
    zh: list = [None] * len(blocks)
    ok = 0
    for attempt in (1, 2):  # 第二轮兜底：接口限流时歇 25 秒再试失败段
        for i in todo:
            if not zh[i]:
                zh[i] = google_translate(blocks[i])
                time.sleep(0.4)  # 对非官方接口客气点
        ok = sum(1 for i in todo if zh[i])
        print(f"[i] 译文第 {attempt} 轮：{ok}/{len(todo)} 段")
        if ok == len(todo) or attempt == 2:
            break
        time.sleep(25)
    if ok == 0:
        return body_html, []
    return html, zh


# ---------------------------------------------------------------- 页面 ----

PAGE_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__DATE__ · __TITLE__</title>
<script>
try { var _d = JSON.parse(localStorage.getItem('eqp1.dark')); if (_d === true || (_d === null && window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches)) document.documentElement.classList.add('dark'); } catch (e) {}
</script>
<script>
window.MathJax = { tex: { inlineMath: [['\\(','\\)']], displayMath: [['\\[','\\]']] }, svg: { fontCache: 'global' } };
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
<style>
:root{--fg:#1c2733;--bg:#f6f7f9;--card:#fff;--line:#dde3ea;--dim:#8a94a0;--acc:#e8720c;
  --gbg:#e4e8ee;--gfg:#5a6472;--defg:#3d4b5c;--prebg:#eef1f5;
  --markbg:#fdf3d8;--markdimbg:#f1f2f4;--markdimfg:#a8b0ba;--track:#c9cfd8;color-scheme:light}
:root.dark{--fg:#cdd3da;--bg:#24262b;--card:#2c2f35;--line:#3c4048;--dim:#8f97a3;--acc:#f0932f;
  --gbg:#3a3f47;--gfg:#a8b0ba;--defg:#b9c0c9;--prebg:#212327;
  --markbg:#443d22;--markdimbg:#2f3136;--markdimfg:#67707c;--track:#4a4f58;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;color:var(--fg);background:var(--bg);
  font-family:"Segoe UI",system-ui,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
main{max-width:880px;margin:0 auto;padding:20px 20px 70px}
.meta{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:6px;color:var(--dim);font-size:14px}
.badge{background:var(--acc);color:#fff;border-radius:6px;padding:1px 8px;font-weight:600}
.badge.gray{background:var(--gbg);color:var(--gfg)}
h1{font-size:22px;margin:2px 0 4px}
h1 a{color:inherit;text-decoration:none;border-bottom:1px dotted var(--line)}
h2{font-size:17px;margin:34px 0 10px}
.hint{color:var(--dim);font-size:13px;margin:2px 0 10px}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px}
.toolbar button{border:1px solid var(--line);background:var(--card);border-radius:8px;
  padding:5px 12px;font-size:13px;cursor:pointer;color:var(--fg)}
.toolbar button:hover{border-color:var(--acc);color:var(--acc)}
.switch{position:fixed;top:16px;right:18px;z-index:9;cursor:pointer;line-height:0}
.switch input{position:absolute;opacity:0;width:0;height:0}
.switch .track{display:inline-block;width:42px;height:24px;border-radius:999px;
  background:var(--track);position:relative;transition:background .2s}
.switch .track::after{content:"";position:absolute;top:3px;left:3px;width:18px;height:18px;
  border-radius:50%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.25);transition:left .2s}
.switch input:checked + .track{background:var(--acc)}
.switch input:checked + .track::after{left:21px}
.switch input:focus-visible + .track{outline:2px solid var(--acc);outline-offset:2px}
#words{display:flex;flex-wrap:wrap;gap:8px}
.chip{border:1px solid var(--line);background:var(--card);border-radius:999px;
  padding:4px 8px 4px 12px;font-size:14px;cursor:pointer;user-select:none;
  display:inline-flex;align-items:center;gap:6px}
.chip b{font-weight:600}
.chip i{color:var(--dim);font-style:normal;font-size:11px}
.chip u{text-decoration:none;color:var(--dim);font-size:11px}
.chip .mini{border:0;background:none;cursor:pointer;color:var(--dim);font-size:12px;padding:0 2px}
.chip .mini:hover{color:var(--acc)}
.chip .mini.okb{color:var(--gfg)}
.chip.known{opacity:.55}
.chip.known b{text-decoration:line-through}
.chip.known .mini.okb{color:var(--acc)}
#defbox{margin-top:12px;border:1px solid var(--line);border-radius:8px;background:var(--card);
  padding:10px 14px;font-size:14px;line-height:1.7;min-height:20px;color:var(--defg)}
#defbox:empty{display:none}
.tagchip{border:1px solid var(--line);border-radius:4px;font-size:10px;color:var(--gfg);
  padding:0 4px;margin:0 2px;white-space:nowrap}
.statement{background:var(--card);border:1px solid var(--line);border-radius:10px;
  padding:6px 28px 16px;line-height:1.7;font-size:16px;overflow-wrap:break-word}
.statement p{margin:.7em 0}
.statement ul,.statement ol{margin:.5em 0;padding-left:1.6em}
.statement pre{background:var(--prebg);padding:10px 12px;border-radius:6px;overflow:auto;font-size:14px}
.statement img{max-width:100%}
:root.dark .statement img{background:#fff;border-radius:4px}
.statement .section-title{font-weight:700;margin:18px 0 2px;font-size:16.5px}
mark.vw{background:var(--markbg);color:inherit;padding:0 1px;border-radius:3px}
mark.vw.dim{background:var(--markdimbg);color:var(--markdimfg)}
.zh{color:var(--dim);font-size:14.5px;line-height:1.7;border-left:2px solid var(--acc);
  padding:2px 0 2px 10px;margin:4px 0 10px}
body:not(.showtrans) .zh{display:none}
li .zh{display:block;margin:2px 0 6px}
body.nohl mark.vw{background:transparent;color:inherit}
footer{margin-top:36px;color:var(--dim);font-size:12px;text-align:center}
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
  <div class="meta">
    <span class="badge gray">__DATE__</span>
    <span class="badge">rating __RATING__</span>
    <span>cf__CONTEST____INDEX__</span>
    <span>__TAGS__</span>
    <a href="__URL__" target="_blank">在 Codeforces 打开 ↗</a>
  </div>
  <h1>__TITLE__</h1>

  <h2>今日生词 <span style="font-size:12px;color:var(--dim)">（按词频：越靠前越罕见）</span></h2>
  <div class="hint">点词 = 看中文释义 · <b>✓</b> = 标记已认识（跨页记忆，存本浏览器） · 「补」= 阈值外保底词</div>
  <div class="toolbar">
    <button id="btn-trans" style="display:none">译文：关</button>
    <button id="btn-hl">高亮：开</button>
  </div>
  <div id="words"></div>
  <div id="defbox"></div>

  <h2>题面</h2>
  <div class="statement" lang="en">__BODY__</div>

  <footer>
    <nav class="footlinks">
      <a href="https://github.com/Lucky-Xiaoxin" target="_blank" rel="noopener">GitHub</a><span>/</span><a href="mailto:yggdya@163.com">Email</a><span>/</span><a href="https://lucky-xiaoxin.github.io/xin-s-blog/" target="_blank" rel="noopener">Blog</a>
    </nav>
    <div style="margin-top:6px">由 scripts/fetch_daily.py 生成于 __GENERATED__ · 公式由 MathJax 渲染（需联网）</div>
  </footer>
</main>
<script>
const WORDS = __WORDS__;
const TRANS = __TRANS__;
const $ = s => document.querySelector(s);
const LS = {
  get(k, d) { try { return JSON.parse(localStorage.getItem('eqp1.' + k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem('eqp1.' + k, JSON.stringify(v)); } catch {} }
};
let known = new Set(LS.get('known', []));
let hl = LS.get('hl', true);
let dark = LS.get('dark', null);
if (dark === null) dark = !!(window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches);

const info = w => WORDS.find(x => x.word === w) || {};

function render() {
  const box = $('#words');
  box.innerHTML = '';
  const sorted = [...WORDS].sort((a, b) =>
    (known.has(a.word) - known.has(b.word)) || ((a.bf ? 1 : 0) - (b.bf ? 1 : 0)) || a.zipf - b.zipf);
  for (const item of sorted) {
    const w = item.word;
    const chip = document.createElement('span');
    chip.className = 'chip' + (known.has(w) ? ' known' : '');
    chip.title = 'Zipf ' + item.zipf + (item.bf ? ' · 阈值外补充' : '')
      + (item.trans ? '\n' + item.trans : '');

    const b = document.createElement('b'); b.textContent = w; chip.appendChild(b);
    const z = document.createElement('i'); z.textContent = item.zipf; chip.appendChild(z);
    if (item.count > 1) { const c = document.createElement('u'); c.textContent = '×' + item.count; chip.appendChild(c); }
    if (item.bf) { const f = document.createElement('u'); f.textContent = '补'; chip.appendChild(f); }

    const okb = document.createElement('button'); okb.className = 'mini okb'; okb.textContent = '✓';
    okb.title = known.has(w) ? '已认识（点击取消）' : '标记已认识（跨页记忆）';
    okb.onclick = e => { e.stopPropagation(); known.has(w) ? known.delete(w) : known.add(w); LS.set('known', [...known]); render(); updateMarks(); };
    chip.appendChild(okb);

    chip.onclick = () => lookup(w);
    box.appendChild(chip);
  }
}

function lookup(w) {
  const box = $('#defbox');
  const d = info(w);
  const tags = (d.tags || '').split(' ').filter(Boolean).slice(0, 3)
    .map(t => '<span class="tagchip">' + t.toUpperCase() + '</span>').join('');
  if (!d.trans && !d.phon) {
    box.innerHTML = '<b>' + w + '</b> ' + tags + ' — ECDICT 子集里没有这个词的释义';
    return;
  }
  box.innerHTML = '<b>' + w + '</b> <i style="color:var(--dim)">' + (d.phon || '') + '</i> ' + tags + '<br>'
    + (d.trans || '').split('\n').join('<br>');
}

function updateMarks() {
  document.querySelectorAll('mark.vw').forEach(m =>
    m.classList.toggle('dim', known.has(m.dataset.w)));
}

$('#btn-hl').onclick = () => { hl = !hl; LS.set('hl', hl); applyHl(); };
function applyHl() {
  document.body.classList.toggle('nohl', !hl);
  $('#btn-hl').textContent = hl ? '高亮：开' : '高亮：关';
}
$('#chk-dark').onchange = e => { dark = e.target.checked; LS.set('dark', dark); applyTheme(); };
function applyTheme() {
  document.documentElement.classList.toggle('dark', dark);
  $('#chk-dark').checked = dark;
}

let transOn = LS.get('trans', false);
function applyTrans() {
  document.body.classList.toggle('showtrans', transOn);
  $('#btn-trans').textContent = transOn ? '译文：开' : '译文：关';
}
if (TRANS.some(t => t)) {
  $('#btn-trans').style.display = '';
  document.querySelectorAll('[data-ti]').forEach(el => {
    const zh = TRANS[+el.dataset.ti];
    if (!zh) return;
    const n = document.createElement(el.tagName === 'LI' ? 'span' : 'div');
    n.className = 'zh';
    n.textContent = zh;
    if (el.tagName === 'LI') el.appendChild(n); else el.after(n);
  });
  $('#btn-trans').onclick = () => { transOn = !transOn; LS.set('trans', transOn); applyTrans(); };
  applyTrans();
}

render();
applyHl();
applyTheme();
updateMarks();
</script>
</body>
</html>
"""


def render_page(meta: dict, title: str, body_html: str, words: list, trans: list | None = None) -> str:
    html = PAGE_TEMPLATE
    repl = {
        "__DATE__": meta["date"],
        "__TITLE__": title or meta["name"],
        "__RATING__": str(meta["rating"]),
        "__CONTEST__": str(meta["contestId"]),
        "__INDEX__": meta["index"],
        "__TAGS__": " ".join("#" + t for t in meta.get("tags", [])[:6]),
        "__URL__": meta["url"],
        "__BODY__": body_html,
        "__WORDS__": json.dumps(words, ensure_ascii=False),
        "__TRANS__": json.dumps(trans or [], ensure_ascii=False),
        "__GENERATED__": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    for k, v in repl.items():
        html = html.replace(k, v)
    return html


# ---------------------------------------------------------------- main ----

def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="每日一题英文题面阅读工具（MVP）")
    ap.add_argument("--date", help="YYYY-MM-DD，默认今天")
    ap.add_argument("--min-rating", type=int, default=1400)
    ap.add_argument("--max-rating", type=int, default=1800)
    ap.add_argument("--handle", help="CF 用户名，排除已 solve 的题")
    ap.add_argument("--zipf", type=float, default=4.0, help="词频阈值，越小生词越多（2026-11-07 起 4.0 试行）")
    ap.add_argument("--min-words", type=int, default=5, help="生词保底数量，0 = 关闭保底补充")
    ap.add_argument("--translate", action="store_true",
                    help="构建时段落级机翻（需境外网络，CI 上用；本地默认关）")
    ap.add_argument("--no-open", action="store_true", help="生成后不自动打开浏览器")
    args = ap.parse_args()

    date_key = args.date or time.strftime("%Y-%m-%d")
    OUT.mkdir(exist_ok=True)

    # 以前出过的题不再重复出现
    used = set()
    for d in OUT.iterdir():
        m = d / "meta.json"
        if m.exists():
            try:
                mj = json.loads(m.read_text(encoding="utf-8"))
                used.add((mj["contestId"], mj["index"]))
            except Exception:
                pass

    day_dir = next((d for d in OUT.iterdir()
                    if d.is_dir() and d.name.startswith(date_key + "_") and (d / "meta.json").exists()), None)

    if day_dir:
        meta = json.loads((day_dir / "meta.json").read_text(encoding="utf-8"))
        print(f"[i] {date_key} 已出过 cf{meta['contestId']}{meta['index']}，复用缓存")
    else:
        solved = get_solved(args.handle) if args.handle else set()
        p = pick_problem(args.min_rating, args.max_rating, solved, date_key, used)
        meta = {
            "date": date_key,
            "contestId": p["contestId"], "index": p["index"],
            "name": p["name"], "rating": p["rating"], "tags": p.get("tags", []),
            "url": f"https://codeforces.com/problemset/problem/{p['contestId']}/{p['index']}",
        }
        day_dir = OUT / f"{date_key}_cf{meta['contestId']}{meta['index']}"
        day_dir.mkdir(parents=True, exist_ok=True)

    stmt_cache = day_dir / "statement.html"
    if stmt_cache.exists():
        raw = stmt_cache.read_text(encoding="utf-8")
        print("[i] 使用已缓存的题面")
    else:
        print(f"[i] 抓取题面：{meta['url']}")
        raw = http_get(meta["url"]).decode("utf-8", "replace")
        stmt_cache.write_text(raw, encoding="utf-8")

    title, body_html, text = clean_statement(raw)
    words = enrich_words(extract_words(text, args.zipf, args.min_words), load_dict())
    body_html = highlight_words(body_html, words)

    trans: list = []
    if args.translate:
        tf = day_dir / "trans.json"
        pre = None
        if tf.exists():  # 同一天重跑：复用已翻译结果，不再打接口
            try:
                pre = json.loads(tf.read_text(encoding="utf-8"))
            except Exception:
                pre = None
        body_html, trans = translate_blocks(body_html, pre_zh=pre)
        if any(trans):
            if pre is None:
                tf.write_text(json.dumps(trans, ensure_ascii=False), encoding="utf-8")
        else:
            print("[warn] 未取到译文：接口当天失败（去 Actions 用 date 参数重跑该天即可修复）或本地无境外网络")

    (day_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (day_dir / "words.json").write_text(json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")
    (day_dir / "page.html").write_text(render_page(meta, title, body_html, words, trans), encoding="utf-8")

    if not words:
        print("[warn] 生词表为空：题面可能没解析到正文，检查 statement.html")
    n_bf = sum(1 for d in words if d.get("bf"))
    print(f"[ok] {len(words)} 个生词（保底补充 {n_bf} 个，{len([d for d in words if d.get('trans')])} 个有释义）→ {day_dir / 'page.html'}")

    if not args.no_open and sys.platform == "win32":
        try:
            os.startfile(day_dir / "page.html")  # noqa: S606
        except Exception:
            pass


if __name__ == "__main__":
    main()
