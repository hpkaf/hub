#!/usr/bin/env bash
# 一次性安装：把 pyyaml 装进项目内 .pylibs，并生成 .env
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"

echo "== python: $($PY -V 2>&1)"
"$PY" -m pip install --target .pylibs --upgrade pyyaml

if [ ! -f .env ]; then
  cp .env.example .env
  echo "== 已生成 .env（记得填 SITE_URL；投稿邮箱/邮件服务可选）"
fi

echo "== 完成。下一步：SKIP_DIGEST=1 ./run_daily.sh"
