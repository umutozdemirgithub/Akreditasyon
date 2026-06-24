from __future__ import annotations

import json
import uuid

import pytest


def _isolated_db(tmp_path, monkeypatch):
    from backend import config, db, file_security, repositories

    data_dir = tmp_path / "update_center_scope"
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


def _candidate(conn, *, tenant_id: str, source_type: str, candidate_kind: str, title: str, payload: dict) -> str:
    from backend.db import now_iso

    candidate_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO update_candidates(
            id, tenant_id, source_type, candidate_kind, profile, title, summary,
            old_version, new_version, old_hash, new_hash, source_url,
            payload_json, diff_json, status, created_at, updated_at, applied_by, applied_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            candidate_id,
            tenant_id,
            source_type,
            candidate_kind,
            "MEDEK",
            title,
            "scope test",
            "",
            "1",
            "",
            str(uuid.uuid4()),
            "test",
            json.dumps(payload, ensure_ascii=False),
            "[]",
            "pending",
            now_iso(),
            now_iso(),
            "",
            "",
        ),
    )
    return candidate_id


def test_update_center_candidate_mutations_are_tenant_scoped(tmp_path, monkeypatch):
    from backend.db import transaction
    from backend.tenancy import save_tenant_admin
    from backend.update_center import apply_update_candidate, ignore_update_candidate, list_update_center_payload

    repositories = _isolated_db(tmp_path, monkeypatch)
    tenant_b = save_tenant_admin("admin", {"name": "Tenant B", "code": "TB", "is_active": True})
    tenant_c = save_tenant_admin("admin", {"name": "Tenant C", "code": "TC", "is_active": True})
    tenant_b_id = str(tenant_b["id"])
    tenant_c_id = str(tenant_c["id"])
    repositories.upsert_user_admin(
        "admin",
        {
            "username": "tenant_admin_b",
            "password": "Tenant_Admin_2026!",
            "role": "Admin",
            "tenant_id": tenant_b_id,
            "tenant_scope": "tenant",
            "email": "tenant-admin-b@example.test",
            "is_active": True,
        },
    )

    with transaction() as conn:
        own_id = _candidate(
            conn,
            tenant_id=tenant_b_id,
            source_type="academic",
            candidate_kind="academic_faculty_add",
            title="Own faculty",
            payload={"tenant_id": tenant_b_id, "faculty_name": "Own Faculty", "accreditation_profile": "MEDEK"},
        )
        other_id = _candidate(
            conn,
            tenant_id=tenant_c_id,
            source_type="academic",
            candidate_kind="academic_faculty_add",
            title="Other faculty",
            payload={"tenant_id": tenant_c_id, "faculty_name": "Other Faculty", "accreditation_profile": "MEDEK"},
        )
        global_id = _candidate(
            conn,
            tenant_id="global",
            source_type="template",
            candidate_kind="template_add",
            title="Global template",
            payload={"template_key": "SCOPE", "template": {"template_key": "SCOPE", "template_name": "Scope", "version": "1", "sections": []}},
        )

    payload = list_update_center_payload("tenant_admin_b")
    by_id = {str(row["id"]): row for row in payload["candidates"]}
    assert own_id in by_id
    assert other_id not in by_id
    assert global_id in by_id
    assert by_id[own_id]["can_apply"] is True
    assert by_id[global_id]["can_apply"] is False

    with pytest.raises(PermissionError):
        apply_update_candidate("tenant_admin_b", other_id)
    with pytest.raises(PermissionError):
        ignore_update_candidate("tenant_admin_b", other_id)
    with pytest.raises(PermissionError):
        apply_update_candidate("tenant_admin_b", global_id)

    assert apply_update_candidate("tenant_admin_b", own_id)["ok"] is True
