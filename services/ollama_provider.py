from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Mapping, Sequence


AI_SETTING_PREFIX = "ai."
DEFAULT_RECOMMENDED_MODELS = ["llama3.1", "llama3.2", "mistral", "gemma2", "qwen2.5"]


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _bool_from_value(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "evet", "açık", "aktif"}


def _float_from_value(value: Any, default: float = 45.0) -> float:
    try:
        parsed = float(value)
    except Exception:
        return default
    return max(3.0, min(parsed, 600.0))


def _setting_rows() -> dict[str, str]:
    try:
        from backend.db import get_conn
        conn = get_conn()
        try:
            rows = conn.execute("SELECT key,value FROM settings WHERE key LIKE ?", (f"{AI_SETTING_PREFIX}%",)).fetchall()
            return {str(row["key"]): str(row["value"]) for row in rows}
        finally:
            conn.close()
    except Exception:
        return {}


def _write_settings(values: Mapping[str, Any]) -> None:
    from backend.db import get_conn
    conn = get_conn()
    try:
        for key, value in values.items():
            conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (f"{AI_SETTING_PREFIX}{key}", str(value)),
            )
        conn.commit()
    finally:
        conn.close()


def _env_config() -> dict[str, Any]:
    provider = os.getenv("MEDEK_AI_PROVIDER", "disabled").strip().lower() or "disabled"
    return {
        "enabled": _env_bool("MEDEK_AI_ENABLED", "false") and provider == "ollama",
        "provider": provider if provider in {"ollama", "disabled"} else "ollama",
        "base_url": os.getenv("MEDEK_OLLAMA_BASE_URL", "http://localhost:11434").strip().rstrip("/"),
        "model": os.getenv("MEDEK_OLLAMA_MODEL", "llama3.1").strip() or "llama3.1",
        "timeout": float(os.getenv("MEDEK_OLLAMA_TIMEOUT", "45") or 45),
        "source": "env",
    }


def ollama_config() -> dict[str, Any]:
    cfg = _env_config()
    rows = _setting_rows()
    if rows:
        cfg.update(
            {
                "enabled": _bool_from_value(rows.get("ai.enabled"), bool(cfg.get("enabled"))),
                "provider": str(rows.get("ai.provider", cfg.get("provider") or "ollama")).strip().lower() or "ollama",
                "base_url": str(rows.get("ai.base_url", cfg.get("base_url") or "http://localhost:11434")).strip().rstrip("/"),
                "model": str(rows.get("ai.model", cfg.get("model") or "llama3.1")).strip() or "llama3.1",
                "timeout": _float_from_value(rows.get("ai.timeout"), float(cfg.get("timeout") or 45)),
                "source": "database",
            }
        )
    if cfg["provider"] != "ollama":
        cfg["enabled"] = False
    return cfg


def _validate_model_name(model: str) -> str:
    model = str(model or "").strip()
    if not model:
        raise ValueError("Model adı boş olamaz.")
    if len(model) > 120 or not re.match(r"^[A-Za-z0-9_.:/-]+$", model):
        raise ValueError("Model adı yalnızca harf, rakam, nokta, alt çizgi, tire, iki nokta ve / içerebilir.")
    return model


def _safe_base_url(value: Any) -> str:
    base_url = str(value or "http://localhost:11434").strip().rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        raise ValueError("Ollama base URL http:// veya https:// ile başlamalıdır.")
    if len(base_url) > 240:
        raise ValueError("Ollama base URL çok uzun.")
    return base_url


def get_ai_settings_admin(username: str = "") -> dict[str, Any]:
    cfg = ollama_config()
    status = ollama_status()
    return {
        "enabled": bool(cfg.get("enabled")),
        "provider": cfg.get("provider", "ollama"),
        "base_url": cfg.get("base_url", "http://localhost:11434"),
        "model": cfg.get("model", "llama3.1"),
        "timeout": cfg.get("timeout", 45),
        "source": cfg.get("source", "env"),
        "recommended_models": DEFAULT_RECOMMENDED_MODELS,
        "status": status,
    }


def update_ai_settings_admin(username: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    provider = str(payload.get("provider", "ollama") or "ollama").strip().lower()
    if provider not in {"ollama", "disabled"}:
        raise ValueError("AI provider yalnızca ollama veya disabled olabilir.")
    enabled = _bool_from_value(payload.get("enabled"), False)
    if provider == "disabled":
        enabled = False
    base_url = _safe_base_url(payload.get("base_url", "http://localhost:11434"))
    model = _validate_model_name(payload.get("model", "llama3.1"))
    timeout = _float_from_value(payload.get("timeout"), 45)
    _write_settings({
        "enabled": "true" if enabled else "false",
        "provider": provider,
        "base_url": base_url,
        "model": model,
        "timeout": str(int(timeout) if timeout.is_integer() else timeout),
        "updated_by": username or "system",
    })
    return get_ai_settings_admin(username)


def _json_request(url: str, payload: Mapping[str, Any] | None = None, timeout: float = 8.0, method: str | None = None) -> dict[str, Any]:
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method or ("POST" if payload is not None else "GET"))
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body or "{}")


