from __future__ import annotations

import json
import math
import re
import unicodedata
import uuid
from datetime import datetime, timedelta
from difflib import unified_diff
from io import BytesIO
from pathlib import Path
from typing import Any

from docx import Document

from .accreditation import accreditation_profile_meta, infer_accreditation_profile_by_rule, normalize_accreditation_profile, profile_section_guide, profile_section_template
from .config import EVIDENCE_DIR, ORG_STORAGE_DIR, SQLITE_PATH, MEDEK_DATABASE_URL, MEDEK_DB_BACKEND, LOGIN_LOCK_MINUTES, LOGIN_MAX_FAILED_ATTEMPTS
from .db import get_conn, now_iso, row_to_dict, rows_to_dicts, transaction
from .tenancy import DEFAULT_TENANT_ID, GLOBAL_SCOPE, TENANT_SCOPE, can_access_tenant, ensure_program_tenant_access, ensure_tenant_access, program_tenant_id, tenant_filter_sql, user_is_global_admin, user_tenant_id
from .file_security import safe_stored_path, slugify, validate_evidence_bytes
from .storage_paths import (
    append_activity_log_snapshot,
    evidence_section_dir,
    write_all_sections_archive,
    write_approval_snapshot,
    write_program_manifest,
    write_section_text_archive,
    write_table_snapshot,
    timestamp_slug,
)
from .security import hash_password, verify_password, validate_password_strength


READONLY_ROLE = "Denetçi"
EDITOR_ROLE = "Editör / Hazırlayıcı"
APPROVER_ROLE = "Onaylayıcı"
TENANT_ADMIN_ROLE = "Kurum Admin"
FACULTY_ADMIN_ROLE = "Birim Admin"
UNIT_COORDINATOR_ROLE = "Birim Koordinatörü"
SUPER_ADMIN_ROLE = "Süper Admin"
LEGACY_ADMIN_ROLE = "Admin"
ADMIN_ROLE = SUPER_ADMIN_ROLE
ROLE_OPTIONS = [SUPER_ADMIN_ROLE, TENANT_ADMIN_ROLE, FACULTY_ADMIN_ROLE, UNIT_COORDINATOR_ROLE, EDITOR_ROLE, APPROVER_ROLE, READONLY_ROLE]
ADMIN_ROLE_OPTIONS = {SUPER_ADMIN_ROLE, TENANT_ADMIN_ROLE, LEGACY_ADMIN_ROLE}
SUPER_ADMIN_ROLE_OPTIONS = {SUPER_ADMIN_ROLE, LEGACY_ADMIN_ROLE}
DELEGATABLE_ROLES_BY_TENANT_ADMIN = {FACULTY_ADMIN_ROLE, UNIT_COORDINATOR_ROLE, EDITOR_ROLE, APPROVER_ROLE, READONLY_ROLE}
DELEGATABLE_ROLES_BY_FACULTY_ADMIN = {UNIT_COORDINATOR_ROLE, EDITOR_ROLE, APPROVER_ROLE, READONLY_ROLE}
ROLE_RANK = {
    SUPER_ADMIN_ROLE: 0,
    TENANT_ADMIN_ROLE: 10,
    FACULTY_ADMIN_ROLE: 20,
    UNIT_COORDINATOR_ROLE: 30,
    EDITOR_ROLE: 40,
    APPROVER_ROLE: 50,
    READONLY_ROLE: 60,
}


def normalized_role(role: str, tenant_scope: str = "") -> str:
    value = str(role or READONLY_ROLE).strip()
    aliases = {
        LEGACY_ADMIN_ROLE: SUPER_ADMIN_ROLE if str(tenant_scope or "").strip() == GLOBAL_SCOPE else TENANT_ADMIN_ROLE,
        "Fakülte/MYO Admin": FACULTY_ADMIN_ROLE,
        "Birim/Fakülte Admin": FACULTY_ADMIN_ROLE,
        "Birim Koordinatoru": UNIT_COORDINATOR_ROLE,
        "Birim Koordinatörü": UNIT_COORDINATOR_ROLE,
        "Editör": EDITOR_ROLE,
        "Hazırlayıcı": EDITOR_ROLE,
        "Editor": EDITOR_ROLE,
        "İzleyici": READONLY_ROLE,
        "Denetçi (İzleyici)": READONLY_ROLE,
        "Denetçi": READONLY_ROLE,
        "Denetci": READONLY_ROLE,
    }
    value = aliases.get(value, value)
    return value if value in ROLE_OPTIONS else READONLY_ROLE



def role_rank(role: str, tenant_scope: str = "") -> int:
    """Return hierarchical rank; lower numbers are more privileged."""
    return ROLE_RANK.get(normalized_role(role, tenant_scope), ROLE_RANK[READONLY_ROLE])


def role_same_or_lower(target_role: str, actor_role: str, actor_scope: str = "") -> bool:
    """Whether target_role is the actor's own level or below it."""
    return role_rank(target_role) >= role_rank(actor_role, actor_scope)


def visible_roles_for_actor(actor: dict[str, Any] | None) -> set[str]:
    role = normalized_role(str((actor or {}).get("role", READONLY_ROLE)), str((actor or {}).get("tenant_scope", "") or ""))
    if role == SUPER_ADMIN_ROLE and is_super_admin_user(actor):
        return set(ROLE_OPTIONS)
    return {candidate for candidate in ROLE_OPTIONS if role_same_or_lower(candidate, role)}


def delegatable_roles_for_actor(actor: dict[str, Any] | None) -> set[str]:
    role = normalized_role(str((actor or {}).get("role", READONLY_ROLE)), str((actor or {}).get("tenant_scope", "") or ""))
    if role == SUPER_ADMIN_ROLE and is_super_admin_user(actor):
        return set(ROLE_OPTIONS) - {SUPER_ADMIN_ROLE}
    if role == TENANT_ADMIN_ROLE:
        return set(DELEGATABLE_ROLES_BY_TENANT_ADMIN)
    if role == FACULTY_ADMIN_ROLE:
        return set(DELEGATABLE_ROLES_BY_FACULTY_ADMIN)
    return set()


def _norm_scope_text(value: Any) -> str:
    return str(value or "").strip().casefold()


def _program_faculty_value(program: dict[str, Any] | None) -> str:
    return str((program or {}).get("school_name") or (program or {}).get("faculty_name") or "").strip()


def _user_faculty_value(user: dict[str, Any] | None) -> str:
    return str((user or {}).get("faculty_name") or "").strip()


def _faculty_scope_matches(user: dict[str, Any] | None, program: dict[str, Any] | None) -> bool:
    actor_faculty = _norm_scope_text(_user_faculty_value(user))
    program_faculty = _norm_scope_text(_program_faculty_value(program))
    return bool(actor_faculty and program_faculty and actor_faculty == program_faculty)

def is_admin_role(role: str) -> bool:
    return normalized_role(role) in {SUPER_ADMIN_ROLE, TENANT_ADMIN_ROLE}


def is_super_admin_user(user: dict[str, Any] | None) -> bool:
    if not user:
        return False
    role = str(user.get("role", ""))
    scope = str(user.get("tenant_scope", "") or "")
    return role in SUPER_ADMIN_ROLE_OPTIONS or (normalized_role(role, scope) == SUPER_ADMIN_ROLE and scope == GLOBAL_SCOPE)


def is_tenant_admin_user(user: dict[str, Any] | None) -> bool:
    if not user:
        return False
    return normalized_role(str(user.get("role", "")), str(user.get("tenant_scope", "") or "")) == TENANT_ADMIN_ROLE


def actor_has_operation_permission(user: dict[str, Any] | None, permission: str) -> bool:
    if is_super_admin_user(user):
        return True
    role = normalized_role(str((user or {}).get("role", READONLY_ROLE)), str((user or {}).get("tenant_scope", "") or ""))
    try:
        from .enterprise.matrix import role_permission_allowed
        return role_permission_allowed(role, permission, str((user or {}).get("tenant_id", DEFAULT_TENANT_ID) or DEFAULT_TENANT_ID))
    except Exception:
        # Safe fallback for early startup/tests: tenant admin can use delegated
        # user/program controls, but not global tenant management.
        if role == TENANT_ADMIN_ROLE:
            return permission in {"user.view", "user.manage", "user.login_attempts.view", "program.view", "program.create", "program.clone", "program.assign_users", "permission.manage", "sidebar.manage"}
        return False


def _can_use_management_operation_matrix(user: dict[str, Any] | None) -> bool:
    if not user:
        return False
    role = normalized_role(str(user.get("role", "")), str(user.get("tenant_scope", "") or ""))
    return is_admin_role(role) or role == FACULTY_ADMIN_ROLE


def assert_operation_permission(username: str, permission: str) -> dict[str, Any]:
    user = get_user(username, active_only=True)
    if not _can_use_management_operation_matrix(user):
        raise PermissionError("Bu işlemi yalnızca yetkili yönetim rolü yapabilir.")
    if not actor_has_operation_permission(user, permission):
        raise PermissionError("Bu işlem için Yetki Matrisi izniniz yok.")
    return user or {}


def assert_any_operation_permission(username: str, permissions: list[str] | set[str] | tuple[str, ...]) -> dict[str, Any]:
    user = get_user(username, active_only=True)
    if not _can_use_management_operation_matrix(user):
        raise PermissionError("Bu işlemi yalnızca yetkili yönetim rolü yapabilir.")
    if not any(actor_has_operation_permission(user, permission) for permission in permissions):
        raise PermissionError("Bu işlem için Yetki Matrisi izniniz yok.")
    return user or {}


def program_operation_permission_allowed(username: str, program_id: str, permission: str) -> bool:
    user = get_user(username, active_only=True)
    if is_super_admin_user(user):
        return True
    try:
        effective_role = get_program_role(username, program_id)
        from .enterprise.matrix import role_permission_allowed
        return role_permission_allowed(effective_role, permission, program_tenant_id(program_id))
    except Exception:
        return False


def assert_program_operation_permission(username: str, program_id: str, permission: str) -> str:
    role = assert_program_access(username, program_id)
    if not program_operation_permission_allowed(username, program_id, permission):
        raise PermissionError("Bu ekran/işlem için Yetki Matrisi izniniz yok.")
    return role


APPROVED = "Onaylandı"
SUBMITTED = "Onaya Gönderildi"
REVISION = "Revizyon Gerekli"
COMPLETED = "Tamamlandı"
READY = "Taslak Hazır"
STATUS_OPTIONS = {"Başlamadı", "Devam Ediyor", READY, REVISION, COMPLETED}
_PROFILE_SCHEMA_READY = False
EPDAD_REPORT_GROUP_TITLE = "B. Standart Alanları (Başlangıç, Süreç ve Ürün Standartları)"


def _ensure_accreditation_profile_column() -> None:
    global _PROFILE_SCHEMA_READY
    if _PROFILE_SCHEMA_READY:
        return
    try:
        with transaction() as conn:
            columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(programs)").fetchall()}
            if "accreditation_profile" not in columns:
                conn.execute("ALTER TABLE programs ADD COLUMN accreditation_profile TEXT NOT NULL DEFAULT 'MEDEK'")
    except Exception:
        return
    _PROFILE_SCHEMA_READY = True

REPORT_MAIN_TITLE_ALIASES = {
    "A. Programa İlişkin Genel Bilgiler": "Programa İlişkin Genel Bilgiler",
    "Ölçüt 2. Program Amaçları": "Ölçüt 2. Program Eğitim Amaçları",
    "Ölçüt 8. Yönetim Yapısı": "Ölçüt 8. Yönetim ve İdari Birimlerin Yapısı",
    "Ölçüt 9. Disipline Özgü Ölçütler": "Ölçüt 9. Programa Özgü Ölçütler",
}

REPORT_MAIN_TITLE_ORDER = {
    "Programa İlişkin Genel Bilgiler": 10,
    "Ölçüt 1. Öğrenciler": 20,
    "Ölçüt 2. Program Eğitim Amaçları": 30,
    "Ölçüt 3. Program Çıktıları": 40,
    "Ölçüt 4. Sürekli İyileştirme": 50,
    "Ölçüt 5. Eğitim Planı": 60,
    "Ölçüt 6. Öğretim Kadrosu": 70,
    "Ölçüt 7. Altyapı": 80,
    "Ölçüt 8. Yönetim ve İdari Birimlerin Yapısı": 90,
    "Ölçüt 9. Programa Özgü Ölçütler": 100,
    "Ek I. Programa İlişkin Ek Bilgiler": 110,
    "Ek II. Kurum Profili": 120,
}



def _json_safe(value: Any, *, _depth: int = 0) -> Any:
    """Return a value that FastAPI/Starlette can serialize as strict JSON.

    Report preview payloads aggregate section text, evidence metadata, table
    rows and AI/report-quality outputs. Imported spreadsheets can carry NaN or
    Infinity values, and some runtime paths can produce bytes/Path/datetime-like
    objects. Starlette's JSONResponse rejects non-finite floats, which used to
    surface in the UI as a bare "Internal Server Error" on the preview screen.
    """
    if _depth > 20:
        return str(value)
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v, _depth=_depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item, _depth=_depth + 1) for item in value]
    return str(value)


def json_safe_payload(payload: Any) -> Any:
    """Public repository helper for API endpoints that return composed JSON."""
    return _json_safe(payload)

REPORT_GROUP_TITLE_ORDER = {
    "A. Programa İlişkin Genel Bilgiler": 10,
    "B. Değerlendirme Özeti": 20,
    EPDAD_REPORT_GROUP_TITLE: 20,
    "EK I – PROGRAMA İLİŞKİN EK BİLGİLER": 30,
    "EK II – KURUM PROFİLİ": 40,
}


def report_main_title(title: str) -> str:
    return REPORT_MAIN_TITLE_ALIASES.get(str(title or "").strip(), str(title or "").strip())


def report_group_title(title: str) -> str:
    main_title = report_main_title(title)
    if main_title == "Programa İlişkin Genel Bilgiler":
        return "A. Programa İlişkin Genel Bilgiler"
    if main_title.startswith("Ölçüt "):
        return "B. Değerlendirme Özeti"
    if main_title.startswith("ES "):
        return EPDAD_REPORT_GROUP_TITLE
    if main_title == "Ek I. Programa İlişkin Ek Bilgiler":
        return "EK I – PROGRAMA İLİŞKİN EK BİLGİLER"
    if main_title == "Ek II. Kurum Profili":
        return "EK II – KURUM PROFİLİ"
    return main_title


def report_subgroup_title(title: str) -> str:
    main_title = report_main_title(title)
    return main_title if main_title.startswith(("Ölçüt ", "ES ")) else ""


def _natural_section_key(value: str) -> tuple[Any, ...]:
    parts = re.split(r"(\d+)", str(value or ""))
    return tuple(int(part) if part.isdigit() else part.casefold() for part in parts if part != "")


def _main_title_order(main_title: str) -> int:
    if main_title in REPORT_MAIN_TITLE_ORDER:
        return REPORT_MAIN_TITLE_ORDER[main_title]
    measure = re.match(r"Ölçüt\s+(\d+)", main_title, flags=re.IGNORECASE)
    if measure:
        return 10 + int(measure.group(1)) * 10
    epdad_standard = re.match(r"ES\s+(\d+)", main_title, flags=re.IGNORECASE)
    if epdad_standard:
        return 10 + int(epdad_standard.group(1)) * 10
    return 900


def _section_sort_value(row: dict[str, Any]) -> tuple[Any, ...]:
    main_title = report_main_title(str(row.get("main_title", "")))
    try:
        sort_order = int(row.get("sort_order") or 0)
    except Exception:
        sort_order = 0
    return (
        _main_title_order(main_title),
        main_title.casefold(),
        sort_order,
        _natural_section_key(str(row.get("section_key", ""))),
    )


