from __future__ import annotations

import pytest


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


def _create_editor_with_one_section(repositories):
    repositories.upsert_user_admin(
        "admin",
        {"username": "scoped_editor", "password": "Editor_Strong_2026!", "role": repositories.EDITOR_ROLE, "email": "editor@example.test", "is_active": True},
    )
    program = repositories.create_program_admin(
        "admin",
        {"program_name": "Scoped Program", "school_name": "Faculty A", "report_year": "2026", "accreditation_profile": "MEDEK"},
    )
    program_id = str(program["id"])
    sections = repositories.list_sections("admin", program_id)
    allowed = str(sections[0]["section_key"])
    blocked = str(sections[1]["section_key"])
    repositories.assign_user_to_program_admin(
        "admin",
        {"username": "scoped_editor", "role": repositories.EDITOR_ROLE, "program_ids": [program_id], "assigned_sections": allowed, "is_active": True},
    )
    return program_id, allowed, blocked


def test_version_diff_requires_section_visibility(tmp_path, monkeypatch):
    from backend.enterprise.versions import section_versions_diff

    repositories = _isolated_db(tmp_path, monkeypatch, "versions_scope")
    program_id, allowed, blocked = _create_editor_with_one_section(repositories)

    repositories.update_section("admin", program_id, blocked, {"report_text": "Secret blocked section snapshot"})

    assert section_versions_diff("scoped_editor", program_id, allowed)["section"]["section_key"] == allowed
    with pytest.raises(PermissionError):
        section_versions_diff("scoped_editor", program_id, blocked)


def test_program_insights_timeline_filters_unassigned_section_history(tmp_path, monkeypatch):
    from backend.db import now_iso, transaction
    from backend.insights import program_insights
    import uuid

    repositories = _isolated_db(tmp_path, monkeypatch, "insights_scope")
    program_id, allowed, blocked = _create_editor_with_one_section(repositories)

    with transaction() as conn:
        for key, note in [(allowed, "allowed submit"), (blocked, "blocked submit")]:
            conn.execute(
                "INSERT INTO section_approvals(id,program_id,section_key,status,requested_by,decided_by,note,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), program_id, key, repositories.SUBMITTED, "admin", "", note, now_iso()),
            )

    payload = program_insights("scoped_editor", program_id)
    timeline_keys = {str(row.get("section_key", "")) for row in payload["timeline"]}
    assert allowed in timeline_keys
    assert blocked not in timeline_keys


def test_notification_inbox_and_read_are_section_scoped(tmp_path, monkeypatch):
    from backend.insights import mark_notifications_read, notification_inbox
    from backend.notifications import create_notification_event

    repositories = _isolated_db(tmp_path, monkeypatch, "notification_inbox_scope")
    program_id, allowed, blocked = _create_editor_with_one_section(repositories)

    allowed_event = create_notification_event("workflow_reminder", [], "Allowed", "", program_id=program_id, section_key=allowed, actor="admin")
    blocked_event = create_notification_event("workflow_reminder", [], "Blocked", "", program_id=program_id, section_key=blocked, actor="admin")

    rows = notification_inbox("scoped_editor", program_id, 20)
    ids = {str(row["id"]) for row in rows}
    assert str(allowed_event["id"]) in ids
    assert str(blocked_event["id"]) not in ids

    result = mark_notifications_read("scoped_editor", program_id, [str(blocked_event["id"])])
    assert result["updated"] == 0


