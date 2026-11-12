#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日摘要邮件：把「新收录」和「即将截止」发到订阅者邮箱。

环境变量：
  SMTP_HOST   例如 smtp.qq.com / smtp.163.com / smtp.resend.com
  SMTP_PORT   默认 465（SSL）；587 走 STARTTLS
  SMTP_USER   发信账号
  SMTP_PASS   授权码（不是登录密码；QQ/163 需在设置里开 SMTP 并生成授权码）
  DIGEST_FROM 可选，默认 = SMTP_USER
  DIGEST_TO   可选，逗号分隔；缺省读 data/subscribers.txt（每行一个，忽略 # 注释）

用法：
  python3 scripts/send_digest.py --dry-run        # 只生成预览，不发信
  python3 scripts/send_digest.py --days 2         # 新收录窗口 = 2 天
  python3 scripts/send_digest.py                  # 真发（需 SMTP_* 环境变量）
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import smtplib
import sys
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common  # noqa: E402

RACES_PATH = os.path.join(common.DATA_DIR, "races.json")
SUBSCRIBERS_PATH = os.path.join(common.DATA_DIR, "subscribers.txt")
STATE_PATH = os.path.join(common.DATA_DIR, "digest_state.json")
PREVIEW_PATH = os.path.join(common.DATA_DIR, "digest_preview.html")

BOOTSTRAP = """<p style="color:#6f6f68;font-size:13px">你收到这封邮件，是因为你的邮箱出现在
AI 赛事雷达的订阅列表里。回复「退订」即可移除。</p>"""


def esc(v) -> str:
    return html.escape(str(v if v is not None else ""), quote=True)


def fmt_date(value) -> str:
    if not value:
        return "待确认"
    try:
        d = dt.date.fromisoformat(value)
    except ValueError:
        return str(value)
    return f"{d.month}月{d.day}日"


def deadline_text(rec: dict) -> str:
    d = common.days_until(rec.get("deadline"))
    if d is None:
        return "截止时间待确认"
    if d > 3:
        return f"{fmt_date(rec['deadline'])} 截止"
    if d > 1:
        return f"还有 {d} 天截止"
    if d == 1:
        return "明天截止"
    if d == 0:
        return "今天截止"
    return "已截止"


