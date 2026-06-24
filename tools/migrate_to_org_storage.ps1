$ErrorActionPreference = "Stop"
Write-Host "Kurumsal klasör migrasyonu başlatılıyor..."
docker exec -it akys-api python /app/tools/migrate_to_org_storage.py
