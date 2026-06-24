from core.project_paths import find_project_root
from tests.frontend_helpers import read_frontend_source, read_frontend_styles

ROOT = find_project_root()


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_email_notification_backend_artifacts_exist():
    config = read("backend/config.py")
    db = read("backend/db.py")
    notifications = read("backend/notifications.py")
    main = read("backend/main.py")
    export_jobs = read("backend/export_jobs.py")

    assert "MEDEK_MAIL_ENABLED" in config
    assert "MEDEK_SMTP_HOST" in config
    assert "CREATE TABLE IF NOT EXISTS notification_events" in db
    assert "def notify_approval_event" in notifications
    assert "def notify_deadlines_updated" in notifications
    assert "def notify_program_assignment" in notifications
    assert "def notify_export_ready" in notifications
    assert '@app.get("/api/admin/notifications")' in main
    assert '@app.get("/api/admin/mail/status")' in main
    assert '@app.get("/api/admin/mail/settings")' in main
    assert '@app.put("/api/admin/mail/settings")' in main
    assert '@app.post("/api/admin/mail/test")' in main
    assert "notify_export_ready" in export_jobs


def test_email_notification_events_are_wired_to_workflows():
    main = read("backend/main.py")
    assert "notify_approval_event" in main
    assert "notify_deadlines_updated" in main
    assert "notify_program_assignment" in main
    assert "notify_user_saved" in main
    assert "background_tasks: BackgroundTasks" in main


def test_email_notification_frontend_and_docs_present():
    api = read("frontend/src/api.js")
    main = read_frontend_source(ROOT)
    env_example = read(".env.web.example")
    doc = read("docs/EMAIL_NOTIFICATIONS.md")
    validate = read("tools/validate_project.py")

    assert "notifications:" in api
    assert "mailStatus:" in api
    assert "mailSettings:" in api
    assert "saveMailSettings:" in api
    assert "testMail:" in api
    assert "E-posta Bildirimleri" in main
    assert "SMTP Sunucu" in main
    assert "Test Mail Gönder" in main
    assert "MEDEK_MAIL_ENABLED=false" in env_example
    assert "MEDEK_SMTP_HOST" in env_example
    assert "Onaya gönderme" in doc
    assert "email notification backend" in validate


def test_email_settings_are_encrypted_and_ui_editable():
    notifications = read("backend/notifications.py")
    schemas = read("backend/schemas.py")
    docs = read("docs/EMAIL_NOTIFICATIONS.md")

    assert "class MailSettingsPayload" in schemas
    assert "class MailTestPayload" in schemas
    assert "Fernet" in notifications
    assert "_encrypt_secret" in notifications
    assert "smtp_password_configured" in notifications
    assert "Yönetim ekranından SMTP ayarı" in docs
    assert "Test Mail Gönder" in docs
