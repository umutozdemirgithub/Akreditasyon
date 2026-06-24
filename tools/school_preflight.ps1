Param(
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"

function Write-Check($Name, $Ok, $Detail = "") {
    $status = if ($Ok) { "PASS" } else { "FAIL" }
    $color = if ($Ok) { "Green" } else { "Red" }
    Write-Host "[$status] $Name $Detail" -ForegroundColor $color
}

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

Write-Host "AKYS school server preflight" -ForegroundColor Cyan
Write-Host "Project root: $root"

$docker = Get-Command docker -ErrorAction SilentlyContinue
Write-Check "Docker CLI" ([bool]$docker) ($docker.Source)

if ($docker) {
    try {
        $version = docker --version
        Write-Check "Docker version" $true $version
    } catch {
        Write-Check "Docker version" $false $_.Exception.Message
    }

    try {
        $compose = docker compose version
        Write-Check "Docker Compose v2" $true $compose
    } catch {
        Write-Check "Docker Compose v2" $false $_.Exception.Message
    }
}

Write-Check "docker-compose.web.yml" (Test-Path "docker-compose.web.yml")
Write-Check "Dockerfile.api" (Test-Path "Dockerfile.api")
Write-Check "frontend/Dockerfile" (Test-Path "frontend/Dockerfile")
Write-Check ".env file" (Test-Path ".env") "Copy .env.web.example to .env if missing"
Write-Check "medek_data directory" (Test-Path "medek_data")
Write-Check "SQLite database" (Test-Path "medek_data/medek_kys_v7_9.sqlite3")

$portBusy = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
Write-Check "Port $Port available" (-not $portBusy) ($(if ($portBusy) { "Port is already in use" } else { "" }))

Write-Host ""
Write-Host "Next command:" -ForegroundColor Cyan
Write-Host "powershell -ExecutionPolicy Bypass -File tools/start_web_stack.ps1"

