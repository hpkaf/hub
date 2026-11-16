# AI 赛事雷达 · Windows 每日流水线
#
# 与 run_daily.sh 等价，额外补上 A 层平台抓取器（原 run_daily.sh 漏掉了这 6 个），
# 并在每次核验前备份 data/races.db。由计划任务「AI Race Radar - Daily」每天 08:00 调用，
# 也可以手动执行：
#   powershell -ExecutionPolicy Bypass -File deploy\run_daily.ps1
#   powershell -ExecutionPolicy Bypass -File deploy\run_daily.ps1 -SkipFetch
#   powershell -ExecutionPolicy Bypass -File deploy\run_daily.ps1 -SkipDigest
[CmdletBinding()]
param(
    [switch]$SkipFetch,
    [switch]$SkipDigest,
    [string]$Python
)

$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$DataDir = Join-Path $Root 'data'
$Log = Join-Path $DataDir 'run.log'
New-Item -ItemType Directory -Force $DataDir | Out-Null

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $line = "[{0}] [{1}] {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    Write-Host $line
    Add-Content -Path $Log -Value $line -Encoding utf8
}

# 日志轮转：超过 2MB 时只保留最后 1MB
if (Test-Path $Log) {
    if ((Get-Item $Log).Length -gt 2MB) {
        $bytes = [System.IO.File]::ReadAllBytes($Log)
        $tail = New-Object byte[] (1MB)
        [Array]::Copy($bytes, $bytes.Length - $tail.Length, $tail, 0, $tail.Length)
        [System.IO.File]::WriteAllBytes($Log, $tail)
    }
}

Write-Log '================ run_daily.ps1 ================'
Write-Log ("host={0} user={1} pid={2}" -f $env:COMPUTERNAME, $env:USERNAME, $PID)

$offset = [TimeZoneInfo]::Local.GetUtcOffset((Get-Date))
if ($offset.TotalHours -ne 8) {
    Write-Log ("本机时区偏移 {0}h，不是 UTC+08:00；截止日/状态可能差一天" -f $offset.TotalHours) 'WARN'
}

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONPATH = (Join-Path $Root '.pylibs')

# 加载 .env（KEY=VALUE，# 注释；同名变量以 .env 为准，与 run_daily.sh 的 source 行为一致）
$envFile = Join-Path $Root '.env'
if (Test-Path $envFile) {
    foreach ($raw in (Get-Content $envFile -Encoding UTF8)) {
        $line = $raw.Trim()
        if ($line.Length -gt 0 -and $line[0] -eq [char]0xFEFF) { $line = $line.Substring(1) }
        if (-not $line -or $line.StartsWith('#')) { continue }
        $idx = $line.IndexOf('=')
        if ($idx -lt 1) { continue }
        $key = $line.Substring(0, $idx).Trim()
        $val = $line.Substring($idx + 1).Trim()
        if ($val.Length -ge 2 -and (($val.StartsWith('"') -and $val.EndsWith('"')) -or ($val.StartsWith("'") -and $val.EndsWith("'")))) {
            $val = $val.Substring(1, $val.Length - 2)
        }
        Set-Item -Path ("Env:" + $key) -Value $val
    }
}

# 定位 Python：参数 > deploy\python-path.txt > PATH
if (-not $Python) {
    $pyFile = Join-Path $PSScriptRoot 'python-path.txt'
    if (Test-Path $pyFile) { $Python = (Get-Content $pyFile -Raw -Encoding UTF8).Trim() }
}
if (-not $Python) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $Python = $cmd.Source }
}
if (-not $Python -or -not (Test-Path $Python)) {
    Write-Log '找不到 Python，请先运行 deploy\install.ps1 或传 -Python <路径>' 'ERROR'
    exit 2
}
Write-Log ("python = {0}" -f $Python)

