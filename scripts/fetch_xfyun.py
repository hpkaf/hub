#!/usr/bin/env python3
"""抓取讯飞 AI 开发者大赛（challenge.xfyun.cn）当前赛事 -> data/candidates_comp.json

数据源：讯飞官方 JSON API（contests-list），详情页 topic/info 服务端返回 200 壳页
仅使用 Python3 标准库。用法：python3 scripts/fetch_xfyun.py
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

SOURCE = "xfyun"
SOURCE_URL = "https://challenge.xfyun.cn/competition"
LIST_API = "https://challenge.xfyun.cn/2020/ai-contest/api/contests/contests-list"
DETAIL = "https://challenge.xfyun.cn/topic/info?type={flag}"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
RAW = os.path.join(DATA, "raw", "comp")
OUT = os.path.join(DATA, "candidates_comp.json")

TYPE_NAMES = {"algorithem": "算法赛", "application": "应用赛", "train": "练习赛"}


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


def parse_date(value):
    if not value or str(value).startswith("1999"):
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(value))
    return "%s-%s-%s" % (m.group(1), m.group(2), m.group(3)) if m else None


def fmt_prize(bonus):
    try:
        value = float(bonus)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    text = ("%g" % value)
    return "%s万元" % text


def main():
    code, body = fetch(LIST_API, {"Referer": "https://challenge.xfyun.cn/competition",
                                  "X-Requested-With": "XMLHttpRequest",
                                  "Accept": "application/json, text/plain, */*"})
    if code != 200:
        raise RuntimeError("list api HTTP %s" % code)
    payload = json.loads(body.decode("utf-8", "replace"))
    save_raw("xfyun_contests_list.json", body)
    rows = payload.get("data") or []
    print("[xfyun] api rows=%d" % len(rows))

    code, html = fetch(SOURCE_URL)
    save_raw("xfyun_competition.html", html)

    # status: 0=未开始 1=已结束 2=进行中（按日期与实测数据推断）
    current = [r for r in rows if str(r.get("status")) in ("0", "2")]
    current.sort(key=lambda r: parse_date(r.get("registerEnd_basic_problem")) or "9999-12-31")
    # 近期已结束的正式赛（非练手赛，决赛在 2026-09-20 之后），作为“近期赛事”补充
    recent_ended = [
        r for r in rows
        if str(r.get("status")) == "1"
        and (r.get("type_basic_problem") or "").strip() != "train"
        and (parse_date(r.get("finalEnd_basic_problem")) or "") >= "2026-09-20"
    ]
    recent_ended.sort(key=lambda r: parse_date(r.get("finalEnd_basic_problem")) or "", reverse=True)
    ordered = current[:6] + recent_ended

    def norm(r):
        flag = (r.get("contest_flag") or "").strip()
        external = (r.get("external_link") or "").strip()
        url = external or (DETAIL.format(flag=flag) if flag else None)
        return {
            "title": clean(r.get("name_basic_problem")),
            "organizer": clean(r.get("sponsorName_basic_problem")),
            "mode": None,
            "city": None,
            "start_date": parse_date(r.get("registerBegin_basic_problem")),
            "end_date": parse_date(r.get("finalEnd_basic_problem")) or parse_date(r.get("prelimEnd_basic_problem")),
            "deadline": parse_date(r.get("registerEnd_basic_problem")),
            "prize": fmt_prize(r.get("bonus_basic_problem")),
            "tracks": [x for x in [clean(r.get("industry")),
                                   TYPE_NAMES.get((r.get("type_basic_problem") or "").strip())] if x],
            "url": url,
            "source": SOURCE,
            "source_url": SOURCE_URL,
            "notes": clean("讯飞AI开发者大赛 · %s · 参赛团队 %s" % (
                TYPE_NAMES.get((r.get("type_basic_problem") or "").strip(), "AI赛"),
                r.get("team_count") or "?")),
        }

    items = []
    for r in ordered:
        item = norm(r)
        if not item["title"] or not item["url"]:
            continue
        if not url_ok(item["url"]):
            print("[skip] url not reachable: %s" % item["url"])
            continue
        if item["url"] and len(items) < 2:
            code2, det_html = fetch(item["url"])
            save_raw("xfyun_topic_sample_%s.html" % (len(items) + 1), det_html)
        items.append(item)
        time.sleep(0.2)
        print("  + %s | %s" % (r.get("contest_flag"), item["title"][:40]))
        if len(items) >= 20:
            break

    merge_into_output(items)
    return 0


if __name__ == "__main__":
    sys.exit(main())
