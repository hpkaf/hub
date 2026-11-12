#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""搜狗微信文章搜索抓取（仅 Python3 标准库）。

源: https://weixin.sogou.com/weixin?type=2&query=黑客松 （另跑 AI黑客松 补充 AI 相关）
反爬与替代入口（实测）：
1) 桌面 UA 直连 → 302 到 antispider；先 GET 首页取 SUID/ABTEST cookie + Referer 后可得 200；
2) 频控后桌面 cookie 方案也会 302，此时改用 **iPhone 移动端 UA 直连**（实测 200，10 条/页）；
3) 文章 /link?url=... 跳转链：带 Cookie+Referer 仍 302 到 antispider（移动 UA 同样），
   因此按约定使用搜索页 URL 作为 url，并在 notes 注明“跳转链未能还原真实 mp.weixin 地址”。
标题、摘要、发布时间均取自真实 SSR HTML，不编造。
用法: python3 scripts/fetch_sogou.py
输出: data/candidates_hack.json（合并 source=sogou 的条目；若本次 0 条不覆盖旧数据）
"""
import html as htmllib
import json
import os
import re
import time
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
from datetime import datetime, timezone, timedelta

BASE = "https://weixin.sogou.com"
QUERIES = ["黑客松", "AI黑客松"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "hack")
OUT = os.path.join(ROOT, "data", "candidates_hack.json")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
MUA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 "
       "(KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1")

AI_KEYS = ["ai", "人工智能", "大模型", "llm", "智能体", "agent", "aigc", "gpt",
           "机器学习", "生成式", "大语言", "智能", "机器人", "科技", "黑客松", "hackathon"]

_cj = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_cj))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_get(url, referer=None, ua=UA, cookies=True):
    headers = {"User-Agent": ua, "Accept": "text/html",
               "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    op = _opener if cookies else urllib.request.build_opener()
    with op.open(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace")


def search_url(q):
    return "%s/weixin?type=2&query=%s" % (BASE, urllib.parse.quote(q))


def parse_results(page):
    """解析真实搜索结果条目：标题、跳转链、摘要、发布时间（timeConvert epoch）。"""
    out = []
    for m in re.finditer(r'<li[^>]*id="sogou_vr_[^"]*"[^>]*>(.*?)</li>', page, re.S):
        block = m.group(1)
        tm = re.search(r'<h3>\s*<a[^>]*href="(/link\?url=[^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not tm:
            continue
        link = htmllib.unescape(tm.group(1))
        title = htmllib.unescape(re.sub(r"<[^>]+>", "", tm.group(2))).strip()
        if not title:
            continue
        sm = re.search(r'<p class="txt-info"[^>]*>(.*?)</p>', block, re.S)
        snippet = htmllib.unescape(re.sub(r"<[^>]+>", "", sm.group(1))).strip() if sm else ""
        dm = re.search(r"timeConvert\('(\d{9,11})'\)", block)
        if dm:
            try:
                pubdate = datetime.fromtimestamp(
                    int(dm.group(1)), tz=timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
            except (ValueError, OSError):
                pubdate = None
        else:
            dm2 = re.search(r'>\s*(\d{4}-\d{2}-\d{2})\s*<', block)
            pubdate = dm2.group(1) if dm2 else None
        out.append({"link": link, "title": title, "snippet": snippet, "pubdate": pubdate})
    return out


def fetch_search(q):
    """返回 (page_html, route)，route 记录使用的入口策略。"""
    su = search_url(q)
    # 策略1：桌面 UA + 首页 cookie + Referer
    try:
        http_get(BASE + "/", referer=None)
        st, page = http_get(su, referer=BASE + "/")
        if parse_results(page):
            return page, "desktop-cookie", su
    except urllib.error.URLError as e:
        print("[sogou] desktop route fail:", e)
    # 策略2：iPhone 移动端 UA 直连（无 cookie）
    try:
        st, page = http_get(su, referer=None, ua=MUA, cookies=False)
        if parse_results(page):
            return page, "mobile-ua", su
    except urllib.error.URLError as e:
        print("[sogou] mobile route fail:", e)
    # 策略3：桌面 UA 无 cookie 直连
    try:
        st, page = http_get(su, referer=None, cookies=False)
        return page, "desktop-plain", su
    except urllib.error.URLError as e:
        print("[sogou] plain route fail:", e)
    return "", "failed", su


def resolve_link(link, referer, ua):
    """尝试还原跳转链真实地址；失败返回 (None, 状态说明)。"""
    url = link if link.startswith("http") else BASE + link
    op = urllib.request.build_opener(_NoRedirect(), urllib.request.HTTPCookieProcessor(_cj))
    req = urllib.request.Request(url, headers={
        "User-Agent": ua, "Accept": "text/html",
        "Accept-Language": "zh-CN,zh;q=0.9", "Referer": referer,
    })
    try:
        with op.open(req, timeout=20) as r:
            code, headers, body = r.status, r.headers, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        code = e.code
        headers = e.headers
        body = e.read().decode("utf-8", "replace") if e.fp else ""
    except urllib.error.URLError:
        return None, "resolve-error"
    loc = headers.get("Location") if headers else None
    if code in (301, 302) and loc:
        if "mp.weixin.qq.com" in loc:
            return loc, "resolved"
        if "antispider" in loc:
            return None, "antispider"
        return None, "redirect-other:%s" % loc[:80]
    if code == 200:
        m = re.search(r'(https?://mp\.weixin\.qq\.com/s\?[^"\'\s<>]+)', body)
        if m:
            return htmllib.unescape(m.group(1)), "resolved-js"
        if "antispider" in body or "请输入验证码" in body:
            return None, "antispider"
        return None, "no-article-url"
    return None, "http-%s" % code


def build():
    os.makedirs(RAW, exist_ok=True)
    rows = []
    seen_titles = set()
    for q in QUERIES:
        page, route, su = fetch_search(q)
        fn = "sogou_search_%s.html" % ("ai" if "AI" in q else "base")
        with open(os.path.join(RAW, fn), "w", encoding="utf-8") as f:
            f.write(page)
        results = parse_results(page)
        print("[sogou] query=%s route=%s results=%d" % (q, route, len(results)))
        ua = MUA if route == "mobile-ua" else UA
        for r in results:
            title = r["title"]
            blob = (title + " " + r["snippet"]).lower()
            if not any(k in blob for k in AI_KEYS):
                continue
            if title in seen_titles:
                continue
            seen_titles.add(title)
            real, status = resolve_link(r["link"], su, ua)
            date_note = ("微信文章发布日=%s；" % r["pubdate"]) if r["pubdate"] else ""
            if real:
                url, notes = real, "搜狗微信真实文章链接（mp.weixin.qq.com）；%s%s%s" % (
                    status, date_note, r["snippet"][:80])
            else:
                url, notes = su, ("搜狗文章跳转链未能还原真实 mp.weixin 地址（%s，反爬）；"
                                  "url 为搜索页链接；%s摘要：%s"
                                  % (status, date_note, r["snippet"][:80]))
            rows.append({
                "title": title,
                "organizer": None,
                "mode": None,
                "city": None,
                "start_date": None,
                "end_date": None,
                "deadline": None,
                "prize": None,
                "tracks": [],
                "url": url,
                "source": "sogou",
                "source_url": su,
                "notes": "入口=%s；%s" % (route, notes),
            })
            time.sleep(0.6)
    return rows


def merge_write(rows):
    if not rows:
        print("[sogou] 本次未抓到条目（反爬/频控），保留既有数据，不覆盖输出文件")
        return
    existing = []
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                existing = json.load(f)
        except (ValueError, OSError):
            existing = []
    merged = [r for r in existing if r.get("source") != "sogou"] + rows
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print("[sogou] rows=%d -> %s (total=%d)" % (len(rows), OUT, len(merged)))


if __name__ == "__main__":
    rows = build()
    merge_write(rows)
    for r in rows:
        print(" ", r["title"][:50], "|", r["url"][:70], "|", r["notes"][:60])
