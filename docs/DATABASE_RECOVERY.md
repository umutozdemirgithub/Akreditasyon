# Database / medek_data Recovery

If `medek_data` is deleted, the API starts with a fresh SQLite database. System templates are restored automatically from `backend/templates/*.json`, but user data is not recoverable without backup.

## What is restored automatically

- System template registry
- MEDEK, MÜDEK and other accreditation template skeletons
- Main criteria / section templates for newly created programs

## What is not restored without backup

- Users
- Programs
- Filled report texts
- Evidence links and uploaded evidence files
- Imported tables
- Approval history and activity logs

## Required after deleting medek_data in production

Set a strong bootstrap admin password in `.env` before starting:

```env
MEDEK_BOOTSTRAP_ADMIN_PASSWORD=MedekAdmin_2026!Guclu
```

Weak values such as `admin123`, `admin`, `password`, or placeholder values are rejected in production.

## Windows recovery command

```powershell
cd C:\Codes\MEDEK\web\ver_128
.\tools\recover_deleted_medek_data.ps1
```

## Manual Docker restart

```powershell
docker compose --env-file .env -f docker-compose.web.yml down
docker compose --env-file .env -f docker-compose.web.yml up -d --build web
docker compose --env-file .env -f docker-compose.web.yml logs -f api
```
