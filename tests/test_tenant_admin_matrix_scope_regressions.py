from __future__ import annotations

import pytest


def _isolated_db(tmp_path, monkeypatch, name: str):
    from backend import config, db, file_security, repositories

    data_dir = tmp_path / name
    sqlite_path = data_dir / "tenant.sqlite3"
    evidence_dir = data_dir / "kanitlar"
    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    monkeypatch.setattr(config, "SQLITE_PATH", sqlite_path)
    monkeypatch.setattr(config, "EVIDENCE_DIR", evidence_dir)
    monkeypatch.setattr(db, "DATA_DIR", data_dir)
    monkeypatch.setattr(db, "SQLITE_PATH", sqlite_path)
    monkeypatch.setattr(db, "EVIDENCE_DIR", evidence_dir)
    monkeypatch.setattr(repositories, "SQLITE_PATH", sqlite_path)
    monkeypatch.setattr(repositories, "EVIDENCE_DIR", evidence_dir)
    monkeypatch.setattr(repositories, "_PROFILE_SCHEMA_READY", False)
    monkeypatch.setattr(file_security, "EVIDENCE_DIR", evidence_dir)
    db.init_db()
    return repositories


def _tenant_admin(repositories, tenant_id: str, username: str = "tenant_admin_b") -> None:
    repositories.upsert_user_admin(
        "admin",
        {
            "username": username,
            "password": "Tenant_Admin_2026!",
            "role": "Admin",
            "tenant_id": tenant_id,
            "tenant_scope": "tenant",
            "full_name": "Tenant Admin B",
            "is_active": True,
        },
    )


def test_tenant_admin_can_resave_effective_matrix(tmp_path, monkeypatch):
    from backend.enterprise.matrix import permission_matrix_admin, update_permission_matrix_admin
    from backend.tenancy import save_tenant_admin

    repositories = _isolated_db(tmp_path, monkeypatch, "matrix_resave")
    tenant = save_tenant_admin("admin", {"name": "Tenant B", "code": "TB", "is_active": True})
    _tenant_admin(repositories, str(tenant["id"]))

    payload = permission_matrix_admin("tenant_admin_b")
    updated = update_permission_matrix_admin("tenant_admin_b", payload["rows"], payload["sidebar_rows"])

    assert updated["admin_scope"] == "tenant_admin"
    assert updated["tenant_id"] == str(tenant["id"])


def test_tenant_admin_matrix_changes_are_scoped_to_own_tenant(tmp_path, monkeypatch):
    from backend.enterprise.matrix import permission_matrix_admin, role_permission_allowed, update_permission_matrix_admin
    from backend.tenancy import DEFAULT_TENANT_ID, save_tenant_admin

    repositories = _isolated_db(tmp_path, monkeypatch, "matrix_scope")
    tenant = save_tenant_admin("admin", {"name": "Tenant B", "code": "TB", "is_active": True})
    tenant_id = str(tenant["id"])
    _tenant_admin(repositories, tenant_id)

    payload = permission_matrix_admin("tenant_admin_b")
    rows = [dict(row) for row in payload["rows"]]
    for row in rows:
        if row["permission"] == "program.create":
            row[repositories.EDITOR_ROLE] = True
    update_permission_matrix_admin("tenant_admin_b", rows, payload["sidebar_rows"])

    assert role_permission_allowed(repositories.EDITOR_ROLE, "program.create", tenant_id) is True
    assert role_permission_allowed(repositories.EDITOR_ROLE, "program.create", DEFAULT_TENANT_ID) is False


def test_backend_enforces_matrix_for_program_create_and_faculty_save(tmp_path, monkeypatch):
    from backend.enterprise.matrix import permission_matrix_admin, update_permission_matrix_admin
    from backend.tenancy import save_faculty_admin, save_tenant_admin

    repositories = _isolated_db(tmp_path, monkeypatch, "matrix_backend_enforce")
    tenant = save_tenant_admin("admin", {"name": "Tenant B", "code": "TB", "is_active": True})
    tenant_id = str(tenant["id"])
    _tenant_admin(repositories, tenant_id)

    # AKYS default matrix gives Kurum Admin permission to manage unit-level programs/faculties.
    saved_faculty = save_faculty_admin(
        "tenant_admin_b",
        {"tenant_id": tenant_id, "faculty_name": "Engineering Faculty", "accreditation_profile": "MEDEK", "is_active": True},
    )
    assert saved_faculty["faculty_name"] == "Engineering Faculty"

    payload = permission_matrix_admin("admin")
    rows = [dict(row) for row in payload["rows"]]
    for row in rows:
        if row["permission"] == "program.create":
            row[repositories.TENANT_ADMIN_ROLE] = False
    update_permission_matrix_admin("admin", rows, payload["sidebar_rows"])

    actor = repositories.get_user("tenant_admin_b")
    assert repositories.actor_has_operation_permission(actor, "program.create") is False
    with pytest.raises(PermissionError):
        repositories.create_program_admin(
            "tenant_admin_b",
            {"tenant_id": tenant_id, "program_name": "Tenant Program", "report_year": "2026", "accreditation_profile": "MEDEK"},
        )


