# english-questions-paper

为 ICPC/CF 英文题面阅读训练做的全免费小工具：每天从 Codeforces 随机抽一道 rating ∈ [1400, 1800] 的原题，自动生成「题面 + 生词表」单页。点击生词标记"我认识"（存浏览器 localStorage，队友互不影响）。

- 设计与决策（稳定结论）：[docs/decisions.md](docs/decisions.md)
- 当前状态：[AGENTS.md](AGENTS.md)

## 用法

```bash
pip install wordfreq                    # 唯一的第三方依赖，其余全标准库
python scripts/build_dict.py            # 一次性：构建 ECDICT 离线释义子集（下载约 70MB，国内较慢；可 --zip 指定手动下载的包）
python scripts/fetch_daily.py           # 今天的题，生成后自动打开浏览器
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `--date YYYY-MM-DD` | 今天 | 补卡某天；同一天重跑幂等 |
| `--min-rating` / `--max-rating` | 1400 / 1800 | 题目难度区间 |
| `--handle 你的CFID` | 无 | 排除已 solve 的题 |
| `--zipf 3.5` | 3.5 | 词频阈值，调小生词更多 |
| `--min-words 5` | 5 | 生词保底数量（阈值外罕词补足，标「补」），0 关闭 |
| `--no-open` | 关 | 不自动打开浏览器 |

输出在 `problems/日期_cf题号/`：`page.html`（自包含单页）、`words.json`（生词表）、`statement.html`（题面缓存）、`meta.json`。释义数据 `data/ecdict-subset.json` 体积大，不入库（见 `.gitignore`），每人构建一次。

## 页面功能

- 点生词 = 标记"我认识"（浏览器 localStorage，队友各自独立）；☆ = 固定保留；「补」= 阈值外保底词
- ⓘ 查中文释义 + 音标 + 考试标签（ECDICT 离线数据，不联网）
- 题面内文里生词淡黄底高亮，已认识的变灰；工具栏可关高亮
- 工具栏：显示/隐藏已认识、高亮开关；右上角 Switch 切换深色模式（默认跟随系统，灰黑配色）
- 公式由 MathJax 渲染（需联网）；生词按 Zipf 词频从罕见到常见排序

## 备注

- 题面版权归出题人，个人/队内学习使用，请低调。
- 题目选取的种子 = 日期 + 区间：同一台机器当天重跑结果一致；以后挂上 GitHub Actions 统一出题后全队同题。
- 句子级双语译文计划随 Actions 外壳上线：境外构建机翻译后烤进页面，国内浏览零请求（见 docs/decisions.md §6）。
