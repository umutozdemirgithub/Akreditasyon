from __future__ import annotations

import pytest


def _isolated_db(tmp_path, monkeypatch, name: str):
    from backend import config, db, file_security, repositories

    data_dir = tmp_path / name
    sqlite_path = data_dir / "faculty.sqlite3"
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


def test_faculty_admin_role_assigns_entire_faculty_scope(tmp_path, monkeypatch):
    repositories = _isolated_db(tmp_path, monkeypatch, "faculty_scope")
    repositories.upsert_user_admin(
        "admin",
        {
            "username": "faculty_owner",
            "password": "FacultyOwner_2026!",
            "role": repositories.EDITOR_ROLE,
            "tenant_id": "tenant_default",
            "tenant_scope": "tenant",
            "full_name": "Faculty Owner",
            "is_active": True,
        },
    )
    p1 = repositories.create_program_admin("admin", {"school_name": "Mühendislik Fakültesi", "faculty_name": "Mühendislik Fakültesi", "department_name": "A", "program_name": "Program A", "report_year": "2026", "accreditation_profile": "MEDEK"})
    p2 = repositories.create_program_admin("admin", {"school_name": "Mühendislik Fakültesi", "faculty_name": "Mühendislik Fakültesi", "department_name": "B", "program_name": "Program B", "report_year": "2026", "accreditation_profile": "MEDEK"})

    rows = repositories.assign_user_to_program_admin(
        "admin",
        {
            "username": "faculty_owner",
            "role": repositories.FACULTY_ADMIN_ROLE,
            "program_ids": [p1["id"], p2["id"]],
            "assigned_sections": "",
            "is_active": True,
        },
    )

    assigned = [row for row in rows if row["username"] == "faculty_owner"]
    assert {row["program_id"] for row in assigned} == {p1["id"], p2["id"]}
    assert {row["role"] for row in assigned} == {repositories.FACULTY_ADMIN_ROLE}
    assert repositories.get_program_role("faculty_owner", p1["id"]) == repositories.FACULTY_ADMIN_ROLE
    assert repositories.get_user("faculty_owner", active_only=True)["faculty_name"] == "Mühendislik Fakültesi"


def test_faculty_admin_role_cannot_span_multiple_faculties(tmp_path, monkeypatch):
    repositories = _isolated_db(tmp_path, monkeypatch, "faculty_scope_reject")
    repositories.upsert_user_admin(
        "admin",
        {
            "username": "faculty_owner",
            "password": "FacultyOwner_2026!",
            "role": repositories.EDITOR_ROLE,
            "tenant_id": "tenant_default",
            "tenant_scope": "tenant",
            "full_name": "Faculty Owner",
            "is_active": True,
        },
    )
    p1 = repositories.create_program_admin("admin", {"school_name": "Mühendislik Fakültesi", "faculty_name": "Mühendislik Fakültesi", "department_name": "A", "program_name": "Program A", "report_year": "2026", "accreditation_profile": "MEDEK"})
    p2 = repositories.create_program_admin("admin", {"school_name": "Eğitim Fakültesi", "faculty_name": "Eğitim Fakültesi", "department_name": "B", "program_name": "Program B", "report_year": "2026", "accreditation_profile": "MEDEK"})

    with pytest.raises(ValueError, match="Birim Admin"):
        repositories.assign_user_to_program_admin(
            "admin",
            {
                "username": "faculty_owner",
                "role": repositories.FACULTY_ADMIN_ROLE,
                "program_ids": [p1["id"], p2["id"]],
                "assigned_sections": "",
                "is_active": True,
            },
        )



def _isolated_db(tmp_path, monkeypatch, name: str):
    from backend import config, db, file_security, repositories

    data_dir = tmp_path / name
    sqlite_path = data_dir / "scope.sqlite3"
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


def test_faculty_admin_program_management_is_faculty_scoped(tmp_path, monkeypatch):
    repositories = _isolated_db(tmp_path, monkeypatch, "faculty_program_management_scope")
    repositories.upsert_user_admin("admin", {"username": "faculty_admin", "password": "Faculty_Admin_2026!", "role": repositories.FACULTY_ADMIN_ROLE, "tenant_id": "tenant_default", "tenant_scope": "tenant", "faculty_name": "Mühendislik Fakültesi", "is_active": True})
    in_scope = repositories.create_program_admin("admin", {"school_name": "Mühendislik Fakültesi", "faculty_name": "Mühendislik Fakültesi", "department_name": "A", "program_name": "Program A", "report_year": "2026", "accreditation_profile": "MEDEK"})
    out_scope = repositories.create_program_admin("admin", {"school_name": "Eğitim Fakültesi", "faculty_name": "Eğitim Fakültesi", "department_name": "B", "program_name": "Program B", "report_year": "2026", "accreditation_profile": "MEDEK"})

    rows = repositories.list_programs_admin("faculty_admin")
    assert {row["id"] for row in rows} == {in_scope["id"]}
    assert repositories.assert_program_access("faculty_admin", in_scope["id"]) == repositories.FACULTY_ADMIN_ROLE
    with pytest.raises(PermissionError):
        repositories.assert_program_operation_permission("faculty_admin", out_scope["id"], "program.edit")


