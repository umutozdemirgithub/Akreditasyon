from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_compose_uses_akreditasyon_root_bind_mounts():
    compose = (ROOT / "docker-compose.web.yml").read_text(encoding="utf-8")
    assert "${AKREDITASYON_ROOT:-./Akreditasyon}/00_canli_veri/postgresql:/var/lib/postgresql/data" in compose
    assert "${AKREDITASYON_ROOT:-./Akreditasyon}/00_canli_veri/medek_data:/app/medek_data" in compose
    assert "medek_pg_data:/var/lib/postgresql/data" not in compose


def test_start_scripts_prepare_desktop_akreditasyon_storage():
    ps1 = (ROOT / "tools" / "start_web_stack.ps1").read_text(encoding="utf-8")
    sh = (ROOT / "tools" / "start_web_stack.sh").read_text(encoding="utf-8")
    for text in (ps1, sh):
        assert "Akreditasyon" in text
        assert "00_canli_veri" in text
        assert "01_zaman_damgali_yedekler" in text
        assert "AKREDITASYON_ROOT" in text


def test_backup_scripts_create_timestamped_backup_area():
    ps1 = (ROOT / "tools" / "backup_medek.ps1").read_text(encoding="utf-8")
    sh = (ROOT / "tools" / "backup_medek.sh").read_text(encoding="utf-8")
    for text in (ps1, sh):
        assert "01_zaman_damgali_yedekler" in text
        assert "pg_dump" in text
        assert "manifest.json" in text
