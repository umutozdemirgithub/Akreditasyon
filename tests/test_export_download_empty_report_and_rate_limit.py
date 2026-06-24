from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = (ROOT / "frontend" / "src" / "views" / "AppViews.jsx").read_text(encoding="utf-8")
APP = (ROOT / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
RATE_LIMIT = (ROOT / "backend" / "rate_limit.py").read_text(encoding="utf-8")


def test_export_view_restores_direct_download_and_allows_empty_report():
    assert "DOCX Hemen İndir" in FRONTEND
    assert "PDF Hemen İndir" in FRONTEND
    assert "api.reportDocx(programId, true)" in FRONTEND
    assert "api.reportPdf(programId, true)" in FRONTEND
    assert "Rapor metni boş veya bloklayıcı eksik olsa bile DOCX/PDF üretimi engellenmez" in FRONTEND


def test_export_jobs_force_final_outputs_and_poll_safely():
    assert "const shouldForce = finalExport ? true : Boolean(force);" in FRONTEND
    assert "Rapor boş olsa bile dosya üretilecek" in FRONTEND
    assert "window.setInterval(() =>" in FRONTEND
    assert ", 7000);" in FRONTEND


def test_rate_limit_does_not_throttle_export_status_polling_as_file_generation():
    assert "report_job_status_read" in RATE_LIMIT
    assert "report_file_generation" in RATE_LIMIT
    assert "path.endswith(\"/report/preflight\")" in RATE_LIMIT
    assert "or path.endswith(\"/report/jobs\")" in RATE_LIMIT
    assert "not path.endswith(\"/download\")" in RATE_LIMIT
    assert 'MEDEK_RATE_LIMIT_GENERAL_PER_MINUTE' in RATE_LIMIT and '"300"' in RATE_LIMIT
    assert 'MEDEK_RATE_LIMIT_EXPORT_PER_MINUTE' in RATE_LIMIT and '"30"' in RATE_LIMIT


def test_global_error_alert_can_be_cleared_after_successful_refresh():
    assert "function showMessage" in APP
    assert "setError(\"\");\n    setMessage(text);" in APP
    assert "async function reloadAll()" in APP
    assert "resetMessages();\n    try" in APP
    assert "onClick={() => setError(\"\")}" in APP
