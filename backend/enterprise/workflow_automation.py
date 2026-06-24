from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import BackgroundTasks

from ..db import get_conn, now_iso, row_to_dict, rows_to_dicts, transaction
from ..notifications import create_notification_event, queue_notification
from ..repositories import ADMIN_ROLE, APPROVER_ROLE, EDITOR_ROLE, assert_admin, get_program, get_user, log_activity
from .workflow import workflow_reminders_payload

SETTING_PREFIX = "workflow."
DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": False,
    "email_enabled": True,
    "in_app_enabled": True,
    "deadline_days_before": 7,
    "repeat_days": 2,
    "include_overdue": True,
    "include_upcoming": True,
    "include_approval_waiting": True,
    "include_revision_waiting": True,
    "include_draft_followup": False,
    "weekly_digest_enabled": False,
    "weekly_digest_weekday": "Monday",
    "last_run_at": "",
    "last_run_summary": "",
}


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text == "":
        return default
    return text in {"1", "true", "yes", "on", "evet", "açık"}


def _int(value: Any, default: int, min_value: int = 0, max_value: int = 365) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(min_value, min(max_value, number))


def _setting_rows(program_id: str) -> dict[str, str]:
    keys = [f"{SETTING_PREFIX}{program_id}.%", f"{SETTING_PREFIX}global.%"]
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT key,value FROM settings WHERE key LIKE ? OR key LIKE ?",
            tuple(keys),
        ).fetchall()
    return {str(row["key"]): str(row["value"] or "") for row in rows}


def _normalize_settings(program_id: str, rows: dict[str, str]) -> dict[str, Any]:
    def get(name: str, default: Any) -> Any:
        return rows.get(f"{SETTING_PREFIX}{program_id}.{name}", rows.get(f"{SETTING_PREFIX}global.{name}", default))

    return {
        "enabled": _bool(get("enabled", DEFAULT_SETTINGS["enabled"]), DEFAULT_SETTINGS["enabled"]),
        "email_enabled": _bool(get("email_enabled", DEFAULT_SETTINGS["email_enabled"]), DEFAULT_SETTINGS["email_enabled"]),
        "in_app_enabled": _bool(get("in_app_enabled", DEFAULT_SETTINGS["in_app_enabled"]), DEFAULT_SETTINGS["in_app_enabled"]),
        "deadline_days_before": _int(get("deadline_days_before", DEFAULT_SETTINGS["deadline_days_before"]), DEFAULT_SETTINGS["deadline_days_before"], 1, 60),
        "repeat_days": _int(get("repeat_days", DEFAULT_SETTINGS["repeat_days"]), DEFAULT_SETTINGS["repeat_days"], 0, 30),
        "include_overdue": _bool(get("include_overdue", DEFAULT_SETTINGS["include_overdue"]), True),
        "include_upcoming": _bool(get("include_upcoming", DEFAULT_SETTINGS["include_upcoming"]), True),
        "include_approval_waiting": _bool(get("include_approval_waiting", DEFAULT_SETTINGS["include_approval_waiting"]), True),
        "include_revision_waiting": _bool(get("include_revision_waiting", DEFAULT_SETTINGS["include_revision_waiting"]), True),
        "include_draft_followup": _bool(get("include_draft_followup", DEFAULT_SETTINGS["include_draft_followup"]), False),
        "weekly_digest_enabled": _bool(get("weekly_digest_enabled", DEFAULT_SETTINGS["weekly_digest_enabled"]), False),
        "weekly_digest_weekday": str(get("weekly_digest_weekday", DEFAULT_SETTINGS["weekly_digest_weekday"]) or "Monday"),
        "last_run_at": str(get("last_run_at", "") or ""),
        "last_run_summary": str(get("last_run_summary", "") or ""),
    }


def workflow_automation_settings(username: str, program_id: str) -> dict[str, Any]:
    # A program access check is performed by the reminders payload; settings are visible to assigned users.
    workflow_reminders_payload(username, program_id)
    settings = _normalize_settings(program_id, _setting_rows(program_id))
    settings["program_id"] = program_id
    return settings


