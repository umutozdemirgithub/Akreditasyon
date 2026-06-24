from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Any

from .db import get_conn, now_iso, row_to_dict, rows_to_dicts, transaction

DEFAULT_TENANT_ID = "tenant_default"
GLOBAL_SCOPE = "global"
TENANT_SCOPE = "tenant"


def _slug(value: str, fallback: str = "kurum") -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return text or fallback


def default_tenant_name() -> str:
    # The default tenant is an internal bootstrap record. It must not carry
    # a real-looking university name on fresh installations, otherwise the
    # first screen looks pre-filled before the Super Admin has completed the
    # first institution setup wizard. MEDEK_DEFAULT_TENANT_NAME is kept for
    # compatibility but no longer used to pre-populate the visible institution.
    return ""


def ensure_default_tenant(conn) -> None:
    # Keep one internal tenant so freshly bootstrapped users/programs always have
    # a safe tenant_id. It is intentionally left as a setup placeholder until
    # the Super Admin completes the first institution wizard.
    conn.execute(
        """INSERT OR IGNORE INTO tenants(id, name, code, domain, is_active, created_at, updated_at, setup_completed_at, appearance_package, appearance_config_json)
           VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (DEFAULT_TENANT_ID, default_tenant_name(), "", "", 1, now_iso(), now_iso(), "", "corporate_blue", "{}"),
    )
    # If an earlier build created the placeholder with a real-looking name,
    # clear it while setup is still incomplete. Existing completed institutions
    # are not touched.
    try:
        conn.execute(
            """UPDATE tenants
               SET name='', code='', domain='', updated_at=?
               WHERE id=? AND COALESCE(setup_completed_at,'')=''""",
            (now_iso(), DEFAULT_TENANT_ID),
        )
    except Exception:
        pass

    # Existing single-tenant installations are migrated into the default tenant.
    for table in ["programs", "program_users", "users"]:
        try:
            conn.execute(f"UPDATE {table} SET tenant_id=? WHERE COALESCE(tenant_id,'')=''", (DEFAULT_TENANT_ID,))
        except Exception:
            pass
    try:
        conn.execute("UPDATE users SET role='Süper Admin' WHERE role='Admin' AND COALESCE(tenant_scope,'tenant')='global'")
        conn.execute("UPDATE users SET role='Kurum Admin' WHERE role='Admin' AND COALESCE(tenant_scope,'tenant')<>'global'")
        conn.execute("UPDATE users SET tenant_scope=? WHERE role IN ('Süper Admin','Admin') AND COALESCE(tenant_scope,'')=''", (GLOBAL_SCOPE,))
        conn.execute("UPDATE users SET tenant_scope=? WHERE role NOT IN ('Süper Admin','Admin') AND COALESCE(tenant_scope,'')=''", (TENANT_SCOPE,))
    except Exception:
        pass


def user_is_global_admin(user: dict[str, Any] | None) -> bool:
    role = str((user or {}).get("role", ""))
    return bool(user and role in {"Süper Admin", "Admin"} and str(user.get("tenant_scope", TENANT_SCOPE) or TENANT_SCOPE) == GLOBAL_SCOPE)


def user_tenant_id(user: dict[str, Any] | None) -> str:
    return str((user or {}).get("tenant_id", DEFAULT_TENANT_ID) or DEFAULT_TENANT_ID)


def assert_global_or_tenant_admin(username: str) -> dict[str, Any]:
    from .repositories import get_user

    user = get_user(username, active_only=True)
    if not user or str(user.get("role", "")) not in {"Süper Admin", "Kurum Admin", "Admin"}:
        raise PermissionError("Bu işlemi yalnızca Süper Admin veya Kurum Admin yapabilir.")
    return user


def require_tenant_management(username: str) -> dict[str, Any]:
    user = assert_global_or_tenant_admin(username)
    from .repositories import actor_has_operation_permission
    if not actor_has_operation_permission(user, "tenant.manage"):
        raise PermissionError("Kurum Yönetimi için Yetki Matrisi izniniz yok.")
    return user


def visible_tenant_ids_for_user(username: str) -> set[str] | None:
    from .repositories import get_user

    user = get_user(username, active_only=True)
    if user_is_global_admin(user):
        return None
    return {user_tenant_id(user)}


def can_access_tenant(username: str, tenant_id: str) -> bool:
    visible = visible_tenant_ids_for_user(username)
    return visible is None or str(tenant_id or DEFAULT_TENANT_ID) in visible


def ensure_tenant_access(username: str, tenant_id: str) -> None:
    if not can_access_tenant(username, tenant_id):
        raise PermissionError("Bu kurum/fakülte alanına erişim yetkiniz yok.")


def program_tenant_id(program_id: str) -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT tenant_id FROM programs WHERE id=?", (program_id,)).fetchone()
    return str(row["tenant_id"] if row and row["tenant_id"] else DEFAULT_TENANT_ID)


def ensure_program_tenant_access(username: str, program_id: str) -> None:
    ensure_tenant_access(username, program_tenant_id(program_id))


def tenant_filter_sql(username: str, table_alias: str = "") -> tuple[str, tuple[Any, ...]]:
    visible = visible_tenant_ids_for_user(username)
    if visible is None:
        return "", ()
    prefix = f"{table_alias}." if table_alias else ""
    return f" AND COALESCE({prefix}tenant_id, ?) IN ({','.join('?' for _ in visible)})", (DEFAULT_TENANT_ID, *sorted(visible))


def _with_setup_flags(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in rows:
        is_default = str(row.get("id", "")) == DEFAULT_TENANT_ID
        setup_completed = bool(str(row.get("setup_completed_at", "") or "").strip())
        program_count = int(row.get("program_count") or 0)
        # The default tenant is an internal bootstrap record until the first
        # institution setup is explicitly completed. In that state it should not
        # look like a real, pre-defined university in the UI.
        placeholder = bool(is_default and not setup_completed and program_count == 0)
        enriched.append({
            **row,
            "is_default_tenant": is_default,
            "setup_completed": setup_completed,
            "is_setup_placeholder": placeholder,
        })
    return enriched


def tenant_setup_status_admin(username: str) -> dict[str, Any]:
    user = assert_global_or_tenant_admin(username)
    tenants = list_tenants_admin(username, True)
    visible = [row for row in tenants if not row.get("is_setup_placeholder")]
    placeholder = next((row for row in tenants if row.get("is_setup_placeholder")), None)
    setup_required = bool(user_is_global_admin(user) and placeholder and len(visible) == 0)
    return {
        "setup_required": setup_required,
        "tenant_id": placeholder.get("id") if placeholder else DEFAULT_TENANT_ID,
        "placeholder_tenant": placeholder,
        "visible_tenant_count": len(visible),
        "message": "İlk kurum kurulumu tamamlanmalı." if setup_required else "Kurum kurulumu tamamlandı.",
    }


def list_tenants_admin(username: str, include_inactive: bool = True) -> list[dict[str, Any]]:
    user = assert_global_or_tenant_admin(username)
    where = "WHERE COALESCE(deleted_at,'')=''"
    params: list[Any] = []
    if not include_inactive:
        where += " AND is_active=1"
    if not user_is_global_admin(user):
        where += " AND id=?"
        params.append(user_tenant_id(user))
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT *,
                      (SELECT COUNT(*) FROM programs p WHERE COALESCE(p.tenant_id, ?) = tenants.id AND COALESCE(p.deleted_at,'')='') AS program_count,
                      (SELECT COUNT(*) FROM users u WHERE COALESCE(u.tenant_id, ?) = tenants.id AND COALESCE(u.deleted_at,'')='') AS user_count
               FROM tenants {where}
               ORDER BY is_active DESC, name""",
            (DEFAULT_TENANT_ID, DEFAULT_TENANT_ID, *params),
        ).fetchall()
    return _with_setup_flags(rows_to_dicts(rows))


