from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks

from .config import DATA_DIR, MEDEK_JOB_BACKEND, MEDEK_REDIS_URL, MEDEK_RQ_QUEUE
from .db import get_conn, now_iso, row_to_dict, rows_to_dicts, transaction
from .file_security import safe_download_name
from .reporting import build_advanced_analytics_docx, build_control_docx, build_final_docx, build_readiness_audit_docx, convert_docx_to_pdf
from .repositories import assert_program_access, assert_report_export_ready, get_program, get_settings, record_export
from .notifications import notify_export_ready
from .storage_paths import write_export_copy

EXPORT_TYPES = {"docx", "pdf", "control_docx", "audit_docx", "analytics_docx", "analytics_pdf"}
EXPORT_DIR = DATA_DIR / "exports"  # legacy fallback; new outputs use organizational storage


def queue_backend() -> str:
    """Return the configured export job backend name."""
    return MEDEK_JOB_BACKEND if MEDEK_JOB_BACKEND in {"background", "rq"} else "background"


def _rq_queue():
    """Create an RQ queue lazily so local installs do not need Redis imports."""
    try:
        from redis import Redis
        from rq import Queue
    except ImportError as exc:  # pragma: no cover - depends on optional runtime package
        raise RuntimeError("Redis/RQ job backend seçili ancak redis ve rq paketleri kurulu değil.") from exc
    redis_conn = Redis.from_url(MEDEK_REDIS_URL)
    return Queue(MEDEK_RQ_QUEUE, connection=redis_conn)


def job_system_status() -> dict[str, Any]:
    """Expose queue backend status for admin/system diagnostics."""
    backend = queue_backend()
    data: dict[str, Any] = {"backend": backend, "queue": MEDEK_RQ_QUEUE}
    if backend == "rq":
        try:
            queue = _rq_queue()
            data.update({"redis_url": MEDEK_REDIS_URL, "queued_jobs": queue.count, "ok": True})
        except Exception as exc:  # noqa: BLE001 - diagnostics only
            data.update({"ok": False, "error": str(exc)})
    else:
        data.update({"ok": True, "note": "FastAPI BackgroundTasks"})
    return data


def _default_file_name(export_type: str, settings: dict[str, str]) -> str:
    if export_type == "docx":
        return settings.get("docx_filename", "AKYS_ODR.docx")
    if export_type == "pdf":
        return settings.get("pdf_filename", "AKYS_ODR.pdf")
    if export_type == "control_docx":
        return settings.get("control_filename", "AKYS_kontrol_tablosu.docx")
    if export_type == "audit_docx":
        return settings.get("audit_filename", "AKYS_hazirlik_denetimi.docx")
    if export_type == "analytics_docx":
        return "AKYS_advanced_analytics_dashboard.docx"
    if export_type == "analytics_pdf":
        return "AKYS_advanced_analytics_dashboard.pdf"
    raise ValueError("Desteklenmeyen çıktı türü.")


def _media_type_for(export_type: str) -> str:
    if export_type in {"pdf", "analytics_pdf"}:
        return "application/pdf"
    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _export_label(export_type: str, settings: dict[str, str]) -> str:
    if export_type == "docx":
        return f"Tam {settings.get('report_short', 'ÖDR')} DOCX"
    if export_type == "pdf":
        return f"Tam {settings.get('report_short', 'ÖDR')} PDF"
    if export_type == "control_docx":
        return "Kontrol DOCX"
    if export_type == "audit_docx":
        return "Hazırlık Denetimi DOCX"
    if export_type == "analytics_docx":
        return "Advanced Analytics DOCX"
    if export_type == "analytics_pdf":
        return "Advanced Analytics PDF"
    return export_type


