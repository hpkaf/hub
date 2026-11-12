#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核验 + 去重 + 入库。

流程：
  1. 读 seeds.yaml + candidates_*.json
  2. 统一结构、过滤非 AI、两级去重
  3. 逐条核验链接（200/301 才算活链；403/405/429 标 unknown）
  4. 写入 SQLite（保留 first_seen），导出 data/races.json 给站点用

用法：
  python3 scripts/verify.py              # 全量核验
  python3 scripts/verify.py --no-verify  # 跳过网络核验（调试用）
  python3 scripts/verify.py --limit 10   # 只核验前 10 条（调试用）
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common  # noqa: E402

DB_PATH = os.path.join(common.DATA_DIR, "races.db")
EXPORT_PATH = os.path.join(common.DATA_DIR, "races.json")

SCHEMA = """
CREATE TABLE IF NOT EXISTS races (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    organizer   TEXT,
    mode        TEXT,
    city        TEXT,
    start_date  TEXT,
    end_date    TEXT,
    deadline    TEXT,
    prize       TEXT,
    tracks      TEXT,
    url         TEXT NOT NULL,
    source      TEXT,
    sources     TEXT,
    source_url  TEXT,
    evidence    TEXT,
    notes       TEXT,
    status      TEXT,
    registration_closed INTEGER DEFAULT 0,
    verify_state    TEXT,
    verify_code     INTEGER,
    verify_final_url TEXT,
    verified_at TEXT,
    first_seen  TEXT,
    last_seen   TEXT
);
CREATE INDEX IF NOT EXISTS idx_races_status ON races(status);
CREATE INDEX IF NOT EXISTS idx_races_deadline ON races(deadline);
"""


