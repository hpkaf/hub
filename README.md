# AI 赛事雷达 · AI Race Radar

> 中国 AI 赛事与黑客松，一站看全。每一场都经过核验：官方链接、报名截止、线上/线下，点开就能报名。

一个**只收 AI 赛道**的国内赛事清单：静态站 + 日历订阅（`.ics`）+ 每日邮件摘要。

> 想先看全景（定位、架构、数据模型、信源、现状、路线图）？读 [docs/PROJECT-OVERVIEW.md](docs/PROJECT-OVERVIEW.md)。
不做"全网最全"，只做"每一条都点得开、日期对得上"。

- 覆盖：大模型 / 算法 / 数据 / 算力 / 智能体 / AIGC / 具身智能 相关的**比赛与黑客松**（线上优先，也收线下）
- 频次：每天 08:00（北京时间）重跑核验
- 形态：纯静态站（可托管在 GitHub Pages / Cloudflare Pages 免费额度内）+ 开放 JSON + `.ics`

---

## 为什么要做（以及为什么不是又一个聚合号）

信息不缺，**能用的信息**缺。现有聚合大多死在两个地方：

1. **链接是编的**：拿大模型直接生成"赛事 + 报名链接"，真实域名 + 虚构路径，80% 点开是 404。实测某个"每日黑客松推送"项目 35 条里 28 条打不开。
2. **没有截止日**：只告诉你"有这么个比赛"，不告诉你"什么时候报名截止"，等于没说。

所以本项目的三条质量红线：

- **链接必须真能打开**：报名页 / 详情页实测 200/301 才算"已确认"；被反爬拦截的标"待确认"，不伪装成有效。
- **截止日必填或显式标"待确认"**：不猜、不编。
- **只收 AI**：非 AI 的综合赛事（哪怕是"互联网+"大类）不收，宁缺毋滥。

聚合的价值不在条数，在核验。

---

## 当前快照（2026-11-08）

- 首页 **43 场**（在架 + 近 14 天结束）；全量 **79 条 / 79 条活链**；详情页/存档 **68 个**
- 公网：**https://race.howfun.cn/**（GitHub Pages，CNAME → `hpkaf.github.io`）
- 日历：**https://race.howfun.cn/calendar.ics**
- 新增页面：`/explore.html`（方向/平台/级别/形式/状态 + 往届 Tab）、`/organizers.html` + 35 个主办方页、`/guides.html` + 3 篇指南、`/match.html`（本地规则匹配）
- 热点模块：首屏右栏「本周值得看」5 条，按截止日 + 奖金/主办方可解释排序；Explore 新增 3/7/14 天内截止筛选。**不是流量热度榜。**
- 产物：`site/`（index / explore / organizers / match / guides / race / organizer / guides + `calendar.ics` + `feed.xml` + `sitemap.xml` + `llms.txt` + `llms-full.txt` + `agent.json` + `api/events.json` + `api/events.md` + `data/races.json` + `data/hot.json`）
- 视觉：**Radar Room**——纸白/近黑双主题、荧光绿信号色、宋体大标题、等宽数据；默认跟随系统明暗，右上角 ◐ 切换
- 投稿：站内 `submit.html` 表单（无后端，走邮件 / 复制），支持从详情页带 `id/title/url` 预填纠错
- 信源：8 个平台 JSON API + 官方活动站/列表（知乎、魔搭、biendata）+ Luma 社区日历 ICS（6 本）+ 和鲸 API + 人工核验种子，实测记录见 [docs/sources.md](docs/sources.md)
- 机器入口：`api/events.json`、`api/events.md`、`data/hot.json`、`feed.xml`、`llms.txt`、`llms-full.txt`、`agent.json`、`calendar.ics`
- 截图：`docs/img/index-desktop.png`（浅色）、`docs/img/index-dark.png`（深色）、`docs/img/explore.png`、`docs/img/organizers.png`、`docs/img/match.png`、`docs/img/guide.png`、`docs/img/detail.png`、`docs/img/submit.png`
- 本地预览：`python3 scripts/serve_site.py --port 8080 --directory site`（`.ics` 会返回 `text/calendar`）

