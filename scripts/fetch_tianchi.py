#!/usr/bin/env python3
"""抓取天池大数据竞赛（aliyun tianchi）当前赛事 -> data/candidates_comp.json

数据源：天池官方 JSON API（列表 + 详情），以及赛事详情页 SSR 壳（用于验证 url 可达）
仅使用 Python3 标准库。用法：python3 scripts/fetch_tianchi.py
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

SOURCE = "tianchi"
SOURCE_URL = "https://tianchi.aliyun.com/competition/gameList/activeList"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RAW = os.path.join(DATA, "raw", "comp")
OUT = os.path.join(DATA, "candidates_comp.json")

LIST_API = ("https://tianchi.aliyun.com/v3/proxy/competition/api/race/page"
            "?visualTab=&raceName=&pageNum={page}&isActive=1")
DETAIL_API = "https://tianchi.aliyun.com/v3/proxy/competition/api/race/getDetail?raceId={rid}"
DETAIL_PAGE = "https://tianchi.aliyun.com/competition/entrance/{rid}"

TAB_NAMES = {1: "AI大模型赛", 2: "数据算法赛", 3: "工程开发赛", 4: "日常学习赛"}


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
    """实际请求详情页，仅接受 HTTP 200/301。"""
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
    text = re.sub(r"[*#>`]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def extract_organizer(text):
    if not text:
        return None
    m = re.search(r"(?:主办单位|主办方|举办单位|承办单位)\s*[：:]\s*([^\n。；;|]{2,60})", text)
    if not m:
        return None
    return clean(m.group(1))[:60]


def fmt_prize(bonus, currency):
    try:
        value = float(bonus)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    unit = "元" if int(currency or 0) == 0 else "元"
    if value == int(value):
        return "%s%s" % (format(int(value), ","), unit)
    return "%s%s" % (value, unit)


def parse_date(value):
    if not value:
        return None
    value = str(value).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", value)
    return "%s-%s-%s" % (m.group(1), m.group(2), m.group(3)) if m else None


def find_deadline(detail):
    race = detail.get("race") or {}
    timeline = detail.get("raceTimeline") or []
    for tl in timeline:
        for point in tl.get("timePointConfig") or []:
            name = (point.get("name") or "") + (point.get("nameEn") or "")
            if "报名" in str(point.get("name") or "") or "Apply" in name:
                d = parse_date(point.get("time"))
                if d:
                    return d
    for season in detail.get("raceSeasons") or []:
        d = parse_date(season.get("applyEndTime"))
        if d:
            return d
    return parse_date(race.get("signupEndTime"))


def main():
    races = []
    total = None
    page = 1
    while page <= 5:
        data, body = fetch_json(LIST_API.format(page=page),
                                {"Referer": "https://tianchi.aliyun.com/competition/gameList/activeList"})
        if page == 1:
            save_raw("tianchi_race_page_p1.json", body)
        payload = data.get("data") or {}
        batch = payload.get("list") or payload.get("raceList") or []
        total = payload.get("total") or total
        races.extend(batch)
        if not batch or (total is not None and len(races) >= total):
            break
        page += 1
    print("[tianchi] list api pages=%d races=%d total=%s" % (page, len(races), total))

    _, list_html = fetch(SOURCE_URL)
    save_raw("tianchi_active_list.html", list_html)

    items = []
    for race in races:
        rid = race.get("raceId")
        if not rid:
            continue
        detail = {}
        try:
            det_json, det_body = fetch_json(DETAIL_API.format(rid=rid),
                                            {"Referer": DETAIL_PAGE.format(rid=rid)})
            detail = det_json.get("data") or {}
            if len(items) < 2:
                save_raw("tianchi_detail_%s.json" % rid, det_body)
        except Exception as exc:  # noqa: BLE001
            print("[warn] detail failed raceId=%s: %r" % (rid, exc))

        race_info = detail.get("race") or race
        url = DETAIL_PAGE.format(rid=rid)
        if not url_ok(url):
            print("[skip] detail page not reachable: %s" % url)
            continue
        time.sleep(0.2)

        tracks = [t.get("tagNameCn") for t in (race_info.get("tagsList") or []) if t.get("tagNameCn")]
        if not tracks:
            tab_name = TAB_NAMES.get(race_info.get("visualTab"))
            tracks = [tab_name] if tab_name else []
        item = {
            "title": clean(race_info.get("name")),
            "organizer": extract_organizer(race_info.get("introduction")),
            "mode": None,
            "city": None,
            "start_date": parse_date(race_info.get("raceStartTime")),
            "end_date": parse_date(race_info.get("raceEndTime")),
            "deadline": find_deadline(detail) or parse_date(race_info.get("signupEndTime")),
            "prize": fmt_prize(race_info.get("bonus"), race_info.get("currency")),
            "tracks": tracks,
            "url": url,
            "source": SOURCE,
            "source_url": SOURCE_URL,
            "notes": clean("天池 · %s · %s 支队伍" % (TAB_NAMES.get(race_info.get("visualTab"), ""),
                                                  race_info.get("teamCount") or "?")),
        }
        if not item["title"]:
            continue
        items.append(item)
        print("  + %s | %s | deadline=%s" % (rid, item["title"][:40], item["deadline"]))

    merge_into_output(items)
    return 0


if __name__ == "__main__":
    sys.exit(main())
