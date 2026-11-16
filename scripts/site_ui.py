#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""站点表现层：品牌常量、HTML 模板、列表/详情/关于/投稿页。

由 build_site.py 导入；样式在 scripts/theme.py。
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import urllib.parse

import common

SITE = common.SITE_DIR
SITE_NAME = "AI 赛事雷达"
SITE_TAGLINE = "中国 AI 赛事与黑客松"
SITE_DESC = "每一场都经过人工核验：官方链接、报名截止、线上 / 线下，点开就能报名。"
SUBMIT_EMAIL = os.environ.get("SUBMIT_EMAIL", "")
SITE_URL = os.environ.get("SITE_URL", "https://ai-race-radar.example.com").rstrip("/")
WEBCAL_URL = SITE_URL.replace("https://", "webcal://", 1).replace("http://", "webcal://", 1) + "/calendar.ics"
SUBSCRIBE_URL = os.environ.get("SUBSCRIBE_URL", "").strip()
SUBSCRIBE_EMAIL = os.environ.get("SUBSCRIBE_EMAIL", "").strip()
# 站点面向中国大陆用户，构建时间统一按北京时间展示；
# GitHub Actions 的 runner 是 UTC，不能再用裸 datetime.now()。
BEIJING = dt.timezone(dt.timedelta(hours=8), "Asia/Shanghai")
UPDATED = dt.datetime.now(BEIJING).strftime("%Y-%m-%d %H:%M")
ASSET_V = dt.datetime.now(BEIJING).strftime("%Y%m%d%H%M%S")

# 在样式表之前决定明暗，避免刷新时闪一下
THEME_BOOT = """<script>
(function(){
  try{
    var q = new URLSearchParams(location.search).get('theme');
    var t = q || localStorage.getItem('airr-theme');
    if (t === 'light' || t === 'dark') document.documentElement.setAttribute('data-theme', t);
  }catch(e){}
})();
</script>"""

SRC_LABEL = {
    "curated": "人工核验",
    "tianchi": "天池",
    "xfyun": "讯飞",
    "datafountain": "DataFountain",
    "aistudio": "百度 AI Studio",
    "dorahacks": "DoraHacks",
    "luma": "Luma 活动页",
    "huodongxing": "活动行",
    "zhihu": "知乎活动站",
    "modelscope": "魔搭 ModelScope",
    "heywhale": "和鲸 Heywhale",
    "biendata": "biendata",
    "lianpu": "联谱",
    "wqai": "湾区 AI 日历",
    "sogou": "公众号",
}

LEVEL_LABEL = {
    "core": "AI 核心赛事",
    "track": "含 AI 赛道 / 方向",
    "platform": "AI 平台赛事",
    "other": "AI 相关综合赛事",
}


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def fmt_md(value) -> str:
    if not value:
        return ""
    try:
        d = dt.date.fromisoformat(value)
    except (ValueError, TypeError):
        return str(value)
    return f"{d.month:02d}.{d.day:02d}"


def fmt_date(value) -> str:
    if not value:
        return "待确认"
    try:
        d = dt.date.fromisoformat(value)
    except (ValueError, TypeError):
        return str(value)
    return f"{d.year}年{d.month}月{d.day}日"


def _days(value):
    return common.days_until(value)


def short_countdown(rec: dict) -> str:
    status = rec.get("status")
    if rec.get("registration_closed"):
        return "报名已关闭"
    if status == "closed":
        return "已截止"
    d = _days(rec.get("deadline"))
    if d is None:
        return "待确认"
    if d > 1:
        return f"还有 {d} 天"
    if d == 1:
        return "明天"
    if d == 0:
        return "今天"
    return "已截止"


def countdown(rec: dict) -> str:
    status = rec.get("status")
    if rec.get("registration_closed"):
        return "报名已关闭"
    if status == "closed":
        return "已截止"
    d = _days(rec.get("deadline"))
    if d is None:
        return "截止时间待确认"
    if d > 7:
        return f"报名截止 {fmt_date(rec.get('deadline'))}（还有 {d} 天）"
    if d > 1:
        return f"还有 {d} 天截止"
    if d == 1:
        return "明天截止"
    if d == 0:
        return "今天截止"
    return "已截止"


def google_calendar_url(rec: dict) -> str:
    """单场赛事的 Google 日历模板链接；没有日期时返回空串。"""
    start = rec.get("start_date") or rec.get("deadline")
    if not start:
        return ""
    try:
        d0 = dt.date.fromisoformat(start)
    except (ValueError, TypeError):
        return ""
    end = rec.get("end_date") or start
    try:
        d1 = dt.date.fromisoformat(end)
    except (ValueError, TypeError):
        d1 = d0
    if d1 < d0:
        d1 = d0
    d1 = d1 + dt.timedelta(days=1)  # Google 全天事件的结束日是排他的
    loc = str(rec.get("city") or "线上") if rec.get("mode") != "online" else "线上"
    parts = []
    if rec.get("organizer"):
        parts.append(f"主办方：{rec['organizer']}")
    if rec.get("deadline"):
        parts.append(f"报名截止：{rec['deadline']}")
    parts.append(f"报名：{rec.get('url')}")
    params = {
        "action": "TEMPLATE",
        "text": rec.get("title") or "AI 赛事",
        "dates": f"{d0:%Y%m%d}/{d1:%Y%m%d}",
        "details": "\n".join(parts),
        "location": loc,
        "ctz": "Asia/Shanghai",
    }
    return "https://calendar.google.com/calendar/render?" + urllib.parse.urlencode(params)


