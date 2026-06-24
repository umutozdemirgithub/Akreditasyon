from pathlib import Path
from tests.frontend_helpers import read_frontend_source, read_frontend_styles

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_role_based_help_backend_has_detailed_guides():
    source = read("backend/insights.py")
    for role in ["Admin", "Editör / Hazırlayıcı", "Onaylayıcı", "Denetçi"]:
        assert role in source
    for key in ["daily_focus", "workflow", "modules", "checklist", "warnings", "common_rules"]:
        assert key in source
    assert "Başlığı kaydet" in source
    assert "Onaylayıcı rolünde onaya gönderme yapılmaz" in source
    assert "Yetki Matrisi" in source


def test_role_based_help_frontend_is_role_specific():
    source = read_frontend_source(ROOT)
    styles = read_frontend_styles(ROOT)
    assert "Rol bazlı ayrıntılı kullanım kılavuzu" in source
    assert "Rolüne Özel Kılavuz" in source
    assert "Bu sayfa yalnızca aktif rolüne ait" in source
    assert "roleOrder.map" not in source
    assert "Günlük odak" in source
    assert "Adım Adım" in source
    assert "Modül Rehberi" in source
    assert "Kontrol Listesi" in source
    assert "Sık yapılan hata ve uyarılar" in source
    for css_class in ["help-role-grid", "workflow-grid", "module-guide-row", "warning-card", "role-locked-help"]:
        assert css_class in styles
