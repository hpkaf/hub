# AI 赛事雷达 · 运行状态速查
#   powershell -ExecutionPolicy Bypass -File deploy\status.ps1
[CmdletBinding()]
param()

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Section {
    param([string]$Title)
    Write-Host ''
    Write-Host ("== {0} ==" -f $Title) -ForegroundColor Cyan
}

Section '计划任务'
foreach ($name in @('AI Race Radar - Daily', 'AI Race Radar - Web')) {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Host ("  {0}：未注册" -f $name) -ForegroundColor Yellow
        continue
    }
    $info = Get-ScheduledTaskInfo -TaskName $name
    $result = $info.LastTaskResult
    if ($result -eq 0) { $resultText = '0 (成功)' }
    elseif ($result -eq 267009) { $resultText = '267009 (运行中)' }
    elseif ($result -eq 267014) { $resultText = '267014 (被终止)' }
    else { $resultText = [string]$result }
    Write-Host ("  {0}" -f $name)
    Write-Host ("    状态={0}  上次运行={1}  结果={2}  下次运行={3}" -f `
        $task.State, $info.LastRunTime, $resultText, $info.NextRunTime)
}

Section '站点'
$port = 8080
$envFile = Join-Path $Root '.env'
if (Test-Path $envFile) {
    $siteLine = Get-Content $envFile -Encoding UTF8 | Where-Object { $_ -match '^SITE_URL=' } | Select-Object -First 1
    if ($siteLine) { Write-Host ("  SITE_URL={0}" -f $siteLine.Substring(9)) }
}
$conn = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1
if ($conn) {
    Write-Host ("  端口 {0} 监听中（PID {1}）" -f $port, $conn.OwningProcess)
} else {
    Write-Host ("  端口 {0} 未监听" -f $port) -ForegroundColor Yellow
}
foreach ($url in @("http://127.0.0.1:{0}/" -f $port, "http://127.0.0.1:{0}/api/events.json" -f $port)) {
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
        Write-Host ("  {0} -> HTTP {1} ({2:N1} KB)" -f $url, $r.StatusCode, ($r.RawContentLength / 1KB))
    } catch {
        Write-Host ("  {0} -> 失败：{1}" -f $url, $_.Exception.Message) -ForegroundColor Yellow
    }
}

Section '数据'
$racesFile = Join-Path $Root 'data\races.json'
if (Test-Path $racesFile) {
    $races = Get-Content $racesFile -Raw -Encoding UTF8 | ConvertFrom-Json
    $total = @($races).Count
    $ok = @($races | Where-Object { $_.verify_state -eq 'ok' }).Count
    $unknown = @($races | Where-Object { $_.verify_state -eq 'unknown' }).Count
    Write-Host ("  races.json：{0} 条（活链 {1} / 待确认 {2}）" -f $total, $ok, $unknown)
}
$apiFile = Join-Path $Root 'site\api\events.json'
if (Test-Path $apiFile) {
    $api = Get-Content $apiFile -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Host ("  api/events.json：{0} 条，updated={1}" -f $api.count, $api.updated)
}
$db = Join-Path $Root 'data\races.db'
if (Test-Path $db) {
    Write-Host ("  races.db：{0:N0} 字节，修改于 {1}" -f (Get-Item $db).Length, (Get-Item $db).LastWriteTime)
}

Section '最近日志（data\run.log）'
$runLog = Join-Path $Root 'data\run.log'
if (Test-Path $runLog) {
    Get-Content $runLog -Tail 15 -Encoding UTF8 | ForEach-Object { Write-Host ("  " + $_) }
} else {
    Write-Host '  暂无 run.log'
}

Section '最近日志（data\serve.log）'
$serveLog = Join-Path $Root 'data\serve.log'
if (Test-Path $serveLog) {
    Get-Content $serveLog -Tail 10 -Encoding UTF8 | ForEach-Object { Write-Host ("  " + $_) }
} else {
    Write-Host '  暂无 serve.log'
}
