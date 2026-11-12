#!/usr/bin/env python3
"""抓取百度 AI Studio（aistudio.baidu.com）当前/近期赛事 -> data/candidates_comp.json

数据源：AI Studio 官方 JSON API（/studio/match/list，分页参数 p；/studio/match/detail）
仅使用 Python3 标准库。用法：python3 scripts/fetch_aistudio.py
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

SOURCE = "aistudio"
SOURCE_URL = "https://aistudio.baidu.com/competition"
LIST_API = "https://aistudio.baidu.com/studio/match/list?p=%d&pageSize=100"
DETAIL_API = "https://aistudio.baidu.com/studio/match/detail?matchId=%s"
DETAIL_PAGE = "https://aistudio.baidu.com/competition/detail/%s/0/introduction"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RAW = os.path.join(DATA, "raw", "comp")
OUT = os.path.join(DATA, "candidates_comp.json")

# 截止日期过滤：排除 2028-2030 的长期“学习赛”
MAX_END = "2027-06-30"
# 近期已结束赛事的最早结束日期
RECENT_END = "2026-08-01"


def fetch(url, headers=None, timeout=30):
    h = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}
    if headers:
        h.update(headers)
    last = None
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.getcode(), r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()[:2000]
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5)
    raise RuntimeError("fetch failed %s: %r" % (url, last))


def fetch_json(url, headers=None):
    code, body = fetch(url, headers)
    if code != 200:
        raise RuntimeError("HTTP %s for %s" % (code, url))
    return json.loads(body.decode("utf-8", "replace")), body


def save_raw(name, body):
    os.makedirs(RAW, exist_ok=True)
    path = os.path.join(RAW, name)
    if isinstance(body, (bytes, bytearray)):
        with open(path, "wb") as f:
            f.write(body)
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
    print("[raw] %s" % path)


def url_ok(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Accept-Language": "zh-CN,zh;q=0.9"})
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read(1024)
            return r.getcode() in (200, 301)
    except urllib.error.HTTPError as e:
        return e.code in (200, 301)
    except Exception:  # noqa: BLE001
        return False


def merge_into_output(items):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    existing = []
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:  # noqa: BLE001
            existing = []
    if not isinstance(existing, list):
        existing = []
    existing = [x for x in existing if x.get("source") != SOURCE]
    existing.extend(items)
    existing.sort(key=lambda x: (x.get("source") or "",
                                 x.get("deadline") or x.get("end_date") or "9999-12-31"))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print("[%s] wrote %d items -> %s (total %d)" % (SOURCE, len(items), OUT, len(existing)))


def clean(text):
    if not text:
        return None
    text = re.sub(r"<[^>]+>", " ", str(text))
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def norm_date(value):
    """'2026/11/19' -> '2026-11-19'"""
    if not value:
        return None
    m = re.match(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", str(value))
    if not m:
        return None
    return "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3)))


def split_tags(tags):
    if not tags:
        return []
    return [t.strip() for t in re.split(r"[、，,;；/]", str(tags)) if t.strip()]


def extract_organizer(text):
    """从详情 markdown（matchContent）里提取主办单位名称。"""
    if not text:
        return None
    # 形式一：**主办单位**：\n  - 单位名称
    m = re.search(r"(?:主办单位|主办方)\**\s*[：:]\s*\**\s*\n+[\s\-*]*([^\n#]{2,60})", text)
    if m:
        return clean(m.group(1))[:60]
    # 形式二：标题行 "# 主办单位" 后跟若干行单位名
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.fullmatch(r"[#*\s]*(?:主办单位|主办方|联合主办)[#*\s]*", line.strip()):
            vals = []
            for nxt in lines[i + 1:i + 5]:
                value = nxt.strip(" *#-")
                if not value:
                    continue
                if value.startswith("#") or "承办" in value:
                    break
                vals.append(value)
                if len(vals) >= 2:
                    break
            if vals:
                return clean("、".join(vals))[:60]
    return None


def main():
    rows = []
    page = 1
    while page <= 10:
        payload, body = fetch_json(LIST_API % page,
                                   {"Referer": SOURCE_URL})
        if page == 1:
            save_raw("aistudio_match_list_p1.json", body)
        result = payload.get("result") or {}
        batch = result.get("data") or []
        rows.extend(batch)
        total_page = result.get("totalPage") or 1
        print("[aistudio] page=%d rows=%d totalCount=%s totalPage=%s" % (
            page, len(batch), result.get("totalCount"), total_page))
        if not batch or page >= total_page:
            break
        page += 1
        time.sleep(0.2)

    code, html = fetch(SOURCE_URL)
    save_raw("aistudio_competition.html", html)

    selected = []
    for row in rows:
        end = norm_date(row.get("endTime"))
        if not end:
            continue
        title = str(row.get("matchName") or "")
        if "测试" in title:  # 平台内部测试页面，非真实赛事
            continue
        status = str(row.get("processText") or "")
        if status != "已结束":
            if end <= MAX_END:
                selected.append(row)
        elif end >= RECENT_END:
            selected.append(row)
    selected.sort(key=lambda r: norm_date(r.get("endTime")) or "9999-12-31")
    print("[aistudio] selected=%d" % len(selected))

    items = []
    for row in selected[:20]:
        mid = row.get("id")
        if not mid:
            continue
        url = DETAIL_PAGE % mid
        detail = {}
        try:
            detail, det_body = fetch_json(DETAIL_API % mid, {"Referer": SOURCE_URL})
            if len(items) < 2:
                save_raw("aistudio_match_detail_%s.json" % mid, det_body)
        except Exception as exc:  # noqa: BLE001
            print("[warn] detail api failed id=%s: %r" % (mid, exc))
        if not url_ok(url):
            print("[skip] detail page not reachable: %s" % url)
            continue
        result = detail.get("result") or {}
        content_parts = [result.get("matchAbs") or row.get("matchAbs") or ""]
        for block in result.get("matchContent") or []:
            content_parts.append(str(block.get("md") or ""))
        organizer = extract_organizer("\n".join(content_parts))
        status = str(row.get("processText") or "")
        item = {
            "title": clean(row.get("matchName")),
            "organizer": organizer,
            "mode": None,
            "city": None,
            "start_date": norm_date(row.get("startTime")),
            "end_date": norm_date(row.get("endTime")),
            "deadline": None,
            "prize": clean(row.get("reward")),
            "tracks": split_tags(row.get("tags")),
            "url": url,
            "source": SOURCE,
            "source_url": SOURCE_URL,
            "notes": clean("飞桨AI Studio · %s · %s" % (
                status or "", ("参赛 %s 人" % row.get("signupCount")) if row.get("signupCount") else "")),
        }
        if not item["title"]:
            continue
        items.append(item)
        time.sleep(0.2)
        print("  + %s | %s | %s %s" % (mid, item["title"][:40], item["end_date"], status))

    merge_into_output(items)
    return 0


if __name__ == "__main__":
    sys.exit(main())
