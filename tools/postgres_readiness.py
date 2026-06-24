from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.project_paths import find_project_root
from services.postgres_migration import build_postgres_readiness_report


def main() -> int:
    root = find_project_root()
    sqlite_path = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "medek_data" / "medek_kys_v7_9.sqlite3"
    report = build_postgres_readiness_report(sqlite_path)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready_for_rehearsal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

