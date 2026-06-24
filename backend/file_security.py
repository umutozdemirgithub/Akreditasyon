from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .config import DATA_DIR, EVIDENCE_DIR, ORG_STORAGE_DIR, MEDEK_MAX_UPLOAD_BYTES, MEDEK_MAX_UPLOAD_MB


ALLOWED_EVIDENCE_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".xls", ".csv", ".png", ".jpg", ".jpeg"}
MAX_UPLOAD_MB = MEDEK_MAX_UPLOAD_MB
MAX_UPLOAD_BYTES = MEDEK_MAX_UPLOAD_BYTES


def slugify(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9ğüşıöçİĞÜŞÖÇ]+", "-", text, flags=re.IGNORECASE)
    return re.sub(r"-+", "-", text).strip("-")[:96] or "dosya"


def safe_download_name(value: Any) -> str:
    name = Path(str(value or "dosya")).name
    name = re.sub(r"[^A-Za-z0-9_.\-ğüşıöçİĞÜŞÖÇ ]+", "_", name, flags=re.UNICODE).strip()
    return name[:160] or "dosya"


def safe_stored_path(path_value: str) -> Path | None:
    try:
        target = Path(path_value).resolve()
        allowed_bases = [EVIDENCE_DIR.resolve(), ORG_STORAGE_DIR.resolve(), DATA_DIR.resolve()]
        for base in allowed_bases:
            if target == base or base in target.parents:
                return target
    except Exception:
        return None
    return None


def file_signature_allowed(original_name: str, data: bytes) -> bool:
    suffix = Path(original_name).suffix.lower()
    if suffix == ".pdf":
        return data.startswith(b"%PDF-")
    if suffix == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix in {".jpg", ".jpeg"}:
        return data.startswith(b"\xff\xd8\xff")
    if suffix in {".docx", ".xlsx"}:
        return data.startswith(b"PK\x03\x04") or data.startswith(b"PK\x05\x06") or data.startswith(b"PK\x07\x08")
    if suffix == ".xls":
        return data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    if suffix == ".csv":
        if b"\x00" in data[:4096]:
            return False
        sample = data[:4096]
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                sample.decode(encoding)
                return True
            except UnicodeDecodeError:
                continue
        return False
    return False


def validate_evidence_bytes(original_name: str, data: bytes) -> None:
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_EVIDENCE_EXTENSIONS:
        raise ValueError(f"Bu dosya türü desteklenmiyor: {suffix}")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"Dosya {MAX_UPLOAD_MB} MB sınırını aşıyor.")
    if not file_signature_allowed(original_name, data):
        raise ValueError("Dosya imzası uzantı ile uyumlu değil.")

