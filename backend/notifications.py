from __future__ import annotations

import base64
import hashlib
import json
import smtplib
import ssl
import uuid
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from typing import Any

try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception as exc:  # pragma: no cover - exercised only when optional dependency is absent
    Fernet = None  # type: ignore[assignment]

    class InvalidToken(Exception):
        pass

    CRYPTOGRAPHY_IMPORT_ERROR = exc
else:
    CRYPTOGRAPHY_IMPORT_ERROR = None

from fastapi import BackgroundTasks

from .config import (
    API_SECRET,
    MEDEK_APP_BASE_URL,
    MEDEK_JOB_BACKEND,
    MEDEK_MAIL_ENABLED,
    MEDEK_REDIS_URL,
    MEDEK_RQ_QUEUE,
    MEDEK_SMTP_FROM,
    MEDEK_SMTP_HOST,
    MEDEK_SMTP_PASSWORD,
    MEDEK_SMTP_PORT,
    MEDEK_SMTP_SSL,
    MEDEK_SMTP_TLS,
    MEDEK_SMTP_USER,
)
from .db import get_conn, now_iso, row_to_dict, rows_to_dicts, transaction
from .repositories import ADMIN_ROLE, APPROVER_ROLE, EDITOR_ROLE, FACULTY_ADMIN_ROLE, SUPER_ADMIN_ROLE, TENANT_ADMIN_ROLE, actor_has_operation_permission, assert_operation_permission, get_program, get_user, normalized_role
from .visibility_scope import visible_notification_where

NOTIFICATION_EVENTS = {
    "approval_submitted",
    "revision_requested",
    "section_approved",
    "approval_undone",
    "deadline_updated",
    "program_assignment",
    "user_saved",
    "export_ready",
    "test_mail",
    "workflow_reminder",
    "weekly_digest",
}


MAIL_SETTING_PREFIX = "mail."


def _bool_from_value(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "evet"}


