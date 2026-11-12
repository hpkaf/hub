# Windows 24×7 部署手册（原生 PowerShell）

这份文档对应「一台常年开机的 Windows 10/11 电脑」：每天 08:00 自动抓取 → 核验 → 建站，
并把 `site/` 作为静态站点常驻在局域网里。不依赖 WSL、Docker、IIS 或任何后台框架。

> 项目自带的 `run_daily.sh` / `serve.sh` / `INSTALL.md` 是 macOS / Linux 版本；
> Windows 请用本文的 `deploy\*.ps1`。二者产物、数据格式完全一致。

---

## 1. 目录与文件

```
ai-race-radar\
├── deploy\
│   ├── run_daily.ps1      # 每日流水线（抓取 → 核验 → 建站 → 可选发信）
│   ├── serve.ps1          # 常驻静态服务（崩溃 5 秒后自动重启）
│   ├── install.ps1        # 一键安装：计划任务 + 防火墙 + 启动站点
│   ├── uninstall.ps1      # 卸载计划任务与防火墙规则（保留数据）
│   ├── status.ps1         # 状态速查：任务 / 端口 / 数据量 / 最近日志
│   └── python-path.txt    # 安装时写入的 Python 绝对路径
├── .env                   # SITE_URL、投稿/订阅邮箱、SMTP（由 install.ps1 生成）
├── data\
│   ├── races.db           # 去重账本（最重要，自动备份）
│   ├── races.json         # 全量导出
│   ├── run.log            # 每日流水线日志（2MB 轮转）
│   ├── serve.log          # 静态服务日志（5MB 轮转）
│   └── backups\           # races-YYYYMMDD-HHMMSS.db，保留最近 30 份
└── site\                  # 构建产物，HTTP 根目录只指向这里
```

---

## 2. 安装（管理员 PowerShell）

```powershell
cd E:\AI赛事\ai-race-radar
powershell -ExecutionPolicy Bypass -File deploy\install.ps1
```

脚本会：

1. 记录 `python.exe` 绝对路径（计划任务在 SYSTEM 账户下没有用户 PATH）；
2. 检查 PyYAML，缺失时装进项目内 `.pylibs`；
3. 没有 `.env` 时生成，并把 `SITE_URL` 设为 `http://<本机局域网IP>:8080`；
4. 注册两个 **以 SYSTEM 运行** 的计划任务（不要求用户登录）：
   - `AI Race Radar - Daily`：每天 08:00，错过则开机后补跑（StartWhenAvailable）；
   - `AI Race Radar - Web`：开机启动，退出后 1 分钟重启（最多 999 次）；
5. 放行 TCP 8080（仅本地子网 `LocalSubnet`，当前网络是「公用」也能用）；
6. 立即启动 Web 任务，并请求 `http://127.0.0.1:8080/` 验证。

安装完成后访问：

- 本机：`http://127.0.0.1:8080/`
- 同 Wi-Fi / 局域网：`http://192.168.1.3:8080/`（以 `.env` 的 `SITE_URL` 为准）

> 端口被占用时：`deploy\uninstall.ps1` 后执行
> `deploy\install.ps1 -Port 8090`，再改 `.env` 的 `SITE_URL` 并重建站点。

---

## 3. 日常操作

```powershell
# 手动跑一次（跳过发信）
powershell -ExecutionPolicy Bypass -File deploy\run_daily.ps1 -SkipDigest

# 只重建站点，不抓取不核验
python scripts\build_site.py

# 状态速查
powershell -ExecutionPolicy Bypass -File deploy\status.ps1

# 只核验前 10 条（调试）
python scripts\verify.py --limit 10

# 邮件预览，不发信
python scripts\send_digest.py --dry-run
```

`run_daily.ps1` 的顺序（与 `run_daily.sh` 对齐，并补齐了原脚本漏掉的 A 层平台源）：

```
天池 → 讯飞 → DataFountain → AI Studio → DoraHacks → 活动行
→ 官方活动站（知乎）→ 魔搭/和鲸/biendata → Luma 日历
→ 联谱线索 → 湾区日历线索 → 公众号线索补全（限流）
→ verify.py（核验 + 去重 + SQLite）→ build_site.py → send_digest.py
```