def create_export_job(username: str, program_id: str, export_type: str, force: bool = False) -> dict[str, Any]:
    assert_program_access(username, program_id)
    if export_type not in EXPORT_TYPES:
        raise ValueError("Geçersiz çıktı türü. docx, pdf, control_docx, audit_docx, analytics_docx veya analytics_pdf kullanın.")
    if export_type in {"docx", "pdf"} and not force:
        assert_report_export_ready(username, program_id)
    settings = get_settings(program_id)
    file_name = safe_download_name(_default_file_name(export_type, settings))
    job_id = str(uuid.uuid4())
    now = now_iso()
    with transaction() as conn:
        conn.execute(
            """INSERT INTO export_jobs(
                id, program_id, export_type, status, file_name, file_path,
                actor, created_at, updated_at, error, progress, message
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (job_id, program_id, export_type, "queued", file_name, "", username, now, now, "", 0, "Kuyrukta"),
        )
    return get_export_job(username, program_id, job_id)


def list_export_jobs(username: str, program_id: str, limit: int = 50) -> list[dict[str, Any]]:
    assert_program_access(username, program_id)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM export_jobs WHERE program_id=? ORDER BY created_at DESC LIMIT ?",
            (program_id, int(limit)),
        ).fetchall()
    return rows_to_dicts(rows)


def get_export_job(username: str, program_id: str, job_id: str) -> dict[str, Any]:
    assert_program_access(username, program_id)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM export_jobs WHERE id=? AND program_id=?",
            (job_id, program_id),
        ).fetchone()
    data = row_to_dict(row)
    if not data:
        raise KeyError("Çıktı işi bulunamadı.")
    return data


def mark_export_job(job_id: str, status: str, *, file_path: str = "", error: str = "", progress: int | None = None, message: str = "") -> None:
    if progress is None:
        progress = {"queued": 0, "running": 15, "done": 100, "failed": 100}.get(status, 0)
    with transaction() as conn:
        conn.execute(
            """UPDATE export_jobs
               SET status=?, file_path=COALESCE(NULLIF(?, ''), file_path), error=?,
                   progress=?, message=?, updated_at=?
               WHERE id=?""",
            (status, file_path, error[:1000], max(0, min(100, int(progress or 0))), message[:500], now_iso(), job_id),
        )


def _build_export_bytes(username: str, program_id: str, export_type: str, base_url: str) -> bytes:
    if export_type == "docx":
        return build_final_docx(username, program_id, base_url=base_url)
    if export_type == "pdf":
        settings = get_settings(program_id)
        docx_data = build_final_docx(username, program_id, base_url=base_url)
        pdf_name = safe_download_name(settings.get("pdf_filename", "AKYS_ODR.pdf"))
        return convert_docx_to_pdf(docx_data, pdf_name.rsplit(".", 1)[0])
    if export_type == "control_docx":
        return build_control_docx(username, program_id)
    if export_type == "audit_docx":
        return build_readiness_audit_docx(username, program_id)
    if export_type == "analytics_docx":
        return build_advanced_analytics_docx(username, program_id)
    if export_type == "analytics_pdf":
        docx_data = build_advanced_analytics_docx(username, program_id)
        return convert_docx_to_pdf(docx_data, "AKYS_advanced_analytics_dashboard")
    raise ValueError("Desteklenmeyen çıktı türü.")


def run_export_job(username: str, program_id: str, job_id: str, export_type: str, base_url: str = "") -> None:
    try:
        mark_export_job(job_id, "running", progress=10, message="Çıktı hazırlanıyor")
        job = get_export_job(username, program_id, job_id)
        file_name = safe_download_name(str(job.get("file_name") or _default_file_name(export_type, get_settings(program_id))))
        extension = ".pdf" if export_type in {"pdf", "analytics_pdf"} else ".docx"
        mark_export_job(job_id, "running", progress=35, message="Rapor içeriği derleniyor")
        data = _build_export_bytes(username, program_id, export_type, base_url)
        mark_export_job(job_id, "running", progress=85, message="Dosya kaydediliyor")
        program = get_program(program_id) or {"id": program_id, "program_name": program_id}
        target_path = write_export_copy(program, file_name=file_name, data=data, export_type=export_type, actor=username, job_id=job_id)
        mark_export_job(job_id, "done", file_path=str(target_path), progress=100, message="Hazır")
        record_export(username, program_id, _export_label(export_type, get_settings(program_id)), file_name, "Background export job")
        notify_export_ready(username, program_id, export_type, job_id)
    except Exception as exc:  # noqa: BLE001 - persist a user-visible background failure
        mark_export_job(job_id, "failed", error=str(exc), progress=100, message="Hata oluştu")


def enqueue_export_job(
    username: str,
    program_id: str,
    export_type: str,
    background_tasks: BackgroundTasks | None = None,
    base_url: str = "",
    force: bool = False,
) -> dict[str, Any]:
    job = create_export_job(username, program_id, export_type, force=force)
    job_id = str(job["id"])
    if queue_backend() == "rq":
        queue = _rq_queue()
        queue.enqueue(
            run_export_job,
            username,
            program_id,
            job_id,
            export_type,
            base_url,
            job_timeout=1800,
            result_ttl=86400,
            failure_ttl=604800,
        )
    else:
        if background_tasks is None:
            raise RuntimeError("BackgroundTasks nesnesi olmadan background job kuyruğa alınamaz.")
        background_tasks.add_task(run_export_job, username, program_id, job_id, export_type, base_url)
    return get_export_job(username, program_id, job_id)


def export_job_file(username: str, program_id: str, job_id: str) -> tuple[Path, str, str]:
    job = get_export_job(username, program_id, job_id)
    if job.get("status") != "done":
        raise RuntimeError("Çıktı henüz hazır değil.")
    path = Path(str(job.get("file_path") or ""))
    if not path.exists() or not path.is_file():
        raise FileNotFoundError("Çıktı dosyası bulunamadı.")
    export_type = str(job.get("export_type") or "docx")
    return path, safe_download_name(str(job.get("file_name") or path.name)), _media_type_for(export_type)
