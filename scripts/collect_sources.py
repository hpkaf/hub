#!/usr/bin/env python3
"""扩展信源采集（B 层：官方/半官方赛事列表）。

目前接入：
- modelscope  魔搭「竞赛/活动」页（服务端渲染 HTML，含报名截止、类型、奖励）
- heywhale    和鲸社区赛事列表（JSON API /v2/api/competitionsCommunity）
- biendata    biendata 数据竞赛 Ongoing/Coming 两个 tab（服务端渲染 HTML）

每个适配器输出统一字段（见 scripts/common.py），写入 data/candidates_extra.json，
由 common.load_candidates() 与 seeds / 平台候选一起参与去重与核验。
"""
import json
import re
import html
import sys
import datetime
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

OUT_PATH = pathlib.Path(common.DATA_DIR) / "candidates_extra.json"
TODAY = datetime.date.today()


def _rec(**kw):
    rec = {
        "title": None, "organizer": None, "mode": None, "city": None,
        "start_date": None, "end_date": None, "deadline": None, "prize": None,
        "tracks": [], "url": None, "source": None, "source_url": None, "notes": None,
    }
    rec.update({k: v for k, v in kw.items() if v is not None})
    rec["tracks"] = [t for t in (rec.get("tracks") or []) if t]
    return rec


def collect_modelscope():
    """魔搭活动页是 SSR，卡片结构：acss-bdgobe，含标题/状态/类型/奖励/报名截止链接。"""
    code, final, text = common.http_get("https://modelscope.cn/events", timeout=25)
    if code != 200:
        print(f"[modelscope] HTTP {code}, skip")
        return []
    out = []
    for card in re.split(r'<div class="acss-bdgobe">', text)[1:]:
        def g(pat):
            m = re.search(pat, card, re.S)
            return html.unescape(m.group(1)).strip() if m else None

        title = g(r'class="acss-1tdct60 acss-dwyc50 acss-utx8dr">(.*?)</div>')
        if not title:
            continue
        href = g(r'href="(/events/\d+/[^"]+)"')
        flat = re.sub(r"<[^>]+>", "|", card)
        flat = re.sub(r"\|+", "|", flat)
        typ = re.search(r"\|([^|]{1,10})\|类型\|", flat)
        award = re.search(r"\|([^|]{0,50})\|奖励\|", flat)
        dl = re.search(r"\|(\d{4}-\d{2}-\d{2})[ T]\d{2}:\d{2}\|报名截止\|", flat)
        status = re.search(r">\s*(进行中|已结束|未开始)\s*<", card)
        summary = g(r'class="acss-1tdct60 acss-1iac2ic acss-6bgbrs">(.*?)</div>')
        typ_text = typ.group(1).strip() if typ else ""
        # 只收赛事类；开发者沙龙/大会/训练营等不收
        if not re.search(r"黑客松|大赛|挑战赛|比赛|竞赛|开发赛|算法赛", typ_text):
            continue
        url = ("https://modelscope.cn" + href) if href else "https://modelscope.cn/events"
        out.append(_rec(
            title=title,
            mode=None,
            deadline=dl.group(1) if dl else None,
            prize=award.group(1).strip() if award else None,
            tracks=[typ.group(1).strip()] if typ else [],
            url=url,
            source="modelscope",
            source_url="https://modelscope.cn/events",
            notes=(f"魔搭活动页（{status.group(1)}）" if status else "魔搭活动页")
                  + (f"：{summary}" if summary else ""),
        ))
    print(f"[modelscope] {len(out)} 条")
    return out


