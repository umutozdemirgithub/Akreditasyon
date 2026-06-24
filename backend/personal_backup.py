from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

from .db import get_conn, now_iso, rows_to_dicts
from .file_security import safe_download_name, safe_stored_path, slugify
from .repositories import (
    APPROVER_ROLE,
    EDITOR_ROLE,
    FACULTY_ADMIN_ROLE,
    READONLY_ROLE,
    SUPER_ADMIN_ROLE,
    TENANT_ADMIN_ROLE,
    UNIT_COORDINATOR_ROLE,
    get_program,
    get_program_role,
    list_evidence,
    list_programs_for_user,
    list_sections,
    list_tables,
)
from .storage_paths import section_folder_name

ZIP_MEDIA_TYPE = "application/zip"
PRIVILEGED_SCOPE_ROLES = {
    SUPER_ADMIN_ROLE,
    TENANT_ADMIN_ROLE,
    FACULTY_ADMIN_ROLE,
    UNIT_COORDINATOR_ROLE,
    APPROVER_ROLE,
    READONLY_ROLE,
}


def archive_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def personal_backup_filename(username: str, program_id: str = "") -> str:
    stamp = archive_timestamp()
    owner = slugify(username or "kullanici")
    scope = f"_{slugify(program_id)}" if program_id else "_tum-yetki-alanim"
    return safe_download_name(f"Akreditasyon_Kisisel_Yedek_{owner}{scope}_{stamp}.zip")


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def _jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return ("\n".join(json.dumps(row, ensure_ascii=False, default=str) for row in rows) + "\n").encode("utf-8")


def _zip_json(zf: zipfile.ZipFile, arcname: str, payload: Any) -> None:
    zf.writestr(arcname, _json_bytes(payload))


def _safe_part(value: Any, fallback: str = "kayit") -> str:
    return slugify(value or fallback)[:96] or fallback


def _program_folder(program: dict[str, Any]) -> str:
    kurum = _safe_part(program.get("university_name") or program.get("tenant_name") or program.get("tenant_id"), "kurum")
    birim = _safe_part(program.get("school_name") or program.get("faculty_name"), "birim")
    bolum = _safe_part(program.get("department_name"), "bolum-yok")
    program_name = _safe_part(program.get("program_name") or program.get("id"), "program")
    yil = _safe_part(program.get("report_year"), "yil-yok")
    program_id = _safe_part(program.get("id"), "program-id")
    return f"Akreditasyon/Kullanici_Yedegi/kurum_{kurum}/birim_{birim}/bolum_{bolum}/program_{program_name}/yil_{yil}/id_{program_id}"


def _text_markdown(program: dict[str, Any], section: dict[str, Any]) -> str:
    title = f"{section.get('section_key', '')} - {section.get('section_title', '')}".strip(" -") or "Başlık"
    lines = [
        f"# {title}",
        "",
        f"- Kurum: {program.get('university_name', '')}",
        f"- Birim: {program.get('school_name', '') or program.get('faculty_name', '')}",
        f"- Bölüm: {program.get('department_name', '')}",
        f"- Program: {program.get('program_name', '')}",
        f"- Rapor yılı: {program.get('report_year', '')}",
        f"- Durum: {section.get('status', '')}",
        f"- Onay durumu: {section.get('approval_status', '')}",
        f"- Termin: {section.get('deadline', '')}",
        f"- Son güncelleme: {section.get('updated_at', '')}",
        "",
        "## Rapor Metni",
        "",
        str(section.get("report_text", "") or ""),
        "",
        "## PUKÖ",
        "",
        "### Planla",
        str(section.get("planla", "") or ""),
        "",
        "### Uygula",
        str(section.get("uygula", "") or ""),
        "",
        "### Kontrol Et",
        str(section.get("kontrol", "") or ""),
        "",
        "### Önlem Al",
        str(section.get("onlem", "") or ""),
        "",
        "## Notlar",
        "",
        str(section.get("notes", "") or ""),
        "",
    ]
    return "\n".join(lines)


def _rows_by_section(table: str, program_id: str, section_keys: set[str]) -> list[dict[str, Any]]:
    if not section_keys:
        return []
    placeholders = ",".join("?" for _ in section_keys)
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE program_id=? AND section_key IN ({placeholders}) ORDER BY section_key",
            [program_id, *sorted(section_keys)],
        ).fetchall()
    return rows_to_dicts(rows)