def update_workflow_automation_settings(username: str, program_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    assert_admin(username)
    workflow_reminders_payload(username, program_id)
    cleaned = _normalize_settings(program_id, {f"{SETTING_PREFIX}{program_id}.{key}": str(payload.get(key, value)) for key, value in DEFAULT_SETTINGS.items()})
    with transaction() as conn:
        for key, value in cleaned.items():
            if key in {"last_run_at", "last_run_summary"}:
                continue
            conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (f"{SETTING_PREFIX}{program_id}.{key}", json.dumps(value, ensure_ascii=False) if isinstance(value, bool) else str(value)),
            )
    log_activity("Workflow ayarları güncellendi", "Otomatik hatırlatma ayarları kaydedildi", username, program_id)
    return workflow_automation_settings(username, program_id)


def _include_reminder(row: dict[str, Any], settings: dict[str, Any]) -> bool:
    category = str(row.get("category") or "")
    days_left = row.get("days_left")
    if category == "Geciken termin":
        return bool(settings.get("include_overdue"))
    if category == "Yaklaşan termin":
        if not bool(settings.get("include_upcoming")):
            return False
        try:
            return int(days_left) <= int(settings.get("deadline_days_before") or 7)
        except (TypeError, ValueError):
            return True
    if category == "Onay bekliyor":
        return bool(settings.get("include_approval_waiting"))
    if category == "Revizyon bekliyor":
        return bool(settings.get("include_revision_waiting"))
    if category == "Hazırlık devam ediyor":
        return bool(settings.get("include_draft_followup"))
    return True


def _slug(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(value or "").strip()).strip("_") or "item"


def _last_sent_at(program_id: str, section_key: str, category: str) -> datetime | None:
    setting_key = f"workflow.sent.{program_id}.{_slug(section_key)}.{_slug(category)}"
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (setting_key,)).fetchone()
    raw = str((row_to_dict(row) or {}).get("value") or "")
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw[:19], fmt)
        except ValueError:
            continue
    return None


def _mark_sent(conn, program_id: str, section_key: str, category: str) -> None:
    setting_key = f"workflow.sent.{program_id}.{_slug(section_key)}.{_slug(category)}"
    conn.execute(
        "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (setting_key, now_iso()),
    )


def _program_label(program_id: str) -> str:
    program = get_program(program_id) or {}
    parts = [program.get("program_name", ""), program.get("accreditation_profile", ""), program.get("report_year", "")]
    return " / ".join([str(part) for part in parts if str(part or "").strip()]) or program_id


def _clean_recipients(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        email = str(row.get("email", "") or "").strip()
        if not email or "@" not in email:
            continue
        key = email.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "email": email,
            "name": str(row.get("full_name", "") or row.get("username", "") or ""),
            "username": str(row.get("username", "") or ""),
        })
    return result


def _admin_recipients(program_id: str) -> list[dict[str, str]]:
    program = get_program(program_id) or {}
    tenant_id = str(program.get("tenant_id", "tenant_default") or "tenant_default")
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT DISTINCT username,full_name,email FROM users
               WHERE is_active=1 AND role=? AND TRIM(COALESCE(email,''))<>''
                 AND (COALESCE(tenant_scope,'tenant')='global' OR COALESCE(tenant_id,'tenant_default')=?)""",
            (ADMIN_ROLE, tenant_id),
        ).fetchall()
    return _clean_recipients(rows_to_dicts(rows))


def _role_recipients(program_id: str, roles: set[str]) -> list[dict[str, str]]:
    if not roles:
        return []
    placeholders = ",".join("?" for _ in roles)
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT DISTINCT u.username,u.full_name,u.email
                FROM users u
                JOIN program_users pu ON pu.username=u.username AND pu.program_id=? AND pu.is_active=1 AND COALESCE(pu.deleted_at,'')=''
               WHERE u.is_active=1 AND TRIM(COALESCE(u.email,''))<>'' AND pu.role IN ({placeholders})""",
            (program_id, *sorted(roles)),
        ).fetchall()
    return _clean_recipients(rows_to_dicts(rows))