> 2026-11-09 本轮构建：77 条活链 / 67 个详情页（MDBA Youth Blockchain Hackathon 从 DoraHacks 信源消失；另 1 条在 11/09 凌晨跨过 90 天窗口自动归档）。
> 差异与修复记录见 [docs/consistency-report.md](docs/consistency-report.md)。

移动端截图用 CDP 真实视口（Chrome CLI 的 `--window-size` 有 500px 下限，直接截 390 会被裁）：

```bash
node scripts/cdp-shot.mjs "file://$PWD/site/index.html" docs/img/index-mobile.png 390 844 2
```

---

## 现在的状态

```
ai-race-radar/
├── scripts/
│   ├── common.py        # 常量、HTTP、URL/标题归一化、状态计算、聚合去重
│   ├── verify.py        # 载入候选 → 去 AI 过滤 → 两级去重 → 链接核验 → SQLite → 导出 races.json
│   ├── build_site.py    # races.json → site/（首页/探索/主办方/匹配/指南 + 详情 + 开放数据）
│   ├── site_ui.py       # 页面模板层：head/foot、列表行、详情、关于、投稿页
│   ├── pages_extra.py   # 探索/主办方/匹配/指南页面模板
│   ├── guides_content.py # 3 篇指南内容
│   ├── taxonomy.py      # 方向标签（智能体/大模型/具身/算法…）
│   ├── organizers.py    # 主办方聚合与实体页
│   ├── hot.py           # 首页「本周值得看」编辑精选
│   ├── summaries.py     # 官方页 meta 简介过滤
│   ├── enrich_summaries.py # 按需抓取官方页简介 → summaries.json
│   ├── theme.py         # 设计系统：STYLE（全部 CSS）+ APP_JS（筛选/搜索/排序/投稿/主题）
│   ├── serve_site.py    # 静态服务：.ics/.md/.json 正确 Content-Type
│   ├── fetch_event_sites.py # 主办方自有活动站 → candidates_events.json
│   ├── collect_sources.py   # 魔搭 / 和鲸 / biendata 适配器 → candidates_extra.json
│   ├── collect_luma.py      # Luma 社区日历（ICS）→ candidates_luma.json
│   ├── collect_lianpu.py    # 联谱活动页 → leads_lianpu.json（线索，不进站）
│   ├── collect_wqai.py      # 湾区 AI 日历 ICS → deadline 补全 / leads_wqai.json
│   ├── discover_wechat.py   # 搜狗微信搜索 → leads_wechat.json（线索）
│   ├── enrich_wechat_leads.py # 公众号线索补全：签名文章 → 正文 + 官方链接（受搜狗限流）
│   └── send_digest.py   # 「新收录 + 3 天内截止」邮件摘要（附 .ics，SMTP / dry-run）
├── data/
│   ├── seeds.yaml           # 人工核验过的种子（curated，最高优先级）
│   ├── organizers.yaml      # 主办方 slug/官网/简介（可选，缺省自动生成）
│   ├── summaries.json       # 官方页 meta 简介（按需刷新）
│   ├── candidates_comp.json # 赛事平台抓取结果（天池/讯飞/DataFountain/AI Studio）
│   ├── candidates_hack.json # 黑客松/活动平台抓取结果（DoraHacks/活动行/公众号）
│   ├── candidates_events.json # 主办方自有活动站抓取结果（知乎黑客松等）
│   ├── event_sites.yaml     # 自有活动站清单（新增站点只加配置）
│   ├── leads.yaml           # 私域线索队列（小红书/公众号，未拿到官方页前不进站）
│   ├── leads_*.json         # 各线索源的待核验队列（联谱 / wqai / 公众号）
│   ├── luma_calendars.yaml  # Luma 社区日历清单（slug + calendar api_id）
│   ├── wechat_whitelist.yaml # 补全时优先处理的公众号白名单
│   ├── races.db             # 去重账本（SQLite，须进版本库）
│   └── races.json           # 站点数据源（导出）
├── site/                    # 构建产物：index / explore / organizers / match / guides
│                            #   + race/<id>.html|.ics + organizer/<slug>.html + guides/<slug>.html
│                            #   + calendar.ics + feed.xml + llms.txt + llms-full.txt + agent.json
│                            #   + api/events.json + api/events.md + sitemap.xml + data/hot.json
├── deploy/                  # Windows 24×7：计划任务、静态服务、备份
├── run_daily.sh             # 一条命令跑完整流水线
└── .github/workflows/daily.yml  # 每天 08:00 自动核验 + 部署
```

