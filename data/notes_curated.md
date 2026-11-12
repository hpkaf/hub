# 种子数据策展笔记（curator · 2026-11-06）

## 1. 本次交付概览

- 输出文件：`data/seeds.yaml`，共 **20 条**人工核验赛事（全部为 2026-10 ~ 2026-12 窗口内、截至 2026-11-06 仍可报名或赛程正在进行/即将举行的中国 AI 相关赛事）。
- 形式分布：**线上 14 条（70%）、线下 3 条（15%）、线上+线下混合 3 条（15%）**，符合「线上优先，可少量一线城市线下」的要求。
- 每条 `url` 均已用 `web_fetch` 实测返回 **HTTP 200**（个别平台页正文由 JS 渲染，仅能验证官方入口可打开；赛事事实以 `source_url` 页面文案为证，已写入 `evidence`）。
- 未达到 30–40 条，原因与补足建议见第 5 节。宁可少而全真，未编造任何赛事名 / 链接 / 奖金 / 日期。

## 2. 检索路径（按效率排序）

1. **魔搭 ModelScope 活动列表** `https://modelscope.cn/events`：SSR 渲染，页面上直接给出「进行中」状态、类型、奖励、报名截止、地点，是本轮最可靠的官方一手来源。详情页 `/events/<id>` 为 JS 空壳，故只能以列表页作为 `source_url`，详情页作为 `url`（均 200）。分页为 JS 渲染，`?page=2` / `?pageNum=2` 无效，无法翻到第 2 页。
2. **WaytoAGI Events 活动平台** `https://events.waytoagi.com/` + 公开 JSON API `https://events.waytoagi.com/api/events`（llms.txt 中声明的免鉴权接口）：结构化给出标题、时间、城市、形式、主办方、报名跳转链接。11 月→12 月在招活动共 7 场（其余 129 场为已结束的 7-10 月活动）。
3. **天池** `https://tianchi.aliyun.com`：赛事入口页（`/competition/entrance/<id>`）与专题页为 JS 空壳，但官方入口本身 200 可验证；赛事事实（主办、奖金、截止）从 AI 活动雷达详情页补全。
4. **AI 活动雷达** `https://airadar.laifuyou.com/zh`：57 条聚合机会，中文条目约 15 条，详情页 SSR 完整（标题/主办/官方入口/奖励/时间节点/来源），用于补官方 URL；其「X 天截止」字段不可靠（多处与真实时间节点矛盾），只作线索，不直接采信。
5. **官方赛站直查**：开放原子大赛 `competition.openatom.tech`、讯飞 `challenge.xfyun.cn`、华为云/华为开发者、火山引擎活动页、liblib（海南岛 AI 电影展官方征片平台）、SMP2026 官网、腾讯开悟、百度 CTI。
6. **搜索**：`web_search` 用于发现新赛源（强网杯、江苏黑客松、B站 AI 创造公开赛、腾讯视频火龙 AIGC 黑客松等），但微信文章/公众号页多触发验证码、高校通知为 PDF/内网，官方页未能核验的不收录。

## 3. 信源清单（实际打开过的页面）

- 魔搭活动列表：`https://modelscope.cn/events`
- WaytoAGI Events：`https://events.waytoagi.com/`、`https://events.waytoagi.com/api/events`、`https://events.waytoagi.com/llms.txt`、活动详情页与报名官网 `https://resonance.waytoagi.com/`
- AI 活动雷达：`https://airadar.laifuyou.com/zh`、`/zh/archive`、`/zh/categories` 及中文条目详情页（TRAE、C4-AI、华为云具身智能、AFAC2026、阿里云 Data+AI、讯飞星火杯、KDD Cup 2026、全民 AI 创作、超级智能体、复杂工业异常检测、鸿蒙应用开发者激励计划、天工计划、iFLYTEK 星火杯等）
- 开放原子大赛：`https://competition.openatom.tech/`、`https://competition.openatom.tech/competition`（列表 JS 空壳）、单个赛项页 `/competitionInfo?id=d83eb10e091c841c71230ad8ecb809fe`
- 天池：`https://tianchi.aliyun.com/competition/entrance/532489`（AFAC2026）、`532482`（工业异常检测）、`532511`（SMP2026）、`532514`（蚂蚁灵波）、`https://tianchi.aliyun.com/specials/promotion/ai2026`
- 华为：`https://developer.huaweicloud.com/competition/information/1300000267`、`https://developer.huawei.com/consumer/cn/activity/incentive/ai`、`https://developer.huawei.com/home/C4-AI`
- 讯飞：`https://challenge.xfyun.cn/competition`、`https://challenge.xfyun.cn/xinghuo`
- 其他官方站：`https://www.volcengine.com/activity/agent/competition/2026`、`https://www.liblib.tv/hiiff-aifilmseason`、`http://smp2026.cips-smp.org/ji-shu-ping-ce`、`https://goaihz.com`、`https://www.cnmaker.org.cn/...`、`https://tencentarena.com/aiarena/en/match/open-competition-2026`、`http://cti.baidu.com/`、`https://www.oschina.net/oa2026/`
- 媒体/通知（仅线索）：量子位（B站 AI 创造公开赛）、科技日报（第三届兴智杯）、央广网/新浪（2026 讯飞 1024）、高校通知（蓝桥杯 2027、传智杯、江苏 AI+ 黑客松）、微信公众号（强网杯青少年 AI 专项赛）

