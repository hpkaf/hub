# AI 赛事雷达 · 项目整体说明

> 一句话：把中国境内**还能报名**的 AI 赛事与黑客松，做成一份每天核验、点开就能报名的清单，并同时以**网站 / 日历订阅 / 邮件摘要 / 公开 JSON** 四种形态对外。

版本：V1.0 · 数据快照 2026-11-16 · 技术栈：Python 标准库 + 原生 HTML/CSS/JS，无框架、无数据库服务

---

## 1. 这是什么

一个**只做 AI 赛道、以"链接真实可达"为第一优先级**的赛事聚合站。收录范围：

- 中国境内（含港澳台）可报名的 AI 赛事、黑客松、算法赛、创新挑战赛
- 线上为主，同时收线下/线上线下混合（标注城市）
- 泛主题黑客松里只要有明确的 AI 赛道，也收，并在列表里标「含 AI 赛道」
- 已结束的赛事不立刻删，保留 90 天可回看，历史数据全部留在公开 JSON 里

不做的：报名代理、收费撮合、UGC 社区、Web3/硬件/加速营等宽口径活动。

---

## 2. 为什么做它

做之前先验证过两件事：

1. **自动聚合不等于可用**。同类开源项目 `hackathon-daily` 用大模型搜索生成每日清单，实测 35 条链接里 28 条打不开（404 / 域名不存在 / 占位符），典型失败是"真实域名 + 编造路径"。所以本项目第一原则是**每条链接必须实测 200/301 才上台**，不用大模型生成赛事。
2. **国内信息相当比例首发在公众号/微信群**，付费聚合站也只覆盖一部分。所以信源按"A 平台 API → B 官方活动站 → C 人工核验 → D 私域线索"四层组织，公众号只当线索来源，不进公开站。

目标定位（用户原话）：先自己用，再做成一个产品形态，作为一个可验证的公开资产（"xxAI 的创始人"）。

---

## 3. 产品形态

| 形态 | 入口 | 说明 |
|---|---|---|
| 网站 | `/`、`/explore.html`、`/organizers.html`、`/guides.html`、`/match.html`、`/calendar.html`、`/race/<id>.html`、`/about.html`、`/submit.html` | 45 条在架 + 68 个详情/存档 + 37 个主办方页 + 3 篇指南；探索页支持方向/平台/级别/形式/状态 + 往届 + 3/7/14 天截止；首屏右栏「本周值得看」；公网 https://race.howfun.cn/ |
| 日历订阅 | `/calendar.html` → `/calendar.ics` | 一键订阅中心（Apple / Outlook / Google / 邮箱入口）；每条赛事一个 VEVENT，另加报名截止提醒事件；详情页可单场加 Google 日历 / 下载 `.ics` |
| 邮件摘要 | `send_digest.py` | 每日「新收录 + 3 天内截止」，SMTP/Resend；邮件附 `calendar.ics` |
| 公开数据 | `/api/events.json`、`/api/events.md`、`/data/races.json`、`/feed.xml` | 带字段说明、更新时间、许可（CC BY 4.0）；Markdown 给 LLM，RSS 给阅读器 |
| 给 AI/检索 | `/llms.txt`、`/llms-full.txt`、`/agent.json`、`/sitemap.xml`、`/robots.txt` | 站点自述、完整 reference、Agent 能力清单、全量 URL |
| 投稿/纠错 | `/submit.html`（支持 `id/title/url` 预填） | 人工核对后 24 小时内上站或更正 |

---

## 4. 质量红线与 AI 分级

四条红线：

1. **链接必须真能打开**：核验返回 200/301 才算"已确认"；403/405/429 标"待确认"，不当有效链接展示；打不开的直接不进列表。
2. **字段只信官方**：标题、日期、报名截止都来自官方报名页；缺失就写"待确认"，不猜。
3. **只收 AI**：非 AI 的综合赛事不收。
4. **去重按证据**：同一赛事在多个渠道出现时，按官方链接 + 标题指纹合并，只留一条。

AI 相关度四级（`ai_level`），判断依据是**官方页的赛道/题目/技术栈，而不是标题**：