---

## 快速开始（本地跑通）

> 部署到 24 小时常开机器（cron / launchd / systemd + 常驻静态服务 + 备份）见 [INSTALL.md](INSTALL.md)；
> 原生 Windows 10/11 见 [docs/windows-24x7.md](docs/windows-24x7.md)（`deploy\install.ps1` 一键注册计划任务）。

```bash
cd ai-race-radar

# 1. 依赖（系统 python 即可，pyyaml 装到项目内 .pylibs）+ 生成 .env
./setup.sh

# 2. 一条命令：核验 → 建站
SKIP_DIGEST=1 ./run_daily.sh

# 3. 看效果（局域网/本机常驻静态服务）
./serve.sh                    # http://127.0.0.1:8080/
# 或 open site/index.html
```

单独跑某一步：

```bash
python3 scripts/verify.py --no-verify      # 跳过联网核验（调试）
python3 scripts/verify.py --limit 10       # 只核验前 10 条
python3 scripts/build_site.py
python3 scripts/send_digest.py --dry-run   # 只生成预览 data/digest_preview.html
```

> 脚本会自动把 `.pylibs` 注入 `sys.path`，所以不必建 venv。

---

## 数据契约

所有抓取源统一输出下面这个结构（`data/candidates_*.json` 是数组，`data/seeds.yaml` 也是列表）：

```json
{
  "title": "赛事名称",
  "organizer": "主办方",
  "mode": "online | offline | hybrid",
  "city": "线上 / 北京 / 深圳…",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "deadline": "YYYY-MM-DD",
  "prize": "奖金或奖项描述",
  "tracks": ["大模型", "智能体"],
  "url": "官方报名/详情页（必须是能打开的官方链接）",
  "source": "curated | tianchi | xfyun | datafountain | aistudio | dorahacks | huodongxing | sogou",
  "source_url": "发现这条信息的页面",
  "evidence": "核验依据，例如：官方页 200，标题与截止日一致",
  "notes": "补充说明"
}
```

字段规则：
- `url` 必须实测可达；编造链接的记录会被 `verify.py` 判死链并从站点剔除。
- 日期统一 `YYYY-MM-DD`，解析不了的留空（前端显示"待确认"），**不要写"待定"之类的自由文本**。
- `mode` 只能三选一；线上赛事 `city` 写"线上"。
- 只收 AI 相关；`is_ai()` 按 `AI_KEYWORDS` + 平台白名单判断。
- 对外展示的 AI 分级用另一套更严的规则（`ai_level()`）：`core`（标题即 AI）/ `track`（泛赛事但赛道里有明确 AI 方向，卡片标「含 AI 赛道」）/ `platform`（天池等 AI 平台比赛）/ `other`（只有间接 AI 线索）。

去重（`common.dedupe`）：
1. 先按归一化 URL（去 `utm_*`/`spm`/末尾斜杠）分组；
2. 组内按来源优先级合并（curated > 平台抓取 > 公众号），补全缺失字段、合并 `tracks`；
3. 再按标题指纹（去年份、去"的"、去标点）做二级去重。

---

## 信源与线索队列