def load_recipients() -> list[str]:
    env = os.environ.get("DIGEST_TO", "").strip()
    if env:
        return [x.strip() for x in env.split(",") if x.strip()]
    if not os.path.exists(SUBSCRIBERS_PATH):
        return []
    out = []
    with open(SUBSCRIBERS_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    return out


def select(records: list[dict], days: int, closing_days: int = 3) -> tuple[list, list]:
    today = dt.date.today()
    cutoff = (today - dt.timedelta(days=days)).isoformat()
    new_items, closing_items = [], []
    for rec in records:
        first = (rec.get("first_seen") or "")[:10]
        status = rec.get("status") or common.compute_status(rec)
        if status == "closed":
            continue
        d = common.days_until(rec.get("deadline"))
        if d is not None and 0 <= d <= closing_days:
            closing_items.append(rec)
        elif first and first >= cutoff:
            new_items.append(rec)
    closing_items.sort(key=lambda r: (r.get("deadline") or "9999", r.get("title") or ""))
    new_items.sort(key=lambda r: (r.get("first_seen") or "", r.get("title") or ""))
    return new_items, closing_items


def item_html(rec: dict, prefix: str) -> str:
    pill = {"closing": ("#fff2e8", "#c2410c", "即将截止"),
            "open": ("#eaf7ef", "#0f7b4f", "报名中"),
            "upcoming": ("#f0efea", "#565650", "即将开始")}.get(rec.get("status") or "", ("#f0efea", "#565650", "待确认"))
    org = esc(rec.get("organizer") or "主办方待确认")
    prize = f'<span style="color:#6f6f68;font-size:12px"> · {esc(rec.get("prize"))}</span>' if rec.get("prize") else ""
    return f"""<tr><td style="padding:14px 0;border-bottom:1px solid #e6e5df">
  <div style="font-size:11px;color:{pill[1]};background:{pill[0]};display:inline-block;border-radius:999px;padding:1px 8px">{pill[2]}</div>
  <div style="font-size:16px;font-weight:700;margin:6px 0 2px"><a href="{prefix}race/{esc(rec['id'])}.html" style="color:#141413;text-decoration:none">{esc(rec.get('title'))}</a></div>
  <div style="font-size:13px;color:#6f6f68">{org}{prize}</div>
  <div style="font-size:13px;color:#141413;margin-top:4px">⏰ {esc(deadline_text(rec))} &nbsp;
    <a href="{esc(rec.get('url'))}" style="color:#0d9488;text-decoration:none">官方报名页 →</a></div>
</td></tr>"""


def render_html(new_items: list, closing_items: list, records: list, days: int) -> str:
    site = os.environ.get("SITE_URL", "https://ai-race-radar.example.com").rstrip("/") + "/"
    total_online = sum(1 for r in records if r.get("mode") == "online" and r.get("status") != "closed")
    rows_new = "".join(item_html(r, site) for r in new_items) or \
        '<tr><td style="padding:16px 0;color:#6f6f68;font-size:13px">过去 %d 天没有新收录。</td></tr>' % days
    rows_close = "".join(item_html(r, site) for r in closing_items) or \
        '<tr><td style="padding:16px 0;color:#6f6f68;font-size:13px">未来几天没有临近截止的赛事。</td></tr>'
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>AI 赛事雷达 · 每日摘要</title></head>
<body style="margin:0;background:#f7f7f4;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f7f7f4;padding:24px 0">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#fff;border:1px solid #e6e5df;border-radius:14px;padding:28px 30px">
<tr><td>
  <div style="font-size:12px;letter-spacing:2px;color:#0d9488;font-weight:700">AI RACE RADAR</div>
  <div style="font-size:22px;font-weight:800;margin:6px 0 4px;color:#141413">AI 赛事雷达 · 每日摘要</div>
  <div style="font-size:13px;color:#6f6f68">{dt.date.today().isoformat()} · 收录 {len(records)} 场，其中线上可报名 {total_online} 场</div>

  <div style="font-size:14px;font-weight:700;margin:24px 0 4px;color:#141413">🆕 新收录（{len(new_items)}）</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows_new}</table>

  <div style="font-size:14px;font-weight:700;margin:26px 0 4px;color:#141413">⏰ 3 天内截止（{len(closing_items)}）</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows_close}</table>

  <div style="border-top:1px solid #e6e5df;margin-top:26px;padding-top:14px">
    <a href="{site}" style="color:#0d9488;font-size:13px;text-decoration:none">打开完整列表 →</a> &nbsp;·&nbsp;
    <a href="{site}calendar.ics" style="color:#0d9488;font-size:13px;text-decoration:none">日历订阅 →</a>
  </div>
  <div style="margin-top:10px;font-size:12px;color:#6f6f68">📎 附件 <b>ai-race-radar.ics</b> 可一次性导入日历（含报名截止提醒）</div>
  {BOOTSTRAP}
