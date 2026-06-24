from pathlib import Path
from tests.frontend_helpers import read_frontend_source, read_frontend_styles

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_insight_backend_and_endpoints_exist():
    insights = read("backend/insights.py")
    main = read("backend/main.py")
    assert "def program_insights" in insights
    assert "def notification_inbox" in insights
    assert "def mark_notifications_read" in insights
    assert '@app.get("/api/programs/{program_id}/insights")' in main
    assert '@app.get("/api/programs/{program_id}/notifications/inbox")' in main
    assert '@app.put("/api/programs/{program_id}/notifications/read")' in main


def test_productivity_modules_are_in_navigation_and_frontend():
    nav = read("frontend/src/config/navigation.jsx")
    frontend = read_frontend_source(ROOT)
    api = read("frontend/src/api.js")
    assert "Bildirim Merkezi" in nav
    assert "Görev & Eksik Analizi" in nav
    assert "Teslim Takvimi" in nav
    assert "Yardım & Kullanım" in nav
    assert "NotificationCenterView" in frontend
    assert "TasksAndGapsView" in frontend
    assert "DeadlineCalendarView" in frontend
    assert "HelpView" in frontend
    assert "notificationInbox" in api
    assert "markNotificationsRead" in api
    assert "insights:" in api


def test_advanced_bulk_operations_are_wired():
    repo = read("backend/repositories.py")
    main = read("backend/main.py")
    api = read("frontend/src/api.js")
    frontend = read_frontend_source(ROOT)
    assert "def bulk_update_advanced" in repo
    assert '@app.put("/api/programs/{program_id}/bulk/advanced")' in main
    assert "bulkAdvanced" in api
    assert "Toplu son teslim tarihi" in frontend