任何抓取步骤失败只记 `WARN` 并继续；`verify.py` / `build_site.py` 失败才中止。
每轮开始前自动备份 `data\races.db`。每个抓取步骤有硬超时（Luma 180 秒、其他 300 秒、核验 1200 秒），
超时会杀掉子进程并沿用上一轮候选——**不会**因为某个源卡死而拖住整条流水线。

---

## 4. 日志与排错

| 文件 | 内容 |
|---|---|
| `data\run.log` | 每日流水线，含每个抓取器的 exit code、耗时、核验统计 |
| `data\serve.log` | HTTP 访问日志与重启记录 |
| 计划任务 | `taskschd.msc` → 任务计划程序库 → `AI Race Radar - *` |

常见问题：

| 现象 | 处理 |
|---|---|
| 站点打不开 | `deploy\status.ps1` 看端口；`Get-ScheduledTaskInfo "AI Race Radar - Web"` 看上次结果 |
| 局域网打不开、本机正常 | 当前网络被识别为「公用」时已按 `LocalSubnet` 放行；再检查路由器 AP 隔离 |
| 首页是旧数据 | 只跑了抓取没建站：`python scripts\build_site.py` |
| 抓取大量失败 | 看 `run.log` 的 `[warn]`；候选数低于库内 60% 时 `verify.py` 会跳过清理，旧数据不会丢 |
| Luma 抓取超时 | `api.lu.ma` 在部分网络会走到不可达的 IPv6；已做 IPv4 优先 + 180 秒超时，旧候选保留，属已知降级 |
| 截止日差一天 | 本机时区必须是 UTC+08:00；`run_daily.ps1` 会检查并告警 |
| 邮件没发 | `.env` 的 `SMTP_*` / `DIGEST_TO` 未配；无收件人时脚本会静默跳过 |
| 端口冲突 | 改端口：`uninstall.ps1` → `install.ps1 -Port 8090` → 改 `.env` 的 `SITE_URL` → 重建 |

---

## 5. 备份与恢复

- 每日流水线开始前自动复制 `races.db` 到 `data\backups\`，保留最近 30 份；
- 额外建议：每周把整个 `data\` 和 `site\` 复制到别的盘 / 网盘；
- 恢复：停 Web 任务 → 用备份覆盖 `data\races.db` → 跑一次 `run_daily.ps1`。

`races.db` 记录 `first_seen`，是「新收录」判断的唯一依据；删掉它会让所有赛事重新变成新收录。

---

## 6. 与 Unix 版的差异

| 项 | `run_daily.sh`（原版） | `deploy\run_daily.ps1`（Windows） |
|---|---|---|
| 平台源 | 未调用天池/讯飞/DF/AI Studio/Dora/活动行 | 已补齐（6 个采集器） |
| 时区 | `export TZ=Asia/Shanghai` | Windows Python 不读 `TZ`；改为检查系统偏移 |
| 日志 | `tee` + `wc` 轮转 | `Add-Content` + 字节级轮转 |
| 清理保护 | 候选 ≥10 条才 prune | 候选 ≥ max(10, 库内 60%) 才 prune |
| 备份 | 需自己加 cron | 每轮自动备份 30 份 |
| 常驻 | `serve.sh` + launchd/systemd | `serve.ps1` + 计划任务，崩溃自动重启 |

---

## 7. 电源与休眠

这台机器当前是「高性能」方案，交流电下「睡眠 / 休眠」都设为 0（从不），计划任务也启用了
`WakeToRun`（到点可唤醒）。如果以后改过电源方案，用下面命令恢复：

```powershell
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change monitor-timeout-ac 15   # 显示器可以睡，主机别睡
```

> 只关显示器不影响站点；主机一旦睡眠，8080 会断，08:00 的流水线也要等唤醒后才补跑。

---

## 8. 安全

- 只暴露 `site\`；`.env`、`data\` 不在 HTTP 根下；
- 防火墙规则限定 `LocalSubnet`，不对公网开放；
- 如需公网访问，优先 Cloudflare Tunnel / Tailscale，不要直接做端口映射；
- `.env` 含 SMTP 授权码，不要提交到仓库（`.gitignore` 已忽略）。
