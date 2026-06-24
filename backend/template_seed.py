from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .accreditation import ACCREDITATION_PROFILES, accreditation_profile_meta, normalize_accreditation_profile, profile_section_template
from .db import get_conn, now_iso, rows_to_dicts, transaction

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
TEMPLATE_VERSION = "2026.1"


def _template_file_key(profile: str) -> str:
    return (
        str(profile or "")
        .strip()
        .upper()
        .translate(str.maketrans({"İ": "I", "Ü": "U", "Ö": "O", "Ç": "C", "Ş": "S", "Ğ": "G"}))
        .replace(" ", "_")
    )


def _template_payload(profile: str) -> dict[str, Any]:
    profile = normalize_accreditation_profile(profile)
    meta = accreditation_profile_meta(profile)
    path = TEMPLATE_DIR / f"{_template_file_key(profile)}.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("sections"), list):
                return data
        except Exception:
            pass
    return {
        "template_key": profile,
        "template_name": meta.get("label", profile),
        "association_name": meta.get("association_name", ""),
        "system_name": meta.get("system_name", ""),
        "version": TEMPLATE_VERSION,
        "report_type": meta.get("report_type", "ÖZ DEĞERLENDİRME RAPORU"),
        "sections": profile_section_template(profile),
    }


def ensure_template_json_files() -> list[dict[str, Any]]:
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    payloads: list[dict[str, Any]] = []
    for profile in ACCREDITATION_PROFILES:
        payload = _template_payload(profile)
        payloads.append(payload)
        path = TEMPLATE_DIR / f"{_template_file_key(profile)}.json"
        if not path.exists():
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payloads


def seed_system_templates(conn=None) -> int:
    payloads = ensure_template_json_files()
    close_after = False
    if conn is None:
        conn = get_conn()
        close_after = True
    try:
        valid_keys = [normalize_accreditation_profile(profile) for profile in ACCREDITATION_PROFILES]
        if valid_keys:
            placeholders = ",".join("?" for _ in valid_keys)
            conn.execute(f"DELETE FROM system_templates WHERE template_key NOT IN ({placeholders})", tuple(valid_keys))
        count = 0
        for payload in payloads:
            key = normalize_accreditation_profile(payload.get("template_key"))
            meta = accreditation_profile_meta(key)
            conn.execute(
                """INSERT OR REPLACE INTO system_templates(
                    template_key, template_name, version, association_name, system_name,
                    report_type, data_json, updated_at
                ) VALUES(?,?,?,?,?,?,?,?)""",
                (
                    key,
                    str(payload.get("template_name") or meta.get("label") or key),
                    str(payload.get("version") or TEMPLATE_VERSION),
                    str(payload.get("association_name") or meta.get("association_name") or ""),
                    str(payload.get("system_name") or meta.get("system_name") or ""),
                    str(payload.get("report_type") or meta.get("report_type") or "ÖZ DEĞERLENDİRME RAPORU"),
                    json.dumps(payload, ensure_ascii=False),
                    now_iso(),
                ),
            )
            count += 1
        if close_after:
            conn.commit()
        return count
    finally:
        if close_after:
            conn.close()


def seed_system_templates_admin(username: str) -> dict[str, Any]:
    from .repositories import assert_admin, log_activity

    assert_admin(username)
    count = seed_system_templates()
    log_activity("Sistem şablonları seed edildi", f"{count} şablon", username, "")
    return {"ok": True, "template_count": count}


def list_system_templates_admin(username: str) -> list[dict[str, Any]]:
    from .repositories import assert_admin

    assert_admin(username)
    with transaction() as conn:
        seed_system_templates(conn)
        rows = conn.execute(
            """SELECT template_key, template_name, version, association_name, system_name,
                      report_type, updated_at,
                      LENGTH(data_json) AS size_bytes
               FROM system_templates
               ORDER BY template_key"""
        ).fetchall()
    return rows_to_dicts(rows)


def restore_missing_program_sections_admin(username: str, program_id: str | None = None) -> dict[str, Any]:
    from .repositories import _insert_empty_sections, assert_admin, log_activity

    assert_admin(username)
    restored: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    with transaction() as conn:
        seed_system_templates(conn)
        if program_id:
            rows = conn.execute("SELECT id, program_name, accreditation_profile FROM programs WHERE id=?", (program_id,)).fetchall()
        else:
            rows = conn.execute("SELECT id, program_name, accreditation_profile FROM programs ORDER BY program_name").fetchall()
        for row in rows:
            pid = str(row["id"])
            count = conn.execute("SELECT COUNT(*) AS n FROM sections WHERE program_id=?", (pid,)).fetchone()["n"]
            if int(count or 0) > 0:
                skipped.append({"program_id": pid, "program_name": row["program_name"], "reason": "sections_exist"})
                continue
            profile = normalize_accreditation_profile(row["accreditation_profile"] or "MEDEK")
            _insert_empty_sections(conn, pid, profile_section_template(profile))
            section_count = conn.execute("SELECT COUNT(*) AS n FROM sections WHERE program_id=?", (pid,)).fetchone()["n"]
            restored.append({"program_id": pid, "program_name": row["program_name"], "profile": profile, "section_count": int(section_count or 0)})
        log_activity("Sistem şablonları geri yüklendi", json.dumps({"restored": restored, "skipped": len(skipped)}, ensure_ascii=False), username, program_id or "")
    return {"ok": True, "restored": restored, "skipped": skipped}
