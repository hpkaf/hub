#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 赛事雷达 - 公共工具。

设计原则：
- 只用标准库（YAML 通过项目内 .pylibs/pyyaml 加载），方便在 GitHub Actions 里直接跑；
- 所有抓取脚本各自独立，本模块只放"数据清洗 / 核验 / 去重 / 状态计算"这类共用逻辑；
- 任何赛事记录必须带真实 url，宁缺毋滥。
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# 部分国内网络到境外站点会拿到 IPv6 地址但没有 IPv6 出口，urllib 会先在 IPv6 上
# 等到超时（luma.com 实测卡 8 分钟以上）。这里只调整解析结果的**顺序**：优先 IPv4，
# 没有 IPv4 时仍回退 IPv6，不改变任何请求语义。
_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_first(host, port, family=0, type=0, proto=0, flags=0):
    infos = _orig_getaddrinfo(host, port, family, type, proto, flags)
    infos.sort(key=lambda info: 0 if info[0] == socket.AF_INET else 1)
    return infos


socket.getaddrinfo = _ipv4_first

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
SITE_DIR = os.path.join(ROOT, "site")
RAW_DIR = os.path.join(DATA_DIR, "raw")


def _load_dotenv() -> None:
    """读取项目根目录的 .env（KEY=VALUE），让单独运行某个脚本时也能拿到 SITE_URL 等配置。

    已存在的环境变量优先（不覆盖），与「显式 export 优先」的直觉一致；
    run_daily.sh / run_daily.ps1 会先加载 .env，这里的 setdefault 不会改变结果。
    """
    path = os.path.join(ROOT, ".env")
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8-sig") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip()
                if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                    val = val[1:-1]
                if key:
                    os.environ.setdefault(key, val)
    except OSError:
        pass


_load_dotenv()

# 项目内依赖（pyyaml），CI 里也可以 pip install -r requirements.txt
_LOCAL_LIBS = os.path.join(ROOT, ".pylibs")
if os.path.isdir(_LOCAL_LIBS) and _LOCAL_LIBS not in sys.path:
    sys.path.insert(0, _LOCAL_LIBS)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

TODAY = dt.date.today()

# 判断一条信息是否属于「AI 赛道」。平台源（天池等）本身就是 AI，可不判断。
AI_KEYWORDS = [
    "AI", "人工智能", "大模型", "LLM", "AIGC", "生成式", "智能体", "Agent",
    "机器学习", "深度学习", "算法", "算力", "多模态", "具身", "机器人",
    "模型", "RAG", "NLP", "CV", "语料", "微调", "推理", "智能", "数据竞赛",
    "提示词", "Prompt", "开源模型", "芯片", "自动驾驶", "具身智能", "世界模型",
]

# 平台源默认就是 AI 赛事，不做关键词过滤
AI_PLATFORMS = {"tianchi", "xfyun", "datafountain", "aistudio"}

# 明确不可信的域名/占位符，直接判死
BLOCKED_HOSTS = {
    "example.com", "example.org", "localhost", "127.0.0.1",
}

DEFAULT_UA_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}


# ---------------------------------------------------------------- 网络
def http_get(url: str, timeout: int = 20, retries: int = 2) -> tuple[int, str, str]:
    """返回 (status_code, final_url, text)。失败返回 (0, url, '')。"""
    last = (0, url, "")
    headers = dict(DEFAULT_UA_HEADERS)
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                charset = resp.headers.get_content_charset()
                raw = resp.read()
                if not charset:
                    head = raw[:2048].decode("ascii", "ignore")
                    m = re.search(r'charset=["\']?([\w-]+)', head, re.I)
                    charset = m.group(1) if m else "utf-8"
                try:
                    text = raw.decode(charset, "ignore")
                except LookupError:
                    text = raw.decode("utf-8", "ignore")
                return resp.status, resp.geturl(), text
        except urllib.error.HTTPError as exc:
            # 4xx/5xx 仍然拿到状态码，可能被反爬（403/405）或页面不存在（404）
            return exc.code, url, ""
        except Exception:
            last = (0, url, "")
            if attempt < retries:
                time.sleep(1.0 + attempt)
    return last