def _editor_recipients(program_id: str, section_key: str) -> list[dict[str, str]]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT DISTINCT u.username,u.full_name,u.email,pu.assigned_sections
                 FROM program_users pu JOIN users u ON u.username=pu.username
                WHERE pu.program_id=? AND pu.is_active=1 AND COALESCE(pu.deleted_at,'')='' AND u.is_active=1
                  AND pu.role=? AND TRIM(COALESCE(u.email,''))<>''""",
            (program_id, EDITOR_ROLE),
        ).fetchall()
    filtered: list[dict[str, Any]] = []
    for row in rows_to_dicts(rows):
        assigned = {part.strip() for part in str(row.get("assigned_sections", "") or "").split(",") if part.strip()}
        if not assigned or section_key in assigned:
            filtered.append(row)
    return _clean_recipients(filtered)


def _user_recipient(username: str) -> list[dict[str, str]]:
    user = get_user(username, active_only=True) or {}
    return _clean_recipients([user])


def _recipients_for_reminder(program_id: str, reminder: dict[str, Any]) -> list[dict[str, str]]:
    category = str(reminder.get("category") or "")
    section_key = str(reminder.get("section_key") or "")
    recipients: list[dict[str, str]] = []
    if category == "Onay bekliyor":
        recipients = _role_recipients(program_id, {APPROVER_ROLE}) + _admin_recipients(program_id)
    elif category == "Revizyon bekliyor":
        recipients = _editor_recipients(program_id, section_key) + _user_recipient(str(reminder.get("latest_actor") or "")) + _admin_recipients(program_id)
    elif category in {"Geciken termin", "Yaklaşan termin", "Hazırlık devam ediyor"}:
        recipients = _editor_recipients(program_id, section_key) + _admin_recipients(program_id)
    else:
        recipients = _role_recipients(program_id, {EDITOR_ROLE, APPROVER_ROLE}) + _admin_recipients(program_id)
    return _clean_recipients(recipients)


def workflow_automation_preview(username: str, program_id: str) -> dict[str, Any]:
    settings = workflow_automation_settings(username, program_id)
    payload = workflow_reminders_payload(username, program_id)
    rows: list[dict[str, Any]] = []
    for row in payload.get("rows", []):
        if not _include_reminder(row, settings):
            continue
        enriched = dict(row)
        recipients = _recipients_for_reminder(program_id, enriched)
        enriched["recipient_count"] = len(recipients)
        enriched["recipient_usernames"] = ", ".join([item.get("username", "") for item in recipients if item.get("username")])
        rows.append(enriched)
    summary: dict[str, int] = {}
    for row in rows:
        summary[str(row.get("category") or "Diğer")] = summary.get(str(row.get("category") or "Diğer"), 0) + 1
    return {
        "program_id": program_id,
        "settings": settings,
        "total": len(rows),
        "high_priority": sum(1 for row in rows if row.get("priority") == "Yüksek"),
        "summary": summary,
        "rows": rows,
    }


def run_workflow_automation(username: str, program_id: str, payload: dict[str, Any] | None = None, background_tasks: BackgroundTasks | None = None) -> dict[str, Any]:
    assert_admin(username)
    options = payload or {}
    settings = workflow_automation_settings(username, program_id)
    force = _bool(options.get("force"), False)
    if not settings.get("enabled") and not force:
        raise ValueError("Workflow otomasyonu kapalı. Önce ayarları etkinleştirin veya force=true ile manuel çalıştırın.")
    preview = workflow_automation_preview(username, program_id)
    max_items = _int(options.get("max_items"), 200, 1, 1000)
    repeat_days = _int(settings.get("repeat_days"), 2, 0, 30)
    run_id = str(uuid.uuid4())
    created = 0
    skipped = 0
    items: list[dict[str, Any]] = []
    program_label = _program_label(program_id)
    now_dt = datetime.now()
    with transaction() as conn:
        conn.execute(
            """INSERT INTO workflow_runs(id,program_id,actor,started_at,mode,total_candidates,created_notifications,skipped_notifications,summary_json)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (run_id, program_id, username, now_iso(), "manual-force" if force else "manual", len(preview.get("rows", [])), 0, 0, "{}"),
        )
    for reminder in preview.get("rows", [])[:max_items]:
        section_key = str(reminder.get("section_key") or "")
        category = str(reminder.get("category") or "")
        last_sent = _last_sent_at(program_id, section_key, category)
        if last_sent and not force and repeat_days > 0 and last_sent > now_dt - timedelta(days=repeat_days):
            skipped += 1
            items.append({**reminder, "notification_id": "", "automation_status": "skipped_recent"})
            continue
        recipients = _recipients_for_reminder(program_id, reminder)
        if not recipients:
            skipped += 1
            items.append({**reminder, "notification_id": "", "automation_status": "skipped_no_recipient"})
            continue
        section_label = f"{section_key} - {reminder.get('section_title', '')}".strip(" -")
        subject = f"Workflow hatırlatması: {category} - {section_label}"
        body = (
            f"{program_label} programı için otomatik workflow hatırlatması.\n\n"
            f"Kategori: {category}\nÖncelik: {reminder.get('priority', '')}\nBaşlık: {section_label}\n"
            f"Son teslim tarihi: {reminder.get('deadline', '-') or '-'}\nDurum: {reminder.get('status', '')}\n"
            f"Onay durumu: {reminder.get('approval_status', '')}\nMesaj: {reminder.get('message', '')}\n\n"
            "Bu bildirim AKYS workflow otomasyonu tarafından üretilmiştir."
        )
        if not settings.get("in_app_enabled", True) and not settings.get("email_enabled", True):
            skipped += 1
            items.append({**reminder, "notification_id": "", "automation_status": "skipped_disabled_channels"})
            continue
        if settings.get("email_enabled", True):
            event = queue_notification("workflow_reminder", recipients, subject, body, program_id=program_id, section_key=section_key, actor=username, background_tasks=background_tasks)
        else:
            event = create_notification_event("workflow_reminder", recipients, subject, body, program_id=program_id, section_key=section_key, actor=username)
            if event.get("id"):
                with transaction() as conn:
                    conn.execute("UPDATE notification_events SET status=?, error=? WHERE id=?", ("disabled", "Workflow e-posta kanalı kapalı; yalnızca in-app bildirim kaydı üretildi.", str(event.get("id"))))
                event = {**event, "status": "disabled", "error": "Workflow e-posta kanalı kapalı; yalnızca in-app bildirim kaydı üretildi."}
        notification_id = str(event.get("id", "") or "")
        with transaction() as conn:
            _mark_sent(conn, program_id, section_key, category)
            conn.execute(
                "INSERT INTO workflow_run_items(id,run_id,program_id,section_key,category,priority,recipient_count,notification_id,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), run_id, program_id, section_key, category, str(reminder.get("priority", "") or ""), len(recipients), notification_id, str(event.get("status", "queued") or "queued"), now_iso()),
            )
        created += 1
        items.append({**reminder, "notification_id": notification_id, "automation_status": "created"})
    summary = {"created": created, "skipped": skipped, "total_candidates": len(preview.get("rows", []))}
    with transaction() as conn:
        conn.execute(
            "UPDATE workflow_runs SET finished_at=?, created_notifications=?, skipped_notifications=?, summary_json=? WHERE id=?",
            (now_iso(), created, skipped, json.dumps(summary, ensure_ascii=False), run_id),
        )
        conn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (f"{SETTING_PREFIX}{program_id}.last_run_at", now_iso()),
        )
        conn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (f"{SETTING_PREFIX}{program_id}.last_run_summary", json.dumps(summary, ensure_ascii=False)),
        )
    log_activity("Workflow otomasyonu çalıştırıldı", f"{created} bildirim oluşturuldu, {skipped} atlandı", username, program_id)
    return {"run_id": run_id, **summary, "items": items}


def workflow_automation_runs(username: str, program_id: str, limit: int = 30) -> list[dict[str, Any]]:
    assert_admin(username)
    workflow_reminders_payload(username, program_id)
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id,program_id,actor,started_at,finished_at,mode,total_candidates,created_notifications,skipped_notifications,summary_json
               FROM workflow_runs WHERE program_id=? ORDER BY started_at DESC LIMIT ?""",
            (program_id, int(limit)),
        ).fetchall()
    return rows_to_dicts(rows)