def normalize_section_rows(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for section in sections:
        item = dict(section)
        raw_main_title = str(item.get("main_title", "") or "")
        normalized_main_title = report_main_title(raw_main_title)
        if normalized_main_title != raw_main_title:
            item["raw_main_title"] = raw_main_title
        item["main_title"] = normalized_main_title
        item["report_group_title"] = report_group_title(normalized_main_title)
        item["report_subgroup_title"] = report_subgroup_title(normalized_main_title)
        normalized.append(item)
    return sorted(normalized, key=_section_sort_value)


def get_user(username: str, active_only: bool = True) -> dict[str, Any] | None:
    with get_conn() as conn:
        if active_only:
            row = conn.execute("SELECT * FROM users WHERE username=? AND is_active=1", (username.strip(),)).fetchone()
        else:
            row = conn.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
    return row_to_dict(row)


def _parse_iso_datetime(value: str) -> datetime | None:
    value = str(value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value[:19], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    clean_username = username.strip()
    user = get_user(clean_username)
    if not user:
        record_login_attempt(clean_username, False, "user missing or inactive")
        return None

    locked_until = _parse_iso_datetime(str(user.get("locked_until", "") or ""))
    if locked_until and locked_until > datetime.now():
        record_login_attempt(clean_username, False, "account locked")
        return None

    if verify_password(password, str(user.get("password_hash", ""))):
        with transaction() as conn:
            conn.execute(
                "UPDATE users SET failed_attempts=0, locked_until='', last_login=?, updated_at=? WHERE username=?",
                (now_iso(), now_iso(), clean_username),
            )
        record_login_attempt(clean_username, True, "success")
        log_activity("Giriş", clean_username, clean_username, "")
        fresh_user = get_user(clean_username)
        return fresh_user or user

    failed_attempts = int(user.get("failed_attempts", 0) or 0) + 1
    lock_value = ""
    note = "bad password"
    if failed_attempts >= LOGIN_MAX_FAILED_ATTEMPTS:
        lock_value = (datetime.now() + timedelta(minutes=LOGIN_LOCK_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
        note = f"bad password; account locked for {LOGIN_LOCK_MINUTES} minutes"
    with transaction() as conn:
        conn.execute(
            "UPDATE users SET failed_attempts=?, locked_until=?, updated_at=? WHERE username=?",
            (failed_attempts, lock_value, now_iso(), clean_username),
        )
    record_login_attempt(clean_username, False, note)
    return None


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "username": user.get("username", ""),
        "role": normalized_role(str(user.get("role", READONLY_ROLE)), str(user.get("tenant_scope", "") or "")),
        "full_name": user.get("full_name", "") or user.get("username", ""),
        "email": user.get("email", "") or "",
        "academic_status": user.get("academic_status", "") or "",
        "tenant_id": user.get("tenant_id", DEFAULT_TENANT_ID) or DEFAULT_TENANT_ID,
        "tenant_scope": user.get("tenant_scope", TENANT_SCOPE) or TENANT_SCOPE,
        "faculty_name": user.get("faculty_name", "") or "",
        "must_change_password": bool(user.get("must_change_password", 0)),
    }
    try:
        from .appearance import appearance_for_user
        payload["appearance"] = appearance_for_user(str(payload["username"]))
    except Exception:
        payload["appearance"] = {"tenant_id": payload["tenant_id"], "package": {"id": "corporate_blue", "name": "Kurumsal Mavi", "mode": "light"}}
    return payload


def change_own_password(username: str, current_password: str, new_password: str) -> dict[str, Any]:
    clean_username = str(username or "").strip()
    user = get_user(clean_username, active_only=True)
    if not user:
        raise PermissionError("Kullanıcı bulunamadı veya aktif değil.")
    if not verify_password(str(current_password or ""), str(user.get("password_hash", ""))):
        record_login_attempt(clean_username, False, "change-password bad current password")
        raise ValueError("Mevcut şifre hatalı.")
    if verify_password(str(new_password or ""), str(user.get("password_hash", ""))):
        raise ValueError("Yeni şifre mevcut şifreyle aynı olamaz.")
    validate_password_strength(str(new_password or ""))
    with transaction() as conn:
        conn.execute(
            """UPDATE users
               SET password_hash=?, must_change_password=0, failed_attempts=0, locked_until='',
                   password_changed_at=?, token_version=COALESCE(token_version, 1) + 1, updated_at=?
               WHERE username=?""",
            (hash_password(str(new_password)), now_iso(), now_iso(), clean_username),
        )
    log_activity("Şifre değiştirildi", "Kullanıcı kendi şifresini değiştirdi", clean_username, "")
    fresh_user = get_user(clean_username, active_only=True)
    if not fresh_user:
        raise PermissionError("Şifre değiştirildi ancak kullanıcı yeniden okunamadı.")
    return fresh_user


def assert_admin(username: str) -> None:
    user = get_user(username, active_only=True)
    if not user or not is_admin_role(str(user.get("role", ""))):
        raise PermissionError("Bu işlemi yalnızca Süper Admin veya Kurum Admin yapabilir.")


def list_users_admin(username: str, include_deleted: bool = False) -> list[dict[str, Any]]:
    # Program Bazlı Kullanıcı ve Rol Atama sekmesi, tam kullanıcı yönetimi kapalı olsa bile
    # aynı kurum/birim kapsamındaki kullanıcı seçim listesine ihtiyaç duyar.
    actor = assert_any_operation_permission(username, {"user.view", "program.assign_users"})
    actor_role = normalized_role(str(actor.get("role", READONLY_ROLE)), str(actor.get("tenant_scope", "") or ""))
    actor_faculty = _user_faculty_value(actor)
    where_parts = []
    params: list[Any] = []
    if not include_deleted:
        where_parts.append("COALESCE(u.deleted_at,'')=''")
    if not user_is_global_admin(actor):
        where_parts.append("COALESCE(u.tenant_id, ?) = ?")
        params.extend([DEFAULT_TENANT_ID, user_tenant_id(actor)])
        if actor_role == TENANT_ADMIN_ROLE:
            # Kurum Admin ekranı kurum dışına çıkamaz. created_by yeni kayıtlarda
            # izlenir; eski kurulumlardan gelen boş created_by kayıtları geriye
            # dönük uyumluluk için kurum içinde görünür kalır.
            where_parts.append("(u.username=? OR COALESCE(u.created_by,'') IN ('', ?))")
            params.extend([username, username])
        elif actor_role == FACULTY_ADMIN_ROLE:
            # Birim Admin yalnız kendi birimi ve kendi altında çalışan rolleri görür.
            # faculty_name boşsa program bazlı atama kayıtları kapsamı belirler.
            where_parts.append(
                """(u.username=? OR COALESCE(u.faculty_name,'')=? OR EXISTS (
                       SELECT 1 FROM program_users pu_actor
                       JOIN program_users pu_target ON pu_target.program_id=pu_actor.program_id
                       WHERE pu_actor.username=? AND pu_actor.is_active=1 AND COALESCE(pu_actor.deleted_at,'')=''
                         AND pu_target.username=u.username AND pu_target.is_active=1 AND COALESCE(pu_target.deleted_at,'')=''
                   ))"""
            )
            params.extend([username, actor_faculty, username])
    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT u.username, u.role, u.tenant_id, COALESCE(t.name, 'Ana Kurum') AS tenant_name,
                      u.tenant_scope, u.faculty_name, u.full_name, u.email, u.academic_status, u.is_active,
                      u.must_change_password, u.failed_attempts, u.locked_until, u.last_login, u.created_at, u.updated_at,
                      u.deleted_at, u.deleted_by, u.created_by
               FROM users u
               LEFT JOIN tenants t ON t.id=COALESCE(u.tenant_id, ?)
               {where_sql}
               ORDER BY t.name, u.role, u.username""",
            (DEFAULT_TENANT_ID, *params),
        ).fetchall()
    visible_roles = visible_roles_for_actor(actor)
    result = []
    for row in rows_to_dicts(rows):
        row_role = normalized_role(str(row.get("role", READONLY_ROLE)), str(row.get("tenant_scope", "") or ""))
        if row_role in visible_roles:
            row["role"] = row_role
            result.append(row)
    return result


def upsert_user_admin(username: str, payload: dict[str, Any]) -> dict[str, Any]:
    actor = assert_operation_permission(username, "user.manage")
    target_username = str(payload.get("username", "") or "").strip()
    role = str(payload.get("role", "") or "").strip()
    if not target_username:
        raise ValueError("Kullanıcı adı boş olamaz.")
    role = normalized_role(role, str(payload.get("tenant_scope", "") or ""))
    if role not in ROLE_OPTIONS:
        raise ValueError("Geçersiz rol.")
    requested_tenant_id = str(payload.get("tenant_id", "") or user_tenant_id(actor)).strip() or DEFAULT_TENANT_ID
    ensure_tenant_access(username, requested_tenant_id)
    requested_scope = str(payload.get("tenant_scope", TENANT_SCOPE) or TENANT_SCOPE).strip()
    if requested_scope not in {GLOBAL_SCOPE, TENANT_SCOPE}:
        requested_scope = TENANT_SCOPE
    if requested_scope == GLOBAL_SCOPE and not user_is_global_admin(actor):
        raise PermissionError("Global tenant kapsamı yalnızca Süper Admin tarafından verilebilir.")
    actor_role = normalized_role(str(actor.get("role", READONLY_ROLE)), str(actor.get("tenant_scope", "") or ""))
    allowed_roles = delegatable_roles_for_actor(actor)
    if not user_is_global_admin(actor) and role not in allowed_roles:
        if actor_role == TENANT_ADMIN_ROLE:
            raise PermissionError("Kurum Admin yalnızca kendi kurumundaki Birim Admin, Birim Koordinatörü, Editör / Hazırlayıcı, Onaylayıcı ve Denetçi rollerini yönetebilir.")
        if actor_role == FACULTY_ADMIN_ROLE:
            raise PermissionError("Birim Admin yalnızca kendi birimindeki Birim Koordinatörü, Editör / Hazırlayıcı, Onaylayıcı ve Denetçi rollerini yönetebilir.")
        raise PermissionError("Bu rolü atama yetkiniz yok.")
    if actor_role == FACULTY_ADMIN_ROLE:
        requested_tenant_id = user_tenant_id(actor)
        actor_faculty = _user_faculty_value(actor)
        if not actor_faculty:
            raise PermissionError("Birim Admin hesabının fakülte kapsamı tanımlı değil.")
        faculty_name = str(payload.get("faculty_name", "") or actor_faculty)
        if _norm_scope_text(faculty_name) != _norm_scope_text(actor_faculty):
            raise PermissionError("Birim Admin yalnızca kendi birimindeki kullanıcıları yönetebilir.")
        payload = {**payload, "tenant_id": requested_tenant_id, "tenant_scope": TENANT_SCOPE, "faculty_name": actor_faculty}
    if role == SUPER_ADMIN_ROLE:
        if not user_is_global_admin(actor):
            raise PermissionError("Süper Admin rolünü yalnızca Süper Admin verebilir.")
        requested_scope = GLOBAL_SCOPE
    else:
        requested_scope = TENANT_SCOPE
    password = str(payload.get("password", "") or "")
    if password:
        validate_password_strength(password)
    full_name = str(payload.get("full_name", "") or "")
    email = str(payload.get("email", "") or "")
    academic_status = str(payload.get("academic_status", "") or "")
    faculty_name = str(payload.get("faculty_name", "") or "")
    is_active = 1 if bool(payload.get("is_active", True)) else 0
    with transaction() as conn:
        exists = conn.execute("SELECT username, role, academic_status, is_active, tenant_id, tenant_scope, faculty_name FROM users WHERE username=?", (target_username,)).fetchone()
        if exists and not can_access_tenant(username, str(exists["tenant_id"] or DEFAULT_TENANT_ID)):
            raise PermissionError("Başka kuruma ait kullanıcıyı güncelleme yetkiniz yok.")
        if exists:
            existing_role = normalized_role(str(exists["role"] or READONLY_ROLE), str(exists["tenant_scope"] or ""))
            if not user_is_global_admin(actor) and not role_same_or_lower(existing_role, actor_role):
                raise PermissionError("Kendi rütbenizin üzerindeki kullanıcıyı değiştiremezsiniz.")
            if actor_role == FACULTY_ADMIN_ROLE and _norm_scope_text(str(exists["faculty_name"] or "")) not in {_norm_scope_text(faculty_name), ""}:
                raise PermissionError("Birim Admin başka birimin kullanıcısını değiştiremez.")
        if exists:
            if password:
                conn.execute(
                    """UPDATE users
                       SET password_hash=?, role=?, tenant_id=?, tenant_scope=?, faculty_name=?, full_name=?, email=?, academic_status=?,
                           is_active=?, must_change_password=1, failed_attempts=0, locked_until='',
                           password_changed_at=?, token_version=COALESCE(token_version, 1) + 1, updated_at=?,
                           deleted_at='', deleted_by=''
                       WHERE username=?""",
                    (hash_password(password), role, requested_tenant_id, requested_scope, faculty_name, full_name, email, academic_status, is_active, now_iso(), now_iso(), target_username),
                )
            else:
                previous = exists
                authorization_changed = bool(
                    previous
                    and (
                        str(previous["role"] or "") != role
                        or str(previous["academic_status"] or "") != academic_status
                        or int(previous["is_active"] or 0) != is_active
                        or str(previous["tenant_id"] or DEFAULT_TENANT_ID) != requested_tenant_id
                        or str(previous["tenant_scope"] or TENANT_SCOPE) != requested_scope
                        or str(previous["faculty_name"] or "") != faculty_name
                    )
                )
                conn.execute(
                    """UPDATE users
                       SET role=?, tenant_id=?, tenant_scope=?, faculty_name=?, full_name=?, email=?, academic_status=?, is_active=?,
                           token_version=CASE WHEN ? THEN COALESCE(token_version, 1) + 1 ELSE COALESCE(token_version, 1) END,
                           updated_at=?, deleted_at='', deleted_by=''
                       WHERE username=?""",
                    (role, requested_tenant_id, requested_scope, faculty_name, full_name, email, academic_status, is_active, 1 if authorization_changed else 0, now_iso(), target_username),
                )
        else:
            if not password:
                raise ValueError("Yeni kullanıcı için şifre gerekli.")
            conn.execute(
                """INSERT INTO users(username,password_hash,role,tenant_id,tenant_scope,faculty_name,full_name,email,academic_status,is_active,must_change_password,created_at,password_changed_at,token_version,updated_at,deleted_at,deleted_by,created_by)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (target_username, hash_password(password), role, requested_tenant_id, requested_scope, faculty_name, full_name, email, academic_status, is_active, 1, now_iso(), now_iso(), 1, now_iso(), '', '', username),
            )
    log_activity("Kullanıcı kaydedildi", f"{target_username} -> {role} / {requested_tenant_id}", username, "")
    user = get_user(target_username, active_only=False) or {}
    return {
        "username": user.get("username", target_username),
        "role": user.get("role", role),
        "tenant_id": user.get("tenant_id", requested_tenant_id),
        "tenant_scope": user.get("tenant_scope", requested_scope),
        "faculty_name": user.get("faculty_name", faculty_name),
        "full_name": user.get("full_name", ""),
        "email": user.get("email", ""),
        "academic_status": user.get("academic_status", ""),
        "is_active": bool(user.get("is_active", is_active)),
        "must_change_password": bool(user.get("must_change_password", 1)),
    }



def delete_user_admin(username: str, target_username: str) -> dict[str, Any]:
    actor = assert_operation_permission(username, "user.manage")
    target_username = str(target_username or "").strip()
    if not target_username:
        raise ValueError("Silinecek kullanıcı belirtilmedi.")
    if target_username == username:
        raise ValueError("Kendi aktif oturum kullanıcınızı silemezsiniz. Önce başka bir admin hesabıyla giriş yapın.")
    with transaction() as conn:
        target = conn.execute("SELECT username, role, is_active, tenant_id FROM users WHERE username=?", (target_username,)).fetchone()
        if not target:
            raise KeyError(target_username)
        if not can_access_tenant(username, str(target["tenant_id"] or DEFAULT_TENANT_ID)):
            raise PermissionError("Başka kuruma ait kullanıcıyı arşivleme yetkiniz yok.")
        actor_role = normalized_role(str(actor.get("role", READONLY_ROLE)), str(actor.get("tenant_scope", "") or ""))
        target_role = normalized_role(str(target["role"] or READONLY_ROLE), "")
        if not user_is_global_admin(actor) and not role_same_or_lower(target_role, actor_role):
            raise PermissionError("Kendi rütbenizin üzerindeki kullanıcıyı arşivleyemezsiniz.")
        if actor_role == FACULTY_ADMIN_ROLE:
            target_user = row_to_dict(target)
            target_full = conn.execute("SELECT faculty_name FROM users WHERE username=?", (target_username,)).fetchone()
            if target_full and _norm_scope_text(target_full["faculty_name"] or "") not in {_norm_scope_text(_user_faculty_value(actor)), ""}:
                raise PermissionError("Birim Admin başka birimin kullanıcısını arşivleyemez.")
        if str(target["role"]) in {SUPER_ADMIN_ROLE, LEGACY_ADMIN_ROLE} and int(target["is_active"] or 0) == 1:
            active_admins = conn.execute(
                "SELECT COUNT(*) AS n FROM users WHERE role IN ('Süper Admin','Admin') AND is_active=1 AND username<>?",
                (target_username,),
            ).fetchone()["n"]
            if int(active_admins or 0) < 1:
                raise ValueError("Son aktif Süper Admin kullanıcısı silinemez.")
        stamp = now_iso()
        conn.execute("UPDATE program_users SET is_active=0, deleted_at=?, deleted_by=?, updated_at=? WHERE username=?", (stamp, username, stamp, target_username))
        conn.execute("UPDATE users SET is_active=0, deleted_at=?, deleted_by=?, token_version=COALESCE(token_version, 1) + 1, updated_at=? WHERE username=?", (stamp, username, stamp, target_username))
    log_activity("Kullanıcı arşivlendi", target_username, username, "")
    return {"deleted": True, "soft_deleted": True, "username": target_username}

def record_login_attempt(username: str, success: bool, note: str = "") -> None:
    try:
        with transaction() as conn:
            conn.execute(
                "INSERT INTO login_attempts(id,username,success,note,created_at) VALUES(?,?,?,?,?)",
                (str(uuid.uuid4()), username.strip(), int(success), note, now_iso()),
            )
    except Exception:
        pass


def log_activity(action: str, detail: str = "", actor: str = "", program_id: str = "") -> None:
    stamp = now_iso()
    entry = {"ts": stamp, "action": action, "detail": detail, "actor": actor, "program_id": program_id}
    try:
        with transaction() as conn:
            conn.execute(
                "INSERT INTO activity_log(id,ts,action,detail,actor,program_id) VALUES(?,?,?,?,?,?)",
                (str(uuid.uuid4()), stamp, action, detail, actor, program_id),
            )
    except Exception:
        pass
    if program_id:
        try:
            program = get_program(program_id) or {"id": program_id, "program_name": program_id}
            append_activity_log_snapshot(program, entry)
        except Exception:
            pass


def list_programs_for_user(username: str) -> list[dict[str, Any]]:
    _ensure_accreditation_profile_column()
    user = get_user(username)
    if not user:
        return []
    with get_conn() as conn:
        user_admin_role = normalized_role(str(user.get("role", "")), str(user.get("tenant_scope", "") or ""))
        if user_admin_role in {SUPER_ADMIN_ROLE, TENANT_ADMIN_ROLE}:
            if user_is_global_admin(user):
                rows = conn.execute(
                    """SELECT p.*, COALESCE(t.name, 'Ana Kurum') AS tenant_name,
                              ? AS user_role, '' AS user_assigned_sections, 1 AS user_program_active
                       FROM programs p
                       LEFT JOIN tenants t ON t.id=COALESCE(p.tenant_id, ?)
                       WHERE p.is_active=1 AND COALESCE(p.deleted_at,'')=''
                       ORDER BY tenant_name, p.faculty_name, p.program_name""",
                    (user_admin_role, DEFAULT_TENANT_ID),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT p.*, COALESCE(t.name, 'Ana Kurum') AS tenant_name,
                              ? AS user_role, '' AS user_assigned_sections, 1 AS user_program_active
                       FROM programs p
                       LEFT JOIN tenants t ON t.id=COALESCE(p.tenant_id, ?)
                       WHERE p.is_active=1 AND COALESCE(p.deleted_at,'')='' AND COALESCE(p.tenant_id, ?)=?
                       ORDER BY tenant_name, p.faculty_name, p.program_name""",
                    (user_admin_role, DEFAULT_TENANT_ID, DEFAULT_TENANT_ID, user_tenant_id(user)),
                ).fetchall()
        elif user_admin_role == FACULTY_ADMIN_ROLE:
            faculty_name = _user_faculty_value(user)
            rows = conn.execute(
                """SELECT p.*, COALESCE(t.name, 'Ana Kurum') AS tenant_name,
                          ? AS user_role, '' AS user_assigned_sections, 1 AS user_program_active
                   FROM programs p
                   LEFT JOIN tenants t ON t.id=COALESCE(p.tenant_id, ?)
                   WHERE p.is_active=1 AND COALESCE(p.deleted_at,'')=''
                     AND COALESCE(p.tenant_id, ?) = ?
                     AND (
                        (?<>'' AND LOWER(COALESCE(NULLIF(p.school_name,''), p.faculty_name, '')) = LOWER(?))
                        OR EXISTS (
                            SELECT 1 FROM program_users pu
                            WHERE pu.program_id=p.id AND pu.username=? AND pu.is_active=1
                              AND COALESCE(pu.deleted_at,'')=''
                              AND COALESCE(pu.tenant_id, ?) = COALESCE(p.tenant_id, ?)
                              AND pu.role=?
                        )
                     )
                   ORDER BY tenant_name, p.school_name, p.department_name, p.program_name""",
                (FACULTY_ADMIN_ROLE, DEFAULT_TENANT_ID, DEFAULT_TENANT_ID, user_tenant_id(user), faculty_name, faculty_name, username, DEFAULT_TENANT_ID, DEFAULT_TENANT_ID, FACULTY_ADMIN_ROLE),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT p.*, COALESCE(t.name, 'Ana Kurum') AS tenant_name,
                          pu.role AS user_role, pu.assigned_sections AS user_assigned_sections,
                          pu.is_active AS user_program_active
                   FROM programs p
                   JOIN program_users pu ON pu.program_id=p.id
                   LEFT JOIN tenants t ON t.id=COALESCE(p.tenant_id, ?)
                   WHERE pu.username=? AND pu.is_active=1 AND COALESCE(pu.deleted_at,'')=''
                     AND p.is_active=1 AND COALESCE(p.deleted_at,'')=''
                     AND COALESCE(p.tenant_id, ?) = COALESCE(pu.tenant_id, ?)
                   ORDER BY tenant_name, p.faculty_name, p.program_name""",
                (DEFAULT_TENANT_ID, username, DEFAULT_TENANT_ID, DEFAULT_TENANT_ID),
            ).fetchall()
    return rows_to_dicts(rows)


def get_program(program_id: str) -> dict[str, Any] | None:
    _ensure_accreditation_profile_column()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM programs WHERE id=?", (program_id,)).fetchone()
    return row_to_dict(row)


def _program_setting_key(program_id: str, key: str) -> str:
    return f"program_setting:{program_id}:{key}"


def get_settings(program_id: str) -> dict[str, str]:
    program = get_program(program_id) or {}
    profile = normalize_accreditation_profile(program.get("accreditation_profile", "MEDEK"))
    profile_meta = accreditation_profile_meta(profile)
    settings = {
        "university": str(program.get("university_name", "") or ""),
        "school": str(program.get("school_name", "") or ""),
        "department": str(program.get("department_name", "") or ""),
        "program": str(program.get("program_name", "") or ""),
        "program_degree": str(program.get("program_degree", "") or ""),
        "report_year": str(program.get("report_year", "") or ""),
        "report_type": str(program.get("report_type", "") or profile_meta.get("report_type", "ÖZ DEĞERLENDİRME RAPORU")),
        "accreditation_profile": profile,
        "accreditation_label": profile_meta.get("label", profile),
        "accreditation_association": profile_meta.get("association_name", ""),
        "accreditation_system_name": profile_meta.get("system_name", ""),
        "report_short": profile_meta.get("report_short", "ÖDR"),
        "docx_filename": profile_meta.get("docx_filename", "AKYS_ODR.docx"),
        "pdf_filename": profile_meta.get("pdf_filename", "AKYS_ODR.pdf"),
        "control_filename": profile_meta.get("control_filename", "AKYS_kontrol_tablosu.docx"),
        "audit_filename": profile_meta.get("audit_filename", "AKYS_hazirlik_denetimi.docx"),
        "backup_filename": profile_meta.get("backup_filename", "MEDEK_yedek.json"),
    }
    program_setting_keys = {"report_no", "doc_date", "rev_date", "rev_no"}
    with get_conn() as conn:
        # Keep legacy global settings for backward compatibility, then apply
        # program-scoped overrides so report metadata never leaks across programs.
        rows = conn.execute("SELECT key,value FROM settings WHERE key NOT LIKE 'program_setting:%'").fetchall()
        program_rows = conn.execute(
            "SELECT key,value FROM settings WHERE key LIKE ?",
            (f"program_setting:{program_id}:%",),
        ).fetchall()
    for row in rows:
        key = str(row["key"] or "")
        if key.startswith("program_setting:"):
            continue
        settings[key] = str(row["value"] or "")
    for row in program_rows:
        raw_key = str(row["key"] or "")
        key = raw_key.rsplit(":", 1)[-1]
        if key in program_setting_keys:
            settings[key] = str(row["value"] or "")
    return settings


def get_settings_for_user(username: str, program_id: str) -> dict[str, str]:
    assert_program_access(username, program_id)
    return get_settings(program_id)


def update_settings_admin(username: str, program_id: str, payload: dict[str, Any]) -> dict[str, str]:
    assert_program_operation_permission(username, program_id, "program.edit")
    program_map = {
        "university": "university_name",
        "school": "school_name",
        "department": "department_name",
        "program": "program_name",
        "program_degree": "program_degree",
        "degree": "program_degree",
        "report_year": "report_year",
        "report_type": "report_type",
        "accreditation_profile": "accreditation_profile",
    }
    setting_keys = {"report_no", "doc_date", "rev_date", "rev_no"}
    refreshed_profile_sections = False
    with transaction() as conn:
        current_program = conn.execute("SELECT accreditation_profile FROM programs WHERE id=?", (program_id,)).fetchone()
        current_profile = normalize_accreditation_profile(current_program["accreditation_profile"]) if current_program else "MEDEK"
        for key, column in program_map.items():
            if key in payload:
                value = normalize_accreditation_profile(payload.get(key)) if key == "accreditation_profile" else str(payload.get(key, "") or "")
                conn.execute(
                    f"UPDATE programs SET {column}=?, updated_at=? WHERE id=?",
                    (value, now_iso(), program_id),
                )
                if key == "accreditation_profile" and value != current_profile:
                    refreshed_profile_sections = _replace_empty_sections_for_profile(conn, program_id, value)
        for key in setting_keys:
            if key in payload:
                conn.execute(
                    "INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
                    (_program_setting_key(program_id, key), str(payload.get(key, "") or "")),
                )
    detail = f"{program_id} - profil başlıkları yenilendi" if refreshed_profile_sections else program_id
    log_activity("Ayarlar güncellendi", detail, username, program_id)
    return get_settings(program_id)


def list_programs_admin(username: str, include_inactive: bool = True) -> list[dict[str, Any]]:
    # Program Yönetimi sekmeleri ayrı ayrı yetkilendirildiği için bu yardımcı
    # liste sadece "Tanımlı Programlar" iznine bağlı kalamaz; Yeni Program,
    # Kopyala veya Program Kullanıcıları sekmeleri de program seçici verisine ihtiyaç duyar.
    actor = assert_any_operation_permission(username, {
        "program.view",
        "program.list.view",
        "program.create",
        "program.clone",
        "program.assign_users",
        "program.users.view",
    })
    _ensure_accreditation_profile_column()
    with get_conn() as conn:
        query = """SELECT p.*, COALESCE(t.name, 'Ana Kurum') AS tenant_name
                   FROM programs p
                   LEFT JOIN tenants t ON t.id=COALESCE(p.tenant_id, ?)
                   WHERE COALESCE(p.deleted_at,'')=''
                     AND (t.id IS NULL OR COALESCE(t.deleted_at,'')='')"""
        params: list[Any] = [DEFAULT_TENANT_ID]
        if not include_inactive:
            query += " AND p.is_active=1"
        actor_role = normalized_role(str(actor.get("role", READONLY_ROLE)), str(actor.get("tenant_scope", "") or ""))
        if not user_is_global_admin(actor):
            query += " AND COALESCE(p.tenant_id, ?)=?"
            params.extend([DEFAULT_TENANT_ID, user_tenant_id(actor)])
            if actor_role == FACULTY_ADMIN_ROLE:
                actor_faculty = _user_faculty_value(actor)
                query += """ AND (
                    (?<>'' AND LOWER(COALESCE(NULLIF(p.school_name,''), p.faculty_name, ''))=LOWER(?))
                    OR EXISTS (
                        SELECT 1 FROM program_users pu_scope
                        WHERE pu_scope.program_id=p.id AND pu_scope.username=? AND pu_scope.is_active=1
                          AND COALESCE(pu_scope.deleted_at,'')='' AND pu_scope.role=?
                    )
                )"""
                params.extend([actor_faculty, actor_faculty, username, FACULTY_ADMIN_ROLE])
        query += " ORDER BY p.is_active DESC, tenant_name, p.faculty_name, p.program_name, p.report_year"
        rows = conn.execute(query, params).fetchall()
    return rows_to_dicts(rows)


def _section_template_rows(conn, source_program_id: str = "", accreditation_profile: str = "") -> list[dict[str, Any]]:
    source = source_program_id
    profile = normalize_accreditation_profile(accreditation_profile) if accreditation_profile else ""
    if not source and profile:
        return profile_section_template(profile)
    if not source:
        row = conn.execute(
            """SELECT program_id AS id, COUNT(*) AS section_count
               FROM sections
               GROUP BY program_id
               HAVING section_count > 0
               ORDER BY section_count DESC, program_id
               LIMIT 1"""
        ).fetchone()
        source = row["id"] if row else ""
    if not source:
        return []
    rows = conn.execute(
        """SELECT section_key, main_title, section_title, sort_order
           FROM sections WHERE program_id=? AND COALESCE(deleted_at,'')='' ORDER BY sort_order, section_key""",
        (source,),
    ).fetchall()
    return rows_to_dicts(rows)


def _insert_empty_sections(conn, program_id: str, template_rows: list[dict[str, Any]]) -> None:
    for index, row in enumerate(template_rows, 1):
        conn.execute(
            """INSERT OR IGNORE INTO sections(
                id, program_id, section_key, main_title, section_title, sort_order,
                status, report_text, planla, uygula, kontrol, onlem, notes,
                deadline, approval_status, approved_by, approved_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()),
                program_id,
                row.get("section_key", ""),
                row.get("main_title", ""),
                row.get("section_title", ""),
                int(row.get("sort_order") or index),
                "Başlamadı",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "Taslak",
                "",
                "",
                now_iso(),
            ),
        )


def _section_skeleton_replaceable(conn, program_id: str) -> bool:
    filled = conn.execute(
        """SELECT COUNT(*) AS n
           FROM sections
           WHERE program_id=?
             AND (
               LENGTH(TRIM(report_text)) > 0 OR LENGTH(TRIM(planla)) > 0 OR
               LENGTH(TRIM(uygula)) > 0 OR LENGTH(TRIM(kontrol)) > 0 OR
               LENGTH(TRIM(onlem)) > 0 OR LENGTH(TRIM(notes)) > 0 OR
               LENGTH(TRIM(deadline)) > 0
             )""",
        (program_id,),
    ).fetchone()["n"]
    if int(filled or 0) > 0:
        return False
    related_tables = ("evidence", "evidence_links", "data_tables", "section_approvals", "section_versions")
    for table in related_tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE program_id=?", (program_id,)).fetchone()["n"]
        except Exception:
            count = 0
        if int(count or 0) > 0:
            return False
    return True


def _replace_empty_sections_for_profile(conn, program_id: str, profile: str) -> bool:
    if not _section_skeleton_replaceable(conn, program_id):
        return False
    conn.execute("DELETE FROM sections WHERE program_id=?", (program_id,))
    _insert_empty_sections(conn, program_id, profile_section_template(profile))
    return True


def _section_signature(rows: list[dict[str, Any]]) -> list[tuple[str, str]]:
    return [(str(row.get("section_key", "")), str(row.get("main_title", ""))) for row in rows]


def ensure_program_section_skeleton(program_id: str) -> None:
    program = get_program(program_id) or {}
    profile = normalize_accreditation_profile(program.get("accreditation_profile", "MEDEK"))
    with transaction() as conn:
        existing = conn.execute("SELECT COUNT(*) AS n FROM sections WHERE program_id=?", (program_id,)).fetchone()
        if int(existing["n"] or 0) > 0:
            if profile != "MEDEK" and _section_skeleton_replaceable(conn, program_id):
                rows = conn.execute(
                    """SELECT section_key, main_title, section_title, sort_order
                       FROM sections WHERE program_id=? AND COALESCE(deleted_at,'')='' ORDER BY sort_order, section_key""",
                    (program_id,),
                ).fetchall()
                current_signature = _section_signature(rows_to_dicts(rows))
                expected_signature = _section_signature(profile_section_template(profile))
                if current_signature != expected_signature:
                    _replace_empty_sections_for_profile(conn, program_id, profile)
            return
        template_rows = _section_template_rows(conn, accreditation_profile=profile)
        if not template_rows:
            return
        _insert_empty_sections(conn, program_id, template_rows)


def create_program_admin(username: str, payload: dict[str, Any]) -> dict[str, Any]:
    actor = assert_operation_permission(username, "program.create")
    _ensure_accreditation_profile_column()
    program_name = str(payload.get("program_name", "") or "").strip()
    if not program_name:
        raise ValueError("Program adı boş olamaz.")
    report_year = str(payload.get("report_year", "") or "2025").strip()
    tenant_id = str(payload.get("tenant_id", "") or user_tenant_id(actor)).strip() or DEFAULT_TENANT_ID
    ensure_tenant_access(username, tenant_id)
    school_name = str(payload.get("school_name", "") or "")
    faculty_name = str(payload.get("faculty_name", "") or school_name or "")
    actor_role = normalized_role(str(actor.get("role", READONLY_ROLE)), str(actor.get("tenant_scope", "") or ""))
    if actor_role == FACULTY_ADMIN_ROLE:
        actor_faculty = _user_faculty_value(actor)
        if not actor_faculty:
            raise PermissionError("Birim Admin hesabının fakülte kapsamı tanımlı değil.")
        requested_faculty = faculty_name or school_name or actor_faculty
        if _norm_scope_text(requested_faculty) != _norm_scope_text(actor_faculty):
            raise PermissionError("Birim Admin yalnızca kendi Fakülte/MYO kapsamındaki programları oluşturabilir.")
        school_name = actor_faculty
        faculty_name = actor_faculty
    department_name = str(payload.get("department_name", "") or "")
    program_degree = str(payload.get("program_degree", payload.get("degree", "")) or "").strip()
    raw_profile = str(payload.get("accreditation_profile", "") or "").strip()
    profile = normalize_accreditation_profile(raw_profile) if raw_profile and raw_profile.upper() not in {"AUTO", "OTOMATIK", "OTOMATİK"} else infer_accreditation_profile_by_rule(
        degree=program_degree,
        faculty_name=faculty_name or school_name,
        department_name=department_name,
        program_name=program_name,
    )
    program_id = f"prog_{slugify(program_name)[:32]}_{slugify(report_year)[:12]}_{uuid.uuid4().hex[:6]}"
    with transaction() as conn:
        if faculty_name:
            conn.execute(
                """INSERT INTO tenant_faculties(id,tenant_id,faculty_name,accreditation_profile,is_active,created_at,updated_at,deleted_at,deleted_by)
                   VALUES(?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(tenant_id, faculty_name) DO UPDATE SET accreditation_profile=excluded.accreditation_profile,
                       is_active=1, updated_at=excluded.updated_at, deleted_at='', deleted_by=''""",
                (str(uuid.uuid4()), tenant_id, faculty_name, profile, 1, now_iso(), now_iso(), "", ""),
            )
        conn.execute(
            """INSERT INTO programs(
                id, university_name, school_name, faculty_name, department_name, program_name,
                report_year, report_type, accreditation_profile, tenant_id, program_degree, is_active, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                program_id,
                str(payload.get("university_name", "") or ""),
                school_name,
                faculty_name,
                department_name,
                program_name,
                report_year,
                str(payload.get("report_type", "") or "ÖZ DEĞERLENDİRME RAPORU"),
                profile,
                tenant_id,
                program_degree,
                1 if bool(payload.get("is_active", True)) else 0,
                now_iso(),
                now_iso(),
            ),
        )
        _insert_empty_sections(conn, program_id, _section_template_rows(conn, accreditation_profile=profile))
        conn.execute(
            """INSERT OR IGNORE INTO program_users(
                id, program_id, username, role, tenant_id, assigned_sections, is_active, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4()), program_id, username, actor_role if actor_role in {TENANT_ADMIN_ROLE, FACULTY_ADMIN_ROLE} else ADMIN_ROLE, tenant_id, "", 1, now_iso(), now_iso()),
        )
    log_activity("Program oluşturuldu", f"{program_name} / {tenant_id}", username, program_id)
    return get_program(program_id) or {}


def clone_program_admin(username: str, payload: dict[str, Any]) -> dict[str, Any]:
    source_program_id = str(payload.get("source_program_id", "") or "").strip()
    source = get_program(source_program_id)
    if not source:
        raise ValueError("Kaynak program bulunamadı.")
    assert_program_operation_permission(username, source_program_id, "program.clone")
    new_program = create_program_admin(
        username,
        {
            "university_name": source.get("university_name", ""),
            "school_name": source.get("school_name", ""),
            "department_name": source.get("department_name", ""),
            "program_name": payload.get("program_name", ""),
            "program_degree": source.get("program_degree", ""),
            "report_year": payload.get("report_year", ""),
            "report_type": source.get("report_type", "ÖZ DEĞERLENDİRME RAPORU"),
            "accreditation_profile": source.get("accreditation_profile", "MEDEK"),
            "tenant_id": source.get("tenant_id", DEFAULT_TENANT_ID),
            "faculty_name": source.get("faculty_name", source.get("school_name", "")),
            "is_active": True,
        },
    )
    new_program_id = str(new_program.get("id", ""))
    with transaction() as conn:
        if bool(payload.get("copy_text", True)):
            source_sections = conn.execute("SELECT * FROM sections WHERE program_id=? AND COALESCE(deleted_at,'')=''", (source_program_id,)).fetchall()
            for section in source_sections:
                conn.execute(
                    """UPDATE sections
                       SET report_text=?, planla=?, uygula=?, kontrol=?, onlem=?, notes=?,
                           deadline=?, status=?, updated_at=?
                       WHERE program_id=? AND section_key=?""",
                    (
                        section["report_text"] or "",
                        section["planla"] or "",
                        section["uygula"] or "",
                        section["kontrol"] or "",
                        section["onlem"] or "",
                        section["notes"] or "",
                        section["deadline"] or "",
                        READY if (section["report_text"] or "").strip() else "Başlamadı",
                        now_iso(),
                        new_program_id,
                        section["section_key"],
                    ),
                )
        if bool(payload.get("copy_tables", False)):
            tables = conn.execute("SELECT * FROM data_tables WHERE program_id=? AND COALESCE(deleted_at,'')=''", (source_program_id,)).fetchall()
            for table in tables:
                conn.execute(
                    "INSERT OR IGNORE INTO data_tables(id,program_id,section_key,table_name,data_json,updated_at) VALUES(?,?,?,?,?,?)",
                    (str(uuid.uuid4()), new_program_id, table["section_key"], table["table_name"], table["data_json"], now_iso()),
                )
        if bool(payload.get("copy_evidence_meta", False)):
            evidence_rows = conn.execute("SELECT * FROM evidence WHERE program_id=? AND COALESCE(deleted_at,'')=''", (source_program_id,)).fetchall()
            for evidence in evidence_rows:
                new_evidence_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO evidence(id,program_id,section_key,code,original_name,stored_path,note,uploaded_at) VALUES(?,?,?,?,?,?,?,?)",
                    (
                        new_evidence_id,
                        new_program_id,
                        evidence["section_key"],
                        evidence["code"],
                        evidence["original_name"],
                        evidence["stored_path"],
                        evidence["note"],
                        now_iso(),
                    ),
                )
                links = conn.execute(
                    "SELECT section_key FROM evidence_links WHERE program_id=? AND evidence_id=?",
                    (source_program_id, evidence["id"]),
                ).fetchall()
                for link in links:
                    conn.execute(
                        "INSERT OR IGNORE INTO evidence_links(program_id,evidence_id,section_key) VALUES(?,?,?)",
                        (new_program_id, new_evidence_id, link["section_key"]),
                    )
    log_activity("Program kopyalandı", f"{source_program_id} -> {new_program_id}", username, new_program_id)
    return get_program(new_program_id) or {}


def set_program_active_admin(username: str, program_id: str, active: bool) -> dict[str, Any]:
    assert_program_operation_permission(username, program_id, "program.edit")
    with transaction() as conn:
        conn.execute("UPDATE programs SET is_active=?, updated_at=? WHERE id=?", (1 if active else 0, now_iso(), program_id))
    log_activity("Program aktifliği değişti", f"{program_id} -> {active}", username, program_id)
    return get_program(program_id) or {}


def delete_program_admin(username: str, program_id: str) -> dict[str, Any]:
    """Soft-delete a program so it can be restored from the admin recovery panel."""
    assert_program_operation_permission(username, program_id, "program.archive")
    program = get_program(program_id)
    if not program:
        raise ValueError("Program bulunamadı.")
    with transaction() as conn:
        conn.execute(
            "UPDATE programs SET is_active=0, deleted_at=?, deleted_by=?, updated_at=? WHERE id=?",
            (now_iso(), username, now_iso(), program_id),
        )
    # Compatibility note for earlier audit wording: "Program silindi" now means soft-delete/archive.
    log_activity("Program arşive taşındı", str(program.get("program_name", program_id)), username, program_id)
    return {"deleted": True, "soft_deleted": True, "program_id": program_id, "program_name": program.get("program_name", "")}

def list_program_users_admin(username: str, program_id: str | None = None) -> list[dict[str, Any]]:
    actor = assert_any_operation_permission(username, {"program.users.view", "program.assign_users"})
    actor_role = normalized_role(str(actor.get("role", READONLY_ROLE)), str(actor.get("tenant_scope", "") or ""))
    with get_conn() as conn:
        params: list[Any] = [DEFAULT_TENANT_ID]
        where = """WHERE COALESCE(pu.deleted_at,'')=''
                   AND COALESCE(u.deleted_at,'')=''
                   AND COALESCE(p.deleted_at,'')=''
                   AND (t.id IS NULL OR COALESCE(t.deleted_at,'')='')"""
        if program_id:
            assert_program_access(username, program_id)
            where += " AND pu.program_id=?"
            params.append(program_id)
        if not user_is_global_admin(actor):
            where += " AND COALESCE(pu.tenant_id, ?)=?"
            params.extend([DEFAULT_TENANT_ID, user_tenant_id(actor)])
            if actor_role == FACULTY_ADMIN_ROLE:
                actor_faculty = _user_faculty_value(actor)
                where += """ AND (
                    (?<>'' AND LOWER(COALESCE(NULLIF(p.school_name,''), p.faculty_name, ''))=LOWER(?))
                    OR EXISTS (
                        SELECT 1 FROM program_users pu_scope
                        WHERE pu_scope.program_id=p.id AND pu_scope.username=? AND pu_scope.is_active=1
                          AND COALESCE(pu_scope.deleted_at,'')='' AND pu_scope.role=?
                    )
                )"""
                params.extend([actor_faculty, actor_faculty, username, FACULTY_ADMIN_ROLE])
        rows = conn.execute(
            f"""SELECT pu.*, u.full_name, u.email, u.academic_status, u.is_active AS user_active,
                       u.role AS global_role, u.tenant_scope AS global_tenant_scope, u.faculty_name AS user_faculty_name,
                       p.program_name, p.report_year, p.faculty_name, p.school_name,
                       COALESCE(t.name, 'Ana Kurum') AS tenant_name
                FROM program_users pu
                JOIN users u ON u.username=pu.username
                JOIN programs p ON p.id=pu.program_id
                LEFT JOIN tenants t ON t.id=COALESCE(pu.tenant_id, ?)
                {where}
                ORDER BY tenant_name, p.faculty_name, p.program_name, pu.role, pu.username""",
            params,
        ).fetchall()
    visible_roles = visible_roles_for_actor(actor)
    scoped_rows = []
    for row in rows_to_dicts(rows):
        program_role = normalized_role(str(row.get("role", READONLY_ROLE)), "")
        global_role = normalized_role(str(row.get("global_role", READONLY_ROLE)), str(row.get("global_tenant_scope", "") or ""))
        if program_role in visible_roles and global_role in visible_roles:
            row["role"] = program_role
            row["global_role"] = global_role
            scoped_rows.append(row)
    return scoped_rows


def assign_user_to_program_admin(username: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    actor = assert_operation_permission(username, "program.assign_users")
    target_username = str(payload.get("username", "") or "").strip()
    role = str(payload.get("role", "") or "").strip()
    program_ids = [str(item).strip() for item in payload.get("program_ids", []) if str(item).strip()]
    if not target_username:
        raise ValueError("Kullanıcı seçilmedi.")
    role = normalized_role(role, "")
    if role not in ROLE_OPTIONS:
        raise ValueError("Geçersiz rol.")
    actor_role = normalized_role(str(actor.get("role", READONLY_ROLE)), str(actor.get("tenant_scope", "") or ""))
    allowed_roles = delegatable_roles_for_actor(actor)
    if role == SUPER_ADMIN_ROLE:
        raise PermissionError("Süper Admin program bazlı rol olarak atanamaz.")
    if role not in allowed_roles:
        if actor_role == TENANT_ADMIN_ROLE:
            raise PermissionError("Kurum Admin program atamalarında yalnızca Birim Admin, Birim Koordinatörü, Editör / Hazırlayıcı, Onaylayıcı ve Denetçi rollerini dağıtabilir.")
        if actor_role == FACULTY_ADMIN_ROLE:
            raise PermissionError("Birim Admin program atamalarında yalnızca Editör / Hazırlayıcı, Onaylayıcı ve Denetçi rollerini dağıtabilir.")
        raise PermissionError("Bu rolü program bazlı dağıtma yetkiniz yok.")
    if not program_ids:
        raise ValueError("En az bir program seçilmelidir.")
    with transaction() as conn:
        target = conn.execute("SELECT username, role, tenant_id, tenant_scope, faculty_name FROM users WHERE username=?", (target_username,)).fetchone()
        if not target:
            raise ValueError("Kullanıcı bulunamadı.")
        target_global_role = normalized_role(str(target["role"] or READONLY_ROLE), str(target["tenant_scope"] or ""))
        if not user_is_global_admin(actor) and str(target["tenant_id"] or DEFAULT_TENANT_ID) != user_tenant_id(actor):
            raise PermissionError("Başka kurum kullanıcısına program yetkisi verilemez.")
        if not user_is_global_admin(actor) and not role_same_or_lower(target_global_role, actor_role):
            raise PermissionError("Kendi rütbenizin üzerindeki kullanıcıya program yetkisi veremezsiniz.")
        if actor_role == FACULTY_ADMIN_ROLE:
            actor_faculty = _user_faculty_value(actor)
            if not actor_faculty:
                raise PermissionError("Birim Admin hesabının fakülte kapsamı tanımlı değil.")
            target_faculty = str(target["faculty_name"] or actor_faculty)
            if _norm_scope_text(target_faculty) != _norm_scope_text(actor_faculty):
                raise PermissionError("Birim Admin başka birim kullanıcısına program yetkisi veremez.")
        faculty_scope_values: set[str] = set()
        for program_id in program_ids:
            program = conn.execute("SELECT id, tenant_id, school_name, faculty_name FROM programs WHERE id=?", (program_id,)).fetchone()
            if not program:
                raise ValueError(f"Program bulunamadı: {program_id}")
            tenant_id = str(program["tenant_id"] or DEFAULT_TENANT_ID)
            if not can_access_tenant(username, tenant_id):
                raise PermissionError("Başka kuruma ait programa yetki verilemez.")
            if actor_role == FACULTY_ADMIN_ROLE:
                program_scope = {"school_name": program["school_name"], "faculty_name": program["faculty_name"], "tenant_id": tenant_id}
                if not _faculty_scope_matches(actor, program_scope) and get_program_role(username, program_id) != FACULTY_ADMIN_ROLE:
                    raise PermissionError("Birim Admin yalnızca kendi birimindeki programlara yetki verebilir.")
            target_scope = str(target["tenant_scope"] or TENANT_SCOPE)
            target_tenant_id = str(target["tenant_id"] or DEFAULT_TENANT_ID)
            if target_scope != GLOBAL_SCOPE and target_tenant_id != tenant_id:
                raise PermissionError("Kullanıcı ve program aynı kuruma ait olmalıdır.")
            existing = conn.execute(
                "SELECT id FROM program_users WHERE program_id=? AND username=?",
                (program_id, target_username),
            ).fetchone()
            values = (
                role,
                tenant_id,
                str(payload.get("assigned_sections", "") or ""),
                1 if bool(payload.get("is_active", True)) else 0,
                now_iso(),
                program_id,
                target_username,
            )
            if role in {FACULTY_ADMIN_ROLE, UNIT_COORDINATOR_ROLE}:
                faculty_scope_values.add(str(program["school_name"] or program["faculty_name"] or ""))
            if existing:
                conn.execute(
                    """UPDATE program_users
                       SET role=?, tenant_id=?, assigned_sections=?, is_active=?, updated_at=?, deleted_at='', deleted_by=''
                       WHERE program_id=? AND username=?""",
                    values,
                )
            else:
                conn.execute(
                    """INSERT INTO program_users(
                        id, program_id, username, role, tenant_id, assigned_sections, is_active, created_at, updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (
                        str(uuid.uuid4()),
                        program_id,
                        target_username,
                        role,
                        tenant_id,
                        str(payload.get("assigned_sections", "") or ""),
                        1 if bool(payload.get("is_active", True)) else 0,
                        now_iso(),
                        now_iso(),
                    ),
                )
        if role in {FACULTY_ADMIN_ROLE, UNIT_COORDINATOR_ROLE} and len({item for item in faculty_scope_values if item}) != 1:
            raise ValueError("Birim Admin/Birim Koordinatörü ataması tek bir birim kapsamındaki programlara yapılmalıdır.")
        if role in {FACULTY_ADMIN_ROLE, UNIT_COORDINATOR_ROLE}:
            faculty_scope = next(iter({item for item in faculty_scope_values if item}), "")
            conn.execute(
                "UPDATE users SET faculty_name=?, token_version=COALESCE(token_version, 1) + 1, updated_at=? WHERE username=?",
                (faculty_scope, now_iso(), target_username),
            )
        else:
            conn.execute(
                "UPDATE users SET token_version=COALESCE(token_version, 1) + 1, updated_at=? WHERE username=?",
                (now_iso(), target_username),
            )
    log_activity("Program kullanıcısı atandı", f"{target_username} -> {role} ({len(program_ids)})", username, "")
    return list_program_users_admin(username)


def get_program_role(username: str, program_id: str) -> str:
    user = get_user(username)
    global_role = normalized_role(str((user or {}).get("role", "") or ""), str((user or {}).get("tenant_scope", "") or ""))
    if global_role in {SUPER_ADMIN_ROLE, TENANT_ADMIN_ROLE}:
        try:
            ensure_program_tenant_access(username, program_id)
            return global_role
        except PermissionError:
            return READONLY_ROLE
    if global_role == FACULTY_ADMIN_ROLE:
        program = get_program(program_id) or {}
        if _faculty_scope_matches(user, program) and can_access_tenant(username, str(program.get("tenant_id") or DEFAULT_TENANT_ID)):
            return FACULTY_ADMIN_ROLE
    with get_conn() as conn:
        row = conn.execute(
            """SELECT role FROM program_users
               WHERE username=? AND program_id=? AND is_active=1 AND COALESCE(deleted_at,'')=''
                 AND COALESCE(tenant_id, ?) = ?""",
            (username, program_id, DEFAULT_TENANT_ID, program_tenant_id(program_id)),
        ).fetchone()
    return normalized_role(str(row["role"]), "") if row else READONLY_ROLE


def get_assignment(username: str, program_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM program_users WHERE username=? AND program_id=? AND is_active=1 AND COALESCE(deleted_at,'')=''",
            (username, program_id),
        ).fetchone()
    return row_to_dict(row)


def assigned_section_keys(username: str, program_id: str) -> set[str]:
    assignment = get_assignment(username, program_id)
    raw = str((assignment or {}).get("assigned_sections", "") or "").strip()
    if not raw:
        return set()
    return {part.strip() for part in raw.split(",") if part.strip()}


def assert_program_access(username: str, program_id: str) -> str:
    ensure_program_tenant_access(username, program_id)
    role = get_program_role(username, program_id)
    if role == READONLY_ROLE:
        user_programs = {row["id"] for row in list_programs_for_user(username)}
        if program_id not in user_programs:
            raise PermissionError("Programa erişim yetkiniz yok.")
    return role


def _section_access_allowed(username: str, program_id: str, section_key: str) -> bool:
    role = assert_program_access(username, program_id)
    if role in {SUPER_ADMIN_ROLE, TENANT_ADMIN_ROLE, FACULTY_ADMIN_ROLE, UNIT_COORDINATOR_ROLE, APPROVER_ROLE, READONLY_ROLE}:
        return True
    assigned = assigned_section_keys(username, program_id)
    return not assigned or section_key in assigned


def list_sections(username: str, program_id: str) -> list[dict[str, Any]]:
    role = assert_program_access(username, program_id)
    assigned = assigned_section_keys(username, program_id)
    ensure_program_section_skeleton(program_id)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sections WHERE program_id=? AND COALESCE(deleted_at,'')=''",
            (program_id,),
        ).fetchall()
    sections = normalize_section_rows(rows_to_dicts(rows))
    if role == EDITOR_ROLE and assigned:
        sections = [row for row in sections if row.get("section_key") in assigned]
    return sections


def get_section(username: str, program_id: str, section_key: str) -> dict[str, Any] | None:
    if not _section_access_allowed(username, program_id, section_key):
        raise PermissionError("Bu başlığa erişim yetkiniz yok.")
    ensure_program_section_skeleton(program_id)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sections WHERE program_id=? AND COALESCE(deleted_at,'')='' AND section_key=?",
            (program_id, section_key),
        ).fetchone()
    result = row_to_dict(row)
    if result:
        result["revision"] = latest_revision_note(program_id, section_key)
        role = assert_program_access(username, program_id)
        from .section_permissions import SECTION_PERMISSION_ACTIONS, section_permission_allows
        result["user_permissions"] = {
            item["action"]: section_permission_allows(program_id, section_key, role, item["action"])
            for item in SECTION_PERMISSION_ACTIONS
        }
    return result


def _section_permission(username: str, program_id: str, section_key: str, action: str) -> bool:
    role = assert_program_access(username, program_id)
    from .section_permissions import section_permission_allows
    return section_permission_allows(program_id, section_key, role, action)


def can_edit_section(username: str, program_id: str, section: dict[str, Any]) -> bool:
    role = assert_program_access(username, program_id)
    section_key = str(section.get("section_key", "") or "")
    if role == READONLY_ROLE or not section_key:
        return False
    if not _section_access_allowed(username, program_id, section_key):
        return False
    if section.get("approval_status") in {APPROVED, SUBMITTED} and role != ADMIN_ROLE:
        return False
    return any(_section_permission(username, program_id, section_key, action) for action in ["edit_text", "edit_puko", "edit_status", "edit_deadline"])


def update_section(username: str, program_id: str, section_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    section = get_section(username, program_id, section_key)
    if not section:
        raise KeyError(section_key)
    if not can_edit_section(username, program_id, section):
        raise PermissionError("Bu başlık düzenlenebilir değil.")

    is_autosave = bool(payload.get("is_autosave"))
    field_policy = {
        "status": "edit_status",
        "report_text": "edit_text",
        "notes": "edit_text",
        "planla": "edit_puko",
        "uygula": "edit_puko",
        "kontrol": "edit_puko",
        "onlem": "edit_puko",
        "deadline": "edit_deadline",
    }
    next_values: dict[str, Any] = {}
    for field, action in field_policy.items():
        current_value = str(section.get(field, "") or "")
        incoming_value = str(payload.get(field, section.get(field, "")) or "")
        if incoming_value != current_value and not _section_permission(username, program_id, section_key, action):
            raise PermissionError(f"{field} alanını düzenleme yetkiniz yok.")
        next_values[field] = incoming_value

    changed = any(str(section.get(field, "") or "") != str(next_values.get(field, "") or "") for field in field_policy)
    with transaction() as conn:
        if changed:
            conn.execute(
                """INSERT INTO section_versions(
                    id, program_id, section_key, saved_at, status, report_text, planla, uygula,
                    kontrol, onlem, notes, deadline, change_summary
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()),
                    program_id,
                    section_key,
                    now_iso(),
                    section.get("status", ""),
                    section.get("report_text", "") or "",
                    section.get("planla", "") or "",
                    section.get("uygula", "") or "",
                    section.get("kontrol", "") or "",
                    section.get("onlem", "") or "",
                    section.get("notes", "") or "",
                    section.get("deadline", "") or "",
                    "Otomatik taslak kaydı" if is_autosave else "Manuel başlık kaydı",
                ),
            )
        next_approval = "Taslak" if section.get("approval_status") == APPROVED else section.get("approval_status", "Taslak")
        conn.execute(
            """UPDATE sections SET status=?, report_text=?, planla=?, uygula=?, kontrol=?, onlem=?,
               notes=?, deadline=?, approval_status=?, updated_at=?
               WHERE program_id=? AND section_key=?""",
            (
                next_values.get("status", section.get("status", "")),
                next_values.get("report_text", section.get("report_text", "")),
                next_values.get("planla", section.get("planla", "")),
                next_values.get("uygula", section.get("uygula", "")),
                next_values.get("kontrol", section.get("kontrol", "")),
                next_values.get("onlem", section.get("onlem", "")),
                next_values.get("notes", section.get("notes", "")),
                next_values.get("deadline", section.get("deadline", "")),
                next_approval,
                now_iso(),
                program_id,
                section_key,
            ),
        )
    action_label = "Otomatik taslak kaydı" if is_autosave else "Manuel başlık kaydı"
    result = get_section(username, program_id, section_key) or {}
    try:
        program = get_program(program_id) or {"id": program_id, "program_name": program_id}
        write_section_text_archive(program, result, actor=username, action=action_label, is_autosave=is_autosave)
        all_sections = []
        with get_conn() as mirror_conn:
            all_sections = rows_to_dicts(mirror_conn.execute(
                "SELECT * FROM sections WHERE program_id=? AND COALESCE(deleted_at,'')='' ORDER BY sort_order, section_key",
                (program_id,),
            ).fetchall())
        write_all_sections_archive(program, all_sections, actor=username, action="Başlık kaydı sonrası tam rapor aynası", create_snapshot=not is_autosave)
    except Exception:
        pass
    log_activity("Başlık otomatik kaydedildi" if is_autosave else "Başlık güncellendi", section_key, username, program_id)
    return result


def list_evidence(username: str, program_id: str, section_key: str | None = None) -> list[dict[str, Any]]:
    role = assert_program_access(username, program_id)
    with get_conn() as conn:
        if section_key:
            if not _section_access_allowed(username, program_id, section_key):
                raise PermissionError("Bu başlığa erişim yetkiniz yok.")
            rows = conn.execute(
                """SELECT DISTINCT e.* FROM evidence e
                   LEFT JOIN evidence_links el ON el.evidence_id=e.id AND el.program_id=e.program_id
                   WHERE e.program_id=? AND COALESCE(e.deleted_at,'')='' AND (e.section_key=? OR el.section_key=?)
                   ORDER BY e.uploaded_at DESC""",
                (program_id, section_key, section_key),
            ).fetchall()
        else:
            assigned = assigned_section_keys(username, program_id) if role == EDITOR_ROLE else set()
            if assigned:
                placeholders = ",".join("?" for _ in assigned)
                params = [program_id, *sorted(assigned), *sorted(assigned)]
                rows = conn.execute(
                    f"""SELECT DISTINCT e.* FROM evidence e
                        LEFT JOIN evidence_links el ON el.evidence_id=e.id AND el.program_id=e.program_id
                        WHERE e.program_id=?
                          AND COALESCE(e.deleted_at,'')=''
                          AND (e.section_key IN ({placeholders}) OR el.section_key IN ({placeholders}))
                        ORDER BY e.uploaded_at DESC""",
                    params,
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM evidence WHERE program_id=? AND COALESCE(deleted_at,'')='' ORDER BY uploaded_at DESC",
                    (program_id,),
                ).fetchall()
    evidence_rows = rows_to_dicts(rows)
    for row in evidence_rows:
        row["section_keys"] = evidence_links(program_id, str(row.get("id", "")))
    return evidence_rows


def evidence_links(program_id: str, evidence_id: str) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT section_key FROM evidence_links WHERE program_id=? AND evidence_id=? ORDER BY section_key",
            (program_id, evidence_id),
        ).fetchall()
    return [str(row["section_key"]) for row in rows]


def _evidence_section_keys(program_id: str, evidence: dict[str, Any]) -> list[str]:
    keys = evidence_links(program_id, str(evidence.get("id", "")))
    if not keys and str(evidence.get("section_key", "") or "").strip():
        keys = [str(evidence.get("section_key", "") or "").strip()]
    return keys


def _evidence_access_allowed(username: str, program_id: str, evidence: dict[str, Any]) -> bool:
    keys = _evidence_section_keys(program_id, evidence)
    if not keys:
        return True
    return any(_section_access_allowed(username, program_id, key) for key in keys)


def save_evidence_file(
    username: str,
    program_id: str,
    section_keys: list[str],
    code: str,
    note: str,
    original_name: str,
    data: bytes,
) -> dict[str, Any]:
    assert_program_access(username, program_id)
    keys = list(dict.fromkeys([key.strip() for key in section_keys if key.strip()]))
    if not keys:
        raise ValueError("En az bir başlık seçilmelidir.")
    for key in keys:
        section = get_section(username, program_id, key)
        if not section:
            raise KeyError(key)
        if not can_edit_section(username, program_id, section):
            raise PermissionError(f"{key} başlığı düzenlenebilir değil.")
    validate_evidence_bytes(original_name, data)
    program = get_program(program_id) or {"id": program_id, "program_name": program_id}
    folder = evidence_section_dir(program, keys[0])
    evidence_id = str(uuid.uuid4())
    safe_name = f"{timestamp_slug()}_{evidence_id}_{slugify(Path(original_name).stem)}{Path(original_name).suffix.lower()}"
    stored = folder / safe_name
    stored.write_bytes(data)
    write_program_manifest(program, extra={"type": "evidence", "section_key": keys[0], "file": str(stored)})
    with transaction() as conn:
        conn.execute(
            "INSERT INTO evidence(id,program_id,section_key,code,original_name,stored_path,note,uploaded_at) VALUES(?,?,?,?,?,?,?,?)",
            (evidence_id, program_id, keys[0], code.strip(), Path(original_name).name, str(stored), note, now_iso()),
        )
        for key in keys:
            conn.execute(
                "INSERT OR IGNORE INTO evidence_links(program_id,evidence_id,section_key) VALUES(?,?,?)",
                (program_id, evidence_id, key),
            )
    log_activity("Kanıt yüklendi", f"{code} -> {', '.join(keys)}", username, program_id)
    return get_evidence_by_id(username, program_id, evidence_id) or {}


def get_evidence_by_id(username: str, program_id: str, evidence_id: str) -> dict[str, Any] | None:
    assert_program_access(username, program_id)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM evidence WHERE program_id=? AND id=? AND COALESCE(deleted_at,'')=''",
            (program_id, evidence_id),
        ).fetchone()
    result = row_to_dict(row)
    if result:
        result["section_keys"] = _evidence_section_keys(program_id, result)
        if not _evidence_access_allowed(username, program_id, result):
            raise PermissionError("Bu kanıta erişim yetkiniz yok.")
    return result


def link_evidence_to_section(username: str, program_id: str, evidence_id: str, section_key: str, code: str = "", note: str = "") -> dict[str, Any]:
    evidence = get_evidence_by_id(username, program_id, evidence_id)
    if not evidence:
        raise KeyError(evidence_id)
    section = get_section(username, program_id, section_key)
    if not section:
        raise KeyError(section_key)
    if not can_edit_section(username, program_id, section):
        raise PermissionError("Bu başlık düzenlenebilir değil.")
    clean_code = str(code or "").strip()
    clean_note = str(note or "").strip()
    with transaction() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO evidence_links(program_id,evidence_id,section_key) VALUES(?,?,?)",
            (program_id, evidence_id, section_key),
        )
        if clean_code or clean_note:
            current_code = str(evidence.get("code", "") or "")
            current_note = str(evidence.get("note", "") or "")
            conn.execute(
                "UPDATE evidence SET code=?, note=? WHERE program_id=? AND id=?",
                (clean_code or current_code, clean_note or current_note, program_id, evidence_id),
            )
    log_activity("Kanıt bağlandı", f"{clean_code or evidence.get('code', evidence_id)} -> {section_key}", username, program_id)
    return get_evidence_by_id(username, program_id, evidence_id) or {}


def evidence_file_path(username: str, program_id: str, evidence_id: str) -> tuple[Path, dict[str, Any]]:
    evidence = get_evidence_by_id(username, program_id, evidence_id)
    if not evidence:
        raise KeyError(evidence_id)
    path = safe_stored_path(str(evidence.get("stored_path", "")))
    if not path or not path.exists():
        raise FileNotFoundError(evidence_id)
    return path, evidence


def delete_evidence_file(username: str, program_id: str, evidence_id: str) -> None:
    evidence = get_evidence_by_id(username, program_id, evidence_id)
    if not evidence:
        raise KeyError(evidence_id)
    for key in evidence.get("section_keys", []) or [evidence.get("section_key", "")]:
        section = get_section(username, program_id, key)
        if section and not can_edit_section(username, program_id, section):
            raise PermissionError(f"{key} başlığı düzenlenebilir değil.")
    path = safe_stored_path(str(evidence.get("stored_path", "")))
    with transaction() as conn:
        conn.execute("DELETE FROM evidence_links WHERE program_id=? AND evidence_id=?", (program_id, evidence_id))
        conn.execute("UPDATE evidence SET deleted_at=?, deleted_by=? WHERE program_id=? AND id=?", (now_iso(), username, program_id, evidence_id))
    # Dosya fiziksel olarak tutulur; kayıt arşivlendiği için rapor ve arşiv listelerinde görünmez.
    log_activity("Kanıt arşivlendi", str(evidence.get("code", evidence_id)), username, program_id)


def table_rows_from_json(raw_json: str) -> list[dict[str, Any]]:
    try:
        raw = json.loads(raw_json or "{}")
    except Exception:
        return []
    if isinstance(raw, list):
        return [row for row in raw if isinstance(row, dict)]
    if isinstance(raw, dict) and isinstance(raw.get("columns"), list) and isinstance(raw.get("data"), list):
        columns = [str(col) for col in raw.get("columns", [])]
        rows: list[dict[str, Any]] = []
        for values in raw.get("data", []):
            if not isinstance(values, list):
                continue
            rows.append({columns[idx]: values[idx] if idx < len(values) else "" for idx in range(len(columns))})
        return rows
    return []


def table_meta_from_json(raw_json: str) -> dict[str, Any]:
    try:
        raw = json.loads(raw_json or "{}")
    except Exception:
        return {}
    if isinstance(raw, dict) and isinstance(raw.get("meta"), dict):
        return raw.get("meta", {})
    return {}


def table_json_from_rows(rows: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> str:
    safe_rows = _json_safe(rows if isinstance(rows, list) else [])
    if not isinstance(safe_rows, list):
        safe_rows = []
    columns: list[str] = []
    for row in safe_rows:
        if not isinstance(row, dict):
            continue
        for key in row.keys():
            if key not in columns:
                columns.append(str(key))
    clean_meta = _json_safe(meta if isinstance(meta, dict) else {})
    if not isinstance(clean_meta, dict):
        clean_meta = {}
    if isinstance(clean_meta.get("columns"), list):
        columns = [str(col) for col in clean_meta.get("columns", []) if str(col).strip()]
    data = [[row.get(col, "") if isinstance(row, dict) else "" for col in columns] for row in safe_rows]
    clean_meta["columns"] = columns
    return json.dumps(
        _json_safe({"columns": columns, "index": list(range(len(safe_rows))), "data": data, "meta": clean_meta}),
        ensure_ascii=False,
        allow_nan=False,
    )


def list_tables(username: str, program_id: str, section_key: str | None = None) -> list[dict[str, Any]]:
    role = assert_program_access(username, program_id)
    with get_conn() as conn:
        if section_key:
            if not _section_access_allowed(username, program_id, section_key):
                raise PermissionError("Bu başlığa erişim yetkiniz yok.")
            rows = conn.execute(
                "SELECT * FROM data_tables WHERE program_id=? AND section_key=? AND COALESCE(deleted_at,'')='' ORDER BY updated_at DESC",
                (program_id, section_key),
            ).fetchall()
        else:
            assigned = assigned_section_keys(username, program_id) if role == EDITOR_ROLE else set()
            if assigned:
                placeholders = ",".join("?" for _ in assigned)
                rows = conn.execute(
                    f"SELECT * FROM data_tables WHERE program_id=? AND section_key IN ({placeholders}) AND COALESCE(deleted_at,'')='' ORDER BY updated_at DESC",
                    [program_id, *sorted(assigned)],
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM data_tables WHERE program_id=? AND COALESCE(deleted_at,'')='' ORDER BY updated_at DESC",
                    (program_id,),
                ).fetchall()
    tables = rows_to_dicts(rows)
    for table in tables:
        raw_json = str(table.get("data_json", "") or "")
        table["rows"] = _json_safe(table_rows_from_json(raw_json))
        table["meta"] = _json_safe(table_meta_from_json(raw_json))
    return _json_safe(tables)


def save_table(username: str, program_id: str, section_key: str, table_name: str, rows: list[dict[str, Any]], meta: dict[str, Any] | None = None, table_id: str = "") -> dict[str, Any]:
    section = get_section(username, program_id, section_key)
    if not section:
        raise KeyError(section_key)
    if not can_edit_section(username, program_id, section):
        raise PermissionError("Bu başlık düzenlenebilir değil.")
    clean_table_name = table_name.strip()
    if not clean_table_name:
        raise ValueError("Tablo adı boş olamaz.")
    data_json = table_json_from_rows(rows, meta)
    clean_table_id = str(table_id or "").strip()
    program = get_program(program_id) or {"id": program_id, "program_name": program_id}
    with transaction() as conn:
        if clean_table_id:
            existing = conn.execute(
                "SELECT id, section_key FROM data_tables WHERE program_id=? AND id=? AND COALESCE(deleted_at,'')=''",
                (program_id, clean_table_id),
            ).fetchone()
            if not existing:
                raise KeyError(clean_table_id)
            source_section = get_section(username, program_id, str(existing["section_key"] or ""))
            if source_section and not can_edit_section(username, program_id, source_section):
                raise PermissionError("Kaynak tablo başlığı düzenlenebilir değil.")
            table_id = existing["id"]
            conn.execute(
                "UPDATE data_tables SET section_key=?, table_name=?, data_json=?, updated_at=? WHERE program_id=? AND id=?",
                (section_key, clean_table_name, data_json, now_iso(), program_id, table_id),
            )
        else:
            existing = conn.execute(
                "SELECT id FROM data_tables WHERE program_id=? AND section_key=? AND table_name=? AND COALESCE(deleted_at,'')='' ORDER BY updated_at DESC LIMIT 1",
                (program_id, section_key, clean_table_name),
            ).fetchone()
            if existing:
                table_id = existing["id"]
                conn.execute(
                    "UPDATE data_tables SET data_json=?, updated_at=? WHERE program_id=? AND id=?",
                    (data_json, now_iso(), program_id, table_id),
                )
            else:
                table_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO data_tables(id,program_id,section_key,table_name,data_json,updated_at) VALUES(?,?,?,?,?,?)",
                    (table_id, program_id, section_key, clean_table_name, data_json, now_iso()),
                )
    write_table_snapshot(
        program,
        section_key=section_key,
        table_id=str(table_id),
        table_name=clean_table_name,
        data_json=data_json,
        actor=username,
    )
    log_activity("Tablo kaydedildi", f"{clean_table_name} -> {section_key}", username, program_id)
    return next((row for row in list_tables(username, program_id, section_key) if row.get("id") == table_id), {})


def attach_table_to_section(username: str, program_id: str, table_id: str, section_key: str, table_name: str = "") -> dict[str, Any]:
    assert_program_access(username, program_id)
    section = get_section(username, program_id, section_key)
    if not section:
        raise KeyError(section_key)
    if not can_edit_section(username, program_id, section):
        raise PermissionError("Bu başlık düzenlenebilir değil.")
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM data_tables WHERE program_id=? AND id=? AND COALESCE(deleted_at,'')=''",
            (program_id, table_id),
        ).fetchone()
    source = row_to_dict(row)
    if not source:
        raise KeyError(table_id)
    source_section_key = str(source.get("section_key", "") or "")
    if not _section_access_allowed(username, program_id, source_section_key):
        raise PermissionError("Kaynak tabloya erişim yetkiniz yok.")
    next_name = (table_name or source.get("table_name") or "Bağlı Tablo").strip()
    raw_json = str(source.get("data_json", "") or "")
    saved = save_table(username, program_id, section_key, next_name, table_rows_from_json(raw_json), table_meta_from_json(raw_json))
    log_activity("Tablo bağlandı", f"{next_name} -> {section_key}", username, program_id)
    return saved


def delete_table(username: str, program_id: str, table_id: str) -> None:
    assert_program_access(username, program_id)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM data_tables WHERE program_id=? AND id=? AND COALESCE(deleted_at,'')=''",
            (program_id, table_id),
        ).fetchone()
    table = row_to_dict(row)
    if not table:
        raise KeyError(table_id)
    section = get_section(username, program_id, str(table.get("section_key", "")))
    if section and not can_edit_section(username, program_id, section):
        raise PermissionError("Bu başlık düzenlenebilir değil.")
    with transaction() as conn:
        archived_name = f"{table.get('table_name', table_id)} [arşiv {now_iso()}]"[:240]
        conn.execute("UPDATE data_tables SET deleted_at=?, deleted_by=?, updated_at=?, table_name=? WHERE program_id=? AND id=?", (now_iso(), username, now_iso(), archived_name, program_id, table_id))
    log_activity("Tablo arşivlendi", str(table.get("table_name", table_id)), username, program_id)


def latest_revision_note(program_id: str, section_key: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            """SELECT * FROM section_approvals
               WHERE program_id=? AND section_key=? AND status=?
               ORDER BY created_at DESC LIMIT 1""",
            (program_id, section_key, REVISION),
        ).fetchone()
    return row_to_dict(row)


def approval_history(username: str, program_id: str, section_key: str = "") -> list[dict[str, Any]]:
    assert_program_access(username, program_id)
    clean_key = str(section_key or "").strip()
    if clean_key and not _section_access_allowed(username, program_id, clean_key):
        raise PermissionError("Bu başlığa erişim yetkiniz yok.")
    with get_conn() as conn:
        if clean_key:
            rows = conn.execute(
                """SELECT * FROM section_approvals
                   WHERE program_id=? AND section_key=?
                   ORDER BY created_at DESC""",
                (program_id, clean_key),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM section_approvals
                   WHERE program_id=?
                   ORDER BY created_at DESC""",
                (program_id,),
            ).fetchall()
    return rows_to_dicts(rows)


def _section_key_value(section: dict[str, Any]) -> str:
    return str(section.get("section_key", "") or "").strip()


def _section_report_blob(section: dict[str, Any], include_puko: bool = True) -> str:
    fields = ["report_text"]
    if include_puko:
        fields.extend(["planla", "uygula", "kontrol", "onlem"])
    return "\n".join(str(section.get(field, "") or "") for field in fields)


def _word_count(value: str) -> int:
    return len(re.findall(r"\w+", str(value or ""), flags=re.UNICODE))


def _code_is_cited(text: str, code: str) -> bool:
    clean_code = str(code or "").strip()
    if not clean_code:
        return False
    pattern = rf"(?<![\w.-]){re.escape(clean_code)}(?![\w.-])"
    return bool(re.search(pattern, str(text or ""), flags=re.IGNORECASE | re.UNICODE))


def _criterion_like_section(section_key: str) -> bool:
    return bool(re.match(r"^(?:\d|ES\b)", str(section_key or "").strip(), flags=re.IGNORECASE))


def _guide_for_quality(program_id: str, section_key: str) -> dict[str, Any]:
    program = get_program(program_id) or {}
    return profile_section_guide(program.get("accreditation_profile", "MEDEK"), section_key)


def quality_for_section(username: str, program_id: str, section: dict[str, Any]) -> dict[str, Any]:
    section_key = _section_key_value(section)
    text = str(section.get("report_text", "") or "")
    report_blob = _section_report_blob(section)
    words = _word_count(text)
    evidence_rows = list_evidence(username, program_id, section_key)
    table_rows = list_tables(username, program_id, section_key)
    evidence_count = len(evidence_rows)
    table_count = len(table_rows)
    puko_count = sum(1 for field in ["planla", "uygula", "kontrol", "onlem"] if str(section.get(field, "") or "").strip())
    guide = _guide_for_quality(program_id, section_key)
    required_tables = [str(item).strip() for item in guide.get("required_tables", []) if str(item).strip()]
    table_required = bool(guide.get("table") or guide.get("requires_table") or required_tables)
    evidence_codes = [str(row.get("code", "") or "").strip() for row in evidence_rows if str(row.get("code", "") or "").strip()]
    cited_evidence_codes = [code for code in evidence_codes if _code_is_cited(report_blob, code)]
    uncited_evidence_codes = [code for code in evidence_codes if code not in cited_evidence_codes]

    score = (
        int(min(words, 420) / 420 * 42)
        + min(evidence_count, 3) * 10
        + min(table_count, 2) * 8
        + puko_count * 6
    )
    risks: list[str] = []
    if words < 120:
        risks.append("Metin kısa")
    if evidence_count == 0 and _criterion_like_section(section_key):
        risks.append("Kanıt yok")
    if uncited_evidence_codes:
        risks.append("Kanıt kodu metinde geçmiyor")
        score -= min(len(uncited_evidence_codes) * 4, 12)
    if table_required and table_count == 0:
        risks.append("Zorunlu/önerilen tablo eksik")
        score -= 12
    if _criterion_like_section(section_key) and puko_count < 4:
        risks.append("PUKÖ döngüsü eksik")

    return {
        "score": max(0, min(100, score)),
        "words": words,
        "evidence": evidence_count,
        "tables": table_count,
        "puko": puko_count,
        "table_required": table_required,
        "required_tables": required_tables,
        "evidence_codes": evidence_codes,
        "cited_evidence": len(cited_evidence_codes),
        "cited_evidence_codes": cited_evidence_codes,
        "uncited_evidence": len(uncited_evidence_codes),
        "uncited_evidence_codes": uncited_evidence_codes,
        "risk": risks,
    }


def _preflight_check(severity: str, code: str, title: str, detail: str, action: str) -> dict[str, str]:
    return {"severity": severity, "code": code, "title": title, "detail": detail, "action": action}


def _section_preflight_row(username: str, program_id: str, section: dict[str, Any]) -> dict[str, Any]:
    section_key = _section_key_value(section)
    quality = quality_for_section(username, program_id, section)
    checks: list[dict[str, str]] = []
    words = int(quality.get("words", 0) or 0)
    evidence_count = int(quality.get("evidence", 0) or 0)
    table_count = int(quality.get("tables", 0) or 0)
    puko_count = int(quality.get("puko", 0) or 0)
    approval_status = str(section.get("approval_status") or "Taslak")
    status = str(section.get("status") or "")

    if words == 0:
        checks.append(_preflight_check("blocker", "empty_text", "Rapor metni boş", "Başlık nihai raporda boş görünecek.", "Rapor metnini yazın veya içe aktarma/AI taslak ile doldurun."))
    elif words < 180:
        checks.append(_preflight_check("warning", "short_text", "Metin derinliği zayıf", f"{words} kelime var; denetim dili için süreç, veri, kanıt ve sonuç bağlantısı güçlendirilmeli.", "Metni iddia, kanıt, bulgu ve iyileştirme akışıyla genişletin."))

    if approval_status == REVISION or status == REVISION:
        revision = latest_revision_note(program_id, section_key) or {}
        detail = str(revision.get("note") or "Revizyon gerekçesi kapatılmamış görünüyor.")
        checks.append(_preflight_check("blocker", "revision_open", "Revizyon açık", detail, "Revizyon notunu karşılayıp başlığı yeniden onaya gönderin."))
    elif approval_status != APPROVED:
        checks.append(_preflight_check("warning", "not_approved", "Onay tamamlanmadı", f"Onay durumu: {approval_status}.", "Nihai rapor öncesi ilgili onaylayıcıdan onay alın."))

    if _criterion_like_section(section_key) and evidence_count == 0:
        checks.append(_preflight_check("blocker", "no_evidence", "Kanıt bağlı değil", "Ölçüt başlığı kanıtsız kalmış.", "İlgili kurul kararı, analiz raporu, tablo veya uygulama kaydını kanıt olarak bağlayın."))
    elif quality.get("uncited_evidence_codes"):
        codes = ", ".join(quality.get("uncited_evidence_codes", [])[:6])
        checks.append(_preflight_check("warning", "uncited_evidence", "Kanıt metinde atıfsız", f"Bağlı olup metinde geçmeyen kanıt kodları: {codes}.", "Rapor metninde ilgili cümlelerin sonuna kanıt kodlarını ekleyin."))

    if quality.get("table_required") and table_count == 0:
        required = ", ".join(quality.get("required_tables", [])[:3]) or "Bu başlık için tablo/veri seti bekleniyor."
        checks.append(_preflight_check("blocker", "missing_required_table", "Zorunlu/önerilen tablo eksik", required, "Tabloyu veri girişi ekranında oluşturup başlığa bağlayın."))

    if _criterion_like_section(section_key) and puko_count < 4:
        checks.append(_preflight_check("warning", "puko_incomplete", "PUKÖ döngüsü eksik", f"{puko_count}/4 PUKÖ alanı dolu.", "Planla, Uygula, Kontrol Et ve Önlem Al alanlarını gerçek karar/sonuç bilgisiyle tamamlayın."))

    if int(quality.get("score", 0) or 0) < 70:
        checks.append(_preflight_check("warning", "low_quality", "Kalite skoru düşük", f"Kalite skoru {quality.get('score', 0)}/100.", "Metin, kanıt, tablo ve PUKÖ eksiklerini kapatıp kalite skorunu yenileyin."))

    blocker_count = sum(1 for item in checks if item["severity"] == "blocker")
    warning_count = sum(1 for item in checks if item["severity"] == "warning")
    severity = "blocker" if blocker_count else "warning" if warning_count else "ready"
    return {
        "section_key": section_key,
        "section_title": section.get("section_title", ""),
        "main_title": section.get("main_title", ""),
        "report_group_title": section.get("report_group_title", "") or section.get("main_title", ""),
        "quality_score": int(quality.get("score", 0) or 0),
        "words": words,
        "evidence_count": evidence_count,
        "cited_evidence": int(quality.get("cited_evidence", 0) or 0),
        "uncited_evidence": int(quality.get("uncited_evidence", 0) or 0),
        "uncited_evidence_codes": quality.get("uncited_evidence_codes", []),
        "table_count": table_count,
        "table_required": bool(quality.get("table_required")),
        "puko_count": puko_count,
        "approval_status": approval_status,
        "status": status,
        "severity": severity,
        "blocker_count": blocker_count,
        "warning_count": warning_count,
        "checks": checks,
    }


def report_preflight_payload(username: str, program_id: str) -> dict[str, Any]:
    assert_program_access(username, program_id)
    sections = list_sections(username, program_id)
    rows = [_section_preflight_row(username, program_id, section) for section in sections]
    blocker_count = sum(int(row.get("blocker_count", 0) or 0) for row in rows)
    warning_count = sum(int(row.get("warning_count", 0) or 0) for row in rows)
    ready_sections = sum(1 for row in rows if row.get("severity") == "ready")
    avg_quality = round(sum(int(row.get("quality_score", 0) or 0) for row in rows) / len(rows), 1) if rows else 0
    cited_total = sum(int(row.get("cited_evidence", 0) or 0) for row in rows)
    evidence_total = sum(int(row.get("evidence_count", 0) or 0) for row in rows)
    citation_percent = round(cited_total / evidence_total * 100, 1) if evidence_total else 0
    top_actions: list[dict[str, Any]] = []
    for row in rows:
        for check in row.get("checks", []):
            if check.get("severity") == "blocker":
                top_actions.append({"section_key": row.get("section_key"), "section_title": row.get("section_title"), **check})
        if len(top_actions) >= 8:
            break
    if len(top_actions) < 8:
        for row in rows:
            for check in row.get("checks", []):
                if check.get("severity") == "warning":
                    top_actions.append({"section_key": row.get("section_key"), "section_title": row.get("section_title"), **check})
                if len(top_actions) >= 8:
                    break
            if len(top_actions) >= 8:
                break
    return {
        "generated_at": now_iso(),
        "ready": blocker_count == 0,
        "blocker_count": blocker_count,
        "warning_count": warning_count,
        "total_sections": len(rows),
        "ready_sections": ready_sections,
        "avg_quality": avg_quality,
        "citation_percent": citation_percent,
        "summary": {
            "ready_label": "Denetime hazır" if blocker_count == 0 else "Bloklayıcı eksikler var",
            "ready_sections": ready_sections,
            "total_sections": len(rows),
            "blockers": blocker_count,
            "warnings": warning_count,
            "avg_quality": avg_quality,
            "citation_percent": citation_percent,
        },
        "top_actions": top_actions,
        "rows": rows,
    }


def assert_report_export_ready(username: str, program_id: str) -> dict[str, Any]:
    payload = report_preflight_payload(username, program_id)
    if not payload.get("ready"):
        actions = payload.get("top_actions", [])[:3]
        details = "; ".join(f"{item.get('section_key')}: {item.get('title')}" for item in actions)
        raise ValueError(f"Nihai rapor için bloklayıcı eksikler var. {details}")
    return payload


def apply_ai_draft_to_section(username: str, program_id: str, section_key: str, text: str) -> dict[str, Any]:
    section = get_section(username, program_id, section_key)
    if not section:
        raise KeyError(section_key)
    clean_text = str(text or "").strip()
    if not clean_text:
        raise ValueError("Uygulanacak AI taslak metni boş olamaz.")
    note = f"AI tam rapor taslağı {now_iso()} tarihinde editör uygulaması için bölüme aktarıldı."
    current_notes = str(section.get("notes", "") or "").strip()
    payload = {
        "status": READY,
        "report_text": clean_text,
        "planla": section.get("planla", "") or "",
        "uygula": section.get("uygula", "") or "",
        "kontrol": section.get("kontrol", "") or "",
        "onlem": section.get("onlem", "") or "",
        "notes": f"{current_notes}\n\n{note}".strip(),
        "deadline": section.get("deadline", "") or "",
    }
    updated = update_section(username, program_id, section_key, payload)
    log_activity("AI taslak uygulandı", section_key, username, program_id)
    return updated


def control_rows(username: str, program_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for section in list_sections(username, program_id):
        quality = quality_for_section(username, program_id, section)
        revision = latest_revision_note(program_id, str(section.get("section_key", "")))
        editor_access = "Açık"
        if section.get("approval_status") in {APPROVED, SUBMITTED}:
            editor_access = "Kilitli"
        rows.append(
            {
                "Rapor Bölümü": section.get("report_group_title", ""),
                "Ana Ölçüt": section.get("report_subgroup_title") or section.get("main_title", ""),
                "Kod": section.get("section_key", ""),
                "Başlık": section.get("section_title", ""),
                "Çalışma Durumu": section.get("status", ""),
                "Onay Durumu": section.get("approval_status", "Taslak"),
                "Editör / Hazırlayıcı Erişimi": editor_access,
                "Kalite": quality["score"],
                "Metin": quality["words"],
                "Kanıt": quality["evidence"],
                "Tablo": quality["tables"],
                "PUKÖ": quality["puko"],
                "Son Revizyon Notu": (revision or {}).get("note", ""),
                "Revizyon Tarihi": (revision or {}).get("created_at", ""),
                "Onaylayan": section.get("approved_by", ""),
                "Onay Tarihi": section.get("approved_at", ""),
                "Termin": section.get("deadline", ""),
                "Güncelleme": section.get("updated_at", ""),
            }
        )
    return rows


def search_sections(username: str, program_id: str, query: str) -> list[dict[str, Any]]:
    assert_program_access(username, program_id)
    needle = query.strip().lower()
    if not needle:
        return []
    results: list[dict[str, Any]] = []
    for section in list_sections(username, program_id):
        section_key = str(section.get("section_key", ""))
        text_blob = " ".join(
            str(section.get(field, "") or "")
            for field in [
                "section_key",
                "report_group_title",
                "report_subgroup_title",
                "main_title",
                "section_title",
                "status",
                "approval_status",
                "report_text",
                "planla",
                "uygula",
                "kontrol",
                "onlem",
                "notes",
            ]
        ).lower()
        evidence = list_evidence(username, program_id, section_key)
        tables = list_tables(username, program_id, section_key)
        evidence_blob = " ".join(str(row.get(field, "") or "") for row in evidence for field in ["code", "original_name", "note"]).lower()
        table_blob = " ".join(str(table.get("table_name", "") or "") for table in tables).lower()
        approval_blob = " ".join(str(row.get(field, "") or "") for row in approval_history(username, program_id, section_key) for field in ["status", "requested_by", "decided_by", "note", "created_at"]).lower()
        if needle in text_blob or needle in evidence_blob or needle in table_blob or needle in approval_blob:
            results.append(
                {
                    "section_key": section_key,
                    "report_group_title": section.get("report_group_title", ""),
                    "report_subgroup_title": section.get("report_subgroup_title", ""),
                    "main_title": section.get("main_title", ""),
                    "section_title": section.get("section_title", ""),
                    "status": section.get("status", ""),
                    "approval_status": section.get("approval_status", ""),
                    "quality": quality_for_section(username, program_id, section),
                    "evidence_count": len(evidence),
                    "table_count": len(tables),
                    "snippet": str(section.get("report_text", "") or "")[:260],
                }
            )
    return results


def stats_payload(username: str, program_id: str) -> dict[str, Any]:
    assert_program_operation_permission(username, program_id, "stats.view")
    sections = list_sections(username, program_id)
    quality_rows = [quality_for_section(username, program_id, section) for section in sections]
    total = len(sections)
    by_report_group: dict[str, dict[str, Any]] = {}
    by_measure: dict[str, dict[str, Any]] = {}
    for section, quality in zip(sections, quality_rows):
        main = str(section.get("report_group_title") or section.get("main_title", ""))
        subgroup = str(section.get("report_subgroup_title", "") or "")
        bucket = by_report_group.setdefault(
            main,
            {
                "main_title": main,
                "report_group_title": main,
                "total": 0,
                "ready": 0,
                "approved": 0,
                "submitted": 0,
                "revision": 0,
                "quality_total": 0,
                "first_section_key": section.get("section_key", ""),
                "subcriteria": {},
            },
        )
        bucket["total"] += 1
        bucket["quality_total"] += quality["score"]
        if not bucket.get("first_section_key"):
            bucket["first_section_key"] = section.get("section_key", "")
        if section.get("status") in {READY, COMPLETED}:
            bucket["ready"] += 1
        if section.get("approval_status") == APPROVED:
            bucket["approved"] += 1
        if section.get("approval_status") == SUBMITTED:
            bucket["submitted"] += 1
        if section.get("approval_status") == REVISION or section.get("status") == REVISION:
            bucket["revision"] += 1
        if subgroup:
            measure_bucket = by_measure.setdefault(
                subgroup,
                {
                    "main_title": subgroup,
                    "report_group_title": main,
                    "total": 0,
                    "ready": 0,
                    "approved": 0,
                    "submitted": 0,
                    "revision": 0,
                    "quality_total": 0,
                    "first_section_key": section.get("section_key", ""),
                },
            )
            measure_bucket["total"] += 1
            measure_bucket["quality_total"] += quality["score"]
            if section.get("status") in {READY, COMPLETED}:
                measure_bucket["ready"] += 1
            if section.get("approval_status") == APPROVED:
                measure_bucket["approved"] += 1
            if section.get("approval_status") == SUBMITTED:
                measure_bucket["submitted"] += 1
            if section.get("approval_status") == REVISION or section.get("status") == REVISION:
                measure_bucket["revision"] += 1

            sub_bucket = bucket["subcriteria"].setdefault(
                subgroup,
                {
                    "main_title": subgroup,
                    "total": 0,
                    "ready": 0,
                    "approved": 0,
                    "submitted": 0,
                    "revision": 0,
                    "quality_total": 0,
                    "first_section_key": section.get("section_key", ""),
                },
            )
            sub_bucket["total"] += 1
            sub_bucket["quality_total"] += quality["score"]
            if section.get("status") in {READY, COMPLETED}:
                sub_bucket["ready"] += 1
            if section.get("approval_status") == APPROVED:
                sub_bucket["approved"] += 1
            if section.get("approval_status") == SUBMITTED:
                sub_bucket["submitted"] += 1
            if section.get("approval_status") == REVISION or section.get("status") == REVISION:
                sub_bucket["revision"] += 1
    report_groups = []
    for item in by_report_group.values():
        total_count = max(int(item["total"]), 1)
        subcriteria = []
        for sub_item in item.pop("subcriteria", {}).values():
            sub_total = max(int(sub_item["total"]), 1)
            subcriteria.append(
                {
                    **sub_item,
                    "readiness_percent": round((int(sub_item["ready"]) / sub_total) * 100, 1),
                    "approval_percent": round((int(sub_item["approved"]) / sub_total) * 100, 1),
                    "quality_avg": round(float(sub_item["quality_total"]) / sub_total, 1),
                }
            )
        report_groups.append(
            {
                **item,
                "subcriteria": subcriteria,
                "readiness_percent": round((int(item["ready"]) / total_count) * 100, 1),
                "approval_percent": round((int(item["approved"]) / total_count) * 100, 1),
                "quality_avg": round(float(item["quality_total"]) / total_count, 1),
            }
        )
    measure_criteria = []
    for item in by_measure.values():
        total_count = max(int(item["total"]), 1)
        measure_criteria.append(
            {
                **item,
                "readiness_percent": round((int(item["ready"]) / total_count) * 100, 1),
                "approval_percent": round((int(item["approved"]) / total_count) * 100, 1),
                "quality_avg": round(float(item["quality_total"]) / total_count, 1),
            }
        )
    low_quality = [
        {
            "section_key": section.get("section_key", ""),
            "section_title": section.get("section_title", ""),
            "main_title": section.get("main_title", ""),
            "report_group_title": section.get("report_group_title", ""),
            "report_subgroup_title": section.get("report_subgroup_title", ""),
            "quality": quality["score"],
            "words": quality["words"],
            "evidence": quality["evidence"],
            "tables": quality["tables"],
            "puko": quality["puko"],
        }
        for section, quality in zip(sections, quality_rows)
        if quality["score"] < 60
    ]
    low_quality.sort(key=lambda row: row["quality"])
    return {
        "summary": dashboard(username, program_id)["summary"],
        "criteria": measure_criteria,
        "measure_criteria": measure_criteria,
        "report_groups": report_groups,
        "totals": {
            "evidence": len(list_evidence(username, program_id)),
            "tables": len(list_tables(username, program_id)),
            "avg_quality": round(sum(row["score"] for row in quality_rows) / total, 1) if total else 0,
            "critical_sections": len(low_quality),
        },
        "critical": low_quality[:30],
    }


def deadline_rows(username: str, program_id: str) -> list[dict[str, Any]]:
    return [
        {
            "section_key": row.get("section_key", ""),
            "report_group_title": row.get("report_group_title", ""),
            "report_subgroup_title": row.get("report_subgroup_title", ""),
            "main_title": row.get("main_title", ""),
            "section_title": row.get("section_title", ""),
            "deadline": row.get("deadline", ""),
            "status": row.get("status", ""),
        }
        for row in list_sections(username, program_id)
    ]


def update_deadlines(username: str, program_id: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    role = assert_program_access(username, program_id)
    if role not in {SUPER_ADMIN_ROLE, TENANT_ADMIN_ROLE}:
        raise PermissionError("Termin planını yalnızca Süper Admin veya Kurum Admin güncelleyebilir.")
    with transaction() as conn:
        for row in rows:
            key = str(row.get("section_key", "")).strip()
            if not key:
                continue
            conn.execute(
                "UPDATE sections SET deadline=?, updated_at=? WHERE program_id=? AND section_key=?",
                (str(row.get("deadline", "") or ""), now_iso(), program_id, key),
            )
    log_activity("Termin planı güncellendi", f"{len(rows)} satır", username, program_id)
    return deadline_rows(username, program_id)


def bulk_update_status(username: str, program_id: str, section_keys: list[str], status: str) -> dict[str, Any]:
    role = assert_program_access(username, program_id)
    if role == READONLY_ROLE:
        raise PermissionError("Toplu işlem için düzenleme yetkisi gerekir.")
    clean_status = str(status or "").strip()
    if clean_status not in STATUS_OPTIONS:
        raise ValueError("Geçersiz durum.")
    keys = [str(key).strip() for key in section_keys if str(key).strip()]
    if not keys:
        raise ValueError("En az bir başlık seçilmelidir.")
    updated = 0
    skipped: list[str] = []
    with transaction() as conn:
        for key in keys:
            section = get_section(username, program_id, key)
            if not section or not can_edit_section(username, program_id, section):
                skipped.append(key)
                continue
            conn.execute(
                """INSERT INTO section_versions(
                    id, program_id, section_key, saved_at, status, report_text, planla, uygula,
                    kontrol, onlem, notes, deadline, change_summary
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()),
                    program_id,
                    key,
                    now_iso(),
                    section.get("status", ""),
                    section.get("report_text", "") or "",
                    section.get("planla", "") or "",
                    section.get("uygula", "") or "",
                    section.get("kontrol", "") or "",
                    section.get("onlem", "") or "",
                    section.get("notes", "") or "",
                    section.get("deadline", "") or "",
                    f"Bulk status -> {clean_status}",
                ),
            )
            conn.execute(
                "UPDATE sections SET status=?, updated_at=? WHERE program_id=? AND section_key=?",
                (clean_status, now_iso(), program_id, key),
            )
            updated += 1
    log_activity("Toplu durum güncellendi", f"{updated}/{len(keys)} -> {clean_status}", username, program_id)
    return {"requested": len(keys), "updated": updated, "skipped": skipped, "status": clean_status}


def preview_payload(username: str, program_id: str) -> dict[str, Any]:
    sections = []
    for section in list_sections(username, program_id):
        section_key = str(section.get("section_key", ""))
        sections.append(
            {
                **section,
                "quality": quality_for_section(username, program_id, section),
                "evidence": list_evidence(username, program_id, section_key),
                "tables": list_tables(username, program_id, section_key),
                "revision": latest_revision_note(program_id, section_key),
            }
        )
    return _json_safe({"settings": get_settings(program_id), "sections": sections})


def record_export(username: str, program_id: str, export_type: str, file_name: str, note: str = "") -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO export_history(id,program_id,export_type,file_name,actor,created_at,note) VALUES(?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), program_id, export_type, file_name, username, now_iso(), note),
        )


def export_history(username: str, program_id: str, limit: int = 100) -> list[dict[str, Any]]:
    assert_program_access(username, program_id)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM export_history WHERE program_id=? ORDER BY created_at DESC LIMIT ?",
            (program_id, limit),
        ).fetchall()
    return rows_to_dicts(rows)


def activity_rows(username: str, program_id: str, limit: int = 100) -> list[dict[str, Any]]:
    role = assert_program_access(username, program_id)
    with get_conn() as conn:
        if role == ADMIN_ROLE:
            rows = conn.execute(
                """SELECT ts, action, detail, actor, program_id
                   FROM activity_log
                   WHERE program_id=? OR program_id=''
                   ORDER BY ts DESC LIMIT ?""",
                (program_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT ts, action, detail, actor, program_id
                   FROM activity_log
                   WHERE actor=? AND (program_id=? OR program_id='')
                   ORDER BY ts DESC LIMIT ?""",
                (username, program_id, limit),
            ).fetchall()
    return rows_to_dicts(rows)


def login_attempt_rows_admin(username: str, limit: int = 100) -> list[dict[str, Any]]:
    actor = assert_operation_permission(username, "user.login_attempts.view")
    with get_conn() as conn:
        if user_is_global_admin(actor):
            rows = conn.execute(
                "SELECT username, success, note, created_at FROM login_attempts ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT la.username, la.success, la.note, la.created_at
                   FROM login_attempts la
                   JOIN users u ON u.username=la.username
                   WHERE COALESCE(u.tenant_id, ?) = ?
                     AND COALESCE(u.deleted_at,'')=''
                   ORDER BY la.created_at DESC LIMIT ?""",
                (DEFAULT_TENANT_ID, user_tenant_id(actor), limit),
            ).fetchall()
    return rows_to_dicts(rows)


PROGRAM_BACKUP_TABLES = [
    "programs",
    "sections",
    "evidence",
    "evidence_links",
    "data_tables",
    "settings",
    "section_approvals",
    "section_comments",
    "section_versions",
    "edit_locks",
    "export_history",
    "export_jobs",
    "notification_events",
    "notification_reads",
    "workflow_runs",
    "workflow_run_items",
    "section_collaboration_sessions",
    "section_template_bank",
    "clause_library",
    "content_blocks",
    "content_block_versions",
    "consistency_check_runs",
    "report_quality_snapshots",
    "auditor_share_links",
]

PROGRAM_BACKUP_CHILD_TABLES = [
    table for table in PROGRAM_BACKUP_TABLES
    if table not in {"programs", "settings", "notification_reads"}
]


def _program_notification_event_ids(conn, program_id: str) -> list[str]:
    rows = conn.execute("SELECT id FROM notification_events WHERE program_id=?", (program_id,)).fetchall()
    return [str(row["id"] or "") for row in rows if str(row["id"] or "")]


def backup_payload(username: str, program_id: str) -> dict[str, Any]:
    assert_admin(username)
    payload: dict[str, Any] = {"schema_version": "web-v1", "created_at": now_iso(), "program_id": program_id, "tables": {}}
    with get_conn() as conn:
        for table in PROGRAM_BACKUP_TABLES:
            if table == "settings":
                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            elif table == "programs":
                rows = conn.execute("SELECT * FROM programs WHERE id=?", (program_id,)).fetchall()
            elif table == "evidence_links":
                rows = conn.execute("SELECT * FROM evidence_links WHERE program_id=?", (program_id,)).fetchall()
            elif table == "notification_reads":
                rows = conn.execute(
                    """SELECT nr.* FROM notification_reads nr
                       JOIN notification_events ne ON ne.id=nr.event_id
                       WHERE ne.program_id=?""",
                    (program_id,),
                ).fetchall()
            else:
                rows = conn.execute(f"SELECT * FROM {table} WHERE program_id=?", (program_id,)).fetchall()
            payload["tables"][table] = rows_to_dicts(rows)
    return payload


def _table_column_names(conn, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [str(row["name"]) for row in rows]


def restore_backup_payload_admin(username: str, program_id: str, payload: dict[str, Any], overwrite: bool = False) -> dict[str, Any]:
    assert_admin(username)
    if not isinstance(payload, dict) or not isinstance(payload.get("tables"), dict):
        raise ValueError("Geçerli bir MEDEK JSON yedeği seçilmelidir.")
    allowed_tables = PROGRAM_BACKUP_TABLES
    child_tables = PROGRAM_BACKUP_CHILD_TABLES
    counts = {table: 0 for table in allowed_tables}
    with transaction() as conn:
        if not conn.execute("SELECT id FROM programs WHERE id=?", (program_id,)).fetchone():
            raise ValueError("Hedef program bulunamadı.")
        if overwrite:
            for event_id in _program_notification_event_ids(conn, program_id):
                conn.execute("DELETE FROM notification_reads WHERE event_id=?", (event_id,))
            for table in child_tables:
                conn.execute(f"DELETE FROM {table} WHERE program_id=?", (program_id,))
        tables = payload.get("tables") or {}
        payload_event_ids = {
            str(row.get("id", "") or "")
            for row in (tables.get("notification_events") or [])
            if isinstance(row, dict) and str(row.get("program_id", "") or "") == program_id
        }
        for table in allowed_tables:
            rows = tables.get(table) or []
            if not isinstance(rows, list):
                continue
            columns = _table_column_names(conn, table)
            if table == "settings":
                for row in rows:
                    if isinstance(row, dict) and "key" in row and "value" in row:
                        conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (str(row.get("key", "")), str(row.get("value", "") or "")))
                        counts[table] += 1
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                data = {key: row.get(key) for key in columns if key in row}
                if table == "programs":
                    if str(data.get("id", "")) != program_id:
                        continue
                    data["updated_at"] = now_iso()
                elif table == "notification_reads":
                    if str(data.get("event_id", "") or "") not in payload_event_ids:
                        continue
                else:
                    if str(data.get("program_id", "")) != program_id:
                        continue
                    if table == "evidence_links":
                        exists = conn.execute(
                            "SELECT 1 FROM evidence_links WHERE program_id=? AND evidence_id=? AND section_key=?",
                            (program_id, data.get("evidence_id", ""), data.get("section_key", "")),
                        ).fetchone()
                        if exists:
                            continue
                if not data:
                    continue
                placeholders = ",".join("?" for _ in data)
                column_sql = ",".join(data.keys())
                verb = "INSERT OR IGNORE" if table in {"evidence_links", "notification_reads"} else "INSERT OR REPLACE"
                conn.execute(f"{verb} INTO {table}({column_sql}) VALUES({placeholders})", tuple(data.values()))
                counts[table] += 1
    log_activity("JSON yedeği geri yüklendi", f"{program_id} üzerine yaz={overwrite} {counts}", username, program_id)
    return {"ok": True, "program_id": program_id, "overwrite": overwrite, "restored": counts}


def system_status(username: str, program_id: str) -> dict[str, Any]:
    assert_admin(username)
    with get_conn() as conn:
        program_count = conn.execute("SELECT COUNT(*) AS n FROM programs WHERE is_active=1").fetchone()["n"]
        user_count = conn.execute("SELECT COUNT(*) AS n FROM users WHERE is_active=1").fetchone()["n"]
        activity_count = conn.execute("SELECT COUNT(*) AS n FROM activity_log").fetchone()["n"]
        login_count = conn.execute("SELECT COUNT(*) AS n FROM login_attempts").fetchone()["n"]
    database_label = "PostgreSQL" if MEDEK_DB_BACKEND == "postgresql" else str(SQLITE_PATH)
    return {
        "database_backend": MEDEK_DB_BACKEND,
        "database": database_label,
        "postgres_configured": bool(MEDEK_DATABASE_URL) if MEDEK_DB_BACKEND == "postgresql" else False,
        "evidence_dir": str(EVIDENCE_DIR),
        "organizational_storage_dir": str(ORG_STORAGE_DIR),
        "active_programs": int(program_count),
        "active_users": int(user_count),
        "activity_rows": int(activity_count),
        "login_rows": int(login_count),
        "program_id": program_id,
    }


def _clean_import_line(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\u00a0", " ")).strip()


def _fold_import_text(value: str) -> str:
    folded = unicodedata.normalize("NFKD", str(value or "").casefold()).replace("ı", "i")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


def _docx_blocks(data: bytes) -> list[dict[str, Any]]:
    import tempfile
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        document = Document(tmp_path)
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass

    blocks: list[dict[str, Any]] = []
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            line = _clean_import_line(Paragraph(child, document).text)
            if line:
                blocks.append({"type": "paragraph", "text": line})
        elif isinstance(child, CT_Tbl):
            table = Table(child, document)
            matrix: list[list[str]] = []
            for row in table.rows:
                cells = [_clean_import_line(cell.text) for cell in row.cells]
                if any(cells):
                    matrix.append(cells)
            if matrix:
                blocks.append({"type": "table", "rows": matrix})
    return blocks


def _docx_lines(data: bytes) -> list[str]:
    lines: list[str] = []
    for block in _docx_blocks(data):
        if block.get("type") == "paragraph":
            lines.append(str(block.get("text", "")))
    return lines


def _docx_table_rows(matrix: list[list[str]]) -> tuple[list[dict[str, str]], list[str]]:
    if not matrix:
        return [], []
    width = max(len(row) for row in matrix)
    normalized = [row + [""] * (width - len(row)) for row in matrix]
    header_idx = 0
    for idx, row in enumerate(normalized):
        if sum(1 for cell in row if cell.strip()) >= max(1, min(2, width)):
            header_idx = idx
            break
    raw_columns = normalized[header_idx]
    columns: list[str] = []
    seen: dict[str, int] = {}
    for idx, column in enumerate(raw_columns):
        name = _clean_import_line(column) or f"Sütun {idx + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name} {seen[name]}"
        else:
            seen[name] = 1
        columns.append(name)
    rows: list[dict[str, str]] = []
    for row in normalized[header_idx + 1 :]:
        if not any(cell.strip() for cell in row):
            continue
        rows.append({columns[idx]: row[idx] for idx in range(width)})
    return rows, columns


def _import_heading_context(sections: list[dict[str, Any]]) -> tuple[re.Pattern[str] | None, dict[str, str], dict[str, str], dict[str, str], set[str]]:
    key_set = {str(section.get("section_key", "")) for section in sections}
    key_by_fold = {key.casefold(): key for key in key_set}
    key_pattern = "|".join(re.escape(key) for key in sorted(key_set, key=len, reverse=True))
    matcher = re.compile(rf"^\s*({key_pattern})(?:[\s\.:)\-\u2013\u2014]+|$)(.*)$", re.IGNORECASE) if key_pattern else None

    title_index: dict[str, str] = {}
    title_by_key: dict[str, str] = {}
    ignored_headings = {
        _fold_import_text("KAPAK"),
        _fold_import_text("ÖZ DEĞERLENDİRME RAPORU"),
        _fold_import_text("İÇİNDEKİLER"),
        _fold_import_text("RAPOR SONU KANIT DİZİNİ"),
    }
    for section in sections:
        key = str(section.get("section_key", ""))
        title = str(section.get("section_title", "") or "")
        if title:
            folded_title = _fold_import_text(title)
            title_index[folded_title] = key
            title_by_key[key] = folded_title
        for heading_key in ("report_group_title", "report_subgroup_title", "main_title"):
            heading = _fold_import_text(str(section.get(heading_key, "") or ""))
            if heading:
                ignored_headings.add(heading)
    return matcher, key_by_fold, title_index, title_by_key, ignored_headings


def _pdf_lines(data: bytes) -> list[str]:
    if not data.startswith(b"%PDF-"):
        raise ValueError("Geçerli bir PDF dosyası seçin.")
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("PDF içe aktarma için pypdf paketi yüklü değil. API bağımlılıklarını yeniden kurun.") from exc

    reader = PdfReader(BytesIO(data))
    lines: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        for raw_line in text.replace("\r", "\n").split("\n"):
            line = _clean_import_line(raw_line)
            lines.append(line)
    if not any(lines):
        raise ValueError("PDF metni çıkarılamadı. Taranmış/görüntü tabanlı PDF için OCR gerekir.")
    return lines


def _is_import_noise_line(line: str) -> bool:
    folded = _fold_import_text(line)
    if not folded:
        return False
    noise_prefixes = (
        "dokuman no",
        "ilk yayin tarihi",
        "revizyon tarihi",
        "revizyon no",
        "sayfa",
        "medek mesleki egitim degerlendirme",
        "32 evler mahallesi",
    )
    return any(folded.startswith(prefix) for prefix in noise_prefixes)


def _is_table_artifact_line(line: str) -> bool:
    clean = _clean_import_line(line)
    if clean.count("|") >= 2:
        return True
    cells = [cell for cell in re.split(r"\t+| {3,}", str(line or "").strip()) if cell.strip()]
    if len(cells) >= 4 and sum(1 for cell in cells if len(cell.strip()) <= 24) >= 3:
        return True
    return False


def _starts_import_list_item(line: str) -> bool:
    return bool(re.match(r"^\s*(?:[-*•●]\s+|\d{1,2}[.)]\s+|[a-zçğıöşü][.)]\s+)", line, re.IGNORECASE))


def _import_text_blocks(lines: list[str], source_type: str) -> list[str]:
    cleaned: list[str] = []
    for raw_line in lines:
        line = _clean_import_line(raw_line)
        if not line:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        if _is_import_noise_line(line) or _is_table_artifact_line(raw_line):
            continue
        cleaned.append(line)

    if source_type != "PDF":
        return [line for line in cleaned if line]

    blocks: list[str] = []
    current: list[str] = []
    for line in cleaned:
        if not line:
            if current:
                blocks.append(" ".join(current).strip())
                current = []
            continue
        if current and _starts_import_list_item(line):
            blocks.append(" ".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append(" ".join(current).strip())
    return [block for block in blocks if block]


def _report_import_buckets(sections: list[dict[str, Any]], lines: list[str]) -> dict[str, list[str]]:
    matcher, key_by_fold, title_index, title_by_key, ignored_headings = _import_heading_context(sections)

    buckets: dict[str, list[str]] = {}
    current_key = ""
    for line in lines:
        line = _clean_import_line(line)
        if not line:
            if current_key and buckets.get(current_key) and buckets[current_key][-1] != "":
                buckets[current_key].append("")
            continue
        match = matcher.match(line) if matcher else None
        if match:
            current_key = key_by_fold.get(match.group(1).casefold(), match.group(1))
            rest = match.group(2).strip()
            buckets.setdefault(current_key, [])
            if len(rest) > 40 and _fold_import_text(rest) != title_by_key.get(current_key, ""):
                buckets[current_key].append(rest)
            continue
        folded = _fold_import_text(line)
        if folded in title_index:
            current_key = title_index[folded]
            buckets.setdefault(current_key, [])
            continue
        if folded in ignored_headings or re.fullmatch(r"\d+", folded or ""):
            continue
        if current_key:
            buckets.setdefault(current_key, []).append(line)
    return buckets


def _infer_import_section_key(text: str, matcher: re.Pattern[str] | None, key_by_fold: dict[str, str], title_index: dict[str, str]) -> str:
    line = _clean_import_line(text)
    if not line:
        return ""
    match = matcher.search(line) if matcher else None
    if match:
        return key_by_fold.get(match.group(1).casefold(), match.group(1))
    folded = _fold_import_text(line)
    if folded in title_index:
        return title_index[folded]
    # Some imported Word files use captions such as "Tablo A.1: ..." or
    # "A.1 tablosu" rather than a clean heading paragraph. In that case,
    # infer the closest section key from any section-key-like token in the caption.
    for folded_key, original_key in key_by_fold.items():
        if re.search(rf"(^|\s){re.escape(folded_key)}($|\s)", folded):
            return original_key
    return ""


def _save_imported_table(username: str, program_id: str, section_key: str, table_name: str, rows: list[dict[str, Any]], meta: dict[str, Any] | None = None) -> bool:
    # Import is an explicit document-level operation. Use section access rather
    # than the stricter live editor lock so tables from an approved/imported
    # report are not silently lost while the user is restoring a report file.
    assert_program_access(username, program_id)
    section = get_section(username, program_id, section_key)
    if not section or not _section_access_allowed(username, program_id, section_key):
        return False
    clean_table_name = _clean_import_line(table_name) or f"İçe Aktarılan Tablo"
    data_json = table_json_from_rows(rows, meta)
    with transaction() as conn:
        existing = conn.execute(
            "SELECT id FROM data_tables WHERE program_id=? AND section_key=? AND table_name=? AND COALESCE(deleted_at,'')='' ORDER BY updated_at DESC LIMIT 1",
            (program_id, section_key, clean_table_name),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE data_tables SET data_json=?, updated_at=? WHERE program_id=? AND id=?",
                (data_json, now_iso(), program_id, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO data_tables(id,program_id,section_key,table_name,data_json,updated_at) VALUES(?,?,?,?,?,?)",
                (str(uuid.uuid4()), program_id, section_key, clean_table_name, data_json, now_iso()),
            )
    return True


def _import_docx_tables(username: str, program_id: str, sections: list[dict[str, Any]], data: bytes) -> int:
    blocks = _docx_blocks(data)
    matcher, key_by_fold, title_index, _, ignored_headings = _import_heading_context(sections)
    current_key = ""
    previous_line = ""
    imported = 0
    table_index = 1
    for block in blocks:
        if block.get("type") == "paragraph":
            line = _clean_import_line(str(block.get("text", "")))
            if not line:
                continue
            inferred_key = _infer_import_section_key(line, matcher, key_by_fold, title_index)
            if inferred_key:
                current_key = inferred_key
                previous_line = line
                continue
            folded = _fold_import_text(line)
            if folded not in ignored_headings:
                previous_line = line
            continue

        if block.get("type") != "table":
            continue
        target_key = current_key or _infer_import_section_key(previous_line, matcher, key_by_fold, title_index)
        if not target_key:
            continue
        rows, columns = _docx_table_rows(block.get("rows", []))
        if not rows or not columns:
            continue
        caption_has_table = bool(re.search(r"\btablo\b", previous_line, re.IGNORECASE))
        table_name = previous_line if caption_has_table else f"{target_key} İçe Aktarılan Tablo {table_index}"
        table_index += 1
        ok = _save_imported_table(
            username,
            program_id,
            target_key,
            table_name,
            rows,
            {"columns": columns, "options": {"fontSize": 9, "headerBg": "#eef4ff", "borderColor": "#cbdff7"}, "source": "docx_import"},
        )
        if ok:
            imported += 1
    return imported


def _apply_report_import_buckets(
    username: str,
    program_id: str,
    buckets: dict[str, list[str]],
    overwrite_empty_only: bool,
    source_type: str,
) -> tuple[int, int]:
    updated = skipped = 0
    with transaction() as conn:
        for key, lines in buckets.items():
            text = "\n\n".join(_import_text_blocks(lines, source_type)).strip()
            if not text:
                continue
            section = get_section(username, program_id, key)
            if not section or not can_edit_section(username, program_id, section):
                skipped += 1
                continue
            if overwrite_empty_only and str(section.get("report_text", "") or "").strip():
                skipped += 1
                continue
            conn.execute(
                "UPDATE sections SET report_text=?, status=CASE WHEN status='Başlamadı' THEN 'Taslak Hazır' ELSE status END, updated_at=? WHERE program_id=? AND section_key=?",
                (text, now_iso(), program_id, key),
            )
            updated += 1
    return updated, skipped


def import_report_file(username: str, program_id: str, original_name: str, data: bytes, overwrite_empty_only: bool = True) -> dict[str, Any]:
    role = assert_program_access(username, program_id)
    if role == READONLY_ROLE:
        raise PermissionError("Rapor içe aktarma için düzenleme yetkisi gerekir.")
    sections = list_sections(username, program_id)
    if not any(can_edit_section(username, program_id, section) for section in sections):
        raise PermissionError("İçe aktarılabilecek düzenlenebilir başlık bulunamadı.")
    clean_name = str(original_name or "rapor").strip() or "rapor"
    lower_name = clean_name.lower()
    if len(data) > 75 * 1024 * 1024:
        raise ValueError("Rapor dosyası 75 MB sınırını aşıyor.")

    if lower_name.endswith(".docx"):
        file_type = "DOCX"
        lines = _docx_lines(data)
    elif lower_name.endswith(".pdf"):
        file_type = "PDF"
        lines = _pdf_lines(data)
    else:
        raise ValueError("Yalnızca DOCX veya PDF rapor dosyası içe aktarılabilir.")

    buckets = _report_import_buckets(sections, lines)
    updated, skipped = _apply_report_import_buckets(username, program_id, buckets, overwrite_empty_only, file_type)
    imported_tables = _import_docx_tables(username, program_id, sections, data) if file_type == "DOCX" else 0
    log_activity(f"{file_type} rapor içe aktarıldı", f"{clean_name}: {updated}/{len(buckets)}, tablo={imported_tables}", username, program_id)
    return {
        "file_type": file_type,
        "detected": len(buckets),
        "updated": updated,
        "skipped": skipped,
        "extracted_lines": len(lines),
        "imported_tables": imported_tables,
    }


def import_docx_text(username: str, program_id: str, original_name: str, data: bytes, overwrite_empty_only: bool = True) -> dict[str, Any]:
    return import_report_file(username, program_id, original_name, data, overwrite_empty_only)


def _guide_for_section(profile: str, section: dict[str, Any], evidence: list[dict[str, Any]], tables: list[dict[str, Any]]) -> dict[str, Any]:
    section_key = str(section.get("section_key", "") or "")
    template_guide = profile_section_guide(profile, section_key)
    expected_evidence = list(template_guide.get("evidence", []))
    evidence_names = [row.get("original_name", "") for row in evidence]
    return {
        "question": template_guide.get("question") or section.get("section_title", ""),
        "evidence": expected_evidence or evidence_names,
        "table": bool(template_guide.get("table") or tables),
    }


def ai_draft_for_section(username: str, program_id: str, section_key: str, target_words: int = 650) -> dict[str, Any]:
    from services.ai_report_writer import build_specialized_report_draft
    from services.ollama_provider import build_ollama_prompt, generate_with_ollama, ollama_status

    section = get_section(username, program_id, section_key)
    if not section:
        raise KeyError(section_key)
    if not _section_permission(username, program_id, section_key, "ai_draft"):
        raise PermissionError("Bu başlık için AI taslak üretme yetkiniz yok.")
    evidence = list_evidence(username, program_id, section_key)
    tables = list_tables(username, program_id, section_key)
    program = get_program(program_id) or {}
    guide = _guide_for_section(program.get("accreditation_profile", "MEDEK"), section, evidence, tables)

    ai_status = ollama_status()
    if ai_status.get("enabled") and ai_status.get("available"):
        try:
            result = generate_with_ollama(build_ollama_prompt(section, guide, evidence, tables, target_words=target_words))
            return {
                "section_key": section_key,
                "section_title": section.get("section_title", ""),
                "text": result["text"],
                "warnings": result.get("warnings", []) + ["Ollama yerel model çıktısıdır; kullanıcı kontrolünden sonra kaydedilmelidir."],
                "evidence_codes": [row.get("code", "") for row in evidence if row.get("code")],
                "table_names": [row.get("table_name", "") for row in tables if row.get("table_name")],
                "provider": "ollama",
                "model": result.get("model", ""),
                "offline": True,
            }
        except Exception as exc:
            fallback_warning = f"Ollama kullanılamadı; yerel şablon üreticiye düşüldü: {exc}"
        else:
            fallback_warning = ""
    else:
        fallback_warning = str(ai_status.get("message", "AI sağlayıcı kapalı; yerel şablon üretici kullanıldı."))

    draft = build_specialized_report_draft(section, guide, evidence, tables, target_words=target_words)
    warnings = list(draft.warnings)
    if fallback_warning:
        warnings.insert(0, fallback_warning)
    return {
        "section_key": section_key,
        "section_title": section.get("section_title", ""),
        "text": draft.text,
        "warnings": warnings,
        "evidence_codes": draft.evidence_codes,
        "table_names": draft.table_names,
        "provider": "deterministic-fallback",
        "model": "local-template",
        "offline": True,
    }


def _draft_diff_preview(current_text: str, proposed_text: str, limit: int = 48) -> list[str]:
    current_lines = [line.strip() for line in str(current_text or "").splitlines() if line.strip()]
    proposed_lines = [line.strip() for line in str(proposed_text or "").splitlines() if line.strip()]
    diff = list(unified_diff(current_lines, proposed_lines, fromfile="mevcut", tofile="ai-taslak", lineterm=""))
    return diff[:limit]


def full_ai_draft_candidates(username: str, program_id: str, include_all: bool = False, target_words: int = 650) -> list[dict[str, Any]]:
    from services.full_report_generator import build_full_report_draft_candidates

    sections = list_sections(username, program_id)
    program = get_program(program_id) or {}
    profile = program.get("accreditation_profile", "MEDEK")
    guide_by_key = {
        str(section.get("section_key", "")): _guide_for_section(
            profile,
            section,
            list_evidence(username, program_id, str(section.get("section_key", ""))),
            list_tables(username, program_id, str(section.get("section_key", ""))),
        )
        for section in sections
    }
    evidence_by_key = {str(section.get("section_key", "")): list_evidence(username, program_id, str(section.get("section_key", ""))) for section in sections}
    table_by_key = {str(section.get("section_key", "")): list_tables(username, program_id, str(section.get("section_key", ""))) for section in sections}
    quality_by_key = {str(section.get("section_key", "")): quality_for_section(username, program_id, section) for section in sections}
    candidates = build_full_report_draft_candidates(
        sections,
        guide_by_key,
        evidence_by_key,
        table_by_key,
        quality_by_key,
        include_all=include_all,
        target_words=target_words,
    )
    section_by_key = {str(section.get("section_key", "")): section for section in sections}
    return [
        {
            "section_key": item.section_key,
            "section_title": item.section_title,
            "main_title": item.main_title,
            "current_words": item.current_words,
            "proposed_words": _word_count(item.draft.text),
            "word_delta": _word_count(item.draft.text) - item.current_words,
            "quality_score": item.quality_score,
            "text": item.draft.text,
            "current_excerpt": str(section_by_key.get(item.section_key, {}).get("report_text", "") or "")[:900],
            "diff_preview": _draft_diff_preview(str(section_by_key.get(item.section_key, {}).get("report_text", "") or ""), item.draft.text),
            "warnings": item.draft.warnings,
            "evidence_codes": item.draft.evidence_codes,
            "table_names": item.draft.table_names,
            "apply_available": True,
        }
        for item in candidates
    ]


def dashboard(username: str, program_id: str) -> dict[str, Any]:
    sections = list_sections(username, program_id)
    total = len(sections)
    approved = sum(1 for row in sections if row.get("approval_status") == APPROVED)
    submitted = sum(1 for row in sections if row.get("approval_status") == SUBMITTED)
    revision = sum(1 for row in sections if row.get("approval_status") == REVISION or row.get("status") == REVISION)
    ready = sum(1 for row in sections if row.get("status") in {READY, COMPLETED})
    criteria: dict[str, dict[str, Any]] = {}
    for section in sections:
        main = section.get("report_group_title") or section.get("main_title", "")
        subgroup = str(section.get("report_subgroup_title", "") or "")
        item = criteria.setdefault(
            main,
            {
                "main_title": main,
                "report_group_title": main,
                "total": 0,
                "approved": 0,
                "ready": 0,
                "first_section_key": section.get("section_key"),
                "subcriteria": {},
            },
        )
        item["total"] += 1
        if section.get("approval_status") == APPROVED:
            item["approved"] += 1
        if section.get("status") in {READY, COMPLETED}:
            item["ready"] += 1
        if subgroup:
            sub_item = item["subcriteria"].setdefault(
                subgroup,
                {
                    "main_title": subgroup,
                    "total": 0,
                    "approved": 0,
                    "ready": 0,
                    "first_section_key": section.get("section_key"),
                },
            )
            sub_item["total"] += 1
            if section.get("approval_status") == APPROVED:
                sub_item["approved"] += 1
            if section.get("status") in {READY, COMPLETED}:
                sub_item["ready"] += 1
    criteria_rows = []
    measure_rows = []
    for item in criteria.values():
        subcriteria = list(item.pop("subcriteria", {}).values())
        criteria_rows.append({**item, "subcriteria": subcriteria})
        measure_rows.extend(subcriteria)
    return {
        "summary": {
            "total_sections": total,
            "ready_sections": ready,
            "approved_sections": approved,
            "submitted_sections": submitted,
            "revision_sections": revision,
            "readiness_percent": round((ready / total) * 100, 1) if total else 0,
            "approval_percent": round((approved / total) * 100, 1) if total else 0,
        },
        "criteria": measure_rows or criteria_rows,
        "measure_criteria": measure_rows or criteria_rows,
        "report_groups": criteria_rows,
    }


def approval_action(username: str, program_id: str, section_key: str, action: str, note: str = "") -> dict[str, Any]:
    section = get_section(username, program_id, section_key)
    if not section:
        raise KeyError(section_key)
    role = assert_program_access(username, program_id)
    action = action.strip().lower()
    if action == "send":
        if role != EDITOR_ROLE:
            raise PermissionError("Onaya gönderme işlemi yalnızca editör rolüyle yapılabilir")
        if not _section_permission(username, program_id, section_key, "submit"):
            raise PermissionError("Bu başlığı onaya gönderme yetkiniz yok.")
        if not can_edit_section(username, program_id, section):
            raise PermissionError("Bu başlık onaya gönderilemez.")
        status = SUBMITTED
        history_status = status
        section_status = READY
        requested_by = username
        decided_by = ""
    elif action == "approve":
        if not _section_permission(username, program_id, section_key, "approve"):
            raise PermissionError("Bu başlığı onaylama yetkiniz yok.")
        status = APPROVED
        history_status = status
        section_status = COMPLETED
        requested_by = ""
        decided_by = username
    elif action == "revision":
        if not _section_permission(username, program_id, section_key, "request_revision"):
            raise PermissionError("Bu başlık için revizyon isteme yetkiniz yok.")
        status = REVISION
        history_status = status
        section_status = REVISION
        requested_by = ""
        decided_by = username
    elif action == "undo":
        if not _section_permission(username, program_id, section_key, "reopen"):
            raise PermissionError("Bu başlığın onayını geri alma yetkiniz yok.")
        if section.get("approval_status") != APPROVED:
            raise ValueError("Yalnızca onaylanmış başlıkların onayı geri alınabilir.")
        status = "Taslak"
        history_status = "Onay Geri Alındı"
        section_status = READY
        requested_by = ""
        decided_by = username
    else:
        raise ValueError("Desteklenmeyen onay işlemi.")
    approval_created_at = now_iso()
    approval_id = str(uuid.uuid4())
    with transaction() as conn:
        conn.execute(
            "UPDATE sections SET approval_status=?, status=?, approved_by=?, approved_at=?, updated_at=? WHERE program_id=? AND section_key=?",
            (status, section_status, decided_by if status == APPROVED else "", now_iso() if status == APPROVED else "", now_iso(), program_id, section_key),
        )
        conn.execute(
            "INSERT INTO section_approvals(id,program_id,section_key,status,requested_by,decided_by,note,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (approval_id, program_id, section_key, history_status, requested_by, decided_by, note, approval_created_at),
        )
    result = get_section(username, program_id, section_key) or {}
    try:
        program = get_program(program_id) or {"id": program_id, "program_name": program_id}
        write_approval_snapshot(
            program,
            {
                "id": approval_id,
                "program_id": program_id,
                "section_key": section_key,
                "status": history_status,
                "requested_by": requested_by,
                "decided_by": decided_by,
                "note": note,
                "created_at": approval_created_at,
            },
            actor=username,
            action=action,
        )
        write_section_text_archive(program, result, actor=username, action=f"Onay işlemi: {history_status}", create_version=True)
    except Exception:
        pass
    log_activity("Onay işlemi", f"{section_key} -> {status}", username, program_id)
    return result



def bulk_update_advanced(username: str, program_id: str, section_keys: list[str], status: str = "", deadline: str = "") -> dict[str, Any]:
    role = assert_program_access(username, program_id)
    if role not in {SUPER_ADMIN_ROLE, TENANT_ADMIN_ROLE}:
        raise PermissionError("Toplu gelişmiş işlemler yalnızca Süper Admin veya Kurum Admin tarafından yapılabilir.")
    keys = [str(key).strip() for key in section_keys if str(key).strip()]
    clean_status = str(status or "").strip()
    clean_deadline = str(deadline or "").strip()
    if not clean_status and not clean_deadline:
        raise ValueError("En az bir güncelleme alanı seçilmelidir.")
    allowed_status = {"Başlamadı", "Devam Ediyor", READY, REVISION, COMPLETED}
    if clean_status and clean_status not in allowed_status:
        raise ValueError("Geçersiz durum seçimi.")
    updated = 0
    skipped: list[str] = []
    with transaction() as conn:
        for key in keys:
            row = conn.execute("SELECT * FROM sections WHERE program_id=? AND COALESCE(deleted_at,'')='' AND section_key=?", (program_id, key)).fetchone()
            section = row_to_dict(row)
            if not section:
                skipped.append(key)
                continue
            assignments: list[str] = []
            params: list[Any] = []
            if clean_status:
                assignments.append("status=?")
                params.append(clean_status)
            if clean_deadline:
                assignments.append("deadline=?")
                params.append(clean_deadline)
            assignments.append("updated_at=?")
            params.append(now_iso())
            params.extend([program_id, key])
            conn.execute(f"UPDATE sections SET {', '.join(assignments)} WHERE program_id=? AND section_key=?", tuple(params))
            conn.execute(
                """INSERT INTO section_versions(
                    id, program_id, section_key, saved_at, status, report_text, planla, uygula,
                    kontrol, onlem, notes, deadline, change_summary
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()),
                    program_id,
                    key,
                    now_iso(),
                    clean_status or section.get("status", ""),
                    section.get("report_text", "") or "",
                    section.get("planla", "") or "",
                    section.get("uygula", "") or "",
                    section.get("kontrol", "") or "",
                    section.get("onlem", "") or "",
                    section.get("notes", "") or "",
                    clean_deadline or section.get("deadline", "") or "",
                    f"Toplu işlem: durum={clean_status or '-'}, termin={clean_deadline or '-'}",
                ),
            )
            updated += 1
    log_activity("Toplu gelişmiş işlem", f"{updated}/{len(keys)} durum={clean_status or '-'} termin={clean_deadline or '-'}", username, program_id)
    return {"requested": len(keys), "updated": updated, "skipped": skipped, "status": clean_status, "deadline": clean_deadline}
