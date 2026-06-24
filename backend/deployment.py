from __future__ import annotations

import os
import socket
from urllib.parse import quote, urlparse
from typing import Any

from .config import (
    CORS_ORIGINS,
    DATA_DIR,
    EVIDENCE_DIR,
    MEDEK_APP_BASE_URL,
    MEDEK_DATABASE_URL,
    MEDEK_DB_BACKEND,
    MEDEK_JOB_BACKEND,
    MEDEK_REDIS_URL,
    MEDEK_SMTP_HOST,
    MEDEK_SMTP_PORT,
    PROJECT_ROOT,
    SQLITE_PATH,
    TRUSTED_HOSTS,
    API_SECRET,
)
from .db import get_conn, now_iso
from .repositories import assert_admin
from .notifications import mail_system_status
from services.ollama_provider import ollama_status


def _mask_secret(value: str, visible: int = 4) -> str:
    clean = str(value or "")
    if not clean:
        return ""
    if len(clean) <= visible * 2:
        return "*" * len(clean)
    return f"{clean[:visible]}…{clean[-visible:]}"


def _check_item(key: str, label: str, status: str, detail: str = "", recommendation: str = "") -> dict[str, str]:
    return {
        "key": key,
        "label": label,
        "status": status,
        "detail": detail,
        "recommendation": recommendation,
    }


def _origin_from_url(value: str) -> str:
    parsed = urlparse(str(value or ""))
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def _host_from_url(value: str) -> str:
    parsed = urlparse(str(value or ""))
    return parsed.hostname or ""


def _db_smoke() -> tuple[bool, str]:
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()
            count = int(row["n"] if hasattr(row, "keys") else row[0])
        return True, f"Veritabanı bağlantısı çalışıyor; users={count}."
    except Exception as exc:  # noqa: BLE001 - deployment diagnostics should surface exact issue
        return False, str(exc)


