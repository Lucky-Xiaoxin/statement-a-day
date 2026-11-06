# statement-a-day
> **A statement a day keeps the WA away.**

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

## 部署（GitHub Actions + Pages）

外壳已就绪：`.github/workflows/daily.yml` 每天北京时间约 08:00 自动抓题、生成页面（含折叠译文）、发布站点。**你要做的只有 4 步**：

1. 在 GitHub 新建**公开**空仓库（Public 是 Actions/Pages 免费的前提）
2. 关联并推送：
   ```bash
   git remote add origin https://github.com/<你>/<仓库名>.git
   git push -u origin main
   ```
3. 仓库 Settings → Pages → Build and deployment → **Source 选 GitHub Actions**
4. Actions 标签页 → daily-problem → **Run workflow** 手动跑一次（验证 + 首次部署）

之后每天上午站点自动更新，队友（和你的手机）访问 `https://<你>.github.io/<仓库名>/`。

备注：
- 若「提交每日产物」一步报 403：Settings → Actions → General → Workflow permissions 改为 **Read and write permissions**。
- CI 首次运行会自动下载 ECDICT（约 70MB）构建释义子集并缓存，之后不再下载。
- 译文只在 CI（境外网络）生成并烤进页面；本地跑没有译文属预期（见 docs/decisions.md §6）。

## 备注

- 题面版权归出题人，个人/队内学习使用，请低调。
- 题目选取的种子 = 日期 + 区间：Actions 统一出题后全队同题；本地当天重跑幂等。
