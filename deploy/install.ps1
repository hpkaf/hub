# AI 赛事雷达 · Windows 24×7 安装脚本
#
# 做了什么：
#   1. 记录 Python 绝对路径到 deploy\python-path.txt（计划任务在 SYSTEM 下没有用户 PATH）
#   2. 没有 .env 时从 .env.example 生成，并把 SITE_URL 指向本机局域网地址
#   3. 注册两个计划任务（SYSTEM 账户，开机即生效，不依赖登录）：
#        AI Race Radar - Daily  每天 08:00 跑流水线
#        AI Race Radar - Web    开机启动静态服务，崩溃自动重启
#   4. 放行防火墙 8080/TCP（仅专用/域网络），并立即启动 Web 任务
#
# 用法（管理员 PowerShell）：
#   powershell -ExecutionPolicy Bypass -File deploy\install.ps1
#   powershell -ExecutionPolicy Bypass -File deploy\install.ps1 -Port 8090
[CmdletBinding()]
param(
    [int]$Port = 8080,
    [string]$Bind = '0.0.0.0',
    [string]$Python
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Write-Step {
    param([string]$Message)
    Write-Host ("==> {0}" -f $Message) -ForegroundColor Cyan
}

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw '需要管理员权限：请用「以管理员身份运行」的 PowerShell 执行本脚本。'
}

Write-Step '定位 Python'
if (-not $Python) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $Python = $cmd.Source }
}
if (-not $Python -or -not (Test-Path $Python)) {
    throw '找不到 python.exe，请用 -Python "C:\...\python.exe" 指定。'
}
$Python = (Resolve-Path $Python).Path
Write-Host ("    {0}" -f $Python)
$pythonInfo = & $Python -c "import sys; print(sys.version.split()[0])" 2>&1
Write-Host ("    Python {0}" -f $pythonInfo)
Set-Content -Path (Join-Path $PSScriptRoot 'python-path.txt') -Value $Python -Encoding utf8

Write-Step '检查项目依赖（PyYAML）'
$yamlCheck = & $Python -c "import yaml; print(yaml.__version__)" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host '    系统 Python 没有 PyYAML，安装到项目内 .pylibs ...'
    & $Python -m pip install --target .pylibs --upgrade pyyaml
    if ($LASTEXITCODE -ne 0) { throw 'PyYAML 安装失败，请检查 pip / 网络。' }
} else {
    Write-Host ("    PyYAML {0}" -f $yamlCheck)
}

Write-Step '检查 .env'
$envFile = Join-Path $Root '.env'
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $Root '.env.example') $envFile
    $lanIp = $null
    try {
        $lanIp = (Get-NetIPConfiguration |
            Where-Object { $_.IPv4DefaultGateway -ne $null -and $_.NetAdapter.Status -eq 'Up' } |
            Select-Object -First 1).IPv4Address.IPAddress
    } catch { }
    if (-not $lanIp) { $lanIp = '127.0.0.1' }
    $siteUrl = "http://{0}:{1}" -f $lanIp, $Port
    $text = [System.IO.File]::ReadAllText($envFile, [System.Text.Encoding]::UTF8)
    $text = $text -replace '(?m)^SITE_URL=.*$', ("SITE_URL=" + $siteUrl)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($envFile, $text, $utf8NoBom)
    Write-Host ("    已生成 .env，SITE_URL={0}" -f $siteUrl)
} else {
    Write-Host '    .env 已存在，保持不动'
}

Write-Step '注册计划任务'
$psExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
if (-not (Test-Path $psExe)) { $psExe = 'powershell.exe' }

$dailyName = 'AI Race Radar - Daily'
$webName = 'AI Race Radar - Web'

$dailyArgs = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}"' -f (Join-Path $PSScriptRoot 'run_daily.ps1')
$webArgs = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}"' -f (Join-Path $PSScriptRoot 'serve.ps1')

$taskPrincipal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest

$dailyTrigger = New-ScheduledTaskTrigger -Daily -At '08:00'
$dailySettings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 10) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries
$dailyAction = New-ScheduledTaskAction -Execute $psExe -Argument $dailyArgs -WorkingDirectory $Root
Register-ScheduledTask -TaskName $dailyName -Action $dailyAction -Trigger $dailyTrigger `
    -Settings $dailySettings -Principal $taskPrincipal -Force `
    -Description 'AI 赛事雷达：每天 08:00 抓取→核验→建站（SKIP_DIGEST 见 .env）' | Out-Null
Write-Host ("    {0} 已注册（每天 08:00）" -f $dailyName)

$webTrigger = New-ScheduledTaskTrigger -AtStartup
$webSettings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries
$webAction = New-ScheduledTaskAction -Execute $psExe -Argument $webArgs -WorkingDirectory $Root
Register-ScheduledTask -TaskName $webName -Action $webAction -Trigger $webTrigger `
    -Settings $webSettings -Principal $taskPrincipal -Force `
    -Description 'AI 赛事雷达：常驻静态站点服务（site/）' | Out-Null
Write-Host ("    {0} 已注册（开机启动）" -f $webName)

Write-Step '配置防火墙'
$ruleName = 'AI Race Radar (TCP {0})' -f $Port
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-not $existingRule) {
    # 只允许同网段访问：即使当前网络被识别为「公用」，也不会对整个互联网开放
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow `
        -Protocol TCP -LocalPort $Port -Profile Any -RemoteAddress LocalSubnet | Out-Null
    Write-Host ("    已放行 TCP {0}（仅限本地子网）" -f $Port)
} else {
    Write-Host ("    防火墙规则已存在：{0}" -f $ruleName)
}

$netProfile = Get-NetConnectionProfile -ErrorAction SilentlyContinue | Select-Object -First 1
if ($netProfile -and $netProfile.NetworkCategory -eq 'Public') {
    Write-Host '    当前网络被识别为「公用」；防火墙规则已按 LocalSubnet 放行，同网段设备可访问。' -ForegroundColor Yellow
    Write-Host '    若仍打不开，可把网络改为「专用」，或检查路由器是否开启了 AP 隔离。' -ForegroundColor Yellow
}

Write-Step '启动 Web 任务并等待站点'
Start-ScheduledTask -TaskName $webName
$ok = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $resp = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/" -f $Port) -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) { $ok = $true; break }
    } catch { }
}
if ($ok) {
    Write-Host ("    站点已就绪：http://127.0.0.1:{0}/" -f $Port) -ForegroundColor Green
} else {
    Write-Host '    站点未在 10 秒内就绪，查看 data\serve.log' -ForegroundColor Yellow
}

Write-Host ''
Write-Host '安装完成。' -ForegroundColor Green
Write-Host ("  本机访问：http://127.0.0.1:{0}/" -f $Port)
Write-Host ("  局域网访问：http://<本机IP>:{0}/（IP 见 .env 的 SITE_URL）" -f $Port)
Write-Host '  手动跑一次：powershell -ExecutionPolicy Bypass -File deploy\run_daily.ps1'
Write-Host '  查看状态：  powershell -ExecutionPolicy Bypass -File deploy\status.ps1'
