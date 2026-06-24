from pathlib import Path

from core.project_paths import find_project_root
from services.postgres_migration import build_postgres_readiness_report

ROOT = find_project_root(Path(__file__))


def test_backup_cron_script_and_docs_exist():
    script = ROOT / "tools" / "backup_medek.sh"
    doc = ROOT / "docs" / "BACKUP_CRON.md"
    assert script.exists()
    assert script.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash")
    assert "tar -czf" in script.read_text(encoding="utf-8")
    assert doc.exists()
    assert "medek_data/kanitlar" in doc.read_text(encoding="utf-8")


def test_operations_docs_and_compose_log_rotation_exist():
    ops = (ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.web.yml").read_text(encoding="utf-8")
    nginx = (ROOT / "docs" / "NGINX_EXAMPLE.md").read_text(encoding="utf-8")
    assert "Yedekleme" in ops
    assert "max-size" in compose and "max-file" in compose
    assert "limit_req_zone" in nginx


def test_risk_register_and_migration_docs_exist():
    risk = (ROOT / "docs" / "RISK_REGISTER.md").read_text(encoding="utf-8")
    pg = (ROOT / "docs" / "POSTGRES_MIGRATION_PLAN.md").read_text(encoding="utf-8")
    mobile = (ROOT / "docs" / "MOBILE_UX_CHECKLIST.md").read_text(encoding="utf-8")
    assert "yerel kural tabanlıdır" in risk
    assert "PostgreSQL" in pg
    assert "Mobile UX" in mobile


def test_postgres_readiness_service_exists():
    service = ROOT / "services" / "postgres_migration.py"
    tool = ROOT / "tools" / "postgres_readiness.py"
    schema = ROOT / "tools" / "postgres_schema.sql"
    export_tool = ROOT / "tools" / "postgres_export.py"
    source = service.read_text(encoding="utf-8")
    assert service.exists()
    assert tool.exists()
    assert schema.exists()
    assert export_tool.exists()
    assert "MIGRATION_ORDER" in source
    assert "def build_postgres_readiness_report" in source
    assert "sqlite_row_counts" in source
    pg_doc = (ROOT / "docs" / "POSTGRES_MIGRATION_PLAN.md").read_text(encoding="utf-8")
    assert "tools/postgres_readiness.py" in pg_doc
    assert "tools/postgres_migrate.py" in pg_doc
    schema_text = schema.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS sections" in schema_text
    assert "CREATE TABLE IF NOT EXISTS export_jobs" in schema_text
    assert "export_sqlite_for_postgres" in export_tool.read_text(encoding="utf-8")


def test_postgres_readiness_missing_sqlite_is_controlled(tmp_path):
    report = build_postgres_readiness_report(tmp_path / "missing.sqlite3")
    assert report["ready_for_rehearsal"] is False
    assert report["table_count"] == 0
    assert report["row_counts"] == {}
    assert "not found" in report["error"].lower()


def test_https_and_windows_backup_artifacts_exist():
    assert (ROOT / "docker-compose.https.yml").exists()
    assert (ROOT / "Caddyfile").exists()
    assert (ROOT / "docs" / "HTTPS_AND_INTRANET.md").exists()
    assert (ROOT / "docs" / "AUTOMATED_BACKUP_WINDOWS.md").exists()
    assert (ROOT / "tools" / "install_backup_task.ps1").exists()
    assert (ROOT / "tools" / "restore_latest_backup.ps1").exists()
