# 部署与 24 小时运行手册

这份文档写给「把项目放到家里一台常年开机的电脑上跑」的场景。**不需要 Chrome、不需要 Docker、不需要数据库服务**，只要 Python 3 和网络。

- 每日流水线：抓取 → 去重 → 逐条核验链接 → 生成静态站 → （可选）发摘要邮件
- 常驻服务：一个静态文件服务器，把 `site/` 目录暴露出来
- 资源占用：CPU 峰值一两分钟（核验时），内存 < 200MB，磁盘 < 300MB（不含截图）

---

## 0. 包里有什么

```
ai-race-radar/
├── INSTALL.md            ← 本文档
├── README.md             ← 项目背景、数据契约、信源清单
├── setup.sh              ← 一次性安装（pyyaml → .pylibs，生成 .env）
├── run_daily.sh          ← 每日流水线入口
├── serve.sh              ← 常驻静态服务
├── .env.example          ← 配置模板（复制为 .env）
├── requirements.txt
├── scripts/              ← 全部 Python 脚本（抓取/核验/建站/邮件/工具）
├── data/                 ← 种子、候选、线索、SQLite 去重账本（数据资产）
├── docs/                 ← 信源清单（sources.md）、上线清单、截图
├── site/                 ← 已构建好的静态站（可直接 serve）
├── variants/             ← 设计探索（视觉方向、字体试验），不影响运行
└── .github/              ← 可选：GitHub Actions 定时 + Pages 部署 + Issue 模板
```

---

## 1. 前置条件

| 需要 | 说明 |
|---|---|
| Python | 3.10+（3.9 应该也能跑，但没实测；`python3 -V` 看一下） |
| 网络 | 能访问天池、讯飞、DoraHacks、活动行、知乎活动站、Luma、和鲸、魔搭、biendata 等；**不需要**境外网络 |
| 磁盘 | 建议留 1GB（目前项目 15MB 左右，数据会缓慢增长） |
| 系统 | macOS / Linux / 原生 Windows 10/11（见 [docs/windows-24x7.md](docs/windows-24x7.md)）；WSL 也可 |

> 截图脚本 `scripts/cdp-shot.mjs` 需要本机装 Chrome，只是开发工具，运行站点和流水线都不用。

---

## 2. 五分钟跑起来

```bash
# 1) 解压（把压缩包换成你的文件名）
tar -xzf ai-race-radar-YYYYMMDD.tar.gz
cd ai-race-radar

# 2) 安装依赖（只装 pyyaml 到项目内 .pylibs，不污染系统 Python）
./setup.sh

# 3) 编辑配置（至少填 SITE_URL；邮箱/邮件服务可选）
vi .env

# 4) 先手动跑一遍完整流水线（跳过发信）
SKIP_DIGEST=1 ./run_daily.sh

# 5) 起一个静态服务看看
./serve.sh
# 浏览器打开 http://<这台机器的IP>:8080/
```

第一次跑大约需要 2–5 分钟（要逐条核验 70+ 个链接）。跑完 `site/` 会被重新生成。

---

## 3. 让它每天自动跑

### 3.1 首选：cron（macOS / Linux 通用）

```bash
crontab -e
```

加一行（注意 `python3` 用绝对路径，cron 的 PATH 很干净）：

```cron
0 8 * * * cd /path/to/ai-race-radar && TZ=Asia/Shanghai PYTHON=/usr/bin/python3 ./run_daily.sh
```

- 日志在 `data/run.log`（脚本自带 2MB 轮转）；
- 时区已经由 `run_daily.sh` 固定为 `Asia/Shanghai`，也可以像上面一样再显式指定；
- macOS 上 cron 需要给「终端/`/usr/sbin/cron`」完全磁盘访问权限（系统设置 → 隐私与安全性 → 完全磁盘访问），否则可能无法写文件。

### 3.2 Linux：systemd timer（更稳，推荐）

`/etc/systemd/system/ai-race-radar.service`：

```ini
[Unit]
Description=AI Race Radar daily pipeline

[Service]
Type=oneshot
WorkingDirectory=/path/to/ai-race-radar
Environment=PYTHON=/usr/bin/python3
Environment=TZ=Asia/Shanghai
ExecStart=/bin/bash /path/to/ai-race-radar/run_daily.sh
```

