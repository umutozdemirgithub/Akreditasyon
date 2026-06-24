# AKYS v128 Enterprise Hardening Report

This release is prepared as a clean institutional delivery package under the
`v128-enterprise-hardening` version standard.

## Completed hardening

- Runtime/release versioning is standardized as `v128-enterprise-hardening`.
- FastAPI runtime version, README, CHANGELOG, frontend package version and release prefix are aligned.
- Clean release output is standardized as `outputs/ver_128_release_clean.zip`.
- Frontend EventSource no longer sends the main API bearer token in a query string.
- Backend EventSource no longer accepts the old primary access-token query fallback.
- SSE uses `/api/programs/{program_id}/events/session` plus the short-lived HttpOnly `medek_stream_token` cookie.
- Stream tokens are scoped by program ID, token version, issuer, audience, type and short TTL.
- `/api/health/ready` verifies database connectivity.
- API Docker healthcheck points to `/api/health/ready`.
- Redis has a `redis-cli ping` healthcheck.
- RQ worker has `python -m backend.worker --healthcheck` and Docker healthcheck support.
- Upload/import/restore flows have `Content-Length`, streamed-body and endpoint-level size guards.
- Defaults: evidence/report/docx import 50 MB, backup restore 10 MB, total request body 60 MB.
- `MEDEK_COOKIE_SECURE` is exposed for HTTPS reverse-proxy deployments.
- API container starts Uvicorn with proxy header support.
- Nginx `client_max_body_size` is aligned with the API total request body default at 60 MB.
- Nginx API proxy settings disable buffering/cache for SSE and keep long reads open.
- `.gitignore` excludes `.env`, database files, `node_modules`, `dist`, outputs and archives.
- `.env.web.example` includes the v128 deployment settings.

## Verification results

- `python tools/validate_project.py`: PASS
- `python -m compileall -q backend services core tools tests`: PASS
- `python -m pytest -q`: 98 passed
- `npm ci`: PASS, 0 vulnerabilities
- `npm audit --audit-level=high`: PASS, 0 vulnerabilities
- `npm run build`: PASS
- Docker compose config checks: PASS with required environment values supplied

## Regression coverage

- Normal API access tokens are rejected by the event stream path.
- Event stream endpoint has no `token` query parameter.
- Streamed/chunked request bodies without `Content-Length` are capped by middleware.
- Cookie secure, proxy header and body-limit deployment settings are present in release files.

## Clean release check

The clean ZIP must not include:

- `.env`
- SQLite/database files
- `medek_data/`
- `node_modules/`
- `frontend/dist/`
- `__pycache__/`
- `.pytest_cache/`
- nested ZIP archives

`ver_128/.env.web.example` is intentionally retained in the delivery package.
