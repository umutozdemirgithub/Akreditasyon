
from __future__ import annotations

from typing import Any

from ..db import get_conn, rows_to_dicts
from ..repositories import FACULTY_ADMIN_ROLE, SUPER_ADMIN_ROLE, TENANT_ADMIN_ROLE, actor_has_operation_permission, get_user, normalized_role
from ..visibility_scope import visible_activity_where


def usage_analytics_admin(username: str, limit: int = 200) -> dict[str, Any]:
    user = get_user(username, active_only=True) or {}
    role = normalized_role(str(user.get("role", "") or ""), str(user.get("tenant_scope", "") or ""))
    if role not in {SUPER_ADMIN_ROLE, TENANT_ADMIN_ROLE, FACULTY_ADMIN_ROLE} or not actor_has_operation_permission(user, "analytics.view"):
        raise PermissionError("Kullanım analitiği için Yetki Matrisi izniniz yok.")
    where_sql, params = visible_activity_where(username)
    with get_conn() as conn:
        actor_rows = conn.execute(
            f"SELECT actor, COUNT(*) AS count FROM activity_log WHERE {where_sql} GROUP BY actor ORDER BY count DESC LIMIT 30",
            params,
        ).fetchall()
        action_rows = conn.execute(
            f"SELECT action, COUNT(*) AS count FROM activity_log WHERE {where_sql} GROUP BY action ORDER BY count DESC LIMIT 50",
            params,
        ).fetchall()
        recent = conn.execute(
            f"SELECT * FROM activity_log WHERE {where_sql} ORDER BY ts DESC LIMIT ?",
            [*params, int(limit)],
        ).fetchall()
    return {"actors": rows_to_dicts(actor_rows), "actions": rows_to_dicts(action_rows), "recent": rows_to_dicts(recent)}
