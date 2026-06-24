from core.project_paths import find_project_root
from tests.frontend_helpers import read_frontend_source, read_frontend_styles

ROOT = find_project_root()


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_program_delete_endpoint_and_frontend_action_exist():
    main = read("backend/main.py")
    repos = read("backend/repositories.py")
    api = read("frontend/src/api.js")
    frontend = read_frontend_source(ROOT)

    assert '@app.delete("/api/admin/programs/{program_id}")' in main
    assert "def delete_program_admin" in repos
    assert '"Program silindi"' in repos
    assert "deleteProgram:" in api
    assert "Program arşive alındı." in frontend
    assert "Geri Yükleme ekranından tekrar aktif edilebilir" in frontend
    assert "programı ve bu programa bağlı başlık, kanıt, tablo, onay, çıktı ve yetki kayıtları kalıcı olarak silinsin mi" not in frontend


def test_approval_send_is_editor_only_and_requires_saved_frontend_state():
    repos = read("backend/repositories.py")
    frontend = read_frontend_source(ROOT)

    assert "if role != EDITOR_ROLE" in repos
    assert "Onaya gönderme işlemi yalnızca editör rolüyle yapılabilir" in repos
    assert "const hasUnsavedSectionChanges" in frontend
    assert "Onaya göndermeden önce Rapor Dizini ekranında 'Bu Başlığı Kaydet'" in frontend
    assert "const canSend = user.role === \"Editör / Hazırlayıcı\"" in frontend
    assert '["Admin", "Editör / Hazırlayıcı"].includes(user.role)' not in frontend


def test_preview_copy_and_program_authority_note_are_user_facing():
    frontend = read_frontend_source(ROOT)

    assert "Rapor Çıktısı Oluştur" in frontend
    assert "DOCX veya PDF çıktısını oluşturup hazır olduğunda aşağıdan indirebilirsiniz." in frontend
    assert "DOCX/PDF üretimi artık API isteğini kilitlemeden" not in frontend
    assert "Program bazlı yetkilendirme nasıl çalışır?" in frontend
    assert "Rol Yetki Matrisi" in frontend
    assert "Mevcut Program Atamaları" in frontend
