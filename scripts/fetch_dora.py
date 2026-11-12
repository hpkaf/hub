#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DoraHacks 黑客松抓取（仅 Python3 标准库）。

数据源: https://dorahacks.io/api/v1/hub/hackathons （页面 /hackathon 前端实际调用的公开 JSON API）
发现方式: 页面为 Nuxt 空壳(window.__NUXT__={})，从 /_nuxt/entry.*.js 中还原
          dl="https://dorahacks.io/api/v1" + "/hackathons" (backend=hub)。
用法: python3 scripts/fetch_dora.py   （项目根目录执行）
输出: data/candidates_hack.json（合并 source=dorahacks 的条目）
"""
import json
import os
import re
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

BASE = "https://dorahacks.io"
API = "https://dorahacks.io/api/v1/hub/hackathons"
LIST_URL = "https://dorahacks.io/hackathon"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "hack")
OUT = os.path.join(ROOT, "data", "candidates_hack.json")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# AI / 大模型相关关键词（标题/tags/ecosystem 命中才算）
AI_KEYS = ["ai", "人工智能", "大模型", "llm", "agent", "智能体", "aigc", "gpt",
           "machine learning", "机器学习", "deep learning", "深度学习", "大语言",
           "generative", "生成式", "model", "智能", "robot", "机器人", "具身"]
# 明显与 AI 无关的币圈/DeFi 词（用于剔除纯 crypto hackathon）
NON_AI = ["dex", "perps", "defi", "nft", "airdrop", "trading bot", "staking", "token sale"]


def http_get(url, accept="application/json", binary=False):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": accept,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
        return r.status, (data if binary else data.decode("utf-8", "replace"))


def get_json(url):
    st, txt = http_get(url)
    return st, json.loads(txt)


def ts_date(ts):
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, OSError, TypeError):
        return None


def is_ai(item):
    blob = " ".join(str(item.get(k) or "") for k in ("title", "tags", "ecosystem")).lower()
    if any(n in blob for n in NON_AI) and not any(k in blob for k in (" ai", "ai ", "llm", "agent", "智能")):
        return False
    return any(k in blob for k in AI_KEYS)


def collect():
    now = time.time()
    items = {}
    # 1) 正在报名/即将开始的赛事（状态过滤，全量翻页）
    for status in ("ongoing", "upcoming"):
        page = 1
        while page <= 3:
            q = urllib.parse.urlencode({"status": status, "page": page, "page_size": 50})
            st, d = get_json(API + "?" + q)
            for it in d.get("results") or []:
                items[it["id"]] = it
            if not d.get("next"):
                break
            page += 1
            time.sleep(0.3)
    # 2) 搜索 AI 相关赛事，补足候选（只取仍在未来/近期结束的）
    for page in (1, 2):
        q = urllib.parse.urlencode({"search": "AI", "page": page, "page_size": 50})
        st, d = get_json(API + "?" + q)
        for it in d.get("results") or []:
            end = it.get("timeline_end") or 0
            if end and end > now - 7 * 86400:
                items[it["id"]] = it
        time.sleep(0.3)
    return items


def build():
    os.makedirs(RAW, exist_ok=True)
    cand = collect()
    with open(os.path.join(RAW, "dorahacks_api_list.json"), "w", encoding="utf-8") as f:
        json.dump(list(cand.values()), f, ensure_ascii=False)

    out = []
    for hid, it in cand.items():
        if not is_ai(it):
            continue
        uname = it.get("uname")
        if not uname:
            continue
        detail = {}
        try:
            st, detail = get_json(API + "/%s" % hid)
            with open(os.path.join(RAW, "dorahacks_detail_%s.json" % hid), "w", encoding="utf-8") as f:
                json.dump(detail, f, ensure_ascii=False)
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError) as e:
            print("[dora] detail fail", hid, e)
        page_url = "%s/hackathon/%s" % (BASE, uname)
        # 质量红线：详情页必须实际请求到 200/301
        try:
            code, html = http_get(page_url, accept="text/html")
        except urllib.error.HTTPError as e:
            code, html = e.code, ""
        with open(os.path.join(RAW, "dorahacks_page_%s.html" % uname), "w", encoding="utf-8") as f:
            f.write(html)
        if code not in (200, 301):
            print("[dora] skip %s http=%s" % (page_url, code))
            continue

        vf = (detail.get("venue_form") or it.get("venue_form") or "").lower()
        mode = "online" if "virtual" in vf or "online" in vf else ("offline" if vf else None)
        if mode is None and not (detail.get("venue_name") or detail.get("venue_address")):
            mode = "online"  # DoraHacks 无场馆信息的默认按线上
        tracks = []
        for t in detail.get("tracks") or []:
            if isinstance(t, dict) and t.get("name"):
                tracks.append(t["name"])
        prize = None
        if detail.get("bonus_price"):
            prize = "%s %s" % (detail["bonus_price"], detail.get("bonus_token") or "")
        start = ts_date(detail.get("timeline_start") or it.get("timeline_start"))
        end = ts_date(detail.get("timeline_end") or it.get("timeline_end"))
        deadline = None
        pre = detail.get("timeline_pre_register") or 0
        if pre and pre > 0:
            deadline = ts_date(pre)
        city = detail.get("venue_name") or detail.get("venue_address") or None
        notes = "DoraHacks API: tags=%s; ecosystem=%s" % (
            it.get("tags") or "-", it.get("ecosystem") or "-")
        out.append({
            "title": detail.get("title") or it.get("title"),
            "organizer": (detail.get("owner") or it.get("owner") or {}).get("name"),
            "mode": mode,
            "city": city,
            "start_date": start,
            "end_date": end,
            "deadline": deadline,
            "prize": prize,
            "tracks": tracks,
            "url": page_url,
            "source": "dorahacks",
            "source_url": LIST_URL,
            "notes": notes,
        })
        time.sleep(0.4)
    return out


def merge_write(rows):
    existing = []
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                existing = json.load(f)
        except (ValueError, OSError):
            existing = []
    merged = [r for r in existing if r.get("source") != "dorahacks"] + rows
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print("[dora] rows=%d -> %s (total=%d)" % (len(rows), OUT, len(merged)))


if __name__ == "__main__":
    rows = build()
    merge_write(rows)
    for r in rows:
        print(" ", r["start_date"], r["mode"], r["title"][:50], "|", r["url"])
