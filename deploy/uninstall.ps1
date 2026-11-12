# AI 赛事雷达 · 卸载 Windows 计划任务与防火墙规则（保留数据与站点）
#   powershell -ExecutionPolicy Bypass -File deploy\uninstall.ps1
[CmdletBinding()]
param(
    [int]$Port = 8080
)

$ErrorActionPreference = 'Continue'

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw '需要管理员权限。'
}

foreach ($name in @('AI Race Radar - Web', 'AI Race Radar - Daily')) {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($task) {
        Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $name -Confirm:$false
        Write-Host ("已删除计划任务：{0}" -f $name)
    } else {
        Write-Host ("未注册：{0}" -f $name)
    }
}

$ruleName = 'AI Race Radar (TCP {0})' -f $Port
$rule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($rule) {
    Remove-NetFirewallRule -DisplayName $ruleName
    Write-Host ("已删除防火墙规则：{0}" -f $ruleName)
}

Write-Host '完成。data\、site\、.env 均保留，可随时重新运行 deploy\install.ps1。'
