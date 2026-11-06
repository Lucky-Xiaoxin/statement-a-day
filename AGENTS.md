# AGENTS — 项目当前状态

> 稳定的设计结论在 `docs/decisions.md`，本文件只记录**当前进度/状态**，随工作随时更新。

- 阶段：**已上线** 🎉（2026-11-07 首跑全绿）。站点：https://lucky-xiaoxin.github.io/statement-a-day/ ；仓库：https://github.com/Lucky-Xiaoxin/statement-a-day 。CI 实测：ECDICT 构建 149,438 词、译文 14/14 段成功、eqp-bot 自动提交、Pages 发布正常。本地文件夹与 GitHub 仓库名不一致（文件夹 E:\english-questions-paper，仓库名 statement-a-day），不影响任何功能。
- 下一步：
  1. 观察 2026-11-08 早上首次全自动 cron 运行（GitHub cron 有 0-60 分钟漂移）；
  2. 队友开始用，校准 `--zipf` / `--min-words`（当前 3.5 / 5，改动需提交后 CI 生效）；
  3. v2 候选：历史词频统计（生词口径，按出现天数）、句式库高亮、Anki CSV 导出。
- 待验证（CI 持续观察）：非官方 Google 接口的长期成功率与译文质量；cron 漂移幅度。
- 已知限制：本地（国内）跑脚本无译文（CI 才有）；MathJax 需联网；`--handle` 拉全量提交较慢。
- 环境：Windows / Git Bash / Python 3.14，主目录 `E:\english-questions-paper`
- 工作约定（用户要求）：
  - `AGENTS.md` 只放当前项目状态；
  - 稳定不变的结论放 `docs/decisions.md`；
  - 全免费方案（GitHub Pages + 脚本方向），不引入付费服务。