def save_tenant_admin(username: str, payload: dict[str, Any]) -> dict[str, Any]:
    user = require_tenant_management(username)
    tenant_id = str(payload.get("id", "") or "").strip()
    name = str(payload.get("name", "") or "").strip()
    if not name:
        raise ValueError("Kurum adı boş olamaz.")
    if not user_is_global_admin(user):
        tenant_id = user_tenant_id(user)
    if not tenant_id:
        tenant_id = f"tenant_{_slug(name)[:36]}_{uuid.uuid4().hex[:6]}"
    ensure_tenant_access(username, tenant_id)
    code = str(payload.get("code", "") or _slug(name, "KURUM").upper()[:16]).strip().upper()
    domain = str(payload.get("domain", "") or "").strip()
    source_url = str(payload.get("source_url", "") or "").strip()
    is_active = 1 if bool(payload.get("is_active", True)) else 0
    stamp = now_iso()
    setup_completed_at = stamp
    with transaction() as conn:
        conn.execute(
            """INSERT INTO tenants(id,name,code,domain,source_url,is_active,created_at,updated_at,deleted_at,deleted_by,setup_completed_at,appearance_package,appearance_config_json)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET name=excluded.name, code=excluded.code, domain=excluded.domain, source_url=excluded.source_url,
                   is_active=excluded.is_active, updated_at=excluded.updated_at, deleted_at='', deleted_by='',
                   setup_completed_at=CASE
                       WHEN COALESCE(tenants.setup_completed_at,'')='' THEN excluded.setup_completed_at
                       ELSE tenants.setup_completed_at
                   END,
                   appearance_package=COALESCE(NULLIF(tenants.appearance_package,''), excluded.appearance_package),
                   appearance_config_json=COALESCE(NULLIF(tenants.appearance_config_json,''), excluded.appearance_config_json)""",
            (tenant_id, name, code, domain, source_url, is_active, stamp, stamp, "", "", setup_completed_at, "corporate_blue", "{}"),
        )
    return next((row for row in list_tenants_admin(username, True) if row.get("id") == tenant_id), {"id": tenant_id, "name": name})


