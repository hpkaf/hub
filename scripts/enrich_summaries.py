#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从官方页抓一段可溯源的赛事简介，写入 data/summaries.json。

只取官方页的 meta description / og:description，不做摘要生成、不编内容。
由 build_site.py 合并进详情页 / API / RSS；不在每日流水线里跑（按需手动刷新即可）。

用法：
  python scripts/enrich_summaries.py              # 只补缺失
  python scripts/enrich_summaries.py --force      # 全量重抓
  python scripts/enrich_summaries.py --limit 10   # 调试
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import summaries  # noqa: E402

OUT = os.path.join(common.DATA_DIR, "summaries.json")
META_PATTERNS = [
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
    r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:description["\']',
    r'<meta[^>]+name=["\']twitter:description["\'][^>]+content=["\']([^"\']+)["\']',
]
TAG = re.compile(r"<[^>]+>")


def extract(text: str) -> str:
    for pat in META_PATTERNS:
        m = re.search(pat, text, re.I | re.S)
        if not m:
            continue
        value = html.unescape(m.group(1))
        value = TAG.sub(" ", value)
        value = re.sub(r"\s+", " ", value).strip(" -|·:：")
        if len(value) >= 20:
            return value[:320]
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    races = common.load_json(os.path.join(common.DATA_DIR, "races.json"), []) or []
    old = common.load_json(OUT, {}) or {}
    out = dict(old) if isinstance(old, dict) else {}
    targets = []
    for rec in races:
        rid = rec.get("id")
        if not rid or not rec.get("url"):
            continue
        if not args.force and (out.get(rid) or {}).get("summary"):
            continue
        targets.append(rec)
    if args.limit:
        targets = targets[: args.limit]

    print(f"[summaries] 目标 {len(targets)} 条（已有 {len(out)} 条）")
    ok = 0
    for i, rec in enumerate(targets, 1):
        code, final_url, text = common.http_get(rec["url"], timeout=15)
        summary = extract(text) if code == 200 and text else ""
        if summary and summaries.is_usable(rec.get("title") or "", summary):
            out[rec["id"]] = {
                "summary": summary,
                "source": rec["url"],
                "fetched_at": common.now_iso(),
            }
            ok += 1
        else:
            summary = ""
        flag = "OK " if summary else "---"
        print(f"  {flag} {i:>2}/{len(targets)} {rec['title'][:34]:<36} {rec['url'][:60]}")
        time.sleep(0.25)

    common.save_json(out, OUT)
    print(f"[summaries] 写入 {OUT}：{len(out)} 条（本轮新增/更新 {ok} 条）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
