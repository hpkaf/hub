#!/usr/bin/env python3
"""抓取「平台自有活动站」上的赛事。

有一类赛事不在任何赛事平台（天池/讯飞/DataFountain/AI Studio/DoraHacks/活动行）上架，
只在主办方自己的活动站发布，比如知乎黑客松的 hackathon-s3.event.zhihu.com。
这类站点通常带官方 JSON API，可直接解析成标准赛事记录。

输入：data/event_sites.yaml
输出：data/candidates_events.json（字段契约与 candidates_comp.json 一致）
原始响应：data/raw/events/*.json

用法：python3 scripts/fetch_event_sites.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

SITES_PATH = os.path.join(common.DATA_DIR, "event_sites.yaml")
OUT_PATH = os.path.join(common.DATA_DIR, "candidates_events.json")
RAW_DIR = os.path.join(common.DATA_DIR, "raw", "events")


def _date_from_iso(value: str | None, shift_back_if_midnight: bool = True) -> str | None:
    """'2026-12-05T00:00:00+08:00' -> '2026-12-04'（24:00 视为前一天结束）。"""
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return value[:10]
    if shift_back_if_midnight and parsed.hour == 0 and parsed.minute == 0 and parsed.second == 0:
        parsed = parsed - dt.timedelta(days=1)
    return parsed.date().isoformat()


def zhihu_event(site: dict) -> list[dict]:
    """知乎活动站适配器：/api/content 返回赛事全量结构化数据。"""
    code, final_url, text = common.http_get(site["api"], timeout=25)
    if code != 200:
        raise RuntimeError(f"API {site['api']} 返回 HTTP {code}")

    os.makedirs(RAW_DIR, exist_ok=True)
    raw_name = os.path.join(RAW_DIR, (site.get("name") or "zhihu") + ".json")
    with open(raw_name, "w", encoding="utf-8") as fh:
        fh.write(text)

    data = json.loads(text)
    meta = data.get("meta") or {}
    phases = data.get("phases") or []
    award = data.get("awards") or {}
    tracks = [t.get("name") for t in (data.get("tracks") or []) if t.get("name")]

    if not phases:
        raise RuntimeError("活动站数据里没有 phases，无法确定报名/比赛时间")

    signup = phases[0]
    start_date = _date_from_iso(signup.get("startAt"), shift_back_if_midnight=False)
    deadline = _date_from_iso(signup.get("endAt"))
    last = phases[-1]
    end_date = _date_from_iso(last.get("endAt"))

    title_parts = [meta.get("title") or site["name"], meta.get("season"), meta.get("edition")]
    title = " ".join(p for p in title_parts if p).strip()

    main_awards = award.get("mainAwards") or []
    prize = ""
    if award.get("prizePool"):
        prize = f"总奖金池 {award['prizePool']}"
        if main_awards:
            first = main_awards[0]
            prize += f"（{first.get('name', '')} {first.get('value', '')}）"

    campus = [c.get("school") or c.get("city") or "" for c in (data.get("campusEvents") or [])]
    campus = [c for c in campus if c]
    notes = "官方活动站 " + site["landing"].rstrip("/")
    if campus:
        notes += f"；另有 {len(campus)} 场校园宣讲（{ '、'.join(campus[:4]) } 等，线下）"
    notes += "；报名与作品提交均线上进行"

    record = {
        "title": title,
        "organizer": site.get("organizer") or "待确认",
        "mode": "online",
        "city": None,
        "start_date": start_date,
        "end_date": end_date,
        "deadline": deadline,
        "prize": prize or None,
        "tracks": tracks,
        "url": meta.get("registrationUrl"),
        "source": "zhihu",
        "source_url": site["landing"],
        "notes": notes,
    }
    return [record]


ADAPTERS = {
    "zhihu_event": zhihu_event,
}


def main() -> int:
    common.ensure_dirs()
    conf = common.load_yaml(SITES_PATH) or {}
    sites = conf.get("sites") or []
    if not sites:
        print(f"[warn] {SITES_PATH} 里没有 sites，跳过")
        return 0

    records: list[dict] = []
    ok_sites = 0
    for site in sites:
        kind = site.get("kind")
        adapter = ADAPTERS.get(kind)
        if not adapter:
            print(f"[warn] 未知 kind={kind}（{site.get('name')}），跳过")
            continue
        try:
            got = adapter(site)
            ok_sites += 1
        except Exception as exc:  # noqa: BLE001
            print(f"[fail] {site.get('name')}: {exc}")
            continue
        for item in got:
            records.append(common.normalize_record(item))
        print(f"[ok] {site.get('name')}: {len(got)} 条")

    if ok_sites == 0:
        print(f"[warn] 所有活动站抓取失败，保留上一轮 {OUT_PATH}")
        return 1

    common.save_json(records, OUT_PATH)
    print(f"[ok] 写入 {OUT_PATH}（{len(records)} 条）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
