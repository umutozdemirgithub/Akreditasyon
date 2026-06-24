$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

function Convert-ToComposePath([string]$PathValue) {
    return ($PathValue -replace '\\','/')
}

function Get-DotEnvValue([string]$Name) {
    if (-not (Test-Path ".env")) { return $null }
    $line = Get-Content ".env" | Where-Object { $_ -match "^$([regex]::Escape($Name))=" } | Select-Object -First 1
    if (-not $line) { return $null }
    return $line.Substring($Name.Length + 1).Trim().Trim('"')
}

function Set-DotEnvValue([string]$Name, [string]$Value) {
    $escaped = [regex]::Escape($Name)
    $newLine = "$Name=$Value"
    if (-not (Test-Path ".env")) {
        Set-Content -Path ".env" -Value $newLine -Encoding UTF8
        return
    }
    $lines = Get-Content ".env"
    $found = $false
    $updated = foreach ($line in $lines) {
        if ($line -match "^$escaped=") {
            $found = $true
            $newLine
        } else {
            $line
        }
    }
    if (-not $found) { $updated += $newLine }
    Set-Content -Path ".env" -Value $updated -Encoding UTF8
}

function New-HexSecret([int]$Bytes = 48) {
    $buffer = New-Object byte[] $Bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($buffer)
    return ([BitConverter]::ToString($buffer) -replace '-', '').ToLowerInvariant()
}

function New-StrongPassword() {
    return "Akys_" + (New-HexSecret 18) + "!Aa1"
}

function Is-PlaceholderOrWeak([string]$Value) {
    if ([string]::IsNullOrWhiteSpace($Value)) { return $true }
    $v = $Value.Trim()
    if ($v -match '^CHANGE_ME') { return $true }
    if ($v -in @('admin', 'admin123', 'password', 'change-this-initial-admin-password')) { return $true }
    return $false
}

function Ensure-RequiredDotEnv() {
    $apiSecret = Get-DotEnvValue "MEDEK_API_SECRET"
    if ((Is-PlaceholderOrWeak $apiSecret) -or ($apiSecret.Length -lt 48)) {
        Set-DotEnvValue "MEDEK_API_SECRET" (New-HexSecret 48)
        Write-Host "MEDEK_API_SECRET otomatik üretildi." -ForegroundColor Yellow
    }

    $bootstrapPassword = Get-DotEnvValue "MEDEK_BOOTSTRAP_ADMIN_PASSWORD"
    if (Is-PlaceholderOrWeak $bootstrapPassword) {
        $newPassword = New-StrongPassword
        Set-DotEnvValue "MEDEK_BOOTSTRAP_ADMIN_PASSWORD" $newPassword
        Write-Host "MEDEK_BOOTSTRAP_ADMIN_PASSWORD otomatik üretildi." -ForegroundColor Yellow
        Write-Host "İlk admin şifresi: $newPassword" -ForegroundColor Yellow
        Write-Host "İlk girişten sonra değiştirin." -ForegroundColor Yellow
    }

    $pgPassword = Get-DotEnvValue "POSTGRES_PASSWORD"
    if (Is-PlaceholderOrWeak $pgPassword) {
        Set-DotEnvValue "POSTGRES_PASSWORD" (New-StrongPassword)
        Write-Host "POSTGRES_PASSWORD otomatik üretildi." -ForegroundColor Yellow
    }

    if ([string]::IsNullOrWhiteSpace((Get-DotEnvValue "MEDEK_ENV"))) { Set-DotEnvValue "MEDEK_ENV" "production" }
    if ([string]::IsNullOrWhiteSpace((Get-DotEnvValue "MEDEK_DB_BACKEND"))) { Set-DotEnvValue "MEDEK_DB_BACKEND" "postgresql" }
    if ([string]::IsNullOrWhiteSpace((Get-DotEnvValue "POSTGRES_DB"))) { Set-DotEnvValue "POSTGRES_DB" "medek" }
    if ([string]::IsNullOrWhiteSpace((Get-DotEnvValue "POSTGRES_USER"))) { Set-DotEnvValue "POSTGRES_USER" "medek" }

    $generalLimit = Get-DotEnvValue "MEDEK_RATE_LIMIT_GENERAL_PER_MINUTE"
    if ([string]::IsNullOrWhiteSpace($generalLimit) -or ([int]$generalLimit -lt 300)) { Set-DotEnvValue "MEDEK_RATE_LIMIT_GENERAL_PER_MINUTE" "300" }
    $exportLimit = Get-DotEnvValue "MEDEK_RATE_LIMIT_EXPORT_PER_MINUTE"
    if ([string]::IsNullOrWhiteSpace($exportLimit) -or ([int]$exportLimit -lt 30)) { Set-DotEnvValue "MEDEK_RATE_LIMIT_EXPORT_PER_MINUTE" "30" }
}