function Invoke-Py {
    param(
        [string]$Name,
        [string[]]$ArgList,
        [switch]$Fatal,
        [int]$TimeoutSec = 600
    )
    Write-Log ("==> {0}" -f $Name)
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $code = 0
    $timedOut = $false
    $outText = ''
    $errText = ''
    try {
        $argString = ($ArgList | ForEach-Object {
            if ($_ -match '\s') { '"' + $_ + '"' } else { $_ }
        }) -join ' '
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $Python
        $psi.Arguments = $argString
        $psi.WorkingDirectory = $Root
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.CreateNoWindow = $true
        $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
        $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8

        $proc = New-Object System.Diagnostics.Process
        $proc.StartInfo = $psi
        [void]$proc.Start()
        $stdoutTask = $proc.StandardOutput.ReadToEndAsync()
        $stderrTask = $proc.StandardError.ReadToEndAsync()
        if (-not $proc.WaitForExit($TimeoutSec * 1000)) {
            $timedOut = $true
            try { $proc.Kill() } catch { }
            [void]$proc.WaitForExit(5000)
            $code = 124
        } else {
            $code = $proc.ExitCode
        }
        if ($stdoutTask) { $outText = $stdoutTask.Result }
        if ($stderrTask) { $errText = $stderrTask.Result }
    } catch {
        Write-Log ("启动失败：{0}" -f $_.Exception.Message) 'ERROR'
        $code = 127
    }
    $sw.Stop()

    # 直接读进程原始输出：PYTHONIOENCODING=utf-8 保证中文/emoji 不经过控制台代码页
    $lines = @()
    if ($outText) { $lines += ($outText -split "`r?`n") }
    if ($errText) { $lines += ($errText -split "`r?`n") }
    $lines = @($lines | Where-Object { $_ -ne '' })
    if ($lines.Count -gt 0) {
        $lines | Out-File -FilePath $Log -Append -Encoding utf8
        $lines | Select-Object -Last 4 | ForEach-Object { Write-Host ([string]$_) }
    }
    if ($timedOut) {
        Write-Log ("{0} 超时（>{1}s），已强制结束；沿用上一轮候选" -f $Name, $TimeoutSec) 'ERROR'
    }
    $level = 'INFO'
    if ($code -ne 0) { $level = 'WARN' }
    Write-Log ("<== {0} exit={1} {2}s" -f $Name, $code, [math]::Round($sw.Elapsed.TotalSeconds, 1)) $level
    if ($code -ne 0 -and $Fatal) {
        throw ("{0} 失败（exit {1}），流水线中止" -f $Name, $code)
    }
}

