#!/usr/bin/env bash
# 常驻静态服务：默认 0.0.0.0:8080，指向 site/
# 环境变量：PORT（默认 8080）、BIND（默认 0.0.0.0）、PYTHON
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
PORT="${PORT:-8080}"
BIND="${BIND:-0.0.0.0}"
echo "AI 赛事雷达 · serving site/ at http://$BIND:$PORT/  (Ctrl-C 停止)"
exec "$PY" scripts/serve_site.py --port "$PORT" --bind "$BIND" --directory site
