#!/usr/bin/env python3
"""湾区 AI 日历（wqai.ltd）采集：赛事截止日 + 线索。

wqai 的 calendar.ics 里，「赛事」类条目的 DTSTART 是**报名截止日**，
标题形如「⏰ 报名截止｜XXX」/「📝 报名开始｜XXX」。它不能直接当赛事库用，
但正好能补我们缺的报名截止日（deadline）。处理：
1) 解析所有「报名截止」条目 → 与库内赛事按标题匹配，匹配上的写 data/wqai_deadline_fill.json；
2) 没匹配上的 → data/leads_wqai.json 线索队列（待人工核验官方页）。
"""
import datetime as dt
import re
from pathlib import Path

import common

HERE = Path(common.ROOT)
ICS_URL = "https://wqai.ltd/calendar/calendar.ics"
FILL = HERE / "data" / "wqai_deadline_fill.json"
LEADS = HERE / "data" / "leads_wqai.json"

PREFIX = re.compile(r"^[⏰📝\s]*(报名截止|报名开始)\s*[｜|:：]\s*")
CITY = re.compile(r"赛事\\?,\s*([^,]+)")


def unfold(block: str) -> str:
    return re.sub(r"\n[ \t]", "", block)


def parse(ics: str) -> list[dict]:
    out = []
    for block in re.split(r"BEGIN:VEVENT", ics)[1:]:
        block = unfold(block.split("END:VEVENT")[0])
        f = {}
        for line in block.splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            k = k.split(";")[0].strip().upper()
            if k in ("SUMMARY", "DTSTART", "DTEND", "URL", "CATEGORIES", "DESCRIPTION", "LOCATION"):
                f[k] = v.strip()
        out.append(f)
    return out


def ics_date(v: str) -> str | None:
    m = re.match(r"(\d{4})(\d{2})(\d{2})", (v or "").replace(":", ""))
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def same(a: str, b: str) -> bool:
    """宽松标题匹配：归一化后互相包含且长度接近。"""
    na, nb = common.norm_title(a), common.norm_title(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    short, long_ = sorted((na, nb), key=len)
    return len(short) >= 8 and short in long_ and len(short) / len(long_) >= 0.55


def main() -> int:
    code, _, ics = common.http_get(ICS_URL)
    if code != 200 or "BEGIN:VCALENDAR" not in ics:
        print(f"[wqai] ICS HTTP {code}，跳过")
        return 1
    events = parse(ics)

    races = common.load_json(str(common.DATA_DIR + "/races.json"), []) or []
    fills, leads = [], []
    for ev in events:
        title = (ev.get("SUMMARY") or "").strip()
        m = PREFIX.match(title)
        if not m:
            continue
        name = PREFIX.sub("", title).strip()
        deadline = ics_date(ev.get("DTSTART") or "")
        if not deadline:
            continue
        # 只保留未来的截止日（含今天）
        if deadline < dt.date.today().isoformat():
            continue
        if not common.is_ai({"title": name, "tracks": []}):
            continue
        city_m = CITY.search(ev.get("CATEGORIES") or "")
        city = city_m.group(1) if city_m else None
        if city == "其他":
            city = None
        url = (ev.get("URL") or "").strip() or None

        matched = next((r for r in races if same(r.get("title", ""), name)), None)
        if matched:
            if not matched.get("deadline"):
                fills.append({"id": matched["id"], "title": matched["title"],
                              "deadline": deadline, "wqai_title": name, "url": url})
            continue
        leads.append({"title": name, "deadline": deadline, "city": city, "url": url,
                      "source": "wqai", "source_url": ICS_URL, "status": "pending",
                      "status_note": "湾区AI日历的报名截止条目；需找到官方报名页核验",
                      "first_seen": common.now_iso()})

    # 合并旧线索、去重
    old = common.load_json(str(LEADS), []) or []
    seen = {(x.get("title"), x.get("deadline")) for x in old}
    all_leads = old + [x for x in leads if (x["title"], x["deadline"]) not in seen]
    common.save_json(all_leads, LEADS)
    common.save_json(fills, FILL)
    print(f"[wqai] 截止日条目 {len(events)} 个事件中，可补库内截止日 {len(fills)} 条，新增线索 {len(leads)} 条")
    for x in fills[:10]:
        print(f"      fill  {x['deadline']}  {x['title'][:44]}")
    for x in leads[:10]:
        print(f"      lead  {x['deadline']}  {x['title'][:44]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
