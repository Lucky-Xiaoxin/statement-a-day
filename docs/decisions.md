# 设计决策（稳定结论）

> 本文记录**大概率不会变动**的结论：目标、选型、边界。随时可变的东西（当前进度、待办）放 `AGENTS.md`。
> 定稿：2026-11-06。其中「免费资源现状」类内容有时效性，变化时回头修订。

## 1. 目标一句话

为 ICPC/CF/AtCoder 英文题面阅读训练做一个**全免费、零服务器**的工具：
每天（或手动）取一道 rating ≤ X 的英文原题，自动生成「题面 + 生词表 + 句式命中 + （可选）双语对照」的静态页面。

## 2. 问题定位（为什么读题难）

按优先级假设：

1. **八股句式不熟**（主瓶颈，待用户确认）：题面是一种固定套路的「方言」——"It is guaranteed that…"、"print any valid answer"、"modulo 10^9+7"、"0-indexed"、"It can be shown that…"、"In the i-th of the following q lines…"。这是**有限集合**，背完受益终身，且 CF/AtCoder/ICPC 通用。→ 工具的第一优先级是**句式库**，不是词典。
2. **生词**：数量不大且高度重复（integer, modulo, permutation, guaranteed, minimum…）。→ 频率过滤即可，不需要真 NLP。
3. 长难句：机翻可缓解，但已被免费浏览器扩展解决（见 §6）。

**推论：「双语对照」是免费商品，「词表 + 句式」才是自建价值。**

## 3. 形态选型

结论：**生成器与外壳分离**。

- 核心 = 一个 Python 生成器：输入（指定题号 或 "今天的题"），输出一个自包含静态 HTML。本地随时可跑，无在线依赖（除抓题面本身）。
- 外壳 = GitHub Actions 定时跑生成器 + GitHub Pages 展示。外壳坏了不影响核心。
- 路径：先做核心（纯本地 MVP），手动跑一两周验证有用，再挂 Actions + Pages。

| 形态 | 每天 | 手机可看 | 历史积累 | 备注 |
|---|---|---|---|---|
| A. Actions + Pages | ✅ 自动 | ✅ 浏览器 | ✅ git 历史 | 公开仓库免费；cron 会延迟、偶发跳过 |
| B. 纯本地脚本 | ❌ 靠人 | ❌ | 弱 | 最低成本，即核心生成器 |
| C. 安卓 APP | ✅ | ✅ | 自建 | 工作量数量级不对，**不做**（手机浏览器开 Pages 即可） |

版权备注：题面版权归出题人。个人学习用途、低调公开重分发，业内普遍接受；若日后想大范围传播，改为只公开词表/句式，原文不放。

## 4. 数据源

- **Codeforces 优先**：
  - `codeforces.com/api/problemset.problems`：全题库 + rating + tags，免费无鉴权（限速约 1 req/s）。实现"选 rating ≤ X 且没做过的题"足够（做过与否查 `user.status`）。
  - 题面本体 **API 没有**，需抓 `codeforces.com/problemset/problem/{contestId}/{index}` HTML：带正常 User-Agent、低频（每天一两页无压力）、失败重试，可换备用镜像（m1.，不保证常驻）。
  - 公式保留原 LaTeX，页面挂 KaTeX/MathJax CDN 渲染。
- **AtCoder 备选**：无官方 API；用 kenkoooo AtCoderProblems 公开 JSON（题号 + 难度），题目页面自带英文 tab 可抓，抓取放慢、礼貌。

## 5. 词表方案（"自动识别" = 频率过滤）

- 用 `wordfreq`（pip，MIT，离线 Zipf 频率），不走在线词典。
- 流程：分词 → 去数字/符号/变量型 token → Zipf 低于阈值（可配）者入生词表 → 减去 `known_words.txt`（个人已知词表，见过即手工加入）→ 按 Zipf 升序输出。
- 附：`phrases.md` 句式库人工积累 + 每篇题面自动正则匹配命中句式并高亮。
- 顺手项：生词表导出 Anki CSV（纯文本，免费）。

## 6. 翻译策略（锦上添花，允许失败）

- 构建时 best-effort 调**非官方** Google 翻译接口（无 key 免费，可能限流），失败则降级纯英文 + 页面提示。
- 日常兜底：**沉浸式翻译**浏览器扩展（免费，任意网页双语对照，手机可装）。
- 不注册任何要 key 的翻译服务（含 DeepL 免费 tier——免费但要注册，违背"零配置"）。

## 7. 明确不做（scope-out）

安卓 APP、账号/登录、付费 API（翻译或 LLM）、自动判题/提交代码、独立"做过题"同步（直接查 CF `user.status`）。

## 8. Open questions（待定；定了移入正文）

- rating 门槛 X 定多少？建议起步 1000–1400：题面语言难度与 rating 不完全挂钩，Div.2 A–C 句式最八股。
- 题源范围：只取 Div.2/3 的 A–C，还是全库随机？
- `known_words.txt` 初始：空表从零积累，还是先灌一份 CET4/6 词表打底？
- 只自己用，还是要分享给别人？影响版权姿势和是否需要配置界面。