def test_faculty_admin_cannot_assign_peer_or_other_faculty(tmp_path, monkeypatch):
    repositories = _isolated_db(tmp_path, monkeypatch, "faculty_assignment_guard")
    repositories.upsert_user_admin("admin", {"username": "faculty_admin", "password": "Faculty_Admin_2026!", "role": repositories.FACULTY_ADMIN_ROLE, "tenant_id": "tenant_default", "tenant_scope": "tenant", "faculty_name": "Mühendislik Fakültesi", "is_active": True})
    repositories.upsert_user_admin("admin", {"username": "editor_a", "password": "Editor_A_2026!", "role": repositories.EDITOR_ROLE, "tenant_id": "tenant_default", "tenant_scope": "tenant", "faculty_name": "Mühendislik Fakültesi", "is_active": True})
    repositories.upsert_user_admin("admin", {"username": "peer_fac", "password": "Peer_Faculty_2026!", "role": repositories.FACULTY_ADMIN_ROLE, "tenant_id": "tenant_default", "tenant_scope": "tenant", "faculty_name": "Mühendislik Fakültesi", "is_active": True})
    in_scope = repositories.create_program_admin("admin", {"school_name": "Mühendislik Fakültesi", "faculty_name": "Mühendislik Fakültesi", "department_name": "A", "program_name": "Program A", "report_year": "2026", "accreditation_profile": "MEDEK"})
    out_scope = repositories.create_program_admin("admin", {"school_name": "Eğitim Fakültesi", "faculty_name": "Eğitim Fakültesi", "department_name": "B", "program_name": "Program B", "report_year": "2026", "accreditation_profile": "MEDEK"})

    repositories.assign_user_to_program_admin("faculty_admin", {"username": "editor_a", "role": repositories.EDITOR_ROLE, "program_ids": [in_scope["id"]], "is_active": True})
    with pytest.raises(PermissionError):
        repositories.assign_user_to_program_admin("faculty_admin", {"username": "peer_fac", "role": repositories.FACULTY_ADMIN_ROLE, "program_ids": [in_scope["id"]], "is_active": True})
    with pytest.raises(PermissionError):
        repositories.assign_user_to_program_admin("faculty_admin", {"username": "editor_a", "role": repositories.EDITOR_ROLE, "program_ids": [out_scope["id"]], "is_active": True})


def test_report_settings_are_program_scoped(tmp_path, monkeypatch):
    repositories = _isolated_db(tmp_path, monkeypatch, "program_settings_scope")
    p1 = repositories.create_program_admin("admin", {"school_name": "A Fakültesi", "faculty_name": "A Fakültesi", "program_name": "Program A", "report_year": "2026", "accreditation_profile": "MEDEK"})
    p2 = repositories.create_program_admin("admin", {"school_name": "B Fakültesi", "faculty_name": "B Fakültesi", "program_name": "Program B", "report_year": "2026", "accreditation_profile": "MEDEK"})

    repositories.update_settings_admin("admin", p1["id"], {"report_no": "R-A", "doc_date": "2026-01-01"})

    assert repositories.get_settings(p1["id"])["report_no"] == "R-A"
    assert repositories.get_settings(p2["id"]).get("report_no", "") != "R-A"


def test_faculty_admin_cannot_overwrite_tenant_operation_matrix(tmp_path, monkeypatch):
    from backend.enterprise.matrix import permission_matrix_admin, role_permission_allowed, update_permission_matrix_admin

    repositories = _isolated_db(tmp_path, monkeypatch, "faculty_matrix_no_overwrite")
    repositories.upsert_user_admin("admin", {"username": "faculty_admin", "password": "Faculty_Admin_2026!", "role": repositories.FACULTY_ADMIN_ROLE, "tenant_id": "tenant_default", "tenant_scope": "tenant", "faculty_name": "Mühendislik Fakültesi", "is_active": True})

    super_payload = permission_matrix_admin("admin")
    super_rows = [dict(row) for row in super_payload["rows"]]
    for row in super_rows:
        if row["permission"] in {"permission.manage", "sidebar.manage"}:
            row[repositories.FACULTY_ADMIN_ROLE] = True
    super_sidebar = [dict(row) for row in super_payload["sidebar_rows"]]
    for row in super_sidebar:
        if row["module"] == "permissions":
            row[repositories.FACULTY_ADMIN_ROLE] = True
    update_permission_matrix_admin("admin", super_rows, super_sidebar)

    payload = permission_matrix_admin("faculty_admin")
    rows = [dict(row) for row in payload["rows"]]
    for row in rows:
        if row["permission"] == "program.create":
            row[repositories.EDITOR_ROLE] = True
    update_permission_matrix_admin("faculty_admin", rows, payload["sidebar_rows"])

    assert role_permission_allowed(repositories.EDITOR_ROLE, "program.create", "tenant_default") is False
