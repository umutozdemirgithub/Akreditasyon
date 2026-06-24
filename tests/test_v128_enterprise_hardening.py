import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.responses import Response

from core.project_paths import find_project_root
from backend import main as main_module
from backend.security import create_access_token, create_stream_token, decode_stream_token

ROOT = find_project_root(Path(__file__))


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_eventsource_uses_stream_session_cookie_not_bearer_query():
    api = read("frontend/src/api.js")
    app = read("frontend/src/App.jsx")
    main = read("backend/main.py")
    assert "openEventStreamSession" in api
    assert "events/session" in api
    assert "events/stream?token=" not in api
    assert "new EventSource(api.eventStreamUrl(activeProgram), { withCredentials: true })" in app
    assert "set_cookie(" in main and "medek_stream_token" in main
    assert "decode_stream_token" in main
    assert "decode_access_token" not in main
    stream_signature = main.split("def program_events_stream", 1)[1].split("):", 1)[0]
    assert "token:" not in stream_signature


def test_stream_token_is_program_scoped_and_short_lived():
    token = create_stream_token("admin", "Süper Admin", "program-a", 3, ttl_seconds=60)
    payload = decode_stream_token(token, "program-a")
    assert payload is not None
    assert payload["sub"] == "admin"
    assert payload["program_id"] == "program-a"
    assert payload["typ"] == "event-stream"
    assert decode_stream_token(token, "program-b") is None


def test_event_stream_rejects_primary_access_token_query_fallback():
    token = create_access_token("admin", "Süper Admin", extra={"token_version": 1})
    with pytest.raises(HTTPException) as exc:
        main_module._stream_user_from_token(token, "program-a")
    assert exc.value.status_code == 401


def test_request_body_guard_limits_streamed_bodies_without_content_length(monkeypatch):
    monkeypatch.setattr(main_module, "MEDEK_MAX_REQUEST_BODY_BYTES", 5)
    monkeypatch.setattr(main_module, "MEDEK_MAX_REQUEST_BODY_MB", 1)

    class DummyRequest:
        method = "POST"
        headers: dict[str, str] = {}

        def __init__(self) -> None:
            self.messages = [
                {"type": "http.request", "body": b"abc", "more_body": True},
                {"type": "http.request", "body": b"def", "more_body": False},
            ]

        async def _receive(self):
            return self.messages.pop(0)

    async def call_next(request):
        while True:
            message = await request._receive()
            if not message.get("more_body"):
                break
        return Response("ok")

    response = asyncio.run(main_module.request_body_size_guard(DummyRequest(), call_next))
    assert response.status_code == 413


def test_upload_and_request_size_guards_are_present():
    config = read("backend/config.py")
    main = read("backend/main.py")
    env = read(".env.web.example")
    assert "MEDEK_MAX_UPLOAD_MB" in config
    assert "MEDEK_MAX_BACKUP_MB" in config
    assert "MEDEK_MAX_REQUEST_BODY_MB" in config
    assert "_RequestBodyTooLarge" in main
    assert "receive_with_limit" in main
    assert "def request_body_size_guard" in main
    assert "async def _read_upload_limited" in main
    assert "await file.read(1024 * 1024)" in main
    assert "MEDEK_MAX_UPLOAD_MB=50" in env


def test_cookie_secure_and_proxy_limits_are_explicit():
    config = read("backend/config.py")
    main = read("backend/main.py")
    env = read(".env.web.example")
    compose = read("docker-compose.web.yml")
    nginx = read("frontend/nginx.conf")
    dockerfile = read("Dockerfile.api")
    assert "MEDEK_COOKIE_SECURE" in config
    assert "secure=MEDEK_COOKIE_SECURE" in main
    assert "MEDEK_COOKIE_SECURE=false" in env
    assert "MEDEK_COOKIE_SECURE=${MEDEK_COOKIE_SECURE:-false}" in compose
    assert "client_max_body_size 60m" in nginx
    assert "$proxy_add_x_forwarded_for" in nginx
    assert "--proxy-headers" in dockerfile
    assert "--forwarded-allow-ips" in dockerfile


def test_docker_readiness_and_worker_healthchecks_are_wired():
    web = read("docker-compose.web.yml")
    queue = read("docker-compose.queue.yml")
    worker = read("backend/worker.py")
    assert "/api/health/ready" in web
    assert "redis-cli" in queue and "ping" in queue
    assert 'command: ["python", "-m", "backend.worker"]' in queue
    assert '["CMD", "python", "-m", "backend.worker", "--healthcheck"]' in queue
    assert "def healthcheck" in worker
    assert "redis_conn.ping()" in worker


def test_release_version_and_clean_zip_are_standardized():
    make_release = read("tools/make_release_zip.py")
    readme = read("README.md")
    changelog = read("CHANGELOG.md")
    package_json = read("frontend/package.json")
    assert "ver_100.1 - Rol ve Tema Senkronizasyonu" in readme
    assert "ver_100_role_theme_sync.zip" in make_release
    assert 'Path("ver_100")' in make_release
    assert "## ver_100.1 - Rol ve Tema Senkronizasyonu" in changelog
    assert '"version": "100.1.0"' in package_json
