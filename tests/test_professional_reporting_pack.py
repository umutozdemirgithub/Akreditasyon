from __future__ import annotations

from pathlib import Path


def _isolated(tmp_path, monkeypatch):
    from backend import config, db, file_security, repositories

    data_dir = tmp_path / "medek_data"
    sqlite_path = data_dir / "test.sqlite3"
    evidence_dir = data_dir / "kanitlar"
    for module in (config, db, repositories, file_security):
        if hasattr(module, "DATA_DIR"):
            monkeypatch.setattr(module, "DATA_DIR", data_dir)
        if hasattr(module, "SQLITE_PATH"):
            monkeypatch.setattr(module, "SQLITE_PATH", sqlite_path)
        if hasattr(module, "EVIDENCE_DIR"):
            monkeypatch.setattr(module, "EVIDENCE_DIR", evidence_dir)
    db.init_db()
    return repositories


def test_professional_reporting_pack_backend_and_frontend_wiring():
    root = Path(__file__).resolve().parents[1]
    main = (root / "backend" / "main.py").read_text(encoding="utf-8")
    module = (root / "backend" / "professional_reporting.py").read_text(encoding="utf-8")
    studio_module = (root / "backend" / "section_studio.py").read_text(encoding="utf-8")
    api = (root / "frontend" / "src" / "api.js").read_text(encoding="utf-8")
    nav = (root / "frontend" / "src" / "config" / "navigation.jsx").read_text(encoding="utf-8")
    frontend = (root / "frontend" / "src" / "views" / "AppViews.jsx").read_text(encoding="utf-8")
    schema = (root / "tools" / "postgres_schema.sql").read_text(encoding="utf-8")

    assert "def professional_reporting_payload" in module
    assert "def consistency_check_payload" in module
    assert "def report_quality_payload" in module
    assert "def mock_audit_payload" in module
    assert "def build_report_package_zip" in module
    assert "premium_readiness" in module
    assert "Premium_98_Readiness.json" in module
    assert "pro_overview" in studio_module
    assert '@app.get("/api/programs/{program_id}/professional-reporting")' in main
    assert '@app.get("/api/programs/{program_id}/professional-reporting/package.zip")' in main
    assert "professionalReporting:" in api
    assert "professionalPackage:" in api
    assert "Profesyonel Raporlama" in nav
    assert "ProfessionalReportingView" in frontend
    assert "studio-pro-gate" in frontend
    assert "professional-pro-gate" in frontend
    assert "9.8+" in frontend
    assert "CREATE TABLE IF NOT EXISTS clause_library" in schema
    assert "CREATE TABLE IF NOT EXISTS content_blocks" in schema
    assert "CREATE TABLE IF NOT EXISTS auditor_share_links" in schema


def test_professional_reporting_smoke(tmp_path, monkeypatch):
    repositories = _isolated(tmp_path, monkeypatch)
    from backend.professional_reporting import (
        build_report_package_zip,
        insert_clause_into_section,
        list_clause_library,
        professional_reporting_payload,
    )
    from backend.section_studio import report_studio_payload

    program = repositories.create_program_admin(
        "admin",
        {
            "university_name": "Test University",
            "school_name": "Test MYO",
            "department_name": "Test Department",
            "program_name": "Professional Reporting Program",
            "report_year": "2026",
            "accreditation_profile": "MEDEK",
        },
    )
    program_id = str(program["id"])
    section_key = str(repositories.list_sections("admin", program_id)[0]["section_key"])
    repositories.upsert_user_admin(
        "admin",
        {
            "username": "editor_prof",
            "role": repositories.EDITOR_ROLE,
            "password": "Editor_Strong_2026!",
            "is_active": True,
        },
    )
    repositories.assign_user_to_program_admin(
        "admin",
        {
            "username": "editor_prof",
            "role": repositories.EDITOR_ROLE,
            "program_ids": [program_id],
            "assigned_sections": section_key,
            "is_active": True,
        },
    )
    repositories.update_section(
        "editor_prof",
        program_id,
        section_key,
        {"report_text": "Ölçüt 1 kapsamında 25 öğrenci için EK-I.K1 kanıtı sunulmuştur.", "status": repositories.READY},
    )

    payload = professional_reporting_payload("editor_prof", program_id)
    assert payload["quality"]["score"] >= 0
    assert payload["premium_pack"]["target_score"] == 98
    assert payload["quality"]["premium_readiness"]["target_label"] == "9.8+"
    assert "Premium_98_Readiness.json" in payload["package_manifest"]
    assert payload["consistency"]["total_issues"] >= 1
    studio = report_studio_payload("admin", program_id)
    assert studio["pro_overview"]["target_score"] == 98
    assert studio["pro_overview"]["target_label"] == "9.8+"
    assert studio["cards"][0]["pro_readiness"]["checklist"]
    clauses = list_clause_library("editor_prof", program_id, section_key)
    assert clauses
    updated = insert_clause_into_section("editor_prof", program_id, section_key, str(clauses[0]["id"]))
    assert clauses[0]["content"] in updated["report_text"]
    package = build_report_package_zip("editor_prof", program_id)
    assert package[:2] == b"PK"
