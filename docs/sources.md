# 信源目录（2026-11-06 实测）

本文件记录「AI 赛事雷达」接入了哪些源、哪些源可用但还没接、哪些源走不通。
所有结论都基于当天实际请求（HTTP 状态 / 能否解析出赛事），不是凭印象。

## 分层模型

| 层 | 含义 | 处理方式 |
|---|---|---|
| A 官方 API / JSON | 平台自己提供的结构化数据 | 直接解析，每日跑 |
| B 官方活动页（SSR/SPA） | 主办方自建活动站、平台活动列表页 | SSR 解析；SPA 需 headless 渲染 |
| C 人工核验 | 主办方官网/公众号里发现，人工确认后入 seeds | 每条必须实测 200，带 evidence |
| D 私域线索 | 小红书/公众号文章/群消息 | 只进 leads 队列，不直接上站 |

## 已接入（跑在 run_daily.sh 里）

| 源 | 入口 | 层 | 实测 | 说明 |
|---|---|---|---|---|
| 天池 | `tianchi.aliyun.com/v3/proxy/competition/api/race/page` | A | ✅ JSON | 17 条，详情 `/api/race/getDetail` |
| 讯飞开放平台 | `challenge.xfyun.cn/.../contests-list` | A | ✅ JSON | 需 UA+Referer+X-Requested-With，全量 672 条 |
| DataFountain | `datafountain.cn/api/competitions` | A | ✅ JSON | 分页封顶 10 |
| 百度 AI Studio | `aistudio.baidu.com/studio/match/list` | A | ✅ JSON | 分页参数是 `p` |
| DoraHacks | `dorahacks.io/api/v1/hub/hackathons` | A | ✅ JSON | 支持 `status=ongoing\|upcoming&search=AI` |
| 活动行 | `huodongxing.com/search?qs=黑客松` | B | ✅ SSR | 详情页内嵌 `var ativityJson` |
| 知乎活动站 | `hackathon-s3.event.zhihu.com/api/content` | B | ✅ JSON | 官方活动站，新增 `fetch_event_sites.py` |
| **魔搭 ModelScope 竞赛/活动** | `modelscope.cn/events` | B | ✅ SSR | **本次新增**；卡片含标题/类型/奖励/报名截止/状态，8 条在架，过滤「开发者沙龙/大会」后 6 条 |
| **和鲸 Heywhale** | `www.heywhale.com/v2/api/competitionsCommunity` | A | ✅ JSON | **本次新增**；全量 104 个赛事，过滤「已结束 + 2025 年前的往届」后 8 条 |
| **biendata** | `www.biendata.xyz/competition/` | B | ✅ SSR | **本次新增**；Ongoing/Coming 两个 tab 共 3 条，但英文 benchmark 标题命中 AI 关键词少（价值有限） |
| **公众号线索补全** | `sogou.com/web?query=<标题>` → 带签名 `mp.weixin.qq.com` 文章 | D 线索 | ⚠️ 限流 | 拿到签名链接时能读全文并抽正文外链；连续约 3 次触发反爬，脚本 2 条/轮 + 45 分钟冷却。Bing/Baidu 实测查不到中文原文 |
| **联谱 lianpu.com** | `lianpu.com/topics/<city>-ai` | D 线索 | ✅ SSR | 城市 AI 主题页内嵌 schema.org ItemList（每页 50 条，name+url）；报名多为扫码/私域，只进线索队列 `leads_lianpu.json` |
| **湾区 AI 日历 wqai.ltd** | `wqai.ltd/calendar/calendar.ics` | D 线索 | ✅ ICS | 「赛事」类条目是报名截止标记（⏰ 报名截止｜名称），可补库内 deadline 或进 `leads_wqai.json`；另有人工核验赛事库可参考 |
| **Luma 社区日历** | `api.lu.ma/ics/get?entity=calendar&id=<cal_id>` | A | ✅ ICS | **本次新增**；社区日历官方 ICS 导出（6 本 AI/黑客松社区日历），含标题/起止/地点/活动链接；`luma.com` 全站搜索无中国城市覆盖，只能按日历订阅 |

