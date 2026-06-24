#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.postgres_migration import MIGRATION_ORDER, sqlite_row_counts  # noqa: E402

try:
    import psycopg
except Exception as exc:  # pragma: no cover
    psycopg = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

REQUIRED_INDEXES = [
    "idx_programs_tenant_active",
    "idx_programs_tenant_faculty",
    "idx_users_tenant_role",
    "idx_program_users_tenant_program",
    "idx_sections_program_status",
    "idx_activity_tenant_program_ts",
    "idx_notifications_tenant_status",
    "idx_export_jobs_tenant_program_status",
    "idx_source_watchers_type_active",
    "idx_update_candidates_status_tenant",
    "idx_clause_library_scope",
    "idx_content_blocks_section",
    "idx_quality_snapshots_program",
    "idx_auditor_links_program",
]


def pg_table_counts(conn) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in MIGRATION_ORDER:
        exists = conn.execute("SELECT to_regclass(%s) IS NOT NULL AS ok", (f"public.{table}",)).fetchone()[0]
        if exists:
            counts[table] = int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
    return counts


def pg_indexes(conn) -> set[str]:
    rows = conn.execute("SELECT indexname FROM pg_indexes WHERE schemaname='public'").fetchall()
    return {str(row[0]) for row in rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate MEDEK PostgreSQL production cutover readiness.")
    parser.add_argument("--dsn", default=os.getenv("MEDEK_DATABASE_URL") or os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL"))
    parser.add_argument("--sqlite", default=os.getenv("MEDEK_SQLITE_PATH", str(ROOT / "medek_data" / "medek_kys_v7_9.sqlite3")))
    parser.add_argument("--strict-counts", action="store_true", help="Fail when PostgreSQL row counts differ from SQLite source row counts.")
    args = parser.parse_args()
    if not args.dsn:
        parser.error("--dsn or MEDEK_DATABASE_URL/POSTGRES_DSN/DATABASE_URL is required")
    if psycopg is None:
        raise RuntimeError(f"psycopg is required: {IMPORT_ERROR}")

    with psycopg.connect(args.dsn) as conn:
        pg_counts = pg_table_counts(conn)
        indexes = pg_indexes(conn)
    sqlite_path = Path(args.sqlite)
    sqlite_counts = sqlite_row_counts(sqlite_path) if sqlite_path.exists() else {}
    missing_tables = [table for table in MIGRATION_ORDER if table not in pg_counts]
    missing_indexes = [idx for idx in REQUIRED_INDEXES if idx not in indexes]
    count_mismatches = {
        table: {"sqlite": sqlite_counts.get(table, 0), "postgres": pg_counts.get(table, 0)}
        for table in MIGRATION_ORDER
        if table in sqlite_counts and sqlite_counts.get(table, 0) != pg_counts.get(table, 0)
    }
    report = {
        "ok": not missing_tables and not missing_indexes and (not args.strict_counts or not count_mismatches),
        "missing_tables": missing_tables,
        "missing_indexes": missing_indexes,
        "count_mismatches": count_mismatches,
        "postgres_counts": pg_counts,
        "sqlite_counts": sqlite_counts,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
