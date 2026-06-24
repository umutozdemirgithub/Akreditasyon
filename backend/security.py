from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import secrets
from typing import Any

try:
    import bcrypt
except Exception:  # pragma: no cover - optional fallback
    bcrypt = None

from .config import API_SECRET, TOKEN_TTL_MINUTES

WEAK_PASSWORDS = {"admin", "admin123", "password", "123456", "12345678", "qwerty", "change-this-initial-admin-password"}


def validate_password_strength(password: str) -> None:
    """Raise ValueError when a password is too weak for production use."""
    value = str(password or "")
    lowered = value.lower()
    if lowered in WEAK_PASSWORDS or lowered.startswith("change_me") or lowered.startswith("changeme"):
        raise ValueError("Şifre çok zayıf veya örnek değer içeriyor.")
    if len(value) < 10:
        raise ValueError("Şifre en az 10 karakter olmalıdır.")
    if not any(ch.isupper() for ch in value):
        raise ValueError("Şifre en az bir büyük harf içermelidir.")
    if not any(ch.islower() for ch in value):
        raise ValueError("Şifre en az bir küçük harf içermelidir.")
    if not any(ch.isdigit() for ch in value):
        raise ValueError("Şifre en az bir rakam içermelidir.")
    if not any(not ch.isalnum() for ch in value):
        raise ValueError("Şifre en az bir özel karakter içermelidir.")


def hash_password(password: str, salt: str | None = None) -> str:
    if bcrypt is not None:
        return "bcrypt$" + bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000).hex()
    return f"pbkdf2${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        if stored_hash.startswith("bcrypt$") and bcrypt is not None:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.split("$", 1)[1].encode("utf-8"))
        if stored_hash.startswith("pbkdf2$"):
            _, salt, digest = stored_hash.split("$", 2)
            candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000).hex()
            return hmac.compare_digest(candidate, digest)
        salt, digest = stored_hash.split("$", 1)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
        return hmac.compare_digest(candidate, digest)
    except Exception:
        return False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def create_access_token(subject: str, role: str, extra: dict[str, Any] | None = None) -> str:
    issued_at = int(time.time())
    payload = {
        "sub": subject,
        "role": role,
        "iat": issued_at,
        "exp": issued_at + TOKEN_TTL_MINUTES * 60,
        "jti": secrets.token_urlsafe(16),
        "iss": "akys",
        "aud": "akys-web",
    }
    if extra:
        payload.update(extra)
    body = _b64(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    sig = _b64(hmac.new(API_SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{sig}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        body, sig = token.split(".", 1)
        expected = _b64(hmac.new(API_SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_unb64(body).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        if payload.get("iss") not in (None, "akys"):
            return None
        if payload.get("aud") not in (None, "akys-web"):
            return None
        return payload
    except Exception:
        return None


def create_stream_token(subject: str, role: str, program_id: str, token_version: int, ttl_seconds: int = 120) -> str:
    """Create a short-lived token for EventSource stream bootstrap.

    This token is deliberately scoped to one program and a tiny lifetime so the
    primary API bearer token never has to be exposed in a URL.
    """
    issued_at = int(time.time())
    payload = {
        "sub": subject,
        "role": role,
        "program_id": program_id,
        "token_version": int(token_version or 1),
        "iat": issued_at,
        "exp": issued_at + int(ttl_seconds),
        "jti": secrets.token_urlsafe(16),
        "iss": "akys",
        "aud": "akys-event-stream",
        "typ": "event-stream",
    }
    body = _b64(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    sig = _b64(hmac.new(API_SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{sig}"


def decode_stream_token(token: str, program_id: str) -> dict[str, Any] | None:
    try:
        body, sig = str(token or "").split(".", 1)
        expected = _b64(hmac.new(API_SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_unb64(body).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        if payload.get("iss") != "akys":
            return None
        if payload.get("aud") != "akys-event-stream":
            return None
        if payload.get("typ") != "event-stream":
            return None
        if str(payload.get("program_id", "")) != str(program_id):
            return None
        return payload
    except Exception:
        return None