def _storage_smoke() -> tuple[bool, str]:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        probe = DATA_DIR / ".medek_write_probe"
        probe.write_text(now_iso(), encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True, f"Yazma izni var: {DATA_DIR}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _compose_files() -> list[dict[str, Any]]:
    files = [
        "docker-compose.web.yml",
        "docker-compose.queue.yml",
        "docker-compose.https.yml",
        ".env.web.example",
        "tools/postgres_schema.sql",
        "tools/postgres_migrate.py",
        "tools/postgres_cutover_check.py",
    ]
    return [
        {"path": item, "exists": (PROJECT_ROOT / item).exists(), "size_bytes": (PROJECT_ROOT / item).stat().st_size if (PROJECT_ROOT / item).exists() else 0}
        for item in files
    ]


def _env_snippet() -> str:
    base_url = MEDEK_APP_BASE_URL or "http://SUNUCU_IP:8080"
    origin = _origin_from_url(base_url) or base_url
    host = _host_from_url(base_url) or "SUNUCU_IP"
    postgres_password = os.getenv("POSTGRES_PASSWORD", "CHANGE_ME_STRONG_POSTGRES_PASSWORD")
    postgres_password_quoted = quote(postgres_password, safe="")
    return "\n".join([
        "MEDEK_ENV=production",
        "MEDEK_API_SECRET=CHANGE_ME_GENERATE_NEW_64_CHAR_SECRET",
        "MEDEK_BOOTSTRAP_ADMIN_PASSWORD=CHANGE_ME_StrongAdmin_2026!",
        "MEDEK_WEB_PORT=8080",
        f"MEDEK_CORS_ORIGINS=http://localhost:8080,http://127.0.0.1:8080,{origin}",
        f"MEDEK_TRUSTED_HOSTS=localhost,127.0.0.1,api,web,{host}",
        f"MEDEK_APP_BASE_URL={base_url}",
        "MEDEK_DB_BACKEND=postgresql",
        "POSTGRES_DB=medek",
        "POSTGRES_USER=medek",
        f"POSTGRES_PASSWORD={postgres_password}",
        f"MEDEK_DATABASE_URL=postgresql://medek:{postgres_password_quoted}@postgres:5432/medek",
        "MEDEK_MAIL_ENABLED=false",
        "MEDEK_JOB_BACKEND=background",
        "MEDEK_AI_ENABLED=false",
    ])


def _run_commands() -> list[dict[str, str]]:
    return [
        {"step": "1", "title": "Yeni secret üret", "command": "python -c \"import secrets; print(secrets.token_hex(32))\""},
        {"step": "2", "title": ".env dosyasını düzenle", "command": "copy .env.web.example .env  # Windows PowerShell için: Copy-Item .env.web.example .env"},
        {"step": "3", "title": "Stack'i başlat", "command": "docker compose -f docker-compose.web.yml up --build -d"},
        {"step": "4", "title": "Servis durumunu kontrol et", "command": "docker compose -f docker-compose.web.yml ps"},
        {"step": "5", "title": "API loglarını izle", "command": "docker compose -f docker-compose.web.yml logs api --tail=100"},
        {"step": "6", "title": "PostgreSQL cutover kontrolü", "command": "docker compose -f docker-compose.web.yml exec api python tools/postgres_cutover_check.py"},
    ]


def deployment_wizard_payload(username: str) -> dict[str, Any]:
    assert_admin(username)
    app_origin = _origin_from_url(MEDEK_APP_BASE_URL)
    app_host = _host_from_url(MEDEK_APP_BASE_URL)
    db_ok, db_detail = _db_smoke()
    storage_ok, storage_detail = _storage_smoke()
    mail_status = mail_system_status()
    ai_status = ollama_status()

    checks: list[dict[str, str]] = []
    checks.append(_check_item(
        "secret",
        "API secret gücü",
        "pass" if API_SECRET and len(API_SECRET) >= 48 and "CHANGE_ME" not in API_SECRET else "fail",
        f"Uzunluk={len(API_SECRET or '')}; değer={_mask_secret(API_SECRET)}",
        "MEDEK_API_SECRET için python secrets.token_hex(32) ile yeni değer üretin.",
    ))
    checks.append(_check_item(
        "base_url",
        "Uygulama bağlantısı",
        "pass" if app_origin else "warn",
        MEDEK_APP_BASE_URL or "MEDEK_APP_BASE_URL boş.",
        "Okul içi son URL veya IP:port adresini MEDEK_APP_BASE_URL olarak yazın.",
    ))
    checks.append(_check_item(
        "cors",
        "CORS origin listesi",
        "pass" if (not app_origin or app_origin in CORS_ORIGINS) else "fail",
        ", ".join(CORS_ORIGINS) or "CORS origin yok.",
        f"MEDEK_CORS_ORIGINS içine {app_origin or 'uygulama origin'} eklenmeli.",
    ))
    checks.append(_check_item(
        "trusted_hosts",
        "Trusted host listesi",
        "pass" if (not app_host or app_host in TRUSTED_HOSTS or "*" in TRUSTED_HOSTS) else "fail",
        ", ".join(TRUSTED_HOSTS) or "Trusted host yok.",
        f"MEDEK_TRUSTED_HOSTS içine {app_host or 'sunucu host/IP'} eklenmeli.",
    ))
    checks.append(_check_item(
        "database",
        "Veritabanı bağlantısı",
        "pass" if db_ok else "fail",
        f"backend={MEDEK_DB_BACKEND}; {db_detail}",
        "Üretimde MEDEK_DB_BACKEND=postgresql ve MEDEK_DATABASE_URL postgres servisini göstermeli.",
    ))
    checks.append(_check_item(
        "postgres_url",
        "PostgreSQL DSN",
        "pass" if (MEDEK_DB_BACKEND == "postgresql" and bool(MEDEK_DATABASE_URL)) else "warn",
        _mask_secret(MEDEK_DATABASE_URL, 10) if MEDEK_DATABASE_URL else "MEDEK_DATABASE_URL boş veya SQLite modu.",
        "PostgreSQL üretim için MEDEK_DATABASE_URL zorunlu olmalı.",
    ))
    checks.append(_check_item(
        "storage",
        "Veri/kanıt klasörü yazma izni",
        "pass" if storage_ok else "fail",
        storage_detail,
        "medek_data volume klasörü API container tarafından yazılabilir olmalı.",
    ))
    checks.append(_check_item(
        "smtp",
        "SMTP yapılandırması",
        "pass" if mail_status.get("enabled") and mail_status.get("smtp_host_configured") else "warn",
        f"enabled={mail_status.get('enabled')}; host={mail_status.get('smtp_host_configured')}; port={mail_status.get('smtp_port')}",
        "E-posta bildirimi kullanılacaksa Ayarlar & Yedek → E-posta Bildirimleri bölümünden test mail gönderin.",
    ))
    checks.append(_check_item(
        "ollama",
        "Ollama/AI bağlantısı",
        "pass" if ai_status.get("available") else "warn",
        ai_status.get("message") or ai_status.get("error") or f"enabled={ai_status.get('enabled')}; provider={ai_status.get('provider')}",
        "AI opsiyoneldir. Kullanılacaksa Ayarlar & Yedek → AI / Ollama Testi bölümünden etkinleştirin, modeli seçin ve Modeli Yükle / Doğrula işlemini çalıştırın.",
    ))
    checks.append(_check_item(
        "compose",
        "Deployment dosyaları",
        "pass" if all(row["exists"] for row in _compose_files() if row["path"] in {"docker-compose.web.yml", ".env.web.example"}) else "fail",
        "docker-compose.web.yml ve .env.web.example API container içinde doğrulandı.",
        "Eksik görünürse Dockerfile.api deployment asset COPY satırlarını ve .dockerignore içindeki .env.web.example istisnasını kontrol edin.",
    ))
    checks.append(_check_item(
        "job_backend",
        "Export job backend",
        "pass" if MEDEK_JOB_BACKEND in {"background", "rq"} else "warn",
        f"backend={MEDEK_JOB_BACKEND}; redis={MEDEK_REDIS_URL}",
        "Tek container için background yeterli; çoklu instance için rq + Redis overlay kullanın.",
    ))

    summary = {
        "pass": len([item for item in checks if item["status"] == "pass"]),
        "warn": len([item for item in checks if item["status"] == "warn"]),
        "fail": len([item for item in checks if item["status"] == "fail"]),
    }
    readiness_score = round((summary["pass"] / max(1, len(checks))) * 100)
    return {
        "checked_at": now_iso(),
        "readiness_score": readiness_score,
        "summary": summary,
        "checks": checks,
        "environment": {
            "database_backend": MEDEK_DB_BACKEND,
            "database_url_configured": bool(MEDEK_DATABASE_URL),
            "sqlite_path": str(SQLITE_PATH),
            "data_dir": str(DATA_DIR),
            "evidence_dir": str(EVIDENCE_DIR),
            "app_base_url": MEDEK_APP_BASE_URL,
            "cors_origins": CORS_ORIGINS,
            "trusted_hosts": TRUSTED_HOSTS,
            "hostname": socket.gethostname(),
            "job_backend": MEDEK_JOB_BACKEND,
            "redis_url": MEDEK_REDIS_URL,
            "smtp_host": MEDEK_SMTP_HOST,
            "smtp_port": MEDEK_SMTP_PORT,
        },
        "mail_status": mail_status,
        "ai_status": ai_status,
        "compose_files": _compose_files(),
        "env_snippet": _env_snippet(),
        "run_commands": _run_commands(),
        "next_steps": [
            "MEDEK_API_SECRET ve admin şifresini gerçek değerlerle değiştirin.",
            "MEDEK_APP_BASE_URL, MEDEK_CORS_ORIGINS ve MEDEK_TRUSTED_HOSTS alanlarını okul içi IP/DNS adresine göre güncelleyin.",
            "PostgreSQL parolasını MEDEK_DATABASE_URL ile aynı tutun.",
            "E-posta kullanılacaksa SMTP ayarını kaydedip test mail gönderin.",
            "Docker stack başladıktan sonra bu sihirbazı tekrar çalıştırın.",
        ],
    }


def deployment_smoke_payload(username: str) -> dict[str, Any]:
    assert_admin(username)
    payload = deployment_wizard_payload(username)
    return {
        "ok": payload["summary"]["fail"] == 0,
        "checked_at": payload["checked_at"],
        "readiness_score": payload["readiness_score"],
        "failures": [item for item in payload["checks"] if item["status"] == "fail"],
        "warnings": [item for item in payload["checks"] if item["status"] == "warn"],
    }