| 级别 | 含义 | 判定 |
|---|---|---|
| `core` | AI 核心赛事 | 标题/主题本身是 AI（大模型、智能体、具身、算法、AIGC 等） |
| `platform` | AI 平台赛事 | 天池 / 讯飞 / DataFountain / AI Studio 等 AI 竞赛平台上的比赛 |
| `track` | 含 AI 赛道/方向 | 泛主题黑客松，但官方赛道里明确有 AI 方向 → 列表标「含 AI 赛道」 |
| `other` | AI 相关综合赛事 | 上述都不满足但证据显示相关 |

宣传语里的"AI 赋能"不算证据；拿不到赛道又无法确认的，宁可不收。

---

## 5. 系统架构与每日流水线

```
A 官方 API/SSR   B 官方活动站      C 人工核验         D 线索队列
天池 讯飞         Luma 社区日历     seeds.yaml        公众号 / 联谱 / 湾区AI日历
DataFountain     ×6（ICS）         （22 条）          （只进 leads，不进公开站）
AI Studio 和鲸
DoraHacks 活动行
知乎活动站 魔搭 biendata
        │              │               │                    │
        ▼              ▼               ▼                    ▼
  collect_*.py ─► data/candidates_*.json          data/leads_*.json（人工/后续核验）
        │
        ▼ common.load_candidates → is_ai / EXCLUDE_TITLE 过滤 → 两级去重
        │
        ▼ verify.py：逐条 HTTP 核验 → data/races.db（SQLite 去重账本，只增不删 first_seen）
        │
        ▼ data/races.json（全量导出）
        │
        ▼ build_site.py → site/（index/detail/about/submit/ics/feed/llms/sitemap）
        │
        ├─► serve.sh / GitHub Pages / 任意静态托管
        └─► send_digest.py（可选）→ 邮件摘要
```

一条命令跑完：`run_daily.sh`（抓取 → 核验 → 建站 → 发信，`.env` 自动加载，TZ 固定 Asia/Shanghai）。

---

## 6. 数据模型

`data/races.json` 每条记录：

| 字段 | 说明 |
|---|---|
| `id` | 由归一化 URL（无 URL 时用标题）哈希生成的 12 位 ID，也是详情页文件名 |
| `title` / `organizer` | 官方标题 / 主办方（未知写"主办方待确认"） |
| `mode` / `city` | `online` / `offline` / `hybrid`；线下才写城市 |
| `start_date` / `end_date` | 比赛起止（YYYY-MM-DD） |
| `deadline` | **报名截止日**，缺失为 `null`，页面上显示"待确认" |
| `prize` / `tracks` | 奖金摘要 / 赛道数组 |
| `url` / `source_url` | 官方报名或详情页 / 信源页 |
| `source` / `sources` | 主信源 / 合并过的全部信源 |
| `status` | `open` / `closing`（≤7 天）/ `upcoming` / `closed` / `unknown` |
| `ai_level` | `core` / `platform` / `track` / `other` |
| `registration_closed` | 官方页明确"报名已关闭"时为 true（即使截止日未到也按已截止处理） |
| `verify_state` / `verify_code` / `verified_at` | 核验结果（ok / dead / unknown、HTTP 码、核验时间） |
| `first_seen` / `last_seen` | 首次/最近一次出现在流水线里的时间（去重账本依据） |

展示规则：

- 首页：在架 + 结束后 14 天内的赛事（45 条）
- 详情页 / feed / sitemap：结束后 90 天内保留（70 条）
- 超过 90 天：从站点下线，但保留在 `data/races.json` 与 `races.db` 历史里

---

## 7. 信源体系（当前已接入 11 个）

