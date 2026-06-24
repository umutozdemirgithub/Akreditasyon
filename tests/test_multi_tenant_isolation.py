from __future__ import annotations

import pytest


def test_tenant_admin_sees_only_own_programs(tmp_path, monkeypatch):
    from backend import config, db, file_security, repositories
    from backend.tenancy import save_tenant_admin, DEFAULT_TENANT_ID

    data_dir = tmp_path / "medek_tenant_data"
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
    monkeypatch.setattr(file_security, "EVIDENCE_DIR", evidence_dir)

    db.init_db()
    tenant_b = save_tenant_admin("admin", {"name": "İkinci Üniversite", "code": "UNI2", "is_active": True})
    tenant_b_id = str(tenant_b["id"])

    default_program = repositories.create_program_admin(
        "admin",
        {"tenant_id": DEFAULT_TENANT_ID, "program_name": "Default Program", "report_year": "2026", "accreditation_profile": "MEDEK"},
    )
    tenant_program = repositories.create_program_admin(
        "admin",
        {"tenant_id": tenant_b_id, "program_name": "Tenant Program", "report_year": "2026", "accreditation_profile": "MEDEK"},
    )

    repositories.upsert_user_admin(
        "admin",
        {
            "username": "tenant_admin_b",
            "password": "Tenant_Admin_2026!",
            "role": "Admin",
            "tenant_id": tenant_b_id,
            "tenant_scope": "tenant",
            "full_name": "Tenant Admin B",
            "is_active": True,
        },
    )

    visible = repositories.list_programs_for_user("tenant_admin_b")
    visible_ids = {row["id"] for row in visible}
    assert str(tenant_program["id"]) in visible_ids
    assert str(default_program["id"]) not in visible_ids

    with pytest.raises(PermissionError):
        repositories.list_sections("tenant_admin_b", str(default_program["id"]))


def test_cross_tenant_program_assignment_is_rejected(tmp_path, monkeypatch):
    from backend import config, db, file_security, repositories
    from backend.tenancy import save_tenant_admin, DEFAULT_TENANT_ID

    data_dir = tmp_path / "medek_tenant_assign"
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
    monkeypatch.setattr(file_security, "EVIDENCE_DIR", evidence_dir)

    db.init_db()
    tenant_b = save_tenant_admin("admin", {"name": "Tenant B", "code": "TB", "is_active": True})
    tenant_program = repositories.create_program_admin(
        "admin",
        {"tenant_id": str(tenant_b["id"]), "program_name": "Tenant B Program", "report_year": "2026", "accreditation_profile": "MEDEK"},
    )
    repositories.upsert_user_admin(
        "admin",
        {
            "username": "default_editor",
            "password": "Default_Editor_2026!",
            "role": "Editör / Hazırlayıcı",
            "tenant_id": DEFAULT_TENANT_ID,
            "full_name": "Default Editor",
            "is_active": True,
        },
    )

    with pytest.raises(PermissionError):
        repositories.assign_user_to_program_admin(
            "admin",
            {"username": "default_editor", "role": "Editör / Hazırlayıcı", "program_ids": [str(tenant_program["id"])], "assigned_sections": "", "is_active": True},
        )


def test_tenant_faculty_save_updates_existing_record(tmp_path, monkeypatch):
    from backend import config, db, file_security, repositories
    from backend.tenancy import DEFAULT_TENANT_ID, list_faculties_admin, save_faculty_admin

    data_dir = tmp_path / "medek_tenant_faculty"
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
    monkeypatch.setattr(file_security, "EVIDENCE_DIR", evidence_dir)

    db.init_db()
    first = save_faculty_admin(
        "admin",
        {"tenant_id": DEFAULT_TENANT_ID, "faculty_name": "Engineering Faculty", "accreditation_profile": "MÜDEK", "is_active": True},
    )
    second = save_faculty_admin(
        "admin",
        {"tenant_id": DEFAULT_TENANT_ID, "faculty_name": "Engineering Faculty", "accreditation_profile": "EPDAD", "is_active": False},
    )

    rows = [row for row in list_faculties_admin("admin", DEFAULT_TENANT_ID) if row["faculty_name"] == "Engineering Faculty"]
    assert second["id"] == first["id"]
    assert len(rows) == 1
    assert rows[0]["accreditation_profile"] == "EPDAD"
    assert rows[0]["is_active"] in (0, False)


