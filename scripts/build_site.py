#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 data/races.json 生成为静态站点（视觉层见 scripts/theme.py 与 scripts/site_ui.py）。"""
from __future__ import annotations

import datetime as dt
import email.utils
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common  # noqa: E402
import hot as hotmod  # noqa: E402
import organizers  # noqa: E402
import pages_extra  # noqa: E402
import summaries  # noqa: E402
import taxonomy  # noqa: E402
import guides_content  # noqa: E402
from theme import APP_JS, STYLE  # noqa: E402
from site_ui import (SITE, SITE_DESC, SITE_NAME, foot, head, render_about,  # noqa: E402
                     render_detail, render_index, render_submit)

RACES_PATH = os.path.join(common.DATA_DIR, "races.json")

# ---------------------------------------------------------------- ICS
def ics_escape(text: str) -> str:
    return (str(text or "").replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def ics_fold(line: str) -> str:
    """RFC 5545：每行不超过 75 字节，超长折行。"""
    out, buf, size = [], "", 0
    for ch in line:
        b = len(ch.encode("utf-8"))
        if size + b > 73:
            out.append(buf)
            buf, size = " " + ch, 1 + b
        else:
            buf += ch
            size += b
    out.append(buf)
    return "\r\n".join(out)


def ics_calendar_header(cal_name: str) -> list[str]:
    return ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//AI Race Radar//CN//ZH",
            "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
            f"X-WR-CALNAME:{cal_name}", "X-WR-TIMEZONE:Asia/Shanghai"]


def ics_vevent_lines(rec: dict, stamp: str) -> list[str]:
    """单场赛事 + 报名截止两个 VEVENT；没有日期时返回空列表。"""
    start = rec.get("start_date") or rec.get("deadline")
    if not start:
        return []
    try:
        d0 = dt.date.fromisoformat(start)
    except ValueError:
        return []
    end = rec.get("end_date") or start
    try:
        d1 = dt.date.fromisoformat(end) + dt.timedelta(days=1)
    except ValueError:
        d1 = d0 + dt.timedelta(days=1)
    desc = "；".join(part for part in [
        f"主办方：{rec.get('organizer')}" if rec.get("organizer") else "",
        f"报名截止：{rec.get('deadline')}" if rec.get("deadline") else "",
        f"奖金：{rec.get('prize')}" if rec.get("prize") else "",
        f"报名：{rec.get('url')}",
        f"收录：{SITE_NAME}（{rec.get('verified_at') or ''} 核验）",
    ] if part)
    loc = "线上" if rec.get("mode") == "online" else (rec.get("city") or "")
    lines = ["BEGIN:VEVENT",
             f"UID:{rec['id']}@ai-race-radar",
             f"DTSTAMP:{stamp}",
             f"DTSTART;VALUE=DATE:{d0.strftime('%Y%m%d')}",
             f"DTEND;VALUE=DATE:{d1.strftime('%Y%m%d')}",
             f"SUMMARY:{ics_escape(rec.get('title'))}",
             f"DESCRIPTION:{ics_escape(desc)}",
             f"URL:{rec.get('url')}"]
    if loc:
        lines.append(f"LOCATION:{ics_escape(loc)}")
    lines.append("END:VEVENT")
    # 报名截止单独一条，方便日历提醒
    if rec.get("deadline"):
        try:
            dd = dt.date.fromisoformat(rec["deadline"])
        except ValueError:
            dd = None
        if dd:
            lines += ["BEGIN:VEVENT",
                      f"UID:{rec['id']}-deadline@ai-race-radar",
                      f"DTSTAMP:{stamp}",
                      f"DTSTART;VALUE=DATE:{dd.strftime('%Y%m%d')}",
                      f"DTEND;VALUE=DATE:{(dd + dt.timedelta(days=1)).strftime('%Y%m%d')}",
                      f"SUMMARY:⏰ 报名截止：{ics_escape(rec.get('title'))}",
                      f"DESCRIPTION:{ics_escape('报名：' + str(rec.get('url')))}",
                      f"URL:{rec.get('url')}",
                      "END:VEVENT"]
    return lines


