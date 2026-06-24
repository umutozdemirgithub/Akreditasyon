#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.postgres_migration import MIGRATION_ORDER, sqlite_row_counts  # noqa: E402
from backend.db_postgres import split_sql_script  # noqa: E402

try:
    import psycopg
    from psycopg import sql
except Exception as exc:  # pragma: no cover - depends on optional tool dependency
    psycopg = None
    sql = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

DEFAULT_SQLITE = ROOT / "medek_data" / "medek_kys_v7_9.sqlite3"
DEFAULT_SCHEMA = ROOT / "tools" / "postgres_schema.sql"

# Keep table migration order centralized so production cutover, JSON export,
# and readiness checks all agree on tenant-aware dependencies.
TABLE_ORDER = MIGRATION_ORDER


def sqlite_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [str(row[1]) for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()]


def postgres_columns(pg_conn: Any, table: str) -> list[str]:
    rows = pg_conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    ).fetchall()
    return [str(row[0]) for row in rows]


def table_exists_sqlite(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return row is not None


def load_schema(pg_conn: Any, schema_path: Path) -> None:
    for statement in split_sql_script(schema_path.read_text(encoding="utf-8")):
        pg_conn.execute(statement)
    pg_conn.commit()


def clear_postgres_tables(pg_conn: Any, tables: list[str]) -> None:
    if not tables:
        return
    identifiers = [sql.Identifier(table) for table in reversed(tables)]
    pg_conn.execute(sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(sql.SQL(", ").join(identifiers)))
    pg_conn.commit()


def copy_table(sqlite_conn: sqlite3.Connection, pg_conn: Any, table: str, *, batch_size: int = 500) -> int:
    if not table_exists_sqlite(sqlite_conn, table):
        return 0
    source_cols = sqlite_columns(sqlite_conn, table)
    target_cols = postgres_columns(pg_conn, table)
    columns = [col for col in source_cols if col in target_cols]
    if not columns:
        return 0
    select_cols = ", ".join(f'"{col}"' for col in columns)
    rows = sqlite_conn.execute(f'SELECT {select_cols} FROM "{table}"').fetchall()
    if not rows:
        return 0
    insert_stmt = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ON CONFLICT DO NOTHING").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    total = 0
    with pg_conn.cursor() as cur:
        for start in range(0, len(rows), batch_size):
            batch = [tuple(row[col] for col in columns) for row in rows[start : start + batch_size]]
            cur.executemany(insert_stmt, batch)
            total += len(batch)
    pg_conn.commit()
    return total


def migrate(sqlite_path: Path, postgres_dsn: str, schema_path: Path, *, clear: bool) -> dict[str, int]:
    if psycopg is None:
        raise RuntimeError(f"psycopg is required for PostgreSQL migration: {IMPORT_ERROR}")
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")
    with sqlite3.connect(sqlite_path) as sqlite_conn, psycopg.connect(postgres_dsn) as pg_conn:
        sqlite_conn.row_factory = sqlite3.Row
        load_schema(pg_conn, schema_path)
        existing_tables = [table for table in TABLE_ORDER if table_exists_sqlite(sqlite_conn, table)]
        if clear:
            clear_postgres_tables(pg_conn, existing_tables)
        result: dict[str, int] = {}
        for table in existing_tables:
            result[table] = copy_table(sqlite_conn, pg_conn, table)
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate AKYS SQLite data to PostgreSQL for rehearsal/production cutover.")
    parser.add_argument("--sqlite", default=os.getenv("MEDEK_SQLITE_PATH", str(DEFAULT_SQLITE)))
    parser.add_argument("--dsn", default=os.getenv("MEDEK_DATABASE_URL") or os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL"), help="PostgreSQL DSN, e.g. postgresql://medek:secret@localhost:5432/medek")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    parser.add_argument("--clear", action="store_true", help="TRUNCATE target tables before copying data.")
    args = parser.parse_args()
    if not args.dsn:
        parser.error("--dsn or POSTGRES_DSN/DATABASE_URL is required")
    before = sqlite_row_counts(Path(args.sqlite))
    copied = migrate(Path(args.sqlite), args.dsn, Path(args.schema), clear=args.clear)
    print("SQLite source row counts:")
    for table, count in before.items():
        print(f"  {table}: {count}")
    print("Copied rows:")
    for table, count in copied.items():
        print(f"  {table}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
