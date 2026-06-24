from pathlib import Path
from tests.frontend_helpers import read_frontend_source, read_frontend_styles

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_insights_no_invalid_report_group_sql_regression():
    source = read("backend/insights.py")
    assert "s.report_group_title" not in source
    assert 'item["report_group_title"] = item.get("main_title", "")' in source


def test_enterprise_feature_endpoints_present():
    main = read("backend/main.py")
    api = read("frontend/src/api.js")
    assert "/api/programs/{program_id}/activity-timeline" in main
    assert "/api/programs/{program_id}/advanced-reporting" in main
    assert "/api/programs/{program_id}/sections/{section_key}/versions" in main
    assert "/api/admin/permissions" in main
    assert "/api/admin/programs/deleted" in main
    assert "activityTimeline:" in api
    assert "advancedReporting:" in api
    assert "sectionVersions:" in api
    assert "deletedPrograms:" in api


def test_soft_delete_and_export_progress_schema_present():
    db = read("backend/db.py")
    repos = read("backend/repositories.py")
    exports = read("backend/export_jobs.py")
    assert "deleted_at TEXT DEFAULT" in db
    assert "deleted_by TEXT DEFAULT" in db
    assert "progress INTEGER NOT NULL DEFAULT 0" in db
    assert "message TEXT DEFAULT" in db
    assert "UPDATE programs SET is_active=0, deleted_at=?" in repos
    assert "progress=35" in exports
    assert "progress=85" in exports
    assert "progress=100" in exports


def test_frontend_modules_for_new_enterprise_features_present():
    nav = read("frontend/src/config/navigation.jsx")
    main = read_frontend_source(ROOT)
    for module in ["timeline", "advanced", "versions", "permissions", "recovery", "analytics", "appearance"]:
        assert module in nav
    for view in ["ActivityTimelineView", "AdvancedDashboardView", "VersionDiffView", "PermissionMatrixView", "RecoveryView", "AnalyticsView", "AppearanceView"]:
        assert f"function {view}" in main
    assert "theme-dark" in main


def test_sidebar_visibility_matrix_is_configurable_and_returned_to_me():
    enterprise = read("backend/enterprise_features.py")
    main = read("backend/main.py")
    nav = read("frontend/src/config/navigation.jsx")
    frontend = read_frontend_source(ROOT)
    api = read("frontend/src/api.js")
    assert "DEFAULT_SIDEBAR_MATRIX" in enterprise
    assert "sidebar_matrix_public" in enterprise
    assert "visible_sidebar_modules_for_role" in enterprise
    assert "_attach_ui_permission_payload" in main
    assert 'user_public["sidebar_matrix"] = _sidebar_matrix_for_user(source)' in main
    assert 'user_public["dashboard_permissions_by_role"] = _dashboard_permissions_by_role_for_user(source)' in main
    assert "sidebar_rows" in main
    assert "modulesForRole(role, sidebarMatrix = [])" in nav
    assert "Sidebar Görünürlük Matrisi" in frontend
    assert "Yetki ve Sidebar Matrislerini Kaydet" in frontend
    assert "savePermissions: (rows, sidebarRows = [])" in api
