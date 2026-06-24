from __future__ import annotations

from datetime import datetime
from typing import Any

from ..db import get_conn, rows_to_dicts
from ..repositories import list_sections


def _parse_date(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw[:19] if "%H" in fmt else raw[:10], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw[:19])
    except Exception:
        return None


def workflow_reminders_payload(username: str, program_id: str) -> dict[str, Any]:
    sections = list_sections(username, program_id)
    visible_keys = {str(row.get("section_key") or "") for row in sections if str(row.get("section_key") or "")}
    now = datetime.now()
    with get_conn() as conn:
        if visible_keys:
            placeholders = ",".join("?" for _ in visible_keys)
            approvals = rows_to_dicts(conn.execute(
                f"""SELECT section_key, status, requested_by, decided_by, note, created_at
                   FROM section_approvals
                   WHERE program_id=? AND section_key IN ({placeholders})
                   ORDER BY created_at DESC""",
                [program_id, *sorted(visible_keys)],
            ).fetchall())
        else:
            approvals = []
    latest_approval: dict[str, dict[str, Any]] = {}
    for row in approvals:
        key = str(row.get("section_key") or "")
        if key and key not in latest_approval:
            latest_approval[key] = row

    reminders = []
    for section in sections:
        deadline = _parse_date(str(section.get("deadline") or ""))
        days_left = None
        if deadline:
            days_left = (deadline.date() - now.date()).days
        approval_status = str(section.get("approval_status") or "Taslak")
        status = str(section.get("status") or "Başlamadı")
        category = "Bilgi"
        priority = "Düşük"
        message = "Takip edilmesi önerilir."
        if deadline and days_left is not None and days_left < 0 and approval_status != "Onaylandı":
            category = "Geciken termin"
            priority = "Yüksek"
            message = f"Termin {abs(days_left)} gün gecikti. Sorumlu editöre hatırlatma gönderin."
        elif deadline and days_left is not None and days_left <= 7 and approval_status != "Onaylandı":
            category = "Yaklaşan termin"
            priority = "Orta"
            message = f"Termin {days_left} gün içinde doluyor."
        elif approval_status == "Onaya Gönderildi":
            category = "Onay bekliyor"
            priority = "Orta"
            message = "Onaylayıcı kararı bekleniyor."
        elif approval_status == "Revizyon Gerekli":
            category = "Revizyon bekliyor"
            priority = "Yüksek"
            message = "Editör / Hazırlayıcı revizyonu tamamlamalı."
        elif status in {"Başlamadı", "Devam Ediyor"}:
            category = "Hazırlık devam ediyor"
            priority = "Düşük"
            message = "Başlık henüz hazır değil."
        else:
            continue
        reminders.append({
            "section_key": section.get("section_key", ""),
            "main_title": section.get("main_title", ""),
            "section_title": section.get("section_title", ""),
            "status": status,
            "approval_status": approval_status,
            "deadline": section.get("deadline", ""),
            "days_left": days_left,
            "category": category,
            "priority": priority,
            "message": message,
            "latest_actor": latest_approval.get(str(section.get("section_key") or ""), {}).get("requested_by") or latest_approval.get(str(section.get("section_key") or ""), {}).get("decided_by") or "",
            "latest_note": latest_approval.get(str(section.get("section_key") or ""), {}).get("note", ""),
        })
    priority_order = {"Yüksek": 0, "Orta": 1, "Düşük": 2}
    reminders.sort(key=lambda row: (priority_order.get(str(row.get("priority")), 9), row.get("days_left") is None, row.get("days_left") or 9999))
    summary: dict[str, int] = {}
    for row in reminders:
        summary[str(row.get("category") or "Diğer")] = summary.get(str(row.get("category") or "Diğer"), 0) + 1
    return {
        "summary": summary,
        "total": len(reminders),
        "high_priority": sum(1 for row in reminders if row.get("priority") == "Yüksek"),
        "medium_priority": sum(1 for row in reminders if row.get("priority") == "Orta"),
        "rows": reminders,
    }
