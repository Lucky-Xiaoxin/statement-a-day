r"""build_dict.py — 一次性构建 ECDICT 离线释义子集（data/ecdict-subset.json）

数据源 ECDICT（github.com/skywind3000/ECDICT，开源免费）：77 万词条，含中文释义、
音标、考试标签（CET4/6/考研/TOEFL/IELTS/GRE…）、exchange 词形变换。

收录规则：
- 0 < Zipf < 4.6 的词（覆盖生词阈值筛选 + 保底补充两个场景；长尾罕词正是要展示的）；
- 或带考试标签 / 柯林斯星级 / BNC·COCA 词频的词（精选常用词，供保底释义）。
- 每词只存第一条例子行中文释义（≤120 字符），控制体积。
- exchange 的 0:原形 存进词条（vertices→vertex），释义查询时回退到原形。

产物 data/ecdict-subset.json 体积约 20-40MB，**不入库**（见 .gitignore）：
本人和队友各构建一次即可，Actions 构建机在 CI 里现算。
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "ecdict-subset.json"
REL_URL = "https://github.com/skywind3000/ECDICT/releases/download/1.0.28/ecdict-stardict-28.zip"
MAX_ZIPF = 4.6


def main() -> None:
    if hasattr(__import__("sys").stdout, "reconfigure"):
        __import__("sys").stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="构建 ECDICT 离线释义子集")
    ap.add_argument("--zip", help="已下载好的 ecdict-stardict zip 路径（默认自动下载）")
    args = ap.parse_args()
    from wordfreq import zipf_frequency

    zp = Path(args.zip) if args.zip else Path(tempfile.gettempdir()) / "ecdict-stardict-28.zip"
    if not zp.exists():
        print(f"[i] 下载 {REL_URL}（约 70MB）…")
        urllib.request.urlretrieve(REL_URL, zp)

    zf = zipfile.ZipFile(zp)
    csv_name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
    print(f"[i] 读取 {csv_name} …")

    w_map: dict = {}
    total = 0
    with zf.open(csv_name) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace"))
        for row in reader:
            total += 1
            w = (row.get("word") or "").strip().lower()
            if not w or not w.isascii() or not w.isalpha():
                continue  # 跳过多词短语、带符号的词条
            tag = (row.get("tag") or "").strip()
            collins = (row.get("collins") or "").strip()
            frq = (row.get("frq") or "").strip()
            bnc = (row.get("bnc") or "").strip()
            z = zipf_frequency(w, "en")
            if z >= MAX_ZIPF and not (tag or collins or frq or bnc):
                continue
            if z <= 0 and not (tag or collins or frq or bnc):
                continue  # 无词频无标签的零散词条，多半是垃圾
            trans = (row.get("translation") or "").strip()
            entry = {}
            if row.get("phonetic", "").strip():
                entry["p"] = row["phonetic"].strip()[:40]
            if trans:
                entry["t"] = trans.split("\n")[0][:120]
            if tag:
                entry["g"] = " ".join(tag.split())
            lemma = ""
            for kv in (row.get("exchange") or "").split("/"):
                if kv.startswith("0:") or kv.startswith("0："):
                    lemma = kv.split(":", 1)[1].strip().lower()
            if lemma and lemma != w:
                entry["0"] = lemma
            if entry:
                w_map[w] = entry
            if total % 200000 == 0:
                print(f"[i] 已扫 {total} 行，收录 {len(w_map)} 词…")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"v": 1, "w": w_map}, ensure_ascii=False), encoding="utf-8")
    print(f"[ok] 扫描 {total} 行，收录 {len(w_map)} 词 → {OUT}（{OUT.stat().st_size / 1e6:.1f} MB）")


if __name__ == "__main__":
    main()