def _tenant_dependency_counts(conn, tenant_id: str) -> dict[str, int]:
    return {
        "program_count": int(conn.execute(
            "SELECT COUNT(*) AS n FROM programs WHERE COALESCE(tenant_id, ?)=? AND COALESCE(deleted_at,'')=''",
            (DEFAULT_TENANT_ID, tenant_id),
        ).fetchone()["n"] or 0),
        "user_count": int(conn.execute(
            "SELECT COUNT(*) AS n FROM users WHERE COALESCE(tenant_id, ?)=? AND COALESCE(deleted_at,'')=''",
            (DEFAULT_TENANT_ID, tenant_id),
        ).fetchone()["n"] or 0),
        "faculty_count": int(conn.execute(
            "SELECT COUNT(*) AS n FROM tenant_faculties WHERE tenant_id=? AND COALESCE(deleted_at,'')=''",
            (tenant_id,),
        ).fetchone()["n"] or 0),
    }


def _copy_faculties_to_tenant(conn, source_tenant_id: str, target_tenant_id: str) -> None:
    rows = conn.execute(
        """SELECT faculty_name, accreditation_profile, is_active
           FROM tenant_faculties
           WHERE tenant_id=? AND COALESCE(deleted_at,'')=''""",
        (source_tenant_id,),
    ).fetchall()
    for faculty in rows:
        faculty_name = str(faculty["faculty_name"] or "").strip()
        if not faculty_name:
            continue
        exists = conn.execute(
            """SELECT id FROM tenant_faculties
               WHERE tenant_id=? AND faculty_name=? AND COALESCE(deleted_at,'')=''""",
            (target_tenant_id, faculty_name),
        ).fetchone()
        if exists:
            continue
        conn.execute(
            """INSERT INTO tenant_faculties(id, tenant_id, faculty_name, accreditation_profile, is_active, created_at, updated_at, deleted_at, deleted_by)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4()), target_tenant_id, faculty_name, faculty["accreditation_profile"] or "MEDEK", int(faculty["is_active"] or 1), now_iso(), now_iso(), "", ""),
        )


def _delete_notification_reads_for_events(conn, event_ids: list[str]) -> None:
    for event_id in event_ids:
        try:
            conn.execute("DELETE FROM notification_reads WHERE event_id=?", (event_id,))
        except Exception:
            pass


def delete_tenant_admin(username: str, tenant_id: str, mode: str = "safe", target_tenant_id: str = "") -> dict[str, Any]:
    user = require_tenant_management(username)
    clean_id = str(tenant_id or "").strip()
    clean_mode = str(mode or "safe").strip().lower()
    target_id = str(target_tenant_id or "").strip()
    if not clean_id:
        raise ValueError("Silinecek kurum seçilmelidir.")
    if clean_id == DEFAULT_TENANT_ID and clean_mode not in {"deactivate", "purge"}:
        raise ValueError("Varsayılan kurum yalnızca pasifleştirilebilir veya Süper Admin tarafından kalıcı temizlenebilir.")
    ensure_tenant_access(username, clean_id)
    if not user_is_global_admin(user) and clean_id != user_tenant_id(user):
        raise PermissionError("Bu kurumu silme yetkiniz yok.")
    if clean_mode not in {"safe", "deactivate", "archive_children", "move", "purge"}:
        raise ValueError("Geçersiz kurum silme modu.")
    if clean_mode == "purge" and not user_is_global_admin(user):
        raise PermissionError("Kurum kalıcı silme işlemini yalnızca Süper Admin yapabilir.")

    with transaction() as conn:
        row = conn.execute(
            "SELECT id, name FROM tenants WHERE id=? AND COALESCE(deleted_at,'')=''",
            (clean_id,),
        ).fetchone()
        if not row:
            raise ValueError("Kurum bulunamadı.")
        counts = _tenant_dependency_counts(conn, clean_id)
        stamp = now_iso()

        if clean_mode == "deactivate":
            conn.execute("UPDATE tenants SET is_active=0, updated_at=? WHERE id=?", (stamp, clean_id))
            conn.execute("UPDATE tenant_faculties SET is_active=0, updated_at=? WHERE tenant_id=? AND COALESCE(deleted_at,'')=''", (stamp, clean_id))
            return {"deleted": False, "deactivated": True, "id": clean_id, "name": row["name"], **counts}

        if clean_mode == "purge":
            is_default_purge = clean_id == DEFAULT_TENANT_ID
            active_current_user = conn.execute(
                """SELECT username FROM users
                   WHERE username=? AND COALESCE(tenant_id, ?)=? AND COALESCE(deleted_at,'')=''""",
                (username, DEFAULT_TENANT_ID, clean_id),
            ).fetchone()
            if active_current_user and not is_default_purge:
                raise ValueError("Kendi aktif kullanıcı hesabınızın bağlı olduğu kurumu kalıcı silemezsiniz. Önce hesabınızı başka kuruma taşıyın.")

            program_rows = conn.execute(
                "SELECT id FROM programs WHERE COALESCE(tenant_id, ?)=?",
                (DEFAULT_TENANT_ID, clean_id),
            ).fetchall()
            program_ids = [str(program["id"] or "") for program in program_rows if str(program["id"] or "").strip()]
            user_rows = conn.execute(
                "SELECT username FROM users WHERE COALESCE(tenant_id, ?)=?",
                (DEFAULT_TENANT_ID, clean_id),
            ).fetchall()
            usernames = [str(item["username"] or "") for item in user_rows if str(item["username"] or "").strip()]
            usernames_to_delete = [item for item in usernames if not (is_default_purge and item == username)]

            file_paths: list[Path] = []
            event_ids: set[str] = set()
            for program_id in program_ids:
                try:
                    file_paths.extend(Path(str(item["stored_path"])) for item in conn.execute("SELECT stored_path FROM evidence WHERE program_id=?", (program_id,)).fetchall() if str(item["stored_path"] or "").strip())
                except Exception:
                    pass
                try:
                    file_paths.extend(Path(str(item["file_path"])) for item in conn.execute("SELECT file_path FROM export_jobs WHERE program_id=?", (program_id,)).fetchall() if str(item["file_path"] or "").strip())
                except Exception:
                    pass
                try:
                    event_ids.update(str(item["id"] or "") for item in conn.execute("SELECT id FROM notification_events WHERE program_id=?", (program_id,)).fetchall() if str(item["id"] or "").strip())
                except Exception:
                    pass
            try:
                event_ids.update(str(item["id"] or "") for item in conn.execute("SELECT id FROM notification_events WHERE COALESCE(tenant_id, ?)=?", (DEFAULT_TENANT_ID, clean_id)).fetchall() if str(item["id"] or "").strip())
            except Exception:
                pass
            _delete_notification_reads_for_events(conn, sorted(event_ids))

            program_child_tables = [
                "evidence_links", "evidence", "data_tables", "section_approvals", "section_comments",
                "section_versions", "sections", "edit_locks", "export_history", "export_jobs",
                "notification_events", "program_users", "workflow_runs", "workflow_run_items", "activity_log",
            ]
            for program_id in program_ids:
                for table in program_child_tables:
                    try:
                        conn.execute(f"DELETE FROM {table} WHERE program_id=?", (program_id,))
                    except Exception:
                        pass

            for table in ["activity_log", "export_history", "export_jobs", "notification_events", "program_users", "workflow_runs", "workflow_run_items"]:
                try:
                    conn.execute(f"DELETE FROM {table} WHERE COALESCE(tenant_id, ?)=?", (DEFAULT_TENANT_ID, clean_id))
                except Exception:
                    pass

            for target_username in usernames_to_delete:
                for table in ["notification_reads", "login_attempts", "program_users"]:
                    try:
                        conn.execute(f"DELETE FROM {table} WHERE username=?", (target_username,))
                    except Exception:
                        pass

            if is_default_purge:
                conn.execute("DELETE FROM users WHERE COALESCE(tenant_id, ?)=? AND username<>?", (DEFAULT_TENANT_ID, clean_id, username))
                conn.execute(
                    """UPDATE users
                       SET role='Süper Admin', tenant_id=?, tenant_scope=?, is_active=1, deleted_at='', deleted_by='', updated_at=?
                       WHERE username=?""",
                    (DEFAULT_TENANT_ID, GLOBAL_SCOPE, stamp, username),
                )
            else:
                conn.execute("DELETE FROM users WHERE COALESCE(tenant_id, ?)=?", (DEFAULT_TENANT_ID, clean_id))
            conn.execute("DELETE FROM tenant_faculties WHERE tenant_id=?", (clean_id,))
            conn.execute("DELETE FROM programs WHERE COALESCE(tenant_id, ?)=?", (DEFAULT_TENANT_ID, clean_id))
            if is_default_purge:
                conn.execute(
                    """UPDATE tenants
                       SET name='', code='', domain='', source_url='', is_active=1, updated_at=?, deleted_at='', deleted_by='', setup_completed_at=''
                       WHERE id=?""",
                    (stamp, clean_id),
                )
            else:
                conn.execute("DELETE FROM tenants WHERE id=?", (clean_id,))

            for file_path in file_paths:
                try:
                    if file_path.exists() and file_path.is_file():
                        file_path.unlink()
                except OSError:
                    pass

            return {"deleted": True, "purged": True, "reset_default_tenant": is_default_purge, "id": clean_id, "name": row["name"], **counts}

        if clean_mode == "safe" and (counts["program_count"] > 0 or counts["user_count"] > 0):
            raise ValueError("Bu kuruma bağlı program veya kullanıcı var. Silmek yerine pasifleştirin, bağlı kayıtları başka kuruma taşıyın veya kurumla birlikte arşive alın.")

        if clean_mode == "move":
            if not target_id:
                raise ValueError("Bağlı kayıtları taşımak için hedef kurum seçilmelidir.")
            if target_id == clean_id:
                raise ValueError("Hedef kurum kaynak kurumla aynı olamaz.")
            ensure_tenant_access(username, target_id)
            target = conn.execute(
                "SELECT id, name FROM tenants WHERE id=? AND COALESCE(deleted_at,'')=''",
                (target_id,),
            ).fetchone()
            if not target:
                raise ValueError("Hedef kurum bulunamadı.")
            _copy_faculties_to_tenant(conn, clean_id, target_id)
            for table in ["programs", "program_users", "users", "activity_log", "notification_events", "export_history", "export_jobs", "workflow_runs", "workflow_run_items"]:
                try:
                    conn.execute(f"UPDATE {table} SET tenant_id=? WHERE COALESCE(tenant_id, ?)=?", (target_id, DEFAULT_TENANT_ID, clean_id))
                except Exception:
                    pass
            conn.execute(
                "UPDATE tenant_faculties SET deleted_at=?, deleted_by=?, is_active=0, updated_at=? WHERE tenant_id=?",
                (stamp, username, stamp, clean_id),
            )
            conn.execute(
                "UPDATE tenants SET deleted_at=?, deleted_by=?, is_active=0, updated_at=? WHERE id=?",
                (stamp, username, stamp, clean_id),
            )
            return {"deleted": True, "moved": True, "id": clean_id, "name": row["name"], "target_tenant_id": target_id, "target_tenant_name": target["name"], **counts}

        if clean_mode == "archive_children":
            active_current_user = conn.execute(
                """SELECT username FROM users
                   WHERE username=? AND COALESCE(tenant_id, ?)=? AND COALESCE(deleted_at,'')=''""",
                (username, DEFAULT_TENANT_ID, clean_id),
            ).fetchone()
            if active_current_user:
                raise ValueError("Kendi kullanıcınızın bağlı olduğu kurumu bağlı kayıtlarla birlikte arşive alamazsınız. Önce kullanıcınızı başka kuruma taşıyın.")
            for table in ["programs", "program_users", "users"]:
                try:
                    conn.execute(
                        f"UPDATE {table} SET deleted_at=?, deleted_by=?, is_active=0, updated_at=? WHERE COALESCE(tenant_id, ?)=? AND COALESCE(deleted_at,'')=''",
                        (stamp, username, stamp, DEFAULT_TENANT_ID, clean_id),
                    )
                except Exception:
                    conn.execute(
                        f"UPDATE {table} SET deleted_at=?, deleted_by=? WHERE COALESCE(tenant_id, ?)=? AND COALESCE(deleted_at,'')=''",
                        (stamp, username, DEFAULT_TENANT_ID, clean_id),
                    )
            conn.execute(
                "UPDATE tenant_faculties SET deleted_at=?, deleted_by=?, is_active=0, updated_at=? WHERE tenant_id=?",
                (stamp, username, stamp, clean_id),
            )

        conn.execute(
            "UPDATE tenants SET deleted_at=?, deleted_by=?, is_active=0, updated_at=? WHERE id=?",
            (stamp, username, stamp, clean_id),
        )
    return {"deleted": True, "id": clean_id, "name": row["name"], **counts}


def list_faculties_admin(username: str, tenant_id: str = "") -> list[dict[str, Any]]:
    user = assert_global_or_tenant_admin(username)
    params: list[Any] = []
    where = "WHERE COALESCE(tf.deleted_at,'')=''"
    if tenant_id:
        ensure_tenant_access(username, tenant_id)
        where += " AND tf.tenant_id=?"
        params.append(tenant_id)
    elif not user_is_global_admin(user):
        where += " AND tf.tenant_id=?"
        params.append(user_tenant_id(user))
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT tf.*, t.name AS tenant_name,
                      (SELECT COUNT(*) FROM programs p WHERE COALESCE(p.tenant_id, ?) = tf.tenant_id AND COALESCE(p.faculty_name, p.school_name, '') = tf.faculty_name AND COALESCE(p.deleted_at,'')='') AS program_count
               FROM tenant_faculties tf
               LEFT JOIN tenants t ON t.id=tf.tenant_id
               {where}
               ORDER BY t.name, tf.faculty_name""",
            (DEFAULT_TENANT_ID, *params),
        ).fetchall()
    return rows_to_dicts(rows)


