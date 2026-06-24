from core.project_paths import find_project_root
from tests.frontend_helpers import read_frontend_source, read_frontend_styles

ROOT = find_project_root()


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_redis_rq_queue_artifacts_exist():
    compose = read("docker-compose.queue.yml")
    requirements = read("requirements-api.txt")
    export_jobs = read("backend/export_jobs.py")
    worker = read("backend/worker.py")
    docs = read("docs/JOB_QUEUE.md")

    assert "akys-redis" in compose
    assert "akys-worker" in compose
    assert "MEDEK_JOB_BACKEND=rq" in compose
    assert "redis>=5.0" in requirements
    assert "rq>=1.16" in requirements
    assert "def queue_backend" in export_jobs
    assert "queue.enqueue" in export_jobs
    assert "Worker([MEDEK_RQ_QUEUE]" in worker
    assert "Redis + RQ" in docs


def test_nginx_caddy_roles_documented():
    doc = read("docs/HTTPS_AND_INTRANET.md")
    assert "Nginx mi Caddy mi" in doc
    assert "Nginx'in önünde" in doc
    assert "Varsayılan tercih" in doc


def test_frontend_modularity_artifacts_exist():
    main = read_frontend_source(ROOT)
    nav = read("frontend/src/config/navigation.jsx")
    table = read("frontend/src/components/DataTable.jsx")
    assert 'config/navigation.jsx' in main
    assert 'components/DataTable.jsx' in main
    assert "export function modulesForRole" in nav
    assert "Rapor Dışa Aktar" in nav
    assert "export function DataTable" in table


def test_validate_project_covers_export_jobs():
    validate = read("tools/validate_project.py")
    assert "export job backend files" in validate
    assert "Redis/RQ queue artifacts" in validate
    assert "background export endpoints" in validate

def test_frontend_runtime_safety_guards_present():
    main = read_frontend_source(ROOT)
    data_table = read("frontend/src/components/DataTable.jsx")
    assert 'components/ErrorBoundary.jsx' in main
    assert 'utils.js' in main
    assert "<ErrorBoundary resetKey={activeModule}" in main
    assert "safeRows" in data_table
    assert "Array.isArray(rows)" in data_table


def test_datatable_imports_react_for_runtime_jsx_safety():
    data_table = read("frontend/src/components/DataTable.jsx")
    assert 'import React from "react"' in data_table
    assert "export function DataTable" in data_table


def test_dashboard_uses_complete_report_directory_groups_for_main_cards():
    main = read_frontend_source(ROOT)
    assert "const reportDirectoryGroups = asArray(stats?.report_groups).length" in main
    assert "const criteria = reportDirectoryGroups.length ? reportDirectoryGroups : measureCriteriaFallback" in main
    assert "Rapor Bölümleri / Ana Ölçütler" in main
    assert "stats?.measure_criteria?.length ? stats.measure_criteria" not in main
