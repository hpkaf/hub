#!/usr/bin/env bash
# AI 赛事雷达 · 每日流水线：核验 → 生成站点 → 发摘要
# 用法：./run_daily.sh            （默认核验全部链接）
#       SKIP_DIGEST=1 ./run_daily.sh
#       PYTHON=/path/to/python3 ./run_daily.sh
set -euo pipefail
cd "$(dirname "$0")"

# 时区固定为北京时间（截止日判断按北京日期，机器在别的时区时避免差一天）
export TZ="${TZ:-Asia/Shanghai}"

# 可选本地配置：SUBMIT_EMAIL / SITE_URL / SMTP_* / DIGEST_TO 等
if [ -f .env ]; then
  set -a; . ./.env; set +a
fi

ROOT="$PWD"
PY="${PYTHON:-python3}"
export PYTHONPATH="$ROOT/.pylibs${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p data
LOG="$ROOT/data/run.log"

{
  echo "=== $(date '+%F %T %Z') 开始 ==="
  # A 层：平台 JSON/SSR 采集器（各自 merge 进 candidates_comp.json / candidates_hack.json，
  # 失败时脚本在写文件前退出，候选文件保持上一轮内容）
  "$PY" scripts/fetch_tianchi.py || echo "[warn] 天池抓取失败，沿用上一次 candidates_comp.json"
  "$PY" scripts/fetch_xfyun.py || echo "[warn] 讯飞抓取失败，沿用上一次 candidates_comp.json"
  "$PY" scripts/fetch_datafountain.py || echo "[warn] DataFountain 抓取失败，沿用上一次 candidates_comp.json"
  "$PY" scripts/fetch_aistudio.py || echo "[warn] AI Studio 抓取失败，沿用上一次 candidates_comp.json"
  "$PY" scripts/fetch_dora.py || echo "[warn] DoraHacks 抓取失败，沿用上一次 candidates_hack.json"
  "$PY" scripts/fetch_hdx.py || echo "[warn] 活动行抓取失败，沿用上一次 candidates_hack.json"
  "$PY" scripts/fetch_event_sites.py || echo "[warn] 官方活动站抓取失败，沿用上一次 candidates_events.json"
  "$PY" scripts/collect_sources.py || echo "[warn] 扩展信源抓取失败，沿用上一次 candidates_extra.json"
  "$PY" scripts/collect_luma.py || echo "[warn] Luma 日历抓取失败，沿用上一次 candidates_luma.json"
  "$PY" scripts/collect_lianpu.py || echo "[warn] 联谱线索抓取失败，沿用上一次 leads_lianpu.json"
  "$PY" scripts/collect_wqai.py || echo "[warn] 湾区内核截止日抓取失败，沿用上一次 leads_wqai.json"
  "$PY" scripts/enrich_wechat_leads.py --limit 2 || echo "[warn] 公众号线索补全跳过（限流或网络原因）"
  "$PY" scripts/verify.py "$@"
  "$PY" scripts/build_site.py
  if [ "${SKIP_DIGEST:-0}" != "1" ]; then
    "$PY" scripts/send_digest.py --days "${DIGEST_DAYS:-2}" || echo "[warn] 摘要邮件失败，检查 SMTP 环境变量（站点已生成）"
  fi
  echo "=== $(date '+%F %T %Z') 完成 ==="
} 2>&1 | tee -a "$LOG"

# 日志超过 2MB 时只保留最后 1MB，避免 24 小时运行越滚越大
if [ -f "$LOG" ] && [ "$(wc -c < "$LOG" | tr -d ' ')" -gt 2097152 ]; then
  tail -c 1048576 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