| 层级 | 来源 | 产出 |
|---|---|---|
| A 官方 API | 天池、讯飞、DataFountain、百度 AI Studio、DoraHacks、活动行、和鲸 Heywhale、Luma 社区日历 ICS | `candidates_comp.json` / `candidates_hack.json` / `candidates_extra.json` / `candidates_luma.json` |
| B 官方活动站 | 主办方自有活动页（如 `hackathon-s3.event.zhihu.com`，带 JSON 活动数据）；魔搭 ModelScope 竞赛/活动页、biendata | `candidates_events.json` / `candidates_extra.json` |
| C 人工核验 | 官网/官方公众号里逐条核实 | `seeds.yaml` |
| D 私域线索 | 小红书、微信群、公众号推文（拿不到稳定的官方报名页）；联谱 lianpu.com 城市 AI 主题页；湾区 AI 日历 wqai.ltd 的截止日条目 | `leads.yaml` / `leads_wechat.json` / `leads_lianpu.json` / `leads_wqai.json`，**不进公开站点** |

公众号流水线：`discover_wechat.py`（搜狗微信搜标题）→ `enrich_wechat_leads.py`（标题 → 搜狗网页 → 带签名文章 → 正文 + 正文里的官方链接）；白名单在 `data/wechat_whitelist.yaml`（29 个主办方/媒体号，优先补全）。搜狗网页连续查约 3 次触发反爬，脚本每轮 2 条、命中即冷却 45 分钟；Bing/Baidu 实测查不到中文原文，转载反查只能走搜狗或人工。

扩展信源的实测记录（哪些源接通了、哪些 SPA/登录墙走不通、厂商赛事站怎么巡检）见 [docs/sources.md](docs/sources.md)。

D 层是刻意留的口子：国内相当一部分黑客松首发在公众号/小红书，但链接不是官方报名页，直接上站会重蹈"80% 死链"的覆辙。线索攒到官方页后，按 `seeds.yaml` 的字段契约并入，再走一遍核验即可。

公众号这条路的实测结论（2026-11）：搜狗微信搜索能稳定拿到标题/公众号/发布时间/摘要（每次 10 条），但结果跳转一律 302 到反爬验证页；直接打开 `mp.weixin.qq.com` 无签名文章只返回 JS 空壳，headless Chrome 会看到「环境异常」；只有搜狗网页搜索偶尔给出的**带签名**文章链接能读到正文，但很快限流。所以公众号只做线索：`python3 scripts/discover_wechat.py` 把搜到的文章写进 `data/leads_wechat.json`（pending，人工确认官方页后再并入），不放进每日流水线，避免触发反爬。

---

## 每日流水线

```
抓取（各源 → candidates_*.json）      ← 平台 API + 官方活动站 + 人工核验
      ↓（公众号/小红书只进 leads.yaml 线索队列，拿到官方页才进候选）
verify.py：AI 过滤 → 两级去重 → 链接核验(200/301) → SQLite（保留 first_seen）→ races.json
      ↓
build_site.py：index + explore + organizers + match + guides + 详情页 + about + calendar.ics + feed.xml + agent.json + data/*.json
      ↓
send_digest.py：新收录 + 3 天内截止 → 邮件（附 calendar.ics）
      ↓
部署：GitHub Pages / Cloudflare Pages（免费）或本机 24×7（deploy/）
```

`verify.py` 的导出规则：`verify_state == "dead"` 的记录不导出；`unknown`（反爬拦截）保留但前台标注"待确认"。

`build_site.py` 的展示规则：
- 首页只放"在架 + 近 14 天结束"的赛事；已结束 14–90 天只保留详情页（长尾/SEO），超过 90 天整体下线；
- 排序：可报名的按截止日在前，已截止沉底；
- 每轮先清空 `site/race/*.html`，避免下线赛事留旧页。

---

## 公开数据与机器入口

对齐 AI 搜索/代理的读取习惯（参考 HackerTrip 的做法，但只做我们真正有的）：

