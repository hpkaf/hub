# 代码 ↔ 文档一致性核对报告

- 核对对象：`ai-race-radar-2026-11-08.tar.gz` 解压后的代码与数据
- 对照文档：`PROJECT-OVERVIEW.md`（V1.0，数据快照 2026-11-08），并抽查 `README.md`、`INSTALL.md`、`docs/sources.md`
- 方法：逐脚本阅读 + 用 `data/races.json`、`site/` 产物、SQLite 账本做数字对账 + 在本机 Python 3.11 上实跑
- 结论：**数据快照与文档高度吻合；但「每日流水线」的代码实现与文档描述有明显缺口，另有 3 个会直接导致 24×7 运行失败/丢数据的问题。以下 P0 已修复，P1/P2 的文档口径问题记录待定。**

---

## 1. 核对结果总览

### 1.1 与文档一致的部分（解压时快照）

| 指标 | 文档 | 实测 |
|---|---|---|
| 全量记录 / 活链 | 79 / 79 全部 200 | 79 / 79，`verify_code` 全为 200 |
| 首页在架 | 45 场 | 45 场（open 24 + closing 4 + upcoming 2 + unknown 11 + 近 14 天 closed 4） |
| 详情页 + 存档 | 70 个 | 70 个 |
| 主办方 | 全量 43 / 首页 28 | 43 / 28 |
| AI 分级 | core 42 / platform 24 / track 7 / other 6 | 完全一致 |
| 状态分布 | open 24 / closing 4 / upcoming 2 / unknown 11 / closed 38 | 完全一致 |
| 形式分布 | 线上 57 / 线下 11 / hybrid 4 / 未知 7 | 完全一致 |
| Luma 日历 | 6 本 | 6 本 |
| 联谱 / 湾区线索 | 14 / 6 | 14 / 6 |
| 站点产物 | 首页 + 70 详情 + about + submit + ics + feed + llms + sitemap | 数量一致（ics 53 个 VEVENT、sitemap 73 个 loc） |

> 说明：以上为**解压后、跑流水线前**的状态；跑完后因一条 DoraHacks 赛事从信源消失，账本按规则清理由 79 → 78，属于正常时效清理，不是缺陷。

### 1.2 发现的问题

