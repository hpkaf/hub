#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""静态站点服务：比 `python -m http.server` 多两件事——

1. `.ics` 返回 `text/calendar`（Windows 上 Python 的 mimetypes 不认 .ics，
   默认会发 application/octet-stream，部分日历客户端会拒收）；
2. `.json` / `.xml` 显式 UTF-8，方便 Calendar / RSS / Agent 直接解析。

用法：
  python scripts/serve_site.py --port 8080 --bind 0.0.0.0 --directory site
"""
from __future__ import annotations

import argparse
import functools
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class SiteHandler(SimpleHTTPRequestHandler):
    def guess_type(self, path):
        lower = str(path).lower()
        if lower.endswith(".ics"):
            return "text/calendar; charset=utf-8"
        if lower.endswith(".json"):
            return "application/json; charset=utf-8"
        if lower.endswith(".md"):
            return "text/markdown; charset=utf-8"
        if lower.endswith(".txt"):
            return "text/plain; charset=utf-8"
        if lower.endswith(".xml"):
            return "application/xml; charset=utf-8"
        return super().guess_type(path)

    def log_message(self, fmt, *args):
        # 默认访问日志；交给外层 serve.ps1 / serve.sh 收集
        super().log_message(fmt, *args)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    parser.add_argument("--bind", default=os.environ.get("BIND", "0.0.0.0"))
    parser.add_argument("--directory", default="site")
    args = parser.parse_args()

    directory = os.path.abspath(args.directory)
    handler = functools.partial(SiteHandler, directory=directory)
    httpd = ThreadingHTTPServer((args.bind, args.port), handler)
    print(f"AI 赛事雷达 · serving {directory} at http://{args.bind}:{args.port}/", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
