from __future__ import annotations

import pytest


def _isolated_db(tmp_path, monkeypatch, name: str):
    from backend import config, db, file_security, repositories

    data_dir = tmp_path / name
    sqlite_path = data_dir / "granular.sqlite3"
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


def test_permission_catalog_has_program_tabs_and_dashboard_actions(tmp_path, monkeypatch):
    from backend.enterprise.matrix import permission_matrix_public

    _isolated_db(tmp_path, monkeypatch, "catalog_actions")
    permissions = {row["permission"] for row in permission_matrix_public()}
    for permission in {
        "program.list.view",
        "program.create",
        "program.clone",
        "program.assign_users",
        "program.users.view",
        "notification.view",
        "quality.view",
        "stats.view",
        "advanced_dashboard.view",
        "activity_trail.view",
        "version_compare.view",
    }:
        assert permission in permissions


def test_program_users_view_is_separate_from_assignment_action(tmp_path, monkeypatch):
    from backend.enterprise.matrix import permission_matrix_admin, update_permission_matrix_admin
    from backend.tenancy import save_tenant_admin

    repositories = _isolated_db(tmp_path, monkeypatch, "program_users_separate")
    tenant = save_tenant_admin("admin", {"name": "Tenant B", "code": "TB", "is_active": True})
    tenant_id = str(tenant["id"])
    _tenant_admin(repositories, tenant_id)
    program = repositories.create_program_admin(
        "admin",
        {"tenant_id": tenant_id, "program_name": "Tenant Program", "report_year": "2026", "accreditation_profile": "MEDEK"},
    )
    repositories.upsert_user_admin(
        "admin",
        {
            "username": "editor_b",
            "password": "Editor_2026!",
            "role": repositories.EDITOR_ROLE,
            "tenant_id": tenant_id,
            "tenant_scope": "tenant",
            "full_name": "Editor B",
            "is_active": True,
        },
    )

    payload = permission_matrix_admin("admin")
    rows = [dict(row) for row in payload["rows"]]
    for row in rows:
        if row["permission"] == "program.assign_users":
            row[repositories.TENANT_ADMIN_ROLE] = False
        if row["permission"] == "program.users.view":
            row[repositories.TENANT_ADMIN_ROLE] = True
    update_permission_matrix_admin("admin", rows, payload["sidebar_rows"])

    visible_rows = repositories.list_program_users_admin("tenant_admin_b", str(program["id"]))
    assert isinstance(visible_rows, list)
    with pytest.raises(PermissionError):
        repositories.assign_user_to_program_admin(
            "tenant_admin_b",
            {"username": "editor_b", "program_ids": [str(program["id"])], "role": repositories.EDITOR_ROLE, "assigned_sections": "", "is_active": True},
        )


def test_dashboard_action_permissions_are_enforced_per_program_role(tmp_path, monkeypatch):
    from backend.enterprise.matrix import permission_matrix_admin, update_permission_matrix_admin

    repositories = _isolated_db(tmp_path, monkeypatch, "dashboard_actions")
    program = repositories.create_program_admin(
        "admin",
        {"program_name": "Default Program", "report_year": "2026", "accreditation_profile": "MEDEK"},
    )
    repositories.upsert_user_admin(
        "admin",
        {
            "username": "editor_a",
            "password": "Editor_2026!",
            "role": repositories.EDITOR_ROLE,
            "tenant_id": "tenant_default",
            "tenant_scope": "tenant",
            "full_name": "Editor A",
            "is_active": True,
        },
    )
    repositories.assign_user_to_program_admin(
        "admin",
        {"username": "editor_a", "program_ids": [str(program["id"])], "role": repositories.EDITOR_ROLE, "assigned_sections": "", "is_active": True},
    )

    payload = permission_matrix_admin("admin")
    rows = [dict(row) for row in payload["rows"]]
    for row in rows:
        if row["permission"] == "stats.view":
            row[repositories.EDITOR_ROLE] = False
    update_permission_matrix_admin("admin", rows, payload["sidebar_rows"])

    with pytest.raises(PermissionError):
        repositories.stats_payload("editor_a", str(program["id"]))


def test_operation_matrix_groups_follow_sidebar_modules_completely(tmp_path, monkeypatch):
    from backend.enterprise.matrix import permission_matrix_public, sidebar_matrix_public

    _isolated_db(tmp_path, monkeypatch, "sidebar_complete_catalog")
    permission_rows = permission_matrix_public()
    sidebar_rows = sidebar_matrix_public()
    categories = {row["category"] for row in permission_rows}
    sidebar_labels = {row["label"] for row in sidebar_rows}
    assert sidebar_labels.issubset(categories)


def test_program_management_category_contains_all_required_subsections(tmp_path, monkeypatch):
    from backend.enterprise.matrix import permission_matrix_public

    _isolated_db(tmp_path, monkeypatch, "program_management_complete_catalog")
    rows = [row for row in permission_matrix_public() if row["category"] == "Program Yönetimi"]
    labels = {row["label"] for row in rows}
    permissions = {row["permission"] for row in rows}
    assert {
        "Kurum Yönetimi",
        "Tanımlı Programlar",
        "Yeni Program",
        "Program Kopyala",
        "Program Bazlı Kullanıcı ve Rol Atama",
        "Program Kullanıcıları",
    }.issubset(labels)
    assert {
        "tenant.manage",
        "program.list.view",
        "program.create",
        "program.clone",
        "program.assign_users",
        "program.users.view",
    }.issubset(permissions)


def test_permission_catalog_is_unique_and_large_enough_for_full_dashboard(tmp_path, monkeypatch):
    from backend.enterprise.matrix import permission_matrix_public

    _isolated_db(tmp_path, monkeypatch, "unique_complete_catalog")
    rows = permission_matrix_public()
    permissions = [row["permission"] for row in rows]
    assert len(permissions) == len(set(permissions))
    assert len(rows) >= 120


def test_permission_matrix_keeps_active_admin_recovery_path_open(tmp_path, monkeypatch):
    from backend.enterprise.matrix import permission_matrix_admin, update_permission_matrix_admin

    _isolated_db(tmp_path, monkeypatch, "permission_self_protection")
    payload = permission_matrix_admin("admin")
    rows = [dict(row) for row in payload["rows"]]
    sidebar_rows = [dict(row) for row in payload["sidebar_rows"]]
    for row in rows:
        if row["permission"] in {"permission.manage", "sidebar.manage"}:
            row["Süper Admin"] = False
    for row in sidebar_rows:
        if row["module"] == "permissions":
            row["Süper Admin"] = False

    result = update_permission_matrix_admin("admin", rows, sidebar_rows)
    protected_permissions = {row["permission"]: row["Süper Admin"] for row in result["rows"] if row["permission"] in {"permission.manage", "sidebar.manage"}}
    protected_sidebar = {row["module"]: row["Süper Admin"] for row in result["sidebar_rows"] if row["module"] == "permissions"}

    assert protected_permissions == {"permission.manage": True, "sidebar.manage": True}
    assert protected_sidebar == {"permissions": True}