| 层 | 信源 | 接入方式 | 状态 |
|---|---|---|---|
| A | 天池 | `v3/proxy/competition/api/race/page` + 详情页 | ✅ 每日 |
| A | 讯飞开放平台 | `contests-list` JSON API | ✅ 每日 |
| A | DataFountain | `api/competitions` | ✅ 每日 |
| A | 百度 AI Studio | `studio/match/list` | ✅ 每日 |
| A | DoraHacks | `api/v1/hub/hackathons` | ✅ 每日 |
| A | 活动行 | 搜索页 SSR + 详情页内嵌 `ativityJson` | ✅ 每日 |
| A | 知乎活动站 | 官方 `/api/content` JSON | ✅ 每日 |
| A | 和鲸 Heywhale | `competitionsCommunity` API | ✅ 每日 |
| A | 魔搭 ModelScope | 事件页 SSR 卡片 | ✅ 每日 |
| A | biendata | 竞赛页 SSR（home/home2） | ✅ 每日 |
| B | Luma 社区日历 | 6 本日历的官方 ICS（AI Hacker House、WaytoAGI、Spark Lab、BotLearn、Telos.Circle、Monad） | ✅ 每日 |
| C | 人工核验 | `data/seeds.yaml`（22 条，含官方站渲染核验的 Rokid 大赛） | ✅ 手动 |
| D | 公众号线索 | 搜狗微信搜索 → `leads_wechat.json`（20 条） | ⚠️ 限流，每日最多补 2 条 |
| D | 联谱 lianpu.com | 城市话题页 JSON-LD → `leads_lianpu.json`（14 条） | ✅ 只作线索 |
| D | 湾区 AI 日历 wqai.ltd | ICS → `leads_wqai.json`（6 条）+ 可补截止日 | ✅ 只作线索 |

探测过但走不通/暂不接的：Rokid 赛事 API（需登录）、华为云大赛列表（接口未定位）、启智 OpenI（/competition 404）、腾讯云开发者竞赛（全部已结束）、赛氪（SPA 空壳）、小红书/知乎（登录墙）、高校创业类大赛（非 AI 专项）。

扩展思路与判断标准见 [`docs/sources.md`](sources.md)。

---

## 8. 去重、清洗与状态规则

- **两级去重**：先按归一化 URL（去 `www`、跟踪参数、尾斜杠），再按标题指纹（去年的年份、"的"、标点、常见前后缀如「报名开启」「重磅」）；同一赛事多信源合并字段，人工核验（curated）优先。
- **标题/内容过滤**：训练营、工作坊、沙龙、直播、练手赛、打榜赛、赛后报道等非赛事内容排除。
- **非 AI 综合赛事**：`is_ai()` 按标题+赛道+信源平台判断，泛主题靠赛道证据。
- **时效清理**：每次运行以本次 `run_start` 为界，删除 `last_seen` 更早的记录（赛事从信源消失即下线）；`races.db` 保留 `first_seen` 用于"新收录"判断。
- **报名截止日**：优先官方页；缺失为 `null`；已知"报名已关闭"的记录单独标 `registration_closed`，页面上仍保留详情但 CTA 变成"查看官方页面"。

---

## 9. 当前数据快照（2026-11-16）

> **78 条 / 45 首页 / 68 详情 / 37 个主办方页**（截至 2026-11-16 13:15 北京时间；公网 https://race.howfun.cn/）。
> 公网 API 与本地一致，count=68，updated=2026-11-16T05:19:32Z。

| 指标 | 数值 |
|---|---|
| 全量记录 / 活链 | 78 条 / **78 条全部核验 200** |
| 首页在架 | 45 场（线上 29、在报名/即将截止 25） |
| 详情页 + 存档 | 68 个 |
| 覆盖主办方 | 全量 37 家（本地）/ 36 家（公网） |
| AI 分级（API） | core 34 / platform 22 / track 6 / other 6 |
| 状态分布（API） | open 21 / closing 4 / upcoming 2 / unknown 11 / closed 30 |
| 形式（API） | 线上 53 / 线下 4 / 线上+线下 4 / 未知 7 |
| 信源 | 11 个自动/半自动信源 + 人工种子 |
| 截止日待确认 | API 中 32 条无截止日（历史存档 41 条，多为已结束的平台赛） |
| 线索队列 | 公众号 20（待补 16）、联谱 14、湾区 6 |

---

## 10. 站点结构与机器接口

**页面**

