#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${MEDEK_APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$PROJECT_DIR"

get_dotenv_value() {
  local name="$1"
  local default="${2:-}"
  if [ -f .env ] && grep -qE "^${name}=" .env; then
    grep -E "^${name}=" .env | head -n1 | cut -d= -f2- | sed 's/^"//; s/"$//'
  else
    printf '%s' "$default"
  fi
}

AK_ROOT="${AKREDITASYON_ROOT:-$(get_dotenv_value AKREDITASYON_ROOT '')}"
if [ -z "${AK_ROOT:-}" ] || [ "$AK_ROOT" = "./Akreditasyon" ]; then
  if [ -d "$HOME/Desktop" ]; then
    AK_ROOT="$HOME/Desktop/Akreditasyon"
  else
    AK_ROOT="$HOME/Akreditasyon"
  fi
fi

RETENTION_DAYS="${MEDEK_BACKUP_RETENTION_DAYS:-30}"
STAMP="$(date +%Y-%m-%d_%H-%M-%S)"
BACKUP_ROOT="$AK_ROOT/01_zaman_damgali_yedekler"
TARGET="$BACKUP_ROOT/$STAMP"
LIVE_DATA="$AK_ROOT/00_canli_veri/medek_data"

mkdir -p "$TARGET"

if [ -d "$LIVE_DATA" ]; then
  tar -czf "$TARGET/medek_data_$STAMP.tar.gz" -C "$LIVE_DATA" .
fi

POSTGRES_USER="$(get_dotenv_value POSTGRES_USER medek)"
POSTGRES_DB="$(get_dotenv_value POSTGRES_DB medek)"
POSTGRES_PASSWORD="$(get_dotenv_value POSTGRES_PASSWORD '')"
DUMP_PATH="$TARGET/postgres_${POSTGRES_DB}_$STAMP.sql"
DB_DUMP_STATUS="created"
if ! docker exec -e "PGPASSWORD=$POSTGRES_PASSWORD" akys-postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$DUMP_PATH" 2> "$TARGET/postgres_dump_error.txt"; then
  DB_DUMP_STATUS="failed"
fi

cat > "$TARGET/manifest.json" <<EOF
{
  "created_at": "$STAMP",
  "akreditasyon_root": "$AK_ROOT",
  "project_root": "$PROJECT_DIR",
  "live_data": "$LIVE_DATA",
  "postgres_database": "$POSTGRES_DB",
  "postgres_user": "$POSTGRES_USER",
  "postgres_dump": "$DB_DUMP_STATUS"
}
EOF

find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +"$RETENTION_DAYS" -exec rm -rf {} +

echo "Zaman damgalı yedek oluşturuldu: $TARGET"
