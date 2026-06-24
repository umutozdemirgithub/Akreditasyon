from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_app_keeps_permission_matrix_renderable_when_sidebar_visibility_changes():
    source = (ROOT / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    assert "sessionAdminCanKeepMatrixOpen" in source
    assert 'activeModule === "permissions" && isAdminRole(activeProgramRole)' in source
    assert "activeModuleCanRender" in source
    assert "onMatrixSaved={refreshCurrentUser}" in source
    assert "Modül erişimi güncellendi" in source


def test_permission_matrix_refreshes_user_after_save():
    source = (ROOT / "frontend" / "src" / "views" / "AppViews.jsx").read_text(encoding="utf-8")
    assert "onMatrixSaved" in source
    assert "await onMatrixSaved().catch(() => null)" in source
    assert "Menü görünürlüğü güvenli şekilde yenilendi" in source


def test_frontend_uses_effective_sidebar_without_legacy_dashboard_fallback():
    navigation = (ROOT / "frontend" / "src" / "config" / "navigation.jsx").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    assert "return allowed;" in navigation
    assert "if (allowed.length) return allowed" not in navigation
    assert 'const renderModule = activeModuleCanRender ? activeModule : ""' in app
    assert 'const firstVisibleModule = visibleModules[0] || ""' in app
    assert "Bu rol için görünür modül bulunmuyor." in app
    assert 'setActiveModule(visibleModules[0] || "dashboard")' not in app


def test_backend_dashboard_permission_does_not_gate_sidebar_visibility():
    source = (ROOT / "backend" / "enterprise" / "matrix.py").read_text(encoding="utf-8")
    main = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
    assert "MODULE_VIEW_PERMISSIONS" in source
    assert '"dashboard": "dashboard.view"' not in source
    assert "dashboard.* izinleri dashboard" in source
    assert "effective_sidebar_matrix_public" in source
    assert "_ensure_effective_sidebar_has_module" in source
    assert "return effective_sidebar_matrix_public" in main
    assert "dashboard_permissions_by_role" in main



def test_effective_sidebar_keeps_dashboard_when_dashboard_view_is_disabled():
    from backend.enterprise.matrix import DEFAULT_PERMISSION_MATRIX, DEFAULT_SIDEBAR_MATRIX, _clean_permission_rows, _clean_sidebar_rows, _effective_sidebar_rows

    permission_rows = _clean_permission_rows(DEFAULT_PERMISSION_MATRIX)
    sidebar_rows = _clean_sidebar_rows(DEFAULT_SIDEBAR_MATRIX)
    for row in permission_rows:
        if row["permission"] == "dashboard.view":
            row["Editör / Hazırlayıcı"] = False
    effective = _effective_sidebar_rows(sidebar_rows, permission_rows)
    dashboard = next(row for row in effective if row["module"] == "dashboard")
    assert dashboard["Editör / Hazırlayıcı"] is True


def test_frontend_dashboard_uses_granular_dashboard_permissions():
    app = (ROOT / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    view = (ROOT / "frontend" / "src" / "views" / "AppViews.jsx").read_text(encoding="utf-8")
    assert "dashboardPermissions={dashboardPermissions}" in app
    assert "dashboard_permissions_by_role" in app
    for permission in [
        "dashboard.view",
        "dashboard.kpi.view",
        "dashboard.priority.view",
        "dashboard.criteria.view",
        "dashboard.charts.view",
        "dashboard.activity.view",
    ]:
        assert permission in view
    assert "canDashboardOverview" in view
    assert 'id: "priority"' in view and "<PriorityPanel" in view
    assert 'id: "charts"' in view and "<MiniChartsPanel" in view
    assert "canDashboardCriteria &&" in view
    assert "effectiveInsightTab" in view


def test_sidebar_and_dashboard_theme_sync_hooks_are_present():
    app = (ROOT / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
    hook = (ROOT / "frontend" / "src" / "hooks" / "useSidebarCollapse.js").read_text(encoding="utf-8")
    styles = (ROOT / "frontend" / "src" / "styles" / "theme-sync.css").read_text(encoding="utf-8")
    view = (ROOT / "frontend" / "src" / "views" / "AppViews.jsx").read_text(encoding="utf-8")
    assert "useSidebarCollapse" in app and "sidebarCollapse.className" in app
    assert "sidebar-topnav" in hook
    assert "--accent" in styles and "--sidebar-bg" in styles and "--card-shadow" in styles
    assert "dashboard-widget-zone" in view
    assert "akys_dashboard_widget_order" in view


def test_approver_can_see_deadline_plan_by_default():
    from backend.enterprise.matrix import DEFAULT_SIDEBAR_MATRIX, _clean_sidebar_rows

    rows = _clean_sidebar_rows(DEFAULT_SIDEBAR_MATRIX)
    deadlines = next(row for row in rows if row["module"] == "deadlines")
    assert deadlines["Onaylayıcı"] is True


def test_permission_matrix_bulk_all_close_has_core_access_guard():
    view = (ROOT / "frontend" / "src" / "views" / "AppViews.jsx").read_text(encoding="utf-8")
    assert "BULK_ALL_CORE_PERMISSIONS" in view
    assert "isBulkAllProtectedPermission" in view
    assert "isBulkAllProtectedSidebarModule" in view
    assert "bulkAllProtectionMessage" in view
    assert "Tümü sekmesindeki toplu kapatma" in view


def test_dashboard_permission_blackout_is_repaired_when_sidebar_dashboard_visible():
    from backend.enterprise.matrix import DEFAULT_PERMISSION_MATRIX, DEFAULT_SIDEBAR_MATRIX, _clean_permission_rows, _clean_sidebar_rows, _restore_dashboard_permission_blackout

    permission_rows = _clean_permission_rows(DEFAULT_PERMISSION_MATRIX)
    sidebar_rows = _clean_sidebar_rows(DEFAULT_SIDEBAR_MATRIX)
    for row in permission_rows:
        if str(row.get("permission", "")).startswith("dashboard."):
            row["Editör / Hazırlayıcı"] = False
    repaired = _restore_dashboard_permission_blackout(permission_rows, sidebar_rows)
    dashboard_rows = [row for row in repaired if str(row.get("permission", "")).startswith("dashboard.")]
    assert any(row["Editör / Hazırlayıcı"] is True for row in dashboard_rows)
    assert next(row for row in repaired if row["permission"] == "dashboard.view")["Editör / Hazırlayıcı"] is True


def test_role_matrix_cleans_auditor_and_unit_coordinator_columns():
    from backend import repositories
    from backend.enterprise.matrix import DEFAULT_PERMISSION_MATRIX, DEFAULT_SIDEBAR_MATRIX, _clean_permission_rows, _clean_sidebar_rows

    permission_rows = _clean_permission_rows(DEFAULT_PERMISSION_MATRIX)
    sidebar_rows = _clean_sidebar_rows(DEFAULT_SIDEBAR_MATRIX)
    assert repositories.READONLY_ROLE == "Denetçi"
    assert all(repositories.UNIT_COORDINATOR_ROLE in row for row in permission_rows)
    assert all(repositories.UNIT_COORDINATOR_ROLE in row for row in sidebar_rows)
    assert all("Denetçi (İzleyici)" not in row for row in permission_rows)
    assert all("Denetçi (İzleyici)" not in row for row in sidebar_rows)


def test_legacy_auditor_matrix_column_is_preserved_as_denetci():
    from backend import repositories
    from backend.enterprise.matrix import DEFAULT_PERMISSION_MATRIX, _clean_permission_rows

    row = next(item for item in DEFAULT_PERMISSION_MATRIX if item["permission"] == "report.import")
    legacy_row = {key: value for key, value in row.items() if key != repositories.READONLY_ROLE}
    legacy_row["Denetçi (İzleyici)"] = True
    cleaned = _clean_permission_rows([legacy_row])
    imported = next(item for item in cleaned if item["permission"] == "report.import")
    assert imported[repositories.READONLY_ROLE] is True