def upsert(conn: sqlite3.Connection, rec: dict, verify: dict | None) -> str:
    """写入/更新一条记录，返回 new / updated / skipped。"""
    row = conn.execute("SELECT id, first_seen FROM races WHERE id = ?", (rec["id"],)).fetchone()
    now = common.now_iso()
    if row is None:
        conn.execute(
            """INSERT INTO races (id, title, organizer, mode, city, start_date, end_date, deadline,
               prize, tracks, url, source, sources, source_url, evidence, notes, status,
               registration_closed, verify_state, verify_code, verify_final_url, verified_at,
               first_seen, last_seen)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rec["id"], rec["title"], rec["organizer"], rec["mode"], rec["city"],
             rec["start_date"], rec["end_date"], rec["deadline"], rec["prize"],
             "|".join(rec.get("tracks") or []), rec["url"], rec["source"],
             "|".join(rec.get("sources") or [rec["source"]]), rec["source_url"],
             rec.get("evidence"), rec.get("notes"), rec["status"],
             1 if rec.get("registration_closed") else 0,
             (verify or {}).get("state"), (verify or {}).get("code"),
             (verify or {}).get("final_url"), now, now, now),
        )
        return "new"

    conn.execute(
        """UPDATE races SET title=?, organizer=?, mode=?, city=?, start_date=?, end_date=?,
           deadline=?, prize=?, tracks=?, url=?, source=?, sources=?, source_url=?, evidence=?,
           notes=?, status=?, registration_closed=?, verify_state=COALESCE(?, verify_state),
           verify_code=COALESCE(?, verify_code),
           verify_final_url=COALESCE(?, verify_final_url),
           verified_at=CASE WHEN ? IS NOT NULL THEN ? ELSE verified_at END,
           last_seen=?
           WHERE id=?""",
        (rec["title"], rec["organizer"], rec["mode"], rec["city"], rec["start_date"],
         rec["end_date"], rec["deadline"], rec["prize"], "|".join(rec.get("tracks") or []),
         rec["url"], rec["source"], "|".join(rec.get("sources") or [rec["source"]]),
         rec["source_url"], rec.get("evidence"), rec.get("notes"), rec["status"],
         1 if rec.get("registration_closed") else 0,
         (verify or {}).get("state"), (verify or {}).get("code"),
         (verify or {}).get("final_url"), now, now, now, rec["id"]),
    )
    return "updated"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-verify", action="store_true", help="跳过链接核验")
    parser.add_argument("--limit", type=int, default=0, help="只核验前 N 条（调试）")
    parser.add_argument("--no-prune", action="store_true", help="不清理已从候选源消失的旧记录")
    args = parser.parse_args()

    common.ensure_dirs()
    run_start = common.now_iso()
    raw_records = common.load_candidates()
    print(f"[1/5] 载入候选 {len(raw_records)} 条")

    # 搜狗只做「线索」：链接是搜索页而非官方页，不进核验清单，留在 data/raw/hack/ 备查
    ai_records = [r for r in raw_records
                  if common.is_ai(r) and common.is_relevant(r) and r.get("source") != "sogou"]
    print(f"[2/5] AI 相关 {len(ai_records)} 条（过滤掉 {len(raw_records) - len(ai_records)} 条非 AI/非赛事）")

    records = common.dedupe(ai_records)
    print(f"[3/5] 去重后 {len(records)} 条")

    verify_map: dict[str, dict] = {}
    if not args.no_verify:
        targets = records[: args.limit] if args.limit else records
        print(f"[4/5] 核验链接 {len(targets)} 条 ...")
        for i, rec in enumerate(targets, 1):
            v = common.check_url(rec["url"])
            verify_map[rec["url"]] = v
            flag = {"ok": "OK ", "unknown": "??? ", "dead": "DEAD"}[v["state"]]
            print(f"  {flag} {v['code'] or '-':>4} {rec['title'][:38]:<40} {rec['url'][:70]}")
            time.sleep(0.25)
    else:
        print("[4/5] 跳过链接核验")

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    # 轻量迁移：老库没有 registration_closed 列时补上
    cols = [r[1] for r in conn.execute("PRAGMA table_info(races)")]
    if "registration_closed" not in cols:
        conn.execute("ALTER TABLE races ADD COLUMN registration_closed INTEGER DEFAULT 0")
        conn.commit()
    stats = {"new": 0, "updated": 0}
    for rec in records:
        stats[upsert(conn, rec, verify_map.get(rec["url"]))] += 1
    conn.commit()

    # 清理：候选源里已经不存在的记录（标题被过滤、链接失效下线等）
    # 防误删：如果本轮候选数远低于库内记录数（典型原因是某个抓取源临时失败、
    # 候选文件被写成空数组），宁可保留旧记录也不清理，避免一次网络抖动清空账本。
    pruned = 0
    if not args.no_prune:
        existing = conn.execute("SELECT COUNT(*) FROM races").fetchone()[0]
        floor = max(10, int(existing * 0.6))
        if len(records) >= floor:
            cur = conn.execute("DELETE FROM races WHERE last_seen < ?", (run_start,))
            pruned = cur.rowcount
            conn.commit()
        else:
            print(f"[warn] 本轮候选仅 {len(records)} 条（库内 {existing} 条，阈值 {floor}），"
                  f"跳过清理，保留旧记录")

    # 导出：只导出活链和 curated 记录，避免把死链带给前端
    rows = conn.execute("SELECT * FROM races ORDER BY deadline IS NULL, deadline, title").fetchall()
    cols = [c[0] for c in conn.execute("SELECT * FROM races LIMIT 1").description]
    export = []
    for row in rows:
        item = dict(zip(cols, row))
        item["tracks"] = [t for t in (item.get("tracks") or "").split("|") if t]
        item["sources"] = [s for s in (item.get("sources") or "").split("|") if s]
        item["registration_closed"] = bool(item.get("registration_closed"))
        item["status"] = common.compute_status(item)
        item["ai_level"] = common.ai_level(item)
        if item["verify_state"] == "dead":
            continue
        export.append(item)
    common.save_json(export, EXPORT_PATH)

    total = len(export)
    ok = sum(1 for r in export if r["verify_state"] == "ok")
    unknown = sum(1 for r in export if r["verify_state"] == "unknown")
    print(f"[5/5] 写入 {DB_PATH}")
    print(f"      新增 {stats['new']} / 更新 {stats['updated']} / 清理 {pruned}；导出 {total} 条"
          f"（活链 {ok}，待确认 {unknown}）")
    print(f"      导出文件：{EXPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
