from pathlib import Path

from backend.enterprise.matrix import DEFAULT_PERMISSION_MATRIX


def test_premium_evidence_and_table_permissions_are_catalogued():
    permissions = {row["permission"] for row in DEFAULT_PERMISSION_MATRIX}
    assert "evidence.premium.view" in permissions
    assert "evidence.ai_coach.view" in permissions
    assert "evidence.bulk_manage" in permissions
    assert "table.premium.view" in permissions
    assert "table.ai_coach.view" in permissions
    assert "table.bulk_manage" in permissions


def test_premium_asset_endpoints_and_frontend_clients_exist():
    main = Path("backend/main.py").read_text(encoding="utf-8")
    api = Path("frontend/src/api.js").read_text(encoding="utf-8")
    views = Path("frontend/src/views/AppViews.jsx").read_text(encoding="utf-8")
    assert '/evidence/studio' in main
    assert '/tables/studio' in main
    assert 'evidenceStudio' in api
    assert 'tablesStudio' in api
    assert 'Premium Kanıt Arşivi' in views
    assert 'Premium Tablo Yönetimi' in views
