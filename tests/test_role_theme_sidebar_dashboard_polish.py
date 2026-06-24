from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_program_purge_uses_dedicated_permission_gate():
    recovery = read("backend/enterprise/recovery.py")
    assert 'def purge_program_admin' in recovery
    assert 'assert_operation_permission(username, "program.purge")' in recovery


def test_appearance_payload_exposes_full_css_variable_theme_tokens():
    appearance = read("backend/appearance.py")
    for token in ["--accent", "--sidebar-bg", "--card-bg", "--text-primary", "--workspace-bg"]:
        assert token in appearance
    assert '"css_variables": css_vars' in appearance
    assert "THEME_TOKEN_OVERRIDES" in appearance


def test_sidebar_and_dashboard_premium_polish_is_wired():
    app = read("frontend/src/App.jsx")
    views = read("frontend/src/views/AppViews.jsx")
    styles = read("frontend/src/styles.css")
    assert "useTenantTheme" in app and "TenantThemeProvider" in app
    assert "QuickSearchOverlay" in app
    assert "akys_sidebar_collapsed" in app
    assert "akys_favorite_modules" in app
    assert "TodayFocusWidget" in views
    assert "CriteriaHeatmapWidget" in views
    assert "DeadlineActivityWidget" in views
    assert "QualityTrendWidget" in views
    assert '@import "./styles/premium-theme-engine.css";' in styles
