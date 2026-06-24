from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import ORG_STORAGE_DIR
from .file_security import safe_download_name, slugify


PROGRAM_SUBDIRS = (
    "01_kanitlar",
    "02_tablolar",
    "03_rapor_ciktilari",
    "04_rapor_metni",
    "05_onay_gecmisi",
    "06_loglar",
)


def timestamp_slug() -> str:
    """Filesystem-safe local timestamp used in archived filenames."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _slug(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    return slugify(text or fallback)


def _same_value(left: Any, right: Any) -> bool:
    return str(left or "").strip().casefold() == str(right or "").strip().casefold()


def section_folder_name(section_key: Any) -> str:
    """Keep section codes human-readable while blocking path traversal."""
    raw = str(section_key or "genel").strip() or "genel"
    return safe_download_name(raw).replace(" ", "_")[:60] or "genel"


def program_storage_dir(program: dict[str, Any]) -> Path:
    """Return the human-navigable archive root for a program.

    Shape:
    medek_data/kurumlar/kurum_<...>/birim_<...>/fakulte_<...>/bolum_<...>/program_<...>/yil_<...>

    The labels intentionally make the hierarchy readable on Windows Explorer and
    avoid ambiguity when a faculty/MYO name is also used as the school/unit name.
    """
    university = program.get("university_name") or program.get("tenant_name") or program.get("tenant_id") or "kurum"
    unit = program.get("school_name") or program.get("faculty_name") or "birim"
    faculty = program.get("faculty_name") or unit or "fakulte"
    department = program.get("department_name") or "bolum-yok"
    program_name = program.get("program_name") or program.get("id") or "program"
    report_year = program.get("report_year") or "yil-yok"
    return (
        ORG_STORAGE_DIR
        / f"kurum_{_slug(university, 'kurum')}"
        / f"birim_{_slug(unit, 'birim')}"
        / f"fakulte_{_slug(faculty, 'fakulte')}"
        / f"bolum_{_slug(department, 'bolum-yok')}"
        / f"program_{_slug(program_name, 'program')}"
        / f"yil_{_slug(report_year, 'yil-yok')}"
    )


def ensure_program_storage(program: dict[str, Any]) -> Path:
    root = program_storage_dir(program)
    root.mkdir(parents=True, exist_ok=True)
    for name in PROGRAM_SUBDIRS:
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def write_program_manifest(program: dict[str, Any], *, extra: dict[str, Any] | None = None) -> Path:
    root = ensure_program_storage(program)
    manifest = {
        "program_id": str(program.get("id", "") or ""),
        "kurum": str(program.get("university_name", "") or program.get("tenant_name", "") or program.get("tenant_id", "") or ""),
        "birim": str(program.get("school_name", "") or ""),
        "fakulte": str(program.get("faculty_name", "") or program.get("school_name", "") or ""),
        "bolum": str(program.get("department_name", "") or ""),
        "program": str(program.get("program_name", "") or ""),
        "rapor_yili": str(program.get("report_year", "") or ""),
        "akreditasyon_profili": str(program.get("accreditation_profile", "") or "MEDEK"),
        "son_guncelleme": datetime.now().isoformat(timespec="seconds"),
        "klasor_yapisi": {
            "01_kanitlar": "Başlık bazlı yüklenen kanıt dosyaları",
            "02_tablolar": "Başlık bazlı tablo JSON kopyaları",
            "03_rapor_ciktilari": "DOCX/PDF ve diğer çıktı dosyaları",
            "04_rapor_metni": "Başlık bazlı rapor metni JSON/Markdown aynaları",
            "05_onay_gecmisi": "Onay/revizyon geçmişi JSONL aynası",
            "06_loglar": "Denetim izi JSONL aynası",
        },
    }
    if extra:
        manifest["son_islem"] = extra
    target = root / "manifest.json"
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return target



def report_text_section_dir(program: dict[str, Any], section_key: Any) -> Path:
    root = ensure_program_storage(program)
    path = root / "04_rapor_metni" / section_folder_name(section_key)
    (path / "versions").mkdir(parents=True, exist_ok=True)
    return path


def approval_history_dir(program: dict[str, Any]) -> Path:
    root = ensure_program_storage(program)
    path = root / "05_onay_gecmisi"
    path.mkdir(parents=True, exist_ok=True)
    return path


def audit_log_dir(program: dict[str, Any]) -> Path:
    root = ensure_program_storage(program)
    path = root / "06_loglar"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _section_payload(program: dict[str, Any], section: dict[str, Any], *, actor: str = "", action: str = "", is_autosave: bool = False) -> dict[str, Any]:
    return {
        "program_id": str(program.get("id", "") or section.get("program_id", "") or ""),
        "kurum": str(program.get("university_name", "") or program.get("tenant_name", "") or program.get("tenant_id", "") or ""),
        "birim": str(program.get("school_name", "") or ""),
        "fakulte": str(program.get("faculty_name", "") or program.get("school_name", "") or ""),
        "bolum": str(program.get("department_name", "") or ""),
        "program": str(program.get("program_name", "") or ""),
        "rapor_yili": str(program.get("report_year", "") or ""),
        "akreditasyon_profili": str(program.get("accreditation_profile", "") or "MEDEK"),
        "section_key": str(section.get("section_key", "") or ""),
        "main_title": str(section.get("main_title", "") or ""),
        "section_title": str(section.get("section_title", "") or ""),
        "status": str(section.get("status", "") or ""),
        "approval_status": str(section.get("approval_status", "") or ""),
        "responsible_username": str(section.get("responsible_username", "") or ""),
        "deadline": str(section.get("deadline", "") or ""),
        "approved_by": str(section.get("approved_by", "") or ""),
        "approved_at": str(section.get("approved_at", "") or ""),
        "updated_at": str(section.get("updated_at", "") or ""),
        "archived_at": datetime.now().isoformat(timespec="seconds"),
        "archived_by": actor,
        "archive_action": action,
        "is_autosave": bool(is_autosave),
        "report_text": str(section.get("report_text", "") or ""),
        "puko": {
            "planla": str(section.get("planla", "") or ""),
            "uygula": str(section.get("uygula", "") or ""),
            "kontrol": str(section.get("kontrol", "") or ""),
            "onlem": str(section.get("onlem", "") or ""),
        },
        "notes": str(section.get("notes", "") or ""),
    }


def _section_markdown(payload: dict[str, Any]) -> str:
    puko = payload.get("puko") if isinstance(payload.get("puko"), dict) else {}
    title = f"{payload.get('section_key', '')} - {payload.get('section_title', '')}".strip(" -")
    lines = [
        f"# {title or 'Başlık'}",
        "",
        f"- Kurum: {payload.get('kurum', '')}",
        f"- Birim/Fakülte: {payload.get('birim', '')} / {payload.get('fakulte', '')}",
        f"- Bölüm/Program: {payload.get('bolum', '')} / {payload.get('program', '')}",
        f"- Rapor yılı: {payload.get('rapor_yili', '')}",
        f"- Durum: {payload.get('status', '')}",
        f"- Onay durumu: {payload.get('approval_status', '')}",
        f"- Sorumlu: {payload.get('responsible_username', '')}",
        f"- Termin: {payload.get('deadline', '')}",
        f"- Arşiv zamanı: {payload.get('archived_at', '')}",
        f"- Arşiv işlemi: {payload.get('archive_action', '')}",
        "",
        "## Rapor Metni",
        "",
        str(payload.get("report_text", "") or ""),
        "",
        "## PUKÖ",
        "",
        "### Planla",
        str(puko.get("planla", "") or ""),
        "",
        "### Uygula",
        str(puko.get("uygula", "") or ""),
        "",
        "### Kontrol Et",
        str(puko.get("kontrol", "") or ""),
        "",
        "### Önlem Al",
        str(puko.get("onlem", "") or ""),
        "",
        "## Notlar",
        "",
        str(payload.get("notes", "") or ""),
        "",
    ]
    return "\n".join(lines)


def write_section_text_archive(
    program: dict[str, Any],
    section: dict[str, Any],
    *,
    actor: str = "",
    action: str = "Başlık kaydı",
    is_autosave: bool = False,
    create_version: bool | None = None,
) -> dict[str, str]:
    """Mirror one section's report text/PUKÖ fields to JSON and Markdown.

    PostgreSQL remains authoritative. These sidecar files make the
    Akreditasyon folder human-readable and recoverable during audit handover.
    Autosaves update latest.* by default; manual saves and workflow actions also
    create timestamped versions.
    """
    folder = report_text_section_dir(program, section.get("section_key", "genel"))
    payload = _section_payload(program, section, actor=actor, action=action, is_autosave=is_autosave)
    json_text = json.dumps(payload, ensure_ascii=False, indent=2)
    md_text = _section_markdown(payload)
    latest_json = folder / "latest.json"
    latest_md = folder / "latest.md"
    latest_json.write_text(json_text, encoding="utf-8")
    latest_md.write_text(md_text, encoding="utf-8")
    result = {"latest_json": str(latest_json), "latest_md": str(latest_md)}
    should_version = (not is_autosave) if create_version is None else bool(create_version)
    if should_version:
        stamp = timestamp_slug()
        version_json = folder / "versions" / f"{stamp}_{section_folder_name(section.get('section_key', 'genel'))}.json"
        version_md = folder / "versions" / f"{stamp}_{section_folder_name(section.get('section_key', 'genel'))}.md"
        version_json.write_text(json_text, encoding="utf-8")
        version_md.write_text(md_text, encoding="utf-8")
        result.update({"version_json": str(version_json), "version_md": str(version_md)})
    write_program_manifest(program, extra={"type": "section_text_archive", "section_key": str(section.get("section_key", "") or ""), "actor": actor, "action": action, "file": result.get("latest_json", "")})
    return result


def write_all_sections_archive(program: dict[str, Any], sections: list[dict[str, Any]], *, actor: str = "", action: str = "Tam rapor aynası", create_snapshot: bool = True) -> Path:
    root = ensure_program_storage(program)
    folder = root / "04_rapor_metni"
    folder.mkdir(parents=True, exist_ok=True)
    payload = {
        "program": {
            "id": str(program.get("id", "") or ""),
            "kurum": str(program.get("university_name", "") or program.get("tenant_name", "") or ""),
            "birim": str(program.get("school_name", "") or ""),
            "fakulte": str(program.get("faculty_name", "") or program.get("school_name", "") or ""),
            "bolum": str(program.get("department_name", "") or ""),
            "program": str(program.get("program_name", "") or ""),
            "rapor_yili": str(program.get("report_year", "") or ""),
            "akreditasyon_profili": str(program.get("accreditation_profile", "") or "MEDEK"),
        },
        "archived_at": datetime.now().isoformat(timespec="seconds"),
        "archived_by": actor,
        "archive_action": action,
        "sections": [_section_payload(program, section, actor=actor, action=action) for section in sections],
    }
    latest = folder / "tum_rapor_latest.json"
    latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if create_snapshot:
        snapshot = folder / f"tum_rapor_{timestamp_slug()}.json"
        snapshot.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_program_manifest(program, extra={"type": "full_report_archive", "actor": actor, "section_count": len(sections), "file": str(latest)})
    return latest


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_approval_snapshot(program: dict[str, Any], approval: dict[str, Any], *, actor: str = "", action: str = "") -> Path:
    folder = approval_history_dir(program)
    payload = {
        "program_id": str(program.get("id", "") or approval.get("program_id", "") or ""),
        "section_key": str(approval.get("section_key", "") or ""),
        "status": str(approval.get("status", "") or ""),
        "requested_by": str(approval.get("requested_by", "") or ""),
        "decided_by": str(approval.get("decided_by", "") or ""),
        "note": str(approval.get("note", "") or ""),
        "created_at": str(approval.get("created_at", "") or ""),
        "archived_at": datetime.now().isoformat(timespec="seconds"),
        "archived_by": actor,
        "archive_action": action,
    }
    append_jsonl(folder / "approval_history.jsonl", payload)
    snapshot = folder / f"{timestamp_slug()}_{section_folder_name(payload['section_key'])}_{_slug(payload['status'], 'onay')}.json"
    snapshot.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_program_manifest(program, extra={"type": "approval_history", "section_key": payload["section_key"], "status": payload["status"], "file": str(snapshot)})
    return snapshot


def append_activity_log_snapshot(program: dict[str, Any], entry: dict[str, Any]) -> Path:
    folder = audit_log_dir(program)
    payload = {
        "program_id": str(program.get("id", "") or entry.get("program_id", "") or ""),
        "ts": str(entry.get("ts", "") or datetime.now().isoformat(timespec="seconds")),
        "action": str(entry.get("action", "") or ""),
        "detail": str(entry.get("detail", "") or ""),
        "actor": str(entry.get("actor", "") or ""),
        "archived_at": datetime.now().isoformat(timespec="seconds"),
    }
    path = folder / "activity_log.jsonl"
    append_jsonl(path, payload)
    return path

def evidence_section_dir(program: dict[str, Any], section_key: Any) -> Path:
    root = ensure_program_storage(program)
    path = root / "01_kanitlar" / section_folder_name(section_key)
    path.mkdir(parents=True, exist_ok=True)
    return path


def table_section_dir(program: dict[str, Any], section_key: Any) -> Path:
    root = ensure_program_storage(program)
    path = root / "02_tablolar" / section_folder_name(section_key)
    path.mkdir(parents=True, exist_ok=True)
    return path


def report_export_dir(program: dict[str, Any]) -> Path:
    root = ensure_program_storage(program)
    path = root / "03_rapor_ciktilari"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_table_snapshot(
    program: dict[str, Any],
    *,
    section_key: str,
    table_id: str,
    table_name: str,
    data_json: str,
    actor: str = "",
) -> Path:
    """Write a timestamped filesystem copy of a saved table.

    PostgreSQL remains authoritative; this sidecar helps manual inspection and
    offline archive review under the Akreditasyon folder.
    """
    folder = table_section_dir(program, section_key)
    file_name = f"{timestamp_slug()}_{safe_download_name(table_name).rsplit('.', 1)[0]}_{table_id[:8]}.json"
    target = folder / file_name
    payload = {
        "program_id": str(program.get("id", "") or ""),
        "section_key": section_key,
        "table_id": table_id,
        "table_name": table_name,
        "actor": actor,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "data": json.loads(data_json or "{}"),
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_program_manifest(program, extra={"type": "table_snapshot", "section_key": section_key, "file": str(target)})
    return target


def write_export_copy(program: dict[str, Any], *, file_name: str, data: bytes, export_type: str, actor: str = "", job_id: str = "") -> Path:
    folder = report_export_dir(program)
    safe_name = safe_download_name(file_name)
    stem = Path(safe_name).stem or "cikti"
    suffix = Path(safe_name).suffix or (".pdf" if "pdf" in export_type else ".docx")
    job_part = f"_{job_id[:8]}" if job_id else ""
    target = folder / f"{timestamp_slug()}_{slugify(export_type)}{job_part}_{safe_download_name(stem)}{suffix.lower()}"
    target.write_bytes(data)
    write_program_manifest(program, extra={"type": "export", "export_type": export_type, "actor": actor, "file": str(target)})
    return target
