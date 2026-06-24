from __future__ import annotations

"""Stable enterprise facade.

FastAPI routers and legacy tests import enterprise features from one stable
surface while the concrete implementations stay separated by concern. Keep
new feature exports here first, then re-export through backend.enterprise_features
for backwards compatibility.
"""

from .analytics import usage_analytics_admin
from .dashboard import advanced_reporting
from .matrix import (
    DEFAULT_PERMISSION_MATRIX,
    DEFAULT_SIDEBAR_MATRIX,
    permission_matrix_admin,
    role_permission_allowed,
    sidebar_matrix_public,
    effective_sidebar_matrix_public,
    repair_legacy_dashboard_sidebar_visibility,
    update_permission_matrix_admin,
    visible_sidebar_modules_for_role,
)
from .recovery import (
    deleted_items_admin,
    deleted_programs_admin,
    purge_item_admin,
    purge_program_admin,
    restore_item_admin,
    restore_program_admin,
)
from .timeline import activity_timeline
from .versions import section_versions_diff
from .audit import compliance_audit_payload
from .workflow import workflow_reminders_payload
from .workflow_automation import (
    workflow_automation_preview,
    workflow_automation_runs,
    workflow_automation_settings,
    run_workflow_automation,
    update_workflow_automation_settings,
)

__all__ = [
    "DEFAULT_PERMISSION_MATRIX",
    "DEFAULT_SIDEBAR_MATRIX",
    "permission_matrix_admin",
    "role_permission_allowed",
    "sidebar_matrix_public",
    "effective_sidebar_matrix_public",
    "repair_legacy_dashboard_sidebar_visibility",
    "update_permission_matrix_admin",
    "visible_sidebar_modules_for_role",
    "deleted_items_admin",
    "deleted_programs_admin",
    "purge_item_admin",
    "purge_program_admin",
    "restore_item_admin",
    "restore_program_admin",
    "activity_timeline",
    "section_versions_diff",
    "advanced_reporting",
    "usage_analytics_admin",
    "compliance_audit_payload",
    "workflow_reminders_payload",
    "workflow_automation_preview",
    "workflow_automation_runs",
    "workflow_automation_settings",
    "run_workflow_automation",
    "update_workflow_automation_settings",
]
