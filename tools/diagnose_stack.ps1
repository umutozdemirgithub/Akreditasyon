$ErrorActionPreference = "Continue"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$composeFiles = @("-f", "docker-compose.web.yml")
if (Test-Path "docker-compose.queue.yml") { $composeFiles += @("-f", "docker-compose.queue.yml") }
if (Test-Path "docker-compose.https.yml") { $composeFiles += @("-f", "docker-compose.https.yml") }

Write-Host "== Docker Compose PS ==" -ForegroundColor Cyan
docker compose --env-file .env @composeFiles ps

Write-Host ""
Write-Host "== API inspect ==" -ForegroundColor Cyan
docker inspect -f 'Status={{.State.Status}} Health={{if .State.Health}}{{.State.Health.Status}}{{end}} ExitCode={{.State.ExitCode}}' akys-api

Write-Host ""
Write-Host "== API logs, last 220 lines ==" -ForegroundColor Cyan
docker logs --tail=220 akys-api

Write-Host ""
Write-Host "== Postgres logs, last 120 lines ==" -ForegroundColor Cyan
docker logs --tail=120 akys-postgres