def test_program_creation_registers_faculty_for_tenant(tmp_path, monkeypatch):
    from backend import config, db, file_security, repositories
    from backend.tenancy import DEFAULT_TENANT_ID, list_faculties_admin

    data_dir = tmp_path / "medek_program_faculty"
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
    monkeypatch.setattr(file_security, "EVIDENCE_DIR", evidence_dir)

    db.init_db()
    repositories.create_program_admin(
        "admin",
        {
            "tenant_id": DEFAULT_TENANT_ID,
            "university_name": "Erciyes Üniversitesi",
            "school_name": "Mühendislik Fakültesi",
            "faculty_name": "Mühendislik Fakültesi",
            "department_name": "Bilgisayar Mühendisliği Bölümü",
            "program_name": "Bilgisayar Mühendisliği",
            "report_year": "2026",
            "accreditation_profile": "MÜDEK",
        },
    )

    rows = [row for row in list_faculties_admin("admin", DEFAULT_TENANT_ID) if row["faculty_name"] == "Mühendislik Fakültesi"]
    assert len(rows) == 1
    assert rows[0]["accreditation_profile"] == "MÜDEK"


def test_tenant_delete_blocks_attached_records(tmp_path, monkeypatch):
    from backend import config, db, file_security, repositories
    from backend.tenancy import delete_tenant_admin, save_tenant_admin

    data_dir = tmp_path / "medek_tenant_delete"
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
    monkeypatch.setattr(file_security, "EVIDENCE_DIR", evidence_dir)

    db.init_db()
    tenant = save_tenant_admin("admin", {"name": "Silinemez Üniversite", "code": "SU", "is_active": True})
    repositories.create_program_admin(
        "admin",
        {"tenant_id": tenant["id"], "program_name": "Bağlı Program", "report_year": "2026", "accreditation_profile": "MEDEK"},
    )

    with pytest.raises(ValueError):
        delete_tenant_admin("admin", str(tenant["id"]))


def test_archived_tenant_program_users_are_hidden_from_admin_views(tmp_path, monkeypatch):
    from backend import config, db, file_security, repositories
    from backend.tenancy import delete_tenant_admin, save_tenant_admin

    data_dir = tmp_path / "medek_tenant_archive_visibility"
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
    monkeypatch.setattr(file_security, "EVIDENCE_DIR", evidence_dir)

    db.init_db()
    tenant = save_tenant_admin("admin", {"name": "AAA University", "code": "AAA", "is_active": True})
    tenant_id = str(tenant["id"])
    program = repositories.create_program_admin(
        "admin",
        {"tenant_id": tenant_id, "program_name": "Bilgisayar Mühendisliği", "report_year": "2026", "accreditation_profile": "MÜDEK"},
    )
    repositories.upsert_user_admin(
        "admin",
        {
            "username": "aaa_editor",
            "password": "AAA_Editor_2026!",
            "role": "Editör / Hazırlayıcı",
            "tenant_id": tenant_id,
            "tenant_scope": "tenant",
            "full_name": "AAA Editor",
            "is_active": True,
        },
    )
    repositories.assign_user_to_program_admin(
        "admin",
        {"username": "aaa_editor", "role": "Editör / Hazırlayıcı", "program_ids": [str(program["id"])], "assigned_sections": "", "is_active": True},
    )

    before = repositories.list_program_users_admin("admin")
    assert any(row["tenant_id"] == tenant_id for row in before)

    delete_tenant_admin("admin", tenant_id, mode="archive_children")

    after_users = repositories.list_program_users_admin("admin")
    after_programs = repositories.list_programs_admin("admin", include_inactive=True)
    assert all(row.get("tenant_id") != tenant_id for row in after_users)
    assert all(row.get("tenant_id") != tenant_id for row in after_programs)


def test_super_admin_can_purge_tenant_with_attached_records(tmp_path, monkeypatch):
    from backend import config, db, file_security, repositories
    from backend.tenancy import delete_tenant_admin, save_tenant_admin

    data_dir = tmp_path / "medek_tenant_purge"
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
    monkeypatch.setattr(file_security, "EVIDENCE_DIR", evidence_dir)

    db.init_db()
    tenant = save_tenant_admin("admin", {"name": "Kalıcı Silinecek Üniversite", "code": "KSU", "is_active": True})
    tenant_id = str(tenant["id"])
    program = repositories.create_program_admin(
        "admin",
        {"tenant_id": tenant_id, "program_name": "Bağlı Program", "report_year": "2026", "accreditation_profile": "MEDEK"},
    )
    repositories.upsert_user_admin(
        "admin",
        {
            "username": "ksu_editor",
            "password": "Ksu_Editor_2026!",
            "role": "Editör / Hazırlayıcı",
            "tenant_id": tenant_id,
            "tenant_scope": "tenant",
            "full_name": "KSU Editor",
            "is_active": True,
        },
    )
    repositories.assign_user_to_program_admin(
        "admin",
        {"username": "ksu_editor", "role": "Editör / Hazırlayıcı", "program_ids": [str(program["id"])], "assigned_sections": "", "is_active": True},
    )

    result = delete_tenant_admin("admin", tenant_id, mode="purge")
    assert result["purged"] is True

    with db.get_conn() as conn:
        assert conn.execute("SELECT COUNT(*) AS n FROM tenants WHERE id=?", (tenant_id,)).fetchone()["n"] == 0
        assert conn.execute("SELECT COUNT(*) AS n FROM programs WHERE tenant_id=?", (tenant_id,)).fetchone()["n"] == 0
        assert conn.execute("SELECT COUNT(*) AS n FROM program_users WHERE tenant_id=?", (tenant_id,)).fetchone()["n"] == 0
        assert conn.execute("SELECT COUNT(*) AS n FROM users WHERE tenant_id=?", (tenant_id,)).fetchone()["n"] == 0


