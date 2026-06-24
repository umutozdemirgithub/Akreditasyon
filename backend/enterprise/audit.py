from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from ..db import get_conn, rows_to_dicts
from ..repositories import assert_program_access, stats_payload


def _limit(value: int | str | None, default: int = 500, maximum: int = 2000) -> int:
    try:
        clean = int(value or default)
    except Exception:
        clean = default
    return max(50, min(maximum, clean))


def _count_by(rows: list[dict[str, Any]], key: str, fallback: str = "-") -> list[dict[str, Any]]:
    counts = Counter(str(row.get(key) or fallback) for row in rows)
    return [{key: item, "count": count} for item, count in counts.most_common()]


def compliance_audit_payload(username: str, program_id: str, limit: int = 500) -> dict[str, Any]:
    """Return a governance-oriented audit export payload.

    This is intentionally read-only and built from existing operational tables so
    it works on old SQLite installations without a destructive migration.
    """
    assert_program_access(username, program_id)
    clean_limit = _limit(limit)
    with get_conn() as conn:
        activity = rows_to_dicts(conn.execute(
            """SELECT id, ts, action, detail, actor, program_id
               FROM activity_log
               WHERE program_id=? OR program_id=''
               ORDER BY ts DESC
               LIMIT ?""",
            (program_id, clean_limit),
        ).fetchall())
        approvals = rows_to_dicts(conn.execute(
            """SELECT id, created_at, section_key, status, requested_by, decided_by, note
               FROM section_approvals
               WHERE program_id=?
               ORDER BY created_at DESC
               LIMIT ?""",
            (program_id, clean_limit),
        ).fetchall())
        notifications = rows_to_dicts(conn.execute(
            """SELECT id, created_at, sent_at, event_type, section_key, actor, status, subject, error
               FROM notification_events
               WHERE program_id=?
               ORDER BY created_at DESC
               LIMIT ?""",
            (program_id, clean_limit),
        ).fetchall())
        exports = rows_to_dicts(conn.execute(
            """SELECT id, created_at, export_type, file_name, actor, note
               FROM export_history
               WHERE program_id=?
               ORDER BY created_at DESC
               LIMIT ?""",
            (program_id, clean_limit),
        ).fetchall())
        versions = rows_to_dicts(conn.execute(
            """SELECT id, saved_at, section_key, status, deadline, change_summary
               FROM section_versions
               WHERE program_id=?
               ORDER BY saved_at DESC
               LIMIT ?""",
            (program_id, clean_limit),
        ).fetchall())
        sections = rows_to_dicts(conn.execute(
            """SELECT section_key, main_title, section_title, status, approval_status, approved_by, approved_at, updated_at, deadline
               FROM sections
               WHERE program_id=? AND COALESCE(deleted_at,'')=''
               ORDER BY sort_order, section_key""",
            (program_id,),
        ).fetchall())

    stats = stats_payload(username, program_id)
    approval_counter = Counter(str(row.get("approval_status") or "Taslak") for row in sections)
    status_counter = Counter(str(row.get("status") or "Başlamadı") for row in sections)
    stale_sections = [row for row in sections if str(row.get("approval_status") or "") in {"Onaya Gönderildi", "Revizyon Gerekli"}]
    section_activity: dict[str, dict[str, Any]] = defaultdict(lambda: {"section_key": "", "activity": 0, "versions": 0, "approvals": 0, "notifications": 0})
    for row in versions:
        key = str(row.get("section_key") or "")
        section_activity[key]["section_key"] = key
        section_activity[key]["versions"] += 1
        section_activity[key]["activity"] += 1
    for row in approvals:
        key = str(row.get("section_key") or "")
        section_activity[key]["section_key"] = key
        section_activity[key]["approvals"] += 1
        section_activity[key]["activity"] += 1
    for row in notifications:
        key = str(row.get("section_key") or "")
        if not key:
            continue
        section_activity[key]["section_key"] = key
        section_activity[key]["notifications"] += 1
        section_activity[key]["activity"] += 1

    section_titles = {str(row.get("section_key") or ""): row for row in sections}
    section_activity_rows = []
    for key, row in section_activity.items():
        section = section_titles.get(key, {})
        section_activity_rows.append({
            **row,
            "main_title": section.get("main_title", ""),
            "section_title": section.get("section_title", ""),
            "approval_status": section.get("approval_status", ""),
            "status": section.get("status", ""),
        })
    section_activity_rows.sort(key=lambda row: int(row.get("activity") or 0), reverse=True)

    risk_rows = list(stats.get("critical", []))[:25]
    summary = {
        "sections": len(sections),
        "activity_events": len(activity),
        "approval_events": len(approvals),
        "notification_events": len(notifications),
        "export_events": len(exports),
        "version_snapshots": len(versions),
        "stale_workflow_items": len(stale_sections),
        "approved": approval_counter.get("Onaylandı", 0),
        "submitted": approval_counter.get("Onaya Gönderildi", 0),
        "revision": approval_counter.get("Revizyon Gerekli", 0),
        "draft": approval_counter.get("Taslak", 0),
        "readiness_percent": stats.get("summary", {}).get("readiness_percent", 0),
        "approval_percent": stats.get("summary", {}).get("approval_percent", 0),
    }
    return {
        "summary": summary,
        "status_counts": [{"status": key, "count": value} for key, value in status_counter.most_common()],
        "approval_counts": [{"approval_status": key, "count": value} for key, value in approval_counter.most_common()],
        "actor_counts": _count_by(activity + notifications + exports, "actor"),
        "action_counts": _count_by(activity, "action"),
        "section_activity": section_activity_rows[:80],
        "stale_workflow": stale_sections[:80],
        "risk_rows": risk_rows,
        "activity": activity,
        "approvals": approvals,
        "notifications": notifications,
        "exports": exports,
        "versions": versions,
    }