`/etc/systemd/system/ai-race-radar.timer`：

```ini
[Unit]
Description=Run AI Race Radar every day at 08:00

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ai-race-radar.timer
systemctl list-timers | grep ai-race
journalctl -u ai-race-radar -n 50
```

### 3.3 macOS：launchd（不用管终端，开机自启）

`~/Library/LaunchAgents/com.airaceradar.daily.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.airaceradar.daily</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>/Users/你/ai-race-radar/run_daily.sh</string></array>
  <key>WorkingDirectory</key><string>/Users/你/ai-race-radar</string>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>/Users/你/ai-race-radar/data/launchd.log</string>
  <key>StandardErrorPath</key><string>/Users/你/ai-race-radar/data/launchd.log</string>
  <key>EnvironmentVariables</key><dict><key>TZ</key><string>Asia/Shanghai</string></dict>
</dict></plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.airaceradar.daily.plist
launchctl list | grep airaceradar
```

Windows：用原生 PowerShell 部署，见 [docs/windows-24x7.md](docs/windows-24x7.md)——
`deploy\install.ps1` 会注册「每天 08:00 流水线」和「开机启动静态站」两个计划任务（SYSTEM 账户，不依赖登录）。

---

## 4. 让它 24 小时提供站点

### 4.1 局域网内访问（最简单）

```bash
./serve.sh          # 默认 0.0.0.0:8080
```

然后同一 Wi-Fi 下用 `http://<这台机器的局域网IP>:8080/` 打开。手机也能看。

常驻（macOS launchd 示例）：

```xml
<!-- ~/Library/LaunchAgents/com.airaceradar.serve.plist -->
<plist version="1.0"><dict>
  <key>Label</key><string>com.airaceradar.serve</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>/Users/你/ai-race-radar/serve.sh</string></array>
  <key>WorkingDirectory</key><string>/Users/你/ai-race-radar</string>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/Users/你/ai-race-radar/data/serve.log</string>
  <key>StandardErrorPath</key><string>/Users/你/ai-race-radar/data/serve.log</string>
</dict></plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.airaceradar.serve.plist
```

Linux systemd：

```ini
# /etc/systemd/system/ai-race-radar-web.service
[Unit]
Description=AI Race Radar static site
[Service]
WorkingDirectory=/path/to/ai-race-radar
ExecStart=/usr/bin/python3 -m http.server 8080 --bind 0.0.0.0 --directory site
Restart=always
[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now ai-race-radar-web
```

> `python -m http.server` 适合家用局域网，不建议直接暴露到公网（没有 HTTPS、没有缓存头）。

### 4.2 想让公网访问（可选）

三种常见做法，按省事程度排序：

1. **Cloudflare Tunnel（推荐，免费）**：装 `cloudflared`，`cloudflared tunnel --url http://localhost:8080` 先拿临时域名；正式绑定自己的域名后就是 HTTPS。
2. **Tailscale Funnel**：零配置 HTTPS 域名，适合自己远程访问。
3. **路由器端口映射 + Caddy**：需要公网 IP，Caddy 自动签 HTTPS，反代到 8080。

上线后记得把 `.env` 里的 `SITE_URL` 改成真实地址，再跑一次 `./run_daily.sh`（或只跑 `python3 scripts/build_site.py`），`sitemap.xml` / `llms.txt` / `api/events.json` 里的绝对链接才会正确。

### 4.3 别让它睡着

- macOS：系统设置 → 电池 → 「防止电脑自动进入睡眠」打开；或 `sudo pmset -a sleep 0 disksleep 0`
- Linux：`sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target`
- 让机器只负责跑这个：插电、关闭自动更新重启，或用 `caffeinate` 常驻

---

## 5. 配置说明（`.env`）