| 入口 | 内容 | 说明 |
|---|---|---|
| `site/api/events.json` | 在架 + 近 90 天已结束赛事 | 顶层带 `count` / `updated` / `fields` 字段说明 / `license`；每条含 `status`、`ai_level`、`summary`、`directions`、`verified_at` |
| `site/api/events.md` | 同一份数据的 Markdown | 给 LLM / Agent 省 token |
| `site/data/hot.json` | 首页「本周值得看」 | 5 条编辑精选，含 `days`、`when`、`reason`；不是流量热度 |
| `site/data/races.json` | 全量核验数据 | 含已下线，供分析/存档 |
| `site/llms.txt` / `llms-full.txt` | 站点说明 / 完整 reference | 定位、入口、字段、核验语义、引用边界、Agent 调用建议 |
| `site/agent.json` / `.well-known/agent.json` | Agent 能力清单 | 只读：event_search / calendar / rss / explore / organizers / guides / match / llms_full |
| `site/calendar.ics` | 日历订阅 | 每场赛事 + 报名截止两个事件；Apple / Outlook / Google 均可订阅 |
| `site/feed.xml` | RSS 2.0 | 阅读器 / Agent 轮询；与 JSON 同源 |
| `site/explore.html` / `organizers.html` / `guides.html` / `match.html` | 浏览与筛选 | 方向/平台/级别/形式/状态 + 往届；主办方实体页；指南；本地规则匹配 |
| `site/sitemap.xml` | 站点地图 | 首页 + 全部详情 + 主办方 + 指南 |

单场详情页还提供「Google 日历 / 下载 .ics」和 schema.org `Event` JSON-LD；Agent 接入细节见 [docs/agent-integration.md](docs/agent-integration.md)。

许可：数据 CC BY 4.0（署名「AI 赛事雷达」）。部署后把 `SITE_URL` 设成正式域名，`llms.txt` / sitemap / feed 里的链接才会指向官方域名。

---

## 视觉与页面（Radar Room）

整站是「雷达室」双主题：默认跟随系统明暗（`prefers-color-scheme`），右上角 ◐ 可手动切换并记住选择。

- **深色**：底色 `#0b100d` 近黑绿，只用一种信号色（荧光绿 `#c9f73f`）+ 一种警示色（琥珀 `#ffb65c`）；强调色出现得越少越像仪表盘。
- **浅色**：纸白 `#f3f4ec` 底 + 深绿 `#3f6b00` 信号色，同一套排版、雷达与发丝线，白天阅读更轻松。
- **字体**：中文大标题用宋体（Songti SC / Noto Serif SC）做编辑感；所有数字、英文标签、编号用等宽（JetBrains Mono / SF Mono）；正文用系统 sans。无外部字体、无 JS 依赖，离线可用。
- **雷达**：首屏右侧同心圆 + 旋转扫描 + 脉冲光点，纯 CSS（`conic-gradient` + `@keyframes`），`prefers-reduced-motion` 下自动关闭。
- **列表**：不是卡片瀑布，是发丝线行式清单——序号 001、状态点、倒计时大数字、hover 左缘亮条；键盘/读屏语义仍是 `<a>`。
- **详情页**：左内容右核验（`VERIFICATION` 侧栏 sticky：链接状态 / 核验时间 / 收录时间 / 核验依据）。
- **关于 / 投稿**：编号章节的 prose 版式，模仿技术文档而不是营销页。

改视觉只需动两个文件：`scripts/theme.py`（CSS + JS）、`scripts/site_ui.py`（HTML 模板与文案）。

### 投稿入口

站内有 `site/submit.html`（表单无后端）：

- 有 `SUBMIT_EMAIL` 环境变量时：点「生成投稿」直接打开邮件客户端，收件人就是它；
- 没有时：按钮改为把整理好的内容复制到剪贴板，投稿人自己粘贴到微信 / 邮件。

```bash
SUBMIT_EMAIL=you@example.com python3 scripts/build_site.py
```

GitHub Actions 里把它设成仓库变量即可；同时建议开启 Issue 模板（`.github/ISSUE_TEMPLATE/submit-event.md`），让技术用户直接提 Issue。

