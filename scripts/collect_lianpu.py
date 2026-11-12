#!/usr/bin/env python3
"""联谱 lianpu.com 线索采集：只进线索队列，不直接上站。

原因：联谱是活动聚合页，报名方式多为「扫码」或主办方私域，没有稳定公开报名链接，
不满足本站「官方链接必须实测 200」的红线，所以只作为待核验线索。
数据：城市 AI 主题页内嵌 schema.org ItemList（name + url），每页 50 条。
"""
import re
import sys
from pathlib import Path

import common

HERE = Path(common.ROOT)
OUT = HERE / "data" / "leads_lianpu.json"

# 只对「比赛/黑客松」类线索入队，聚会/大会/纯工作坊不占队列
COMP = re.compile(r"黑客松|hackathon|大赛|挑战赛|竞赛|比赛|开发赛|马拉松|创作赛|创意赛", re.I)

TOPICS = [
    ("上海", "https://lianpu.com/topics/shanghai-ai"),
    ("北京", "https://lianpu.com/topics/beijing-ai"),
    ("深圳", "https://lianpu.com/topics/shenzhen-ai"),
    ("杭州", "https://lianpu.com/topics/hangzhou-ai"),
    ("重庆", "https://lianpu.com/topics/chongqing-ai"),
]


def parse_itemlist(html: str) -> list[dict]:
    items = []
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        if '"ItemList"' not in block:
            continue
        try:
            data = common.load_json.__globals__["json"].loads(block) if False else __import__("json").loads(block)
        except Exception:
            continue
        for el in data.get("itemListElement") or []:
            name = (el.get("name") or "").strip()
            url = (el.get("url") or "").strip()
            if name and url.startswith("https://lianpu.com/event/"):
                items.append({"title": name, "url": url})
    return items


def main() -> int:
    existing = {x.get("url") for x in (common.load_json(str(OUT), []) or [])}
    leads, seen = [], set(existing)

    for city, topic in TOPICS:
        code, _, html = common.http_get(topic)
        if code != 200:
            print(f"[lianpu] {city} HTTP {code}，跳过")
            continue
        items = parse_itemlist(html)
        new = 0
        for it in items:
            if not COMP.search(it["title"]):
                continue
            if it["url"] in seen:
                continue
            seen.add(it["url"])
            leads.append({
                "title": it["title"],
                "city": city,
                "url": it["url"],
                "source": "lianpu",
                "source_url": topic,
                "status": "pending",
                "status_note": "联谱聚合页；需找到主办方官方报名页后再决定是否收录",
                "first_seen": common.now_iso(),
            })
            new += 1
        print(f"[lianpu] {city}: {len(items)} 条，新增 {new} 条线索")

    all_leads = (common.load_json(str(OUT), []) or []) + leads
    common.save_json(all_leads, OUT)
    print(f"[lianpu] 线索队列共 {len(all_leads)} 条 → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
