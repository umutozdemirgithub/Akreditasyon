from __future__ import annotations

import json
from typing import Any

from .db import get_conn, now_iso, rows_to_dicts, transaction
from .repositories import (
    ROLE_OPTIONS,
    APPROVER_ROLE,
    EDITOR_ROLE,
    READONLY_ROLE,
    FACULTY_ADMIN_ROLE,
    UNIT_COORDINATOR_ROLE,
    SUPER_ADMIN_ROLE,
    TENANT_ADMIN_ROLE,
    get_user,
    is_super_admin_user,
    is_tenant_admin_user,
    normalized_role as normalize_role_value,
)

TENANT_DELEGATE_ROLES = [FACULTY_ADMIN_ROLE, UNIT_COORDINATOR_ROLE, EDITOR_ROLE, APPROVER_ROLE, READONLY_ROLE]
FACULTY_DELEGATE_ROLES = [UNIT_COORDINATOR_ROLE, EDITOR_ROLE, APPROVER_ROLE, READONLY_ROLE]
ROLE_LEGACY_LABELS = {
    READONLY_ROLE: ("Denetçi (İzleyici)", "İzleyici", "Denetci"),
    EDITOR_ROLE: ("Editör", "Hazırlayıcı", "Editor"),
}

SECTION_PERMISSION_ACTIONS: list[dict[str, Any]] = [{'action': 'view',
  'label': 'Görür',
  'description': 'Başlığı ve ilişkili özetleri görüntüler.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'action': 'edit_text',
  'label': 'Rapor metni düzenler',
  'description': 'Ana rapor metnini günceller.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'action': 'edit_puko',
  'label': 'PUKÖ düzenler',
  'description': 'Planla, Uygula, Kontrol Et, Önlem Al alanlarını günceller.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'action': 'edit_status',
  'label': 'Durum değiştirir',
  'description': 'Başlık hazırlık durumunu değiştirir.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'action': 'edit_deadline',
  'label': 'Termin düzenler',
  'description': 'Başlık son teslim tarihini düzenler.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'action': 'submit',
  'label': 'Onaya gönderir',
  'description': 'Başlığı onay kuyruğuna gönderir. Operasyonel kural gereği varsayılan olarak yalnızca Editör / Hazırlayıcı rolüne açıktır.',
  'Admin': False,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi': False,
  'Süper Admin': False,
  'Kurum Admin': False,
  'Birim Admin': False},
 {'action': 'approve',
  'label': 'Onaylar',
  'description': 'Başlığı onaylar.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': True,
  'Denetçi': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'action': 'request_revision',
  'label': 'Revizyon ister',
  'description': 'Başlık için revizyon talebi oluşturur.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': True,
  'Denetçi': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'action': 'reopen',
  'label': 'Kilidi/Onayı açar',
  'description': 'Onaylanmış başlığı tekrar taslağa çeker.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': True,
  'Denetçi': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'action': 'evidence_upload',
  'label': 'Kanıt yükler',
  'description': 'Başlığa kanıt dosyası ekler.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'action': 'table_edit',
  'label': 'Tablo düzenler',
  'description': 'Başlığa bağlı tabloyu oluşturur veya günceller.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'action': 'ai_draft',
  'label': 'AI taslak üretir',
  'description': 'Başlık için yerel/kapalı devre AI taslağı alır.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True}]

def _default_for_action(row: dict[str, Any], role: str) -> bool:
    def value_for(target_role: str, fallback: bool = False) -> bool:
        if target_role in row:
            return bool(row.get(target_role))
        for alias in ROLE_LEGACY_LABELS.get(target_role, ()):
            if alias in row:
                return bool(row.get(alias))
        return bool(fallback)

    if role == SUPER_ADMIN_ROLE:
        return value_for(SUPER_ADMIN_ROLE, bool(row.get("Admin", True)))
    if role == TENANT_ADMIN_ROLE:
        return value_for(TENANT_ADMIN_ROLE, bool(row.get("Admin", False)))
    if role == FACULTY_ADMIN_ROLE:
        return value_for(FACULTY_ADMIN_ROLE, bool(row.get("Admin", False)))
    if role == UNIT_COORDINATOR_ROLE:
        return value_for(UNIT_COORDINATOR_ROLE, value_for(FACULTY_ADMIN_ROLE, bool(row.get("Admin", False))))
    return value_for(role, False)


DEFAULT_BY_ACTION: dict[str, dict[str, bool]] = {
    row["action"]: {role: _default_for_action(row, role) for role in ROLE_OPTIONS}
    for row in SECTION_PERMISSION_ACTIONS
}


def _role_map_value(role_map: dict[str, Any], role: str, fallback: Any = False) -> bool | None:
    if role in role_map:
        return bool(role_map.get(role))
    for alias in ROLE_LEGACY_LABELS.get(role, ()):
        if alias in role_map:
            return bool(role_map.get(alias))
    return None if fallback is None else bool(fallback)


def _setting_key(program_id: str) -> str:
    return f"section_permission_policy_json:{program_id}"


def _load_policy(program_id: str) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (_setting_key(program_id),)).fetchone()
    if not row:
        return {}
    try:
        parsed = json.loads(str(row["value"] or "{}"))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _clean_policy(policy: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for section_key, action_map in (policy or {}).items():
        skey = str(section_key or "").strip()
        if not skey or not isinstance(action_map, dict):
            continue
        clean[skey] = {}
        for action, role_map in action_map.items():
            action_key = str(action or "").strip()
            if action_key not in DEFAULT_BY_ACTION or not isinstance(role_map, dict):
                continue
            clean[skey][action_key] = {role: _role_map_value(role_map, role, DEFAULT_BY_ACTION[action_key].get(role, False)) for role in ROLE_OPTIONS}
    return clean


def section_permission_allows(program_id: str, section_key: str, role: str, action: str) -> bool:
    normalized = normalize_role_value(role)
    action_key = str(action or "").strip()
    if action_key not in DEFAULT_BY_ACTION:
        return False
    if normalized == SUPER_ADMIN_ROLE:
        default_value = True
    else:
        default_value = DEFAULT_BY_ACTION[action_key].get(normalized, False)
    policy = _load_policy(program_id)
    override_map = ((policy.get(str(section_key), {}) or {}).get(action_key, {}) or {})
    override = _role_map_value(override_map, normalized, None) if isinstance(override_map, dict) else None
    return bool(default_value if override is None else override)


def section_permission_payload(program_id: str) -> dict[str, Any]:
    policy = _load_policy(program_id)
    with get_conn() as conn:
        section_rows = rows_to_dicts(conn.execute(
            """SELECT section_key, main_title, section_title, sort_order, approval_status, status
               FROM sections
               WHERE program_id=? AND COALESCE(deleted_at,'')=''
               ORDER BY sort_order""",
            (program_id,),
        ).fetchall())
    rows: list[dict[str, Any]] = []
    for section in section_rows:
        skey = str(section.get("section_key", "") or "")
        for action_row in SECTION_PERMISSION_ACTIONS:
            action = action_row["action"]
            role_values = {
                role: _role_map_value(((policy.get(skey, {}) or {}).get(action, {}) or {}), role, DEFAULT_BY_ACTION[action].get(role, False))
                for role in ROLE_OPTIONS
            }
            rows.append({
                "section_key": skey,
                "main_title": section.get("main_title", ""),
                "section_title": section.get("section_title", ""),
                "sort_order": section.get("sort_order", 0),
                "status": section.get("status", ""),
                "approval_status": section.get("approval_status", ""),
                "action": action,
                "label": action_row["label"],
                "description": action_row["description"],
                **role_values,
            })
    return {"roles": ROLE_OPTIONS, "actions": SECTION_PERMISSION_ACTIONS, "rows": rows, "default_rows": rows, "updated_at": now_iso()}


def update_section_permission_policy(program_id: str, rows: list[dict[str, Any]], actor_username: str | None = None) -> dict[str, Any]:
    actor = get_user(actor_username, active_only=True) if actor_username else None
    actor_role = normalize_role_value(str((actor or {}).get("role", "")), str((actor or {}).get("tenant_scope", "") or ""))
    tenant_admin = is_tenant_admin_user(actor)
    faculty_admin = actor_role == FACULTY_ADMIN_ROLE
    current_payload = section_permission_payload(program_id) if (tenant_admin or faculty_admin) else None
    current = {(r["section_key"], r["action"]): r for r in (current_payload or {}).get("rows", [])}
    next_policy: dict[str, Any] = {}
    for row in rows or []:
        skey = str(row.get("section_key", "") or "").strip()
        action = str(row.get("action", "") or "").strip()
        if not skey or action not in DEFAULT_BY_ACTION:
            continue
        role_values: dict[str, bool] = {}
        gate_row = current.get((skey, action), {}) if (tenant_admin or faculty_admin) else {}
        for role in ROLE_OPTIONS:
            if tenant_admin and role not in TENANT_DELEGATE_ROLES:
                role_values[role] = bool(gate_row.get(role, DEFAULT_BY_ACTION[action].get(role, False)))
                continue
            if faculty_admin and role not in FACULTY_DELEGATE_ROLES:
                role_values[role] = bool(gate_row.get(role, DEFAULT_BY_ACTION[action].get(role, False)))
                continue
            desired = _role_map_value(row, role, DEFAULT_BY_ACTION[action].get(role, False))
            if tenant_admin and desired and not bool(gate_row.get(TENANT_ADMIN_ROLE, False)):
                raise PermissionError("Kurum Admin kendisine kapalı başlık/işlem iznini başka role açamaz.")
            if faculty_admin and desired and not bool(gate_row.get(FACULTY_ADMIN_ROLE, False)):
                raise PermissionError("Birim Admin kendisine kapalı başlık/işlem iznini başka role açamaz.")
            role_values[role] = desired
        next_policy.setdefault(skey, {})[action] = role_values
    clean = _clean_policy(next_policy)
    with transaction() as conn:
        conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (_setting_key(program_id), json.dumps(clean, ensure_ascii=False)))
    return section_permission_payload(program_id)