</td></tr></table>
</td></tr></table></body></html>"""


def render_text(new_items: list, closing_items: list, records: list, days: int) -> str:
    lines = [f"AI 赛事雷达 · 每日摘要（{dt.date.today().isoformat()}）",
             f"收录 {len(records)} 场", "", f"【新收录 {len(new_items)}】"]
    for r in new_items or []:
        lines.append(f"- {r.get('title')} | {r.get('organizer') or '-'} | {deadline_text(r)}")
        lines.append(f"  {r.get('url')}")
    if not new_items:
        lines.append("（过去 %d 天没有新收录）" % days)
    lines += ["", f"【3 天内截止 {len(closing_items)}】"]
    for r in closing_items:
        lines.append(f"- {r.get('title')} | {deadline_text(r)}")
        lines.append(f"  {r.get('url')}")
    if not closing_items:
        lines.append("（无）")
    lines += ["", "—— 本邮件由 AI 赛事雷达自动生成，报名以官方页面为准。",
              "附件 ai-race-radar.ics 可直接导入 Apple 日历 / Outlook / Google 日历。"]
    return "\n".join(lines)


def send(subject: str, http_html: str, text: str, recipients: list[str]) -> bool:
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "465"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    if not (host and user and password):
        print("[skip] 未配置 SMTP_HOST / SMTP_USER / SMTP_PASS；预览已生成，配置授权码后自动发送")
        return False
    msg = MIMEMultipart("mixed")
    msg["Subject"] = Header(subject, "utf-8")
    from_addr = os.environ.get("DIGEST_FROM", "").strip()
    if from_addr:
        name, addr = parseaddr(from_addr)
        if not addr or "@" not in addr:
            raise SystemExit("DIGEST_FROM 需写成「显示名 <邮箱>」或裸邮箱，例如 digest@example.com")
        envelope_from = addr
        msg["From"] = formataddr((name or "AI 赛事雷达", addr))
    else:
        envelope_from = user
        msg["From"] = formataddr(("AI 赛事雷达", user))
    msg["To"] = ", ".join(recipients)
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(text, "plain", "utf-8"))
    alt.attach(MIMEText(http_html, "html", "utf-8"))
    msg.attach(alt)
    # 附一份日历文件：收件人可以直接导入 Apple 日历 / Outlook / Google 日历
    ics_path = os.path.join(common.SITE_DIR, "calendar.ics")
    if os.path.exists(ics_path):
        try:
            with open(ics_path, encoding="utf-8") as fh:
                ics_text = fh.read()
        except OSError:
            ics_text = ""
        if ics_text:
            ics_part = MIMEText(ics_text, "calendar", "utf-8")
            ics_part.add_header("Content-Disposition", "attachment", filename="ai-race-radar.ics")
            msg.attach(ics_part)
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=30)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
        server.starttls()
    try:
        server.login(user, password)
        server.sendmail(envelope_from, recipients, msg.as_string())
    finally:
        server.quit()
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=2, help="新收录窗口（天），默认 2")
    parser.add_argument("--dry-run", action="store_true", help="只生成预览，不发信")
    parser.add_argument("--limit", type=int, default=0, help="最多展示条数（调试）")
    args = parser.parse_args()

    records = common.load_json(RACES_PATH, [])
    if not records:
        print(f"[warn] {RACES_PATH} 为空，先跑 scripts/verify.py")
    new_items, closing_items = select(records, args.days)
    if args.limit:
        new_items, closing_items = new_items[: args.limit], closing_items[: args.limit]

    subject = f"AI 赛事雷达｜新收录 {len(new_items)}，3 天内截止 {len(closing_items)}（{dt.date.today().strftime('%m/%d')}）"
    page = render_html(new_items, closing_items, records, args.days)
    text = render_text(new_items, closing_items, records, args.days)
    os.makedirs(os.path.dirname(PREVIEW_PATH), exist_ok=True)
    with open(PREVIEW_PATH, "w", encoding="utf-8") as fh:
        fh.write(page)

    recipients = load_recipients()
    print(subject)
    print(f"新收录 {len(new_items)} / 3 天内截止 {len(closing_items)}；预览：{PREVIEW_PATH}")
    if args.dry_run:
        print("--- dry-run 纯文本 ---")
        print(text)
        return 0
    if not recipients:
        print("[skip] 没有订阅者：在 data/subscribers.txt 写邮箱，或设置 DIGEST_TO")
        return 0
    if not send(subject, page, text, recipients):
        return 0
    common.save_json({"last_sent_at": common.now_iso(), "count": len(recipients)}, STATE_PATH)
    print(f"[ok] 已发送给 {len(recipients)} 个订阅者")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