def _mail_setting_rows() -> dict[str, str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM settings WHERE key LIKE ?", (f"{MAIL_SETTING_PREFIX}%",)).fetchall()
    return {str(row["key"]): str(row["value"] or "") for row in rows}


def _upsert_setting(conn, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def _fernet() -> Fernet:
    if Fernet is None:
        raise RuntimeError(f"SMTP şifreleme için cryptography paketi gerekir: {CRYPTOGRAPHY_IMPORT_ERROR}")
    key = base64.urlsafe_b64encode(hashlib.sha256(API_SECRET.encode("utf-8")).digest())
    return Fernet(key)


def _encrypt_secret(value: str) -> str:
    if not value:
        return ""
    return "fernet:v1:" + _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def _decrypt_secret(value: str) -> str:
    if not value:
        return ""
    if not value.startswith("fernet:v1:"):
        # Backward-compatible fallback for manually seeded legacy rows. Do not
        # create new plain-text rows; update_mail_settings_admin always encrypts.
        return value
    token = value.split(":", 2)[2].encode("utf-8")
    try:
        return _fernet().decrypt(token).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("SMTP şifresi çözülemedi. MEDEK_API_SECRET değişmiş olabilir.") from exc


def _effective_mail_config() -> dict[str, Any]:
    rows = _mail_setting_rows()
    get = lambda key, default="": rows.get(f"{MAIL_SETTING_PREFIX}{key}", default)
    enabled_raw = get("enabled", str(MEDEK_MAIL_ENABLED).lower())
    tls_raw = get("tls", str(MEDEK_SMTP_TLS).lower())
    ssl_raw = get("ssl", str(MEDEK_SMTP_SSL).lower())
    try:
        port = int(get("smtp_port", str(MEDEK_SMTP_PORT)) or 587)
    except ValueError:
        port = 587
    password_row = get("smtp_password", "")
    password_error = ""
    try:
        password = _decrypt_secret(password_row) if password_row else MEDEK_SMTP_PASSWORD
    except RuntimeError as exc:
        # Keep the admin configuration screen usable even when MEDEK_API_SECRET
        # was rotated after an SMTP password had already been saved. The admin
        # can clear/re-enter the SMTP password from the UI instead of being
        # blocked by a 500 response.
        password = ""
        password_error = str(exc)
    return {
        "enabled": _bool_from_value(enabled_raw, MEDEK_MAIL_ENABLED),
        "smtp_host": get("smtp_host", MEDEK_SMTP_HOST).strip(),
        "smtp_port": port,
        "smtp_user": get("smtp_user", MEDEK_SMTP_USER).strip(),
        "smtp_password": password,
        "smtp_from": get("smtp_from", MEDEK_SMTP_FROM).strip() or "akreditasyon@localhost",
        "tls": _bool_from_value(tls_raw, MEDEK_SMTP_TLS),
        "ssl": _bool_from_value(ssl_raw, MEDEK_SMTP_SSL),
        "app_base_url": get("app_base_url", MEDEK_APP_BASE_URL).strip().rstrip("/"),
        "settings_stored": bool(rows),
        "job_backend": MEDEK_JOB_BACKEND,
        "password_error": password_error,
    }


def _safe_mail_settings(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or _effective_mail_config()
    return {
        "enabled": bool(config.get("enabled")),
        "smtp_host": str(config.get("smtp_host", "") or ""),
        "smtp_port": int(config.get("smtp_port") or 587),
        "smtp_user": str(config.get("smtp_user", "") or ""),
        "smtp_password": "",
        "smtp_password_configured": bool(config.get("smtp_password")),
        "smtp_from": str(config.get("smtp_from", "") or ""),
        "tls": bool(config.get("tls")),
        "ssl": bool(config.get("ssl")),
        "app_base_url": str(config.get("app_base_url", "") or ""),
        "settings_stored": bool(config.get("settings_stored")),
        "job_backend": str(config.get("job_backend", MEDEK_JOB_BACKEND) or MEDEK_JOB_BACKEND),
        "password_error": str(config.get("password_error", "") or ""),
    }


def get_mail_settings_admin(username: str) -> dict[str, Any]:
    assert_operation_permission(username, "notification.settings")
    return _safe_mail_settings()


def update_mail_settings_admin(username: str, payload: dict[str, Any]) -> dict[str, Any]:
    assert_operation_permission(username, "notification.settings")
    smtp_port = int(payload.get("smtp_port") or 587)
    if smtp_port < 1 or smtp_port > 65535:
        raise ValueError("SMTP port 1-65535 aralığında olmalıdır.")
    enabled = _bool_from_value(payload.get("enabled"), False)
    tls = _bool_from_value(payload.get("tls"), True)
    ssl_enabled = _bool_from_value(payload.get("ssl"), False)
    if tls and ssl_enabled:
        raise ValueError("TLS ve SSL aynı anda etkin olamaz. Port 587 için TLS, port 465 için SSL seçin.")
    with transaction() as conn:
        _upsert_setting(conn, "mail.enabled", "true" if enabled else "false")
        _upsert_setting(conn, "mail.smtp_host", str(payload.get("smtp_host", "") or "").strip())
        _upsert_setting(conn, "mail.smtp_port", str(smtp_port))
        _upsert_setting(conn, "mail.smtp_user", str(payload.get("smtp_user", "") or "").strip())
        _upsert_setting(conn, "mail.smtp_from", str(payload.get("smtp_from", "") or "").strip())
        _upsert_setting(conn, "mail.tls", "true" if tls else "false")
        _upsert_setting(conn, "mail.ssl", "true" if ssl_enabled else "false")
        _upsert_setting(conn, "mail.app_base_url", str(payload.get("app_base_url", "") or "").strip().rstrip("/"))
        if bool(payload.get("clear_password")):
            _upsert_setting(conn, "mail.smtp_password", "")
        else:
            password = str(payload.get("smtp_password", "") or "")
            if password:
                _upsert_setting(conn, "mail.smtp_password", _encrypt_secret(password))
    return _safe_mail_settings()


def mail_system_status() -> dict[str, Any]:
    config = _effective_mail_config()
    return {
        "enabled": bool(config["enabled"]),
        "smtp_host_configured": bool(config["smtp_host"]),
        "smtp_port": int(config["smtp_port"]),
        "smtp_user_configured": bool(config["smtp_user"]),
        "smtp_password_configured": bool(config["smtp_password"]),
        "smtp_from": config["smtp_from"],
        "tls": bool(config["tls"]),
        "ssl": bool(config["ssl"]),
        "app_base_url_configured": bool(config["app_base_url"]),
        "settings_stored": bool(config["settings_stored"]),
        "job_backend": config["job_backend"],
        "password_error": str(config.get("password_error", "") or ""),
    }


def list_notification_events_admin(username: str, limit: int = 100) -> list[dict[str, Any]]:
    user = get_user(username, active_only=True) or {}
    role = normalized_role(str(user.get("role", "") or ""), str(user.get("tenant_scope", "") or ""))
    if role not in {SUPER_ADMIN_ROLE, TENANT_ADMIN_ROLE, FACULTY_ADMIN_ROLE} or not actor_has_operation_permission(user, "notification.view"):
        raise PermissionError("Bildirim olayları için Yetki Matrisi izniniz yok.")
    where_sql, params = visible_notification_where(username)
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT id,event_type,program_id,section_key,actor,recipients_json,subject,status,error,created_at,sent_at
               FROM notification_events WHERE {where_sql} ORDER BY created_at DESC LIMIT ?""",
            [*params, int(limit)],
        ).fetchall()
    return rows_to_dicts(rows)


def _clean_recipients(recipients: list[dict[str, Any]] | list[str]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in recipients:
        if isinstance(item, str):
            email = item.strip()
            name = ""
            username = ""
        else:
            email = str(item.get("email", "") or "").strip()
            name = str(item.get("full_name", "") or item.get("username", "") or "").strip()
            username = str(item.get("username", "") or "").strip()
        if not email or "@" not in email:
            continue
        key = email.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append({"email": email, "name": name, "username": username})
    return result


def _program_label(program_id: str) -> str:
    program = get_program(program_id) or {}
    if not program:
        return program_id
    parts = [
        str(program.get("program_name", "") or "").strip(),
        str(program.get("accreditation_profile", "") or "").strip(),
        str(program.get("report_year", "") or "").strip(),
    ]
    return " / ".join([p for p in parts if p]) or program_id


def _section_label(program_id: str, section_key: str) -> str:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT section_key, main_title, section_title FROM sections WHERE program_id=? AND section_key=?",
            (program_id, section_key),
        ).fetchone()
    data = row_to_dict(row) or {}
    title = str(data.get("section_title", "") or "").strip()
    main = str(data.get("main_title", "") or "").strip()
    key = str(data.get("section_key", "") or section_key).strip()
    if title and main and title != main:
        return f"{key} - {main} / {title}"
    return f"{key} - {title or main or section_key}"


def _app_link(program_id: str = "", section_key: str = "") -> str:
    base_url = str(_effective_mail_config().get("app_base_url", "") or "")
    if not base_url:
        return ""
    # The current frontend is a single-page app. The base URL is the safest link;
    # the program/section identifiers are included as query hints for future deep links.
    if program_id and section_key:
        return f"{base_url}/?program={program_id}&section={section_key}"
    if program_id:
        return f"{base_url}/?program={program_id}"
    return base_url


def _user_recipient(username: str) -> list[dict[str, str]]:
    user = get_user(username, active_only=True) or {}
    return _clean_recipients([user])


def _program_role_recipients(program_id: str, roles: set[str], *, include_global: bool = True) -> list[dict[str, str]]:
    params: list[Any] = [program_id]
    role_placeholders = ",".join("?" for _ in roles) or "?"
    params.extend(sorted(roles) or [""])
    global_clause = ""
    if include_global:
        global_clause = f" OR u.role IN ({role_placeholders})"
        params.extend(sorted(roles) or [""])
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT DISTINCT u.username, u.full_name, u.email
                   FROM users u
                   LEFT JOIN program_users pu ON pu.username=u.username AND pu.program_id=? AND pu.is_active=1
                  WHERE u.is_active=1
                    AND TRIM(COALESCE(u.email, '')) <> ''
                    AND (pu.role IN ({role_placeholders}){global_clause})""",
            tuple(params),
        ).fetchall()
    return _clean_recipients(rows_to_dicts(rows))


def _program_active_recipients(program_id: str, *, include_admins: bool = True) -> list[dict[str, str]]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT DISTINCT u.username, u.full_name, u.email
                 FROM users u
                 LEFT JOIN program_users pu ON pu.username=u.username AND pu.program_id=? AND pu.is_active=1
                WHERE u.is_active=1
                  AND TRIM(COALESCE(u.email, '')) <> ''
                  AND (pu.program_id IS NOT NULL OR (?=1 AND u.role=?))""",
            (program_id, 1 if include_admins else 0, ADMIN_ROLE),
        ).fetchall()
    return _clean_recipients(rows_to_dicts(rows))


def _last_submitter(program_id: str, section_key: str) -> str:
    with get_conn() as conn:
        row = conn.execute(
            """SELECT requested_by FROM section_approvals
                 WHERE program_id=? AND section_key=? AND status='Onaya Gönderildi'
                 ORDER BY created_at DESC LIMIT 1""",
            (program_id, section_key),
        ).fetchone()
    return str((row_to_dict(row) or {}).get("requested_by", "") or "")


def _assigned_editor_recipients(program_id: str, section_key: str) -> list[dict[str, str]]:
    # Notify editors explicitly assigned to the section; editors with blank
    # assigned_sections are program-wide editors and are also included.
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT DISTINCT u.username, u.full_name, u.email, pu.assigned_sections
                 FROM program_users pu
                 JOIN users u ON u.username=pu.username
                WHERE pu.program_id=? AND pu.is_active=1 AND u.is_active=1 AND pu.role=?
                  AND TRIM(COALESCE(u.email, '')) <> ''""",
            (program_id, EDITOR_ROLE),
        ).fetchall()
    candidates = []
    for row in rows_to_dicts(rows):
        assigned = str(row.get("assigned_sections", "") or "").strip()
        keys = {part.strip() for part in assigned.split(",") if part.strip()}
        if not keys or section_key in keys:
            candidates.append(row)
    return _clean_recipients(candidates)


def create_notification_event(
    event_type: str,
    recipients: list[dict[str, Any]] | list[str],
    subject: str,
    body: str,
    *,
    program_id: str = "",
    section_key: str = "",
    actor: str = "",
) -> dict[str, Any]:
    if event_type not in NOTIFICATION_EVENTS:
        raise ValueError("Desteklenmeyen bildirim olayı.")
    clean = _clean_recipients(recipients)
    notification_id = str(uuid.uuid4())
    now = now_iso()
    status = "queued" if clean else "skipped"
    error = "" if clean else "Alıcı e-posta adresi bulunamadı."
    with transaction() as conn:
        conn.execute(
            """INSERT INTO notification_events(
                id,event_type,program_id,section_key,actor,recipients_json,subject,body,status,error,created_at,sent_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (notification_id, event_type, program_id, section_key, actor, json.dumps(clean, ensure_ascii=False), subject, body, status, error, now, ""),
        )
    return get_notification_event(notification_id) or {"id": notification_id, "status": status}


def get_notification_event(notification_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM notification_events WHERE id=?", (notification_id,)).fetchone()
    return row_to_dict(row)


def _set_notification_status(notification_id: str, status: str, *, error: str = "") -> None:
    sent_at = now_iso() if status in {"sent", "disabled", "skipped"} else ""
    with transaction() as conn:
        conn.execute(
            "UPDATE notification_events SET status=?, error=?, sent_at=COALESCE(NULLIF(?, ''), sent_at) WHERE id=?",
            (status, error[:1000], sent_at, notification_id),
        )


def _smtp_host_is_gmail(host: str) -> bool:
    normalized = str(host or "").strip().lower()
    return normalized in {"smtp.gmail.com", "gmail-smtp-in.l.google.com"} or normalized.endswith(".gmail.com")


def _normalized_from_header(config: dict[str, Any]) -> str:
    """Return a safe RFC 5322 From header.

    Admins often type only a display name such as "AKYS ÖDR" into the
    sender field. SMTP providers like Gmail still require a real address in the
    From header. If the sender field has no address, pair that display name with
    the SMTP user address.
    """
    raw_from = str(config.get("smtp_from") or "").strip()
    smtp_user = str(config.get("smtp_user") or "").strip()
    parsed_name, parsed_email = parseaddr(raw_from)
    if parsed_email and "@" in parsed_email:
        return formataddr((parsed_name, parsed_email)) if parsed_name else parsed_email
    if smtp_user and "@" in smtp_user:
        display_name = raw_from or "AKYS"
        return formataddr((display_name, smtp_user))
    return raw_from or "akreditasyon@localhost"


def _validate_smtp_config_for_send(config: dict[str, Any]) -> None:
    host = str(config.get("smtp_host") or "").strip()
    if not host:
        raise RuntimeError("SMTP sunucu adresi tanımlı değil.")
    port = int(config.get("smtp_port") or 587)
    tls_enabled = bool(config.get("tls"))
    ssl_enabled = bool(config.get("ssl"))
    smtp_user = str(config.get("smtp_user") or "").strip()
    smtp_password = str(config.get("smtp_password") or "")
    if tls_enabled and ssl_enabled:
        raise RuntimeError("TLS ve SSL aynı anda açık olamaz. Port 587 için TLS, port 465 için SSL seçin.")
    if smtp_user and not smtp_password:
        raise RuntimeError("SMTP kullanıcı adı girilmiş ama SMTP şifresi boş. Gmail için normal hesap şifresi değil, Google Uygulama Şifresi girilmelidir.")
    if _smtp_host_is_gmail(host):
        if port == 587 and not tls_enabled:
            raise RuntimeError("Gmail SMTP için port 587 kullanılıyorsa TLS açık olmalıdır.")
        if port == 465 and not ssl_enabled:
            raise RuntimeError("Gmail SMTP için port 465 kullanılıyorsa SSL açık olmalıdır.")
        if not smtp_user or not smtp_password:
            raise RuntimeError("Gmail SMTP kimlik doğrulaması ister. SMTP kullanıcı e-posta adresi ve Google Uygulama Şifresi girilmelidir.")


def _smtp_login_if_needed(server: smtplib.SMTP, config: dict[str, Any]) -> None:
    smtp_user = str(config.get("smtp_user") or "").strip()
    if not smtp_user:
        return
    smtp_password = str(config.get("smtp_password") or "")
    try:
        server.login(smtp_user, smtp_password)
    except smtplib.SMTPNotSupportedError as exc:
        host = str(config.get("smtp_host") or "")
        port = int(config.get("smtp_port") or 587)
        hint = "SMTP sunucusu AUTH desteği ilan etmiyor."
        if _smtp_host_is_gmail(host):
            hint = "Gmail için 587+TLS veya 465+SSL kullanın; bağlantı STARTTLS sonrası yeniden EHLO yapılarak doğrulanır."
        elif port == 25:
            hint = "Port 25 genelde kurum içi relay içindir; kullanıcı/şifre boş bırakılmalıdır."
        raise RuntimeError(f"SMTP AUTH desteklenmiyor. {hint}") from exc
    except smtplib.SMTPAuthenticationError as exc:
        detail = exc.smtp_error.decode("utf-8", errors="ignore") if isinstance(exc.smtp_error, bytes) else str(exc.smtp_error)
        if _smtp_host_is_gmail(str(config.get("smtp_host") or "")):
            raise RuntimeError("Gmail SMTP kimlik doğrulaması başarısız. Google hesabında 2 Adımlı Doğrulama açık olmalı ve SMTP Şifre alanına normal Gmail şifresi değil Google Uygulama Şifresi girilmelidir.") from exc
        raise RuntimeError(f"SMTP kimlik doğrulaması başarısız: {detail or exc.smtp_code}") from exc


def _send_smtp_message(recipients: list[dict[str, str]], subject: str, body: str) -> None:
    config = _effective_mail_config()
    _validate_smtp_config_for_send(config)
    message = EmailMessage()
    message["From"] = _normalized_from_header(config)
    message["To"] = ", ".join(item["email"] for item in recipients)
    message["Subject"] = subject
    message.set_content(body)
    if config["ssl"]:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(config["smtp_host"], int(config["smtp_port"]), context=context, timeout=20) as server:
            server.ehlo()
            _smtp_login_if_needed(server, config)
            server.send_message(message)
    else:
        with smtplib.SMTP(config["smtp_host"], int(config["smtp_port"]), timeout=20) as server:
            server.ehlo()
            if config["tls"]:
                server.starttls(context=ssl.create_default_context())
                # AUTH is often advertised only after STARTTLS. A second EHLO is
                # required by RFC 3207 and fixes Gmail/Office365 false
                # "SMTP AUTH extension not supported" failures.
                server.ehlo()
            _smtp_login_if_needed(server, config)
            server.send_message(message)


def deliver_notification_event(notification_id: str) -> None:
    event = get_notification_event(notification_id)
    if not event:
        return
    if event.get("status") not in {"queued", "retry"}:
        return
    try:
        recipients = json.loads(str(event.get("recipients_json", "[]") or "[]"))
    except json.JSONDecodeError:
        recipients = []
    recipients = _clean_recipients(recipients)
    if not recipients:
        _set_notification_status(notification_id, "skipped", error="Alıcı e-posta adresi bulunamadı.")
        return
    if not _effective_mail_config()["enabled"]:
        _set_notification_status(notification_id, "disabled", error="E-posta bildirimleri kapalı")
        return
    try:
        _send_smtp_message(recipients, str(event.get("subject", "") or ""), str(event.get("body", "") or ""))
        _set_notification_status(notification_id, "sent")
    except Exception as exc:  # noqa: BLE001 - persist SMTP failure for admin diagnostics
        _set_notification_status(notification_id, "failed", error=str(exc))


def _rq_queue():
    from redis import Redis
    from rq import Queue

    redis_conn = Redis.from_url(MEDEK_REDIS_URL)
    return Queue(MEDEK_RQ_QUEUE, connection=redis_conn)


def enqueue_notification(event: dict[str, Any], background_tasks: BackgroundTasks | None = None) -> None:
    notification_id = str(event.get("id", "") or "")
    if not notification_id or event.get("status") == "skipped":
        return
    try:
        if MEDEK_JOB_BACKEND == "rq":
            _rq_queue().enqueue(deliver_notification_event, notification_id, job_timeout=120, result_ttl=3600, failure_ttl=86400)
        elif background_tasks is not None:
            background_tasks.add_task(deliver_notification_event, notification_id)
        else:
            deliver_notification_event(notification_id)
    except Exception as exc:  # noqa: BLE001 - notifications must not break business workflow
        _set_notification_status(notification_id, "failed", error=f"Kuyruğa alma hatası: {exc}")


def queue_notification(
    event_type: str,
    recipients: list[dict[str, Any]] | list[str],
    subject: str,
    body: str,
    *,
    program_id: str = "",
    section_key: str = "",
    actor: str = "",
    background_tasks: BackgroundTasks | None = None,
) -> dict[str, Any]:
    try:
        event = create_notification_event(
            event_type,
            recipients,
            subject,
            body,
            program_id=program_id,
            section_key=section_key,
            actor=actor,
        )
        enqueue_notification(event, background_tasks)
        return event
    except Exception as exc:  # noqa: BLE001 - notifications must not break business workflow
        return {"ok": False, "error": str(exc)}


def send_test_mail_admin(username: str, payload: dict[str, Any], background_tasks: BackgroundTasks | None = None) -> dict[str, Any]:
    assert_operation_permission(username, "notification.settings")
    current_user = get_user(username, active_only=True) or {}
    to_addr = str(payload.get("to", "") or current_user.get("email", "") or "").strip()
    if not to_addr or "@" not in to_addr:
        raise ValueError("Test mail için geçerli bir alıcı e-posta adresi girin.")
    subject = str(payload.get("subject", "") or "AKYS test e-postası").strip()
    body = str(payload.get("body", "") or "Bu e-posta Akreditasyon Kalite Yönetim Sistemi SMTP ayarlarını test etmek için gönderilmiştir.").strip()
    return queue_notification("test_mail", [to_addr], subject, body, actor=username, background_tasks=background_tasks)


def notify_approval_event(
    actor: str,
    program_id: str,
    section_key: str,
    action: str,
    note: str,
    section: dict[str, Any],
    background_tasks: BackgroundTasks | None = None,
) -> None:
    action = str(action or "").strip().lower()
    program = _program_label(program_id)
    section_label = _section_label(program_id, section_key)
    link = _app_link(program_id, section_key)
    actor_user = get_user(actor, active_only=False) or {"username": actor}
    actor_label = str(actor_user.get("full_name") or actor_user.get("username") or actor)
    if action == "send":
        recipients = _program_role_recipients(program_id, {APPROVER_ROLE, ADMIN_ROLE})
        subject = f"Onay bekliyor - {section_label}"
        body = f"{program} programında bir başlık onaya gönderildi.\n\nBaşlık: {section_label}\nGönderen: {actor_label}\nNot: {note or '-'}\nDurum: {section.get('approval_status', '')}\n{('Bağlantı: ' + link) if link else ''}\n\nBu e-posta otomatik gönderilmiştir."
        queue_notification("approval_submitted", recipients, subject, body, program_id=program_id, section_key=section_key, actor=actor, background_tasks=background_tasks)
    elif action == "approve":
        recipients = _user_recipient(_last_submitter(program_id, section_key)) + _program_role_recipients(program_id, {ADMIN_ROLE})
        subject = f"Onaylandı - {section_label}"
        body = f"{program} programında bir başlık onaylandı.\n\nBaşlık: {section_label}\nOnaylayan: {actor_label}\nNot: {note or '-'}\n{('Bağlantı: ' + link) if link else ''}\n\nBu e-posta otomatik gönderilmiştir."
        queue_notification("section_approved", recipients, subject, body, program_id=program_id, section_key=section_key, actor=actor, background_tasks=background_tasks)
    elif action == "revision":
        submitter = _user_recipient(_last_submitter(program_id, section_key))
        editors = _assigned_editor_recipients(program_id, section_key)
        recipients = submitter + editors + _program_role_recipients(program_id, {ADMIN_ROLE})
        subject = f"Revizyon istendi - {section_label}"
        body = f"{program} programında bir başlık için revizyon istendi.\n\nBaşlık: {section_label}\nİsteyen: {actor_label}\nRevizyon notu: {note or '-'}\n{('Bağlantı: ' + link) if link else ''}\n\nBu e-posta otomatik gönderilmiştir."
        queue_notification("revision_requested", recipients, subject, body, program_id=program_id, section_key=section_key, actor=actor, background_tasks=background_tasks)
    elif action == "undo":
        recipients = _user_recipient(_last_submitter(program_id, section_key)) + _program_role_recipients(program_id, {ADMIN_ROLE})
        subject = f"Onay geri alındı - {section_label}"
        body = f"{program} programında bir başlığın onayı geri alındı.\n\nBaşlık: {section_label}\nİşlem yapan: {actor_label}\nNot: {note or '-'}\n{('Bağlantı: ' + link) if link else ''}\n\nBu e-posta otomatik gönderilmiştir."
        queue_notification("approval_undone", recipients, subject, body, program_id=program_id, section_key=section_key, actor=actor, background_tasks=background_tasks)


def notify_deadlines_updated(
    actor: str,
    program_id: str,
    changed_rows: list[dict[str, Any]],
    background_tasks: BackgroundTasks | None = None,
) -> None:
    rows = [row for row in changed_rows if str(row.get("deadline", "") or "").strip()]
    if not rows:
        return
    program = _program_label(program_id)
    recipients = _program_active_recipients(program_id, include_admins=True)
    preview = "\n".join(f"- {row.get('section_key', '')}: {row.get('section_title', '')} -> {row.get('deadline', '')}" for row in rows[:12])
    if len(rows) > 12:
        preview += f"\n- ... {len(rows) - 12} başlık daha"
    link = _app_link(program_id)
    subject = f"Son teslim tarihi planı güncellendi - {program}"
    body = f"{program} programında son teslim tarihi planı güncellendi.\n\nGüncellenen başlıklar:\n{preview}\n\n{('Bağlantı: ' + link) if link else ''}\n\nBu e-posta otomatik gönderilmiştir."
    queue_notification("deadline_updated", recipients, subject, body, program_id=program_id, actor=actor, background_tasks=background_tasks)


def notify_program_assignment(
    actor: str,
    target_username: str,
    program_ids: list[str],
    role: str,
    background_tasks: BackgroundTasks | None = None,
) -> None:
    recipients = _user_recipient(target_username)
    if not recipients:
        return
    program_lines = "\n".join(f"- {_program_label(program_id)}" for program_id in program_ids)
    link = _app_link()
    subject = "Program yetkiniz güncellendi"
    body = f"Akreditasyon Kalite Yönetim Sistemi içinde program yetkiniz güncellendi.\n\nRol: {role}\nProgramlar:\n{program_lines}\n\n{('Sistem bağlantısı: ' + link) if link else ''}\n\nBu e-posta otomatik gönderilmiştir."
    queue_notification("program_assignment", recipients, subject, body, actor=actor, background_tasks=background_tasks)


def notify_user_saved(actor: str, saved_user: dict[str, Any], password_was_set: bool, background_tasks: BackgroundTasks | None = None) -> None:
    recipients = _clean_recipients([saved_user])
    if not recipients:
        return
    username = str(saved_user.get("username", "") or "")
    link = _app_link()
    subject = "Kullanıcı hesabınız güncellendi"
    extra = "İlk girişten sonra şifrenizi değiştirmeniz istenebilir." if password_was_set else "Hesap bilgileriniz güncellendi."
    body = f"Akreditasyon Kalite Yönetim Sistemi hesabınız güncellendi.\n\nKullanıcı adı: {username}\n{extra}\n\nGüvenlik nedeniyle bu e-postada şifre paylaşılmaz.\n{('Sistem bağlantısı: ' + link) if link else ''}\n\nBu e-posta otomatik gönderilmiştir."
    queue_notification("user_saved", recipients, subject, body, actor=actor, background_tasks=background_tasks)


def notify_export_ready(actor: str, program_id: str, export_type: str, job_id: str) -> None:
    recipients = _user_recipient(actor)
    if not recipients:
        return
    program = _program_label(program_id)
    link = _app_link(program_id)
    subject = f"Rapor çıktısı hazır - {program}"
    body = f"{program} programı için {export_type} rapor çıktısı hazırlandı.\n\nİş numarası: {job_id}\n{('Sistem bağlantısı: ' + link) if link else ''}\n\nBu e-posta otomatik gönderilmiştir."
    queue_notification("export_ready", recipients, subject, body, program_id=program_id, actor=actor, background_tasks=None)
