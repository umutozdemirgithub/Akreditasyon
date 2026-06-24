from __future__ import annotations

import os
import secrets
from pathlib import Path
from urllib.parse import quote


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_VERSION = os.getenv("MEDEK_APP_VERSION", "ver_100.1-role-theme-sync")
DATA_DIR = Path(os.getenv("MEDEK_DATA_DIR", str(PROJECT_ROOT / "medek_data")))
SQLITE_PATH = Path(os.getenv("MEDEK_SQLITE_PATH", str(DATA_DIR / "medek_kys_v7_9.sqlite3")))
EVIDENCE_DIR = Path(os.getenv("MEDEK_EVIDENCE_DIR", str(DATA_DIR / "kanitlar")))
ORG_STORAGE_DIR = Path(os.getenv("MEDEK_ORG_STORAGE_DIR", str(DATA_DIR / "kurumlar")))

MEDEK_DB_BACKEND = os.getenv("MEDEK_DB_BACKEND", "sqlite").strip().lower()
if MEDEK_DB_BACKEND in {"postgres", "postgresql", "pg"}:
    MEDEK_DB_BACKEND = "postgresql"
else:
    MEDEK_DB_BACKEND = "sqlite"


def _postgres_dsn_from_parts() -> str:
    user = os.getenv("POSTGRES_USER", "medek").strip() or "medek"
    password = os.getenv("POSTGRES_PASSWORD", "")
    host = os.getenv("POSTGRES_HOST", "postgres").strip() or "postgres"
    port = os.getenv("POSTGRES_PORT", "5432").strip() or "5432"
    db_name = os.getenv("POSTGRES_DB", "medek").strip() or "medek"
    return f"postgresql://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}/{quote(db_name, safe='')}"


MEDEK_DATABASE_URL = (os.getenv("MEDEK_DATABASE_URL") or os.getenv("POSTGRES_DSN") or "").strip()
if MEDEK_DB_BACKEND == "postgresql" and not MEDEK_DATABASE_URL:
    MEDEK_DATABASE_URL = _postgres_dsn_from_parts()

API_SECRET = os.getenv("MEDEK_API_SECRET") or os.getenv("MEDEK_ADMIN_PASSWORD") or ""
if not API_SECRET and os.getenv("MEDEK_ENV", "").lower() == "production":
    raise RuntimeError("MEDEK_API_SECRET is required in production.")
if not API_SECRET:
    # Development-only ephemeral secret. This prevents accidentally shipping a
    # hard-coded token signing key while keeping local smoke tests convenient.
    API_SECRET = secrets.token_urlsafe(48)
TOKEN_TTL_MINUTES = int(os.getenv("MEDEK_API_TOKEN_TTL_MINUTES", "480"))
LOGIN_MAX_FAILED_ATTEMPTS = int(os.getenv("MEDEK_LOGIN_MAX_FAILED_ATTEMPTS", "5"))
LOGIN_LOCK_MINUTES = int(os.getenv("MEDEK_LOGIN_LOCK_MINUTES", "15"))

RAW_CORS_ORIGINS = os.getenv(
    "MEDEK_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080",
)
CORS_ORIGINS = [origin.strip() for origin in RAW_CORS_ORIGINS.split(",") if origin.strip()]

RAW_TRUSTED_HOSTS = os.getenv("MEDEK_TRUSTED_HOSTS", "localhost,127.0.0.1,api,web")
TRUSTED_HOSTS = [host.strip() for host in RAW_TRUSTED_HOSTS.split(",") if host.strip()]

if os.getenv("MEDEK_ENV", "").lower() == "production":
    if MEDEK_DB_BACKEND == "postgresql" and not MEDEK_DATABASE_URL:
        raise RuntimeError("MEDEK_DATABASE_URL or POSTGRES_DSN is required when MEDEK_DB_BACKEND=postgresql.")
    weak_api_secrets = {"admin", "admin123", "password", "change-this-initial-admin-password"}
    if API_SECRET.lower() in weak_api_secrets or len(API_SECRET) < 48:
        raise RuntimeError("MEDEK_API_SECRET must be at least 48 characters and non-placeholder in production.")
    if "*" in CORS_ORIGINS:
        raise RuntimeError("MEDEK_CORS_ORIGINS must not contain '*' in production.")
    if "*" in TRUSTED_HOSTS:
        raise RuntimeError("MEDEK_TRUSTED_HOSTS must not contain '*' in production.")

# Export/job execution backend. Default remains process-local BackgroundTasks for
# simple single-container deployments. Set MEDEK_JOB_BACKEND=rq and run the
# queue compose overlay to use Redis + RQ for multi-instance production.
MEDEK_JOB_BACKEND = os.getenv("MEDEK_JOB_BACKEND", "background").strip().lower()
MEDEK_REDIS_URL = os.getenv("MEDEK_REDIS_URL", "redis://redis:6379/0").strip()
MEDEK_RQ_QUEUE = os.getenv("MEDEK_RQ_QUEUE", "medek_exports").strip() or "medek_exports"

# SMTP/e-mail notifications. Disabled by default; when enabled, workflow events
# such as approval submission, revision, approval, deadline updates, role
# assignments, and completed report exports can notify the relevant users.
MEDEK_MAIL_ENABLED = _env_bool("MEDEK_MAIL_ENABLED", "false")
MEDEK_SMTP_HOST = os.getenv("MEDEK_SMTP_HOST", "").strip()
MEDEK_SMTP_PORT = int(os.getenv("MEDEK_SMTP_PORT", "587"))
MEDEK_SMTP_USER = os.getenv("MEDEK_SMTP_USER", "").strip()
MEDEK_SMTP_PASSWORD = os.getenv("MEDEK_SMTP_PASSWORD", "")
MEDEK_SMTP_FROM = os.getenv("MEDEK_SMTP_FROM", MEDEK_SMTP_USER or "akreditasyon@localhost").strip()
MEDEK_SMTP_TLS = _env_bool("MEDEK_SMTP_TLS", "true")
MEDEK_SMTP_SSL = _env_bool("MEDEK_SMTP_SSL", "false")
MEDEK_APP_BASE_URL = os.getenv("MEDEK_APP_BASE_URL", "").strip().rstrip("/")
MEDEK_COOKIE_SECURE = _env_bool(
    "MEDEK_COOKIE_SECURE",
    "true" if MEDEK_APP_BASE_URL.lower().startswith("https://") else "false",
)

MEDEK_MAX_UPLOAD_MB = int(os.getenv("MEDEK_MAX_UPLOAD_MB", "50"))
MEDEK_MAX_UPLOAD_BYTES = MEDEK_MAX_UPLOAD_MB * 1024 * 1024
MEDEK_MAX_BACKUP_MB = int(os.getenv("MEDEK_MAX_BACKUP_MB", "10"))
MEDEK_MAX_BACKUP_BYTES = MEDEK_MAX_BACKUP_MB * 1024 * 1024
MEDEK_MAX_REQUEST_BODY_MB = int(os.getenv("MEDEK_MAX_REQUEST_BODY_MB", "60"))
MEDEK_MAX_REQUEST_BODY_BYTES = MEDEK_MAX_REQUEST_BODY_MB * 1024 * 1024
