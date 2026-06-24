#!/usr/bin/env bash
set -euo pipefail
echo "Kurumsal klasör migrasyonu başlatılıyor..."
docker exec -it akys-api python /app/tools/migrate_to_org_storage.py
