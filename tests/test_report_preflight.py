from __future__ import annotations

import pytest


@pytest.fixture()
def report_program(tmp_path, monkeypatch):
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
    program = repositories.create_program_admin(
        "admin",
        {
            "university_name": "Test University",
            "school_name": "Test School",
            "department_name": "Test Department",
            "program_name": "Report Preflight Program",
            "report_year": "2026",
            "accreditation_profile": "MEDEK",
        },
    )
    return repositories, str(program["id"])


def test_report_preflight_blocks_empty_final_report(report_program):
    repositories, program_id = report_program

    payload = repositories.report_preflight_payload("admin", program_id)

    assert payload["ready"] is False
    assert payload["blocker_count"] > 0
    assert any(item["code"] == "empty_text" for item in payload["top_actions"])
    with pytest.raises(ValueError):
        repositories.assert_report_export_ready("admin", program_id)


def test_quality_tracks_evidence_citations_and_preflight_row(report_program):
    repositories, program_id = report_program
    section = next(row for row in repositories.list_sections("admin", program_id) if str(row["section_key"]).startswith("1."))
    key = str(section["section_key"])
    code = f"{key}.K1"
    text = (
        f"{key} başlığı kapsamında öğrenci süreçleri kurul kararları, uygulama kayıtları ve izleme sonuçlarıyla yürütülmektedir. "
        f"Bu uygulama {code} kanıtı ile doğrulanmakta, elde edilen bulgular dönem sonunda program kurulunda değerlendirilmekte ve iyileştirme kararlarına aktarılmaktadır. "
        "Süreç, sorumlu birimler ve izleme yöntemi raporda açık biçimde tanımlanmıştır."
    )
    repositories.save_evidence_file("admin", program_id, [key], code, "Kurul kararı ve izleme raporu", "kanit.pdf", b"%PDF-1.4\n")
    repositories.update_section(
        "admin",
        program_id,
        key,
        {
            "status": repositories.READY,
            "report_text": text,
            "planla": "Süreç hedefleri ve sorumlu birimler tanımlanır.",
            "uygula": "Uygulamalar kayıt altına alınır.",
            "kontrol": "Sonuçlar dönem sonunda analiz edilir.",
            "onlem": "Eksikler kurul kararıyla iyileştirilir.",
            "notes": "",
            "deadline": "",
        },
    )

    updated = repositories.get_section("admin", program_id, key)
    quality = repositories.quality_for_section("admin", program_id, updated)
    preflight = repositories.report_preflight_payload("admin", program_id)
    row = next(item for item in preflight["rows"] if item["section_key"] == key)

    assert quality["cited_evidence"] == 1
    assert quality["uncited_evidence"] == 0
    assert row["uncited_evidence"] == 0
    assert not any(check["code"] == "no_evidence" for check in row["checks"])


def test_apply_ai_draft_updates_section_with_versioned_status(report_program):
    repositories, program_id = report_program
    section = repositories.list_sections("admin", program_id)[0]
    key = str(section["section_key"])

    updated = repositories.apply_ai_draft_to_section("admin", program_id, key, "AI tarafından önerilen kontrollü rapor metni.")

    assert updated["report_text"] == "AI tarafından önerilen kontrollü rapor metni."
    assert updated["status"] == repositories.READY
    assert "AI tam rapor taslağı" in updated["notes"]


def test_preview_payload_is_json_safe_for_non_finite_table_values(report_program):
    import json
    import math

    repositories, program_id = report_program
    section = repositories.list_sections("admin", program_id)[0]
    key = str(section["section_key"])

    repositories.save_table(
        "admin",
        program_id,
        key,
        "NaN Güvenli Tablo",
        [{"Gösterge": "Doluluk", "Değer": math.nan}, {"Gösterge": "Sınır", "Değer": math.inf}],
        {"columns": ["Gösterge", "Değer"], "source": math.nan},
    )

    payload = repositories.preview_payload("admin", program_id)
    tables = [table for row in payload["sections"] for table in row.get("tables", []) if table.get("table_name") == "NaN Güvenli Tablo"]

    assert tables
    assert tables[0]["rows"][0]["Değer"] is None
    assert tables[0]["rows"][1]["Değer"] is None
    assert tables[0]["meta"]["source"] is None
    json.dumps(payload, allow_nan=False)