def collect_heywhale():
    """和鲸社区赛事：/v2/api/competitionsCommunity，返回 totalNum/page/perPage/data。"""
    out = []
    for page in (1, 2, 3):
        url = ("https://www.heywhale.com/v2/api/competitionsCommunity"
               f"?perPage=50&page={page}&CompetitionEventType=1")
        code, final, text = common.http_get(url, timeout=25)
        if code != 200:
            print(f"[heywhale] HTTP {code} page={page}, stop")
            break
        try:
            data = json.loads(text)
        except Exception:
            print(f"[heywhale] JSON 解析失败 page={page}, stop")
            break
        items = data.get("data") or []
        if not items:
            break
        for it in items:
            end = (it.get("EndDate") or "")[:10]
            if end and end < TODAY.isoformat():
                continue  # 已结束，进站没有意义
            start = (it.get("StartDate") or "")[:10] or None
            if start and start < "2025-01-01":
                continue  # 平台上有大量往届赛事被填了远期占位结束时间
            landing = it.get("LandingUrl") or ""
            cid = it.get("_id") or ""
            url = landing if landing.startswith("http") else (
                f"https://www.heywhale.com/mw/competition/{cid}" if cid else "")
            if not url:
                continue
            tracks = [t for t in (it.get("Tags") or []) + (it.get("Fields") or []) if isinstance(t, str)]
            prize = (it.get("Award") or "").strip() or (it.get("DisplayLabel") or "").strip() or None
            out.append(_rec(
                title=(it.get("Name") or "").strip(),
                start_date=start, end_date=end or None,
                prize=prize,
                tracks=tracks,
                url=url,
                source="heywhale",
                source_url="https://www.heywhale.com/home/competition",
                notes=(it.get("ShortDescription") or "")[:300] or None,
            ))
        total = data.get("totalNum") or 0
        if page * 50 >= total:
            break
    print(f"[heywhale] {len(out)} 条（未结束）")
    return out


def collect_biendata():
    """biendata 竞赛页：Ongoing 在 id=home，Coming 在 id=home2。"""
    code, final, text = common.http_get("https://www.biendata.xyz/competition/", timeout=25)
    if code != 200:
        print(f"[biendata] HTTP {code}, skip")
        return []
    out = []
    for panel, label in (("home", "进行中"), ("home2", "即将开始")):
        start = text.find(f'id="{panel}"')
        if start < 0:
            continue
        nxt = [text.find(f'id="{p}"', start + 1) for p in ("home", "home2", "home3")]
        nxt = [n for n in nxt if n > start]
        seg = text[start: min(nxt) if nxt else len(text)]
        for li in re.findall(r'<li class="[^"]*">(.*?)</li>', seg, re.S):
            tm = re.search(r'class="des_text p0" title="([^"]+)"', li)
            if not tm:
                continue
            title = html.unescape(tm.group(1)).strip()
            href = re.search(r'href="(/competition/[^/"]+/)"', li)
            sponsor = re.search(r"Sponsor:\s*(.*?)</span>", li, re.S)
            timeline = re.search(r"Timeline:\s*([0-9-]{8,10})\s*~\s*([0-9-]{8,10})", li)
            out.append(_rec(
                title=title,
                organizer=html.unescape(sponsor.group(1)).strip() if sponsor else None,
                mode="online",
                start_date=timeline.group(1) if timeline else None,
                end_date=timeline.group(2) if timeline else None,
                url=("https://www.biendata.xyz" + href.group(1)) if href else "https://www.biendata.xyz/competition/",
                source="biendata",
                source_url="https://www.biendata.xyz/competition/",
                notes=f"biendata 竞赛（{label}）",
            ))
    print(f"[biendata] {len(out)} 条")
    return out


def main():
    common.ensure_dirs()
    records = []
    ok_sources = set()
    collectors = (
        ("modelscope", collect_modelscope),
        ("heywhale", collect_heywhale),
        ("biendata", collect_biendata),
    )
    for source, fn in collectors:
        try:
            got = fn()
            records.extend(got)
            ok_sources.add(source)
        except Exception as exc:  # 单个源失败不影响其他源
            print(f"[warn] {fn.__name__} 失败：{type(exc).__name__}: {exc}")
    # 去掉标题/URL 为空、标题明显不是赛事的记录；详情字段统一交给 verify 阶段
    cleaned = []
    for rec in records:
        if not rec.get("title") or not rec.get("url"):
            continue
        if common.EXCLUDE_TITLE.search(rec["title"]):
            continue
        cleaned.append(common.normalize_record(rec))
    cleaned = [r for r in cleaned if r]

    # 某个源本轮失败时，保留它上一轮的候选，避免一次网络抖动把该源的记录全部清掉
    old = common.load_json(str(OUT_PATH), []) or []
    kept = [r for r in old if isinstance(r, dict) and r.get("source") not in ok_sources]
    merged, seen = [], set()
    for rec in kept + cleaned:
        key = rec.get("url") or rec.get("title")
        if key in seen:
            continue
        seen.add(key)
        merged.append(rec)
    common.save_json(merged, str(OUT_PATH))
    from collections import Counter
    print(f"[ok] 扩展信源候选 {len(merged)} 条 → {OUT_PATH}"
          f"（本轮成功源 {len(ok_sources)}/{len(collectors)}，保留旧源 {len(kept)} 条）")
    print("     ", dict(Counter(r.get("source") for r in merged)))


if __name__ == "__main__":
    main()