def test_tenant_admin_analytics_and_notifications_are_program_scoped(tmp_path, monkeypatch):
    from backend.enterprise.analytics import usage_analytics_admin
    from backend.notifications import create_notification_event, list_notification_events_admin
    from backend.tenancy import DEFAULT_TENANT_ID, save_tenant_admin

    repositories = _isolated_db(tmp_path, monkeypatch, "tenant_scope")
    tenant = save_tenant_admin("admin", {"name": "Tenant B", "code": "TB", "is_active": True})
    tenant_id = str(tenant["id"])
    repositories.upsert_user_admin(
        "admin",
        {
            "username": "tenant_admin_b",
            "password": "Tenant_Admin_2026!",
            "role": "Admin",
            "tenant_id": tenant_id,
            "tenant_scope": "tenant",
            "email": "tenant-admin@example.test",
            "is_active": True,
        },
    )
    default_program = repositories.create_program_admin(
        "admin",
        {"tenant_id": DEFAULT_TENANT_ID, "program_name": "Default Program", "report_year": "2026", "accreditation_profile": "MEDEK"},
    )
    tenant_program = repositories.create_program_admin(
        "admin",
        {"tenant_id": tenant_id, "program_name": "Tenant Program", "report_year": "2026", "accreditation_profile": "MEDEK"},
    )

    repositories.log_activity("Default secret action", "", "admin", str(default_program["id"]))
    repositories.log_activity("Tenant visible action", "", "tenant_actor", str(tenant_program["id"]))
    create_notification_event("workflow_reminder", [], "Default notification", "", program_id=str(default_program["id"]), actor="admin")
    tenant_notification = create_notification_event("workflow_reminder", [], "Tenant notification", "", program_id=str(tenant_program["id"]), actor="tenant_actor")

    analytics = usage_analytics_admin("tenant_admin_b")
    actions = {str(row["action"]) for row in analytics["recent"]}
    assert "Tenant visible action" in actions
    assert "Default secret action" not in actions

    notifications = list_notification_events_admin("tenant_admin_b")
    notification_ids = {str(row["id"]) for row in notifications}
    assert str(tenant_notification["id"]) in notification_ids
    assert all(str(row.get("program_id", "")) != str(default_program["id"]) for row in notifications)


def test_workflow_reminders_are_section_scoped(tmp_path, monkeypatch):
    from backend.enterprise.workflow import workflow_reminders_payload

    repositories = _isolated_db(tmp_path, monkeypatch, "workflow_reminder_scope")
    program_id, allowed, blocked = _create_editor_with_one_section(repositories)

    repositories.update_section("admin", program_id, allowed, {"status": "Devam Ediyor", "deadline": "2030-01-01"})
    repositories.update_section("admin", program_id, blocked, {"status": "Devam Ediyor", "deadline": "2030-01-01"})

    payload = workflow_reminders_payload("scoped_editor", program_id)
    keys = {str(row.get("section_key") or "") for row in payload["rows"]}
    assert allowed in keys
    assert blocked not in keys
    assert keys <= {allowed}


def test_advanced_reporting_trends_are_section_scoped(tmp_path, monkeypatch):
    from backend.db import transaction
    from backend.enterprise.dashboard import advanced_reporting
    from backend.enterprise.matrix import permission_matrix_admin, update_permission_matrix_admin
    import uuid

    repositories = _isolated_db(tmp_path, monkeypatch, "advanced_trend_scope")
    program_id, allowed, blocked = _create_editor_with_one_section(repositories)

    payload = permission_matrix_admin("admin")
    rows = [dict(row) for row in payload["rows"]]
    for row in rows:
        if row["permission"] == "advanced_dashboard.view":
            row[repositories.EDITOR_ROLE] = True
    update_permission_matrix_admin("admin", rows, payload["sidebar_rows"])

    with transaction() as conn:
        for key, day in [(allowed, "2030-01-01"), (blocked, "2030-01-02")]:
            conn.execute(
                """INSERT INTO section_versions(
                    id, program_id, section_key, saved_at, status, report_text, planla, uygula,
                    kontrol, onlem, notes, deadline, change_summary
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (str(uuid.uuid4()), program_id, key, f"{day} 09:00:00", "Devam Ediyor", "", "", "", "", "", "", "", "scope probe"),
            )
            conn.execute(
                "INSERT INTO activity_log(id,ts,action,detail,actor,program_id) VALUES(?,?,?,?,?,?)",
                (str(uuid.uuid4()), f"{day} 10:00:00", "scope probe", key, "admin", program_id),
            )

    scoped = advanced_reporting("scoped_editor", program_id)
    trend_dates = {str(row.get("date")): int(row.get("saved_sections") or 0) for row in scoped["trend_chart"]}
    activity_dates = {str(row.get("date")): int(row.get("activity_count") or 0) for row in scoped["activity_trend"]}
    assert trend_dates.get("2030-01-01") == 1
    assert "2030-01-02" not in trend_dates
    assert activity_dates.get("2030-01-01") == 1
    assert "2030-01-02" not in activity_dates
