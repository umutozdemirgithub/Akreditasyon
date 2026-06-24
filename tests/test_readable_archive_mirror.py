from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORAGE = (ROOT / "backend" / "storage_paths.py").read_text(encoding="utf-8")
REPOS = (ROOT / "backend" / "repositories.py").read_text(encoding="utf-8")
DOC = (ROOT / "docs" / "READABLE_ARCHIVE_MIRROR.md").read_text(encoding="utf-8")
TOOL = (ROOT / "tools" / "mirror_full_archive.py").read_text(encoding="utf-8")
PS1 = (ROOT / "tools" / "mirror_full_archive.ps1").read_text(encoding="utf-8")
SH = (ROOT / "tools" / "mirror_full_archive.sh").read_text(encoding="utf-8")


def test_report_text_and_full_report_mirror_paths_exist():
    assert "04_rapor_metni" in STORAGE
    assert "def report_text_section_dir" in STORAGE
    assert "def write_section_text_archive" in STORAGE
    assert "latest.json" in STORAGE
    assert "latest.md" in STORAGE
    assert "versions" in STORAGE
    assert "def write_all_sections_archive" in STORAGE
    assert "tum_rapor_latest.json" in STORAGE


def test_approval_and_audit_mirror_paths_exist():
    assert "05_onay_gecmisi" in STORAGE
    assert "06_loglar" in STORAGE
    assert "def write_approval_snapshot" in STORAGE
    assert "approval_history.jsonl" in STORAGE
    assert "def append_activity_log_snapshot" in STORAGE
    assert "activity_log.jsonl" in STORAGE


def test_repositories_write_mirrors_on_save_approval_and_log():
    assert "write_section_text_archive(program, result" in REPOS
    assert "write_all_sections_archive(program, all_sections" in REPOS
    assert "write_approval_snapshot(" in REPOS
    assert "append_activity_log_snapshot(program, entry)" in REPOS
    assert "Otomatik taslak kaydı" in REPOS
    assert "Manuel başlık kaydı" in REPOS


def test_full_archive_sync_tool_exists_for_existing_database_records():
    assert "def mirror_program" in TOOL
    assert "write_section_text_archive" in TOOL
    assert "write_all_sections_archive" in TOOL
    assert "write_table_snapshot" in TOOL
    assert "write_approval_snapshot" in TOOL
    assert "append_activity_log_snapshot" in TOOL
    assert "evidence_index.json" in TOOL
    assert "PROJECT_ROOT" in TOOL
    assert "sys.path.insert(0, str(PROJECT_ROOT))" in TOOL
    assert "docker exec -w /app -e PYTHONPATH=/app akys-api python /app/tools/mirror_full_archive.py" in PS1
    assert "$LASTEXITCODE" in PS1
    assert "docker exec -w /app -e PYTHONPATH=/app akys-api python /app/tools/mirror_full_archive.py" in SH


def test_documentation_describes_readable_archive_contents():
    assert "Okunabilir Tam Arşiv Aynası" in DOC
    assert "04_rapor_metni" in DOC
    assert "latest.json" in DOC
    assert "latest.md" in DOC
    assert "tum_rapor_latest.json" in DOC
    assert "approval_history.jsonl" in DOC
    assert "activity_log.jsonl" in DOC
    assert "mirror_full_archive.ps1" in DOC
