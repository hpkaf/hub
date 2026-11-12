# -*- coding: utf-8 -*-
"""首页「本周值得看」：按截止日 + 可核验字段做编辑精选。

不是流量热度榜：我们没有站内报名/浏览数据，不伪造“XX 人关注”。
只从在架赛事里取最近截止的几条，按截止日由近到远排序；
同一天优先有奖金、有主办方的，理由在页面上写清楚。
"""
from __future__ import annotations

import datetime as dt
import re


def _prize_score(text: str | None) -> float:
    """把奖金文案粗略折成人民币，仅用于同日赛事的编辑排序。"""
    text = str(text or "")
    best = 0.0
    for num, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(万|万元|W|w|USD|美元|元|¥|￥)?", text):
        value = float(num)
        unit = unit or ""
        if unit in ("万", "万元", "W", "w"):
            value *= 10000
        elif unit in ("USD", "美元"):
            value *= 7
        best = max(best, value)
    return best


def _days(deadline: str | None, today: dt.date) -> int | None:
    if not deadline:
        return None
    try:
        return (dt.date.fromisoformat(deadline) - today).days
    except (ValueError, TypeError):
        return None


def _when(days: int) -> str:
    if days == 0:
        return "今天截止"
    if days == 1:
        return "明天截止"
    return f"{days} 天后截止"


def picks(records: list[dict], today: dt.date | None = None, limit: int = 5) -> dict:
    today = today or dt.date.today()
    chosen: list[dict] = []
    window = 7
    for window in (7, 14, 30):
        chosen = []
        for rec in records:
            if rec.get("status") not in ("open", "closing", "upcoming"):
                continue
            days = _days(rec.get("deadline"), today)
            if days is None or days < 0 or days > window:
                continue
            chosen.append({
                "rec": rec,
                "days": days,
                "when": _when(days),
                "reason": " · ".join(p for p in [
                    _when(days),
                    rec.get("prize") or "奖金待确认",
                    rec.get("organizer") or "主办方待确认",
                ] if p),
            })
        if len(chosen) >= 3 or window == 30:
            break
    chosen.sort(key=lambda x: (
        x["days"],
        -_prize_score(x["rec"].get("prize")),
        0 if x["rec"].get("organizer") else 1,
        x["rec"].get("title") or "",
    ))
    chosen = chosen[:limit]
    if window == 7:
        label, kicker = "本周值得看", "THIS WEEK"
    elif window == 14:
        label, kicker = "近期值得看", "NEXT 14 DAYS"
    else:
        label, kicker = "接下来值得看", "NEXT 30 DAYS"
    return {"items": chosen, "window": window, "label": label, "kicker": kicker}


def to_public(hot: dict) -> list[dict]:
    out = []
    for item in hot.get("items") or []:
        rec = item["rec"]
        out.append({
            "id": rec["id"],
            "title": rec.get("title"),
            "organizer": rec.get("organizer"),
            "mode": rec.get("mode"),
            "city": rec.get("city"),
            "deadline": rec.get("deadline"),
            "days": item["days"],
            "when": item["when"],
            "prize": rec.get("prize"),
            "reason": item["reason"],
            "url": rec.get("url"),
        })
    return out