def save_faculty_admin(username: str, payload: dict[str, Any]) -> dict[str, Any]:
    user = require_tenant_management(username)
    from .accreditation import normalize_accreditation_profile

    tenant_id = str(payload.get("tenant_id", "") or user_tenant_id(user)).strip() or DEFAULT_TENANT_ID
    ensure_tenant_access(username, tenant_id)
    faculty_name = str(payload.get("faculty_name", "") or payload.get("name", "") or "").strip()
    if not faculty_name:
        raise ValueError("Fakülte/MYO adı boş olamaz.")
    profile = normalize_accreditation_profile(payload.get("accreditation_profile", "MEDEK"))
    is_active = 1 if bool(payload.get("is_active", True)) else 0
    faculty_id = str(payload.get("id", "") or "").strip() or f"fac_{_slug(faculty_name)[:36]}_{uuid.uuid4().hex[:6]}"
    with transaction() as conn:
        if not str(payload.get("id", "") or "").strip():
            existing = conn.execute(
                """SELECT id FROM tenant_faculties
                   WHERE tenant_id=? AND faculty_name=?""",
                (tenant_id, faculty_name),
            ).fetchone()
            if existing:
                faculty_id = str(existing["id"])
        conn.execute(
            """INSERT INTO tenant_faculties(id,tenant_id,faculty_name,accreditation_profile,is_active,created_at,updated_at,deleted_at,deleted_by)
               VALUES(?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET tenant_id=excluded.tenant_id, faculty_name=excluded.faculty_name,
                   accreditation_profile=excluded.accreditation_profile, is_active=excluded.is_active,
                   updated_at=excluded.updated_at, deleted_at='', deleted_by=''""",
            (faculty_id, tenant_id, faculty_name, profile, is_active, now_iso(), now_iso(), "", ""),
        )
    return next((row for row in list_faculties_admin(username, tenant_id) if row.get("id") == faculty_id), {"id": faculty_id})


