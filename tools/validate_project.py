from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.project_paths import find_project_root


ROOT = find_project_root()
PY_SOURCES = [
    *sorted((ROOT / "backend").glob("*.py")),
    *sorted((ROOT / "backend" / "enterprise").glob("*.py")),
    *sorted((ROOT / "backend" / "repos").glob("*.py")),
    *sorted((ROOT / "services").glob("*.py")),
    *sorted((ROOT / "core").glob("*.py")),
    *sorted((ROOT / "tools").glob("*.py")),
]
SCAN_SOURCES = [
    *sorted((ROOT / "backend").glob("*.py")),
    *sorted((ROOT / "backend" / "enterprise").glob("*.py")),
    *sorted((ROOT / "backend" / "repos").glob("*.py")),
    *sorted((ROOT / "services").glob("*.py")),
    *sorted((ROOT / "core").glob("*.py")),
]


def run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    rc, out = run([sys.executable, "-m", "py_compile", *[str(p) for p in PY_SOURCES]])
    checks.append(("python module compile", rc == 0, out.strip()))

    source = "\n".join(p.read_text(encoding="utf-8") for p in PY_SOURCES)
    scan_source = "\n".join(p.read_text(encoding="utf-8") for p in SCAN_SOURCES)
    frontend_paths = [
        *sorted((ROOT / "frontend" / "src").rglob("*.jsx")),
        *sorted((ROOT / "frontend" / "src").rglob("*.js")),
    ]
    frontend_source = "\n".join(path.read_text(encoding="utf-8") for path in frontend_paths)
    css_paths = [
        ROOT / "frontend" / "src" / "styles.css",
        *sorted((ROOT / "frontend" / "src" / "styles").glob("*.css")),
    ]
    frontend_css_source = "\n".join(path.read_text(encoding="utf-8") for path in css_paths if path.exists())
    api_source = (ROOT / "frontend" / "src" / "api.js").read_text(encoding="utf-8")

    try:
        dupes_by_file: dict[str, list[str]] = {}
        for src_path in PY_SOURCES:
            tree = ast.parse(src_path.read_text(encoding="utf-8"), filename=str(src_path))
            file_funcs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            file_dupes = sorted({f for f in file_funcs if file_funcs.count(f) > 1})
            if file_dupes:
                dupes_by_file[src_path.relative_to(ROOT).as_posix()] = file_dupes
        checks.append(("AST parse + duplicate function names", not dupes_by_file, f"duplicates={dupes_by_file}"))
    except Exception as exc:
        checks.append(("AST parse", False, repr(exc)))

    forbidden = ["eval(", "exec(", "pickle.loads", "os.system(", "subprocess.Popen", "shell=True"]
    hits = [x for x in forbidden if x in scan_source + frontend_source + api_source]
    checks.append(("dangerous primitive scan", not hits, f"hits={hits}"))

    required_files = [
        "backend/main.py",
        "backend/repositories.py",
        "backend/security.py",
        "backend/file_security.py",
        "backend/reporting.py",
        "services/ai_report_writer.py",
        "services/full_report_generator.py",
        "frontend/package.json",
        "frontend/src/main.jsx",
        "frontend/src/App.jsx",
        "frontend/src/views/AppViews.jsx",
        "frontend/src/constants/appConstants.js",
        "frontend/src/api.js",
        "frontend/nginx.conf",
        "frontend/Dockerfile",
        "Dockerfile.api",
        "docker-compose.web.yml",
        "docker-compose.queue.yml",
        ".env.web.example",
        "requirements-api.txt",
        "backend/export_jobs.py",
        "backend/worker.py",
        "backend/notifications.py",
        "backend/insights.py",
        "docs/EMAIL_NOTIFICATIONS.md",
        "frontend/src/config/navigation.jsx",
        "frontend/src/components/DataTable.jsx",
        "frontend/src/components/ErrorBoundary.jsx",
        "frontend/src/utils.js",
        "docs/JOB_QUEUE.md",
        "tools/make_release_zip.ps1",
        "tools/postgres_migrate.py",
        "tools/postgres_cutover_check.py",
        "tools/postgres_schema.sql",
        "backend/deployment.py",
        "docs/DEPLOYMENT_INSTALLER_WIZARD.md",
    ]
    missing = [path for path in required_files if not (ROOT / path).exists()]
    checks.append(("web runtime files", not missing, f"missing={missing}"))

    legacy_leftovers = [
        "app" + ".py",
        "requirements" + ".txt",
        "Dockerfile",
        "docker-compose" + ".yml",
        "ui",
        "medek_catalog.py",
        "medek_config.py",
        "medek_preview.py",
        "medek_styles.py",
    ]
    leftovers = [path for path in legacy_leftovers if (ROOT / path).exists()]
    checks.append(("legacy local files removed", not leftovers, f"leftovers={leftovers}"))

    checks.append(("FastAPI app present", 'app = FastAPI(title="AKYS API"' in source, ""))
    checks.append(("evidence link passes code/note", 'data.get("code", "")' in source and 'data.get("note", "")' in source, ""))
    checks.append(("table attach used in frontend", "api.attachTable" in frontend_source, ""))
    checks.append(("section-scoped archive lists", "assigned_section_keys(username, program_id) if role == EDITOR_ROLE" in source, ""))
    checks.append(("admin-only backup/system", "def backup_payload" in source and "def system_status" in source and "assert_admin(username)" in source, ""))
    checks.append(("PDF conversion support", "def convert_docx_to_pdf" in source and "libreoffice" in source, ""))
    checks.append(("empty database bootstrap", "def init_db" in source and "MEDEK_BOOTSTRAP_ADMIN_PASSWORD" in source, ""))
    checks.append(("clean release packaging", "make_release_zip.ps1" in "\n".join(p.as_posix() for p in (ROOT / "tools").glob("*")), ""))

    checks.append(("export job backend files", "def enqueue_export_job" in source and "def job_system_status" in source and "MEDEK_JOB_BACKEND" in source, ""))
    checks.append(("Redis/RQ queue artifacts", (ROOT / "docker-compose.queue.yml").exists() and "rq" in (ROOT / "requirements-api.txt").read_text(encoding="utf-8") and "akys-worker" in (ROOT / "docker-compose.queue.yml").read_text(encoding="utf-8"), ""))
    checks.append(("background export endpoints", '@app.post("/api/programs/{program_id}/report/jobs")' in source and "report_job_download" in source and "createExportJob" in api_source, ""))
    checks.append(("queue documentation", "Redis + RQ" in (ROOT / "docs" / "JOB_QUEUE.md").read_text(encoding="utf-8") and "Nginx mi Caddy mi" in (ROOT / "docs" / "HTTPS_AND_INTRANET.md").read_text(encoding="utf-8"), ""))
    checks.append(("frontend modular components", (ROOT / "frontend" / "src" / "App.jsx").exists() and (ROOT / "frontend" / "src" / "views" / "AppViews.jsx").exists() and (ROOT / "frontend" / "src" / "constants" / "appConstants.js").exists() and "config/navigation.jsx" in frontend_source and "components/DataTable.jsx" in frontend_source and (ROOT / "frontend" / "src" / "views" / "AuthScreens.jsx").exists(), ""))
    
    data_table_source = (ROOT / "frontend" / "src" / "components" / "DataTable.jsx").read_text(encoding="utf-8")
    checks.append(("frontend runtime safety", 'ErrorBoundary' in frontend_source and 'asArray' in frontend_source and 'safeRows' in data_table_source, ""))
    checks.append(("React import in JSX components", 'import React from "react"' in data_table_source, "DataTable.jsx must import React because Vite builds without a project-level automatic JSX runtime config."))
    checks.append(("dashboard report directory groups", "const reportDirectoryGroups = asArray(stats?.report_groups).length" in frontend_source and "Rapor Bölümleri / Ana Ölçütler" in frontend_source, "Dashboard main cards must use complete report_groups first so A/B/EK blocks from Report Directory are not missing."))

    notifications_source = (ROOT / "backend" / "notifications.py").read_text(encoding="utf-8")
    checks.append(("email notification backend", "def notify_approval_event" in notifications_source and "def notify_deadlines_updated" in notifications_source and "def notify_export_ready" in notifications_source and "notification_events" in source, ""))
    checks.append(("email notification endpoints", '@app.get("/api/admin/notifications")' in source and '@app.get("/api/admin/mail/status")' in source and '@app.get("/api/admin/mail/settings")' in source and '@app.post("/api/admin/mail/test")' in source and "notifications:" in api_source and "mailStatus:" in api_source and "mailSettings:" in api_source and "testMail:" in api_source, ""))
    checks.append(("SMTP settings UI", "SMTP Sunucu" in frontend_source and "Test Mail Gönder" in frontend_source and "E-posta Ayarlarını Kaydet" in frontend_source, ""))
    checks.append(("SMTP password encryption", "Fernet" in notifications_source and "_encrypt_secret" in notifications_source and "smtp_password_configured" in notifications_source, ""))
    checks.append(("SMTP env example", "MEDEK_MAIL_ENABLED" in (ROOT / ".env.web.example").read_text(encoding="utf-8") and "MEDEK_SMTP_HOST" in (ROOT / ".env.web.example").read_text(encoding="utf-8"), ""))
    checks.append(("email notification documentation", "E-posta Bildirimleri" in (ROOT / "docs" / "EMAIL_NOTIFICATIONS.md").read_text(encoding="utf-8") and "Onaya gönderme" in (ROOT / "docs" / "EMAIL_NOTIFICATIONS.md").read_text(encoding="utf-8"), ""))
    checks.append(("program hard delete workflow", '@app.delete("/api/admin/programs/{program_id}")' in source and "def delete_program_admin" in source and "deleteProgram:" in api_source and "Program kalıcı olarak silindi." in frontend_source, ""))
    checks.append(("editor-only approval submission", ("if role != EDITOR_ROLE" in source or '"submit"' in source and "_section_permission" in source) and ('const canSend = user.role === "Editör / Hazırlayıcı"' in frontend_source or "const canSend = Boolean(actionPerms.submit)" in frontend_source) and "hasUnsavedSectionChanges" in frontend_source, ""))
    checks.append(("user-facing export copy", "Rapor Çıktısı Oluştur" in frontend_source and "DOCX veya PDF çıktısını oluşturup hazır olduğunda" in frontend_source and "API isteğini kilitlemeden" not in frontend_source, ""))
    checks.append(("comprehensive program authority note", "Program bazlı yetkilendirme nasıl çalışır?" in frontend_source and "Rol Yetki Matrisi" in frontend_source and "Mevcut Program Atamaları" in frontend_source, ""))
    insights_source = (ROOT / "backend" / "insights.py").read_text(encoding="utf-8")
    navigation_source = (ROOT / "frontend" / "src" / "config" / "navigation.jsx").read_text(encoding="utf-8")
    checks.append(("enterprise insight center", "def program_insights" in insights_source and "Görev & Eksik Analizi" in navigation_source and "Bildirim Merkezi" in navigation_source and "program_insights_endpoint" in source and "insights:" in api_source, ""))
    checks.append(("notification inbox/read API", "def notification_inbox" in insights_source and "notification_reads" in source and "notificationInbox" in api_source and "markNotificationsRead" in api_source, ""))
    checks.append(("deadline calendar and help modules", "deadlineCalendar" in navigation_source and "Yardım & Kullanım" in navigation_source and "DeadlineCalendarView" in frontend_source and "HelpView" in frontend_source, ""))
    checks.append(("advanced bulk operations", "def bulk_update_advanced" in source and '@app.put("/api/programs/{program_id}/bulk/advanced")' in source and "bulkAdvanced" in api_source and "Toplu son teslim tarihi" in frontend_source, ""))
    checks.append(("sidebar visibility matrix", "DEFAULT_SIDEBAR_MATRIX" in source and "sidebar_matrix_public" in source and "visible_sidebar_modules_for_role" in source and "Sidebar Görünürlük Matrisi" in frontend_source and "sidebar_rows" in api_source + frontend_source, ""))
    checks.append(("role based detailed help manual", "role_order" in insights_source and "daily_focus" in insights_source and "Rol bazlı ayrıntılı kullanım kılavuzu" in frontend_source and "workflow-grid" in frontend_css_source, ""))

    checks.append(("enterprise feature modules", (ROOT / "backend" / "enterprise" / "matrix.py").exists() and (ROOT / "backend" / "enterprise" / "timeline.py").exists() and "from .enterprise.matrix import" in source, ""))
    matrix_source = (ROOT / "backend" / "enterprise" / "matrix.py").read_text(encoding="utf-8")
    checks.append(("granular permission catalogue", "program.assign_users" in matrix_source and "section.version_view" in matrix_source and "notification.settings" in matrix_source and matrix_source.count('"permission"') >= 35, ""))
    checks.append(("soft delete extended", "Kanıt arşivlendi" in (ROOT / "backend" / "repositories.py").read_text(encoding="utf-8") and "Tablo arşivlendi" in (ROOT / "backend" / "repositories.py").read_text(encoding="utf-8") and "Kullanıcı arşivlendi" in (ROOT / "backend" / "repositories.py").read_text(encoding="utf-8"), ""))
    checks.append(("notification polling UI", "notificationUnreadCount" in frontend_source and "window.setInterval(poll, 30000)" in frontend_source and "nav-badge" in frontend_source, ""))
    checks.append(("side by side matrix UI", "matrix-grid" in frontend_source and "matrix-summary" in frontend_source and ".matrix-grid" in frontend_css_source, ""))
    tenancy_source = (ROOT / "backend" / "tenancy.py").read_text(encoding="utf-8")
    checks.append(("multi-tenant backend isolation", "CREATE TABLE IF NOT EXISTS tenants" in source and "tenant_scope" in source and "ensure_program_tenant_access" in source and "def list_tenants_admin" in tenancy_source, ""))
    checks.append(("multi-tenant admin endpoints", '@app.get("/api/admin/tenants")' in source and '@app.get("/api/admin/tenant-faculties")' in source and "tenants:" in api_source and "tenantFaculties:" in api_source, ""))
    checks.append(("academic catalog importer", "import_academic_catalog_admin" in source and "discover_academic_catalog_from_yokatlas" in source and "importTenantAcademicCatalog" in api_source and "YÖK Atlas’tan Akademik Yapıyı Bul" in frontend_source, ""))
    checks.append(("compliance audit endpoints", '@app.get("/api/programs/{program_id}/compliance")' in source and '@app.get("/api/programs/{program_id}/compliance/docx")' in source, ""))
    checks.append(("multi-tenant admin UI", "Kurum / Fakülte İzolasyonu" in frontend_source and "Tenant kapsamı" in frontend_source and "tenant_id" in frontend_source, ""))
    checks.append(("multi-tenant documentation", (ROOT / "docs" / "MULTI_TENANT_ISOLATION.md").exists() and "tenant-aware" in (ROOT / "docs" / "MULTI_TENANT_ISOLATION.md").read_text(encoding="utf-8"), ""))

    db_postgres_source = (ROOT / "backend" / "db_postgres.py").read_text(encoding="utf-8")
    postgres_schema_source = (ROOT / "tools" / "postgres_schema.sql").read_text(encoding="utf-8")
    compose_source = (ROOT / "docker-compose.web.yml").read_text(encoding="utf-8")
    checks.append(("PostgreSQL runtime backend", "MEDEK_DB_BACKEND" in source and "connect_postgres" in source and "translate_sqlite_to_postgres" in db_postgres_source, ""))
    checks.append(("PostgreSQL production compose", "akys-postgres" in compose_source and "service_healthy" in compose_source and "MEDEK_DATABASE_URL" in compose_source, ""))
    checks.append(("tenant-aware PostgreSQL schema", "idx_programs_tenant_active" in postgres_schema_source and "idx_notifications_tenant_status" in postgres_schema_source and "CREATE TABLE IF NOT EXISTS workflow_runs" in postgres_schema_source, ""))
    checks.append(("PostgreSQL cutover tooling", (ROOT / "tools" / "postgres_migrate.py").exists() and (ROOT / "tools" / "postgres_cutover_check.py").exists() and "MIGRATION_ORDER" in (ROOT / "services" / "postgres_migration.py").read_text(encoding="utf-8"), ""))

    deployment_source = (ROOT / "backend" / "deployment.py").read_text(encoding="utf-8")
    checks.append(("deployment installer wizard backend", '@app.get("/api/admin/deployment/wizard")' in source and '@app.post("/api/admin/deployment/smoke")' in source and "def deployment_wizard_payload" in deployment_source and "def deployment_smoke_payload" in deployment_source, ""))
    checks.append(("deployment installer wizard UI", "Kurulum Sihirbazı" in frontend_source and "Smoke Test Çalıştır" in frontend_source and "deploymentWizard:" in api_source and "deploymentSmoke:" in api_source, ""))
    checks.append(("deployment installer wizard documentation", (ROOT / "docs" / "DEPLOYMENT_INSTALLER_WIZARD.md").exists() and "MEDEK_APP_BASE_URL" in (ROOT / "docs" / "DEPLOYMENT_INSTALLER_WIZARD.md").read_text(encoding="utf-8"), ""))

    width = max(len(name) for name, _, _ in checks)
    failed = 0
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name:<{width}} {detail}")
        failed += 0 if ok else 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
