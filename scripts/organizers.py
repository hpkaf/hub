# -*- coding: utf-8 -*-
"""主办方实体页：把 78 条赛事按 organizer 聚合成 42 个可访问的实体页。"""
from __future__ import annotations

import hashlib
import os
import re

import common

OVERRIDES_PATH = os.path.join(common.DATA_DIR, "organizers.yaml")


def _load_overrides() -> dict[str, dict]:
    if not os.path.exists(OVERRIDES_PATH):
        return {}
    try:
        data = common.load_yaml(OVERRIDES_PATH) or {}
    except Exception:
        return {}
    items = data.get("organizers") if isinstance(data, dict) else data
    out = {}
    for item in items or []:
        if isinstance(item, dict) and item.get("name"):
            out[str(item["name"]).strip()] = item
    return out


def _slug_base(name: str) -> str:
    s = str(name or "").strip().lower()
    s = re.sub(r"[\s&×/]+", "-", s)
    s = re.sub(r"[^a-z0-9-]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    if len(s) >= 3:
        return s[:48]
    return "org-" + hashlib.sha1(str(name).encode("utf-8")).hexdigest()[:8]


def _current(rec: dict) -> bool:
    if rec.get("status") != "closed":
        return True
    ref = rec.get("deadline") or rec.get("end_date") or rec.get("start_date")
    d = common.days_until(ref)
    return d is not None and d >= -14


def _letter(name: str) -> str:
    s = str(name or "").strip()
    return s[0].upper() if s else "?"


def build(records: list[dict]) -> list[dict]:
    overrides = _load_overrides()
    groups: dict[str, list[dict]] = {}
    for rec in records:
        name = (rec.get("organizer") or "").strip()
        if not name:
            continue
        groups.setdefault(name, []).append(rec)

    used = set()
    orgs = []
    for name, items in groups.items():
        meta = overrides.get(name, {})
        base = str(meta.get("slug") or _slug_base(name)).strip("-") or _slug_base(name)
        slug = base
        n = 2
        while slug in used:
            slug = f"{base}-{n}"
            n += 1
        used.add(slug)

        current = [r for r in items if _current(r)]
        past = [r for r in items if not _current(r)]
        current.sort(key=lambda r: (r.get("deadline") or "9999-12-31", r.get("title") or ""))
        past.sort(key=lambda r: (r.get("deadline") or r.get("end_date") or "0000-00-00"), reverse=True)
        modes = []
        for r in items:
            m = r.get("mode")
            if m and m not in modes:
                modes.append(m)
        cities = []
        for r in items:
            c = (r.get("city") or "").strip()
            if c and c not in cities:
                cities.append(c)
        levels = []
        for r in items:
            lv = common.ai_level(r)
            if lv and lv not in levels:
                levels.append(lv)
        latest = current[0] if current else (past[0] if past else items[0])
        auto = (
            f"已收录 {len(items)} 场 AI 赛事"
            f"（在架 {len(current)} / 往届 {len(past)}），"
            f"形式：{'、'.join(common.MODE_LABEL.get(m, m) for m in modes) or '待确认'}；"
            f"最近一场：{latest.get('title') or '—'}"
            + (f"，报名截止 {latest.get('deadline')}" if latest.get("deadline") else "")
            + "。"
        )
        orgs.append({
            "name": name,
            "slug": slug,
            "letter": _letter(name),
            "website": str(meta.get("website") or "").strip(),
            "intro": str(meta.get("intro") or "").strip() or auto,
            "auto_intro": auto,
            "records": items,
            "current": current,
            "past": past,
            "modes": modes,
            "cities": cities,
            "levels": levels,
            "latest": latest,
        })

    orgs.sort(key=lambda o: (-len(o["current"]), -len(o["records"]), o["name"]))
    return orgs
