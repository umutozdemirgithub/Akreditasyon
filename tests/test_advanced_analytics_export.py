from __future__ import annotations


def _patch_data_dir(tmp_path, monkeypatch):
    from backend import config, db, file_security, repositories

    data_dir = tmp_path / "medek_analytics_export_data"
    sqlite_path = data_dir / "analytics.sqlite3"
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
    return db, repositories


def test_advanced_analytics_payload_and_docx_export(tmp_path, monkeypatch):
    db, repositories = _patch_data_dir(tmp_path, monkeypatch)
    db.init_db()
    program = repositories.create_program_admin(
        "admin",
        {"program_name": "Analytics Export Program", "report_year": "2026", "accreditation_profile": "MEDEK"},
    )
    program_id = str(program["id"])
    sections = repositories.list_sections("admin", program_id)
    first = sections[0]["section_key"]
    repositories.update_section(
        "admin",
        program_id,
        first,
        {
            "status": "Taslak Hazır",
            "approval_status": "Onaylandı",
            "report_text": "Bu bölüm analytics export testi için yeterli metin içerir.",
            "planla": "Planlama yapılmıştır.",
            "uygula": "Uygulama tamamlanmıştır.",
            "kontrol": "Kontrol mekanizması işletilmiştir.",
            "onlem": "Önlem döngüsü tanımlanmıştır.",
            "notes": "",
            "deadline": "",
        },
    )

    from backend.enterprise.dashboard import advanced_reporting
    from backend.reporting import build_advanced_analytics_docx

    payload = advanced_reporting("admin", program_id)
    assert payload["summary"]["total"] >= 1
    assert "approval_distribution" in payload
    assert "status_distribution" in payload
    assert "trend_chart" in payload

    docx_data = build_advanced_analytics_docx("admin", program_id)
    assert docx_data.startswith(b"PK")
    assert len(docx_data) > 10000