def test_recovery_archive_is_limited_to_actor_tenant(tmp_path, monkeypatch):
    from backend.enterprise.recovery import deleted_programs_admin, restore_program_admin
    from backend.tenancy import DEFAULT_TENANT_ID, save_tenant_admin

    repositories = _isolated_db(tmp_path, monkeypatch, "recovery_scope")
    tenant = save_tenant_admin("admin", {"name": "Tenant B", "code": "TB", "is_active": True})
    tenant_id = str(tenant["id"])
    default_program = repositories.create_program_admin(
        "admin",
        {"tenant_id": DEFAULT_TENANT_ID, "program_name": "Default Program", "report_year": "2026", "accreditation_profile": "MEDEK"},
    )
    tenant_program = repositories.create_program_admin(
        "admin",
        {"tenant_id": tenant_id, "program_name": "Tenant Program", "report_year": "2026", "accreditation_profile": "MEDEK"},
    )
    _tenant_admin(repositories, tenant_id)

    repositories.delete_program_admin("admin", str(default_program["id"]))
    repositories.delete_program_admin("admin", str(tenant_program["id"]))

    deleted_ids = {str(row["id"]) for row in deleted_programs_admin("tenant_admin_b")}
    assert deleted_ids == {str(tenant_program["id"])}
    with pytest.raises(PermissionError):
        restore_program_admin("tenant_admin_b", str(default_program["id"]))


def test_tenant_admin_faculty_admin_delegation_respects_parent_hierarchy(tmp_path, monkeypatch):
    from backend.enterprise.matrix import permission_matrix_admin, role_permission_allowed, sidebar_matrix_public, update_permission_matrix_admin
    from backend.tenancy import save_tenant_admin

    repositories = _isolated_db(tmp_path, monkeypatch, "tenant_delegates_faculty_under_parent")
    tenant = save_tenant_admin("admin", {"name": "Tenant B", "code": "TB", "is_active": True})
    tenant_id = str(tenant["id"])
    _tenant_admin(repositories, tenant_id)

    payload = permission_matrix_admin("tenant_admin_b")
    assert payload["editable_roles"][:1] == [repositories.FACULTY_ADMIN_ROLE]

    rows = [dict(row) for row in payload["rows"]]
    for row in rows:
        if row["permission"] == "program.view":
            row[repositories.FACULTY_ADMIN_ROLE] = False
    sidebar = [dict(row) for row in payload["sidebar_rows"]]
    for row in sidebar:
        if row["module"] == "programs":
            row[repositories.FACULTY_ADMIN_ROLE] = False
    update_permission_matrix_admin("tenant_admin_b", rows, sidebar)

    assert role_permission_allowed(repositories.FACULTY_ADMIN_ROLE, "program.view", tenant_id) is False
    assert next(row for row in sidebar_matrix_public(tenant_id) if row["module"] == "programs")[repositories.FACULTY_ADMIN_ROLE] is False

    payload = permission_matrix_admin("tenant_admin_b")
    rows = [dict(row) for row in payload["rows"]]
    for row in rows:
        if row["permission"] == "program.view":
            row[repositories.FACULTY_ADMIN_ROLE] = True
    sidebar = [dict(row) for row in payload["sidebar_rows"]]
    for row in sidebar:
        if row["module"] == "programs":
            row[repositories.FACULTY_ADMIN_ROLE] = True
    update_permission_matrix_admin("tenant_admin_b", rows, sidebar)

    assert role_permission_allowed(repositories.FACULTY_ADMIN_ROLE, "program.view", tenant_id) is True
    assert next(row for row in sidebar_matrix_public(tenant_id) if row["module"] == "programs")[repositories.FACULTY_ADMIN_ROLE] is True


def test_super_admin_kurum_admin_cap_blocks_stale_lower_grants(tmp_path, monkeypatch):
    import json
    from backend.db import transaction
    from backend.enterprise.matrix import permission_matrix_admin, role_permission_allowed, sidebar_matrix_public, update_permission_matrix_admin
    from backend.tenancy import save_tenant_admin

    repositories = _isolated_db(tmp_path, monkeypatch, "super_kurum_cap_blocks_stale_lower")
    tenant = save_tenant_admin("admin", {"name": "Tenant B", "code": "TB", "is_active": True})
    tenant_id = str(tenant["id"])
    _tenant_admin(repositories, tenant_id)

    stale_rows = [dict(row) for row in permission_matrix_admin("admin")["rows"]]
    for row in stale_rows:
        if row["permission"] == "program.view":
            row[repositories.FACULTY_ADMIN_ROLE] = True
    stale_sidebar = [dict(row) for row in permission_matrix_admin("admin")["sidebar_rows"]]
    for row in stale_sidebar:
        if row["module"] == "programs":
            row[repositories.FACULTY_ADMIN_ROLE] = True
    with transaction() as conn:
        conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (f"permission_matrix_json:{tenant_id}", json.dumps(stale_rows, ensure_ascii=False)))
        conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (f"sidebar_matrix_json:{tenant_id}", json.dumps(stale_sidebar, ensure_ascii=False)))

    super_payload = permission_matrix_admin("admin")
    super_rows = [dict(row) for row in super_payload["rows"]]
    for row in super_rows:
        if row["permission"] == "program.view":
            row[repositories.TENANT_ADMIN_ROLE] = False
    super_sidebar = [dict(row) for row in super_payload["sidebar_rows"]]
    for row in super_sidebar:
        if row["module"] == "programs":
            row[repositories.TENANT_ADMIN_ROLE] = False
    update_permission_matrix_admin("admin", super_rows, super_sidebar)

    assert role_permission_allowed(repositories.TENANT_ADMIN_ROLE, "program.view", tenant_id) is False
    assert role_permission_allowed(repositories.FACULTY_ADMIN_ROLE, "program.view", tenant_id) is False
    assert next(row for row in sidebar_matrix_public(tenant_id) if row["module"] == "programs")[repositories.FACULTY_ADMIN_ROLE] is False
