from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = (ROOT / "backend" / "personal_backup.py").read_text(encoding="utf-8")
MAIN = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
FRONTEND_API = (ROOT / "frontend" / "src" / "api.js").read_text(encoding="utf-8")
VIEWS = (ROOT / "frontend" / "src" / "views" / "AppViews.jsx").read_text(encoding="utf-8")
DOC = (ROOT / "docs" / "PERSONAL_ROLE_SCOPED_BACKUP.md").read_text(encoding="utf-8")


def test_personal_backup_module_builds_role_scoped_zip():
    assert "build_program_personal_backup_zip" in API
    assert "build_all_personal_backup_zip" in API
    assert "list_sections(username, program_id)" in API
    assert "list_evidence(username, program_id)" in API
    assert "list_tables(username, program_id)" in API
    assert "section_versions" in API
    assert "activity_log.jsonl" in API
    assert "evidence_files_copied" in API
    assert "safe_stored_path" in API
    assert "Kullanici_Yedegi" in API


def test_personal_backup_endpoints_are_available():
    assert '@app.get("/api/me/backup/personal.zip")' in MAIN
    assert '@app.get("/api/programs/{program_id}/backup/personal.zip")' in MAIN
    assert "build_all_personal_backup_zip" in MAIN
    assert "build_program_personal_backup_zip" in MAIN
    assert "application/zip" in API


def test_frontend_exposes_personal_backup_download_buttons():
    assert "personalProgramBackupZip" in FRONTEND_API
    assert "personalAllBackupZip" in FRONTEND_API
    assert "Bu Programdaki Yetki Alanımı ZIP İndir" in VIEWS
    assert "Tüm Yetki Alanımı ZIP İndir" in VIEWS
    assert "Kişisel Yedek İndir" in VIEWS


def test_documentation_describes_personal_backup_scope():
    assert "Rol Bazlı Kişisel ZIP Yedek" in DOC
    assert "/api/me/backup/personal.zip" in DOC
    assert "Editör atanmış başlıkları" in DOC
    assert "01_rapor_metni" in DOC
    assert "02_kanitlar" in DOC
