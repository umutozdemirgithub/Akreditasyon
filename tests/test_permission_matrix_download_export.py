from __future__ import annotations


def _isolated_db(tmp_path, monkeypatch, name: str):
    from backend import config, db, file_security, repositories

    data_dir = tmp_path / name
    sqlite_path = data_dir / "matrix_download.sqlite3"
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


def test_permission_matrix_download_payload_contains_current_matrices(tmp_path, monkeypatch):
    _isolated_db(tmp_path, monkeypatch, "permission_matrix_download_payload")
    from backend.main import _permission_matrix_csv, _permission_matrix_download_payload

    payload = _permission_matrix_download_payload("admin")

    assert payload["export_type"] == "AKYS Yetki Matrisi"
    assert "Süper Admin" in payload["role_scope"]
    assert payload["matrices"]["operation_permissions"]
    assert payload["matrices"]["sidebar_visibility"]
    assert "section_policies" in payload["matrices"]

    csv_text = _permission_matrix_csv(payload)
    assert "İşlem Yetki Matrisi" in csv_text
    assert "Sidebar Görünürlük Matrisi" in csv_text
    assert "Süper Admin" in csv_text


def test_frontend_permission_matrix_download_buttons_are_present():
    from pathlib import Path

    source = Path("frontend/src/views/AppViews.jsx").read_text(encoding="utf-8")
    assert "Son Matrisi CSV İndir" in source
    assert "Son Matrisi JSON İndir" in source
    assert "downloadPermissionMatrix" in source