---

## 部署（零成本起步）

### 方案 A：GitHub Pages（推荐，和自动更新天然配套）

1. 建仓库并 push 本项目；
2. Settings → Pages → Source 选 **GitHub Actions**；
3. 启用 `.github/workflows/daily.yml`：每天 UTC 00:00 自动核验 + 部署；
4. 自定义域名（可选）：Pages → Custom domain 填域名，DNS 加 CNAME 记录；
5. 设置仓库变量 `SITE_URL=https://你的域名`，让 sitemap / `.ics` / 邮件里的链接用正式域名（本地构建默认占位域名）。

### 方案 B：Cloudflare Pages

- 连接仓库，构建命令 `python3 scripts/build_site.py`，输出目录 `site`；
- 免费额度足够，国内访问通常比 GitHub Pages 好一点。

### 方案 C：自己服务器

- `site/` 是纯静态文件，rsync / nginx 直接托管即可；
- 想省心可用腾讯云轻量（¥60/月起）或 Vercel 免费额度。

---

## 邮件订阅

```bash
export SMTP_HOST=smtp.qq.com SMTP_PORT=465
export SMTP_USER=you@qq.com SMTP_PASS=授权码      # 不是登录密码
export DIGEST_TO=a@x.com,b@y.com                  # 或写进 data/subscribers.txt
python3 scripts/send_digest.py --days 2
```

- `--dry-run` 只写 `data/digest_preview.html`，不发信；先看样式再接 SMTP。
- Gmail 发信可换 `smtp.gmail.com:587`（STARTTLS）+ 应用专用密码；Resend / SendGrid 免费额度也可用。
- 邮件正文会附一份 `ai-race-radar.ics`，收件人可直接导入日历；站点「关于」页的订阅入口由 `SUBSCRIBE_URL`（表单）或 `SUBSCRIBE_EMAIL`（mailto）控制。

---

## 路线图

- [x] 本地流水线：核验 → 去重 → SQLite → 静态站 → `.ics`
- [x] 每日邮件摘要（新收录 + 即将截止）
- [x] GitHub Actions 定时核验与部署
- [x] sitemap.xml / robots.txt（便于搜索引擎收录）
- [x] 抓取自动化：天池 / 讯飞 / DataFountain / AI Studio / DoraHacks / 活动行 的采集器（已接入 `run_daily.sh` 与 Windows 包装器）
- [ ] 报名截止的 `.ics` 提前提醒（VALARM，截止前 3 天）
- [ ] 过期赛事自动归档（保留历史页，避免死链）
- [ ] 主办方投稿入口（GitHub Issue 模板 + 自动校验）
- [ ] 订阅者列表与退订（Resend audience / 自建）

## 成本

| 项目 | 费用 | 说明 |
| --- | --- | --- |
| 域名 `.com` | ¥70/年 | `.ai` 约 ¥600/年，起步建议 `.com` |
| 托管（Pages） | ¥0 | GitHub Pages / Cloudflare Pages |
| 定时任务（Actions） | ¥0 | 公开仓库免费额度足够 |
| 邮件（Resend 等） | ¥0 | 免费额度 100 封/天起 |
| 数据库 | ¥0 | SQLite 单文件 |
| **合计** | **≈ ¥70/年** | 境内访问提速再 +¥60/月（可选） |

## 命名候选

当前工作名 **AI 赛事雷达 / AI Race Radar**（域名建议 `airaceradar.com`、`airr.cn`）。
备选：赛雷达、AI 赛历（`aisaili.com`）、HackChina（偏黑客松）、AI 赛程（`aisaicheng.com`）。
原则：双拼优先、能口头说清、不蹭已有品牌。

## 免责声明

本站仅整理公开信息，不代收费用、不代办报名；赛事资格、奖金与规则均以主办方官方页面为准。
如主办方要求调整或下架，请提 Issue 或邮件联系，24 小时内处理。
