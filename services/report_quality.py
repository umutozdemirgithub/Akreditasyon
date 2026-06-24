from __future__ import annotations

from typing import Any, Mapping, Sequence


def _value(row: Mapping[str, Any] | Any, key: str, default: Any = "") -> Any:
    try:
        return row[key]
    except Exception:
        return default


def build_report_quality_scorecard(
    sections: Sequence[Mapping[str, Any] | Any],
    guide_by_key: Mapping[str, Mapping[str, Any]],
    evidence_count_by_key: Mapping[str, int],
    table_count_by_key: Mapping[str, int],
    quality_by_key: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Calculate a report-level score using text, evidence, PUKO, table and approval coverage."""
    rows: list[dict[str, Any]] = []
    for section in sections:
        key = str(_value(section, "section_key", ""))
        guide = guide_by_key.get(key, {})
        quality = quality_by_key.get(key, {})
        words = int(quality.get("words", 0) or 0)
        evidence_count = int(evidence_count_by_key.get(key, 0) or 0)
        table_count = int(table_count_by_key.get(key, 0) or 0)
        puko_count = int(quality.get("puko", 0) or 0)
        uncited = int(quality.get("uncited_evidence", 0) or 0)
        approval = str(_value(section, "approval_status", "Taslak") or "Taslak")

        text_score = min(words / 420, 1) * 30
        evidence_score = min(evidence_count / 2, 1) * 20
        if uncited:
            evidence_score = max(0, evidence_score - min(uncited * 4, 12))
        puko_score = min(puko_count / 4, 1) * 20
        table_required = bool(guide.get("table"))
        table_score = (15 if table_count > 0 else 0) if table_required else 15
        approval_score = 15 if approval == "Onaylandı" else 8 if approval == "Onaya Gönderildi" else 4 if approval == "Revizyon İstendi" else 0
        total = round(text_score + evidence_score + puko_score + table_score + approval_score)
        rows.append({
            "Kod": key,
            "Başlık": str(_value(section, "section_title", "")),
            "Metin": round(text_score),
            "Kanıt": round(evidence_score),
            "PUKÖ": round(puko_score),
            "Tablo": round(table_score),
            "Onay": round(approval_score),
            "Toplam": total,
            "Risk": "; ".join([str(x) for x in quality.get("risk", []) or []]) or "Yok",
        })

    avg_score = round(sum(row["Toplam"] for row in rows) / len(rows), 1) if rows else 0
    summary = {
        "score": avg_score,
        "excellent": sum(1 for row in rows if row["Toplam"] >= 85),
        "needs_work": sum(1 for row in rows if row["Toplam"] < 70),
        "total": len(rows),
    }
    return rows, summary

