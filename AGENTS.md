# AGENTS — 项目当前状态

> 稳定的设计结论在 `docs/decisions.md`，本文件只记录**当前进度/状态**，随工作随时更新。

- 阶段：**已上线** 🎉（2026-11-07 首跑全绿）。站点：https://lucky-xiaoxin.github.io/statement-a-day/ ；仓库：https://github.com/Lucky-Xiaoxin/statement-a-day 。CI 实测：ECDICT 构建 149,438 词、译文 14/14 段成功、eqp-bot 自动提交、Pages 发布正常。v0.3 交互重构（2026-11-07 晚）：点词=看释义、✓=标记已认识（不隐藏）、☆/ⓘ 删除、Zipf 阈值调至 4.0 试行一周、trans.json 复用使本地重渲染保留译文。本地文件夹与 GitHub 仓库名不一致（文件夹 E:\english-questions-paper，仓库名 statement-a-day），不影响任何功能。v0.4（2026-11-07）：总词表统计页上线（stats.html），深色 Switch 常驻全站三类页面。v0.4.1（2026-11-11）：总词表页移动端适配（≤640px 卡片式布局），README 补充在线站点链接。v0.4.2（2026-11-11）：新增 `deploy.yml`，合并 main 后自动重建目录/统计页并发布 Pages（不抓题不提交）；此前合并 PR 不会触发发布，是移动端修复"未生效"的原因。
- 下一步：
  1. 观察 2026-11-08 早上首次全自动 cron 运行（GitHub cron 有 0-60 分钟漂移）；
  2. 队友开始用，校准 `--zipf` / `--min-words`（当前 4.0 / 5，改动需提交后 CI 生效）；
  3. v2 候选：句式库高亮、Anki CSV 导出（总词表统计已于 2026-11-07 上线：`scripts/build_stats.py`，按出现天数聚合、浏览器端过滤已认识、CI 自动重算、入口在首页）。
- 待验证（CI 持续观察）：非官方 Google 接口的长期成功率与译文质量；cron 漂移幅度。
- 已知限制：本地（国内）跑脚本无译文（CI 才有）；MathJax 需联网；`--handle` 拉全量提交较慢。
- 环境：Windows / Git Bash / Python 3.14，主目录 `E:\english-questions-paper`
- 工作约定（用户要求）：
  - `AGENTS.md` 只放当前项目状态；
  - 稳定不变的结论放 `docs/decisions.md`；
  - 全免费方案（GitHub Pages + 脚本方向），不引入付费服务。