def event_jsonld(rec: dict) -> str:
    """schema.org Event 结构化数据，给搜索引擎和 Agent 读。"""
    start = rec.get("start_date") or rec.get("deadline")
    if not start:
        return ""
    status = rec.get("status") or "unknown"
    organizer = (rec.get("organizer") or "").strip()
    if organizer in ("", "待确认", "主办方待确认"):
        organizer = ""
    if rec.get("mode") == "online":
        location = {"@type": "VirtualLocation", "url": rec.get("url")}
    elif rec.get("city"):
        location = {
            "@type": "Place",
            "name": str(rec["city"]),
            "address": {"@type": "PostalAddress", "addressLocality": str(rec["city"])},
        }
    else:
        location = {"@type": "Place", "name": "待确认"}
    if rec.get("registration_closed") or status == "closed":
        availability = "https://schema.org/SoldOut"
    elif status in ("open", "closing"):
        availability = "https://schema.org/InStock"
    elif status == "upcoming":
        availability = "https://schema.org/PreOrder"
    else:
        availability = "https://schema.org/InStock"
    desc_parts = [p for p in [
        f"主办方：{organizer}" if organizer else "",
        f"报名截止：{rec.get('deadline')}" if rec.get("deadline") else "",
        f"赛道：{'、'.join(rec.get('tracks') or [])}" if rec.get("tracks") else "",
        f"报名：{rec.get('url')}",
    ] if p]
    description = (rec.get("summary") or "；".join(desc_parts)).strip()
    data = {
        "@context": "https://schema.org",
        "@type": "Event",
        "@id": f"{SITE_URL}/race/{rec['id']}.html",
        "name": rec.get("title"),
        "startDate": start,
        "endDate": rec.get("end_date") or start,
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": {
            "online": "https://schema.org/OnlineEventAttendanceMode",
            "offline": "https://schema.org/OfflineEventAttendanceMode",
            "hybrid": "https://schema.org/MixedEventAttendanceMode",
        }.get(rec.get("mode") or "", "https://schema.org/OnlineEventAttendanceMode"),
        "location": location,
        "url": rec.get("url"),
        "description": description,
        "inLanguage": "zh-CN",
        "dateModified": rec.get("last_seen") or None,
        "offers": {
            "@type": "Offer",
            "url": rec.get("url"),
            "availability": availability,
            "validThrough": rec.get("deadline") or None,
        },
    }
    if not data["dateModified"]:
        data.pop("dateModified")
    if not data["offers"]["validThrough"]:
        data["offers"].pop("validThrough")
    if rec.get("prize"):
        data["award"] = rec["prize"]
    if rec.get("tracks"):
        data["keywords"] = "、".join(str(t) for t in rec["tracks"])
    if rec.get("source_url") and rec.get("source_url") != rec.get("url"):
        data["sameAs"] = [rec["source_url"]]
    if organizer:
        data["organizer"] = {"@type": "Organization", "name": organizer}
        if rec.get("organizer_slug"):
            data["organizer"]["url"] = f"{SITE_URL}/organizer/{rec['organizer_slug']}.html"
    raw = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">{raw}</script>'


def _json_script(data) -> str:
    raw = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">{raw}</script>'


def site_jsonld() -> str:
    """全站 Organization / WebSite / Dataset 图，给搜索与 Agent 读。"""
    org_id = SITE_URL + "/#organization"
    graph = [
        {
            "@type": "Organization",
            "@id": org_id,
            "name": SITE_NAME,
            "url": SITE_URL + "/",
            "description": SITE_DESC,
            "knowsAbout": ["AI 赛事", "黑客松", "hackathon", "AI competition", "算法赛", "智能体"],
        },
        {
            "@type": "WebSite",
            "@id": SITE_URL + "/#website",
            "url": SITE_URL + "/",
            "name": SITE_NAME,
            "description": SITE_DESC,
            "inLanguage": "zh-CN",
            "publisher": {"@id": org_id},
            "potentialAction": {
                "@type": "SearchAction",
                "target": {
                    "@type": "EntryPoint",
                    "urlTemplate": SITE_URL + "/explore.html?q={search_term_string}",
                },
                "query-input": "required name=search_term_string",
            },
        },
        {
            "@type": "Dataset",
            "name": "AI 赛事雷达公开数据",
            "description": "中国 AI 赛事与黑客松的核验清单，含状态、截止日、AI 分级与核验时间。",
            "url": SITE_URL + "/api/events.json",
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "creator": {"@id": org_id},
            "isAccessibleForFree": True,
        },
    ]
    return _json_script({"@context": "https://schema.org", "@graph": graph})


def itemlist_jsonld(records: list[dict], name: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": name,
        "numberOfItems": len(records),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i,
                "url": f"{SITE_URL}/race/{rec['id']}.html",
                "name": rec.get("title") or "",
            }
            for i, rec in enumerate(records, 1)
        ],
    }
    return _json_script(data)


def subscribe_html() -> str:
    if SUBSCRIBE_URL:
        return (f'<a href="{esc(SUBSCRIBE_URL)}">点此填写邮箱订阅</a>：每天一封「新收录 + 3 天内截止」，'
                '邮件里附 calendar.ics；退订见邮件底部。')
    if SUBSCRIBE_EMAIL:
        href = "mailto:" + SUBSCRIBE_EMAIL + "?subject=" + urllib.parse.quote("订阅 AI 赛事雷达")
        return (f'<a href="{esc(href)}">发邮件订阅</a>：正文写「订阅」即可；'
                '每天一封「新收录 + 3 天内截止」，附 calendar.ics。')
    return '邮件服务配置后开放；当前可先用日历订阅或 RSS。'


def head(title: str, desc: str, depth: int = 0, page: str = "") -> str:
    prefix = "../" * depth
    nav = [("index.html", "赛事", "index"), ("explore.html", "探索", "explore"),
           ("calendar.html", "日历", "calendar"), ("submit.html", "投稿", "submit")]
    links = "".join(
        '<a href="{0}{1}"{2}>{3}</a>'.format(
            prefix, href, ' class="on"' if key and key == page else "", label)
        for href, label, key in nav)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta name="theme-color" content="#0b100d" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f3f4ec" media="(prefers-color-scheme: light)">
