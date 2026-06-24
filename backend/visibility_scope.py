from __future__ import annotations

from typing import Any

from .db import get_conn, rows_to_dicts
from .repositories import (
    APPROVER_ROLE,
    EDITOR_ROLE,
    FACULTY_ADMIN_ROLE,
    READONLY_ROLE,
    SUPER_ADMIN_ROLE,
    TENANT_ADMIN_ROLE,
    assert_program_access,
    assigned_section_keys,
    get_program,
    get_program_role,
    get_user,
    list_programs_for_user,
    normalized_role,
)
from .tenancy import DEFAULT_TENANT_ID, user_is_global_admin, user_tenant_id

SCOPE_ADMIN_ROLES = {SUPER_ADMIN_ROLE, TENANT_ADMIN_ROLE, FACULTY_ADMIN_ROLE}
PROGRAM_WIDE_ROLES = {SUPER_ADMIN_ROLE, TENANT_ADMIN_ROLE, FACULTY_ADMIN_ROLE, APPROVER_ROLE, READONLY_ROLE}


def actor_role(username: str, program_id: str | None = None) -> str:
    """Return the user's effective role for global or program scoped checks."""
    user = get_user(username, active_only=True) or {}
    global_role = normalized_role(str(user.get("role", "") or ""), str(user.get("tenant_scope", "") or ""))
    if program_id:
        try:
            return get_program_role(username, program_id)
        except Exception:
            return global_role
    return global_role


def is_scope_admin_role(role: str) -> bool:
    return normalized_role(role) in SCOPE_ADMIN_ROLES


def user_visible_program_ids(username: str) -> list[str]:
    """Programs the user may see, already tenant/faculty/assignment scoped."""
    return [str(row.get("id", "") or "") for row in list_programs_for_user(username) if str(row.get("id", "") or "")]


def user_visible_program_id_set(username: str) -> set[str]:
    return set(user_visible_program_ids(username))


def section_visible_to_user(username: str, program_id: str, section_key: str | None) -> bool:
    """Mirror repository section visibility for cross-module feeds.

    Editors with explicit assigned_sections may see only those sections. Program-wide
    roles keep the program-level view. Empty section_key values represent program
    level events; editors may see them only when they are not narrowed to sections.
    """
    key = str(section_key or "").strip()
    role = assert_program_access(username, program_id)
    if role in PROGRAM_WIDE_ROLES:
        return True
    assigned = assigned_section_keys(username, program_id)
    if not assigned:
        return True
    return bool(key and key in assigned)


def visible_section_keys(username: str, program_id: str) -> set[str]:
    """Section keys visible to the user for filtering timelines and history rows."""
    role = assert_program_access(username, program_id)
    assigned = assigned_section_keys(username, program_id)
    if role == EDITOR_ROLE and assigned:
        return set(assigned)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT section_key FROM sections WHERE program_id=? AND COALESCE(deleted_at,'')=''",
            (program_id,),
        ).fetchall()
    return {str(row["section_key"] or "") for row in rows if str(row["section_key"] or "")}


def event_visible_to_user(username: str, program_id: str, event: dict[str, Any]) -> bool:
    """Central visibility check for program feed rows.

    The rule is intentionally stricter for editors: own activity and assigned-section
    activity are visible, while unassigned section activity is hidden.
    """
    event_program = str(event.get("program_id", "") or "")
    if event_program and event_program != str(program_id):
        return False
    role = assert_program_access(username, program_id)
    actor = str(event.get("actor", "") or "").lower()
    section_key = str(event.get("section_key", "") or "").strip()
    if not event_program:
        return role == SUPER_ADMIN_ROLE or actor == username.lower()
    if role in PROGRAM_WIDE_ROLES:
        return section_visible_to_user(username, program_id, section_key)
    if actor == username.lower():
        return True
    return section_visible_to_user(username, program_id, section_key)


def visible_activity_where(username: str) -> tuple[str, list[Any]]:
    """SQL WHERE fragment for activity_log style tables with a program_id column.

    Super Admin sees all rows. Other roles see rows for programs in their current
    hierarchy/assignments plus their own global actor rows. Global/system rows are
    not tenant-safe unless they are the actor's own rows.
    """
    user = get_user(username, active_only=True) or {}
    role = normalized_role(str(user.get("role", "") or ""), str(user.get("tenant_scope", "") or ""))
    if role == SUPER_ADMIN_ROLE and user_is_global_admin(user):
        return "1=1", []
    ids = user_visible_program_ids(username)
    clauses: list[str] = []
    params: list[Any] = []
    if ids:
        placeholders = ",".join("?" for _ in ids)
        clauses.append(f"program_id IN ({placeholders})")
        params.extend(ids)
    clauses.append("(COALESCE(program_id,'')='' AND LOWER(COALESCE(actor,''))=LOWER(?))")
    params.append(username)
    return "(" + " OR ".join(clauses) + ")", params


def visible_notification_where(username: str) -> tuple[str, list[Any]]:
    """SQL WHERE fragment for notification_events with program_id and actor."""
    return visible_activity_where(username)


def filter_section_rows(username: str, program_id: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = visible_section_keys(username, program_id)
    role = assert_program_access(username, program_id)
    if role != EDITOR_ROLE or not assigned_section_keys(username, program_id):
        return rows
    return [row for row in rows if str(row.get("section_key", "") or "") in keys]