def check_url(url: str, timeout: int = 15) -> dict:
    """核验一条赛事链接。ok / unknown / dead 三态。"""
    host = urllib.parse.urlparse(url).netloc.lower()
    if not host:
        return {"state": "dead", "code": 0, "final_url": url, "reason": "bad_url"}
    if host in BLOCKED_HOSTS or host.endswith(".example.com"):
        return {"state": "dead", "code": 0, "final_url": url, "reason": "placeholder"}
    code, final_url, _ = http_get(url, timeout=timeout)
    if 200 <= code < 400:
        state = "ok"
    elif code in (401, 403, 405, 429, 503):
        state = "unknown"  # 反爬/限流，不代表页面不存在
    elif code == 0:
        state = "unknown" if "://" in url else "dead"
    else:
        state = "dead"
    return {"state": state, "code": code, "final_url": final_url, "reason": ""}


# ---------------------------------------------------------------- 文本 / 去重
_PUNCT = re.compile(r"[\s\u3000\-—–_·|/\\:：;；,，.。!！?？'\"“”‘’「」『』()（）\[\]【】<>《》〈〉〔〕#@&+*=~`^%$]+")


_TITLE_PREFIX = re.compile(r"^(全新升级|重磅|官宣|正式推出|正式上线|正式启动)")
_TITLE_SUFFIX = re.compile(
    r"(开启报名|报名开启|报名开始|报名启动|开始报名|现已开启|正式启动|"
    r"火热进行中|火热报名中|报名中|招募开启|启动报名|报名|启动|来袭|来啦|开启)$"
)


def norm_title(title: str) -> str:
    """标题指纹：去年份、去「的」、去标点空白、去常见宣传前后缀、统一小写。"""
    t = (title or "").strip().lower()
    t = re.sub(r"20\d{2}\s*年?\s*度?", "", t)
    t = t.replace("的", "")
    t = _PUNCT.sub("", t)
    t = _TITLE_PREFIX.sub("", t)
    for _ in range(2):
        t = _TITLE_SUFFIX.sub("", t)
    return t


def norm_url(url: str) -> str:
    """URL 归一化：去跟踪参数、去末尾斜杠、统一 scheme/host。"""
    if not url:
        return ""
    try:
        p = urllib.parse.urlsplit(url.strip())
    except ValueError:
        return url
    host = p.netloc.lower().removeprefix("www.")
    path = p.path.rstrip("/") or "/"
    keep = []
    for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=False):
        if k.lower() in {"utm_source", "utm_medium", "utm_campaign", "utm_term",
                         "utm_content", "spm", "from", "share_token", "continueflag"}:
            continue
        keep.append((k, v))
    query = urllib.parse.urlencode(keep)
    return urllib.parse.urlunsplit(("https", host, path, query, ""))


def record_hash(rec: dict) -> str:
    """稳定 ID：优先用官方链接，其次用标题指纹。"""
    base = norm_url(rec.get("url") or "") or norm_title(rec.get("title") or "")
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]


def slugify(title: str, record_id: str) -> str:
    zh = re.sub(r"[^\u4e00-\u9fff a-zA-Z0-9]+", "-", (title or "").strip())
    zh = re.sub(r"\s+", "-", zh).strip("-")[:40].lower()
    return f"{record_id}-{zh}" if zh else record_id


# ---------------------------------------------------------------- 日期 / 状态
DATE_PATTERNS = [
    r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})",
    r"(\d{4})年(\d{1,2})月(\d{1,2})日",
]


def parse_date(value) -> str | None:
    """把各种写法统一成 YYYY-MM-DD；解析不了返回 None。"""
    if not value:
        return None
    if isinstance(value, (dt.date, dt.datetime)):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    for pat in DATE_PATTERNS:
        m = re.search(pat, s)
        if m:
            y, mo, d = (int(x) for x in m.groups())
            try:
                return dt.date(y, mo, d).strftime("%Y-%m-%d")
            except ValueError:
                return None
    return None