| 变量 | 作用 | 建议 |
|---|---|---|
| `SITE_URL` | sitemap / llms / feed 里的站点地址 | **必填**，写成实际访问地址 |
| `SUBMIT_EMAIL` | 投稿按钮的收件邮箱 | 想收投稿就填；不填则按钮变成「复制内容」 |
| `SUBSCRIBE_URL` | 「关于」页的邮件订阅表单地址 | 可选；Tally / Buttondown 等 |
| `SUBSCRIBE_EMAIL` | 「关于」页的 mailto 订阅收件邮箱 | 可选；人工把地址加进 `data/subscribers.txt` |
| `SMTP_HOST/PORT/USER/PASS` | 邮件摘要的 SMTP | 用 Resend（`smtp.resend.com:465`）或任意邮箱 SMTP；摘要会附 `.ics` 日历 |
| `DIGEST_FROM` | 发件人 | 必须与 SMTP 账号匹配 |
| `DIGEST_TO` | 收件人（逗号分隔） | 也可以用 `data/subscribers.txt`，一行一个 |
| `DIGEST_DAYS` | 「新收录」窗口天数 | 默认 2 |
| `SKIP_DIGEST=1` | 临时不发信 | 调试时用 |

`run_daily.sh` 会自动 `source .env`；`.env` 已加入 `.gitignore`，不会被误提交。

---

## 6. 数据与备份（重要）

真正值钱的是 **`data/races.db`**：它是去重账本，记录每条赛事的 `first_seen`。丢了它，第二天所有赛事都会变成「新收录」。

每天备份（加一条 cron）：

```cron
30 9 * * * cd /path/to/ai-race-radar && tar -czf /backup/ai-race-radar-$(date +\%F).tar.gz data site && find /backup -name 'ai-race-radar-*.tar.gz' -mtime +30 -delete
```

换机器/重装：整个目录拷过去 → `./setup.sh` → `SKIP_DIGEST=1 ./run_daily.sh` 即可，历史不会丢。

---

## 7. 日常运维

```bash
tail -f data/run.log                  # 看当天流水线
SKIP_DIGEST=1 ./run_daily.sh          # 手动跑一次
python3 scripts/verify.py --limit 5   # 只核验前 5 条（调试）
python3 scripts/build_site.py         # 只重建站点
python3 scripts/send_digest.py --dry-run   # 只生成邮件预览，不发信
node scripts/cdp-shot.mjs "file://$PWD/site/index.html" /tmp/m.png 390 844 2  # 手机视口截图（可选）
```

- 新增赛事：往 `data/seeds.yaml` 追加一条（字段见 README「数据契约」），或等抓取器自动发现；
- 删掉某条：从 `seeds.yaml` 移除后跑一遍流水线（或从 `data/races.db` 删除对应行再重建）；
- 站点的 `site/race/` 每次构建都会清空重写，不要手动改产物，改 `scripts/site_ui.py` / `scripts/theme.py`。

---

## 8. 故障排查

| 现象 | 原因 / 处理 |
|---|---|
| `ModuleNotFoundError: yaml` | 没跑 `./setup.sh`，或跑脚本时改了 `PYTHON` 环境变量导致 `.pylibs` 没注入 |
| `run_daily.sh: Permission denied` | `chmod +x run_daily.sh setup.sh serve.sh` |
| 某一步 `[warn] ... 抓取失败` | 网络/反爬波动；采集器可能保留旧候选，`verify.py` 在候选数低于库内 60% 时会跳过清理，避免批量误删，属正常降级 |
| 公众号补全一直跳过 | 搜狗限流（约 45 分钟冷却），属正常；每天最多补 2 条 |
| 页面 404 | `serve.sh` 的工作目录必须指向项目的 `site/`；端口被占用就 `PORT=8090 ./serve.sh` |
| 首页还是旧数据 | 只跑了抓取没跑建站；跑 `./run_daily.sh` 或 `python3 scripts/build_site.py` |
| 截止日差一天 | 机器时区不是北京时间；`run_daily.sh` 已固定 `TZ=Asia/Shanghai`，别覆盖它 |
| `sitemap.xml` 里是 example.com | `.env` 的 `SITE_URL` 没填，或填完没重建站点 |
| 磁盘变大 | `data/raw/` 是信源快照，可整目录删；`data/run.log` 会自动轮转 |

---

## 9. 安全提醒

- 只暴露 `site/` 目录；**不要**把项目根目录（含 `.env`、`data/`）用静态服务暴露出去；
- `.env` 里有 SMTP 密码，注意文件权限（`chmod 600 .env`）；
- 公网访问建议走 Cloudflare Tunnel / Tailscale，比直接端口映射安全；
- 可选：`git init` 后只提交代码与数据（`.env`、`.pylibs/`、`data/run.log` 已在 `.gitignore`）。