<meta name="color-scheme" content="dark light">
{THEME_BOOT}
{site_jsonld()}
<link rel="alternate" type="text/calendar" title="AI 赛事雷达 · 赛事日历" href="{prefix}calendar.ics">
<link rel="alternate" type="application/rss+xml" title="AI 赛事雷达 · 赛事 RSS" href="{prefix}feed.xml">
<link rel="alternate" type="text/plain" title="AI 赛事雷达 · llms.txt" href="{prefix}llms.txt">
<link rel="stylesheet" href="{prefix}assets/style.css?v={ASSET_V}">
</head>
<body>
<header class="site"><div class="wrap hrow">
  <a class="brand" href="{prefix}index.html"><span class="mark"></span><span class="bname">{SITE_NAME}</span><span class="ben">AI RACE RADAR</span></a>
  <nav class="top">{links}</nav>
  <button class="theme-toggle" id="theme-toggle" type="button" aria-label="切换明暗主题" aria-pressed="false" title="切换明暗主题"><span aria-hidden="true">◐</span></button>
  <span class="live"><i></i><span class="lk">LIVE · 08:00</span></span>
</div></header>
<main class="wrap">"""


def foot(depth: int = 0) -> str:
    prefix = "../" * depth
    return f"""</main>
<footer class="site"><div class="wrap">
  <div class="fcols">
    <div class="fcol">
      <div class="fmark">{SITE_NAME} / AI RACE RADAR</div>
      <p>中国 AI 赛事与黑客松的核验清单。只在官方链接能打开、日期对得上时才收录；每天 08:00 重跑一次。</p>
      <p class="fmeta">DATA UPDATED · {UPDATED}</p>
    </div>
    <div class="fcol"><div class="fhead">EXPLORE</div>
      <a href="{prefix}explore.html">探索全部</a>
      <a href="{prefix}organizers.html">主办方</a>
      <a href="{prefix}guides.html">指南</a>
      <a href="{prefix}match.html">帮我找赛事</a>
    </div>
    <div class="fcol"><div class="fhead">DATA</div>
      <a href="{prefix}api/events.json">api/events.json</a>
      <a href="{prefix}llms.txt">llms.txt</a>
      <a href="{prefix}llms-full.txt">llms-full.txt</a>
      <a href="{prefix}agent.json">agent.json</a>
      <a href="{prefix}sitemap.xml">sitemap.xml</a>
    </div>
    <div class="fcol"><div class="fhead">ABOUT</div>
      <a href="{prefix}about.html">方法与信源</a>
      <a href="{prefix}about.html#faq">常见问题</a>
      <a href="{prefix}submit.html">提交赛事 / 纠错</a>
      <a href="{prefix}calendar.html">日历订阅</a>
      <a href="{prefix}feed.xml">RSS</a>
    </div>
  </div>
  <div class="fine">
    <span>© 2026 {SITE_NAME}</span>
    <span>不收费 · 不代办报名 · 以主办方官方页面为准</span>
    <span>CC BY 4.0</span>
  </div>
</div></footer>
<script src="{prefix}assets/app.js?v={ASSET_V}"></script>
</body></html>"""


def deadline_cell(rec: dict) -> str:
    if rec.get("registration_closed"):
        return '<span class="dnum sm">已关闭</span><span class="ddate">报名通道关闭</span>'
    if rec.get("status") == "closed":
        sub = fmt_md(rec.get("deadline")) + " 截止" if rec.get("deadline") else "时间已过"
        return f'<span class="dnum sm">已截止</span><span class="ddate">{esc(sub)}</span>'
    d = _days(rec.get("deadline"))
    if d is None:
        return '<span class="dnum sm">待确认</span><span class="ddate">截止时间未知</span>'
    if d < 0:
        return f'<span class="dnum sm">已截止</span><span class="ddate">{esc(fmt_md(rec.get("deadline")))} 截止</span>'
    num = f"{d:02d}" if d < 100 else "99+"
    cls = " warn" if d <= 3 else ""
    return (f'<span class="dnum{cls}">{num}<small>天</small></span>'
            f'<span class="ddate">{esc(fmt_md(rec.get("deadline")))} 截止</span>')


def row_sub(rec: dict) -> str:
    parts = [f'<span>{esc(rec.get("organizer") or "主办方待确认")}</span>']
    mode = common.MODE_LABEL.get(rec.get("mode") or "", "")
    city = rec.get("city") if rec.get("mode") != "online" else ""
    loc = mode + (f" · {city}" if city else "")
    if loc:
        parts += ['<span class="sep">/</span>', f"<span>{esc(loc)}</span>"]
    tracks = (rec.get("tracks") or [])[:3]
    if tracks:
        parts += ['<span class="sep">/</span>', f"<span>{esc(' · '.join(tracks))}</span>"]
    if common.ai_level(rec) == "track":
        parts.append('<span class="badge">含 AI 赛道</span>')
    return "".join(parts)


def render_row(rec: dict, idx: int, prefix: str = "") -> str:
    status = rec.get("status") or "unknown"
    level = rec.get("ai_level") or common.ai_level(rec)
    dirs = " ".join(rec.get("directions") or [])
    city = rec.get("city") or ""
    days = common.days_until(rec.get("deadline"))
    hay = " ".join([rec.get("title") or "", rec.get("organizer") or "",
                    str(rec.get("tracks") or ""), city, rec.get("summary") or "",
                    rec.get("notes") or ""])
    return f"""<a class="race-row" href="{prefix}race/{esc(rec['id'])}.html"
  data-status="{esc(status)}" data-mode="{esc(rec.get('mode') or '')}"
  data-level="{esc(level)}" data-source="{esc(rec.get('source') or '')}"
  data-city="{esc(city)}" data-dir="{esc(dirs)}" data-tab="{esc(rec.get('_tab') or '')}"
  data-deadline="{esc(rec.get('deadline') or '9999-12-31')}"
  data-days="{days if days is not None else 9999}"
  data-start="{esc(rec.get('start_date') or '')}"
  data-end="{esc(rec.get('end_date') or '')}"
  data-firstseen="{esc(rec.get('first_seen') or '')}"
  data-hay="{esc(hay)}">
  <span class="idx"><i class="st {esc(status)}"></i><span class="num">{idx:03d}</span></span>
  <span class="r-main">
    <span class="r-title">{esc(rec.get('title'))}</span>
    <span class="r-sub">{row_sub(rec)}</span>
  </span>
  <span class="r-deadline">{deadline_cell(rec)}</span>
  <span class="arrow">→</span>
