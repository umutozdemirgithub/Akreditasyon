"""Premium evidence archive and table management payload builders."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .repositories import (
    assert_program_operation_permission,
    list_evidence,
    list_sections,
    list_tables,
)


def _parse_dt(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def _age_days(value: str | None) -> int | None:
    dt = _parse_dt(value)
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0, int((datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() // 86400))


def _risk(score: int) -> str:
    if score < 55:
        return "critical"
    if score < 78:
        return "warning"
    return "good"


def _file_type(name: str) -> str:
    suffix = Path(str(name or "")).suffix.lower().strip(".")
    if suffix in {"png", "jpg", "jpeg", "webp", "gif", "bmp"}:
        return "Görsel"
    if suffix == "pdf":
        return "PDF"
    if suffix in {"doc", "docx"}:
        return "Word"
    if suffix in {"xls", "xlsx", "csv"}:
        return "Tablo"
    return suffix.upper() if suffix else "Dosya"


def _section_maps(sections: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    by_key = {str(row.get("section_key", "")): row for row in sections}
    title = {key: str(row.get("section_title", key)) for key, row in by_key.items()}
    return by_key, title


def _section_group(section: dict[str, Any] | None) -> str:
    if not section:
        return "Bağlantısız"
    key = str(section.get("section_key", "") or "")
    title = str(section.get("section_title", "") or key)
    parent = str(section.get("parent_key", "") or "").strip()
    if parent:
        return parent
    if "." in key:
        return key.split(".", 1)[0]
    return title[:28] or key or "Genel"


def _evidence_card(row: dict[str, Any], section_titles: dict[str, str], section_by_key: dict[str, dict[str, Any]]) -> dict[str, Any]:
    keys = [str(key) for key in (row.get("section_keys") or [row.get("section_key")]) if str(key or "").strip()]
    note = str(row.get("note", "") or "").strip()
    name = str(row.get("original_name", "") or "Kanıt")
    age = _age_days(str(row.get("uploaded_at", "") or ""))
    score = 100
    if not keys:
        score -= 35
    if not note:
        score -= 15
    if not str(row.get("code", "") or "").strip():
        score -= 10
    if age is not None and age > 365:
        score -= 12
    score = max(0, min(100, score))
    suggestions: list[str] = []
    if not keys:
        suggestions.append("Kanıtı en az bir ölçüt/alt başlık ile ilişkilendirin.")
    if not note:
        suggestions.append("Kanıtın hangi bulguyu desteklediğini açıklayan kısa not ekleyin.")
    if not str(row.get("code", "") or "").strip():
        suggestions.append("MEDEK/MÜDEK rapor standardına uygun kanıt kodu tanımlayın.")
    if _file_type(name) == "Görsel":
        suggestions.append("Görsel kanıt için tarih, yer ve bağlam bilgisini not alanında belirtin.")
    if _file_type(name) == "PDF":
        suggestions.append("PDF içinde ilgili sayfa veya bölüm numarasını not alanına ekleyin.")
    if not suggestions:
        suggestions.append("Kanıt iyi görünüyor; rapor metninde bu kanıta açık referans verildiğini kontrol edin.")
    primary_section = section_by_key.get(keys[0]) if keys else None
    return {
        "id": row.get("id"),
        "code": row.get("code") or "Kodsuz",
        "original_name": name,
        "note": note,
        "uploaded_at": row.get("uploaded_at"),
        "section_keys": keys,
        "section_titles": [section_titles.get(key, key) for key in keys],
        "section_group": _section_group(primary_section),
        "file_type": _file_type(name),
        "quality_score": score,
        "risk_level": _risk(score),
        "age_days": age,
        "ai_suggestions": suggestions[:4],
        "status_label": "Bağlı" if keys else "Bağlantısız",
    }


def evidence_archive_studio_payload(username: str, program_id: str) -> dict[str, Any]:
    assert_program_operation_permission(username, program_id, "evidence.premium.view")
    sections = list_sections(username, program_id)
    section_by_key, section_titles = _section_maps(sections)
    rows = list_evidence(username, program_id)
    cards = [_evidence_card(row, section_titles, section_by_key) for row in rows]
    critical = sum(1 for card in cards if card["risk_level"] == "critical")
    warning = sum(1 for card in cards if card["risk_level"] == "warning")
    linked = sum(1 for card in cards if card.get("section_keys"))
    recent = sum(1 for card in cards if card.get("age_days") is not None and card["age_days"] <= 7)
    type_counts: dict[str, int] = {}
    for card in cards:
        type_counts[card["file_type"]] = type_counts.get(card["file_type"], 0) + 1
    heatmap = []
    for section in sections:
        key = str(section.get("section_key", ""))
        section_cards = [card for card in cards if key in card.get("section_keys", [])]
        count = len(section_cards)
        avg_score = int(round(sum(card["quality_score"] for card in section_cards) / count)) if count else 0
        score = avg_score if count else 35
        heatmap.append({
            "section_key": key,
            "section_title": section.get("section_title", key),
            "evidence_count": count,
            "quality_score": score,
            "risk_level": _risk(score),
        })
    assistant = {
        "headline": "Kanıtlar ölçütlere bağlandığında rapor güvenilirliği belirgin artar.",
        "actions": [
            "Kodsuz veya notsuz kanıtları tamamlayın.",
            "Kanıtı olmayan kırmızı ölçütlere öncelik verin.",
            "Her kanıt notunda hangi ölçütü desteklediğini açıkça belirtin.",
            "Görsel/PDF kanıtlarda tarih, sayfa ve bağlam bilgisini ekleyin.",
        ],
        "recommended_types": ["Toplantı tutanağı", "Öğrenci/mezun geri bildirim raporu", "İyileştirme karar formu", "Ders değerlendirme çıktısı", "Komisyon kararı"],
    }
    return {
        "overview": {
            "total": len(cards),
            "linked": linked,
            "missing_link": len(cards) - linked,
            "critical": critical,
            "warning": warning,
            "recent": recent,
            "type_counts": type_counts,
        },
        "cards": cards,
        "heatmap": heatmap,
        "assistant": assistant,
    }


def _table_card(table: dict[str, Any], section_titles: dict[str, str], section_by_key: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = table.get("rows") if isinstance(table.get("rows"), list) else []
    columns: list[str] = []
    meta = table.get("meta") if isinstance(table.get("meta"), dict) else {}
    if isinstance(meta.get("columns"), list):
        columns = [str(col) for col in meta.get("columns", []) if str(col).strip()]
    for row in rows:
        if isinstance(row, dict):
            for key in row.keys():
                if str(key) not in columns:
                    columns.append(str(key))
    total_cells = max(1, len(rows) * max(1, len(columns)))
    filled_cells = sum(1 for row in rows if isinstance(row, dict) for col in columns if str(row.get(col, "") or "").strip())
    completeness = int(round((filled_cells / total_cells) * 100)) if rows and columns else 0
    score = completeness
    if not rows:
        score = 25
    if not columns:
        score = min(score, 25)
    if len(columns) >= 8 and len(rows) >= 12:
        score = min(100, score + 5)
    if not str(table.get("table_name", "") or "").strip():
        score = max(0, score - 15)
    key = str(table.get("section_key", "") or "")
    suggestions: list[str] = []
    if not rows:
        suggestions.append("Tabloya en az bir veri satırı ekleyin veya CSV’den aktarın.")
    if completeness < 70:
        suggestions.append("Boş hücreleri tamamlayın; eksik veri kalite skorunu düşürür.")
    if len(columns) < 3:
        suggestions.append("Açıklama, kanıt kodu ve tarih/sorumlu gibi destekleyici sütunlar ekleyin.")
    if not key:
        suggestions.append("Tabloyu ilgili ölçüt/alt başlık ile ilişkilendirin.")
    if not suggestions:
        suggestions.append("Tablo iyi görünüyor; rapor metninde tablo numarasıyla referans verildiğini kontrol edin.")
    return {
        "id": table.get("id"),
        "table_name": table.get("table_name") or "Adsız Tablo",
        "section_key": key,
        "section_title": section_titles.get(key, key or "Belirtilmedi"),
        "section_group": _section_group(section_by_key.get(key)),
        "updated_at": table.get("updated_at"),
        "row_count": len(rows),
        "column_count": len(columns),
        "completeness": completeness,
        "quality_score": max(0, min(100, score)),
        "risk_level": _risk(max(0, min(100, score))),
        "ai_suggestions": suggestions[:4],
        "columns": columns[:12],
    }


def table_management_studio_payload(username: str, program_id: str) -> dict[str, Any]:
    assert_program_operation_permission(username, program_id, "table.premium.view")
    sections = list_sections(username, program_id)
    section_by_key, section_titles = _section_maps(sections)
    tables = list_tables(username, program_id)
    cards = [_table_card(table, section_titles, section_by_key) for table in tables]
    avg_score = int(round(sum(card["quality_score"] for card in cards) / len(cards))) if cards else 0
    critical = sum(1 for card in cards if card["risk_level"] == "critical")
    total_rows = sum(card["row_count"] for card in cards)
    heatmap = []
    for section in sections:
        key = str(section.get("section_key", ""))
        section_cards = [card for card in cards if card.get("section_key") == key]
        count = len(section_cards)
        score = int(round(sum(card["quality_score"] for card in section_cards) / count)) if count else 35
        heatmap.append({
            "section_key": key,
            "section_title": section.get("section_title", key),
            "table_count": count,
            "quality_score": score,
            "risk_level": _risk(score),
        })
    assistant = {
        "headline": "Tabloların rapor metniyle tutarlı, dolu ve kanıt koduyla ilişkilendirilmiş olması kaliteyi artırır.",
        "actions": [
            "Boş hücresi çok olan tabloları tamamlayın.",
            "Her tabloya açıklayıcı ad ve ilgili ölçüt bağlantısı verin.",
            "Kanıt kodu veya veri kaynağı sütunu ekleyin.",
            "Büyük tablolar için CSV şablonunu kullanarak standart yapıyı koruyun.",
        ],
        "templates": ["Öğrenci başarı izleme tablosu", "PUKÖ iyileştirme takip tablosu", "Ders değerlendirme analiz tablosu", "Kanıt eşleştirme tablosu"],
    }
    return {
        "overview": {
            "total": len(cards),
            "avg_score": avg_score,
            "critical": critical,
            "total_rows": total_rows,
            "wide_tables": sum(1 for card in cards if card["column_count"] >= 8),
            "empty_tables": sum(1 for card in cards if card["row_count"] == 0),
        },
        "cards": cards,
        "heatmap": heatmap,
        "assistant": assistant,
    }
