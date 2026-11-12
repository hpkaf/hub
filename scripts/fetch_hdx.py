#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""活动行（Huodongxing）AI 黑客松抓取（仅 Python3 标准库）。

关键发现：
- 搜索页 https://www.huodongxing.com/search?qs=AI黑客松 的**结果列表是服务端渲染的**，
  每张卡片为 <a class="item-title" href="/event/{id}?... " title="标题">。
- 详情页 https://www.huodongxing.com/event/{id} 内嵌 `var ativityJson = {...}`（完整 JSON，
  含 Title/Start/End/City/Address/Tag/Organizers）与 `var OrganizerList = [...]`（主办方名称）。
用法: python3 scripts/fetch_hdx.py
输出: data/candidates_hack.json（合并 source=huodongxing 的条目）
"""
import html as htmllib
import json
import os
import re
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone, timedelta

BASE = "https://www.huodongxing.com"
SEARCH_URL = "https://www.huodongxing.com/search?qs=" + urllib.parse.quote("AI黑客松")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "hack")
OUT = os.path.join(ROOT, "data", "candidates_hack.json")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

AI_KEYS = ["ai", "人工智能", "大模型", "llm", "agent", "智能体", "aigc", "gpt",
           "机器学习", "生成式", "大语言", "智能", "机器人", "黑客松", "hackathon"]


def http_get(url, accept="text/html"):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": accept,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace")


def ms_to_date(v):
    """活动行时间格式 '/Date(1794013200000)/' -> 'YYYY-MM-DD'（北京时间）。"""
    if not v:
        return None
    m = re.search(r"/Date\((\d+)\)/", str(v))
    if not m:
        return None
    try:
        ts = int(m.group(1)) / 1000.0
        return datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    except (ValueError, OSError):
        return None


def extract_json_var(text, varname):
    """从 HTML 内嵌 JS 中解析 `var {varname} = <json>;`。"""
    m = re.search(r"var\s+%s\s*=\s*" % re.escape(varname), text)
    if not m:
        return None
    s = text[m.end():]
    try:
        obj, _ = json.JSONDecoder().raw_decode(s)
        return obj
    except ValueError:
        return None


def parse_search(page_html):
    """返回 [(event_id, title, card_html)]；标题来自真实卡片 title 属性，去重。"""
    res = []
    seen = set()
    for m in re.finditer(
            r'<a[^>]+class="item-title"[^>]+href="(/event/(\d+))[^"]*"[^>]*title="([^"]*)"',
            page_html):
        eid, title = m.group(2), htmllib.unescape(m.group(3)).strip()
        if eid not in seen:
            seen.add(eid)
            res.append((eid, title))
    # 兼容属性顺序不同的卡片
    if not res:
        for m in re.finditer(r'title="([^"]+)"[^>]+href="(/event/(\d+))', page_html):
            eid, title = m.group(3), htmllib.unescape(m.group(1)).strip()
            if eid not in seen:
                seen.add(eid)
                res.append((eid, title))
    return res


def parse_detail(eid, title):
    url = "%s/event/%s" % (BASE, eid)
    try:
        code, page = http_get(url)
    except urllib.error.HTTPError as e:
        return None, e.code
    with open(os.path.join(RAW, "hdx_event_%s.html" % eid), "w", encoding="utf-8") as f:
        f.write(page)
    if code not in (200, 301):
        return None, code
    act = extract_json_var(page, "ativityJson") or {}
    orgs = extract_json_var(page, "OrganizerList") or []
    real_title = act.get("Title") or title
    tag = act.get("Tag") or ""
    if not any(k in (real_title + " " + tag).lower() for k in AI_KEYS):
        return None, code
    org_name = None
    ids = act.get("Organizers") or []
    omap = {o.get("Id"): o.get("Name") for o in orgs if isinstance(o, dict)}
    if ids and ids[0] in omap:
        org_name = omap[ids[0]]
    elif orgs and isinstance(orgs[0], dict):
        org_name = orgs[0].get("Name")
    mode = None
    city = act.get("City") or None
    address = act.get("Address") or ""
    if act.get("Mode"):
        mode = {"online": "online", "offline": "offline", "hybrid": "hybrid"}.get(
            str(act["Mode"]).lower(), None)
    if mode is None:
        if city and ("线上" in address or "在线" in address or "直播" in address):
            mode = "online"
        elif city:
            mode = "offline"
    notes = "活动行详情内嵌 ativityJson; 标签=%s; 地址=%s; 状态=%s" % (
        tag or "-", address or "-", act.get("Status"))
    return {
        "title": real_title,
        "organizer": org_name,
        "mode": mode,
        "city": city,
        "start_date": ms_to_date(act.get("Start")),
        "end_date": ms_to_date(act.get("End")),
        "deadline": None,
        "prize": None,
        "tracks": [t for t in re.split(r"[,，]", tag) if t],
        "url": url,
        "source": "huodongxing",
        "source_url": SEARCH_URL,
        "notes": notes,
    }, code


def build():
    os.makedirs(RAW, exist_ok=True)
    st, page = http_get(SEARCH_URL)
    with open(os.path.join(RAW, "huodongxing_search.html"), "w", encoding="utf-8") as f:
        f.write(page)
    cards = parse_search(page)
    print("[hdx] search cards:", len(cards))
    out = []
    for eid, title in cards:
        try:
            row, code = parse_detail(eid, title)
        except (urllib.error.URLError, ValueError) as e:
            print("[hdx] fail", eid, e)
            continue
        if row:
            out.append(row)
        time.sleep(0.3)
    return out


def merge_write(rows):
    existing = []
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                existing = json.load(f)
        except (ValueError, OSError):
            existing = []
    merged = [r for r in existing if r.get("source") != "huodongxing"] + rows
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print("[hdx] rows=%d -> %s (total=%d)" % (len(rows), OUT, len(merged)))


if __name__ == "__main__":
    rows = build()
    merge_write(rows)
    for r in rows:
        print(" ", r["start_date"], r["mode"], r["title"][:50], "|", r["url"])
