# AGENTS — 项目当前状态

> 稳定的设计结论在 `docs/decisions.md`，本文件只记录**当前进度/状态**，随工作随时更新。

- 阶段：**MVP v0.2**（2026-11-07）。v0.1（11-06）跑通并实测；v0.2 按试用反馈改造：释义换 ECDICT 离线子集（`scripts/build_dict.py` 一次性构建 `data/ecdict-subset.json`，不入库，队友各构建一次）、去掉自动沉底（等价于页面打开次数，零区分度）、题面内文淡黄高亮+开关、`--min-words`（默认 5）保底补充、去掉词库导出/导入（换设备从零点起）。v0.1 样例：`problems/2026-11-06_cf1997D/`。
- 下一步：
  1. 试跑校准 `--zipf` / `--min-words`；
  2. 挂外壳：GitHub Actions cron + Pages，构建时加段落级折叠译文（非官方 Google 接口，境外构建机可达，烤进页面）；
  3. v2：历史词频统计（生词口径，按出现天数）、句式库高亮、Anki CSV 导出、index 目录页。
- 已知限制：本地（国内）构建无句子级译文（Actions 上线后解决）；ECDICT 子集需每人构建一次（GitHub Release 下载约 70MB，国内较慢，可用 `--zip` 指定手动下载的包）；MathJax 渲染需联网；`--handle` 拉全量提交记录较慢。
- 环境：Windows / Git Bash / Python 3.14，主目录 `E:\english-questions-paper`
- 工作约定（用户要求）：
  - `AGENTS.md` 只放当前项目状态；
  - 稳定不变的结论放 `docs/decisions.md`；
  - 全免费方案（GitHub Pages + 脚本方向），不引入付费服务。
