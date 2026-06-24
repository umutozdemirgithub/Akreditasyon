
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..db import get_conn, now_iso, rows_to_dicts, transaction
from ..repositories import assert_operation_permission, get_program, log_activity
from ..tenancy import DEFAULT_TENANT_ID, can_access_tenant, ensure_program_tenant_access, tenant_filter_sql


def deleted_programs_admin(username: str) -> list[dict[str, Any]]:
    assert_operation_permission(username, "recovery.restore")
    tenant_sql, tenant_params = tenant_filter_sql(username)
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM programs WHERE COALESCE(deleted_at,'')<>''{tenant_sql} ORDER BY deleted_at DESC",
            tenant_params,
        ).fetchall()
    return rows_to_dicts(rows)


def deleted_items_admin(username: str) -> list[dict[str, Any]]:
    """Return every soft-deleted item that can be reviewed from the admin archive.

    The product started with program-level soft delete. This wider archive gives
    admins visibility into section/evidence/table records too, without forcing a
    dangerous permanent delete workflow for report sections.
    """
    assert_operation_permission(username, "recovery.restore")
    program_sql, program_params = tenant_filter_sql(username, "p")
    user_sql, user_params = tenant_filter_sql(username, "u")
    with get_conn() as conn:
        programs = conn.execute(
            """SELECT 'program' AS item_type, id AS item_id, id AS program_id, '' AS section_key,
                      program_name AS label, school_name AS context, deleted_at, deleted_by,
                      1 AS can_restore, 1 AS can_purge
               FROM programs p WHERE COALESCE(p.deleted_at,'')<>''""" + program_sql,
            program_params,
        ).fetchall()
        sections = conn.execute(
            """SELECT 'section' AS item_type, s.id AS item_id, s.program_id, s.section_key,
                      s.section_title AS label, s.main_title AS context, s.deleted_at, s.deleted_by,
                      1 AS can_restore, 0 AS can_purge
               FROM sections s JOIN programs p ON p.id=s.program_id
               WHERE COALESCE(s.deleted_at,'')<>''""" + program_sql,
            program_params,
        ).fetchall()
        evidence = conn.execute(
            """SELECT 'evidence' AS item_type, e.id AS item_id, e.program_id, e.section_key,
                      e.original_name AS label, e.code AS context, e.deleted_at, e.deleted_by,
                      1 AS can_restore, 1 AS can_purge
               FROM evidence e JOIN programs p ON p.id=e.program_id
               WHERE COALESCE(e.deleted_at,'')<>''""" + program_sql,
            program_params,
        ).fetchall()
        tables = conn.execute(
            """SELECT 'table' AS item_type, dt.id AS item_id, dt.program_id, dt.section_key,
                      dt.table_name AS label, 'Tablo' AS context, dt.deleted_at, dt.deleted_by,
                      1 AS can_restore, 1 AS can_purge
               FROM data_tables dt JOIN programs p ON p.id=dt.program_id
               WHERE COALESCE(dt.deleted_at,'')<>''""" + program_sql,
            program_params,
        ).fetchall()
        program_users = conn.execute(
            """SELECT 'program_user' AS item_type, pu.id AS item_id, pu.program_id, pu.username AS section_key,
                      pu.username AS label, pu.role AS context, pu.deleted_at, pu.deleted_by,
                      1 AS can_restore, 0 AS can_purge
               FROM program_users pu JOIN programs p ON p.id=pu.program_id
               WHERE COALESCE(pu.deleted_at,'')<>''""" + program_sql,
            program_params,
        ).fetchall()
        users = conn.execute(
            """SELECT 'user' AS item_type, u.username AS item_id, '' AS program_id, u.username AS section_key,
                      u.username AS label, u.role AS context, u.deleted_at, u.deleted_by,
                      1 AS can_restore, 0 AS can_purge
               FROM users u WHERE COALESCE(u.deleted_at,'')<>''""" + user_sql,
            user_params,
        ).fetchall()
    rows = rows_to_dicts(list(programs) + list(sections) + list(evidence) + list(tables) + list(program_users) + list(users))
    return sorted(rows, key=lambda row: str(row.get("deleted_at", "")), reverse=True)


def restore_program_admin(username: str, program_id: str) -> dict[str, Any]:
    assert_operation_permission(username, "recovery.restore")
    ensure_program_tenant_access(username, program_id)
    with transaction() as conn:
        row = conn.execute("SELECT * FROM programs WHERE id=?", (program_id,)).fetchone()
        if not row:
            raise KeyError("Program bulunamadı.")
        conn.execute("UPDATE programs SET is_active=1, deleted_at='', deleted_by='', updated_at=? WHERE id=?", (now_iso(), program_id))
        conn.execute("UPDATE sections SET deleted_at='', deleted_by='', updated_at=? WHERE program_id=?", (now_iso(), program_id))
        conn.execute("UPDATE program_users SET deleted_at='', deleted_by='', updated_at=? WHERE program_id=?", (now_iso(), program_id))
        conn.execute("UPDATE evidence SET deleted_at='', deleted_by='' WHERE program_id=?", (program_id,))
        conn.execute("UPDATE data_tables SET deleted_at='', deleted_by='', updated_at=? WHERE program_id=?", (now_iso(), program_id))
    log_activity("Program geri yüklendi", program_id, username, program_id)
    return {"restored": True, "program_id": program_id}


