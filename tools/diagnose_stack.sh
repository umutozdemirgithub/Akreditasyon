#!/usr/bin/env bash
set +e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
compose_files=(-f docker-compose.web.yml)
[[ -f docker-compose.queue.yml ]] && compose_files+=(-f docker-compose.queue.yml)
[[ -f docker-compose.https.yml ]] && compose_files+=(-f docker-compose.https.yml)

echo "== Docker Compose PS =="
docker compose --env-file .env "${compose_files[@]}" ps

echo ""
echo "== API inspect =="
docker inspect -f 'Status={{.State.Status}} Health={{if .State.Health}}{{.State.Health.Status}}{{end}} ExitCode={{.State.ExitCode}}' akys-api

echo ""
echo "== API logs, last 220 lines =="
docker logs --tail=220 akys-api

echo ""
echo "== Postgres logs, last 120 lines =="
docker logs --tail=120 akys-postgres