| # | 严重度 | 文档说法 | 代码/实际 | 影响 | 处理 |
|---|---|---|---|---|---|
| 1 | **P0** | `PROJECT-OVERVIEW` §5/§7、`docs/sources.md`：天池/讯飞/DataFountain/AI Studio/DoraHacks/活动行 **✅ 每日**，且「已接入（跑在 run_daily.sh 里）」 | `run_daily.sh` 只调用 `fetch_event_sites / collect_sources / collect_luma / lianpu / wqai / enrich`，**完全没有调用** `fetch_tianchi / fetch_xfyun / fetch_datafountain / fetch_aistudio / fetch_dora / fetch_hdx`；`candidates_comp.json`、`candidates_hack.json` 停留在 11-06 | 6 个 A 层平台源实际不更新，站点会逐渐只剩旧赛事；文档的「11 个自动源每日跑」不成立 | **已修**：`run_daily.sh`、`.github/workflows/daily.yml`、`deploy/run_daily.ps1` 均补齐 6 个采集器 |
| 2 | **P0** | `INSTALL.md` §8：某一步抓取失败会「沿用上一次的候选数据」 | `fetch_event_sites` / `collect_sources` / `collect_luma` 在抓取失败但未抛异常时会**用空数组覆盖**旧候选；随后 `verify.py` 以 `run_start` 清理 `last_seen` 更早的记录 → 一次网络抖动可清掉大部分账本（seeds 21 条除外） | 24×7 无人值守时的数据丢失风险 | **已修**：① 三个采集器失败时保留上一轮候选（按 source / calendar 粒度）；② `verify.py` 清理前增加阈值——候选数 < max(10, 库内 60%) 时跳过清理并告警 |
| 3 | **P0** | `INSTALL.md` §1：Python 3.10+ | `scripts/site_ui.py` 的 `head()` 用了 f-string 内反斜杠（`f'...{" class=\"on\"" ...}'`），**Python 3.11 直接 SyntaxError**，本机无法建站；CI 用 3.12 才没暴露 | Windows 本机（3.11.9）流水线在最后一步失败 | **已修**：改为 `str.format()`，并用 `python -m compileall scripts` 验证 3.11 全通过 |
| 4 | **P1** | §10 / README：`/data/races.json` 是「全量数据（含已下线）」 | `build_site.py` 写 `site/data/races.json` 时用的是**已按 90 天过滤**的 70 条，不是 79 条全量 | 对外承诺的存档数据缺 9 条 | **已修**：`build_site.py` 单独保存 `full_records`（当前 78 条）到 `site/data/races.json` |
| 5 | **P1** | §6 数据模型列出 `ai_level` | 实际 `data/races.json` 没有 `ai_level` 字段，只在建站时计算 | 公开数据与文档字段表不一致；订阅者拿不到分级 | **已修**：`verify.py` 导出时写入 `ai_level` |
| 6 | **P1** | §4：「判断依据是官方页的赛道/题目/技术栈，**而不是标题**」 | `ai_level()` 的 `core` 明确按**标题**强关键词判定，`platform` 按平台，`track` 才看 tracks | 文档自相矛盾（同节表格又写 core 看「标题/主题」） | **未改代码**（现有逻辑合理），建议把这句话改为「core 看标题，track 看赛道证据」 |
| 7 | **P2** | §9：「在架清单中约 11 条截止时间待确认」 | 首页 45 条中 `deadline=null` 的有 **26 条**，扣除 4 条已截止，**22 条前台显示「待确认」**；11 是 `status=unknown` 的条数 | 读者会低估待补数据量 | 建议改文档口径（或单独统计「无 deadline 且未截止」） |
| 8 | **P2** | §7：`seeds.yaml`（**22 条**） | 实际 21 条（`load_yaml` 解析与行数统计均为 21） | 数量口径差 1 | 建议改文档 |
| 9 | **P2** | §9：公众号线索 20（**待补 16**） | 实际 pending 15（跑完补全后 13） | 数量口径 | 建议改文档 |
| 10 | **P2** | §7：「当前已接入 **11 个**」，但表格列了 15 行 | 11 个指「自动源」（10 个 A 层 + Luma）；`races.json` 里实际出现的 source 只有 10 个（modelscope / biendata 采集到了候选，但过滤后 0 条进库） | 容易误读覆盖率 | 建议拆成「自动源 11 / 半自动与线索 4」并注明 0 条源 |
| 11 | **P2** | §7、`sources.md`：湾区日历「可补库内截止日」 | `collect_wqai.py` 只写 `data/wqai_deadline_fill.json`，**没有任何代码读取并应用**；本次该文件为 `[]` | 功能承诺未闭环，只能人工合并 | 建议在 `verify.py` 应用 fill，或把文案改为「输出待人工合并」 |
| 12 | **P2** | — | `enrich_wechat_leads.py` 注释「优先白名单、再按发布新→旧」，实际 sort 把白名单放后面、旧日期优先 | 补全顺序与设计相反 | **已修**（改为 `(in whitelist, date)` 降序） |
| 13 | **P2** | — | 详情页「数据来源」映射缺 modelscope / heywhale / biendata，页面直接显示英文 source id | 展示不统一 | **已修**：补全 `SRC_LABEL` |
| 14 | **信息** | `INSTALL.md`：Windows 仅建议 WSL，任务计划用 Git Bash 跑 `.sh` | 本机是原生 Windows 10 + Python 3.11，无 WSL | 官方没有 Windows 原生部署路径 | **已补**：`deploy/*.ps1` + `docs/windows-24x7.md` |
| 15 | **P2** | §14 / README：「深色/浅色自适应」 | `theme.py` 只有一套近黑主题，没有任何浅色媒体查询或切换入口 | 用户反馈「页面有点暗」时无法切到浅色 | **已修**：新增纸白浅色主题（`prefers-color-scheme` 自动跟随 + 右上角 ◐ 手动切换 + 本地记忆） |
| 16 | **P1** | `.env.example`：`DIGEST_FROM=AI 赛事雷达 <digest@...>` | `send_digest.py` 把这个完整字符串再塞进 `formataddr`，中文地址触发 `UnicodeEncodeError`，邮件摘要实际发不出去 | 配好 SMTP 也发不了信 | **已修**：用 `parseaddr` 拆显示名/裸地址，envelope 用裸地址；摘要另附 `calendar.ics` |

---

## 2. 修复清单（本次改动）

