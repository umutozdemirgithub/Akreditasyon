#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

get_env() {
  local name="$1"
  if [[ ! -f .env ]]; then return 0; fi
  grep -E "^${name}=" .env | head -n1 | cut -d= -f2- | sed 's/^"//;s/"$//'
}

set_env() {
  local name="$1" value="$2"
  if [[ ! -f .env ]]; then echo "${name}=${value}" > .env; return; fi
  if grep -qE "^${name}=" .env; then
    python - "$name" "$value" <<'PY'
from pathlib import Path
import sys
name, value = sys.argv[1], sys.argv[2]
p = Path('.env')
lines = p.read_text(encoding='utf-8').splitlines()
out = [f'{name}={value}' if line.startswith(f'{name}=') else line for line in lines]
p.write_text('\n'.join(out) + '\n', encoding='utf-8')
PY
  else
    echo "${name}=${value}" >> .env
  fi
}

hex_secret() {
  local bytes="${1:-48}"
  python - "$bytes" <<'PY'
import secrets, sys
print(secrets.token_hex(int(sys.argv[1])))
PY
}

strong_password() {
  echo "Akys_$(hex_secret 18)!Aa1"
}

is_weak() {
  local value="${1:-}"
  [[ -z "$value" ]] && return 0
  [[ "$value" == CHANGE_ME* ]] && return 0
  case "$value" in admin|admin123|password|change-this-initial-admin-password) return 0 ;; esac
  return 1
}

ensure_required_env() {
  local api_secret bootstrap pg_password general_limit export_limit new_password
  api_secret="$(get_env MEDEK_API_SECRET || true)"
  if is_weak "$api_secret" || [[ ${#api_secret} -lt 48 ]]; then
    set_env MEDEK_API_SECRET "$(hex_secret 48)"
    echo "MEDEK_API_SECRET otomatik üretildi."
  fi

  bootstrap="$(get_env MEDEK_BOOTSTRAP_ADMIN_PASSWORD || true)"
  if is_weak "$bootstrap"; then
    new_password="$(strong_password)"
    set_env MEDEK_BOOTSTRAP_ADMIN_PASSWORD "$new_password"
    echo "MEDEK_BOOTSTRAP_ADMIN_PASSWORD otomatik üretildi."
    echo "İlk admin şifresi: $new_password"
    echo "İlk girişten sonra değiştirin."
  fi

  pg_password="$(get_env POSTGRES_PASSWORD || true)"
  if is_weak "$pg_password"; then
    set_env POSTGRES_PASSWORD "$(strong_password)"
    echo "POSTGRES_PASSWORD otomatik üretildi."
  fi

  [[ -z "$(get_env MEDEK_ENV || true)" ]] && set_env MEDEK_ENV production
  [[ -z "$(get_env MEDEK_DB_BACKEND || true)" ]] && set_env MEDEK_DB_BACKEND postgresql
  [[ -z "$(get_env POSTGRES_DB || true)" ]] && set_env POSTGRES_DB medek
  [[ -z "$(get_env POSTGRES_USER || true)" ]] && set_env POSTGRES_USER medek

  general_limit="$(get_env MEDEK_RATE_LIMIT_GENERAL_PER_MINUTE || true)"
  if [[ -z "$general_limit" || "$general_limit" -lt 300 ]]; then set_env MEDEK_RATE_LIMIT_GENERAL_PER_MINUTE 300; fi
  export_limit="$(get_env MEDEK_RATE_LIMIT_EXPORT_PER_MINUTE || true)"
  if [[ -z "$export_limit" || "$export_limit" -lt 30 ]]; then set_env MEDEK_RATE_LIMIT_EXPORT_PER_MINUTE 30; fi
}

prepare_storage() {
  local ak_root="$1"
  mkdir -p \
    "$ak_root/00_canli_veri/postgresql" \
    "$ak_root/00_canli_veri/medek_data/kanitlar" \
    "$ak_root/00_canli_veri/medek_data/exports" \
    "$ak_root/00_canli_veri/medek_data/backups" \
    "$ak_root/01_zaman_damgali_yedekler" \
    "$ak_root/02_dis_aktarimlar" \
    "$ak_root/03_loglar" \
    "$ak_root/04_kurulum" \
    "$ak_root/99_arsiv"
  local stamp
  stamp="$(date +%Y-%m-%d_%H-%M-%S)"
  {
    echo "AKYS / Akreditasyon storage initialized"
    echo "Timestamp: $stamp"
    echo "Root: $ak_root"
    echo "Project: $ROOT"
  } > "$ak_root/04_kurulum/baslatma_${stamp}.txt"
}

if [[ ! -f .env ]]; then
  if [[ -f .env.web.example ]]; then
    cp .env.web.example .env
    echo "Created .env from .env.web.example."
  else
    echo ".env file is missing and .env.web.example was not found." >&2
    exit 1
  fi
fi

ensure_required_env

ak_root="$(get_env AKREDITASYON_ROOT || true)"
if [[ -z "$ak_root" || "$ak_root" == "./Akreditasyon" ]]; then
  desktop="${HOME}/Desktop"
  ak_root="${desktop}/Akreditasyon"
  set_env AKREDITASYON_ROOT "$ak_root"
fi
prepare_storage "$ak_root"

mkdir -p medek_data/kanitlar

declare -a compose_files=(-f docker-compose.web.yml)
[[ -f docker-compose.queue.yml ]] && compose_files+=(-f docker-compose.queue.yml)
[[ -f docker-compose.https.yml ]] && compose_files+=(-f docker-compose.https.yml)

docker compose --env-file .env "${compose_files[@]}" up --build -d
docker compose --env-file .env "${compose_files[@]}" ps

api_state="$(docker inspect -f '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' akys-api 2>/dev/null || true)"
if [[ "$api_state" != "running healthy" ]]; then
  echo ""
  echo "API sağlıklı başlamadı. Son loglar:" >&2
  docker logs --tail=160 akys-api >&2 || true
  exit 1
fi

echo ""
echo "AKYS web stack started."
echo "Open: http://SERVER_IP:8080 or configured MEDEK_WEB_PORT"
echo "Veriler masaüstündeki Akreditasyon klasörüne yazılır."
