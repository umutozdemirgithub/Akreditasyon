from __future__ import annotations

"""Synchronize PostgreSQL/SQLite accreditation records into readable files.

This command does not replace the database. It creates/refreshes JSON, Markdown,
and JSONL mirrors under medek_data/kurumlar/... so that the Desktop/Akreditasyon
folder can be inspected independently during audit preparation.
"""

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.db import get_conn, rows_to_dicts
from backend.storage_paths import (
    append_activity_log_snapshot,
    write_all_sections_archive,
    write_approval_snapshot,
    write_program_manifest,
    write_section_text_archive,
    write_table_snapshot,
)


def _rows(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with get_conn() as conn:
        return rows_to_dicts(conn.execute(sql, params).fetchall())


def mirror_program(program: dict[str, Any]) -> dict[str, int]:
    program_id = str(program.get("id", "") or "")
    if not program_id:
        return {"sections": 0, "tables": 0, "approvals": 0, "logs": 0}

    write_program_manifest(program, extra={"type": "full_archive_sync", "program_id": program_id})

    sections = _rows(
        "SELECT * FROM sections WHERE program_id=? AND COALESCE(deleted_at,'')='' ORDER BY sort_order, section_key",
        (program_id,),
    )
    for section in sections:
        write_section_text_archive(program, section, actor="system", action="Tam arşiv senkronizasyonu", create_version=False)
    if sections:
        write_all_sections_archive(program, sections, actor="system", action="Tam arşiv senkronizasyonu")

    tables = _rows(
        "SELECT * FROM data_tables WHERE program_id=? AND COALESCE(deleted_at,'')='' ORDER BY section_key, table_name",
        (program_id,),
    )
    for table in tables:
        write_table_snapshot(
            program,
            section_key=str(table.get("section_key", "") or "genel"),
            table_id=str(table.get("id", "") or ""),
            table_name=str(table.get("table_name", "") or "Tablo"),
            data_json=str(table.get("data_json", "{}") or "{}"),
            actor="system",
        )

    approvals = _rows(
        "SELECT * FROM section_approvals WHERE program_id=? ORDER BY created_at",
        (program_id,),
    )
    for approval in approvals:
        write_approval_snapshot(program, approval, actor="system", action="Tam arşiv senkronizasyonu")

    logs = _rows(
        "SELECT * FROM activity_log WHERE program_id=? ORDER BY ts",
        (program_id,),
    )
    for entry in logs:
        append_activity_log_snapshot(program, entry)

    # Evidence files are already stored physically. This index makes the folder
    # self-describing without duplicating large binary files.
    evidence = _rows(
        "SELECT * FROM evidence WHERE program_id=? AND COALESCE(deleted_at,'')='' ORDER BY uploaded_at",
        (program_id,),
    )
    evidence_index = {
        "program_id": program_id,
        "evidence_count": len(evidence),
        "evidence": evidence,
    }
    root_manifest = write_program_manifest(
        program,
        extra={
            "type": "full_archive_sync_complete",
            "section_count": len(sections),
            "table_count": len(tables),
            "approval_count": len(approvals),
            "activity_log_count": len(logs),
            "evidence_count": len(evidence),
        },
    )
    evidence_index_path = root_manifest.parent / "01_kanitlar" / "evidence_index.json"
    evidence_index_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_index_path.write_text(json.dumps(evidence_index, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "sections": len(sections),
        "tables": len(tables),
        "approvals": len(approvals),
        "logs": len(logs),
        "evidence": len(evidence),
    }


def main() -> int:
    programs = _rows("SELECT * FROM programs WHERE COALESCE(deleted_at,'')='' ORDER BY university_name, school_name, department_name, program_name")
    totals = {"programs": len(programs), "sections": 0, "tables": 0, "approvals": 0, "logs": 0, "evidence": 0}
    for program in programs:
        result = mirror_program(program)
        for key in ("sections", "tables", "approvals", "logs", "evidence"):
            totals[key] += int(result.get(key, 0) or 0)
    print(json.dumps(totals, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
