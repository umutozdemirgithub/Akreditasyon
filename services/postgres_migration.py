from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


# Keep this list in sync with backend.db SCHEMA_SQL/tools/postgres_schema.sql.
# PostgreSQL rehearsal, cutover checks, and JSON exports all depend on this
# order to avoid silently dropping data from newer product modules.
MIGRATION_ORDER = [
    "tenants",
    "tenant_faculties",
    "programs",
    "users",
    "program_users",
    "sections",
    "evidence",
    "evidence_links",
    "data_tables",
    "section_approvals",
    "section_comments",
    "section_versions",
    "edit_locks",
    "activity_log",
    "notification_events",
    "notification_reads",
    "export_history",
    "export_jobs",
    "workflow_runs",
    "workflow_run_items",
    "login_attempts",
    "settings",
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
    "system_templates",
]

SQLITE_TO_POSTGRES_TYPES = {
    "INTEGER": "integer",
    "REAL": "double precision",
    "TEXT": "text",
    "BLOB": "bytea",
    "NUMERIC": "numeric",
}


def sqlite_tables(sqlite_path: Path) -> list[str]:
    """Return user table names from the SQLite source database."""
    with sqlite3.connect(sqlite_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    return [row[0] for row in rows]


def sqlite_row_counts(sqlite_path: Path) -> dict[str, int]:
    """Return row counts per table for pre/post migration comparison."""
    counts: dict[str, int] = {}
    with sqlite3.connect(sqlite_path) as conn:
        for table in sqlite_tables(sqlite_path):
            quoted = '"' + table.replace('"', '""') + '"'
            counts[table] = int(conn.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0])
    return counts


def build_postgres_readiness_report(sqlite_path: Path) -> dict[str, Any]:
    """Summarize whether the current SQLite data is ready for a PostgreSQL migration rehearsal."""
    if not sqlite_path.exists() or not sqlite_path.is_file():
        return {
            "sqlite_path": str(sqlite_path),
            "table_count": 0,
            "tables": [],
            "migration_order": [],
            "missing_core_tables": MIGRATION_ORDER.copy(),
            "extra_tables": [],
            "row_counts": {},
            "ready_for_rehearsal": False,
            "error": "SQLite source database not found. Start the app once or pass an existing SQLite path.",
        }
    tables = sqlite_tables(sqlite_path)
    counts = sqlite_row_counts(sqlite_path)
    missing_core = [name for name in MIGRATION_ORDER if name not in tables]
    unordered_extra = [name for name in tables if name not in MIGRATION_ORDER]
    return {
        "sqlite_path": str(sqlite_path),
        "table_count": len(tables),
        "tables": tables,
        "migration_order": [name for name in MIGRATION_ORDER if name in tables],
        "missing_core_tables": missing_core,
        "extra_tables": unordered_extra,
        "row_counts": counts,
        "ready_for_rehearsal": not missing_core,
    }