> 新增的三个源由 `scripts/collect_sources.py` 采集，产出 `data/candidates_extra.json`，与其它候选一起参与去重/核验。

## 可用但未接（按优先级）

| 源 | 入口 | 状态 | 为什么值得接 / 卡点 |
|---|---|---|---|
| 中国研究生创新实践系列大赛 | `cpipc.acge.org.cn` | SSR 313KB，可解析 | 教育部系列赛事，含 AI 相关主题赛；需解析赛事列表 + 详情 |
| 华为云大赛 | `competition.huaweicloud.com` | Angular SPA | 有 `/v5/noauth/competitions/detail/` 等接口，但列表接口未定位；需渲染或继续逆向 |
| 启智 OpenI | `openi.pcl.ac.cn` | 首页 200，`/competition` 404 | AI 协作平台，赛事入口路径待确认 |
| 火山引擎活动 | `volcengine.com/activities` | SPA，HTML 仅 67KB 壳 | 活动页需渲染/找 API |
| 开放原子大赛 | `competition.openatom.tech` | Vue SSR 首页只有赛程，无赛事列表 | 列表接口待找；开源类非纯 AI |
| 我爱竞赛网 | `52jingsai.com` | GBK 页面可读，搜索需 searchid | 赛事百科型，可做 D 层线索源 |
| 赛氪 | `saikr.com` | 首页 SPA 空壳（4.6KB） | 有 API 但需逆向，优先级低 |
| 开源之夏 | `summer.oschina.io` | SSL handshake 失败 | 年度开源活动，一年一次，价值一般 |
| 腾讯云开发者竞赛 | `cloud.tencent.com/developer/competition` | SSR 正常 | 20 个面板全部标记已结束（--end），不接 |

## 明确走不通 / 不适合

| 源 | 实测 | 结论 |
|---|---|---|
| Rokid 赛事平台 | SPA；`rcs.rokid.com/space-api/api/front/race/list` 返回 `{"code":1002,"message":"Please sign in first"}` | 公开 API 需登录；只能 headless 渲染或人工核验（当前 Spatial Joy 2026 走 curated 种子） |
| 微信公众号 | 搜狗微信搜索只有标题/摘要，`/link?url` 一律 302 antispider；直接打开文章是「环境异常」验证页 | 只能当线索源（`discover_wechat.py`），不能当数据源 |
| 小红书 | 登录墙 | 只能人工提供线索 |
| 知乎问题/文章 | 登录墙/反爬 | 同上 |
| 智源 hub | 首页无赛事聚合 | 不接 |
| 摩尔线程 / 中国创新创业大赛官网 | 503 / 代理不通 | 暂不接 |
| 高校「互联网+」「挑战杯」「创客中国」等创业类大赛 | SSR 可读 | 非 AI 专项、且多为校级/省级过程赛，噪声大，先不接 |

## 厂商官方赛事站（B 层，人工/低频）

厂商自建赛事页是最容易漏的一类（不在任何平台 API 里，SEO 也弱）。当前做法：

- 已收录：Rokid Spatial Joy 2026（`spatialjoy.rokid.com/2026`，curated，证据里写明渲染核验）
- 待巡检名单：Rokid、雷鸟 RayNeo、XREAL、宇树 Unitree、摩尔线程、智谱、Kimi、MiniMax、阶跃、百川、商汤、NVIDIA、高通、小米/OPPO/vivo/荣耀/联想等
- 巡检方式：按季度（或用户提供线索时）用 `Chrome --headless --dump-dom` 渲染官方页 → 人工确认 → 写入 `data/seeds.yaml`；单页 DOM 提取可用 `scripts/cdp-shot.mjs` 同类方式
- 不放进每日流水线的原因：SPA 渲染在 CI 上成本高、且多数厂商一年只办 1–2 次

## 扩充信源的判断标准

1. 能不能稳定拿到**官方报名链接**（不是聚合站二传）？
2. 能不能拿到**报名截止日**（没有截止日的比赛对用户价值减半）？
3. 更新频率与维护成本：JSON API > SSR 列表 > SPA 渲染 > 公众号线索。
4. 只收 AI 相关：平台赛看题目/赛道，泛赛事看 AI 赛道证据（见 about 页「收录口径」）。
