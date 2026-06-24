#!/usr/bin/env bash
set -euo pipefail
echo "[MEDEK-KYS] Tam okunabilir arsiv aynasi olusturuluyor..."
if ! docker ps --filter "name=akys-api" --filter "status=running" --format "{{.Names}}" | grep -Fxq "akys-api"; then
  echo "akys-api calismiyor. Once tools/start_web_stack.ps1 ile sistemi baslatin." >&2
  exit 1
fi
docker exec -w /app -e PYTHONPATH=/app akys-api python /app/tools/mirror_full_archive.py
echo "[MEDEK-KYS] Arsiv aynalama tamamlandi. Masaustu/Akreditasyon/00_canli_veri/medek_data/kurumlar klasorunu kontrol edin."
