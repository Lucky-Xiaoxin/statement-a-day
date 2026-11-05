# AGENTS — 项目当前状态

> 稳定的设计结论在 `docs/decisions.md`，本文件只记录**当前进度/状态**，随工作随时更新。

- 阶段：**MVP 已跑通**（2026-11-06）。`scripts/fetch_daily.py`：CF API 选题（[1400,1800] 全库随机，排除已出过，`--handle` 可排除已 solve）→ 抓题面并清洗（`$$$` LaTeX 转 `\(...\)`、去 header/样例、图片绝对化）→ wordfreq 词频过滤（剔公式/人名/缩写碎片、单复数合并）→ 自包含 `page.html`。样例：`problems/2026-11-06_cf1997D/`，浏览器实测：MathJax 渲染、点词标记、释义查询（含降级）、显示开关全部正常。
- 下一步：
  1. 本人 + 队友试用几天，校准 `--zipf` 阈值（默认 3.5）；
  2. 挂外壳：GitHub Actions cron + Pages（核心脚本不用改）；
  3. v2 候选：句式库正则高亮、Anki CSV 导出、index 总目录页。
- 已知限制：dictionaryapi.dev 对 CP 专业词覆盖不全（已有 Google 翻译兜底）；MathJax 渲染需联网；`--handle` 拉全量提交记录较慢。
- 环境：Windows / Git Bash / Python 3.14，主目录 `E:\english-questions-paper`
- 工作约定（用户要求）：
  - `AGENTS.md` 只放当前项目状态；
  - 稳定不变的结论放 `docs/decisions.md`；
  - 全免费方案（GitHub Pages + 脚本方向），不引入付费服务。