</a>"""


def render_hero_panel(hot: dict | None) -> str:
    items = (hot or {}).get("items") or []
    if not items:
        return """
<aside class="hero-panel">
  <div class="hp-head"><div><div class="kicker">DEADLINE RADAR</div><h2>本周值得看</h2></div></div>
  <p class="hp-empty">未来 7 天暂无明确截止的赛事；可以浏览全部在架赛事，或订阅日历等下一场。</p>
  <div class="hp-foot"><a href="explore.html">浏览全部赛事 →</a></div>
</aside>"""
    rows = []
    for i, item in enumerate(items, 1):
        rec = item["rec"]
        days = item["days"]
        rows.append(f"""
  <a class="hp-row" href="race/{esc(rec['id'])}.html">
    <span class="hp-days">{days:02d}<small>天</small></span>
    <span class="hp-main">
      <b>{esc(rec.get('title'))}</b>
      <small>{esc(rec.get('organizer') or '主办方待确认')} · {esc(rec.get('prize') or '奖金待确认')}</small>
    </span>
    <span class="hp-arrow">→</span>
  </a>""")
    window = hot.get("window") or 7
    return f"""
<aside class="hero-panel" aria-labelledby="hot-title">
  <div class="hp-head">
    <div>
      <div class="kicker">DEADLINE RADAR / {len(items)} PICKS</div>
      <h2 id="hot-title">{esc(hot.get('label') or '本周值得看')}</h2>
    </div>
    <span class="hp-live"><i></i>LIVE / 08:00</span>
  </div>
  <div class="hp-summary">
    <span class="hp-big">{len(items)}</span>
    <span class="hp-unit">场<br>{window} 天内截止</span>
    <span class="hp-note">最早 {esc(items[0]['when'])}<br>按截止日 + 奖金排序</span>
  </div>
  <div class="hp-list">{"".join(rows)}</div>
  <div class="hp-foot">
    <a href="explore.html?window={window}">查看全部 {window} 天内截止 →</a>
    <span>不是流量榜</span>
  </div>
</aside>"""


def render_index(records: list[dict], hot: dict | None = None) -> str:
    total = len(records)
    online = sum(1 for r in records if r.get("mode") == "online")
    openable = sum(1 for r in records if r.get("status") in ("open", "closing"))
    orgs = len({r.get("organizer") for r in records if r.get("organizer")})
    rows = "\n".join(render_row(r, i + 1) for i, r in enumerate(records))
    hero_panel = render_hero_panel(hot)
    return head(f"{SITE_NAME} · {SITE_TAGLINE}", SITE_DESC, page="index") + f"""
<section class="hero">
  <div class="hero-copy">
    <div class="kicker">SIGNAL 001 / {esc(UPDATED[:10])} / BEIJING</div>
    <h1 class="display">中国 AI 赛事<br><em>与黑客松</em></h1>
    <p class="sub">官方链接、报名截止、线上或线下——每一场都核验过才收录。不追条数，只追能点开的那一条。</p>
    <div class="cta hero-cta">
      <a class="btn primary" href="#list">浏览在架赛事</a>
      <a class="btn ghost" href="match.html">帮我找赛事</a>
      <a class="btn ghost" href="calendar.html">订阅日历</a>
    </div>
  </div>
  {hero_panel}
</section>

<div class="ledger">
  <div class="cell"><span class="k">收录 / TRACKED</span><span class="v">{total}<small>场</small></span></div>
  <div class="cell"><span class="k">线上 / ONLINE</span><span class="v">{online}<small>场</small></span></div>
  <div class="cell"><span class="k">在报名 / OPEN</span><span class="v acc">{openable}<small>场</small></span></div>
  <div class="cell"><span class="k">主办方 / ORGS</span><span class="v">{orgs}<small>家</small></span></div>
  <div class="cell"><span class="k">核验 / VERIFIED</span><span class="v">08:00<small>每日</small></span></div>
</div>

<div class="rail">
  <div class="search"><span class="sl">/</span>
    <input id="q" type="text" placeholder="搜索赛事、主办方、赛道" autocomplete="off"></div>
  <div class="chips">
    <button class="chip active" data-filter="mode" data-value="all">全部</button>
    <button class="chip" data-filter="mode" data-value="online">线上</button>
    <button class="chip" data-filter="mode" data-value="offline">线下</button>
    <button class="chip" data-filter="mode" data-value="hybrid">混合</button>
    <button class="chip" data-filter="status" data-value="closing">即将截止</button>
  </div>
  <div class="sortwrap"><label>SORT</label>
    <select id="sort">
      <option value="deadline">截止日</option>
      <option value="newest">收录时间</option>
    </select>
  </div>
</div>

<div class="list-head" id="list"><span>● 在架 · <b class="cnt">{total}</b> 场</span>
  <span><a href="explore.html">筛选全部 / 往届 →</a></span></div>