## 4. 失效 / 存疑 / 未收录（附原因）

### 4.1 已过期（2026-07 ~ 2026-10 截止或已结束，不进种子）

| 赛事 | 关键时间 | 官方页/线索 |
|---|---|---|
| TRAE AI 创造力大赛（字节） | 报名+初赛 6/16–7/15，决赛 8/22 | https://forum.trae.cn/c/38-category/39 |
| C4-AI 中国高校计算机大赛-人工智能创意赛 2026（华为） | 校赛报名截止 7/15 | https://developer.huawei.com/home/C4-AI（200）、https://developer.huaweicloud.com/c4ai.html |
| 首届超级智能体大赛 2026（广州市 AI 产业办） | 报名截止 7/31，决赛 11 月下旬 | https://www.gz.gov.cn/zwfw/zxfw/kjcy/content/post_10862954.html |
| 讯飞星火杯大模型应用创新赛 2026 | 初赛 8/13、复赛 9/13、总决赛 10/23–24 | https://challenge.xfyun.cn/xinghuo（200） |
| KDD Cup 2026 Tencent UNI-REC Challenge | 2026-07-31 截止 | https://algo.qq.com/ |
| 2026 腾讯开悟人工智能全球公开赛（服创大赛 D 类） | 报名 2–3 月、比赛 4–8 月、8 月颁奖 | https://tencentarena.com/aiarena/en/match/open-competition-2026（200） |
| 2026 百度商业 AI 技术创新大赛 | 7 月已收官 | http://cti.baidu.com/（200，页面写明「圆满收官」） |
| 2026 全民 AI 创作大赛 | 作品征集 5/22–8/31 | 腾讯新闻页（聚合页官方入口） |
| 首届蚂蚁灵波具身大模型挑战赛 | 活动日 2026-10-26 已结束 | 天池 532514 |
| 第四届开放原子大赛—2026 开源行业解决方案创新赛 | 报名 10/31 截止，决赛 11/13 北京 | https://www.oschina.net/oa2026/（200）、官方赛项页 |
| ClawHunt 上海黑客松 | 2026-10-30 ~ 11-01 已结束 | https://clawhunt.store/（WaytoAGI 列表） |
| 百度 AI Studio 竞赛列表 / 天池比赛列表 | 页面仅 logo/框架空壳，无法枚举在招赛事 | https://aistudio.baidu.com/competition、https://tianchi.aliyun.com/competition |

### 4.2 存疑（事实不完整，暂不收录）

