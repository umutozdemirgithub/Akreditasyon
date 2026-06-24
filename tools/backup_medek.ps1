Param(
    [string]$AkreditasyonRoot = "",
    [int]$RetentionDays = 30
)

$ErrorActionPreference = "Stop"

$project = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $project

function Get-DotEnvValue([string]$Name, [string]$Default = "") {
    if (-not (Test-Path ".env")) { return $Default }
    $line = Get-Content ".env" | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -First 1
    if (-not $line) { return $Default }
    $value = $line.Substring($Name.Length + 1).Trim().Trim('"')
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return $value
}

if ([string]::IsNullOrWhiteSpace($AkreditasyonRoot)) {
    $AkreditasyonRoot = Get-DotEnvValue "AKREDITASYON_ROOT" ""
}
if ([string]::IsNullOrWhiteSpace($AkreditasyonRoot) -or $AkreditasyonRoot -eq "./Akreditasyon") {
    $desktop = [Environment]::GetFolderPath("Desktop")
    if ([string]::IsNullOrWhiteSpace($desktop)) { $desktop = Join-Path $HOME "Desktop" }
    $AkreditasyonRoot = Join-Path $desktop "Akreditasyon"
}
$AkreditasyonRoot = $AkreditasyonRoot -replace '/', [System.IO.Path]::DirectorySeparatorChar

$stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$backupRoot = Join-Path $AkreditasyonRoot "01_zaman_damgali_yedekler"
$target = Join-Path $backupRoot $stamp
New-Item -ItemType Directory -Path $target -Force | Out-Null

$liveData = Join-Path $AkreditasyonRoot "00_canli_veri\medek_data"
if (Test-Path $liveData) {
    Compress-Archive -Path $liveData -DestinationPath (Join-Path $target "medek_data_$stamp.zip") -Force
}

$postgresUser = Get-DotEnvValue "POSTGRES_USER" "medek"
$postgresDb = Get-DotEnvValue "POSTGRES_DB" "medek"
$postgresPass = Get-DotEnvValue "POSTGRES_PASSWORD" ""
$dumpPath = Join-Path $target "postgres_${postgresDb}_$stamp.sql"

try {
    docker exec -e "PGPASSWORD=$postgresPass" akys-postgres pg_dump -U $postgresUser -d $postgresDb | Set-Content -Path $dumpPath -Encoding UTF8
    $dbDumpStatus = "created"
} catch {
    $dbDumpStatus = "failed: $($_.Exception.Message)"
    "PostgreSQL dump alınamadı: $($_.Exception.Message)" | Set-Content -Path (Join-Path $target "postgres_dump_error.txt") -Encoding UTF8
}

$manifest = [ordered]@{
    created_at = $stamp
    akreditasyon_root = $AkreditasyonRoot
    project_root = $project
    live_data = $liveData
    postgres_database = $postgresDb
    postgres_user = $postgresUser
    postgres_dump = $dbDumpStatus
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $target "manifest.json") -Encoding UTF8

$threshold = (Get-Date).AddDays(-1 * $RetentionDays)
Get-ChildItem -Path $backupRoot -Directory |
    Where-Object { $_.LastWriteTime -lt $threshold } |
    Remove-Item -Recurse -Force

Write-Host "Zaman damgalı yedek oluşturuldu: $target" -ForegroundColor Green
