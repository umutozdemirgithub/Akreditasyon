from __future__ import annotations

from datetime import datetime

from fastapi import Header, HTTPException, Request

from .repositories import get_user, public_user
from .security import decode_access_token


def _parse_iso_datetime(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def current_user(request: Request, authorization: str = Header(default="")) -> dict:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Oturum bilgisi eksik.")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Oturum süresi dolmuş veya geçersiz.")

    username = str(payload.get("sub", "") or "")
    user = get_user(username, active_only=False)
    if not user:
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı.")
    if not bool(user.get("is_active", 0)):
        raise HTTPException(status_code=401, detail="Hesap kullanıma kapatılmıştır.")

    locked_until = _parse_iso_datetime(user.get("locked_until", ""))
    if locked_until and locked_until > datetime.now():
        raise HTTPException(status_code=401, detail="Hesap geçici olarak kilitlenmiştir.")

    current_version = int(user.get("token_version", 1) or 1)
    token_version = int(payload.get("token_version", current_version) or current_version)
    if token_version != current_version:
        raise HTTPException(status_code=401, detail="Oturum geçersiz. Lütfen yeniden giriş yapın.")

    # Role changes should take effect without waiting for token expiry.
    if str(payload.get("role", "")) and str(payload.get("role")) != str(user.get("role", "")):
        raise HTTPException(status_code=401, detail="Oturum yetkisi güncel değil. Lütfen yeniden giriş yapın.")

    user_public = public_user(user)
    allowed_during_password_change = {
        "/api/me",
        "/api/me/change-password",
        "/api/auth/login",
        "/api/health",
    }
    if user_public.get("must_change_password") and request.url.path not in allowed_during_password_change:
        raise HTTPException(status_code=403, detail="Devam etmeden önce şifrenizi değiştirmeniz gerekir.")

    return user_public
