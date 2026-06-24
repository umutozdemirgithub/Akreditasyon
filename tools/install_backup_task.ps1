param(
    [string]$ProjectDir = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),
    [string]$TaskName = "AKYS-Daily-Backup",
    [string]$RunAt = "02:30"
)

$ErrorActionPreference = "Stop"
$project = Resolve-Path $ProjectDir
$script = Join-Path $project "tools\backup_medek.ps1"
if (!(Test-Path $script)) {
    throw "Backup script not found: $script"
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -BackupDir `"$(Join-Path $project 'medek_data\backups')`""
$trigger = New-ScheduledTaskTrigger -Daily -At $RunAt
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Daily AKYS medek_data backup" -Force | Out-Null
Write-Host "Scheduled backup task installed: $TaskName at $RunAt"
Write-Host "Project: $project"
