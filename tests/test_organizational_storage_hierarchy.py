from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "backend" / "config.py").read_text(encoding="utf-8")
STORAGE = (ROOT / "backend" / "storage_paths.py").read_text(encoding="utf-8")
REPOS = (ROOT / "backend" / "repositories.py").read_text(encoding="utf-8")
EXPORT_JOBS = (ROOT / "backend" / "export_jobs.py").read_text(encoding="utf-8")
MAIN = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
SECURITY = (ROOT / "backend" / "file_security.py").read_text(encoding="utf-8")
DOC = (ROOT / "docs" / "ORGANIZATIONAL_STORAGE_HIERARCHY.md").read_text(encoding="utf-8")


def test_org_storage_config_and_path_builder_exist():
    assert "ORG_STORAGE_DIR" in CONFIG
    assert "DATA_DIR / \"kurumlar\"" in CONFIG
    assert "def program_storage_dir" in STORAGE
    assert "kurum_" in STORAGE
    assert "birim_" in STORAGE
    assert "fakulte_" in STORAGE
    assert "bolum_" in STORAGE
    assert "program_" in STORAGE
    assert "manifest.json" in STORAGE


def test_evidence_and_table_snapshots_use_hierarchy():
    assert "evidence_section_dir(program, keys[0])" in REPOS
    assert "write_program_manifest(program" in REPOS
    assert "write_table_snapshot(" in REPOS
    assert "timestamp_slug()" in REPOS


def test_export_outputs_are_written_to_organizational_storage():
    assert "write_export_copy" in EXPORT_JOBS
    assert "target_path = write_export_copy" in EXPORT_JOBS
    assert "write_export_copy(get_program(program_id)" in MAIN
    assert "03_rapor_ciktilari" in STORAGE


def test_file_security_allows_new_and_legacy_storage_paths():
    assert "ORG_STORAGE_DIR.resolve()" in SECURITY
    assert "EVIDENCE_DIR.resolve()" in SECURITY
    assert "DATA_DIR.resolve()" in SECURITY


def test_documentation_describes_expected_tree():
    assert "kurumlar" in DOC
    assert "01_kanitlar" in DOC
    assert "02_tablolar" in DOC
    assert "03_rapor_ciktilari" in DOC
    assert "manifest.json" in DOC



def test_migration_scripts_can_copy_legacy_files_into_hierarchy():
    py = (ROOT / "tools" / "migrate_to_org_storage.py").read_text(encoding="utf-8")
    ps1 = (ROOT / "tools" / "migrate_to_org_storage.ps1").read_text(encoding="utf-8")
    sh = (ROOT / "tools" / "migrate_to_org_storage.sh").read_text(encoding="utf-8")
    assert "migrate_evidence" in py
    assert "migrate_export_jobs" in py
    assert "snapshot_tables" in py
    assert "UPDATE evidence SET stored_path" in py
    assert "UPDATE export_jobs SET file_path" in py
    assert "docker exec -it akys-api" in ps1
    assert "docker exec -it akys-api" in sh
