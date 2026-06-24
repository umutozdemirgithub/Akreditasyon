from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response


@dataclass(frozen=True)
class RateLimitRule:
    limit: int
    window_seconds: int


_HITS: dict[str, Deque[float]] = defaultdict(deque)


def allow_request(key: str, rule: RateLimitRule) -> bool:
    """Simple per-process sliding-window limiter.

    This is sufficient for a single API container / intranet pilot. For multiple
    API replicas, replace with a Redis-backed limiter or enforce limits at Nginx.
    """
    now = time.monotonic()
    hits = _HITS[key]
    cutoff = now - rule.window_seconds
    while hits and hits[0] < cutoff:
        hits.popleft()
    if len(hits) >= rule.limit:
        return False
    hits.append(now)
    return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.enabled = os.getenv("MEDEK_RATE_LIMIT_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
        self.general = RateLimitRule(int(os.getenv("MEDEK_RATE_LIMIT_GENERAL_PER_MINUTE", "300")), 60)
        self.login = RateLimitRule(int(os.getenv("MEDEK_RATE_LIMIT_LOGIN_PER_MINUTE", "5")), 60)
        self.upload = RateLimitRule(int(os.getenv("MEDEK_RATE_LIMIT_UPLOAD_PER_MINUTE", "30")), 60)
        self.export = RateLimitRule(int(os.getenv("MEDEK_RATE_LIMIT_EXPORT_PER_MINUTE", "30")), 60)

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        if not self.enabled or request.url.path == "/api/health":
            return await call_next(request)

        client = request.headers.get("x-real-ip", "").strip()
        if not client:
            client = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        if not client and request.client:
            client = request.client.host
        client = client or "unknown"
        auth = request.headers.get("authorization", "")[:64]
        identity = auth if auth.lower().startswith("bearer ") else client

        path = request.url.path
        report_job_status_read = (
            path.endswith("/report/preflight")
            or path.endswith("/report/jobs")
            or ("/report/jobs/" in path and not path.endswith("/download"))
        )
        report_file_generation = (
            path.endswith("/report/docx")
            or path.endswith("/report/pdf")
            or (path.endswith("/report/jobs") and request.method == "POST")
            or ("/report/jobs/" in path and path.endswith("/download"))
        )

        if path == "/api/auth/login":
            key = f"login:{client}"
            rule = self.login
        elif "/evidence" in path and request.method in {"POST", "PUT"}:
            key = f"upload:{identity}"
            rule = self.upload
        elif report_file_generation or path.endswith("/backup") or path.endswith("/backup/restore"):
            key = f"export:{identity}"
            rule = self.export
        elif report_job_status_read:
            key = f"general:{identity}"
            rule = self.general
        else:
            key = f"general:{identity}"
            rule = self.general

        if not allow_request(key, rule):
            return JSONResponse(
                {"detail": "Çok fazla istek gönderildi. Lütfen kısa süre sonra tekrar deneyin."},
                status_code=429,
                headers={"Retry-After": str(rule.window_seconds)},
            )
        return await call_next(request)