def restore_item_admin(username: str, item_type: str, item_id: str) -> dict[str, Any]:
    assert_operation_permission(username, "recovery.restore")
    kind = str(item_type or "").strip().lower()
    if kind == "program":
        return restore_program_admin(username, item_id)
    if kind == "user":
        with transaction() as conn:
            row = conn.execute("SELECT * FROM users WHERE username=?", (item_id,)).fetchone()
            if not row:
                raise KeyError("Kullanıcı bulunamadı.")
            if not can_access_tenant(username, str(row["tenant_id"] or DEFAULT_TENANT_ID)):
                raise PermissionError("Başka kuruma ait kullanıcıyı geri yükleme yetkiniz yok.")
            conn.execute("UPDATE users SET is_active=1, deleted_at='', deleted_by='', updated_at=? WHERE username=?", (now_iso(), item_id))
            conn.execute("UPDATE program_users SET is_active=1, deleted_at='', deleted_by='', updated_at=? WHERE username=? AND COALESCE(deleted_at,'')<>''", (now_iso(), item_id))
        log_activity("Kullanıcı geri yüklendi", item_id, username, "")
        return {"restored": True, "item_type": kind, "item_id": item_id, "program_id": ""}
    table_map = {
        "section": ("sections", "updated_at=?", (now_iso(),)),
        "evidence": ("evidence", "deleted_at=''", tuple()),
        "table": ("data_tables", "updated_at=?", (now_iso(),)),
        "program_user": ("program_users", "is_active=1, updated_at=?", (now_iso(),)),
    }
    if kind not in table_map:
        raise ValueError("Desteklenmeyen arşiv öğesi türü.")
    table, extra_set, extra_values = table_map[kind]
    with transaction() as conn:
        row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (item_id,)).fetchone()
        if not row:
            raise KeyError("Arşiv öğesi bulunamadı.")
        program_id = str(row["program_id"] if "program_id" in row.keys() else "")
        if program_id:
            ensure_program_tenant_access(username, program_id)
        set_clause = "deleted_at='', deleted_by=''"
        if extra_set and extra_set != "deleted_at=''":
            set_clause = f"{set_clause}, {extra_set}"
        conn.execute(f"UPDATE {table} SET {set_clause} WHERE id=?", (*extra_values, item_id))
    log_activity("Arşiv öğesi geri yüklendi", f"{kind}:{item_id}", username, program_id)
    return {"restored": True, "item_type": kind, "item_id": item_id, "program_id": program_id}


def purge_item_admin(username: str, item_type: str, item_id: str) -> dict[str, Any]:
    assert_operation_permission(username, "recovery.purge")
    kind = str(item_type or "").strip().lower()
    if kind == "program":
        return purge_program_admin(username, item_id)
    if kind not in {"evidence", "table"}:
        raise ValueError("Bu öğe türünde kalıcı silme kapalıdır. Önce geri yükleyip ilgili iş akışından yönetin.")
    file_path: Path | None = None
    program_id = ""
    with transaction() as conn:
        if kind == "evidence":
            row = conn.execute("SELECT * FROM evidence WHERE id=?", (item_id,)).fetchone()
            if not row:
                raise KeyError("Kanıt bulunamadı.")
            program_id = str(row["program_id"] or "")
            ensure_program_tenant_access(username, program_id)
            file_path = Path(str(row["stored_path"] or "")) if str(row["stored_path"] or "").strip() else None
            conn.execute("DELETE FROM evidence_links WHERE evidence_id=?", (item_id,))
            conn.execute("DELETE FROM evidence WHERE id=?", (item_id,))
        else:
            row = conn.execute("SELECT * FROM data_tables WHERE id=?", (item_id,)).fetchone()
            if not row:
                raise KeyError("Tablo bulunamadı.")
            program_id = str(row["program_id"] or "")
            ensure_program_tenant_access(username, program_id)
            conn.execute("DELETE FROM data_tables WHERE id=?", (item_id,))
    if file_path:
        try:
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
        except OSError:
            pass
    log_activity("Arşiv öğesi kalıcı silindi", f"{kind}:{item_id}", username, program_id)
    return {"purged": True, "item_type": kind, "item_id": item_id, "program_id": program_id}


def purge_program_admin(username: str, program_id: str) -> dict[str, Any]:
    assert_operation_permission(username, "program.purge")
    ensure_program_tenant_access(username, program_id)
    program = get_program(program_id)
    if not program:
        raise KeyError("Program bulunamadı.")
    evidence_paths: list[Path] = []
    export_paths: list[Path] = []
    with transaction() as conn:
        evidence_rows = conn.execute("SELECT stored_path FROM evidence WHERE program_id=?", (program_id,)).fetchall()
        evidence_paths = [Path(str(row["stored_path"])) for row in evidence_rows if str(row["stored_path"] or "").strip()]
        export_rows = conn.execute("SELECT file_path FROM export_jobs WHERE program_id=?", (program_id,)).fetchall()
        export_paths = [Path(str(row["file_path"])) for row in export_rows if str(row["file_path"] or "").strip()]
        for table in ["evidence_links", "evidence", "data_tables", "section_approvals", "section_comments", "section_versions", "sections", "edit_locks", "export_history", "export_jobs", "notification_events", "program_users"]:
            conn.execute(f"DELETE FROM {table} WHERE program_id=?", (program_id,))
        conn.execute("DELETE FROM programs WHERE id=?", (program_id,))
    for file_path in evidence_paths + export_paths:
        try:
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
        except OSError:
            pass
    log_activity("Program kalıcı silindi", str(program.get("program_name", program_id)), username, program_id)
    return {"purged": True, "program_id": program_id}