def tenant_dashboard_admin(username: str) -> dict[str, Any]:
    tenants = list_tenants_admin(username, True)
    faculties = list_faculties_admin(username)
    with get_conn() as conn:
        visible = visible_tenant_ids_for_user(username)
        params: list[Any] = []
        where = "WHERE COALESCE(p.deleted_at,'')=''"
        if visible is not None:
            where += f" AND COALESCE(p.tenant_id, ?) IN ({','.join('?' for _ in visible)})"
            params = [DEFAULT_TENANT_ID, *sorted(visible)]
        rows = conn.execute(
            f"""SELECT COALESCE(t.name, 'Ana Kurum') AS tenant_name, COALESCE(p.faculty_name, p.school_name, '') AS faculty_name,
                      COUNT(*) AS program_count,
                      SUM(CASE WHEN p.is_active=1 THEN 1 ELSE 0 END) AS active_program_count
               FROM programs p
               LEFT JOIN tenants t ON t.id=COALESCE(p.tenant_id, ?)
               {where}
               GROUP BY COALESCE(t.name, 'Ana Kurum'), COALESCE(p.faculty_name, p.school_name, '')
               ORDER BY tenant_name, faculty_name""",
            (DEFAULT_TENANT_ID, *params),
        ).fetchall()
    return {"tenants": tenants, "faculties": faculties, "program_distribution": rows_to_dicts(rows), "default_tenant_id": DEFAULT_TENANT_ID, "setup": tenant_setup_status_admin(username)}
