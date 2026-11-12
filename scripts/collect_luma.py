#!/usr/bin/env python3
"""Luma 社区日历采集器。

思路：Luma 没有公开搜索接口，但每个社区日历都有官方 ICS 导出：
    https://api.lu.ma/ics/get?entity=calendar&id=<calendar_api_id>
一份 ICS 含该社区全部活动（标题/起止时间/地点/活动链接/状态），
从 DESCRIPTION 里能取到 https://luma.com/<event-slug> 作为官方页面。

配置：data/luma_calendars.yaml（slug/api_id/name/city/note）
产出：data/candidates_luma.json（待 verify.py 核验）
"""
import re
import sys
from pathlib import Path

import common

HERE = Path(common.ROOT)
CONFIG = HERE / "data" / "luma_calendars.yaml"
OUT = HERE / "data" / "candidates_luma.json"
ICS_API = "https://api.lu.ma/ics/get?entity=calendar&id={api_id}"

# 黑客松/比赛关键词：命中的活动才当候选（社区日历里也有聚会、分享会）
HACK_WORDS = re.compile(
    r"黑客松|hackathon|hack\b|编程马拉松|开发赛|挑战赛|大赛|竞赛|编程赛|比赛|hackathon",
    re.I,
)
URL_RE = re.compile(r"https://(?:luma\.com|lu\.ma)/[A-Za-z0-9]+", re.I)


def resolve_api_id(slug: str) -> str | None:
    """兜底：从日历页面 HTML 里解析 calendar_api_id。"""
    code, _, text = common.http_get(f"https://luma.com/{slug}")
    if code != 200:
        return None
    m = re.search(r'"calendar_api_id":"(cal-[A-Za-z0-9]+)"', text)
    return m.group(1) if m else None


def unfold(line: str) -> str:
    """ICS 折行：续行以空格或 tab 开头。"""
    return re.sub(r"\r?\n[ \t]", "", line)


def parse_vevents(ics: str) -> list[dict]:
    """把 ICS 拆成 [{SUMMARY, DTSTART, DTEND, LOCATION, DESCRIPTION}]。"""
    events = []
    for block in re.split(r"BEGIN:VEVENT", ics)[1:]:
        block = block.split("END:VEVENT")[0]
        block = unfold(block)
        fields = {}
        for line in block.splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            k = k.split(";")[0].strip().upper()
            if k in ("SUMMARY", "DTSTART", "DTEND", "LOCATION", "DESCRIPTION", "UID", "STATUS"):
                fields[k] = v.strip()
        if fields.get("SUMMARY"):
            events.append(fields)
    return events


def ics_date(v: str | None) -> str | None:
    """20261108T013000Z / 20261108 -> 2026-11-08（北京日期）。"""
    if not v:
        return None
    m = re.match(r"(\d{4})(\d{2})(\d{2})", v.replace(":", ""))
    if not m:
        return None
    y, mo, d = m.groups()
    # 带 Z 的时间转北京后可能跨日
    if "T" in v and v.endswith("Z"):
        try:
            import datetime as dt
            t = dt.datetime.strptime(v.replace("Z", ""), "%Y%m%dT%H%M%S")
            t = t.replace(tzinfo=dt.timezone.utc) + dt.timedelta(hours=8)
            return t.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return f"{y}-{mo}-{d}"


def enrich_status(rec: dict) -> None:
    """抓活动页拿报名状态（ICS 不含），sold-out/closed 标记 registration_closed。"""
    try:
        code, _, text = common.http_get(rec["url"])
        if code != 200:
            return
        m = re.search(r'"registration_availability":"([^"]+)"', text)
        if m and m.group(1) in ("sold-out", "closed", "not-open"):
            rec["registration_closed"] = True
    except Exception:
        return


def main() -> int:
    cfg = common.load_yaml(str(CONFIG)) or {}
    calendars = cfg.get("calendars") or []
    today = __import__("datetime").date.today().isoformat()
    out, seen = [], set()
    succeeded = set()

    for cal in calendars:
        slug = cal.get("slug") or ""
        api_id = cal.get("api_id") or ""
        name = cal.get("name") or slug
        city = cal.get("city")
        print(f"[luma] {slug} ...")
        if not api_id:
            api_id = resolve_api_id(slug) or ""
            if api_id:
                print(f"  [resolved] api_id={api_id}（建议写回配置文件）")
        if not api_id:
            print("  [skip] 未拿到 calendar_api_id")
            continue

        code, _, ics = common.http_get(ICS_API.format(api_id=api_id))
        if code != 200 or "BEGIN:VCALENDAR" not in ics:
            print(f"  [skip] ICS HTTP {code}")
            continue
        events = parse_vevents(ics)
        succeeded.add(slug)
        kept = 0
        for ev in events:
            title = (ev.get("SUMMARY") or "").strip()
            start = ics_date(ev.get("DTSTART"))
            end = ics_date(ev.get("DTEND")) or start
            if not start or start < today:
                continue
            if common.EXCLUDE_TITLE.search(title):
                continue
            # AI 社区日历本身即证据：整本日历都收；非 AI 社区只收关键词命中的
            if not (cal.get("ai") or HACK_WORDS.search(title) or common.is_ai({"title": title, "tracks": []})):
                continue
            m = URL_RE.search(ev.get("DESCRIPTION") or "")
            if not m:
                continue
            url = m.group(0)
            if url in seen:
                continue
            rec = {
                "title": title,
                "organizer": name,
                "mode": "offline" if cal.get("city") and cal.get("city") != "线上" else "online",
                "city": None if cal.get("city") in (None, "线上") else cal.get("city"),
                "start_date": start,
                "end_date": end if end != start else None,
                "deadline": None,
                "prize": None,
                "tracks": [],
                "url": url,
                "source": "luma",
                "source_url": f"https://luma.com/{slug}",
                "notes": f"Luma 日历：{name}",
                "evidence": f"Luma ICS（{api_id}）",
            }
            rec = common.normalize_record(rec)
            enrich_status(rec)
            seen.add(url)
            out.append(rec)
            kept += 1
        print(f"  [ok] {len(events)} 个活动 → 保留 {kept} 条")

    # 本轮失败/跳过的日历保留上一轮候选，避免一次 ICS 超时清空整个 Luma 源
    old = common.load_json(str(OUT), []) or []
    kept_old = [
        r for r in old
        if isinstance(r, dict)
        and (r.get("source_url") or "").rstrip("/").split("/")[-1] not in succeeded
    ]
    merged, merged_seen = [], set()
    for rec in kept_old + out:
        url = rec.get("url")
        if not url or url in merged_seen:
            continue
        merged_seen.add(url)
        merged.append(rec)

    common.save_json(merged, OUT)
    print(f"[luma] 共 {len(merged)} 条候选（本轮成功日历 {len(succeeded)}/{len(calendars)}，"
          f"保留旧候选 {len(kept_old)} 条）→ {OUT}")
    if not succeeded:
        print("[warn] 所有 Luma 日历均失败，已保留上一轮候选")
        return 1
    for r in merged:
        print(f"      {r.get('start_date') or '?'}  {r['title']}  {r['url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