def list_ollama_models() -> dict[str, Any]:
    cfg = ollama_config()
    try:
        body = _json_request(f"{cfg['base_url']}/api/tags", timeout=min(float(cfg.get("timeout") or 45), 8.0), method="GET")
        models = [item.get("name", "") for item in body.get("models", []) if item.get("name")]
        return {"ok": True, "models": models, "base_url": cfg["base_url"], "selected_model": cfg["model"]}
    except Exception as exc:
        return {"ok": False, "models": [], "base_url": cfg.get("base_url"), "selected_model": cfg.get("model"), "error": str(exc)}


def pull_ollama_model(model: str | None = None) -> dict[str, Any]:
    cfg = ollama_config()
    selected = _validate_model_name(model or cfg.get("model") or "llama3.1")
    try:
        body = _json_request(
            f"{cfg['base_url']}/api/pull",
            payload={"name": selected, "stream": False},
            timeout=max(60.0, min(float(cfg.get("timeout") or 60), 600.0)),
        )
        models = list_ollama_models()
        return {
            "ok": True,
            "model": selected,
            "status": body.get("status", "pulled"),
            "message": f"{selected} modeli Ollama tarafında hazırlandı.",
            "models": models.get("models", []),
        }
    except Exception as exc:
        return {"ok": False, "model": selected, "error": str(exc), "message": "Model yükleme başarısız. Ollama servisinin açık ve erişilebilir olduğundan emin olun."}


def ollama_status() -> dict[str, Any]:
    cfg = ollama_config()
    if not cfg["enabled"]:
        models_result = list_ollama_models()
        return {
            **cfg,
            "available": False,
            "mode": "deterministic-fallback",
            "models": models_result.get("models", []),
            "message": "AI kapalı; yerel şablon tabanlı taslak üretici kullanılacak.",
            "error": models_result.get("error", "") if not models_result.get("ok") else "",
        }
    try:
        body = _json_request(f"{cfg['base_url']}/api/tags", timeout=min(cfg["timeout"], 8), method="GET")
        models = [item.get("name", "") for item in body.get("models", []) if item.get("name")]
        selected_ready = cfg["model"] in models or any(str(name).split(":")[0] == str(cfg["model"]).split(":")[0] for name in models)
        if not selected_ready:
            return {**cfg, "available": False, "mode": "deterministic-fallback", "models": models, "message": f"Ollama açık ama seçili model yüklü değil: {cfg['model']}", "error": "selected_model_missing"}
        return {**cfg, "available": True, "mode": "ollama", "models": models, "message": "Ollama bağlantısı hazır."}
    except Exception as exc:
        return {**cfg, "available": False, "mode": "deterministic-fallback", "error": str(exc), "message": "Ollama erişilemedi; sistem güvenli şekilde yerel şablon üreticiye düşecek."}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _clip(value: str, limit: int = 1200) -> str:
    clean = _clean(value)
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"


def build_ollama_prompt(section: Mapping[str, Any], guide: Mapping[str, Any], evidence: Sequence[Mapping[str, Any]], tables: Sequence[Mapping[str, Any]], target_words: int = 650) -> str:
    evidence_lines = "\n".join([f"- {row.get('code', '')}: {row.get('original_name', '')} — {row.get('note', '')}" for row in evidence[:12]]) or "- Kanıt eklenmemiş. Kanıt ihtiyacını metinde belirt."
    table_lines = "\n".join([f"- {row.get('table_name', '')}" for row in tables[:8]]) or "- Tablo eklenmemiş."
    return f"""
Sen bir Türkçe akreditasyon öz değerlendirme raporu editörüsün. Çıktı yalnızca kullanıcı tarafından incelenecek TASLAK metindir; kesin hüküm verme, olmayan kanıt uydurma.

Başlık kodu: {section.get('section_key', '')}
Başlık: {section.get('section_title', '')}
Ana grup: {section.get('main_title', '')}
Soru / ölçüt yönlendirmesi: {guide.get('question', section.get('section_title', ''))}
Beklenen kanıtlar: {', '.join([str(x) for x in guide.get('evidence', [])])}
Mevcut rapor metni: {_clip(section.get('report_text', ''), 1600)}
PUKÖ Planla: {_clip(section.get('planla', ''), 700)}
PUKÖ Uygula: {_clip(section.get('uygula', ''), 700)}
PUKÖ Kontrol Et: {_clip(section.get('kontrol', ''), 700)}
PUKÖ Önlem Al: {_clip(section.get('onlem', ''), 700)}
Kanıtlar:
{evidence_lines}
Tablolar:
{table_lines}

Görev: Yaklaşık {target_words} kelimelik, kurumsal, kanıt odaklı, MEDEK/YÖKAK tarzına uygun rapor taslağı yaz. Kanıt kodu yoksa [KANIT GEREKİR] etiketi kullan. Çıktının sonunda kısa "Kontrol notu" bölümü ekle.
""".strip()


def generate_with_ollama(prompt: str) -> dict[str, Any]:
    cfg = ollama_config()
    if not cfg["enabled"]:
        raise RuntimeError("Ollama devre dışı.")
    payload = {
        "model": cfg["model"],
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.25, "top_p": 0.85},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{cfg['base_url']}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg["timeout"]) as response:
            body = json.loads(response.read().decode("utf-8"))
        text = str(body.get("response", "") or "").strip()
        if not text:
            raise RuntimeError("Ollama boş yanıt döndürdü.")
        return {"text": text, "provider": "ollama", "model": cfg["model"], "warnings": []}
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama bağlantı hatası: {exc}") from exc
