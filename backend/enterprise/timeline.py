from __future__ import annotations

from typing import Any

from ..db import get_conn, row_to_dict
from ..repositories import EDITOR_ROLE, assert_program_operation_permission, assigned_section_keys
from ..visibility_scope import event_visible_to_user, visible_section_keys


def _activity_section_key(detail: str, known_keys: set[str]) -> str:
    text = str(detail or "").strip()
    if text in known_keys:
        return text
    # Several repository audit entries store the section key as the first token
    # or inside a short human-readable detail. Keep this conservative to avoid
    # accidental false positives.
    for key in known_keys:
        if key and (text.startswith(f"{key} ") or text.startswith(f"{key}:") or f" {key} " in f" {text} "):
            return key
    return ""


def activity_timeline(username: str, program_id: str, limit: int = 200) -> dict[str, Any]:
    role = assert_program_operation_permission(username, program_id, "activity_trail.view")
    events: list[dict[str, Any]] = []
    known_section_keys = visible_section_keys(username, program_id)
    editor_is_narrowed = role == EDITOR_ROLE and bool(assigned_section_keys(username, program_id))
    with get_conn() as conn:
        queries = [
            ("activity", "SELECT id,ts AS created_at,action AS event,detail,actor,program_id,'' AS section_key FROM activity_log WHERE program_id=? OR program_id='' ORDER BY ts DESC LIMIT ?"),
            ("approval", "SELECT id,created_at,status AS event,note AS detail,requested_by AS actor,program_id,section_key FROM section_approvals WHERE program_id=? ORDER BY created_at DESC LIMIT ?"),
            ("notification", "SELECT id,created_at,event_type AS event,subject AS detail,actor,program_id,section_key,status,error FROM notification_events WHERE program_id=? ORDER BY created_at DESC LIMIT ?"),
            ("export", "SELECT id,created_at,export_type AS event,file_name AS detail,actor,program_id,'' AS section_key FROM export_history WHERE program_id=? ORDER BY created_at DESC LIMIT ?"),
            ("version", "SELECT id,saved_at AS created_at,change_summary AS event,'' AS detail,'' AS actor,program_id,section_key FROM section_versions WHERE program_id=? ORDER BY saved_at DESC LIMIT ?"),
        ]
        for source, sql in queries:
            try:
                for row in conn.execute(sql, (program_id, int(limit))).fetchall():
                    item = row_to_dict(row) or {}
                    item["source"] = source
                    if source == "activity" and not item.get("section_key"):
                        item["section_key"] = _activity_section_key(str(item.get("detail", "") or ""), known_section_keys)
                    if source == "export" and editor_is_narrowed and str(item.get("actor", "") or "").lower() != username.lower():
                        continue
                    if event_visible_to_user(username, program_id, item):
                        events.append(item)
            except Exception:
                continue
    events.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
    actors: dict[str, int] = {}
    sources: dict[str, int] = {}
    for event in events:
        actors[str(event.get("actor") or "Sistem")] = actors.get(str(event.get("actor") or "Sistem"), 0) + 1
        sources[str(event.get("source") or "other")] = sources.get(str(event.get("source") or "other"), 0) + 1
    return {"events": events[:int(limit)], "actor_counts": [{"actor": k, "count": v} for k, v in actors.items()], "source_counts": [{"source": k, "count": v} for k, v in sources.items()]}
