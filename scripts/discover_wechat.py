#!/usr/bin/env python3
"""公众号线索发现（D 层，只进 leads，不进公开站点）。

为什么只发现不采集：
- 搜狗微信搜索能稳定列出文章的标题/公众号/发布时间/摘要，但结果链接
  /link?url=... 一律 302 到 /antispider/ 验证页，拿不到 mp.weixin 正文 URL；
- 直接打开 mp.weixin.qq.com 文章链接（无签名）只返回 17KB 的 JS 空壳，
  headless Chrome 渲染得到「环境异常，去验证」；
- 搜狗网页搜索偶尔会给出带签名的文章链接（src=11&timestamp=...&signature=...），
  这种链接可以读到正文，但搜狗网页搜索很快限流（连续查询直接 302/空壳），
  因此不能作为每日稳定的数据源。

结论：公众号只当线索源。这里把搜到的文章记入 data/leads_wechat.json（pending），
由人工确认官方报名页后，再按 leads.yaml / seeds.yaml 的契约进公开数据。

用法：
  python3 scripts/discover_wechat.py                 # 默认 4 个查询，每个 20 条
  python3 scripts/discover_wechat.py --queries "AI黑客松" "具身智能 大赛"
  python3 scripts/discover_wechat.py --dry-run       # 只打印，不写文件
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

LEADS_PATH = Path(common.DATA_DIR) / "leads_wechat.json"
SOGOU = "https://weixin.sogou.com/weixin?type=2&query={q}"  # 注意：加 tsn= 会 302 到反爬页
# 微信侧更认移动端 UA；桌面 UA 也能搜，但频控不同。
IPHONE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
DEFAULT_QUERIES = ["AI 黑客松", "AI 大赛 报名", "大模型 黑客松", "智能体 大赛"]

# 明显是赛后报道/复盘/获奖公示的文章，不是可报名赛事，进线索队列也没用。
EXCLUDE_LEAD_TITLE = re.compile(r"名单揭晓|获奖名单|复盘|总结|回顾|报道|赛后|闭幕|落幕|分析|盘点")

MAX_PER_RUN = 80
SLEEP_BETWEEN_QUERIES = 3.0


def fetch(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": IPHONE_UA,
            "Referer": "https://weixin.sogou.com/",
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    for enc in ("utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "ignore")


def strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s)).replace("\u200b", "").strip()


def parse_results(page: str) -> list[dict]:
    items = re.findall(r'<li id="sogou_vr_11002601_box_\d+".*?</li>', page, re.S)
    out: list[dict] = []
    for item in items:
        m = re.search(r'id="sogou_vr_11002601_title_\d+"[^>]*>(.*?)</a>', item, re.S)
        title = strip_tags(m.group(1)) if m else ""
        link = re.search(r'href="(/link\?url=[^"]+)"', item)
        account = re.search(r'class="all-time-y2">(.*?)<', item, re.S)
        ts = re.search(r"timeConvert\('(\d+)'\)", item)
        summary = re.search(r'class="txt-info"[^>]*>(.*?)</p>', item, re.S)
        if not title or not link:
            continue
        publish = ""
        if ts:
            try:
                publish = datetime.fromtimestamp(int(ts.group(1)), tz=timezone.utc).astimezone().strftime("%Y-%m-%d")
            except (ValueError, OSError):
                publish = ""
        out.append(
            {
                "title": title,
                "account": strip_tags(account.group(1)) if account else "",
                "publish_date": publish,
                "summary": strip_tags(summary.group(1))[:120] if summary else "",
                "sogou_url": "https://weixin.sogou.com" + html.unescape(link.group(1)),
            }
        )
    return out


def relevant(item: dict) -> bool:
    text = f"{item['title']} {item['summary']}"
    if common.EXCLUDE_TITLE.search(text) or EXCLUDE_LEAD_TITLE.search(item["title"]):
        return False
    # 太旧的（超过 120 天）大概率已经结束，不进当轮线索
    if item.get("publish_date"):
        try:
            age = (datetime.now() - datetime.strptime(item["publish_date"], "%Y-%m-%d")).days
            if age > 120:
                return False
        except ValueError:
            pass
    return any(k.lower() in text.lower() for k in common.STRONG_AI_KEYWORDS) or any(
        k in text for k in ("黑客松", "hackathon", "挑战赛", "创新赛")
    )


def load_leads() -> dict:
    if LEADS_PATH.exists():
        return json.loads(LEADS_PATH.read_text(encoding="utf-8"))
    return {"updated_at": None, "note": "公众号线索（未核验，不进公开站点）", "leads": []}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", nargs="*", default=DEFAULT_QUERIES)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    common.ensure_dirs()
    state = load_leads()
    known = {common.norm_title(x["title"]) for x in state["leads"]}
    added: list[dict] = []
    failed: list[str] = []

    for i, q in enumerate(args.queries):
        if i:
            time.sleep(SLEEP_BETWEEN_QUERIES)
        url = SOGOU.format(q=urllib.parse.quote(q))
        try:
            page = fetch(url)
        except Exception as exc:  # noqa: BLE001
            failed.append(f"{q}: {exc}")
            print(f"[fail] {q}: {exc}")
            continue
        if "antispider" in page or "请输入验证码" in page:
            failed.append(f"{q}: 被反爬验证拦截")
            print(f"[blocked] {q} 触发搜狗验证，停止本轮")
            break
        results = parse_results(page)
        print(f"[ok] {q}: {len(results)} 条")
        for r in results:
            if len(added) >= MAX_PER_RUN:
                break
            if not relevant(r):
                continue
            key = common.norm_title(r["title"])
            if key in known:
                continue
            known.add(key)
            added.append(
                {
                    **r,
                    "status": "pending",
                    "status_note": "搜狗微信搜到，正文/报名入口未验证；需人工确认官方报名页",
                    "found_at": common.now_iso()[:10],
                    "found_by": "sogou-weixin search",
                    "query": q,
                }
            )

    if args.dry_run:
        for r in added[:20]:
            print(f"  + {r['publish_date']} [{r['account']}] {r['title']}")
        print(f"[dry-run] 新增 {len(added)} 条，未写文件")
        return 0

    if added:
        state["leads"].extend(added)
        state["leads"] = state["leads"][-400:]
        state["updated_at"] = common.now_iso()
        common.save_json(state, str(LEADS_PATH))
        print(f"[write] {LEADS_PATH}：新增 {len(added)} 条，共 {len(state['leads'])} 条")
        for r in added[:10]:
            print(f"  + {r['publish_date']} [{r['account']}] {r['title']}")
        if len(added) > 10:
            print(f"  …… 以及另外 {len(added) - 10} 条")
    else:
        print("[skip] 没有新线索")
    if failed:
        print(f"[warn] {len(failed)} 个查询失败/被拦")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