<section class="race-list">
{rows}
</section>
<div class="empty" style="display:none">没有匹配的赛事，换个关键词试试。</div>
{itemlist_jsonld(records, SITE_NAME + " 在架赛事")}""" + foot()


def organizer_link(rec: dict, prefix: str = "") -> str:
    name = rec.get("organizer") or "主办方待确认"
    slug = rec.get("organizer_slug") or ""
    if slug:
        return f'<a href="{prefix}organizer/{esc(slug)}.html">{esc(name)}</a>'
    return esc(name)


def agenda_html(rec: dict) -> str:
    """只用已收录的日期生成日程，不编造报名开始等节点。"""
    items = []
    for label, key in (("报名截止", "deadline"), ("比赛开始", "start_date"), ("比赛结束", "end_date")):
        value = rec.get(key)
        if not value:
            continue
        try:
            d = dt.date.fromisoformat(value)
        except (ValueError, TypeError):
            continue
        items.append((d, label, value))
    if not items:
        return """
  <section class="race-section">
    <h2>日程</h2>
    <p>官方页暂未给出可核验的报名截止或比赛日期；待主办方更新后再补。</p>
    <p class="section-note">不猜测日期，也不把“长期开放”当成具体截止日。</p>
  </section>"""
    # 同一天只保留一条：报名截止 > 比赛开始 > 比赛结束
    seen = set()
    unique = []
    for d, label, value in sorted(items, key=lambda x: (x[0], {"报名截止": 0, "比赛开始": 1, "比赛结束": 2}[x[1]])):
        if d in seen and label != "报名截止":
            continue
        seen.add(d)
        unique.append((label, value))
    lis = "".join(
        f'<li><span class="ag-date">{esc(fmt_date(value))}</span>'
        f'<span class="ag-title">{esc(label)}</span></li>'
        for label, value in unique
    )
    return f"""
  <section class="race-section">
    <h2>日程</h2>
    <ol class="agenda">{lis}</ol>
    <p class="section-note">仅展示已收录的日期节点；未收录的环节不猜测。</p>
  </section>"""


def related_html(rec: dict) -> str:
    rel = rec.get("_related") or []
    if not rel:
        return ""
    cards = "".join(
        f'<a class="related-card" href="../race/{esc(r["id"])}.html">'
        f'<span class="rc-title">{esc(r.get("title"))}</span>'
        f'<span class="rc-meta">{esc(common.MODE_LABEL.get(r.get("mode") or "", "待确认"))}'
        f' · {esc(fmt_date(r.get("deadline")))} 截止</span></a>'
        for r in rel
    )
    return f"""
  <section class="race-section">
    <h2>相关赛事</h2>
    <div class="related-grid">{cards}</div>
  </section>"""


def source_block(rec: dict) -> str:
    source_url = rec.get("source_url") or rec.get("url") or ""
    title = rec.get("title") or ""
    corr = ("../submit.html?id=" + urllib.parse.quote(str(rec.get("id") or ""))
            + "&title=" + urllib.parse.quote(title)
            + "&url=" + urllib.parse.quote(rec.get("url") or ""))
    evidence = (f'<p class="source-evidence">核验依据：{esc(rec.get("evidence"))}</p>'
                if rec.get("evidence") else "")
    return f"""
  <section class="race-section source-box" id="source">
    <h2>信息来源与更正</h2>
    <p>本页为公开信息整理，赛事由主办方举办，与 {SITE_NAME} 无主办关系。
      链接返回 200 只代表页面可打开，不代表赛事信息与官方页完全一致；报名、资格、奖金以主办方页面为准。</p>
    <div class="source-lines">
      <div>来源页：<a href="{esc(source_url)}" target="_blank" rel="noopener nofollow">{esc(source_url)}</a></div>
      <div>链接核验：<b>{esc(rec.get("verified_at") or "未知")}</b>（HTTP {esc(rec.get("verify_code") or "—")}）</div>
      <div>页面更新：<b>{esc(rec.get("last_seen") or "未知")}</b></div>
      <div>数据来源：<b>{esc(SRC_LABEL.get(rec.get("source") or "", rec.get("source") or "人工核验"))}</b></div>
    </div>
    {evidence}
    <p class="source-actions"><a href="{esc(corr)}">发现信息有误？提交纠错 →</a></p>
  </section>"""


def render_detail(rec: dict) -> str:
    status = rec.get("status") or "unknown"
    status_label = common.STATUS_LABEL.get(status, "待确认")
    mode = common.MODE_LABEL.get(rec.get("mode") or "", "待确认")
    city = rec.get("city") if rec.get("mode") != "online" else ""
    src = "、".join(SRC_LABEL.get(s, s) for s in (rec.get("sources") or [rec.get("source") or ""]) if s)
    deadline_note = (fmt_date(rec.get("deadline")) + "（" + short_countdown(rec) + "）"
                     if rec.get("deadline") else "待确认")
    organizer = organizer_link(rec, "../")
    kv = [
        ("主办方", organizer),
        ("形式", esc(mode) + (f" · {esc(city)}" if city else "")),
        ("报名截止", esc(deadline_note)),
        ("比赛时间", esc(fmt_date(rec.get("start_date")))
         + (" — " + esc(fmt_date(rec.get("end_date"))) if rec.get("end_date") else "")),
        ("奖金", esc(rec.get("prize") or "以官方页面为准")),
        ("赛道", esc("、".join(rec.get("tracks") or [])) or "以官方页面为准"),
        ("AI 相关度", esc(LEVEL_LABEL.get(common.ai_level(rec), "AI 相关综合赛事"))),
        ("数据来源", esc(src or "人工核验")),
    ]
    kv_html = "".join(f'<div class="row"><dt>{k}</dt><dd>{v}</dd></div>' for k, v in kv)
    verify_state = "已确认可打开" if rec.get("verify_state") == "ok" else "待确认（可能被防爬拦截）"
    code = f"（HTTP {rec.get('verify_code')}）" if rec.get("verify_code") else ""
    evidence = (f'<div class="vline">依据 <b>{esc(rec.get("evidence"))}</b></div>'
                if rec.get("evidence") else "")
    cta_label = "查看官方页面" if status == "closed" else "前往官方报名页"
    google_url = google_calendar_url(rec)
    has_cal = bool(rec.get("start_date") or rec.get("deadline"))
    cal_buttons = ""
    if google_url:
        cal_buttons += (f'<a class="btn ghost" href="{esc(google_url)}" target="_blank" rel="noopener">'
                        'Google 日历</a>')
    if has_cal:
        cal_buttons += (f'<a class="btn ghost" href="{esc(rec["id"])}.ics" '
                        f'download="ai-race-radar-{esc(rec["id"])}.ics">下载 .ics</a>')
    summary = (rec.get("summary") or "").strip()
    notes = (rec.get("notes") or "").strip()
    if summary or notes:
        inner = f'<p>{esc(summary)}</p>' if summary else ""
        if notes:
            inner += f'<p class="section-note">收录备注：{esc(notes)}</p>'
        summary_html = f"""
  <section class="race-section">
    <h2>活动简介</h2>
    {inner}
  </section>"""
    else:
        parts = []
        org = (rec.get("organizer") or "").strip()
        if org and org not in ("待确认", "主办方待确认"):
            parts.append(f"主办方：{org}")
        mode = common.MODE_LABEL.get(rec.get("mode") or "", "待确认")
        if mode:
            parts.append("形式：" + mode + (f" · {rec['city']}" if rec.get("city") and rec.get("mode") != "online" else ""))
        if rec.get("tracks"):
            parts.append("赛道：" + "、".join(str(t) for t in rec["tracks"]))
        if rec.get("deadline"):
            parts.append("报名截止：" + fmt_date(rec["deadline"]))
        elif rec.get("start_date"):
            parts.append("比赛开始：" + fmt_date(rec["start_date"]))
        if rec.get("prize"):
            parts.append("奖金：" + str(rec["prize"]))
        brief = "；".join(parts) if parts else "官方页暂未提供可用的活动简介，报名与规则请以官方页为准。"
        summary_html = f"""
  <section class="race-section">
    <h2>活动简介</h2>
    <p>{esc(brief)}</p>
    <p class="section-note">官方页未提供独立简介；以上为已核验字段摘要，不替代主办方原文。</p>
  </section>"""
    agenda = agenda_html(rec)
    related = related_html(rec)
    source = source_block(rec)
    jsonld = event_jsonld(rec)
    desc = summary[:140] if summary else (rec.get("title") or "")
    return head(f"{rec.get('title')} · {SITE_NAME}", desc, depth=1) + f"""