def _section_versions(program_id: str, section_keys: set[str]) -> list[dict[str, Any]]:
    if not section_keys:
        return []
    placeholders = ",".join("?" for _ in section_keys)
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT * FROM section_versions
                WHERE program_id=? AND section_key IN ({placeholders})
                ORDER BY saved_at DESC""",
            [program_id, *sorted(section_keys)],
        ).fetchall()
    return rows_to_dicts(rows)


def _activity_rows(username: str, program_id: str, include_scope_rows: bool) -> list[dict[str, Any]]:
    with get_conn() as conn:
        if include_scope_rows:
            rows = conn.execute(
                "SELECT * FROM activity_log WHERE program_id=? ORDER BY ts DESC LIMIT 1000",
                (program_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM activity_log WHERE program_id=? AND actor=? ORDER BY ts DESC LIMIT 1000",
                (program_id, username),
            ).fetchall()
    return rows_to_dicts(rows)


def _export_rows(username: str, program_id: str, include_scope_rows: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    with get_conn() as conn:
        if include_scope_rows:
            history = conn.execute("SELECT * FROM export_history WHERE program_id=? ORDER BY created_at DESC", (program_id,)).fetchall()
            jobs = conn.execute("SELECT * FROM export_jobs WHERE program_id=? ORDER BY created_at DESC", (program_id,)).fetchall()
        else:
            history = conn.execute("SELECT * FROM export_history WHERE program_id=? AND actor=? ORDER BY created_at DESC", (program_id, username)).fetchall()
            jobs = conn.execute("SELECT * FROM export_jobs WHERE program_id=? AND actor=? ORDER BY created_at DESC", (program_id, username)).fetchall()
    return rows_to_dicts(history), rows_to_dicts(jobs)


def _write_file_if_safe(zf: zipfile.ZipFile, arcname: str, stored_path: Any) -> bool:
    path = safe_stored_path(str(stored_path or ""))
    if not path or not path.exists() or not path.is_file():
        return False
    zf.writestr(arcname, path.read_bytes())
    return True


def _add_program_to_zip(zf: zipfile.ZipFile, username: str, program_id: str) -> dict[str, Any]:
    role = get_program_role(username, program_id)
    program = get_program(program_id) or {"id": program_id, "program_name": program_id}
    base = _program_folder(program)
    sections = list_sections(username, program_id)
    section_keys = {str(section.get("section_key", "") or "") for section in sections if str(section.get("section_key", "") or "")}
    include_scope_rows = role in PRIVILEGED_SCOPE_ROLES
    evidence_rows = list_evidence(username, program_id)
    table_rows = list_tables(username, program_id)
    approvals = _rows_by_section("section_approvals", program_id, section_keys)
    comments = _rows_by_section("section_comments", program_id, section_keys)
    versions = _section_versions(program_id, section_keys)
    activity = _activity_rows(username, program_id, include_scope_rows)
    export_history, export_jobs = _export_rows(username, program_id, include_scope_rows)
    manifest = {
        "backup_type": "role_scoped_personal_backup",
        "created_at": now_iso(),
        "owner_username": username,
        "program_id": program_id,
        "effective_role": role,
        "scope_note": "Bu ZIP yalnızca kullanıcının rol/yetki kapsamından okunabilen başlık, tablo, kanıt ve işlem kayıtlarını içerir.",
        "program": program,
        "counts": {
            "sections": len(sections),
            "evidence": len(evidence_rows),
            "tables": len(table_rows),
            "approvals": len(approvals),
            "comments": len(comments),
            "section_versions": len(versions),
            "activity_rows": len(activity),
            "export_history": len(export_history),
            "export_jobs": len(export_jobs),
        },
    }
    _zip_json(zf, f"{base}/manifest.json", manifest)
    _zip_json(zf, f"{base}/00_metadata/program.json", program)
    _zip_json(zf, f"{base}/00_metadata/sections_index.json", sections)

    for section in sections:
        section_key = str(section.get("section_key", "") or "genel")
        section_dir = section_folder_name(section_key)
        _zip_json(zf, f"{base}/01_rapor_metni/{section_dir}/latest.json", section)
        zf.writestr(f"{base}/01_rapor_metni/{section_dir}/latest.md", _text_markdown(program, section).encode("utf-8"))

    _zip_json(zf, f"{base}/02_kanitlar/evidence_index.json", evidence_rows)
    copied_evidence = 0
    for ev in evidence_rows:
        section_key = str((ev.get("section_keys") or [ev.get("section_key", "genel")])[0] or "genel") if isinstance(ev.get("section_keys"), list) else str(ev.get("section_key", "genel") or "genel")
        original = safe_download_name(ev.get("original_name") or ev.get("id") or "kanit")
        file_name = f"{_safe_part(ev.get('code') or ev.get('id'), 'kanit')}_{original}"
        if _write_file_if_safe(zf, f"{base}/02_kanitlar/{section_folder_name(section_key)}/{file_name}", ev.get("stored_path")):
            copied_evidence += 1
    manifest["counts"]["evidence_files_copied"] = copied_evidence

    _zip_json(zf, f"{base}/03_tablolar/tables_index.json", table_rows)
    for table in table_rows:
        section_key = str(table.get("section_key", "genel") or "genel")
        table_name = _safe_part(table.get("table_name") or table.get("id"), "tablo")
        _zip_json(zf, f"{base}/03_tablolar/{section_folder_name(section_key)}/{table_name}_{str(table.get('id', ''))[:8]}.json", table)

    _zip_json(zf, f"{base}/04_ciktilar/export_history.json", export_history)
    _zip_json(zf, f"{base}/04_ciktilar/export_jobs.json", export_jobs)
    copied_exports = 0
    for job in export_jobs:
        if str(job.get("status", "")) != "done":
            continue
        file_name = safe_download_name(job.get("file_name") or Path(str(job.get("file_path", "") or "cikti")).name)
        if _write_file_if_safe(zf, f"{base}/04_ciktilar/dosyalar/{_safe_part(job.get('export_type'), 'export')}_{file_name}", job.get("file_path")):
            copied_exports += 1
    manifest["counts"]["export_files_copied"] = copied_exports

    _zip_json(zf, f"{base}/05_islem_gecmisi/approvals.json", approvals)
    _zip_json(zf, f"{base}/05_islem_gecmisi/comments.json", comments)
    _zip_json(zf, f"{base}/05_islem_gecmisi/section_versions.json", versions)
    zf.writestr(f"{base}/05_islem_gecmisi/activity_log.jsonl", _jsonl_bytes(activity))

    scoped_payload = {
        "manifest": manifest,
        "program": program,
        "sections": sections,
        "evidence": evidence_rows,
        "tables": table_rows,
        "approvals": approvals,
        "comments": comments,
        "section_versions": versions,
        "activity_log": activity,
        "export_history": export_history,
        "export_jobs": export_jobs,
    }
    _zip_json(zf, f"{base}/99_raw/scoped_backup.json", scoped_payload)
    # Rewrite final manifest after copied file counters are known.
    _zip_json(zf, f"{base}/00_metadata/final_counts.json", manifest["counts"])
    return manifest


def build_program_personal_backup_zip(username: str, program_id: str) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        manifest = _add_program_to_zip(zf, username, program_id)
        _zip_json(zf, "Akreditasyon/Kullanici_Yedegi/manifest.json", {
            "backup_type": "single_program_role_scoped_personal_backup",
            "created_at": now_iso(),
            "owner_username": username,
            "program_count": 1,
            "programs": [manifest],
        })
    return buffer.getvalue()


def build_all_personal_backup_zip(username: str) -> bytes:
    programs = list_programs_for_user(username)
    buffer = BytesIO()
    manifests: list[dict[str, Any]] = []
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for program in programs:
            program_id = str(program.get("id", "") or "")
            if not program_id:
                continue
            try:
                manifests.append(_add_program_to_zip(zf, username, program_id))
            except PermissionError:
                continue
        _zip_json(zf, "Akreditasyon/Kullanici_Yedegi/manifest.json", {
            "backup_type": "all_accessible_programs_role_scoped_personal_backup",
            "created_at": now_iso(),
            "owner_username": username,
            "program_count": len(manifests),
            "scope_note": "Bu ZIP, kullanıcının erişebildiği tüm programlardaki rol kapsamı verilerini içerir.",
            "programs": manifests,
        })
    return buffer.getvalue()