def days_until(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        d = dt.date.fromisoformat(date_str)
    except ValueError:
        return None
    return (d - TODAY).days


def compute_status(rec: dict) -> str:
    """报名状态：open / closing（7 天内截止）/ closed / upcoming / unknown。"""
    if rec.get("registration_closed"):
        return "closed"
    deadline = rec.get("deadline")
    d = days_until(deadline)
    if d is not None:
        if d < 0:
            return "closed"
        if d <= 7:
            return "closing"
        return "open"
    # 没有报名截止：比赛都结束了就是 closed，还没开始就是 upcoming
    end = days_until(rec.get("end_date"))
    if end is not None and end < 0:
        return "closed"
    start = days_until(rec.get("start_date"))
    if start is not None:
        return "upcoming" if start > 0 else "open"
    return "unknown"


STATUS_LABEL = {
    "open": "报名中",
    "closing": "即将截止",
    "closed": "已截止",
    "upcoming": "即将开始",
    "unknown": "待确认",
}
MODE_LABEL = {"online": "线上", "offline": "线下", "hybrid": "线上+线下"}


# ---------------------------------------------------------------- 聚合清洗
def clean_text(value, limit: int = 200) -> str | None:
    if value is None:
        return None
    s = re.sub(r"\s+", " ", str(value)).strip()
    return s[:limit] if s else None


def normalize_record(raw: dict) -> dict | None:
    """把各抓取源的原始记录统一成标准结构；不合格返回 None。"""
    title = clean_text(raw.get("title"), 120)
    url = (raw.get("url") or "").strip()
    if not title or len(title) < 4 or not url.startswith("http"):
        return None
    source = clean_text(raw.get("source"), 20) or "unknown"
    mode = raw.get("mode") if raw.get("mode") in ("online", "offline", "hybrid") else None
    if mode is None and source in AI_PLATFORMS:
        mode = "online"  # 算法赛平台默认线上提交
    rec = {
        "title": title,
        "organizer": clean_text(raw.get("organizer"), 80),
        "mode": mode,
        "city": clean_text(raw.get("city"), 30),
        "start_date": parse_date(raw.get("start_date")),
        "end_date": parse_date(raw.get("end_date")),
        "deadline": parse_date(raw.get("deadline")),
        "prize": clean_text(raw.get("prize"), 120),
        "tracks": [clean_text(t, 40) for t in (raw.get("tracks") or []) if clean_text(t, 40)][:8],
        "url": url,
        "source": source,
        "source_url": (raw.get("source_url") or url).strip(),
        "evidence": clean_text(raw.get("evidence"), 300),
        "notes": clean_text(raw.get("notes"), 300),
        # 主办方已明确关闭报名（例如 Luma 显示 Registration Closed），此时不再按截止日推断
        "registration_closed": bool(raw.get("registration_closed")),
    }
    rec["id"] = record_hash(rec)
    rec["status"] = compute_status(rec)
    return rec


EXCLUDE_TITLE = re.compile(r"实战营|训练营|工作坊|沙龙|公开课|直播|练手赛|千言数据集|Q力星期四|打榜赛|Baseline")


def is_relevant(rec: dict) -> bool:
    """排除明显不是"比赛"的活动（训练营、工坊、沙龙等）。"""
    return not EXCLUDE_TITLE.search(rec.get("title") or "")


def is_ai(rec: dict) -> bool:
    if rec.get("source") in AI_PLATFORMS:
        return True
    blob = " ".join(str(rec.get(k) or "") for k in ("title", "organizer", "tracks", "prize"))
    return any(k.lower() in blob.lower() for k in AI_KEYWORDS)


# 判断「是否 AI 赛事」可以宽（AI_KEYWORDS），但对外标注「这是什么 AI 赛事」要严：
# 只认能说明技术方向的强词，避免「智能硬件」「算法赛」这种泛词把非 AI 赛事标成含 AI 赛道。
STRONG_AI_KEYWORDS = [
    "AI", "人工智能", "大模型", "LLM", "AIGC", "生成式", "智能体", "Agent",
    "机器学习", "深度学习", "计算机视觉", "多模态", "具身", "机器人", "RAG",
    "NLP", "语料", "提示词", "Prompt", "自动驾驶", "世界模型", "语音识别",
]


def ai_level(rec: dict) -> str:
    """AI 相关度分层（对外展示/feed 字段），永远返回一个值。

    - core：标题本身就是 AI 赛事 —— 整场按 AI 收录；
    - track：标题是泛主题，但赛道/题目/奖金字段里有明确的 AI 方向 —— 标注「含 AI 赛道」；
    - platform：天池/讯飞/DataFountain/AI Studio 等 AI 平台上的比赛；
    - other：只在信源/简介里带 AI 线索，无法归入以上（仍收录，但不算核心）。
    """
    def has_strong(text: str) -> bool:
        low = (text or "").lower()
        return any(k.lower() in low for k in STRONG_AI_KEYWORDS)

    if has_strong(str(rec.get("title") or "")):
        return "core"
    if rec.get("source") in AI_PLATFORMS:
        # 平台上的算法赛整场都是 AI，不因为标题没写"AI"就降级成"含 AI 赛道"
        return "platform"
    tracks = " ".join(str(t) for t in (rec.get("tracks") or []))
    if has_strong(tracks):
        return "track"
    if has_strong(str(rec.get("prize") or "")) or has_strong(str(rec.get("notes") or "")):
        return "other"
    return "other"


def load_yaml(path: str):
    import yaml  # 延迟导入，避免没装 pyyaml 时所有脚本都挂

    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_json(path: str, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(obj, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def load_candidates() -> list[dict]:
    """合并所有抓取源产出 + 人工核验种子。"""
    records: list[dict] = []

    seeds_path = os.path.join(DATA_DIR, "seeds.yaml")
    if os.path.exists(seeds_path):
        try:
            seeds = load_yaml(seeds_path) or []
            if isinstance(seeds, dict):
                seeds = seeds.get("races") or seeds.get("events") or []
            for item in seeds:
                if isinstance(item, dict):
                    records.append(normalize_record({**item, "source": "curated"}))
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] seeds.yaml 解析失败: {exc}")

    for name in ("candidates_comp.json", "candidates_hack.json", "candidates_events.json",
                 "candidates_extra.json", "candidates_luma.json"):
        path = os.path.join(DATA_DIR, name)
        for item in load_json(path, []) or []:
            if isinstance(item, dict):
                records.append(normalize_record(item))

    return [r for r in records if r]


def dedupe(records: list[dict]) -> list[dict]:
    """两级去重：先按归一化 URL，再按标题指纹；合并时保留信息更全的字段。"""
    source_rank = {"curated": 5, "zhihu": 5, "tianchi": 4, "xfyun": 4, "datafountain": 4,
                   "aistudio": 4, "modelscope": 4, "heywhale": 4, "luma": 4, "biendata": 3,
                   "dorahacks": 3, "huodongxing": 3, "sogou": 1}
    groups: dict[str, list[dict]] = {}
    for rec in records:
        key = norm_url(rec["url"]) or norm_title(rec["title"])
        groups.setdefault(key, []).append(rec)

    # 二级：标题指纹合并（同标题不同链接，例如公众号文章 + 官网）
    by_title: dict[str, str] = {}
    merged: list[dict] = []
    for key, items in groups.items():
        items.sort(key=lambda r: source_rank.get(r.get("source"), 0), reverse=True)
        base = dict(items[0])
        for other in items[1:]:
            for field in ("organizer", "mode", "city", "start_date", "end_date", "deadline",
                          "prize", "evidence"):
                if not base.get(field) and other.get(field):
                    base[field] = other[field]
            base["tracks"] = list(dict.fromkeys((base.get("tracks") or []) + (other.get("tracks") or [])))[:8]
            base.setdefault("sources", [])
            base["sources"] = list(dict.fromkeys(base["sources"] + [other["source"]]))
        tk = norm_title(base["title"])
        if tk in by_title and len(base["title"]) > 6:
            continue  # 标题已收录，丢弃
        by_title[tk] = key
        merged.append(base)
    return merged


def now_iso() -> str:
    # 数据时间统一按北京时间记录；服务器/CI 的本地时区不参与。
    bj = dt.timezone(dt.timedelta(hours=8), "Asia/Shanghai")
    return dt.datetime.now(bj).strftime("%Y-%m-%dT%H:%M:%S")


def ensure_dirs() -> None:
    for d in (DATA_DIR, SITE_DIR, RAW_DIR):
        os.makedirs(d, exist_ok=True)
