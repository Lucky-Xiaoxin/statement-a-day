r"""build_dict.py — 一次性构建 ECDICT 离线释义子集（data/ecdict-subset.json）

数据源：ECDICT 1.0.28 的 stardict 包（简明英汉字典增强版，340 万词条，
sametypesequence=m 纯文本格式，词条首行 `*[音标]`，其后为中文释义行）。

收录规则：只保留 Zipf ∈ (0, 4.6) 的单词——低段正是我们要展示的生词长尾，
上限覆盖保底补充的回填词。产物约 20-30MB，不入库（见 .gitignore）：
本人和队友各构建一次即可，Actions 构建机在 CI 里现算。
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "ecdict-subset.json"
REL_URL = "https://github.com/skywind3000/ECDICT/releases/download/1.0.28/ecdict-stardict-28.zip"
MAX_ZIPF = 4.6
DIR = "stardict-ecdict-2.4.2"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="构建 ECDICT 离线释义子集")
    ap.add_argument("--zip", help="已下载好的 ecdict-stardict zip 路径（默认自动下载）")
    args = ap.parse_args()
    from wordfreq import zipf_frequency

    zp = Path(args.zip) if args.zip else Path(tempfile.gettempdir()) / "ecdict-stardict-28.zip"
    if not zp.exists():
        print(f"[i] 下载 {REL_URL}（约 70MB，国内较慢）…")
        urllib.request.urlretrieve(REL_URL, zp)

    zf = zipfile.ZipFile(zp)

    # ---- 第一遍：流式扫 idx（word\0 + offset(4B BE) + size(4B BE)），按词频过滤 ----
    idx = zf.open(f"{DIR}/{DIR}.idx")
    kept = []  # (word_lower, off, size)
    total = 0
    buf = b""
    print("[i] 扫描 idx（340 万词条）…")
    while True:
        chunk = idx.read(1 << 20)
        if not chunk:
            break
        buf += chunk
        pos = 0
        while True:
            z = buf.find(b"\x00", pos)
            if z < 0 or z + 9 > len(buf):
                break
            w = None
            try:
                w = buf[pos:z].decode("utf-8")
                off, size = struct.unpack_from(">II", buf, z + 1)
            except Exception:
                pass
            pos = z + 9
            if not w:
                continue
            total += 1
            wl = w.lower()
            if wl.isascii() and wl.isalpha() and len(wl) > 1:
                zz = zipf_frequency(wl, "en")
                if 0 < zz < MAX_ZIPF:
                    kept.append((wl, off, size))
            if total % 1000000 == 0:
                print(f"[i] idx 已扫 {total} 条，命中 {len(kept)} …")
        buf = buf[pos:]
    print(f"[i] idx 共 {total} 条，按词频筛出 {len(kept)} 条")

    # ---- 第二遍：按 offset 排序后单趟流式读 dict（不用随机 seek）----
    kept.sort(key=lambda r: r[1])
    d = zf.open(f"{DIR}/{DIR}.dict")
    w_map: dict = {}
    cursor = 0
    print("[i] 流式读取 dict …")
    for i, (wl, off, size) in enumerate(kept):
        if off > cursor:
            d.read(off - cursor)
            cursor = off
        raw = d.read(size).decode("utf-8", "replace")
        cursor = off + size
        lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
        if not lines:
            continue
        entry = {}
        if lines[0].startswith("*[") and "]" in lines[0]:
            entry["p"] = lines[0][2:lines[0].index("]")][:40]
            lines = lines[1:]
        senses = [ln for ln in lines if not ln.startswith("[")]  # 跳过 [网络] 等标签行
        if senses:
            entry["t"] = senses[0][:110]  # 只取第一条释义，避免第二行常是被截断的残句
        if entry:
            w_map.setdefault(wl, entry)
        if (i + 1) % 100000 == 0:
            print(f"[i] dict 已处理 {i + 1}/{len(kept)} …")

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"v": 1, "w": w_map}, ensure_ascii=False), encoding="utf-8")
    print(f"[ok] 收录 {len(w_map)} 词 → {OUT}（{OUT.stat().st_size / 1e6:.1f} MB）")


if __name__ == "__main__":
    main()
