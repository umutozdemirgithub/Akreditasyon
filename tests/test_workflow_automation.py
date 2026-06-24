from __future__ import annotations

from datetime import date, timedelta


def _patch_data_dir(tmp_path, monkeypatch):
    from backend import config, db, file_security, repositories

    data_dir = tmp_path / "medek_workflow_data"
    sqlite_path = data_dir / "workflow.sqlite3"
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


def test_workflow_automation_preview_and_run(tmp_path, monkeypatch):
    db, repositories = _patch_data_dir(tmp_path, monkeypatch)
    from backend.db import get_conn
    from backend.enterprise.workflow_automation import (
        run_workflow_automation,
        update_workflow_automation_settings,
        workflow_automation_preview,
    )

    db.init_db()
    program = repositories.create_program_admin(
        "admin",
        {"program_name": "Workflow Program", "report_year": "2026", "accreditation_profile": "MEDEK"},
    )
    program_id = str(program["id"])
    repositories.upsert_user_admin(
        "admin",
        {
            "username": "editor1",
            "password": "Editor_2026_Strong!",
            "role": "Editör / Hazırlayıcı",
            "full_name": "Editor One",
            "email": "editor1@example.edu.tr",
            "is_active": True,
        },
    )
    repositories.assign_user_to_program_admin(
        "admin",
        {"username": "editor1", "program_ids": [program_id], "role": "Editör / Hazırlayıcı", "assigned_sections": "", "is_active": True},
    )
    section_key = repositories.list_sections("admin", program_id)[0]["section_key"]
    overdue_day = (date.today() - timedelta(days=2)).isoformat()
    repositories.update_section(
        "admin",
        program_id,
        section_key,
        {"status": "Devam Ediyor", "report_text": "", "planla": "", "uygula": "", "kontrol": "", "onlem": "", "notes": "", "deadline": overdue_day},
    )
    update_workflow_automation_settings(
        "admin",
        program_id,
        {"enabled": True, "deadline_days_before": 7, "repeat_days": 0, "include_overdue": True, "include_draft_followup": False},
    )
    preview = workflow_automation_preview("admin", program_id)
    assert preview["total"] >= 1
    assert any(row["category"] == "Geciken termin" for row in preview["rows"])

    result = run_workflow_automation("admin", program_id, {"force": True}, None)
    assert result["created"] >= 1
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM notification_events WHERE event_type='workflow_reminder'").fetchone()["n"]
    assert int(count) >= 1
