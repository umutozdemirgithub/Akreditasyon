from __future__ import annotations

import pytest


@pytest.fixture()
def isolated_program(tmp_path, monkeypatch):
    from backend import config, db, file_security, repositories

    data_dir = tmp_path / "medek_data"
    sqlite_path = data_dir / "test.sqlite3"
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
    repositories.upsert_user_admin(
        "admin",
        {
            "username": "section_editor",
            "role": repositories.EDITOR_ROLE,
            "password": "Editor_Strong_2026!",
            "full_name": "Section Editor",
            "is_active": True,
        },
    )
    program = repositories.create_program_admin(
        "admin",
        {
            "university_name": "Test University",
            "school_name": "Test School",
            "department_name": "Test Department",
            "program_name": "Access Control Program",
            "report_year": "2026",
            "accreditation_profile": "MEDEK",
        },
    )
    program_id = str(program["id"])
    sections = repositories.list_sections("admin", program_id)
    allowed_key = str(sections[0]["section_key"])
    blocked_key = str(sections[1]["section_key"])
    repositories.assign_user_to_program_admin(
        "admin",
        {
            "username": "section_editor",
            "role": repositories.EDITOR_ROLE,
            "program_ids": [program_id],
            "assigned_sections": allowed_key,
            "is_active": True,
        },
    )
    return repositories, program_id, allowed_key, blocked_key


def test_editor_cannot_download_or_link_hidden_section_evidence(isolated_program):
    repositories, program_id, allowed_key, blocked_key = isolated_program
    evidence = repositories.save_evidence_file(
        "admin",
        program_id,
        [blocked_key],
        "B.K1",
        "hidden",
        "hidden.pdf",
        b"%PDF-1.4\n% hidden test file\n",
    )

    assert repositories.list_evidence("section_editor", program_id) == []
    with pytest.raises(PermissionError):
        repositories.evidence_file_path("section_editor", program_id, str(evidence["id"]))
    with pytest.raises(PermissionError):
        repositories.link_evidence_to_section("section_editor", program_id, str(evidence["id"]), allowed_key)


def test_editor_cannot_attach_or_move_hidden_section_table(isolated_program):
    repositories, program_id, allowed_key, blocked_key = isolated_program
    table = repositories.save_table(
        "admin",
        program_id,
        blocked_key,
        "Hidden table",
        [{"secret": "value"}],
        {},
    )

    with pytest.raises(PermissionError):
        repositories.attach_table_to_section("section_editor", program_id, str(table["id"]), allowed_key, "Copied table")
    with pytest.raises(PermissionError):
        repositories.save_table(
            "section_editor",
            program_id,
            allowed_key,
            "Moved table",
            [{"secret": "value"}],
            {},
            str(table["id"]),
        )


def test_forced_password_change_flow(isolated_program):
    repositories, _program_id, _allowed_key, _blocked_key = isolated_program
    user_before = repositories.get_user("section_editor", active_only=True)
    assert user_before is not None
    assert repositories.public_user(user_before)["must_change_password"] is True

    with pytest.raises(ValueError):
        repositories.change_own_password("section_editor", "wrong", "Editor_New_2026!")

    changed = repositories.change_own_password("section_editor", "Editor_Strong_2026!", "Editor_New_2026!")
    assert repositories.public_user(changed)["must_change_password"] is False
    assert repositories.authenticate_user("section_editor", "Editor_Strong_2026!") is None
    assert repositories.authenticate_user("section_editor", "Editor_New_2026!") is not None


def test_dashboard_report_groups_include_complete_report_directory_blocks(isolated_program):
    repositories, program_id, *_ = isolated_program
    payload = repositories.stats_payload("admin", program_id)
    titles = [row["report_group_title"] for row in payload["report_groups"]]
    assert "A. Programa İlişkin Genel Bilgiler" in titles
    assert "B. Değerlendirme Özeti" in titles
    assert "EK I – PROGRAMA İLİŞKİN EK BİLGİLER" in titles
    assert "EK II – KURUM PROFİLİ" in titles
    assert len(payload["measure_criteria"]) >= 9


def test_epdad_dashboard_report_groups_include_standard_area_and_appendices(isolated_program):
    repositories, *_ = isolated_program
    program = repositories.create_program_admin(
        "admin",
        {
            "university_name": "Test University",
            "school_name": "Eğitim Fakültesi",
            "department_name": "Temel Eğitim Bölümü",
            "program_name": "Okul Öncesi Öğretmenliği",
            "report_year": "2026",
            "accreditation_profile": "EPDAD",
        },
    )
    payload = repositories.stats_payload("admin", str(program["id"]))
    titles = [row["report_group_title"] for row in payload["report_groups"]]
    assert "A. Programa İlişkin Genel Bilgiler" in titles
    assert "B. Standart Alanları (Başlangıç, Süreç ve Ürün Standartları)" in titles
    assert "EK I – PROGRAMA İLİŞKİN EK BİLGİLER" in titles
    assert "EK II – KURUM PROFİLİ" in titles
    assert len(payload["measure_criteria"]) >= 7