| 文件 | 改动 |
|---|---|
| `run_daily.sh` | 增加 6 个平台采集器（天池/讯飞/DF/AI Studio/Dora/活动行），失败仅 warn |
| `.github/workflows/daily.yml` | 同上，新增「抓取平台源」步骤 |
| `scripts/verify.py` | ① 清理阈值防误删；② 导出增加 `ai_level` |
| `scripts/collect_sources.py` | 单个源失败时保留该源上一轮候选（按 source 粒度合并） |
| `scripts/fetch_event_sites.py` | 所有活动站都失败时不覆盖 `candidates_events.json`，返回非 0 让包装器记 WARN |
| `scripts/collect_luma.py` | 失败/跳过的日历保留上一轮候选（按 calendar slug 粒度合并） |
| `scripts/build_site.py` | `site/data/races.json` 改为全量（含 90 天外存档） |
| `scripts/site_ui.py` | ① 修 Python 3.11 f-string 语法错误；② 补齐 source 中文名；③ 页头加主题切换按钮与首屏防闪烁脚本；④ CSS/JS 加构建版本号避免缓存；⑤「方法」移出主导航；⑥ 详情页加 Google 日历 / 单场 .ics / JSON-LD；⑦ 「关于」页加订阅与 Agent 入口 |
| `scripts/theme.py` | 新增浅色主题（系统偏好自动 + 手动切换），深色底色略微提亮；所有硬编码色改为 CSS 变量；新增 `.cta-note`、`.prose code` |
| `scripts/build_site.py` | 新增单场 `.ics`、`feed.xml`（RSS）、llms 的 Agent 段落；ICS 生成重构为可复用函数 |
| `scripts/serve_site.py` | 新增静态服务：`.ics` 返回 `text/calendar`，`.json`/`.xml` 显式 UTF-8 |
| `scripts/send_digest.py` | 修 `DIGEST_FROM` 中文显示名崩溃；摘要邮件附 `ai-race-radar.ics` |
| `scripts/common.py` | ① 启动时读取项目根 `.env`（已存在环境变量优先），单独跑脚本也能拿到 `SITE_URL`；② DNS 解析结果 IPv4 优先，规避 Luma 在无 IPv6 出口网络上的长时间假死 |
| `scripts/enrich_wechat_leads.py` | 修正线索排序方向 |
| `deploy/run_daily.ps1` | Windows 每日流水线：补齐平台源、每步超时（默认 300s / Luma 180s / 核验 1200s）、备份 DB、日志轮转、.env/Python 定位 |
| `deploy/serve.ps1` | Windows 常驻静态服务：崩溃 5 秒重启、日志轮转 |
| `deploy/install.ps1` / `uninstall.ps1` / `status.ps1` | 计划任务、防火墙、状态速查 |
| `docs/windows-24x7.md` | 原生 Windows 24×7 部署手册 |

### 2.1 实跑发现（不是文档对不上，但会影响 24×7）

| 现象 | 原因 | 处理 |
|---|---|---|
| `collect_luma.py` 卡 10 分钟以上 | `api.lu.ma` 的 IPv6 地址在无 IPv6 出口的网络上进入 `SYN_SENT`，Windows 下 socket 超时不生效；同期 IPv4 也可能被限流 | ① `common.py` 把 DNS 结果改为 IPv4 优先；② PowerShell 包装器给每步加硬超时（Luma 180s），超时杀进程并沿用上一轮候选 |
| `fetch_dora.py` 偶发 `SSL: UNEXPECTED_EOF_WHILE_READING` | DoraHacks 侧 TLS 抖动 | 非致命，包装器记 WARN 继续；候选文件在写盘前退出，不会清空 |
| SYSTEM 计划任务下日志中文乱码 | PowerShell 捕获 native stdout 时按控制台代码页解码 | 改为 `ProcessStartInfo` + `StandardOutputEncoding=UTF8` 直接读原始输出 |
| `.ps1` 中文导致语法错误 | Windows PowerShell 5.1 对无 BOM 的 UTF-8 按 ANSI 解析 | `deploy/*.ps1` 统一保存为 **UTF-8 with BOM**；改脚本时注意保持 |

---

## 3. 复核方式

```powershell
cd E:\AI赛事\ai-race-radar

# 语法 / 兼容性
python -m compileall -q scripts

# 数据对账（与本文 1.1 同口径）
python scripts\verify.py --no-verify   # 只读候选、不联网，检查载入/去重
python scripts\build_site.py

# 站点自检
powershell -ExecutionPolicy Bypass -File deploy\status.ps1
```

> 注意：日常运行后条数会变化（新收录、信源下线、90 天清理），1.1 的数字是 2026-11-08 解压快照，不是恒定值。
