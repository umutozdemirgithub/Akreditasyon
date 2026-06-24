from pathlib import Path
from tests.frontend_helpers import read_frontend_source, read_frontend_styles

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
DEPLOYMENT = (ROOT / "backend" / "deployment.py").read_text(encoding="utf-8")
FRONTEND = read_frontend_source(ROOT)
API = (ROOT / "frontend" / "src" / "api.js").read_text(encoding="utf-8")
DOC = (ROOT / "docs" / "DEPLOYMENT_INSTALLER_WIZARD.md").read_text(encoding="utf-8")


def test_deployment_wizard_backend_endpoints_present():
    assert '@app.get("/api/admin/deployment/wizard")' in SOURCE
    assert '@app.post("/api/admin/deployment/smoke")' in SOURCE
    assert "deployment_wizard_payload" in SOURCE
    assert "deployment_smoke_payload" in SOURCE


def test_deployment_wizard_checks_cover_production_risks():
    for needle in [
        "API secret gücü",
        "CORS origin listesi",
        "Trusted host listesi",
        "Veritabanı bağlantısı",
        "Veri/kanıt klasörü yazma izni",
        "SMTP yapılandırması",
        "Ollama/AI bağlantısı",
        "Export job backend",
    ]:
        assert needle in DEPLOYMENT
    assert "_mask_secret" in DEPLOYMENT
    assert "MEDEK_DATABASE_URL" in DEPLOYMENT


def test_deployment_wizard_frontend_and_docs_present():
    assert "Kurulum Sihirbazı" in FRONTEND
    assert "Smoke Test Çalıştır" in FRONTEND
    assert "Önerilen .env iskeleti" in FRONTEND
    assert "deploymentWizard:" in API
    assert "deploymentSmoke:" in API
    assert "GET  /api/admin/deployment/wizard" in DOC
