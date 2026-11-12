#!/usr/bin/env python3
"""抓取 DataFountain 数据科学竞赛（datafountain.cn）近期赛事 -> data/candidates_comp.json

数据源：www.datafountain.cn 官方 JSON API（/api/competitions，page/pageSize）
仅使用 Python3 标准库。用法：python3 scripts/fetch_datafountain.py
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

SOURCE = "datafountain"
SOURCE_URL = "https://www.datafountain.cn/competitions"
LIST_API = "https://www.datafountain.cn/api/competitions?page=%d&pageSize=10"
DETAIL_API = "https://www.datafountain.cn/api/competitions/%s"
DETAIL_PAGE = "https://www.datafountain.cn/competitions/%s"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RAW = os.path.join(DATA, "raw", "comp")
OUT = os.path.join(DATA, "candidates_comp.json")

# 只收录结束日期在该日期之后的 AI 相关赛事（近期/当前）
SINCE = datetime.date(2026, 6, 1)


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


def cn_date(value):
    """ISO/UTC 时间转北京时间日期（YYYY-MM-DD）。"""
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(text)
    except ValueError:
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
        return "%s-%s-%s" % (m.group(1), m.group(2), m.group(3)) if m else None
    if dt.tzinfo is not None:
        dt = dt.astimezone(datetime.timezone(datetime.timedelta(hours=8)))
    return dt.strftime("%Y-%m-%d")


def fmt_prize(reward):
    text = clean(reward)
    if not text:
        return None
    if re.fullmatch(r"\d+(\.\d+)?", text):
        try:
            return "%s元" % format(int(float(text)), ",")
        except ValueError:
            return text
    return text


def find_deadline(detail, record):
    """从详情 API 的 schedules / race.schedules 里找报名截止。"""
    blocks = []
    blocks.extend(detail.get("schedules") or [])
    races = detail.get("race") or {}
    blocks.extend(races.get("schedules") or [])
    for block in blocks:
        title = str(block.get("title") or "")
        if "报名" in title:
            d = cn_date(block.get("endTime"))
            if d:
                return d
    for block in (detail.get("raceSeasons") or []):
        d = cn_date(block.get("applyEndTime"))
        if d:
            return d
    return None


def main():
    rows = []
    total = None
    for page in range(1, 7):
        payload, body = fetch_json(LIST_API % page)
        if page == 1:
            save_raw("datafountain_page1.json", body)
        cmpt = payload.get("cmpt") or {}
        batch = cmpt.get("competitions") or []
        total = cmpt.get("total")
        rows.extend(batch)
        if not batch:
            break
        print("[datafountain] page=%d rows=%d total=%s" % (page, len(batch), total))
        time.sleep(0.2)

    code, list_html = fetch(SOURCE_URL)
    save_raw("datafountain_competitions.html", list_html)

    recent = []
    for row in rows:
        end = cn_date(row.get("endTime"))
        if not end:
            continue
        try:
            end_d = datetime.date.fromisoformat(end)
        except ValueError:
            continue
        if end_d < SINCE:
            continue
        recent.append(row)
    recent.sort(key=lambda r: cn_date(r.get("endTime")) or "9999-12-31")
    print("[datafountain] recent candidates=%d" % len(recent))

    items = []
    for row in recent[:20]:
        cid = row.get("id")
        if not cid:
            continue
        url = DETAIL_PAGE % cid
        if not url_ok(url):
            print("[skip] detail page not reachable: %s" % url)
            continue
        detail = {}
        try:
            detail, det_body = fetch_json(DETAIL_API % cid)
            if len(items) < 2:
                save_raw("datafountain_detail_%s.json" % cid, det_body)
        except Exception as exc:  # noqa: BLE001
            print("[warn] detail api failed id=%s: %r" % (cid, exc))
        organizers = detail.get("organizers") or row.get("organizers") or []
        organizer = None
        for org in organizers:
            role = str(org.get("roleName") or "")
            if "主办" in role:
                organizer = clean(org.get("name"))
                break
        if not organizer and organizers:
            organizer = clean(organizers[0].get("name"))
        tags = detail.get("tags") or row.get("tags") or []
        item = {
            "title": clean(detail.get("title") or row.get("title")),
            "organizer": organizer,
            "mode": None,
            "city": None,
            "start_date": cn_date(detail.get("startTime") or row.get("startTime")),
            "end_date": cn_date(detail.get("endTime") or row.get("endTime")),
            "deadline": find_deadline(detail, row),
            "prize": fmt_prize(detail.get("reward") or row.get("reward")),
            "tracks": [t.get("nameCn") for t in tags if t.get("nameCn")],
            "url": url,
            "source": SOURCE,
            "source_url": SOURCE_URL,
            "notes": clean("DataFountain · %s · 状态：%s" % (
                detail.get("typeLabel") or row.get("typeLabel") or "",
                row.get("state") or "")),
        }
        if not item["title"]:
            continue
        items.append(item)
        time.sleep(0.2)
        print("  + %s | %s | %s" % (cid, item["title"][:40], item["end_date"]))

    merge_into_output(items)
    return 0


if __name__ == "__main__":
    sys.exit(main())
