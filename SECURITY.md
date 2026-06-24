# Security Policy

This project keeps the detailed operational security guide in `docs/SECURITY.md`.

Use this root-level file as the quick checklist before deploying AKYS:

- Set `MEDEK_ENV=production`.
- Set a unique `MEDEK_API_SECRET` with at least 48 characters.
- Set `MEDEK_BOOTSTRAP_ADMIN_PASSWORD` to a strong password and change it after first login.
- Do not use `*` in `MEDEK_CORS_ORIGINS` or `MEDEK_TRUSTED_HOSTS` in production.
- Keep `MEDEK_TRUSTED_HOSTS` limited to real intranet hostnames, reverse-proxy names, and service names such as `api` and `web`.
- Keep backups encrypted or access-controlled.
- Rotate secrets after sharing logs, screenshots, or `.env` content.
- Build public/internal release zips only with `tools/make_release_zip.py` or `tools/make_release_zip.ps1`; the generated archive is verified and must not contain `.env`, databases, evidence files, cache folders, `node_modules`, frontend `dist`, `outputs`, `work`, or old zip archives.

See `docs/SECURITY.md` for the full hardening guide and incident checklist.