<div class="crumbs"><a href="../index.html">← 全部赛事</a> <span class="crumb-sep">/</span> <a href="../explore.html">探索</a></div>
<article class="race">
  <div class="meta-line">
    <span class="pill {esc(status)}"><i class="st {esc(status)}"></i>{esc(status_label)}</span>
    <span>{esc(mode)}{f' · {esc(city)}' if city else ''}</span>
    <span>{esc(countdown(rec))}</span>
  </div>
  <h1>{esc(rec.get('title'))}</h1>
  <div class="org"><span>{organizer}</span><span>·</span><span>{esc(fmt_date(rec.get('start_date')))}</span></div>
  <div class="cta">
    <a class="btn primary" href="{esc(rec.get('url'))}" target="_blank" rel="noopener nofollow">{cta_label} ↗</a>
    {cal_buttons}
  </div>
  <div class="cta-note">或 <a href="../calendar.html">订阅全部赛事日历</a>（加入手机 / 电脑日历后自动同步）</div>
  <div class="race-body">
    <dl class="kv">{kv_html}</dl>
    <aside class="verify">
      <div class="vhead">VERIFICATION</div>
      <div class="vline">链接 <b>{esc(verify_state)}{esc(code)}</b></div>
      <div class="vline">核验 <b>{esc(rec.get("verified_at") or "未知")}</b></div>
      <div class="vline">收录 <b>{esc(rec.get("last_seen") or "未知")}</b></div>
      {evidence}
      <div class="vnote">链接可打开 ≠ 赛事信息完全一致；报名、资格与奖金以主办方官方页面为准。</div>
    </aside>
  </div>
  {summary_html}
  {agenda}
  {related}
  {source}
  {jsonld}
</article>""" + foot(depth=1)


FAQ_ITEMS = [
    ("链接能打开，为什么不等于信息都核实过？",
     "「已确认可打开」只代表我们在核验时请求到了 200/301。赛事日期、奖金、参赛资格和报名状态仍可能变化，"
     "详情页会分别标注「链接核验时间」和「页面更新时间」，最终以主办方官方页面为准。"),
    ("为什么有的报名截止显示「待确认」？",
     "官方页面没有给出明确截止日，或页面是动态渲染、我们拿不到可靠字段。我们宁可写「待确认」，也不猜一个日期。"),
    ("为什么只收这些赛事？",
     "只收 AI 相关、且有公开可访问官方链接的赛事。非 AI 综合赛、私域扫码报名、只有截图没有官方页的线索不进公开列表；"
     "线索会留在内部队列，拿到官方页并实测 200 后再收录。"),
    ("已结束的赛事保留多久？",
     "结束后 14 天内仍在首页；14–90 天保留详情页与 API/存档；超过 90 天从站点下线，但仍保留在全量 JSON 与去重账本里。"),
    ("页面更新时间和主办方公告时间有什么区别？",
     "页面更新时间是本站构建/复核页面的时间，不是主办方发布或修改规则的时间。主办方可能在我们核验之后调整信息，报名前请再看一次官方页。"),
    ("数据可以转载或引用吗？",
     "可以，许可为 CC BY 4.0，请署名「AI 赛事雷达」并附核验时间；涉及具体赛事事实时，请优先引用主办方官方页面。"),
    ("主办方如何纠错、认领或要求下架？",
     "从任意详情页点「提交纠错」，或到提交页填写官方链接与要修改的字段；核对官方页后 24 小时内处理。主办方要求下架会即时处理。"),
    ("为什么没有报名人数、热度排名？",
     "我们没有站内报名系统，也没有可靠的全量报名数据；不展示无法核实的社交证明。"),
]


def faq_html() -> str:
    items = "".join(
        f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>"
        for q, a in FAQ_ITEMS
    )
    return f'<div class="faq">{items}</div>'


def faq_jsonld() -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in FAQ_ITEMS
        ],
    }
    return _json_script(data)


ABOUT_BODY = """
<div class="crumbs"><a href="index.html">← 返回首页</a></div>
<article class="prose">
<h1>方法与信源</h1>
<p class="lead">{name} 只做一件事：把中国境内的 AI 赛事与黑客松整理成一份<strong>能点开、能报名、日期对得上</strong>的清单，并且每天复核一次。</p>

