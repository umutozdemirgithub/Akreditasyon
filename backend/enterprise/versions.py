
from __future__ import annotations

import difflib
from typing import Any

from ..db import get_conn, row_to_dict, rows_to_dicts
from ..repositories import assert_program_operation_permission, get_section

VERSION_FIELDS = ["status", "report_text", "planla", "uygula", "kontrol", "onlem", "notes", "deadline"]


def _version_label(row: dict[str, Any], fallback: str = "Güncel") -> str:
    if not row:
        return fallback
    return str(row.get("saved_at") or row.get("updated_at") or fallback)


def _text_diff(old: str, new: str) -> list[dict[str, str]]:
    diff_rows = []
    for line in difflib.ndiff(str(old or "").splitlines(), str(new or "").splitlines()):
        if line.startswith("? "):
            continue
        diff_rows.append({"type": {"- ": "silindi", "+ ": "eklendi", "  ": "aynı"}.get(line[:2], ""), "line": line[2:]})
    return diff_rows[:800]


def _side_by_side(old: str, new: str) -> list[dict[str, str]]:
    matcher = difflib.SequenceMatcher(a=str(old or "").splitlines(), b=str(new or "").splitlines())
    rows: list[dict[str, str]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        left = str(old or "").splitlines()[i1:i2]
        right = str(new or "").splitlines()[j1:j2]
        size = max(len(left), len(right), 1)
        for idx in range(size):
            rows.append({
                "type": {"equal": "aynı", "replace": "değişti", "delete": "silindi", "insert": "eklendi"}.get(tag, tag),
                "old": left[idx] if idx < len(left) else "",
                "new": right[idx] if idx < len(right) else "",
            })
            if len(rows) >= 800:
                return rows
    return rows


def _field_changes(old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for field in VERSION_FIELDS:
        old_value = str(old.get(field, "") or "")
        new_value = str(new.get(field, "") or "")
        changed = old_value != new_value
        rows.append({
            "field": field,
            "changed": changed,
            "old_length": len(old_value),
            "new_length": len(new_value),
            "old_preview": old_value[:240],
            "new_preview": new_value[:240],
        })
    return rows



def _change_summary(side_rows: list[dict[str, str]], field_rows: list[dict[str, Any]]) -> dict[str, Any]:
    added = sum(1 for row in side_rows if row.get("type") == "eklendi")
    removed = sum(1 for row in side_rows if row.get("type") == "silindi")
    changed = sum(1 for row in side_rows if row.get("type") == "değişti")
    field_changed = [row.get("field") for row in field_rows if row.get("changed")]
    coach = []
    if added or changed:
        coach.append("Yeni sürümde metin genişletilmiş veya yeniden yapılandırılmış.")
    if removed:
        coach.append("Bazı ifadeler kaldırılmış; kanıt veya karar referansı kaybı olup olmadığı kontrol edilmeli.")
    if any(field in field_changed for field in ["planla", "uygula", "kontrol", "onlem"]):
        coach.append("PUKÖ alanlarında değişiklik var; döngünün plan-uygulama-kontrol-önlem ilişkisi korunmalı.")
    if not coach:
        coach.append("Metinsel fark sınırlı; alan bazlı küçük güncellemeler incelenebilir.")
    return {
        "added_lines": added,
        "removed_lines": removed,
        "changed_lines": changed,
        "changed_fields": field_changed,
        "ai_summary": coach[:4],
    }

def _pick_version(versions: list[dict[str, Any]], current: dict[str, Any], version_id: str) -> dict[str, Any]:
    clean = str(version_id or "").strip()
    if not clean or clean == "current":
        return current
    for version in versions:
        if str(version.get("id") or "") == clean:
            return version
    return versions[0] if versions else current


def section_versions_diff(username: str, program_id: str, section_key: str, base_id: str = "", compare_id: str = "current") -> dict[str, Any]:
    assert_program_operation_permission(username, program_id, "version_compare.view")
    # Program-level access is not enough for editors with assigned sections.
    # Reuse the repository section guard so a guessed section_key cannot expose
    # version snapshots for an unassigned title.
    guarded_section = get_section(username, program_id, section_key)
    if not guarded_section:
        raise KeyError(section_key)
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM section_versions WHERE program_id=? AND section_key=? ORDER BY saved_at DESC LIMIT 50", (program_id, section_key)).fetchall()
    versions = rows_to_dicts(rows)
    current_dict = guarded_section or {}
    previous = versions[0] if versions else {}
    base = _pick_version(versions, current_dict, base_id or (str(previous.get("id")) if previous else "current"))
    compare = _pick_version(versions, current_dict, compare_id or "current")
    old_text = str(base.get("report_text", "") or "")
    new_text = str(compare.get("report_text", "") or "")
    side_rows = _side_by_side(old_text, new_text)
    field_rows = _field_changes(base, compare)
    return {
        "section": current_dict,
        "versions": versions,
        "selected": {
            "base_id": str(base.get("id") or "current"),
            "base_label": _version_label(base, "Güncel"),
            "compare_id": str(compare.get("id") or "current"),
            "compare_label": _version_label(compare, "Güncel"),
        },
        "diff": _text_diff(old_text, new_text),
        "side_by_side": side_rows,
        "field_changes": field_rows,
        "summary": _change_summary(side_rows, field_rows),
    }
