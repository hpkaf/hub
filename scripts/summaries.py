# -*- coding: utf-8 -*-
"""读取 data/summaries.json，并过滤掉平台通用 meta 描述。

很多平台详情页的 meta description 是站点介绍（讯飞/天池/DataFountain/和鲸/活动行），
不是赛事介绍。宁可不显示，也不把平台广告当赛事简介。
"""
from __future__ import annotations

import json
import os
import re

import common

PATH = os.path.join(common.DATA_DIR, "summaries.json")

GENERIC_PATTERNS = [
    "讯飞开放平台",
    "天池大数据竞赛",
    "DataFountain（简称DF平台）",
    "和鲸社区是数据科学开源社区",
    "活动时间,预约报名",
    "活动嘉宾,主办方等",
    "华为云大赛平台",
    "知乎，中文互联网高质量的问答社区",
    "The best online hackathon infrastructure",
    "NO LONGER ACTIVE",
    "竞赛平台",
]


def _norm(text: str) -> str:
    s = re.sub(r"\s+", "", str(text or "")).lower()
    s = re.sub(r"[|｜·:：,，。.!！?？\-—_/]+", "", s)
    return s


def is_usable(title: str, summary: str) -> bool:
    s = re.sub(r"\s+", " ", str(summary or "")).strip()
    t = str(title or "").strip()
    if len(s) < 35:
        return False
    ns, nt = _norm(s), _norm(t)
    if not ns or not nt:
        return False
    if ns == nt:
        return False
    if ns.startswith(nt) and len(ns) <= len(nt) + 8:
        return False
    for pat in GENERIC_PATTERNS:
        if _norm(pat) in ns:
            return False
    return True


def _clean(text: str) -> str:
    s = re.sub(r"^\s*#+\s*", "", str(text or ""))
    s = re.sub(r"[#*`>]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load(records: list[dict]) -> dict[str, str]:
    try:
        with open(PATH, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    out = {}
    for rec in records:
        item = data.get(rec.get("id")) or {}
        summary = _clean(item.get("summary") if isinstance(item, dict) else "")
        if summary and is_usable(rec.get("title") or "", summary):
            out[rec["id"]] = summary
    return out