def test_tenant_admin_cannot_purge_tenant(tmp_path, monkeypatch):
    from backend import config, db, file_security, repositories
    from backend.tenancy import delete_tenant_admin, save_tenant_admin

    data_dir = tmp_path / "medek_tenant_purge_permission"
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
    monkeypatch.setattr(file_security, "EVIDENCE_DIR", evidence_dir)

    db.init_db()
    tenant = save_tenant_admin("admin", {"name": "Kurum Admin Üniversitesi", "code": "KAU", "is_active": True})
    tenant_id = str(tenant["id"])
    repositories.upsert_user_admin(
        "admin",
        {
            "username": "kau_admin",
            "password": "Kau_Admin_2026!",
            "role": "Kurum Admin",
            "tenant_id": tenant_id,
            "tenant_scope": "tenant",
            "full_name": "KAU Admin",
            "is_active": True,
        },
    )

    with pytest.raises(PermissionError):
        delete_tenant_admin("kau_admin", tenant_id, mode="purge")


def test_super_admin_can_purge_default_tenant_institution_data(tmp_path, monkeypatch):
    from backend import config, db, file_security, repositories
    from backend.tenancy import DEFAULT_TENANT_ID, delete_tenant_admin, save_faculty_admin, save_tenant_admin

    data_dir = tmp_path / "medek_default_tenant_purge"
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
    monkeypatch.setattr(file_security, "EVIDENCE_DIR", evidence_dir)

    db.init_db()
    save_tenant_admin("admin", {"id": DEFAULT_TENANT_ID, "name": "Niğde", "code": "OHU", "domain": "www.ohu.edu.tr", "is_active": True})
    save_faculty_admin("admin", {"tenant_id": DEFAULT_TENANT_ID, "faculty_name": "Mühendislik Fakültesi", "accreditation_profile": "MÜDEK"})
    program = repositories.create_program_admin(
        "admin",
        {"tenant_id": DEFAULT_TENANT_ID, "program_name": "Bağlı Program", "report_year": "2026", "accreditation_profile": "MEDEK"},
    )
    repositories.upsert_user_admin(
        "admin",
        {
            "username": "ohu_editor",
            "password": "Ohu_Editor_2026!",
            "role": "Editör / Hazırlayıcı",
            "tenant_id": DEFAULT_TENANT_ID,
            "tenant_scope": "tenant",
            "full_name": "OHU Editor",
            "is_active": True,
        },
    )
    repositories.assign_user_to_program_admin(
        "admin",
        {"username": "ohu_editor", "role": "Editör / Hazırlayıcı", "program_ids": [str(program["id"])], "assigned_sections": "", "is_active": True},
    )

    result = delete_tenant_admin("admin", DEFAULT_TENANT_ID, mode="purge")
    assert result["purged"] is True
    assert result["reset_default_tenant"] is True

    with db.get_conn() as conn:
        default_row = conn.execute("SELECT name, code, domain, setup_completed_at FROM tenants WHERE id=?", (DEFAULT_TENANT_ID,)).fetchone()
        assert default_row is not None
        assert default_row["name"] == ""
        assert default_row["code"] == ""
        assert default_row["domain"] == ""
        assert default_row["setup_completed_at"] == ""
        assert conn.execute("SELECT COUNT(*) AS n FROM programs WHERE COALESCE(tenant_id, ?) = ?", (DEFAULT_TENANT_ID, DEFAULT_TENANT_ID)).fetchone()["n"] == 0
        assert conn.execute("SELECT COUNT(*) AS n FROM program_users WHERE COALESCE(tenant_id, ?) = ?", (DEFAULT_TENANT_ID, DEFAULT_TENANT_ID)).fetchone()["n"] == 0
        assert conn.execute("SELECT COUNT(*) AS n FROM tenant_faculties WHERE tenant_id=?", (DEFAULT_TENANT_ID,)).fetchone()["n"] == 0
        assert conn.execute("SELECT COUNT(*) AS n FROM users WHERE username='ohu_editor'").fetchone()["n"] == 0
        admin = conn.execute("SELECT role, tenant_id, tenant_scope, is_active FROM users WHERE username='admin'").fetchone()
        assert admin is not None
        assert admin["role"] == "Süper Admin"
        assert admin["tenant_id"] == DEFAULT_TENANT_ID
        assert admin["tenant_scope"] == "global"
        assert admin["is_active"] == 1
