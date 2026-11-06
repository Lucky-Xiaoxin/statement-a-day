# AGENTS — 项目当前状态

> 稳定的设计结论在 `docs/decisions.md`，本文件只记录**当前进度/状态**，随工作随时更新。

- 阶段：**外壳就绪，待用户建仓推送**（2026-11-07）。核心（v0.2 全部特性：ECDICT 离线释义、内文高亮、min-words 保底、右上角 Switch 深色模式）+ 部署外壳：`.github/workflows/daily.yml`（cron 北京时间~08:00，cache 词典子集，`--translate` 段落级折叠译文，commit 产物，deploy-pages）+ `scripts/build_index.py`（站点首页）。本地已验证：译文失败优雅降级、stub 译文渲染 14 段全对位、index 两日条目。样例：`problems/2026-11-06_cf1997D/`、`problems/2026-11-07_cf1081D/`。
- 下一步（用户侧）：GitHub 建公开仓库 → push → Settings→Pages 选 GitHub Actions → 手动 Run workflow 验证 → 观察 11-08 早上首次自动运行。
- 待验证（CI 首跑才能确认）：非官方 Google 接口从 Actions 出发的真实成功率与译文质量；cron 漂移幅度。
- v2 候选：历史词频统计（生词口径，按出现天数）、句式库高亮、Anki CSV 导出。
- 已知限制：本地（国内）构建无译文（预期）；ECDICT 子集需每人构建一次（70MB，国内较慢，`--zip` 可指定手动下载包）；MathJax 需联网；`--handle` 拉全量提交较慢。
- 环境：Windows / Git Bash / Python 3.14，主目录 `E:\statement-a-day`
- 工作约定（用户要求）：
  - `AGENTS.md` 只放当前项目状态；
  - 稳定不变的结论放 `docs/decisions.md`；
  - 全免费方案（GitHub Pages + 脚本方向），不引入付费服务。
