
from pathlib import Path
from tests.frontend_helpers import read_frontend_source, read_frontend_styles

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_enterprise_features_are_modularized():
    facade = read("backend/enterprise_features.py")
    assert "from .enterprise.matrix import" in facade
    assert "from .enterprise.recovery import" in facade
    assert (ROOT / "backend/enterprise/matrix.py").exists()
    assert (ROOT / "backend/enterprise/timeline.py").exists()


def test_permission_matrix_is_more_granular():
    matrix = read("backend/enterprise/matrix.py")
    assert "program.assign_users" in matrix
    assert "section.version_view" in matrix
    assert "evidence.upload" in matrix
    assert "table.delete" in matrix
    assert "notification.settings" in matrix
    assert matrix.count('"permission"') >= 35


def test_soft_delete_extended_to_evidence_tables_users():
    db = read("backend/db.py")
    repo = read("backend/repositories.py")
    assert '_ensure_column(conn, "evidence", "deleted_at"' in db
    assert '_ensure_column(conn, "data_tables", "deleted_at"' in db
    assert '_ensure_column(conn, "users", "deleted_at"' in db
    assert "Kanıt arşivlendi" in repo
    assert "Tablo arşivlendi" in repo
    assert "Kullanıcı arşivlendi" in repo


def test_sidebar_and_permission_matrices_are_side_by_side_and_polled():
    main = read_frontend_source(ROOT)
    css = read_frontend_styles(ROOT)
    assert "notificationUnreadCount" in main
    assert "window.setInterval(poll, 30000)" in main
    assert "matrix-grid" in main
    assert ".matrix-grid" in css
