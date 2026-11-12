#!/usr/bin/env python3
"""公众号线索补全：标题 → 搜狗网页 → 带签名文章 → 正文 + 官方链接。

搜狗微信搜索只能给标题/摘要（/link 反爬），但搜狗**网页搜索**会给出带签名的
mp.weixin.qq.com 文章链接（src=11&timestamp=...&signature=...），该链接可读全文。
本脚本对 leads_wechat.json 里待处理的线索执行：
  1) 用标题搜搜狗网页，取第一条带签名的公众号文章；
  2) 抓正文，抽取正文里的外部链接（官方报名页/活动页）；
  3) 回写 leads：wechat_url / body_len / official_urls / status。
限流：搜狗网页连续查 3 次左右会 302/空壳，所以默认每轮只补 6 条，间隔 12s。

用法：
  python3 scripts/enrich_wechat_leads.py            # 补 6 条
  python3 scripts/enrich_wechat_leads.py --limit 3  # 补 3 条
  python3 scripts/enrich_wechat_leads.py --dry-run
"""
from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import common

LEADS = Path(common.DATA_DIR) / "leads_wechat.json"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
SOGOU_WEB = "https://www.sogou.com/web?query={q}"
SLEEP = 12.0

# 白名单从 data/wechat_whitelist.yaml 读，改配置不用改代码
_WH = common.load_yaml(str(Path(common.DATA_DIR) / "wechat_whitelist.yaml")) or {}
WHITELIST = set(_WH.get("accounts") or [])
STATE = Path(common.DATA_DIR) / "leads_wechat_state.json"

# 正文里算「官方入口」的域名
OFFICIAL_DOMAINS = (
    "lu.ma", "luma.com", "huodongxing.com", "modelscope.cn", "tianchi.aliyun.com",
    "challenge.xfyun.cn", "datafountain.cn", "aistudio.baidu.com", "dorahacks.io",
    "heywhale.com", "biendata.xyz", "event.zhihu.com", "zhihu.com/hackathon",
    "bagevent.com", "wjx.cn", "jsj.top", "openatom.tech", "competition.",
    "github.com", "gitee.com", "spatialjoy.rokid.com", "waytoagi.com",
    "events.waytoagi.com", "resonance.waytoagi.com", "adventure-x.cn",
)
MP = re.compile(r"https?://mp\.weixin\.qq\.com/s\?[^\"'<>\\s]+")
HREF = re.compile(r'href="([^"]+)"')


def get(url: str, referer: str = "https://www.sogou.com/") -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer,
                                               "Accept-Language": "zh-CN,zh;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode("utf-8", "ignore")
    except Exception as e:  # noqa: BLE001
        return 0, str(e)


def strip_tags(s: str) -> str:
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def rate_limited() -> bool:
    st = common.load_json(str(STATE), {}) or {}
    return (st.get("retry_after") or "") > common.now_iso()


def set_cooldown(minutes: int = 45) -> None:
    import datetime as dt
    until = (dt.datetime.now() + dt.timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S")
    common.save_json({"retry_after": until, "reason": "sogou antispider"}, STATE)


def find_sogou_mp_link(title: str) -> str | None:
    q = urllib.parse.quote(title[:60])
    code, page = get(SOGOU_WEB.format(q=q))
    if code != 200:
        set_cooldown()
        return None
    if "antispider" in page:
        set_cooldown()
        return None
    if "没有找到" in page and "相关结果" not in page:
        return None
    # 搜狗结果里的公众号链接是 http://mp.weixin.qq.com/s?src=11&timestamp=..&signature=..
    for m in re.finditer(r'https?://mp\.weixin\.qq\.com/s\?src=[^"\'<>\\s]+', page):
        return html.unescape(m.group(0))
    return None


def parse_article(article_url: str) -> tuple[str | None, str]:
    """返回 (标题, 正文纯文本)。"""
    code, page = get(article_url, referer="https://www.sogou.com/")
    if code != 200:
        return None, ""
    t = re.search(r'<h1[^>]*class="rich_media_title"[^>]*>(.*?)</h1>', page, re.S)
    if not t:
        t = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]+)"', page)
    title = strip_tags(t.group(1)) if t else None
    # js_content 里可能有嵌套 div，直接截到下一个 <script
    pos = page.find('id="js_content"')
    text = ""
    if pos > 0:
        seg = page[pos: pos + 600000]
        end = seg.find("<script")
        if end > 0:
            seg = seg[:end]
        text = strip_tags(seg)
    return title, text


def extract_official(text_html: str) -> list[str]:
    urls = []
    for m in HREF.finditer(text_html):
        u = html.unescape(m.group(1))
        if not u.startswith("http"):
            continue
        if any(d in u for d in OFFICIAL_DOMAINS) and "mp.weixin.qq.com" not in u:
            if u not in urls:
                urls.append(u)
    return urls[:6]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = common.load_json(str(LEADS), {}) or {}
    leads = data.get("leads") or []
    if rate_limited():
        print("[wechat-enrich] 搜狗网页处于冷却期，跳过本轮")
        return 0

    # 待补全的线索：优先白名单公众号、再按发布时间新→旧
    todo = [x for x in leads if x.get("status") in ("pending", "no_search_hit")]
    todo.sort(key=lambda x: (x.get("account") in WHITELIST, x.get("publish_date") or ""),
              reverse=True)
    todo = todo[: args.limit]
    if not todo:
        print("[wechat-enrich] 没有待补全的线索")
        return 0

    for lead in todo:
        title = lead.get("title") or ""
        print(f"[wechat-enrich] {lead.get('account')} | {title[:40]} ...")
        link = find_sogou_mp_link(title)
        if not link:
            lead["status"] = "no_search_hit"
            lead["enriched_at"] = common.now_iso()
            print("  [miss] 搜狗网页无带签名链接（限流已记录冷却）")
            break
        art_title, body = parse_article(link)
        if len(body) < 80:
            lead["status"] = "body_blocked"
            lead["wechat_url"] = link
            lead["enriched_at"] = common.now_iso()
            print(f"  [blocked] 正文过短（{len(body)} 字）")
            time.sleep(SLEEP)
            continue
        official = extract_official(body)
        lead["status"] = "has_official_link" if official else "body_only"
        lead["wechat_url"] = link
        lead["body_len"] = len(body)
        lead["body_excerpt"] = body[:600]
        lead["official_urls"] = official
        lead["enriched_at"] = common.now_iso()
        print(f"  [ok] 正文 {len(body)} 字；官方链接 {len(official)} 个")
        for u in official:
            print(f"        {u[:90]}")
        time.sleep(SLEEP)

    data["leads"] = leads
    data["updated_at"] = common.now_iso()
    if not args.dry_run:
        common.save_json(data, LEADS)
    print(f"[wechat-enrich] 完成 {len(todo)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
