from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_start_scripts_autogenerate_missing_production_secrets():
    ps1 = (ROOT / "tools" / "start_web_stack.ps1").read_text(encoding="utf-8")
    sh = (ROOT / "tools" / "start_web_stack.sh").read_text(encoding="utf-8")
    for text in (ps1, sh):
        assert "MEDEK_API_SECRET" in text
        assert "MEDEK_BOOTSTRAP_ADMIN_PASSWORD" in text
        assert "POSTGRES_PASSWORD" in text
        assert "CHANGE_ME" in text
        assert "İlk admin şifresi" in text


def test_compose_api_healthcheck_has_boot_tolerance_and_rate_defaults():
    compose = (ROOT / "docker-compose.web.yml").read_text(encoding="utf-8")
    assert "MEDEK_RATE_LIMIT_GENERAL_PER_MINUTE=${MEDEK_RATE_LIMIT_GENERAL_PER_MINUTE:-300}" in compose
    assert "MEDEK_RATE_LIMIT_EXPORT_PER_MINUTE=${MEDEK_RATE_LIMIT_EXPORT_PER_MINUTE:-30}" in compose
    assert "start_period: 60s" in compose
    assert "retries: 10" in compose


def test_diagnostic_scripts_are_packaged():
    assert (ROOT / "tools" / "diagnose_stack.ps1").exists()
    assert (ROOT / "tools" / "diagnose_stack.sh").exists()
    assert "docker logs --tail=220 akys-api" in (ROOT / "tools" / "diagnose_stack.ps1").read_text(encoding="utf-8")