def write_ics(lines: list[str], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("\r\n".join(ics_fold(line) for line in lines) + "\r\n")


def build_ics(records: list[dict], path: str) -> None:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ics_calendar_header(SITE_NAME)
    for rec in records:
        lines += ics_vevent_lines(rec, stamp)
    lines.append("END:VCALENDAR")
    write_ics(lines, path)


def build_event_ics(rec: dict, path: str, stamp: str | None = None) -> bool:
    """单场赛事的独立 .ics（详情页「下载 .ics」用）。"""
    stamp = stamp or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ics_vevent_lines(rec, stamp)
    if not lines:
        return False
    write_ics(ics_calendar_header(SITE_NAME) + lines + ["END:VCALENDAR"], path)
    return True


# ---------------------------------------------------------------- SEO
def site_base() -> str:
    return os.environ.get("SITE_URL", "https://ai-race-radar.example.com").rstrip("/")


def build_sitemap(records: list[dict], orgs: list[dict], guides: list[dict]) -> None:
    base = site_base()
    today = dt.date.today().isoformat()
    urls = [
        (f"{base}/", "1.0", "daily"),
        (f"{base}/explore.html", "0.9", "daily"),
        (f"{base}/organizers.html", "0.8", "weekly"),
        (f"{base}/match.html", "0.7", "weekly"),
        (f"{base}/guides.html", "0.7", "weekly"),
        (f"{base}/about.html", "0.6", "monthly"),
        (f"{base}/submit.html", "0.5", "monthly"),
    ]
    urls += [(f"{base}/race/{rec['id']}.html", "0.8", "weekly") for rec in records]
    urls += [(f"{base}/organizer/{org['slug']}.html", "0.6", "weekly") for org in orgs]
    urls += [(f"{base}/guides/{guide['slug']}.html", "0.6", "monthly") for guide in guides]
    body = "\n".join(
        f"  <url><loc>{html.escape(u)}</loc><lastmod>{today}</lastmod>"
        f"<changefreq>{freq}</changefreq><priority>{prio}</priority></url>"
        for u, prio, freq in urls)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{body}\n</urlset>\n")
    with open(os.path.join(SITE, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write(xml)
    with open(os.path.join(SITE, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")


# ---------------------------------------------------------------- 公开数据 / llms.txt
FEED_FIELDS = {
    "id": "站内唯一 ID（也是详情页文件名）",
    "title": "赛事名称（保留官方写法）",
    "organizer": "主办方",
    "mode": "online | offline | hybrid",
    "city": "城市（线上为空或'线上'）",
    "start_date": "比赛开始 YYYY-MM-DD",
    "end_date": "比赛结束 YYYY-MM-DD",
    "deadline": "报名截止 YYYY-MM-DD；未知为 null",
    "prize": "奖金描述（官方口径）",
    "tracks": "赛道/方向数组",
    "summary": "官方页 meta 简介（可选，已过滤平台通用描述）",
    "directions": "站内方向标签数组（智能体/大模型/具身/算法等）",
    "url": "官方报名/详情链接（已实测可打开）",
    "source": "首个信源代号",
    "sources": "全部信源代号",
    "status": "open | closing | closed | upcoming | unknown",
    "ai_level": "core（标题即 AI）| track（泛赛事含 AI 赛道/方向）| platform（AI 平台比赛）| other（AI 相关综合）",
    "verified_at": "链接最近核验时间",
    "verify_code": "链接核验 HTTP 状态码",
    "first_seen": "本雷达首次收录时间",
    "last_seen": "本雷达最近一次见到该赛事的时间",
}


def build_feed(records: list[dict]) -> None:
    base = site_base()
    events = []
    for rec in records:
        events.append({
            "id": rec.get("id"),
            "title": rec.get("title"),
            "organizer": rec.get("organizer"),
            "mode": rec.get("mode"),
            "city": rec.get("city"),
            "start_date": rec.get("start_date"),
            "end_date": rec.get("end_date"),
            "deadline": rec.get("deadline"),
            "prize": rec.get("prize"),
            "tracks": rec.get("tracks") or [],
            "summary": rec.get("summary") or "",
            "directions": rec.get("directions") or [],
            "url": rec.get("url"),
            "source": rec.get("source"),
            "sources": rec.get("sources") or [],
            "status": rec.get("status"),
            "ai_level": common.ai_level(rec),
            "verified_at": rec.get("verified_at"),
            "verify_code": rec.get("verify_code"),
            "first_seen": rec.get("first_seen"),
            "last_seen": rec.get("last_seen"),
        })
    payload = {
        "site": SITE_NAME,
        "homepage": base + "/",
        "description": SITE_DESC + " 含近 90 天已结束赛事（status=closed），供检索与存档。",
        "updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cadence": "daily 08:00 Asia/Shanghai",
        "count": len(events),
        "license": "CC BY 4.0 (attribution: AI 赛事雷达)",
        "attribution": "数据来自 AI 赛事雷达，报名与奖金以主办方官方页面为准",
        "fields": FEED_FIELDS,
        "events": events,
    }
    api_dir = os.path.join(SITE, "api")
    os.makedirs(api_dir, exist_ok=True)
    common.save_json(payload, os.path.join(api_dir, "events.json"))


def build_rss(records: list[dict]) -> None:
    """RSS 2.0：给阅读器 / Agent 的低门槛入口。"""
    base = site_base()
    now = email.utils.format_datetime(dt.datetime.now(dt.timezone.utc))
    items = []
    for rec in records:
        link = f"{base}/race/{rec['id']}.html"
        status = common.STATUS_LABEL.get(rec.get("status") or "", rec.get("status") or "")
        desc = " · ".join(p for p in [
            rec.get("summary") or "",
            status,
            rec.get("organizer") or "",
            f"截止 {rec['deadline']}" if rec.get("deadline") else "截止待确认",
            rec.get("url") or "",
        ] if p)[:360]
        try:
            pub_dt = dt.datetime.fromisoformat(rec.get("first_seen") or "")
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=dt.timezone(dt.timedelta(hours=8)))
            pub_date = email.utils.format_datetime(pub_dt)
        except (ValueError, TypeError):
            pub_date = now
        items.append(
            "    <item>\n"
            f"      <title>{html.escape(rec.get('title') or '')}</title>\n"
            f"      <link>{html.escape(link)}</link>\n"
            f"      <guid isPermaLink=\"false\">{html.escape(rec['id'])}</guid>\n"
            f"      <pubDate>{pub_date}</pubDate>\n"
            f"      <description>{html.escape(desc)}</description>\n"
            "    </item>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        f"    <title>{html.escape(SITE_NAME)} · 中国 AI 赛事与黑客松</title>\n"
        f"    <link>{html.escape(base)}/</link>\n"
        f"    <description>{html.escape(SITE_DESC)}</description>\n"
        "    <language>zh-CN</language>\n"
        f"    <lastBuildDate>{now}</lastBuildDate>\n"
        + "\n".join(items) + "\n"
        "  </channel>\n"
        "</rss>\n"
    )
    with open(os.path.join(SITE, "feed.xml"), "w", encoding="utf-8") as fh:
        fh.write(xml)


def build_llms(records: list[dict]) -> None:
    base = site_base()
    webcal = base.replace("https://", "webcal://", 1).replace("http://", "webcal://", 1) + "/calendar.ics"
    updated = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    llms = f"""# {SITE_NAME} (AI Race Radar)

> 中国 AI 赛事与黑客松的核验清单：只收 AI 相关赛事，每条官方链接实测可打开（HTTP 200/301），
> 每日 08:00（Asia/Shanghai）重新核验；提供日历订阅与公开 JSON。非 AI 综合赛事不收，
> 综合赛里含明确 AI 赛道的会标注 ai_level=track。

## 入口
- 首页: {base}/
- 探索（方向/平台/级别/形式/状态）: {base}/explore.html
- 主办方索引: {base}/organizers.html
- 匹配: {base}/match.html
- 指南: {base}/guides.html
- 方法与 FAQ: {base}/about.html
- 提交赛事 / 纠错: {base}/submit.html
- 公开 JSON（在架 + 近 90 天已结束）: {base}/api/events.json
- 公开 Markdown: {base}/api/events.md
- 本周值得看（编辑精选，不是流量榜）: {base}/data/hot.json
- 全量核验数据: {base}/data/races.json
- 日历订阅（含报名截止提醒）: {base}/calendar.ics
- 日历 webcal（Apple 日历直接打开）: {webcal}
- RSS: {base}/feed.xml
- Agent manifest: {base}/agent.json
- 站点地图: {base}/sitemap.xml

## 数据
- 收录数量: {len(records)} 场（含近 90 天已结束，按 status 区分；真正可报名的用 status 过滤）
- 页面更新时间: {updated}
- 更新节奏: 每天 08:00 重跑链接核验与状态
- 字段: id, title, organizer, mode, city, start_date, end_date, deadline, prize, tracks,
  summary, directions, url, status, ai_level, verified_at
- 引用建议: 「数据来自 AI 赛事雷达，核验时间 YYYY-MM-DD」，报名与奖金以官方页面为准
- 许可: CC BY 4.0（署名: AI 赛事雷达）

## Agent 接入
- 结构化数据: GET {base}/api/events.json（顶层 count / updated / fields，events 数组）
- 过滤建议: status in ("open","closing")；deadline 非空；ai_level 按需
- 日历: {base}/calendar.ics（订阅）或 {webcal}（Apple 日历）
- RSS: {base}/feed.xml
- 单场: 详情页有「Google 日历 / 下载 .ics」；events[].url 是官方报名页
- 写操作: 本站没有报名 / 写接口，报名请打开 events[].url

## 核验规则（摘要）
- 链接：实测 200/301 才展示；403/405/429 标"待确认"；死链移出列表
- 截止日：来自官方页面，缺失写"待确认"，不猜测
- 去重：官方链接 + 标题指纹合并
- AI 分级：core（标题即 AI）/ track（泛赛事含 AI 赛道/方向）/ platform（AI 平台比赛）/ other（AI 相关综合）

## 联系
- 提交赛事 / 纠错 / 主办方校对：见 {base}/about.html#contribute
"""
    with open(os.path.join(SITE, "llms.txt"), "w", encoding="utf-8") as fh:
        fh.write(llms)


def build_agent_manifest() -> None:
    base = site_base()
    data = {
        "name": "AI 赛事雷达",
        "description": "中国 AI 赛事与黑客松的核验清单；只提供只读数据，不代办报名。",
        "url": base + "/",
        "version": "1.0",
        "capabilities": [
            {"name": "event_search", "description": "搜索在架与近 90 天 AI 赛事", "endpoint": base + "/api/events.json"},
            {"name": "event_markdown", "description": "同一份数据的 Markdown 列表", "endpoint": base + "/api/events.md"},
            {"name": "hot", "description": "首页本周值得看（编辑精选，不是流量榜）", "endpoint": base + "/data/hot.json"},
            {"name": "calendar", "description": "iCalendar 订阅，含报名截止提醒", "endpoint": base + "/calendar.ics"},
            {"name": "rss", "description": "RSS 2.0 订阅", "endpoint": base + "/feed.xml"},
            {"name": "explore", "description": "按方向/平台/级别/形式/状态筛选", "endpoint": base + "/explore.html"},
            {"name": "organizers", "description": "主办方实体页索引", "endpoint": base + "/organizers.html"},
            {"name": "guides", "description": "选赛/参赛指南", "endpoint": base + "/guides.html"},
            {"name": "match", "description": "按项目方向做规则匹配（浏览器本地）", "endpoint": base + "/match.html"},
            {"name": "llms_full", "description": "完整 AI reference", "endpoint": base + "/llms-full.txt"},
            {"name": "dataset", "description": "全量核验数据（含已下线）", "endpoint": base + "/data/races.json"},
        ],
        "authentication": {"type": "none"},
        "limits": {"rate": "数据每天 08:00（Asia/Shanghai）更新一次，建议 1–6 小时轮询"},
        "contact": "见 " + base + "/submit.html",
        "citation": "AI 赛事雷达，报名与奖金以主办方官方页为准；许可 CC BY 4.0",
    }
    common.save_json(data, os.path.join(SITE, "agent.json"))
    well_known = os.path.join(SITE, ".well-known")
    os.makedirs(well_known, exist_ok=True)
    common.save_json(data, os.path.join(well_known, "agent.json"))


def build_llms_full(records: list[dict]) -> None:
    base = site_base()
    updated = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    fields = """- id: 站内 ID（详情页文件名）
- title / organizer: 官方标题 / 主办方
- mode: online | offline | hybrid
- city: 线下城市；线上为空或“线上”
- start_date / end_date: YYYY-MM-DD
- deadline: 报名截止 YYYY-MM-DD；未知为 null
- prize / tracks: 奖金摘要 / 赛道数组
- url / source_url: 官方报名或详情页 / 信源页
- status: open | closing | closed | upcoming | unknown
- ai_level: core | platform | track | other
- verified_at / verify_code: 链接最近核验时间 / HTTP 码
- first_seen / last_seen: 首次 / 最近收录时间"""
    body = f"""# AI 赛事雷达 · Full Reference

> 中国 AI 赛事与黑客松的核验清单。只收 AI 相关赛事；链接实测 200/301 才展示；
> 报名与奖金以主办方官方页为准。更新：{updated}（构建时间，Asia/Shanghai）。

## 站点

- 首页: {base}/
- 探索: {base}/explore.html
- 主办方: {base}/organizers.html
- 指南: {base}/guides.html
- 方法/FAQ: {base}/about.html
- 提交/纠错: {base}/submit.html

## 数据入口

- JSON: {base}/api/events.json（{len(records)} 条，在架 + 近 90 天）
- Markdown: {base}/api/events.md
- 本周值得看: {base}/data/hot.json（编辑精选，不是流量榜）
- 全量: {base}/data/races.json（含 90 天外存档）
- 日历: {base}/calendar.ics；webcal: {base.replace('https://', 'webcal://', 1).replace('http://', 'webcal://', 1)}/calendar.ics
- RSS: {base}/feed.xml
- Agent manifest: {base}/agent.json

## 字段

{fields}

## 核验语义

- “已确认”只代表 HTTP 200/301 链接可打开，不代表赛事日期、奖金、资格与官方页永久一致。
- 页面更新时间是本站构建时间，不是主办方公告时间。
- 截止日缺失写“待确认”，不猜测；报名已关闭时 registration_closed=true。
- 已结束赛事保留 14 天首页 / 90 天详情 / 全量 JSON 存档。

## Agent 调用建议

```bash
curl -s {base}/api/events.json | jq '.events[] | select(.status=="open" or .status=="closing")'
curl -s {base}/api/events.md
```

过滤：status in (“open”,“closing”)；deadline 非空；ai_level 按需。
本站没有写接口；报名请打开 events[].url。

## 引用与边界

- 可引用本页对平台功能、数据方法、字段与核验语义的说明。
- 涉及具体赛事的日期、奖金、资格、地点或报名状态，应优先引用主办方官方页面。
- 不要从本页推断流量、营收、合作方数量或赛事可用性。
- 许可：CC BY 4.0（署名：AI 赛事雷达）。
"""
    with open(os.path.join(SITE, "llms-full.txt"), "w", encoding="utf-8") as fh:
        fh.write(body)


def build_events_md(records: list[dict]) -> None:
    base = site_base()
    lines = [
        "# AI 赛事雷达 · 赛事清单",
        "",
        f"> 更新：{dt.datetime.now().strftime('%Y-%m-%d %H:%M')}（构建时间，Asia/Shanghai）",
        f"> 共 {len(records)} 条（在架 + 近 90 天）；报名/奖金以主办方官方页为准。",
        f"> JSON: {base}/api/events.json · 许可: CC BY 4.0",
        "",
    ]
    for rec in records:
        date = rec.get("deadline") or rec.get("start_date") or "待确认"
        lines.append(f"## {rec.get('title')}")
        lines.append(f"- 状态: {common.STATUS_LABEL.get(rec.get('status') or '', '待确认')} | AI: {common.ai_level(rec)}")
        lines.append(f"- 形式: {common.MODE_LABEL.get(rec.get('mode') or '', '待确认')}"
                     + (f" · {rec['city']}" if rec.get("city") else ""))
        lines.append(f"- 截止: {date} | 比赛: {rec.get('start_date') or '?'} → {rec.get('end_date') or '?'}")
        if rec.get("prize"):
            lines.append(f"- 奖金: {rec['prize']}")
        lines.append(f"- 报名: {rec.get('url')}")
        lines.append("")
    with open(os.path.join(SITE, "api", "events.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def build_match_data(records: list[dict]) -> None:
    data = []
    for rec in records:
        data.append({
            "id": rec["id"],
            "title": rec.get("title"),
            "organizer": rec.get("organizer"),
            "mode": rec.get("mode"),
            "city": rec.get("city"),
            "status": rec.get("status"),
            "deadline": rec.get("deadline"),
            "ai_level": rec.get("ai_level") or common.ai_level(rec),
            "tracks": rec.get("tracks") or [],
            "directions": rec.get("directions") or [],
            "summary": rec.get("summary") or "",
        })
    common.save_json(data, os.path.join(SITE, "data", "match.json"))


def enrich_records(records: list[dict]) -> None:
    sm = summaries.load(records)
    for rec in records:
        rec["summary"] = sm.get(rec["id"], "")
        rec["directions"] = taxonomy.directions_for(rec)
        rec["ai_level"] = common.ai_level(rec)


def attach_related(records: list[dict]) -> None:
    for rec in records:
        scored = []
        for other in records:
            if other["id"] == rec["id"]:
                continue
            score = 0
            if rec.get("organizer") and rec.get("organizer") == other.get("organizer"):
                score += 3
            shared = set(rec.get("directions") or []) & set(other.get("directions") or [])
            score += len(shared) * 2
            if rec.get("ai_level") == other.get("ai_level"):
                score += 1
            if other.get("status") in ("open", "closing"):
                score += 1
            if score:
                scored.append((score, other))
        scored.sort(key=lambda x: (-x[0], x[1].get("deadline") or "9999-12-31"))
        rec["_related"] = [r for _, r in scored[:3]]


# ---------------------------------------------------------------- main
def archived(rec: dict) -> bool:
    """已结束超过 14 天的赛事：详情页与 sitemap/feed 保留到 90 天，但不再上首页。"""
    if rec.get("status") != "closed":
        return False
    ref = rec.get("deadline") or rec.get("end_date") or rec.get("start_date")
    d = common.days_until(ref)
    return d is not None and d < -14


def stale(rec: dict) -> bool:
    """前台只展示「现在还能用」的信息：
    - 已截止：保留 90 天（做历史参考 + 长尾搜索，避免赛事页刚结束就下线）；
    - 其它状态：日期已过去 90 天以上的旧比赛隐藏（更老进全量 JSON 存档）。
    """
    ref = rec.get("deadline") or rec.get("end_date") or rec.get("start_date")
    d = common.days_until(ref)
    if d is None:
        return False
    return d < -90


def main() -> int:
    common.ensure_dirs()
    records = common.load_json(RACES_PATH, [])
    if not records:
        print(f"[warn] {RACES_PATH} 为空，先跑 scripts/verify.py")
    # 只展示已确认或 curated 的；dead 已在 verify 导出时剔除
    full_records = [r for r in records if r.get("verify_state") in ("ok", "unknown", None)]
    enrich_records(full_records)
    # 超过 90 天的旧赛事彻底下线；14–90 天的已结束赛事保留详情页（SEO/存档），但不上首页
    records = [r for r in full_records if not stale(r)]
    records.sort(key=lambda r: (r.get("status") == "closed",
                                r.get("deadline") is None,
                                r.get("deadline") or "9999-12-31",
                                r.get("title") or ""))
    index_records = [r for r in records if not archived(r)]
    hot_picks = hotmod.picks(index_records)

    orgs = organizers.build(records)
    slug_by_name = {o["name"]: o["slug"] for o in orgs}
    for rec in records:
        rec["organizer_slug"] = slug_by_name.get((rec.get("organizer") or "").strip(), "")
    current_ids = {r["id"] for r in index_records}
    for rec in records:
        rec["_tab"] = "current" if rec["id"] in current_ids else "past"
    attach_related(records)
    guides = guides_content.build(records, index_records)

    race_dir = os.path.join(SITE, "race")
    org_dir = os.path.join(SITE, "organizer")
    guide_dir = os.path.join(SITE, "guides")
    for d in (race_dir, org_dir, guide_dir):
        os.makedirs(d, exist_ok=True)
    # 清掉上一轮产物，避免下线赛事/主办方留下旧页面
    for d in (race_dir, org_dir, guide_dir):
        for name in os.listdir(d):
            if name.endswith((".html", ".ics")):
                os.remove(os.path.join(d, name))
    os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
    os.makedirs(os.path.join(SITE, "data"), exist_ok=True)
    os.makedirs(os.path.join(SITE, "api"), exist_ok=True)

    with open(os.path.join(SITE, "assets", "style.css"), "w", encoding="utf-8") as fh:
        fh.write(STYLE.strip() + "\n")
    with open(os.path.join(SITE, "assets", "app.js"), "w", encoding="utf-8") as fh:
        fh.write(APP_JS.strip() + "\n")
    with open(os.path.join(SITE, "assets", "explore.js"), "w", encoding="utf-8") as fh:
        fh.write(pages_extra.EXPLORE_JS.strip() + "\n")
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(render_index(index_records, hot_picks))
    with open(os.path.join(SITE, "explore.html"), "w", encoding="utf-8") as fh:
        fh.write(pages_extra.render_explore(records))
    with open(os.path.join(SITE, "organizers.html"), "w", encoding="utf-8") as fh:
        fh.write(pages_extra.render_organizers_index(orgs))
    with open(os.path.join(SITE, "match.html"), "w", encoding="utf-8") as fh:
        fh.write(pages_extra.render_match(records))
    with open(os.path.join(SITE, "guides.html"), "w", encoding="utf-8") as fh:
        fh.write(pages_extra.render_guides_index())
    with open(os.path.join(SITE, "about.html"), "w", encoding="utf-8") as fh:
        fh.write(render_about())
    with open(os.path.join(SITE, "submit.html"), "w", encoding="utf-8") as fh:
        fh.write(render_submit())
    for org in orgs:
        with open(os.path.join(org_dir, f"{org['slug']}.html"), "w", encoding="utf-8") as fh:
            fh.write(pages_extra.render_organizer(org))
    for guide in guides:
        with open(os.path.join(guide_dir, f"{guide['slug']}.html"), "w", encoding="utf-8") as fh:
            fh.write(pages_extra.render_guide(guide))

    ics_stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    ics_count = 0
    for rec in records:
        with open(os.path.join(race_dir, f"{rec['id']}.html"), "w", encoding="utf-8") as fh:
            fh.write(render_detail(rec))
        if build_event_ics(rec, os.path.join(race_dir, f"{rec['id']}.ics"), ics_stamp):
            ics_count += 1
    build_ics(index_records, os.path.join(SITE, "calendar.ics"))
    build_sitemap(records, orgs, guides)
    build_feed(records)
    build_rss(records)
    build_llms(records)
    build_llms_full(records)
    build_agent_manifest()
    build_events_md(records)
    build_match_data(records)
    common.save_json(hotmod.to_public(hot_picks), os.path.join(SITE, "data", "hot.json"))
    # /data/races.json 是对外承诺的「全量核验数据」：保留超过 90 天、已从前台
    # 下线但仍在账本里的记录；首页/详情页/feed 仍用 90 天窗口的 records。
    common.save_json([{k: v for k, v in r.items() if not k.startswith("_")} for r in full_records],
                     os.path.join(SITE, "data", "races.json"))
    common.save_json(
        [{"name": o["name"], "slug": o["slug"], "cities": o["cities"],
          "website": o["website"], "intro": o["intro"],
          "events": [r["id"] for r in o["records"]]} for o in orgs],
        os.path.join(SITE, "data", "organizers.json"),
    )

    print(f"[ok] 站点生成：{SITE}")
    print(f"     首页 {len(index_records)} 场（在架 + 近 14 天结束）· 详情页/存档 {len(records)} 场"
          f" · 探索 {len(records)} 场 · 主办方 {len(orgs)} 个 · 指南 {len(guides)} 篇")
    print(f"     index/explore/organizers/match/guides + race/*.html + organizer/*.html"
          f" + guides/*.html + race/*.ics（{ics_count}）")
    print(f"     + api/events.json + api/events.md + feed.xml + llms-full.txt + agent.json + sitemap.xml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
