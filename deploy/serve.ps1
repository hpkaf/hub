# AI 赛事雷达 · Windows 常驻静态服务（带崩溃自动重启）
#
# 由计划任务「AI Race Radar - Web」在开机时启动，也可手动运行：
#   powershell -ExecutionPolicy Bypass -File deploy\serve.ps1
#   $env:PORT=8090; powershell ... -File deploy\serve.ps1
#
# 只把 site\ 目录暴露出去；项目根目录（含 .env、data\）不在 HTTP 根下。
[CmdletBinding()]
param(
    [int]$Port = 0,
    [string]$Bind = '',
    [string]$Python
)

$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if ($Port -le 0) {
    if ($env:PORT) { $Port = [int]$env:PORT } else { $Port = 8080 }
}
if (-not $Bind) {
    if ($env:BIND) { $Bind = $env:BIND } else { $Bind = '0.0.0.0' }
}

$DataDir = Join-Path $Root 'data'
$Log = Join-Path $DataDir 'serve.log'
New-Item -ItemType Directory -Force $DataDir | Out-Null

function Write-ServeLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -Path $Log -Value $line -Encoding utf8
    Write-Host $line
}

if (Test-Path $Log) {
    if ((Get-Item $Log).Length -gt 5MB) {
        $bytes = [System.IO.File]::ReadAllBytes($Log)
        $tail = New-Object byte[] (1MB)
        [Array]::Copy($bytes, $bytes.Length - $tail.Length, $tail, 0, $tail.Length)
        [System.IO.File]::WriteAllBytes($Log, $tail)
    }
}

if (-not $Python) {
    $pyFile = Join-Path $PSScriptRoot 'python-path.txt'
    if (Test-Path $pyFile) { $Python = (Get-Content $pyFile -Raw -Encoding UTF8).Trim() }
}
if (-not $Python) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $Python = $cmd.Source }
}
if (-not $Python -or -not (Test-Path $Python)) {
    Write-ServeLog '找不到 Python，无法启动静态服务'
    exit 2
}

$site = Join-Path $Root 'site'
$serveScript = Join-Path $Root 'scripts\serve_site.py'
if (-not (Test-Path (Join-Path $site 'index.html'))) {
    Write-ServeLog 'site\index.html 不存在，先跑一次 deploy\run_daily.ps1'
}
if (-not (Test-Path $serveScript)) {
    Write-ServeLog 'scripts\serve_site.py 不存在，回退到 python -m http.server'
}

Write-ServeLog ("serve.ps1 启动：python={0} bind={1} port={2} root={3}" -f $Python, $Bind, $Port, $site)

while ($true) {
    if (Test-Path $Log) {
        if ((Get-Item $Log).Length -gt 5MB) {
            $bytes = [System.IO.File]::ReadAllBytes($Log)
            $tail = New-Object byte[] (1MB)
            [Array]::Copy($bytes, $bytes.Length - $tail.Length, $tail, 0, $tail.Length)
            [System.IO.File]::WriteAllBytes($Log, $tail)
        }
    }
    Write-ServeLog ("启动 http.server（{0}:{1}）" -f $Bind, $Port)
    if (Test-Path $serveScript) {
        & $Python $serveScript --port $Port --bind $Bind --directory $site 2>&1 | ForEach-Object {
            $line = [string]$_
            if ($line) {
                Add-Content -Path $Log -Value ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $line) -Encoding utf8
                Write-Host $line
            }
        }
    } else {
        & $Python -m http.server $Port --bind $Bind --directory $site 2>&1 | ForEach-Object {
            $line = [string]$_
            if ($line) {
                Add-Content -Path $Log -Value ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $line) -Encoding utf8
                Write-Host $line
            }
        }
    }
    $code = $LASTEXITCODE
    Write-ServeLog ("http.server 退出（exit={0}），5 秒后重启" -f $code)
    Start-Sleep -Seconds 5
}