function Ensure-AkreditasyonStorage([string]$AkRoot) {
    $folders = @(
        "00_canli_veri",
        "00_canli_veri\postgresql",
        "00_canli_veri\medek_data",
        "00_canli_veri\medek_data\kanitlar",
        "00_canli_veri\medek_data\exports",
        "00_canli_veri\medek_data\backups",
        "01_zaman_damgali_yedekler",
        "02_dis_aktarimlar",
        "03_loglar",
        "04_kurulum",
        "99_arsiv"
    )

    foreach ($folder in $folders) {
        $target = Join-Path $AkRoot $folder
        if (-not (Test-Path $target)) {
            New-Item -ItemType Directory -Path $target -Force | Out-Null
        }
    }

    $stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $marker = Join-Path $AkRoot "04_kurulum\baslatma_$stamp.txt"
    @(
        "AKYS / Akreditasyon storage initialized",
        "Timestamp: $stamp",
        "Root: $AkRoot",
        "Project: $root"
    ) | Set-Content -Path $marker -Encoding UTF8
}

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.web.example") {
        Copy-Item ".env.web.example" ".env"
        Write-Host "Created .env from .env.web.example." -ForegroundColor Yellow
    } else {
        throw ".env file is missing and .env.web.example was not found."
    }
}

Ensure-RequiredDotEnv

$existingAkRoot = Get-DotEnvValue "AKREDITASYON_ROOT"
if ([string]::IsNullOrWhiteSpace($existingAkRoot) -or $existingAkRoot -eq "./Akreditasyon") {
    $desktop = [Environment]::GetFolderPath("Desktop")
    if ([string]::IsNullOrWhiteSpace($desktop)) {
        $desktop = Join-Path $HOME "Desktop"
    }
    $akRoot = Join-Path $desktop "Akreditasyon"
    Set-DotEnvValue "AKREDITASYON_ROOT" (Convert-ToComposePath $akRoot)
} else {
    $akRoot = $existingAkRoot -replace '/', [System.IO.Path]::DirectorySeparatorChar
}

Ensure-AkreditasyonStorage $akRoot

Write-Host ""
Write-Host "Akreditasyon ana klasörü hazır:" -ForegroundColor Cyan
Write-Host "  $akRoot"
Write-Host ""

# Legacy/local klasör de dursun; eski araçlar doğrudan proje içini ararsa hata almasın.
if (-not (Test-Path "medek_data")) { New-Item -ItemType Directory -Path "medek_data" | Out-Null }
if (-not (Test-Path "medek_data/kanitlar")) { New-Item -ItemType Directory -Path "medek_data/kanitlar" | Out-Null }

$composeFiles = @("-f", "docker-compose.web.yml")
if (Test-Path "docker-compose.queue.yml") { $composeFiles += @("-f", "docker-compose.queue.yml") }
if (Test-Path "docker-compose.https.yml") { $composeFiles += @("-f", "docker-compose.https.yml") }

docker compose --env-file .env @composeFiles up --build -d
docker compose --env-file .env @composeFiles ps

$apiState = docker inspect -f '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' akys-api 2>$null
if ($LASTEXITCODE -eq 0 -and ($apiState -notmatch 'running healthy')) {
    Write-Host ""
    Write-Host "API sağlıklı başlamadı. Son loglar:" -ForegroundColor Red
    docker logs --tail=160 akys-api
    throw "akys-api healthy değil: $apiState"
}

Write-Host ""
Write-Host "AKYS web stack started." -ForegroundColor Green
Write-Host "Open: http://SERVER_IP:8080 or configured MEDEK_WEB_PORT"
Write-Host "Veriler masaüstündeki Akreditasyon klasörüne yazılır."