- **B站「build in bilibili · AI 创造公开赛」第二赛季**：2026-10-24 启动、奖金池最高 220 万现金、含 NVIDIA RTX Spark / Google 出海单元（量子位报道 200）。官方活动规则页 `https://www.bilibili.com/opus/1210076034617049096` 触发验证码，活动报名页未定位 → 缺 `url` 官方报名页，未收录。
- **GOAI 2026 世界人工智能开源大赛**：官网 `https://goaihz.com` 仅渲染标题「世界人工智能开源大赛」，AI for Research 赛道「报名中」来自搜索摘要，缺赛程/奖金/截止事实 → 未收录。
- **鸿蒙应用开发者激励计划 2026**：仅有 ithome 报道页（聚合页官方入口指向媒体而非华为官方），官方报名页未确认 → 未收录。
- **2026 科大讯飞 1024 开发者节**：2026-10-22 已举办（央广网/新浪），非在招赛事。
- **高校师生 3 个月 Pro 权益（Qoder Work）**：权益型福利，非赛事。
- **强网杯青少年 AI 应用专项赛（第十届）**、**2026 江苏省 AI+科学与工程创新实践黑客松**、**第三届 CCF 算法能力大赛（CACC）区域赛**、**第十八届蓝桥杯（2027）**、**第九届传智杯**、**第十一届创客中国智能体与具身智能赛**、**第三届兴智杯**、**中国研究生创新实践系列大赛**：均有搜索线索，但官方报名页为微信（验证码）/PDF/JS 空壳/未定位，未通过「官方页 200 + 事实核验」标准 → 全部记入待补。
- **腾讯视频火龙 AIGC 黑客松**（48h 现场、120 万现金）：来源为 deepseek.club 活动页（JS 空壳），官方页未定位 → 未收录。
- **和鲸 GENESIS 黑客松**（$20K，7/5 截止）、**Intel AI PC 征文/OpenClaw 技能挑战**：过期 / 平台页空壳，未收录。

### 4.3 已知数据局限

- 魔搭 8 条均来自同一列表页，因详情页 SSR 空壳，`start_date/end_date` 只能为 null，`organizer` 只能取标题中明确主体；`mode` 按平台活动类型推断（列表标注「开发者线下沙龙」的 DDC 记为 offline，其余记为 online），已在 evidence 中保留原文依据。
- 天池/华为云/火山引擎/讯飞平台页正文为 JS 渲染，只能验证官方入口可打开；奖金与截止时间来自聚合页或官网标题，`deadline` 拿不到确切日期时置 null，未用聚合页不可靠的「X 天截止」倒推日期。
- `AI 活动雷达` 的「X 天截止」与真实时间节点冲突（如 TRAE 显示「3 天截止」但实际 7/15 已截止），因此只把它当线索源，日期以官方/活动页/时间节点原文为准。

## 5. 覆盖率判断与补足建议

- **覆盖率**：截至 2026-11-06，能在官方源上核验「仍在报名/进行中」的中国 AI 赛事约 20 条，已全部收录；AI 活动雷达 57 条中中文在招条目约 15 条（多数已过期），魔搭在招 8 条全部收录，WaytoAGI 11–12 月在招 7 场收录 3 条（其余为大会/聚会/已截止）。
- **未达 30–40 条的主因**：① 11 月初是 Q4 赛季节奏低谷，大量赛事（TRAE、C4-AI、腾讯开悟、百度 CTI、讯飞星火杯、全民 AI 创作等）已在 7–10 月截止；② 国内赛事主阵地（天池、AI Studio、开放原子 /competition、微信公众平台）大量使用 JS 渲染或验证码，无法枚举在招赛项；③ 30 分钟时间盒内优先保证「每条可核验」，未扩散到低置信度来源。
- **可在下一轮补足的方向**（均已找到入口，预计 10–15 条）：
  1. 开放原子大赛按赛项枚举（`/competition` 需 JS，可搜 `competitionInfo?id=` 或官方公众号），当前在招赛项可能不止 1 个；
  2. 天池比赛列表（可尝试官方 API/搜索 `tianchi.aliyun.com/competition/entrance/<id>` 的 5324xx–5325xx 段）；
  3. 赛氪、我爱竞赛网、活动行、高校竞赛通知聚合（蓝桥杯 2027、传智杯、CACC、兴智杯、研创赛）；
  4. B 站、小红书、腾讯视频、字节 TRAE 新赛季官方活动页（需处理验证码/JS）；
  5. WaytoAGI 每周新增活动（有公开 JSON API，适合做成每日增量）。

## 6. 备注

- 本文件与 `data/seeds.yaml` 是本次仅有的两个写文件，未改动 `scripts/`、`site/`、`data/candidates_*.json`、`data/raw/` 等他人文件。
- 时间盒：2026-11-06 15:39 开始，约 16:15 完成（略超 30 分钟，主要花在官方 URL 逐个 `web_fetch` 核验与 JS 空壳排查）。
