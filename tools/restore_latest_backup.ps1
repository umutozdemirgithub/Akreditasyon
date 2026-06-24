param(
    [string]$ProjectDir = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),
    [string]$BackupDir = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$project = Resolve-Path $ProjectDir
if ([string]::IsNullOrWhiteSpace($BackupDir)) {
    $BackupDir = Join-Path $project "medek_data\backups"
}
if (!(Test-Path $BackupDir)) {
    throw "Backup directory not found: $BackupDir"
}
$latest = Get-ChildItem $BackupDir -Filter "medek_data_*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (!$latest) {
    throw "No medek_data_*.zip file found in $BackupDir"
}
$targetData = Join-Path $project "medek_data"
if ((Test-Path $targetData) -and !$Force) {
    throw "medek_data exists. Re-run with -Force after stopping the Docker stack and taking a copy."
}
if (Test-Path $targetData) {
    Rename-Item $targetData ("medek_data_before_restore_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
}
Expand-Archive -Path $latest.FullName -DestinationPath $project -Force
Write-Host "Restored latest backup: $($latest.FullName)"