<h2 id="verify"><span>01</span>我们怎么核验</h2>
<ul>
<li><strong>每条必须带官方链接</strong>：报名 / 详情页优先，链接实测返回 200/301 才算「已确认」；被反爬拦截（403/405/429）标注「待确认」，不会当成有效链接展示。</li>
<li><strong>「已确认」只指链接可打开</strong>：HTTP 200 是链接核验，不代表赛事日期、奖金、资格与官方页完全一致；详情页会分别标注「链接核验时间」和「页面更新时间」，最终以主办方官方页为准。</li>
<li><strong>标题与日期以官方页面为准</strong>：标题不改写、不夸张；报名截止、比赛时间来自官方页，缺失就写「待确认」，不猜。</li>
<li><strong>只收 AI 相关</strong>：大模型、算法、数据、算力、智能体、AIGC、具身智能等赛道；非 AI 的综合赛事不收。</li>
<li><strong>去重</strong>：同一赛事在多个渠道出现时按官方链接 + 标题指纹合并，只保留一条。</li>
<li><strong>每天 08:00 重跑</strong>：重新核验链接、更新截止状态；过期赛事自动标记「已截止」，死链从列表中移除。</li>
<li><strong>已结束赛事保留 90 天</strong>：结束 14 天内仍在首页（便于回看），14–90 天保留详情页与数据存档，超过 90 天下线；历史可从全量 JSON 检索。</li>
</ul>

<h2 id="sources"><span>02</span>信源</h2>
<ul>
<li>官方赛事平台：天池、讯飞开放平台、DataFountain、百度 AI Studio 等；</li>
<li>黑客松平台与活动平台：DoraHacks、活动行、Luma 社区日历；</li>
<li>主办方自有活动站：如知乎黑客松的 event 子域（带官方 JSON 活动数据，直接解析）；</li>
<li>主办方官网与官方公众号（人工核验）；</li>
<li>小红书 / 微信群 / 公众号私域信息：只进「线索队列」，拿到官方报名页并实测 200 后才收录；</li>
<li>公开可访问的赛事聚合页，仅作线索，必须回到官方页确认后才收录。</li>
</ul>
<p>我们不使用「让大模型直接生成赛事信息」的方式，因为那样会产出大量打不开的链接——聚合的价值在于<strong>核验</strong>，不在于条数。</p>

<h2 id="scope"><span>03</span>收录口径：泛赛事里的 AI 怎么算</h2>
<p>很多黑客松主题是综合的（Web3、硬件、开源、消费），只有一部分赛道涉及 AI。我们按<strong>证据分级</strong>，不按标题一刀切：</p>
<ul>
<li><strong>AI 核心赛事</strong>：标题或主题本身是 AI（大模型、智能体、具身、算法、AIGC 等），整场按 AI 收录。</li>
<li><strong>综合赛 · 含 AI 赛道</strong>：标题是泛主题，但官方报名页的赛道、题目或评审标准里明确有 AI 方向——收录，并在列表上标注「含 AI 赛道」，赛道字段只写 AI 相关部分。</li>
<li><strong>AI 平台赛事</strong>：天池、讯飞、DataFountain、AI Studio 等平台上的比赛，平台场景本身就是 AI。</li>
</ul>
<p>判断只采信官方页面的赛道 / 题目 / 技术栈，不采信宣传语里的「AI 赋能」；拿不到赛道信息、又无法确认是 AI 的，宁可不收。</p>

<h2 id="data"><span>04</span>数据接口</h2>
<ul>
<li><a href="api/events.json">api/events.json</a>：赛事 JSON（在架 + 近 90 天已结束，含字段说明、更新时间、AI 分级）</li>
<li><a href="api/events.md">api/events.md</a>：同一份数据的 Markdown 版（给 LLM / Agent 省 token）</li>
<li><a href="data/hot.json">data/hot.json</a>：首页「本周值得看」5 条（编辑精选，不是流量榜）</li>
<li><a href="data/races.json">data/races.json</a>：全量核验数据（含已下线，供分析 / 存档）</li>
<li><a href="calendar.html">calendar.html</a>：日历订阅（一键加入 Apple / Outlook / Google，含报名截止提醒）</li>
<li><a href="feed.xml">feed.xml</a>：RSS（给阅读器 / Agent）</li>
<li><a href="llms.txt">llms.txt</a>：写给 AI 搜索 / 代理读取的站点说明</li>
<li><a href="llms-full.txt">llms-full.txt</a>：完整版 AI reference（字段、核验语义、引用边界）</li>
<li><a href="agent.json">agent.json</a> / <a href=".well-known/agent.json">.well-known/agent.json</a>：Agent 能力清单</li>
<li><a href="sitemap.xml">sitemap.xml</a>：站点地图</li>
</ul>
<p>引用请带上「数据来自 AI 赛事雷达 · 核验时间」；数据许可：CC BY 4.0（署名）。</p>

