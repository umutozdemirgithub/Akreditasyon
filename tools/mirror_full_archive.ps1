$ErrorActionPreference = "Stop"
Write-Host "[MEDEK-KYS] Tam okunabilir arsiv aynasi olusturuluyor..."

$container = docker ps --filter "name=akys-api" --filter "status=running" --format "{{.Names}}"
if ($container -notcontains "akys-api") {
    throw "akys-api calismiyor. Once tools/start_web_stack.ps1 ile sistemi baslatin."
}

docker exec -w /app -e PYTHONPATH=/app akys-api python /app/tools/mirror_full_archive.py
if ($LASTEXITCODE -ne 0) {
    throw "Arsiv aynalama basarisiz oldu. Ustteki hata mesajini kontrol edin."
}

Write-Host "[MEDEK-KYS] Arsiv aynalama tamamlandi. Masaustu/Akreditasyon/00_canli_veri/medek_data/kurumlar klasorunu kontrol edin."
