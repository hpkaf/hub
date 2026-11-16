# Agent / 自动化接入

本站是纯静态站，**没有写接口**；所有数据都能用 GET 读取，适合 AI Agent、RSS 阅读器、脚本和日历客户端。

## 入口

| 入口 | 类型 | 适合 |
|---|---|---|
| `/api/events.json` | JSON | Agent / 脚本；在架 + 近 90 天记录，含字段说明 |
| `/api/events.md` | Markdown | 给 LLM 的省 token 版本 |
| `/data/hot.json` | JSON | 首页「本周值得看」5 条；含 `days`、`when`、`reason`，不是流量榜 |
| `/calendar.html` | HTML | 人类一键订阅（Apple / Outlook / Google / 邮箱） |
| `/calendar.ics` | iCalendar | 底层日历 feed，Apple / Outlook / Google 订阅 |
| `/feed.xml` | RSS 2.0 | 阅读器、Agent 轮询 |
| `/llms.txt` / `/llms-full.txt` | 纯文本 | 站点说明 / 完整 reference（字段、核验语义、引用边界） |
| `/agent.json` / `/.well-known/agent.json` | JSON | Agent 能力清单（只读，无鉴权） |
| `/explore.html` / `/organizers.html` / `/guides.html` / `/match.html` | HTML | 人类浏览；Agent 可抓 HTML，但优先用 JSON/Markdown |

单场详情页另有「Google 日历 / 下载 .ics」按钮，以及 schema.org `Event` JSON-LD。

## Agent manifest

```json
{
  "name": "AI 赛事雷达",
  "authentication": {"type": "none"},
  "capabilities": [
    {"name": "event_search", "endpoint": "…/api/events.json"},
    {"name": "event_markdown", "endpoint": "…/api/events.md"},
    {"name": "calendar", "endpoint": "…/calendar.ics"},
    {"name": "rss", "endpoint": "…/feed.xml"}
  ]
}
```

完整清单见 `/agent.json`；`match.html` 是浏览器本地规则匹配，不提供 API 打分。

## JSON 结构

```json
{
  "site": "AI 赛事雷达",
  "updated": "2026-11-08T12:43:22Z",
  "count": 68,
  "fields": {"deadline": "报名截止 ...", "...": "..."},
  "events": [
    {
      "id": "04ea79cafa53",
      "title": "2026全国大数据与计算智能挑战赛",
      "organizer": "和鲸 Heywhale",
      "mode": "online",
      "start_date": "2025-12-31",
      "end_date": "2027-01-30",
      "deadline": null,
      "status": "open",
      "ai_level": "other",
      "url": "https://...",
      "verified_at": "2026-11-08T20:54:21",
      "verify_code": 200
    }
  ]
}
```

关键字段：

- `status`：`open` / `closing`（≤7 天）/ `upcoming` / `closed` / `unknown`
- `ai_level`：`core` / `platform` / `track` / `other`
- `deadline`：可能为 `null`，页面上显示「待确认」；不要自己猜
- `url`：官方报名 / 详情页，已实测可打开
- `registration_closed`：官方明确关闭报名时为 `true`

## 常用过滤

```bash
# 还能报名的（推荐）
curl -s http://192.168.1.3:8080/api/events.json \
  | jq '.events[] | select(.status == "open" or .status == "closing")
        | {title, deadline, url}'

# 7 天内截止
curl -s http://192.168.1.3:8080/api/events.json \
  | jq --arg today "$(date +%F)" \
    '.events[] | select(.deadline != null and .deadline >= $today)
     | {title, deadline, url}'
```

## 放进日历

- **订阅全部**：`https://race.howfun.cn/calendar.ics`；Apple 日历可直接打开
  `webcal://race.howfun.cn/calendar.ics`；Google 日历「其他日历 → 通过网址添加」。
- **一键入口**：`https://race.howfun.cn/calendar.html`，含 Apple / Outlook / Google 按钮和邮箱收链接。
- **只加一场**：详情页「Google 日历」按钮，或下载同目录的 `<id>.ics`。
- **邮件**：`send_digest.py` 发出的摘要邮件附带 `ai-race-radar.ics`，收件人可直接导入。

## 给 Agent 的提示词示例

> 读取 `https://race.howfun.cn/api/events.json`，筛出 `status` 为 `open` 或 `closing`
> 且 `deadline` 非空的 AI 赛事，按截止日排序；对每条给出标题、截止日、官方链接，
> 并把这些赛事加入我的日历。不要编造 `url`，报名前以官方页面为准。

## 邮件订阅（可选）

静态站不收集邮箱。两种接法：

1. `SUBSCRIBE_URL`：填 Tally / Buttondown / 金数据等表单地址，站点「关于」页会出现订阅入口；
2. `SUBSCRIBE_EMAIL`：填收件邮箱，站点出现 `mailto:` 订阅入口，人工把地址加进
   `data/subscribers.txt`。

配好 `SMTP_*` 后，`send_digest.py` 每天发「新收录 + 3 天内截止」，并附日历文件。

## 注意

- 不要高频轮询：数据每天 08:00 更新一次，建议 1–6 小时间隔。
- 所有报名、资格、奖金以 `events[].url` 官方页面为准。
- 如需 MCP / 函数调用封装，可直接基于 `/api/events.json` 做一个只读工具；本站不提供写操作。
