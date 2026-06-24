from __future__ import annotations

# Facade kept for stable imports from backend.main. Concrete functionality is
# split by concern under backend/enterprise/*. A stronger enterprise.facade
# module also re-exports this public surface for new code.
from .enterprise.matrix import (
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
from .enterprise.recovery import (
    deleted_items_admin,
    deleted_programs_admin,
    purge_item_admin,
    purge_program_admin,
    restore_item_admin,
    restore_program_admin,
)
from .enterprise.timeline import activity_timeline
from .enterprise.versions import section_versions_diff
from .enterprise.dashboard import advanced_reporting
from .enterprise.analytics import usage_analytics_admin
from .enterprise.audit import compliance_audit_payload
from .enterprise.workflow import workflow_reminders_payload
from .enterprise.workflow_automation import (
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