- `/` 列表：搜索、线上/线下/混合/即将截止筛选、按截止日排序、倒计时、AI 级别徽章
- `/race/<id>.html` 详情：赛程、奖金、赛道、官方报名按钮、VERIFICATION 核验侧栏（链接状态 / 核验时间 / 依据）
- `/about.html` 方法与信源：核验标准、信源分层、收录口径、数据接口、保留期、免责声明
- `/submit.html` 投稿/纠错：填完生成邮件或复制内容（配 `SUBMIT_EMAIL`）
- `/calendar.html` 日历订阅中心：Apple / Outlook / Google 入口 + 邮箱收链接 + `.ics` fallback；底层 `/calendar.ics`

**机器接口**

- `/api/events.json`：在架 + 近 90 天记录（含 `ai_level`、`summary`、`directions`、`verified_at`、字段说明）
- `/api/events.md`：同一份数据的 Markdown（给 LLM / Agent）
- `/data/races.json`：全量数据（含已下线）
- `/feed.xml`：RSS 2.0（给阅读器 / Agent）
- `/race/<id>.ics`：单场日历文件；详情页另有 Google 日历模板链接
- `/llms.txt` / `llms-full.txt`：给 AI 搜索/代理的站点说明与完整 reference
- `/agent.json` / `.well-known/agent.json`：只读 Agent 能力清单
- `/sitemap.xml`、`/robots.txt`

**视觉方向**：Radar Room（夜间雷达室）——近黑底 + 荧光绿信号色 + 宋体大标题 + 等宽数据 + 同心圆雷达动效 + 发丝线清单；默认跟随系统明暗，另提供纸白浅色主题（右上角 ◐ 切换），三个备选视觉方向与字体试验留在 `variants/` 备用。

---

## 11. 三种运行方式

1. **本机手动**：`./setup.sh` → `SKIP_DIGEST=1 ./run_daily.sh` → `./serve.sh`
2. **24×7 常驻（家用电脑）**：cron / launchd / systemd 每天 08:00 跑流水线 + `serve.sh` 常驻 + 备份 `races.db`，完整步骤见 [`INSTALL.md`](../INSTALL.md)
3. **本机唯一数据源 + GitHub Pages**（当前采用）：本机 08:00 流水线 commit/push，`.github/workflows/pages.yml` 只负责部署；`daily-refresh-manual.yml` 仅保留手动触发，避免和本机抢数据

---

## 12. 成本

| 项 | 费用 |
|---|---|
| 服务器 | ¥0（静态站，家里旧电脑或 GitHub Pages） |
| 数据库 | ¥0（SQLite 文件） |
| 邮件 | ¥0（Resend 免费额度 / 任意邮箱 SMTP） |
| 域名 | `.com` 约 ¥70/年；`.ai` 约 ¥600/年；`.dev/.app` 约 ¥120/年 |
| 推广 | 暂 ¥0 |
| **首年合计** | **约 ¥70（不买 .ai 域名）～ ¥600** |

---

## 13. 项目结构

```
ai-race-radar/
├── scripts/
│   ├── common.py            # 常量、归一化、去重、AI 分级、状态计算
│   ├── collect_*.py         # 各信源采集（平台 API / SSR / Luma ICS / 线索源）
│   ├── verify.py            # 链接核验 + SQLite 账本 + 全量导出
│   ├── build_site.py        # 建站（列表/详情/关于/投稿/ics/feed/llms/sitemap）
│   ├── site_ui.py           # 页面结构与文案
│   ├── theme.py             # Radar Room 样式与前端交互
│   ├── send_digest.py       # 邮件摘要
│   ├── enrich_wechat_leads.py  # 公众号线索补全（限流）
│   └── cdp-shot.mjs         # 真机视口截图（开发工具）
├── data/                    # 种子、候选、线索、races.db、races.json
├── site/                    # 构建产物（可被任意静态服务托管）
├── docs/                    # 信源清单、上线清单、截图、本说明
├── variants/                # 设计/字体探索
├── setup.sh / run_daily.sh / serve.sh / .env.example
├── INSTALL.md / README.md / requirements.txt
└── .github/                 # Actions 定时 + Pages + Issue 模板
```

---

## 14. 已完成 / 下一步

**已完成**

