from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "frontend" / "src" / "App.jsx").read_text(encoding="utf-8")
VIEWS = (ROOT / "frontend" / "src" / "views" / "AppViews.jsx").read_text(encoding="utf-8")
API = (ROOT / "frontend" / "src" / "api.js").read_text(encoding="utf-8")
SCHEMAS = (ROOT / "backend" / "schemas.py").read_text(encoding="utf-8")
REPOS = (ROOT / "backend" / "repositories.py").read_text(encoding="utf-8")
DOC = (ROOT / "docs" / "AUTOSAVE_DRAFT_GUARD.md").read_text(encoding="utf-8")


def test_frontend_has_debounced_autosave_and_local_draft_guard():
    assert "useRef" in APP
    assert "autosaveTimerRef" in APP
    assert "medek:auto-draft" in APP
    assert "window.localStorage.setItem" in APP
    assert "window.localStorage.removeItem" in APP
    assert "}, 25000);" in APP
    assert "saveSection({ silent: true, source: \"autosave\"" in APP
    assert "beforeunload" in APP


def test_autosave_state_is_visible_in_section_editor():
    assert "autosaveState={autosaveState}" in APP
    assert "autosave-status-bar" in VIEWS
    assert "Otomatik kaydediliyor" in VIEWS
    assert "Otomatik kayıt bekliyor" in VIEWS
    assert "Otomatik kaydedildi" in VIEWS
    assert "25 saniye" in VIEWS


def test_api_and_backend_mark_autosave_separately():
    assert "is_autosave: Boolean(options.autosave)" in API
    assert "is_autosave: bool = False" in SCHEMAS
    assert "is_autosave = bool(payload.get(\"is_autosave\"))" in REPOS
    assert "Otomatik taslak kaydı" in REPOS
    assert "Başlık otomatik kaydedildi" in REPOS
    assert "Manuel başlık kaydı" in REPOS


def test_autosave_documentation_exists():
    assert "Otomatik Taslak Kaydı" in DOC
    assert "localStorage" in DOC
    assert "25 saniye" in DOC
    assert "is_autosave=true" in DOC
