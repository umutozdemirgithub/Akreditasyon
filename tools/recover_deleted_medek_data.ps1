$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

function Read-DotEnvValue($name) {
    if (-not (Test-Path ".env")) { return "" }
    $line = Get-Content ".env" | Where-Object { $_ -match "^\s*$name\s*=" } | Select-Object -Last 1
    if (-not $line) { return "" }
    return (($line -split "=", 2)[1]).Trim().Trim('"').Trim("'")
}

if (-not (Test-Path ".env")) {
    throw ".env bulunamadı. Önce .env.web.example dosyasını .env olarak kopyalayın ve değerleri düzenleyin."
}

$bootstrap = Read-DotEnvValue "MEDEK_BOOTSTRAP_ADMIN_PASSWORD"
$legacy = Read-DotEnvValue "MEDEK_ADMIN_PASSWORD"
$password = if ($bootstrap) { $bootstrap } else { $legacy }
$weak = @("admin", "admin123", "password", "123456", "12345678", "change-this-initial-admin-password")

if (-not $password -or $password.Length -lt 10 -or ($weak -contains $password.ToLower())) {
    throw "Yeni/veritabanı silinmiş kurulum için güçlü MEDEK_BOOTSTRAP_ADMIN_PASSWORD gerekli. .env içine örnek: MEDEK_BOOTSTRAP_ADMIN_PASSWORD=MedekAdmin_2026!Guclu"
}

if (-not (Test-Path "medek_data")) { New-Item -ItemType Directory -Path "medek_data" | Out-Null }
if (-not (Test-Path "medek_data\kanitlar")) { New-Item -ItemType Directory -Path "medek_data\kanitlar" | Out-Null }
if (-not (Test-Path "medek_data\exports")) { New-Item -ItemType Directory -Path "medek_data\exports" | Out-Null }
if (-not (Test-Path "medek_data\backups")) { New-Item -ItemType Directory -Path "medek_data\backups" | Out-Null }

Write-Host "medek_data klasörleri hazırlandı. Docker stack yeniden başlatılıyor..." -ForegroundColor Cyan
docker compose --env-file .env -f docker-compose.web.yml down
docker compose --env-file .env -f docker-compose.web.yml up -d --build web
docker compose --env-file .env -f docker-compose.web.yml ps
