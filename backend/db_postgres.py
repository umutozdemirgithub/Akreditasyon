from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Sequence

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception as exc:  # pragma: no cover - only needed when PostgreSQL runtime is enabled
    psycopg = None
    dict_row = None
    PSYCOPG_IMPORT_ERROR = exc
else:
    PSYCOPG_IMPORT_ERROR = None


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PK_BY_TABLE = {
    "settings": "key",
    "system_templates": "template_key",
    "tenants": "id",
    "tenant_faculties": "id",
    "activity_log": "id",
    "data_tables": "id",
    "evidence": "id",
    "export_history": "id",
    "export_jobs": "id",
    "login_attempts": "id",
    "notification_events": "id",
    "program_users": "id",
    "programs": "id",
    "section_approvals": "id",
    "section_comments": "id",
    "section_versions": "id",
    "sections": "id",
    "users": "username",
    "workflow_runs": "id",
    "workflow_run_items": "id",
    "source_watchers": "id",
    "update_candidates": "id",
    "source_check_logs": "id",
    "section_template_bank": "id",
    "clause_library": "id",
    "content_blocks": "id",
    "content_block_versions": "id",
    "consistency_check_runs": "id",
    "report_quality_snapshots": "id",
    "section_collaboration_sessions": "id",
    "auditor_share_links": "id",
}


@dataclass
class _CompatResult:
    rows: list[dict[str, Any]]

    def fetchone(self) -> dict[str, Any] | None:
        return self.rows[0] if self.rows else None

    def fetchall(self) -> list[dict[str, Any]]:
        return self.rows


class PostgresCompatConnection:
    """Small compatibility layer for the existing SQLite-style repository code.

    The MEDEK repositories intentionally use plain SQL and qmark placeholders.
    This wrapper keeps that style working during the PostgreSQL cutover by:
    - translating qmark placeholders to psycopg placeholders,
    - mapping SQLite UPSERT shorthands to PostgreSQL ON CONFLICT clauses,
    - emulating PRAGMA table_info for additive migration checks,
    - returning dict rows compatible with sqlite3.Row usage in the codebase.
    """

    dialect = "postgresql"

    def __init__(self, dsn: str) -> None:
        if psycopg is None or dict_row is None:
            raise RuntimeError(f"psycopg is required for MEDEK_DB_BACKEND=postgresql: {PSYCOPG_IMPORT_ERROR}")
        self._conn = psycopg.connect(dsn, row_factory=dict_row)

    def __enter__(self) -> "PostgresCompatConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()

    def close(self) -> None:
        self._conn.close()

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> Any:
        stripped = sql.strip()
        pragma = _parse_pragma_table_info(stripped)
        if pragma:
            return self._table_info(pragma)
        translated = translate_sqlite_to_postgres(stripped)
        cur = self._conn.execute(translated, tuple(params or ()))
        return cur

    def executemany(self, sql: str, params_seq: Iterable[Sequence[Any]]) -> Any:
        translated = translate_sqlite_to_postgres(sql.strip())
        with self._conn.cursor() as cur:
            cur.executemany(translated, [tuple(params) for params in params_seq])
            return cur

    def executescript(self, script: str) -> None:
        for statement in split_sql_script(script):
            self.execute(statement)

    def _table_info(self, table: str) -> _CompatResult:
        if not _IDENTIFIER_RE.match(table):
            raise ValueError(f"Invalid table name: {table!r}")
        rows = self._conn.execute(
            """
            SELECT column_name AS name
            FROM information_schema.columns
            WHERE table_schema = current_schema() AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        ).fetchall()
        return _CompatResult([dict(row) for row in rows])


def connect_postgres(dsn: str) -> PostgresCompatConnection:
    return PostgresCompatConnection(dsn)


def split_sql_script(script: str) -> list[str]:
    statements: list[str] = []
    buf: list[str] = []
    in_single = False
    in_double = False
    escape = False
    for char in script:
        if char == "\\" and not escape:
            escape = True
            buf.append(char)
            continue
        if char == "'" and not in_double and not escape:
            in_single = not in_single
        elif char == '"' and not in_single and not escape:
            in_double = not in_double
        if char == ";" and not in_single and not in_double:
            statement = "".join(buf).strip()
            if statement:
                statements.append(statement)
            buf = []
        else:
            buf.append(char)
        escape = False
    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def translate_sqlite_to_postgres(sql: str) -> str:
    sql = _rewrite_insert_or_replace(sql)
    sql = _rewrite_insert_or_ignore(sql)
    return _escape_psycopg_percent_literals(_translate_qmark_params(sql))


def _translate_qmark_params(sql: str) -> str:
    out: list[str] = []
    in_single = False
    in_double = False
    i = 0
    while i < len(sql):
        char = sql[i]
        if char == "'" and not in_double:
            out.append(char)
            # SQL escapes single quote as ''. Keep literal mode if escaped.
            if i + 1 < len(sql) and sql[i + 1] == "'":
                out.append(sql[i + 1])
                i += 2
                continue
            in_single = not in_single
            i += 1
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            out.append(char)
            i += 1
            continue
        if char == "?" and not in_single and not in_double:
            out.append("%s")
        else:
            out.append(char)
        i += 1
    return "".join(out)


def _escape_psycopg_percent_literals(sql: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(sql):
        char = sql[i]
        if char != "%":
            out.append(char)
            i += 1
            continue
        next_char = sql[i + 1] if i + 1 < len(sql) else ""
        if next_char in {"s", "b", "t"}:
            out.append(char)
        elif next_char == "%":
            out.append("%%")
            i += 1
        else:
            out.append("%%")
        i += 1
    return "".join(out)


def _rewrite_insert_or_ignore(sql: str) -> str:
    match = re.match(r"(?is)^INSERT\s+OR\s+IGNORE\s+INTO\s+(.+)$", sql)
    if not match:
        return sql
    return f"INSERT INTO {match.group(1).strip()} ON CONFLICT DO NOTHING"


def _rewrite_insert_or_replace(sql: str) -> str:
    match = re.match(
        r"(?is)^INSERT\s+OR\s+REPLACE\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*VALUES\s*\((.*)\)$",
        sql,
    )
    if not match:
        return sql
    table = match.group(1)
    columns = [col.strip().strip('"') for col in match.group(2).split(",")]
    values = match.group(3).strip()
    conflict_col = _PK_BY_TABLE.get(table)
    if not conflict_col or conflict_col not in columns:
        return f"INSERT INTO {table}({','.join(columns)}) VALUES({values}) ON CONFLICT DO NOTHING"
    update_cols = [col for col in columns if col != conflict_col]
    if update_cols:
        set_sql = ", ".join(f"{col}=EXCLUDED.{col}" for col in update_cols)
        conflict_sql = f"ON CONFLICT({conflict_col}) DO UPDATE SET {set_sql}"
    else:
        conflict_sql = f"ON CONFLICT({conflict_col}) DO NOTHING"
    return f"INSERT INTO {table}({','.join(columns)}) VALUES({values}) {conflict_sql}"


def _parse_pragma_table_info(sql: str) -> str | None:
    match = re.match(r"(?is)^PRAGMA\s+table_info\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*$", sql)
    return match.group(1) if match else None