<h2 id="subscribe"><span>05</span>订阅与接入</h2>
<p>按习惯选一个即可，所有方式都来自同一份每日核验数据：</p>
<ul>
<li><strong>日历订阅（推荐）</strong>：打开 <a href="calendar.html">订阅页面</a>，按你的日历点一下即可；不用先下载 .ics 再导入。Apple / iPhone 可直接打开 <a href="{webcal}">webcal:// 链接</a>；Google 日历需要复制链接后粘贴一次；Outlook 可一键打开订阅。</li>
<li><strong>单场加入</strong>：每场详情页有「Google 日历 / 下载 .ics」，适合只加一两场。</li>
<li><strong>邮件摘要</strong>：{subscribe}</li>
<li><strong>Agent / RSS</strong>：<a href="api/events.json">api/events.json</a>（结构化数据）、<a href="feed.xml">feed.xml</a>（RSS）、<a href="llms.txt">llms.txt</a>（给 AI 的站点说明）。Agent 直接 GET JSON，按 <strong>status</strong> 过滤即可。</li>
</ul>

<h2 id="contribute"><span>06</span>提交赛事 / 纠错</h2>
<p>发现遗漏或信息有误，欢迎在 <a href="submit.html">提交页面</a> 填官方链接与说明；我们核对官方页面后 24 小时内更新。主办方要求修正口径或下架，也走同一个入口。</p>

<h2 id="disclaimer"><span>07</span>免责声明</h2>
<p>本站仅做公开信息整理，不代收费用、不代办报名、不构成任何报名建议；所有赛事的资格、奖金与规则均以主办方官方页面为准。若主办方要求下架，请联系我们即刻处理。</p>

<h2 id="faq"><span>08</span>常见问题</h2>
{faq}
{faq_jsonld}
</article>
"""


def render_about() -> str:
    sub = subscribe_html()
    body = (ABOUT_BODY.replace("{name}", SITE_NAME)
            .replace("{webcal}", esc(WEBCAL_URL))
            .replace("{site_url}", esc(SITE_URL))
            .replace("{subscribe}", sub)
            .replace("{faq}", faq_html())
            .replace("{faq_jsonld}", faq_jsonld()))
    return head(f"方法与信源 · {SITE_NAME}", "AI 赛事雷达的核验标准、信源、数据接口与订阅方式。",
                page="about") + body + foot()


def render_submit() -> str:
    note = ("填写后点「生成投稿」，会打开你的邮件客户端并带上内容。"
            if SUBMIT_EMAIL else
            "邮箱上线后自动发送；现在点按钮会把内容复制到剪贴板，直接粘贴到微信 / 邮件即可。")
    return head(f"提交赛事 · {SITE_NAME}",
                "发现漏收的 AI 赛事或信息有误？把官方链接发给我们，核对后 24 小时内更新。",
                page="submit") + f"""
<div class="crumbs"><a href="index.html">← 返回首页</a></div>
<article class="prose">
  <h1>提交赛事</h1>
  <p class="lead">发现漏收、信息有误，或者你就是主办方？填完发给我们。核对官方页面后 24 小时内上站或更正——收录不收费，也不接受只有截图、没有官方链接的投稿。</p>
  <form class="form" id="submit-form" data-email="{esc(SUBMIT_EMAIL)}">
    <div class="field">
      <label for="f-name">赛事名称 <span class="req">*</span></label>
      <input id="f-name" required placeholder="例：Spatial Joy 2026 Rokid 全球开发大赛">
    </div>
    <div class="field">
      <label for="f-url">官方链接 <span class="req">*</span></label>
      <input id="f-url" required placeholder="报名页 / 详情页，必须是主办方官方页面">
      <div class="hint">推文、海报、活动行转发页不算官方链接；需要能打开并看到赛事信息。</div>
    </div>
    <div class="field">
      <label for="f-org">主办方</label>
      <input id="f-org" placeholder="公司 / 高校 / 社区">
    </div>
    <div class="field">
      <label for="f-deadline">报名截止</label>
      <input id="f-deadline" type="date">
    </div>
    <div class="field">
      <label for="f-note">补充说明</label>
      <textarea id="f-note" placeholder="线上还是线下、赛道、奖金、你与赛事的关系（参赛者 / 主办方 / 路过）"></textarea>
    </div>
    <div class="form-actions">
      <button class="btn primary" type="submit">生成投稿 →</button>
      <button class="btn ghost" type="button" id="copy-btn">复制内容</button>
      <span class="form-msg" id="form-msg"></span>
    </div>
    <div class="hint">{note}<br>已经收录但信息有误？同样填在这里，注明「纠错」即可。</div>
  </form>

  <h2 id="rules"><span>01</span>我们怎么处理投稿</h2>
  <ul>
    <li><strong>先核验，再上站</strong>：打开官方链接确认赛事真实存在、日期与报名入口对得上；打不开的链接不会收录。</li>
    <li><strong>只收 AI 相关</strong>：标题或赛道涉及大模型、智能体、具身、算法、AIGC 等；泛赛事里明确含 AI 赛道的会标注「含 AI 赛道」。</li>
    <li><strong>24 小时内回复</strong>：能收录的直接进列表；不收录会说明原因（非 AI、链接失效、信息不足）。</li>
    <li><strong>主办方校对</strong>：如果你是主办方，可要求我们按官方口径修正标题、日期、奖金与报名入口。</li>
  </ul>

  <h2 id="more"><span>02</span>更快的通道</h2>
  <p>公众号 / 私域赛事（扫码报名、审核制）也欢迎投稿：请附上官方报名页或主办方公众号文章链接，我们会进线索队列人工核验。</p>
  <p>也可以用 <a href="api/events.json">公开 JSON</a> 或 <a href="llms.txt">llms.txt</a> 直接读全量数据；发现错漏时把对应条目 id 一起发来，定位更快。</p>
</article>""" + foot()