# 备份去重账本：单点依赖，保留最近 30 份
$db = Join-Path $DataDir 'races.db'
if (Test-Path $db) {
    $backupDir = Join-Path $DataDir 'backups'
    New-Item -ItemType Directory -Force $backupDir | Out-Null
    $backup = Join-Path $backupDir ("races-{0}.db" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
    Copy-Item $db $backup -Force
    Write-Log ("已备份 races.db -> {0}" -f $backup)
    Get-ChildItem $backupDir -Filter 'races-*.db' |
        Sort-Object LastWriteTime -Descending |
        Select-Object -Skip 30 |
        Remove-Item -Force -ErrorAction SilentlyContinue
}

$steps = @()
if (-not $SkipFetch) {
    # A 层：各采集器只 merge 自己 source 的条目；失败时在写文件前退出，旧候选保留
    $steps += @(
        @{ Name = '天池';                 Script = 'scripts/fetch_tianchi.py';      Timeout = 300 },
        @{ Name = '讯飞';                 Script = 'scripts/fetch_xfyun.py';        Timeout = 300 },
        @{ Name = 'DataFountain';         Script = 'scripts/fetch_datafountain.py'; Timeout = 300 },
        @{ Name = '百度 AI Studio';       Script = 'scripts/fetch_aistudio.py';     Timeout = 300 },
        @{ Name = 'DoraHacks';            Script = 'scripts/fetch_dora.py';         Timeout = 300 },
        @{ Name = '活动行';               Script = 'scripts/fetch_hdx.py';          Timeout = 300 },
        @{ Name = '官方活动站';           Script = 'scripts/fetch_event_sites.py';  Timeout = 180 },
        @{ Name = '魔搭/和鲸/biendata';   Script = 'scripts/collect_sources.py';    Timeout = 180 },
        @{ Name = 'Luma 日历';            Script = 'scripts/collect_luma.py';       Timeout = 180 }
    )
    foreach ($s in $steps) {
        Invoke-Py -Name $s.Name -ArgList @($s.Script) -TimeoutSec $s.Timeout
    }
    Invoke-Py -Name '联谱线索' -ArgList @('scripts/collect_lianpu.py') -TimeoutSec 180
    Invoke-Py -Name '湾区日历线索' -ArgList @('scripts/collect_wqai.py') -TimeoutSec 120
    Invoke-Py -Name '公众号线索补全' -ArgList @('scripts/enrich_wechat_leads.py', '--limit', '2') -TimeoutSec 180
}

Invoke-Py -Name '核验/去重/入库' -ArgList @('scripts/verify.py') -Fatal -TimeoutSec 1200
Invoke-Py -Name '生成站点' -ArgList @('scripts/build_site.py') -Fatal -TimeoutSec 300

$skipDigest = $SkipDigest -or ($env:SKIP_DIGEST -eq '1')
if (-not $skipDigest) {
    $days = '2'
    if ($env:DIGEST_DAYS) { $days = $env:DIGEST_DAYS }
    Invoke-Py -Name '邮件摘要' -ArgList @('scripts/send_digest.py', '--days', $days)
} else {
    Write-Log 'SKIP_DIGEST=1 / -SkipDigest：跳过邮件摘要'
}

# 摘要
try {
    $races = Get-Content (Join-Path $DataDir 'races.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $ok = @($races | Where-Object { $_.verify_state -eq 'ok' }).Count
    $unknown = @($races | Where-Object { $_.verify_state -eq 'unknown' }).Count
    Write-Log ("完成：全量 {0} 条（活链 {1} / 待确认 {2}）" -f @($races).Count, $ok, $unknown)
} catch {
    Write-Log ("读取 races.json 失败：{0}" -f $_.Exception.Message) 'WARN'
}
# ---- 方案 A：本机是唯一数据源；提交后 push，GitHub Pages 由 pages.yml 部署 ----
$Git = $null
foreach ($candidate in @(
    'D:\comfyui安装\Git\cmd\git.exe',
    'C:\Program Files\Git\cmd\git.exe',
    (Get-Command git -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -ErrorAction SilentlyContinue)
)) {
    if ($candidate -and (Test-Path $candidate)) { $Git = $candidate; break }
}
if (-not $Git) {
    Write-Log '找不到 git.exe，跳过 commit/push；本站仍在本机更新，但公网不会同步' 'ERROR'
} else {
    $GitRoot = Split-Path (Split-Path $Git -Parent) -Parent
    $Ssh = (Join-Path $GitRoot 'usr\bin\ssh.exe') -replace '\\', '/'
    if (-not (Test-Path $Ssh)) { $Ssh = 'C:/Windows/System32/OpenSSH/ssh.exe' }
    $key = 'C:/Users/Administrator/.ssh/id_ed25519_ai_race'
    $sshCmd = '"{0}" -i "{1}" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new' -f $Ssh, $key
    $gitArgs = @(
        '-c', 'user.name=ai-race-radar-bot',
        '-c', 'user.email=bot@users.noreply.github.com',
        '-c', ('core.sshCommand=' + $sshCmd)
    )
    $env:GIT_TERMINAL_PROMPT = '0'
    $branch = (& $Git rev-parse --abbrev-ref HEAD 2>$null | Select-Object -First 1)
    if (-not $branch -or $branch -eq 'HEAD') { $branch = 'main' }
    $branch = ([string]$branch).Trim()

    try {
        Write-Log ("==> git add/commit (branch={0})" -f $branch)
        & $Git @gitArgs add -A 2>&1 | Out-File -FilePath $Log -Append -Encoding utf8
        $changes = & $Git status --porcelain 2>$null
        if (-not $changes) {
            Write-Log '没有文件变化，跳过 commit/push'
        } else {
            $msg = 'chore: daily refresh ' + (Get-Date -Format 'yyyy-MM-dd')
            & $Git @gitArgs commit -m $msg 2>&1 | Out-File -FilePath $Log -Append -Encoding utf8
            if ($LASTEXITCODE -ne 0) { throw ("git commit exit {0}" -f $LASTEXITCODE) }

            Write-Log '==> git fetch/merge/push'
            & $Git fetch origin $branch 2>&1 | Out-File -FilePath $Log -Append -Encoding utf8
            $local = ([string](& $Git rev-parse HEAD 2>$null)).Trim()
            $remote = ([string](& $Git rev-parse ("origin/" + $branch) 2>$null)).Trim()
            if ($remote -and $local -ne $remote) {
                Write-Log '远端有新提交，先合并；数据文件冲突时保留本机版本'
                & $Git @gitArgs pull --no-rebase --no-edit -X ours origin $branch 2>&1 |
                    Out-File -FilePath $Log -Append -Encoding utf8
            }
            $pushOut = & $Git @gitArgs push origin ("HEAD:" + $branch) 2>&1
            $pushOut | Out-File -FilePath $Log -Append -Encoding utf8
            if ($LASTEXITCODE -eq 0) {
                Write-Log '已推送到 GitHub，Pages 将自动部署'
            } else {
                Write-Log ("git push 失败（exit {0}），下次运行会重试" -f $LASTEXITCODE) 'ERROR'
            }
        }
    } catch {
        Write-Log ("git 同步失败：{0}" -f $_.Exception.Message) 'ERROR'
    }
}

Write-Log '================ done ================'