- 4 层信源、11 个自动/半自动接入、每日流水线、77/77 活链核验
- AI 四级标注、90 天存档、去重账本、报名关闭状态
- 静态站（列表/详情/关于/投稿）、日历订阅、邮件摘要
- 探索页（方向/平台/级别/形式/状态 + 往届）、37 个主办方页、3 篇指南、AI 匹配页
- 详情页：官方 meta 简介、日程、主办方卡、相关赛事、来源/更正、日期结构化数据
- 公开数据（`api/events.json`、`api/events.md`、`data/races.json`、`feed.xml`）
- Agent/LLM：`llms.txt`、`llms-full.txt`、`agent.json`、`.well-known/agent.json`、JSON-LD graph
- Radar Room 视觉、深色/浅色自适应、移动端 390 真机视口验收
- 24×7 家用部署包（安装/常驻/备份/排错手册）

**下一步（按优先级）**

1. 上线：定名字 + 域名，建 GitHub 仓库，配 Pages（或家用机器 + Tunnel）；只差用户三个输入
2. 线索核验：14 条联谱 + 6 条湾区 + 16 条公众号线索，人工确认官方入口后进站
3. 质量补全：在架清单里 26 条无截止日（其中 22 条前台显示「待确认」）逐步补齐
4. 公众号：限流下的替代方案（投稿入口、主办方直联、白名单批量人工核验）
5. 可选：字体升级（思源宋体 + IBM Plex Mono）、软著申请材料生成

---

## 15. 已知限制与风险

- **私域活动**：大量黑客松在公众号/微信群发布，报名走二维码或审核制，没有公开可核验的报名页 → 只能进线索队列，不上站
- **反爬**：搜狗微信约 45 分钟冷却；部分站点（Rokid 平台、华为云）需登录或接口未公开
- **SPA 站点**：需要 headless 渲染核验，成本高，按季度巡检而非每日
- **季节性**：11 月初在招赛事偏少，条数会波动；入口集中在寒暑假和春招/秋招
- **信息时效**：虽然每天核验，报名状态最终仍以主办方页面为准（站点已声明）
- **合规**：只做公开信息整理，不代报名、不收费；主办方要求下架会即时处理
- **单点依赖**：`races.db` 丢失会导致"新收录"全部重置，必须备份

---

## 16. 文档索引

| 文档 | 内容 |
|---|---|
| [`README.md`](../README.md) | 快速开始、数据契约、信源表、公开数据、路线图 |
| [`INSTALL.md`](../INSTALL.md) | 24×7 部署：cron/launchd/systemd、常驻服务、备份、排错 |
| [`docs/sources.md`](sources.md) | 信源四层模型、已接入/可用未接/走不通清单、扩源判断标准 |
| [`docs/launch-checklist.md`](launch-checklist.md) | 命名/域名/上线/推广清单与周指标 |
| [`docs/benchmark-hackertrip.md`](benchmark-hackertrip.md) | HackerTrip 对标研究：可借鉴与不借鉴 |
| 本文 | 项目整体说明（定位、架构、数据、现状、路线） |

---

## 17. 本机 24×7 部署（2026-11-08 补记）

项目已在一台 Windows 10 工作机上以原生 PowerShell 部署（不依赖 WSL / Docker）：

- 每日流水线：计划任务 `AI Race Radar - Daily`，每天 08:00 以 SYSTEM 运行，入口 `deploy\run_daily.ps1`
- 常驻站点：计划任务 `AI Race Radar - Web`，开机启动、崩溃自动重启，`http://192.168.1.3:8080/`（本机 `127.0.0.1:8080`）
- 数据备份：每轮流水线前自动复制 `data\races.db` 到 `data\backups\`，保留 30 份
- 部署手册：[`windows-24x7.md`](windows-24x7.md)
- 一致性核对与代码修复记录：[`consistency-report.md`](consistency-report.md)
- Agent / RSS / 日历接入：[`agent-integration.md`](agent-integration.md)
- 当前运行模式：本机是唯一数据源；08:00 流水线结束后 commit/push，GitHub Pages 仅负责部署
- 与本文的已知差异：运行后全量记录为 78 条（历史 DoraHacks 赛事从信源消失并按时效规则清理）；
  原 `run_daily.sh` 漏掉的 6 个平台采集器已补齐
