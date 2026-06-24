from __future__ import annotations
from tests.frontend_helpers import read_frontend_source, read_frontend_styles

import ast
from pathlib import Path

from core.project_paths import find_project_root


ROOT = find_project_root(Path(__file__))
PY_SOURCES = [
    *sorted((ROOT / "backend").glob("*.py")),
    *sorted((ROOT / "backend" / "repos").glob("*.py")),
    *sorted((ROOT / "services").glob("*.py")),
    *sorted((ROOT / "core").glob("*.py")),
]
SOURCE = "\n".join(path.read_text(encoding="utf-8") for path in PY_SOURCES)
FRONTEND = read_frontend_source(ROOT)
AUTH_VIEW = (ROOT / "frontend" / "src" / "views" / "AuthScreens.jsx").read_text(encoding="utf-8")
NAVIGATION = (ROOT / "frontend" / "src" / "config" / "navigation.jsx").read_text(encoding="utf-8")
API = (ROOT / "frontend" / "src" / "api.js").read_text(encoding="utf-8")


def test_web_only_package_shape():
    required = [
        "backend/main.py",
        "backend/repositories.py",
        "backend/reporting.py",
        "services/ai_report_writer.py",
        "frontend/src/main.jsx",
        "frontend/src/api.js",
        "frontend/nginx.conf",
        "frontend/Dockerfile",
        "Dockerfile.api",
        "docker-compose.web.yml",
        "requirements-api.txt",
        ".env.web.example",
        "tools/make_release_zip.ps1",
    ]
    assert all((ROOT / path).exists() for path in required)
    assert not (ROOT / ("app" + ".py")).exists()
    assert not (ROOT / "ui").exists()
    assert not list(ROOT.glob("medek_*.py"))
    assert not (ROOT / ("docker-compose" + ".yml")).exists()
    assert not (ROOT / ("requirements" + ".txt")).exists()


def test_python_sources_compile_and_avoid_high_risk_primitives():
    for src_path in PY_SOURCES:
        compile(src_path.read_text(encoding="utf-8"), str(src_path), "exec")
    for tree in [ast.parse(path.read_text(encoding="utf-8"), filename=str(path)) for path in PY_SOURCES]:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"eval", "exec"}
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert not (node.func.attr == "system" and getattr(node.func.value, "id", "") == "os")
    assert "shell=True" not in SOURCE


def test_fastapi_web_endpoints_are_present():
    assert 'app = FastAPI(title="AKYS API"' in SOURCE
    for route in [
        '"/api/auth/login"',
        '"/api/programs/{program_id}/sections/{section_key}"',
        '"/api/programs/{program_id}/evidence/{evidence_id}/download"',
        '"/api/programs/{program_id}/tables/{table_id}"',
        '"/api/programs/{program_id}/tables/attach"',
        '"/api/programs/{program_id}/report/docx"',
        '"/api/programs/{program_id}/report/pdf"',
        '"/api/programs/{program_id}/report/jobs"',
        '"/api/programs/{program_id}/backup/json"',
        '"/api/programs/{program_id}/backup/restore"',
    ]:
        assert route in SOURCE


def test_evidence_link_preserves_code_and_note():
    assert "class EvidenceLinkPayload" in SOURCE
    assert "code: str = \"\"" in SOURCE
    assert "note: str = \"\"" in SOURCE
    assert 'data.get("code", "")' in SOURCE
    assert 'data.get("note", "")' in SOURCE
    assert "UPDATE evidence SET code=?, note=?" in SOURCE


def test_section_scoped_evidence_and_table_archives():
    assert "role = assert_program_access(username, program_id)" in SOURCE
    assert "if not _section_access_allowed(username, program_id, section_key)" in SOURCE
    assert "assigned_section_keys(username, program_id) if role == EDITOR_ROLE else set()" in SOURCE
    assert "e.section_key IN" in SOURCE
    assert "section_key IN" in SOURCE


def test_admin_only_sensitive_operations_and_settings_access():
    assert "def get_settings_for_user" in SOURCE
    assert "return get_settings_for_user(user[\"username\"], program_id)" in SOURCE
    assert "def backup_payload" in SOURCE
    assert "def system_status" in SOURCE
    assert SOURCE.count("assert_admin(username)") >= 5


def test_empty_database_bootstrap_and_clean_release_tool():
    assert "def init_db" in SOURCE
    assert "MEDEK_BOOTSTRAP_ADMIN_PASSWORD" in SOURCE
    assert (ROOT / "tools" / "make_release_zip.ps1").exists()


def test_frontend_uses_table_attach_and_web_api_base():
    assert "api.attachTable" in FRONTEND
    assert "Seçili tabloyu bu başlığa bağla" in FRONTEND
    assert "linkEvidence" in FRONTEND
    assert 'const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";' in API


def test_first_login_password_change_and_simplified_menu_present():
    assert '"/api/me/change-password"' in SOURCE
    assert "def change_own_password" in SOURCE
    assert "must_change_password" in SOURCE
    assert 'changePassword: (currentPassword, newPassword)' in API
    assert "function ChangePasswordScreen" in AUTH_VIEW
    assert "./views/AuthScreens" in FRONTEND
    assert 'const everyone = ["dashboard", "notifications", "tasks", "entry", "evidence", "tables", "control", "search", "stats", "preview", "export", "deadlineCalendar", "help"]' in NAVIGATION
    assert 'const admin = ["docx", "approval", "programs", "users", "deadlines", "bulk", "settings"]' in NAVIGATION
    assert 'const approver = ["approval", "deadlines"]' in NAVIGATION
    assert "AI Stratejik Özet" not in FRONTEND
    assert "AI ile Akreditasyon Taslağı Oluştur" not in FRONTEND


def test_program_management_uses_tenant_first_selection_flow():
    assert "function selectNewProgramFaculty(schoolName)" in FRONTEND
    assert "function selectAssignmentTenant(tenantId)" in FRONTEND
    assert "programTenantGroups" in FRONTEND
    assert "programUserTenantGroups" in FRONTEND
    assert "newProgramFacultyOptions.map" in FRONTEND
    assert "Kurum (Üniversite)" in FRONTEND
    assert "Kurum / Üniversite" in FRONTEND


def test_enterprise_ops_extensions_present():
    assert "CREATE TABLE IF NOT EXISTS export_jobs" in SOURCE
    assert "def enqueue_export_job" in SOURCE
    assert "BackgroundTasks" in SOURCE
    assert "createExportJob" in API
    assert "Rapor Çıktısı Oluştur" in FRONTEND
    assert "from .repos.users_repo import" in SOURCE
    assert (ROOT / "docker-compose.https.yml").exists()
    assert (ROOT / "Caddyfile").exists()
    assert (ROOT / "tools" / "install_backup_task.ps1").exists()
    assert (ROOT / "tools" / "postgres_migrate.py").exists()


def test_no_turkish_mojibake_in_user_visible_errors():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    backend = (root / "backend" / "main.py").read_text(encoding="utf-8")
    assert "BaÅ" not in backend
    assert "BaÅŸlÄ±k bulunamadÄ±" not in backend
    assert "Başlık bulunamadı" in backend
