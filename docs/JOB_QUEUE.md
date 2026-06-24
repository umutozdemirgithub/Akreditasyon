# Export job queue: BackgroundTasks vs Redis/RQ

AKYS supports two report-export execution modes.

## Default: FastAPI BackgroundTasks

Use this for local use, pilots, and a single API container. It requires no extra
service and is enabled by default:

```env
MEDEK_JOB_BACKEND=background
```

Start the normal stack:

```powershell
docker compose --env-file .env -f docker-compose.web.yml up --build -d
```

Limitation: if the API container restarts while a report is being generated, the
job may stop. It is also not suitable for multiple API instances.

## Production option: Redis + RQ

Use this when you run multiple API instances, expect concurrent exports, or want
report jobs to be processed by a separate worker process.

```env
MEDEK_JOB_BACKEND=rq
MEDEK_REDIS_URL=redis://redis:6379/0
MEDEK_RQ_QUEUE=medek_exports
```

Start with the queue overlay:

```powershell
docker compose --env-file .env -f docker-compose.web.yml -f docker-compose.queue.yml up --build -d
```

Expected containers:

```text
akys-api
akys-web
akys-redis
akys-worker
```

The API creates the export job row and enqueues work in Redis. The worker builds
the DOCX/PDF and writes the result under `medek_data/exports`.

## Operational checks

```powershell
docker logs --tail 80 akys-worker
docker logs --tail 80 akys-redis
```

If the queue is not enabled, the report job endpoints continue to work with the
default background backend.

## E-posta bildirimleri ve queue

Aynı backend seçimi e-posta bildirimleri için de kullanılır. `MEDEK_JOB_BACKEND=background` iken SMTP gönderimi FastAPI BackgroundTasks ile yapılır. `MEDEK_JOB_BACKEND=rq` iken onay, revizyon, termin planı, rol atama ve rapor hazır bildirimleri Redis/RQ kuyruğuna alınır.

SMTP ayrıntıları için `docs/EMAIL_NOTIFICATIONS.md` dosyasına bakın.
