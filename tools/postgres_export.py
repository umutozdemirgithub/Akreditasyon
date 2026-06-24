from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.project_paths import find_project_root
from services.postgres_migration import MIGRATION_ORDER, sqlite_tables


def export_sqlite_for_postgres(sqlite_path: Path, out_path: Path) -> dict[str, int]:
    tables = sqlite_tables(sqlite_path)
    ordered_tables = [name for name in MIGRATION_ORDER if name in tables] + [name for name in tables if name not in MIGRATION_ORDER]
    payload: dict[str, list[dict[str, object]]] = {}
    counts: dict[str, int] = {}
    with sqlite3.connect(sqlite_path) as conn:
        conn.row_factory = sqlite3.Row
        for table in ordered_tables:
            quoted = '"' + table.replace('"', '""') + '"'
            rows = [dict(row) for row in conn.execute(f"SELECT * FROM {quoted}").fetchall()]
            payload[table] = rows
            counts[table] = len(rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"tables": payload, "row_counts": counts}, ensure_ascii=False, indent=2), encoding="utf-8")
    return counts


def main() -> int:
    root = find_project_root()
    sqlite_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "medek_data" / "medek_kys_v7_9.sqlite3"
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "medek_data" / "postgres_migration_export.json"
    counts = export_sqlite_for_postgres(sqlite_path, out_path)
    print(json.dumps({"output": str(out_path), "row_counts": counts}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

