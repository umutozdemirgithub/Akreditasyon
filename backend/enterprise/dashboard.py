
from __future__ import annotations

from typing import Any

from .timeline import _activity_section_key
from ..db import get_conn, rows_to_dicts
from ..repositories import assert_program_operation_permission, list_sections, quality_for_section
from ..visibility_scope import event_visible_to_user, visible_section_keys


def advanced_reporting(username: str, program_id: str) -> dict[str, Any]:
    assert_program_operation_permission(username, program_id, "advanced_dashboard.view")
    sections = list_sections(username, program_id)
    by_group: dict[str, dict[str, Any]] = {}
    puko = {"Planla": 0, "Uygula": 0, "Kontrol": 0, "Önlem": 0}
    status_distribution: dict[str, int] = {}
    approval_distribution: dict[str, int] = {}
    heatmap = []
    for section in sections:
        q = quality_for_section(username, program_id, section)
        status_distribution[str(section.get("status") or "Belirsiz")] = status_distribution.get(str(section.get("status") or "Belirsiz"), 0) + 1
        approval_distribution[str(section.get("approval_status") or "Taslak")] = approval_distribution.get(str(section.get("approval_status") or "Taslak"), 0) + 1
        group = str(section.get("report_group_title") or section.get("main_title") or "Genel")
        row = by_group.setdefault(group, {"group": group, "total": 0, "ready": 0, "approved": 0, "revision": 0, "quality_sum": 0})
        row["total"] += 1
        row["quality_sum"] += int(q.get("score", 0) or 0)
        if section.get("status") in {"Taslak Hazır", "Tamamlandı"}:
            row["ready"] += 1
        if section.get("approval_status") == "Onaylandı":
            row["approved"] += 1
        if section.get("approval_status") == "Revizyon Gerekli" or section.get("status") == "Revizyon Gerekli":
            row["revision"] += 1
        for label, field in [("Planla", "planla"), ("Uygula", "uygula"), ("Kontrol", "kontrol"), ("Önlem", "onlem")]:
            if str(section.get(field, "") or "").strip():
                puko[label] += 1
        heatmap.append({"section_key": section.get("section_key", ""), "section_title": section.get("section_title", ""), "group": group, "risk": max(0, 100-int(q.get("score", 0) or 0)), "quality": int(q.get("score", 0) or 0), "status": section.get("status", ""), "approval_status": section.get("approval_status", "")})
    groups = []
    for row in by_group.values():
        total = max(1, int(row["total"]))
        row["readiness_percent"] = round(row["ready"] / total * 100, 1)
        row["approval_percent"] = round(row["approved"] / total * 100, 1)
        row["quality_avg"] = round(row["quality_sum"] / total, 1)
        del row["quality_sum"]
        groups.append(row)
    sorted_heatmap = sorted(heatmap, key=lambda r: r["risk"], reverse=True)[:120]
    total_sections = len(sections)
    summary = {
        "total": total_sections,
        "approved": sum(1 for section in sections if section.get("approval_status") == "Onaylandı"),
        "revision": sum(1 for section in sections if section.get("approval_status") in {"Revizyon Gerekli", "Revizyon İstendi"} or section.get("status") == "Revizyon Gerekli"),
        "high_risk": sum(1 for row in heatmap if int(row.get("risk", 0) or 0) >= 70),
        "quality_avg": round(sum(int(row.get("quality", 0) or 0) for row in heatmap) / max(1, len(heatmap)), 1),
    }
    visible_keys = visible_section_keys(username, program_id)
    trend: list[dict[str, Any]] = []
    activity_trend: list[dict[str, Any]] = []
    with get_conn() as conn:
        if visible_keys:
            placeholders = ",".join("?" for _ in visible_keys)
            trend_rows = conn.execute(f"""
                SELECT substr(saved_at, 1, 10) AS date, COUNT(*) AS saved_sections
                FROM section_versions
                WHERE program_id=? AND section_key IN ({placeholders})
                GROUP BY substr(saved_at, 1, 10)
                ORDER BY date DESC
                LIMIT 30
            """, [program_id, *sorted(visible_keys)]).fetchall()
            trend = list(reversed(rows_to_dicts(trend_rows)))
        activity_rows = rows_to_dicts(conn.execute("""
            SELECT id, ts AS created_at, action AS event, detail, actor, program_id, '' AS section_key
            FROM activity_log
            WHERE program_id=?
            ORDER BY ts DESC
            LIMIT 1000
        """, (program_id,)).fetchall())
    activity_counts: dict[str, int] = {}
    for row in activity_rows:
        row["section_key"] = _activity_section_key(str(row.get("detail") or ""), visible_keys)
        if not event_visible_to_user(username, program_id, row):
            continue
        day = str(row.get("created_at") or "")[:10]
        if day:
            activity_counts[day] = activity_counts.get(day, 0) + 1
    activity_trend = [
        {"date": day, "activity_count": count}
        for day, count in reversed(sorted(activity_counts.items(), reverse=True)[:30])
    ]
    return {
        "summary": summary,
        "group_chart": sorted(groups, key=lambda row: row.get("quality_avg", 0)),
        "puko_chart": [{"field": k, "count": v} for k, v in puko.items()],
        "status_distribution": [{"status": k, "count": v} for k, v in sorted(status_distribution.items())],
        "approval_distribution": [{"approval_status": k, "count": v} for k, v in sorted(approval_distribution.items())],
        "trend_chart": trend,
        "activity_trend": activity_trend,
        "risk_heatmap": sorted_heatmap,
    }
