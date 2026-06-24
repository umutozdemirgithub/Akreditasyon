from pathlib import Path

from backend.db import INDEX_SQL, SCHEMA_SQL
from backend.db_postgres import split_sql_script, translate_sqlite_to_postgres
from services.postgres_migration import MIGRATION_ORDER

ROOT = Path(__file__).resolve().parents[1]

PRODUCT_MODULE_TABLES = [
    "source_watchers",
    "update_candidates",
    "source_check_logs",
    "section_template_bank",
    "clause_library",
    "content_blocks",
    "content_block_versions",
    "consistency_check_runs",
    "report_quality_snapshots",
    "section_collaboration_sessions",
    "auditor_share_links",
]


def test_postgres_sqlite_compat_translation_handles_qmark_and_literals():
    sql = "SELECT * FROM sections WHERE program_id=? AND note='neden ? burada' AND section_key=?"
    translated = translate_sqlite_to_postgres(sql)
    assert "program_id=%s" in translated
    assert "section_key=%s" in translated
    assert "neden ? burada" in translated


def test_postgres_sqlite_compat_escapes_literal_percent_for_psycopg():
    sql = "SELECT key,value FROM settings WHERE key NOT LIKE 'program_setting:%' AND value LIKE ?"
    translated = translate_sqlite_to_postgres(sql)
    assert "program_setting:%%" in translated
    assert "value LIKE %s" in translated


def test_postgres_sqlite_compat_rewrites_insert_or_replace():
    sql = "INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)"
    translated = translate_sqlite_to_postgres(sql)
    assert translated.startswith("INSERT INTO settings")
    assert "ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value" in translated
    assert translated.count("%s") == 2


def test_postgres_sqlite_compat_rewrites_insert_or_ignore():
    sql = "INSERT OR IGNORE INTO evidence_links(program_id,evidence_id,section_key) VALUES(?,?,?)"
    translated = translate_sqlite_to_postgres(sql)
    assert translated.startswith("INSERT INTO evidence_links")
    assert translated.endswith("ON CONFLICT DO NOTHING")
    assert translated.count("%s") == 3


def test_runtime_schema_contains_tenant_aware_tables_and_indexes():
    schema = SCHEMA_SQL + "\n" + INDEX_SQL
    for table in ["tenants", "tenant_faculties", "workflow_runs", "workflow_run_items", "notification_reads"]:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in schema
    for idx in ["idx_programs_tenant_active", "idx_users_tenant_role", "idx_export_jobs_tenant_program_status"]:
        assert idx in schema


def test_postgres_schema_file_matches_runtime_cutover_tables():
    schema_file = (ROOT / "tools" / "postgres_schema.sql").read_text(encoding="utf-8")
    for table in MIGRATION_ORDER:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in schema_file
    assert "idx_programs_tenant_active" in schema_file
    assert "idx_notifications_tenant_status" in schema_file


def test_postgres_cutover_and_program_backup_cover_product_module_tables():
    from backend.repositories import PROGRAM_BACKUP_TABLES

    for table in PRODUCT_MODULE_TABLES:
        assert table in MIGRATION_ORDER
    for table in [
        "clause_library",
        "content_blocks",
        "content_block_versions",
        "consistency_check_runs",
        "report_quality_snapshots",
        "section_collaboration_sessions",
        "auditor_share_links",
        "notification_events",
        "notification_reads",
        "workflow_runs",
        "workflow_run_items",
    ]:
        assert table in PROGRAM_BACKUP_TABLES


def test_schema_splitter_handles_multiple_statements():
    statements = split_sql_script("CREATE TABLE a(x text); CREATE INDEX b ON a(x);")
    assert statements == ["CREATE TABLE a(x text)", "CREATE INDEX b ON a(x)"]
