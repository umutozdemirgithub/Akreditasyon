from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import ORG_STORAGE_DIR  # noqa: E402
from backend.db import get_conn, init_db, rows_to_dicts, transaction  # noqa: E402
from backend.file_security import safe_download_name  # noqa: E402
from backend.repositories import get_program  # noqa: E402
from backend.storage_paths import (  # noqa: E402
    evidence_section_dir,
    report_export_dir,
    timestamp_slug,
    write_program_manifest,
    write_table_snapshot,
)


def _is_inside(path: Path, base: Path) -> bool:
    try:
        resolved = path.resolve()
        resolved_base = base.resolve()
        return resolved == resolved_base or resolved_base in resolved.parents
    except Exception:
        return False


def _copy_if_needed(src: Path, dst: Path) -> Path | None:
    if not src.exists() or not src.is_file():
        return None
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        shutil.copy2(src, dst)
    return dst


def migrate_evidence() -> int:
    count = 0
    with get_conn() as conn:
        rows = rows_to_dicts(conn.execute("SELECT * FROM evidence WHERE COALESCE(deleted_at,'')=''" ).fetchall())
    for row in rows:
        program_id = str(row.get("program_id", "") or "")
        program = get_program(program_id) or {"id": program_id, "program_name": program_id}
        old_path = Path(str(row.get("stored_path", "") or ""))
        if not old_path or _is_inside(old_path, ORG_STORAGE_DIR):
            continue
        section_key = str(row.get("section_key", "") or "genel")
        original_name = safe_download_name(row.get("original_name") or old_path.name)
        target = evidence_section_dir(program, section_key) / f"{timestamp_slug()}_{row.get('id', '')}_{original_name}"
        copied = _copy_if_needed(old_path, target)
        if not copied:
            continue
        with transaction() as conn:
            conn.execute("UPDATE evidence SET stored_path=? WHERE id=?", (str(copied), row.get("id")))
        write_program_manifest(program, extra={"type": "legacy_evidence_migrated", "file": str(copied)})
        count += 1
    return count


def migrate_export_jobs() -> int:
    count = 0
    with get_conn() as conn:
        rows = rows_to_dicts(conn.execute("SELECT * FROM export_jobs WHERE COALESCE(file_path,'')<>''" ).fetchall())
    for row in rows:
        program_id = str(row.get("program_id", "") or "")
        program = get_program(program_id) or {"id": program_id, "program_name": program_id}
        old_path = Path(str(row.get("file_path", "") or ""))
        if not old_path or _is_inside(old_path, ORG_STORAGE_DIR):
            continue
        file_name = safe_download_name(row.get("file_name") or old_path.name)
        target = report_export_dir(program) / f"{timestamp_slug()}_legacy_{row.get('id', '')}_{file_name}"
        copied = _copy_if_needed(old_path, target)
        if not copied:
            continue
        with transaction() as conn:
            conn.execute("UPDATE export_jobs SET file_path=? WHERE id=?", (str(copied), row.get("id")))
        write_program_manifest(program, extra={"type": "legacy_export_migrated", "file": str(copied)})
        count += 1
    return count


def snapshot_tables() -> int:
    count = 0
    with get_conn() as conn:
        rows = rows_to_dicts(conn.execute("SELECT * FROM data_tables WHERE COALESCE(deleted_at,'')=''" ).fetchall())
    for row in rows:
        program_id = str(row.get("program_id", "") or "")
        program = get_program(program_id) or {"id": program_id, "program_name": program_id}
        write_table_snapshot(
            program,
            section_key=str(row.get("section_key", "") or "genel"),
            table_id=str(row.get("id", "") or ""),
            table_name=str(row.get("table_name", "") or "tablo"),
            data_json=str(row.get("data_json", "{}") or "{}"),
            actor="migration",
        )
        count += 1
    return count


def main() -> None:
    init_db()
    evidence_count = migrate_evidence()
    export_count = migrate_export_jobs()
    table_count = snapshot_tables()
    print("Kurumsal klasör migrasyonu tamamlandı.")
    print(f"Kanıt dosyası: {evidence_count}")
    print(f"Çıktı dosyası: {export_count}")
    print(f"Tablo JSON kopyası: {table_count}")
    print(f"Hedef kök: {ORG_STORAGE_DIR}")


if __name__ == "__main__":
    main()
