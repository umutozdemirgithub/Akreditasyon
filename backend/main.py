from __future__ import annotations

import asyncio
import csv
import json
import logging
from io import StringIO
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import (
    APP_VERSION,
    CORS_ORIGINS,
    TRUSTED_HOSTS,
    MEDEK_COOKIE_SECURE,
    MEDEK_MAX_BACKUP_BYTES,
    MEDEK_MAX_BACKUP_MB,
    MEDEK_MAX_REQUEST_BODY_BYTES,
    MEDEK_MAX_REQUEST_BODY_MB,
    MEDEK_MAX_UPLOAD_BYTES,
    MEDEK_MAX_UPLOAD_MB,
)
from .db import get_conn, init_db, now_iso
from .dependencies import current_user
from .file_security import safe_download_name
from .reporting import build_advanced_analytics_docx, build_compliance_audit_docx, build_control_docx, build_final_docx, build_readiness_audit_docx, convert_docx_to_pdf
from .rate_limit import RateLimitMiddleware
from .export_jobs import enqueue_export_job, export_job_file, get_export_job, list_export_jobs
from .enterprise_features import (
    activity_timeline,
    advanced_reporting,
    compliance_audit_payload,
    deleted_items_admin,
    deleted_programs_admin,
    purge_item_admin,
    permission_matrix_admin,
    role_permission_allowed,
    restore_item_admin,
    purge_program_admin,
    restore_program_admin,
    section_versions_diff,
    effective_sidebar_matrix_public,
    repair_legacy_dashboard_sidebar_visibility,
    sidebar_matrix_public,
    update_permission_matrix_admin,
    usage_analytics_admin,
    workflow_reminders_payload,
    workflow_automation_preview,
    workflow_automation_runs,
    workflow_automation_settings,
    run_workflow_automation,
    update_workflow_automation_settings,
)
from .repositories import (
    apply_ai_draft_to_section,
    assert_program_operation_permission,
    assert_report_export_ready,
    get_program,
    get_user as repo_get_user,
    ROLE_OPTIONS,
    FACULTY_ADMIN_ROLE,
    is_admin_role,
    is_super_admin_user,
    normalized_role,
    report_preflight_payload,
    visible_roles_for_actor,
)

from .asset_studio import evidence_archive_studio_payload, table_management_studio_payload
from .insights import (
    mark_notifications_read,
    notification_inbox,
    program_help,
    program_insights,
)
from .notifications import (
    get_mail_settings_admin,
    list_notification_events_admin,
    mail_system_status,
    notify_approval_event,
    notify_deadlines_updated,
    notify_program_assignment,
    notify_user_saved,
    send_test_mail_admin,
    update_mail_settings_admin,
)
from .repos.approval_repo import approval_action, approval_history
from .repos.audit_repo import activity_rows, export_history
from .repos.backup_repo import (
    ai_draft_for_section,
    backup_payload,
    full_ai_draft_candidates,
    get_settings,
    get_settings_for_user,
    import_report_file,
    restore_backup_payload_admin,
    system_status,
    update_settings_admin,
)
from .repos.evidence_repo import (
    delete_evidence_file,
    evidence_file_path,
    list_evidence,
    link_evidence_to_section,
    save_evidence_file,
)
from .repos.programs_repo import (
    assign_user_to_program_admin,
    clone_program_admin,
    create_program_admin,
    delete_program_admin,
    list_program_users_admin,
    list_programs_admin,
    list_programs_for_user,
    set_program_active_admin,
)
from .repos.sections_repo import (
    bulk_update_status,
    bulk_update_advanced,
    control_rows,
    dashboard,
    deadline_rows,
    get_section,
    list_sections,
    preview_payload,
    search_sections,
    stats_payload,
    update_deadlines,
    update_section,
)
from .repos.tables_repo import attach_table_to_section, delete_table, list_tables, save_table
from .repos.users_repo import (
    authenticate_user,
    change_own_password,
    delete_user_admin,
    list_users_admin,
    login_attempt_rows_admin,
    public_user,
    upsert_user_admin,
)
from .schemas import (
    AcademicCatalogImportPayload,
    ApprovalRequest,
    BulkStatusPayload,
    BulkAdvancedPayload,
    NotificationReadPayload,
    ChangePasswordPayload,
    DeadlinePayload,
    EvidenceLinkPayload,
    LoginRequest,
    MailSettingsPayload,
    MailTestPayload,
    ProgramAssignmentPayload,
    ProgramClonePayload,
    ProgramPayload,
    SectionUpdate,
    SettingsPayload,
    TableAttachPayload,
    TablePayload,
    TenantPayload,
    TenantFacultyPayload,
    TokenResponse,
    UserPayload,
)
from .security import create_access_token, create_stream_token, decode_stream_token
from .storage_paths import write_export_copy
from .template_seed import list_system_templates_admin, restore_missing_program_sections_admin, seed_system_templates_admin
from .update_center import list_update_center_payload, run_update_center_check, apply_update_candidate, ignore_update_candidate
from .section_permissions import section_permission_payload, update_section_permission_policy
from .professional_reporting import (
    AUDITOR_PACKAGE_FILENAME,
    PACKAGE_FILENAME,
    build_report_package_zip,
    consistency_check_payload,
    create_auditor_share_link,
    create_clause,
    insert_clause_into_section,
    list_auditor_share_links,
    list_clause_library,
    mock_audit_payload,
    professional_reporting_payload,
    report_quality_payload,
    seed_clause_library,
    sentence_diff_payload,
)
from .section_studio import (
    report_studio_payload,
    quick_ai_suggestions,
    recalculate_section_quality,
    bulk_studio_update,
    collaboration_ping,
    active_collaborators,
    section_docx_bytes,
    section_template_bank,
    create_section_template,
    accreditation_gap_scan,
    evidence_matching_assistant,
)
from services.ollama_provider import get_ai_settings_admin, list_ollama_models, ollama_status, pull_ollama_model, update_ai_settings_admin
from .tenancy import delete_tenant_admin, list_tenants_admin, save_tenant_admin, list_faculties_admin, save_faculty_admin, tenant_dashboard_admin, tenant_setup_status_admin
from .deployment import deployment_smoke_payload, deployment_wizard_payload
from .appearance import admin_appearance_payload, appearance_for_user, update_tenant_appearance_admin
from .academic_importer import import_academic_catalog_admin

from .personal_backup import (
    ZIP_MEDIA_TYPE,
    build_all_personal_backup_zip,
    build_program_personal_backup_zip,
    personal_backup_filename,
)


logger = logging.getLogger(__name__)

app = FastAPI(title="AKYS API", version=APP_VERSION)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=TRUSTED_HOSTS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class _RequestBodyTooLarge(Exception):
    pass


@app.middleware("http")
async def request_body_size_guard(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Reject oversized request bodies before handlers read them into memory."""
    if request.method not in {"POST", "PUT", "PATCH"}:
        return await call_next(request)

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MEDEK_MAX_REQUEST_BODY_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"İstek gövdesi {MEDEK_MAX_REQUEST_BODY_MB} MB sınırını aşıyor."},
                )
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Geçersiz Content-Length başlığı."})

    original_receive = request._receive  # type: ignore[attr-defined]
    total = 0

    async def receive_with_limit():  # type: ignore[no-untyped-def]
        nonlocal total
        message = await original_receive()
        if message.get("type") == "http.request":
            total += len(message.get("body", b"") or b"")
            if total > MEDEK_MAX_REQUEST_BODY_BYTES:
                raise _RequestBodyTooLarge
        return message

    request._receive = receive_with_limit  # type: ignore[attr-defined]
    try:
        return await call_next(request)
    except _RequestBodyTooLarge:
        return JSONResponse(
            status_code=413,
            content={"detail": f"İstek gövdesi {MEDEK_MAX_REQUEST_BODY_MB} MB sınırını aşıyor."},
        )


DASHBOARD_PERMISSION_KEYS = [
    "dashboard.view",
    "dashboard.kpi.view",
    "dashboard.priority.view",
    "dashboard.criteria.view",
    "dashboard.charts.view",
    "dashboard.activity.view",
]


def _matrix_tenant_id_for_user(user: dict[str, Any]) -> str:
    if is_super_admin_user(user):
        return ""
    return str(user.get("tenant_id", "") or "tenant_default")


def _sidebar_matrix_for_user(user: dict[str, Any]) -> list[dict[str, Any]]:
    return effective_sidebar_matrix_public(_matrix_tenant_id_for_user(user))


def _dashboard_permissions_for_role(role: str, tenant_id: str) -> dict[str, bool]:
    normalized = normalized_role(str(role or "Denetçi"))
    return {key: role_permission_allowed(normalized, key, tenant_id) for key in DASHBOARD_PERMISSION_KEYS}


def _dashboard_permissions_for_user(user: dict[str, Any]) -> dict[str, bool]:
    role = normalized_role(str(user.get("role", "") or "Denetçi"), str(user.get("tenant_scope", "") or ""))
    return _dashboard_permissions_for_role(role, _matrix_tenant_id_for_user(user))


def _dashboard_permissions_by_role_for_user(user: dict[str, Any]) -> dict[str, dict[str, bool]]:
    tenant_id = _matrix_tenant_id_for_user(user)
    return {role: _dashboard_permissions_for_role(role, tenant_id) for role in ROLE_OPTIONS}


def _attach_ui_permission_payload(user_public: dict[str, Any], source_user: dict[str, Any] | None = None) -> dict[str, Any]:
    source = source_user or user_public
    user_public["sidebar_matrix"] = _sidebar_matrix_for_user(source)
    user_public["dashboard_permissions"] = _dashboard_permissions_for_user(source)
    user_public["dashboard_permissions_by_role"] = _dashboard_permissions_by_role_for_user(source)
    return user_public


@app.on_event("startup")
def startup() -> None:
    init_db()
    repair_legacy_dashboard_sidebar_visibility()


async def _read_upload_limited(file: UploadFile, *, max_bytes: int, max_mb: int, label: str) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValueError(f"{label} {max_mb} MB sınırını aşıyor.")
        chunks.append(chunk)
    return b"".join(chunks)


def _stream_user_from_payload(payload: dict[str, Any]) -> dict:
    username = str(payload.get("sub", "") or "")
    user = repo_get_user(username, active_only=False)
    if not user or not bool(user.get("is_active", 0)):
        raise HTTPException(status_code=401, detail="Kullanıcı bulunamadı veya pasif.")
    token_version = int(payload.get("token_version", user.get("token_version", 1)) or 1)
    if token_version != int(user.get("token_version", 1) or 1):
        raise HTTPException(status_code=401, detail="Oturum güncel değil.")
    return public_user(user)


@app.get("/api/health")
def health() -> dict:
    # Production healthcheck intentionally avoids leaking filesystem paths or
    # internal deployment details. The detailed system status remains behind
    # authenticated/admin endpoints.
    return {"ok": True, "version": APP_VERSION}


@app.get("/api/health/ready")
def health_ready() -> dict:
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001 - readiness must return a clear 503
        raise HTTPException(status_code=503, detail="Veritabanı bağlantısı hazır değil.") from exc


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Kullanıcı adı veya şifre hatalı.")
    user_public = _attach_ui_permission_payload(public_user(user), user)
    token = create_access_token(
        user_public["username"],
        user_public["role"],
        extra={"token_version": int(user.get("token_version", 1) or 1)},
    )
    return TokenResponse(access_token=token, user=user_public)


@app.get("/api/me")
def me(user: dict = Depends(current_user)) -> dict:
    return _attach_ui_permission_payload(dict(user), user)


def _stream_user_from_token(token: str, program_id: str) -> dict:
    payload = decode_stream_token(str(token or ""), program_id)
    if not payload:
        raise HTTPException(status_code=401, detail="Canlı bağlantı oturumu geçersiz.")
    return _stream_user_from_payload(payload)


@app.post("/api/programs/{program_id}/events/session")
def program_events_session(program_id: str, response: Response, request: Request, user: dict = Depends(current_user)) -> dict:
    try:
        # Reuse the existing program access gate without sending any event data.
        list_export_jobs(user["username"], program_id, 1)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    raw_user = repo_get_user(str(user.get("username", "")), active_only=False) or {}
    stream_token = create_stream_token(
        str(user.get("username", "")),
        str(user.get("role", "")),
        program_id,
        int(raw_user.get("token_version", 1) or 1),
        ttl_seconds=180,
    )
    response.set_cookie(
        "medek_stream_token",
        stream_token,
        max_age=180,
        httponly=True,
        secure=MEDEK_COOKIE_SECURE,
        samesite="strict",
        path="/api/programs",
    )
    return {"ok": True, "expires_in_seconds": 180}


@app.get("/api/ai/status")
def global_ai_status(user: dict = Depends(current_user)) -> dict:
    if not is_admin_role(str(user.get("role", ""))):
        raise HTTPException(status_code=403, detail="AI bağlantı testi yalnızca Süper Admin veya Kurum Admin tarafından görüntülenebilir.")
    return {**ollama_status(), "checked_at": now_iso(), "endpoint": "/api/ai/status"}


@app.get("/api/admin/ai/settings")
def admin_ai_settings(user: dict = Depends(current_user)) -> dict:
    if not is_admin_role(str(user.get("role", ""))):
        raise HTTPException(status_code=403, detail="AI ayarları yalnızca Süper Admin veya Kurum Admin tarafından görüntülenebilir.")
    return get_ai_settings_admin(user.get("username", ""))


@app.put("/api/admin/ai/settings")
def admin_ai_settings_update(payload: dict[str, Any], user: dict = Depends(current_user)) -> dict:
    if not is_admin_role(str(user.get("role", ""))):
        raise HTTPException(status_code=403, detail="AI ayarlarını değiştirme yetkiniz yok.")
    try:
        return update_ai_settings_admin(user.get("username", ""), payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/admin/ai/models")
def admin_ai_models(user: dict = Depends(current_user)) -> dict:
    if not is_admin_role(str(user.get("role", ""))):
        raise HTTPException(status_code=403, detail="AI model listesini görüntüleme yetkiniz yok.")
    return {**list_ollama_models(), "checked_at": now_iso()}


@app.post("/api/admin/ai/models/pull")
def admin_ai_model_pull(payload: dict[str, Any], user: dict = Depends(current_user)) -> dict:
    if not is_admin_role(str(user.get("role", ""))):
        raise HTTPException(status_code=403, detail="AI modeli yükleme yetkiniz yok.")
    return {**pull_ollama_model(str(payload.get("model", "") or "")), "checked_at": now_iso()}


@app.get("/api/programs/{program_id}/events/stream")
async def program_events_stream(program_id: str, request: Request) -> StreamingResponse:
    stream_token = request.cookies.get("medek_stream_token") or ""
    user = _stream_user_from_token(stream_token, program_id)

    async def event_generator():
        event_id = 0
        while True:
            if await request.is_disconnected():
                break
            try:
                inbox = notification_inbox(user["username"], program_id, 50)
                jobs = list_export_jobs(user["username"], program_id, 15)
                payload = {
                    "type": "sync",
                    "program_id": program_id,
                    "unread_count": len([row for row in inbox if not row.get("read")]),
                    "latest_notification_id": str(inbox[0].get("id", "")) if inbox else "",
                    "latest_notification_subject": str(inbox[0].get("subject", "")) if inbox else "",
                    "export_jobs": jobs,
                    "server_time": now_iso(),
                }
                yield f"event: medek\nid: {event_id}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            except PermissionError:
                yield "event: medek-error\ndata: {\"detail\":\"Bu programa erişim yetkiniz yok.\"}\n\n"
                break
            except Exception as exc:  # noqa: BLE001 - live status stream must not crash the API worker
                data = json.dumps({"detail": str(exc), "server_time": now_iso()}, ensure_ascii=False)
                yield f"event: medek-error\ndata: {data}\n\n"
            event_id += 1
            await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/me/change-password", response_model=TokenResponse)
def me_change_password(payload: ChangePasswordPayload, user: dict = Depends(current_user)) -> TokenResponse:
    try:
        changed_user = change_own_password(user["username"], payload.current_password, payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    user_public = _attach_ui_permission_payload(public_user(changed_user), changed_user)
    token = create_access_token(
        user_public["username"],
        user_public["role"],
        extra={"token_version": int(changed_user.get("token_version", 1) or 1)},
    )
    return TokenResponse(access_token=token, user=user_public)


@app.get("/api/programs")
def programs(user: dict = Depends(current_user)) -> list[dict]:
    return list_programs_for_user(user["username"])


@app.get("/api/admin/programs")
def admin_programs(include_inactive: bool = True, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return list_programs_admin(user["username"], include_inactive)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/admin/programs")
def admin_program_create(payload: ProgramPayload, user: dict = Depends(current_user)) -> dict:
    try:
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        return create_program_admin(user["username"], data)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/admin/programs/clone")
def admin_program_clone(payload: ProgramClonePayload, user: dict = Depends(current_user)) -> dict:
    try:
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        return clone_program_admin(user["username"], data)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/admin/programs/{program_id}/active")
def admin_program_active(program_id: str, active: bool = True, user: dict = Depends(current_user)) -> dict:
    try:
        return set_program_active_admin(user["username"], program_id, active)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.delete("/api/admin/programs/{program_id}")
def admin_program_delete(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return delete_program_admin(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc




@app.get("/api/admin/programs/deleted")
def admin_deleted_programs(user: dict = Depends(current_user)) -> list[dict]:
    try:
        return deleted_programs_admin(user["username"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/admin/recovery/items")
def admin_deleted_items(user: dict = Depends(current_user)) -> list[dict]:
    try:
        return deleted_items_admin(user["username"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.put("/api/admin/recovery/items/{item_type}/{item_id}/restore")
def admin_item_restore(item_type: str, item_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return restore_item_admin(user["username"], item_type, item_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/admin/recovery/items/{item_type}/{item_id}/purge")
def admin_item_purge(item_type: str, item_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return purge_item_admin(user["username"], item_type, item_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/admin/programs/{program_id}/restore")
def admin_program_restore(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return restore_program_admin(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/api/admin/programs/{program_id}/purge")
def admin_program_purge(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return purge_program_admin(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc




@app.get("/api/appearance/current")
def current_appearance(user: dict = Depends(current_user)) -> dict:
    try:
        return appearance_for_user(user["username"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/admin/appearance")
def admin_appearance(user: dict = Depends(current_user)) -> dict:
    try:
        return admin_appearance_payload(user["username"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.put("/api/admin/appearance/tenants/{tenant_id}")
def admin_appearance_update(tenant_id: str, payload: dict[str, Any], user: dict = Depends(current_user)) -> dict:
    try:
        return update_tenant_appearance_admin(user["username"], tenant_id, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/api/admin/permissions")
def admin_permissions(user: dict = Depends(current_user)) -> dict:
    try:
        return permission_matrix_admin(user["username"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.put("/api/admin/permissions")
def admin_permissions_update(payload: dict[str, Any], user: dict = Depends(current_user)) -> dict:
    try:
        return update_permission_matrix_admin(user["username"], payload.get("rows", []), payload.get("sidebar_rows", []))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _permission_matrix_download_payload(username: str, program_id: str | None = None) -> dict[str, Any]:
    payload = permission_matrix_admin(username)
    actor = repo_get_user(username, active_only=True) or {}
    role_scope = [role for role in ROLE_OPTIONS if role in visible_roles_for_actor(actor)]
    section_payload: dict[str, Any] = {"rows": []}
    if program_id:
        # list_sections enforces program, tenant and faculty scope before section policies are exported.
        list_sections(username, program_id)
        section_payload = section_permission_payload(program_id)

    def keep_roles(row: dict[str, Any], base_fields: list[str]) -> dict[str, Any]:
        clean = {field: row.get(field, "") for field in base_fields}
        clean.update({role: bool(row.get(role, False)) for role in role_scope})
        return clean

    return {
        "export_type": "AKYS Yetki Matrisi",
        "generated_at": now_iso(),
        "admin_scope": payload.get("admin_scope", ""),
        "tenant_id": payload.get("tenant_id") or "global",
        "program_id": program_id or "",
        "role_scope": role_scope,
        "editable_roles": [role for role in payload.get("editable_roles", []) if role in role_scope],
        "protected_roles": [role for role in payload.get("protected_roles", []) if role in role_scope],
        "note": payload.get("delegation_note", ""),
        "matrices": {
            "operation_permissions": [keep_roles(row, ["category", "permission", "label", "description"]) for row in payload.get("rows", [])],
            "sidebar_visibility": [keep_roles(row, ["group", "module", "label", "description"]) for row in payload.get("sidebar_rows", [])],
            "section_policies": [keep_roles(row, ["main_title", "section_key", "section_title", "action", "label", "description"]) for row in section_payload.get("rows", [])],
        },
    }


def _permission_matrix_csv(payload: dict[str, Any]) -> str:
    roles = [str(role) for role in payload.get("role_scope", [])]
    output = StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\n")
    writer.writerow(["Matris", "Grup/Kategori", "Kod", "Etiket", "Açıklama", *roles])

    def role_value(row: dict[str, Any], role: str) -> str:
        return "Açık" if bool(row.get(role, False)) else "Kapalı"

    for row in payload.get("matrices", {}).get("operation_permissions", []):
        writer.writerow(["İşlem Yetki Matrisi", row.get("category", ""), row.get("permission", ""), row.get("label", ""), row.get("description", ""), *[role_value(row, role) for role in roles]])
    for row in payload.get("matrices", {}).get("sidebar_visibility", []):
        writer.writerow(["Sidebar Görünürlük Matrisi", row.get("group", ""), row.get("module", ""), row.get("label", ""), row.get("description", ""), *[role_value(row, role) for role in roles]])
    for row in payload.get("matrices", {}).get("section_policies", []):
        writer.writerow(["Section Bazlı Yetki Matrisi", row.get("main_title", ""), f"{row.get('section_key', '')} / {row.get('action', '')}", row.get("label", "") or row.get("section_title", ""), row.get("description", ""), *[role_value(row, role) for role in roles]])
    return output.getvalue()


@app.get("/api/admin/permissions/download")
def admin_permissions_download(format: str = "csv", program_id: str | None = None, user: dict = Depends(current_user)) -> Response:
    try:
        payload = _permission_matrix_download_payload(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    stamp = now_iso().replace(":", "-")[:19]
    extension = "json" if str(format).lower() == "json" else "csv"
    filename = safe_download_name(f"AKYS_yetki_matrisi_{stamp}.{extension}")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if extension == "json":
        return Response(json.dumps(payload, ensure_ascii=False, indent=2), media_type="application/json; charset=utf-8", headers=headers)
    return Response("﻿" + _permission_matrix_csv(payload), media_type="text/csv; charset=utf-8", headers=headers)


@app.get("/api/admin/deployment/wizard")
def admin_deployment_wizard(user: dict = Depends(current_user)) -> dict:
    try:
        return deployment_wizard_payload(user["username"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/admin/deployment/smoke")
def admin_deployment_smoke(user: dict = Depends(current_user)) -> dict:
    try:
        return deployment_smoke_payload(user["username"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

@app.get("/api/admin/analytics")
def admin_analytics(limit: int = 200, user: dict = Depends(current_user)) -> dict:
    try:
        return usage_analytics_admin(user["username"], limit)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

@app.get("/api/admin/tenants")
def admin_tenants(include_inactive: bool = True, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return list_tenants_admin(user["username"], include_inactive)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/admin/tenants")
def admin_tenant_save(payload: TenantPayload, user: dict = Depends(current_user)) -> dict:
    try:
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        return save_tenant_admin(user["username"], data)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/admin/tenants/{tenant_id}")
def admin_tenant_delete(tenant_id: str, mode: str = "safe", target_tenant_id: str = "", user: dict = Depends(current_user)) -> dict:
    try:
        return delete_tenant_admin(user["username"], tenant_id, mode=mode, target_tenant_id=target_tenant_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc



@app.post("/api/admin/tenants/import-academic-catalog")
def admin_tenant_academic_catalog_import(payload: AcademicCatalogImportPayload, user: dict = Depends(current_user)) -> dict:
    try:
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        return import_academic_catalog_admin(user["username"], data)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/admin/tenant-faculties")
def admin_tenant_faculties(tenant_id: str = "", user: dict = Depends(current_user)) -> list[dict]:
    try:
        return list_faculties_admin(user["username"], tenant_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/admin/tenant-faculties")
def admin_tenant_faculty_save(payload: TenantFacultyPayload, user: dict = Depends(current_user)) -> dict:
    try:
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        return save_faculty_admin(user["username"], data)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/admin/tenant-dashboard")
def admin_tenant_dashboard(user: dict = Depends(current_user)) -> dict:
    try:
        return tenant_dashboard_admin(user["username"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/admin/tenant-setup")
def admin_tenant_setup(user: dict = Depends(current_user)) -> dict:
    try:
        return tenant_setup_status_admin(user["username"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

@app.get("/api/admin/program-users")
def admin_program_users(program_id: str | None = None, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return list_program_users_admin(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/admin/program-users")
def admin_program_user_save(payload: ProgramAssignmentPayload, background_tasks: BackgroundTasks, user: dict = Depends(current_user)) -> list[dict]:
    try:
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        rows = assign_user_to_program_admin(user["username"], data)
        notify_program_assignment(
            user["username"],
            str(data.get("username", "") or ""),
            [str(item) for item in data.get("program_ids", [])],
            str(data.get("role", "") or ""),
            background_tasks,
        )
        return rows
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/admin/login-attempts")
def admin_login_attempts(limit: int = 100, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return login_attempt_rows_admin(user["username"], limit)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/admin/notifications")
def admin_notifications(limit: int = 100, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return list_notification_events_admin(user["username"], limit)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/admin/mail/status")
def admin_mail_status(user: dict = Depends(current_user)) -> dict:
    try:
        # Reuse the admin-only notification listing guard instead of exposing SMTP
        # diagnostics to non-admin users. Passwords/secrets are never returned.
        list_notification_events_admin(user["username"], 1)
        return mail_system_status()
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/admin/mail/settings")
def admin_mail_settings(user: dict = Depends(current_user)) -> dict:
    try:
        return get_mail_settings_admin(user["username"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.put("/api/admin/mail/settings")
def admin_mail_settings_update(payload: MailSettingsPayload, user: dict = Depends(current_user)) -> dict:
    try:
        return update_mail_settings_admin(user["username"], payload.model_dump())
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/admin/mail/test")
def admin_mail_test(payload: MailTestPayload, background_tasks: BackgroundTasks, user: dict = Depends(current_user)) -> dict:
    try:
        return send_test_mail_admin(user["username"], payload.model_dump(), background_tasks)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc




@app.get("/api/admin/update-center")
def admin_update_center(user: dict = Depends(current_user)) -> dict:
    try:
        return list_update_center_payload(user["username"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/admin/update-center/check")
def admin_update_center_check(payload: dict[str, Any] | None = None, user: dict = Depends(current_user)) -> dict:
    try:
        data = payload or {}
        return run_update_center_check(user["username"], str(data.get("scope") or "all"), bool(data.get("online") or False))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/admin/update-center/candidates/{candidate_id}/apply")
def admin_update_center_apply(candidate_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return apply_update_candidate(user["username"], candidate_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/admin/update-center/candidates/{candidate_id}/ignore")
def admin_update_center_ignore(candidate_id: str, payload: dict[str, Any] | None = None, user: dict = Depends(current_user)) -> dict:
    try:
        return ignore_update_candidate(user["username"], candidate_id, str((payload or {}).get("note") or ""))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/admin/system-templates")
def admin_system_templates(user: dict = Depends(current_user)) -> list[dict]:
    try:
        return list_system_templates_admin(user["username"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/admin/system-templates/seed")
def admin_system_templates_seed(user: dict = Depends(current_user)) -> dict:
    try:
        return seed_system_templates_admin(user["username"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/admin/system-templates/restore-missing-sections")
def admin_system_templates_restore_missing_sections(program_id: str | None = None, user: dict = Depends(current_user)) -> dict:
    try:
        return restore_missing_program_sections_admin(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/users")
def users(include_deleted: bool = False, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return list_users_admin(user["username"], include_deleted=include_deleted)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/users")
def user_save(payload: UserPayload, background_tasks: BackgroundTasks, user: dict = Depends(current_user)) -> dict:
    try:
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        saved = upsert_user_admin(user["username"], data)
        notify_user_saved(user["username"], saved, bool(str(data.get("password", "") or "").strip()), background_tasks)
        return saved
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/users/{target_username}")
def user_delete(target_username: str, user: dict = Depends(current_user)) -> dict:
    try:
        return delete_user_admin(user["username"], target_username)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/settings")
def settings(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return get_settings_for_user(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.put("/api/programs/{program_id}/settings")
def settings_update(program_id: str, payload: SettingsPayload, user: dict = Depends(current_user)) -> dict:
    try:
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        return update_settings_admin(user["username"], program_id, data)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/dashboard")
def program_dashboard(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return dashboard(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/stats")
def program_stats(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return stats_payload(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/insights")
def program_insights_endpoint(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return program_insights(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/help")
def program_help_endpoint(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return program_help(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc




@app.get("/api/programs/{program_id}/activity-timeline")
def program_activity_timeline(program_id: str, limit: int = 200, user: dict = Depends(current_user)) -> dict:
    try:
        return activity_timeline(user["username"], program_id, limit)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/advanced-reporting")
def program_advanced_reporting(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return advanced_reporting(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc




@app.get("/api/programs/{program_id}/advanced-reporting/docx")
def program_advanced_reporting_docx(program_id: str, user: dict = Depends(current_user)) -> Response:
    try:
        data = build_advanced_analytics_docx(user["username"], program_id)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": 'attachment; filename="AKYS_advanced_analytics_dashboard.docx"'},
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/advanced-reporting/pdf")
def program_advanced_reporting_pdf(program_id: str, user: dict = Depends(current_user)) -> Response:
    try:
        docx_data = build_advanced_analytics_docx(user["username"], program_id)
        pdf_data = convert_docx_to_pdf(docx_data, "AKYS_advanced_analytics_dashboard")
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="AKYS_advanced_analytics_dashboard.pdf"'},
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc




@app.get("/api/programs/{program_id}/professional-reporting")
def professional_reporting(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return professional_reporting_payload(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/professional-reporting/consistency")
def professional_reporting_consistency(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return consistency_check_payload(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/professional-reporting/quality")
def professional_reporting_quality(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return report_quality_payload(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/professional-reporting/mock-audit")
def professional_reporting_mock_audit(program_id: str, sample_size: int = 5, user: dict = Depends(current_user)) -> dict:
    try:
        return mock_audit_payload(user["username"], program_id, sample_size=sample_size)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/professional-reporting/clauses")
def professional_reporting_clauses(program_id: str, section_key: str = "", user: dict = Depends(current_user)) -> list[dict]:
    try:
        return list_clause_library(user["username"], program_id, section_key=section_key)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/programs/{program_id}/professional-reporting/clauses/seed")
def professional_reporting_seed_clauses(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return seed_clause_library(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/programs/{program_id}/professional-reporting/clauses")
def professional_reporting_create_clause(program_id: str, payload: dict[str, Any], user: dict = Depends(current_user)) -> dict:
    try:
        return create_clause(user["username"], program_id, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/programs/{program_id}/sections/{section_key}/professional-reporting/clauses/{clause_id}/insert")
def professional_reporting_insert_clause(program_id: str, section_key: str, clause_id: str, payload: dict[str, Any] | None = None, user: dict = Depends(current_user)) -> dict:
    try:
        return insert_clause_into_section(user["username"], program_id, section_key, clause_id, str((payload or {}).get("position", "append")))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Clause veya başlık bulunamadı.") from exc


@app.get("/api/programs/{program_id}/sections/{section_key}/professional-reporting/sentence-diff")
def professional_reporting_sentence_diff(program_id: str, section_key: str, base_id: str = "", user: dict = Depends(current_user)) -> dict:
    try:
        return sentence_diff_payload(user["username"], program_id, section_key, base_id=base_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.") from exc


@app.get("/api/programs/{program_id}/professional-reporting/package.zip")
def professional_reporting_package(program_id: str, request: Request, user: dict = Depends(current_user)) -> Response:
    try:
        data = build_report_package_zip(user["username"], program_id, base_url=str(request.base_url).rstrip("/"), auditor=False)
        return Response(content=data, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{PACKAGE_FILENAME}"'})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/professional-reporting/auditor-package.zip")
def professional_reporting_auditor_package(program_id: str, request: Request, user: dict = Depends(current_user)) -> Response:
    try:
        data = build_report_package_zip(user["username"], program_id, base_url=str(request.base_url).rstrip("/"), auditor=True)
        return Response(content=data, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{AUDITOR_PACKAGE_FILENAME}"'})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/professional-reporting/auditor-links")
def professional_reporting_auditor_links(program_id: str, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return list_auditor_share_links(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/programs/{program_id}/professional-reporting/auditor-links")
def professional_reporting_create_auditor_link(program_id: str, payload: dict[str, Any], user: dict = Depends(current_user)) -> dict:
    try:
        return create_auditor_share_link(user["username"], program_id, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

@app.get("/api/programs/{program_id}/sections/{section_key}/versions")
def program_section_versions(program_id: str, section_key: str, user: dict = Depends(current_user)) -> dict:
    try:
        return section_versions_diff(user["username"], program_id, section_key)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/section-permissions")
def program_section_permissions(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        # list_sections applies program access and tenant/assignment visibility before the policy is returned.
        list_sections(user["username"], program_id)
        return section_permission_payload(program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.put("/api/programs/{program_id}/section-permissions")
def program_section_permissions_update(program_id: str, payload: dict[str, Any], user: dict = Depends(current_user)) -> dict:
    role = normalized_role(str(user.get("role", "")), str(user.get("tenant_scope", "") or ""))
    if not (is_admin_role(role) or role == FACULTY_ADMIN_ROLE):
        raise HTTPException(status_code=403, detail="Bölüm bazlı yetki politikası yalnızca Süper Admin, Kurum Admin veya yetkilendirilmiş Birim Admin tarafından güncellenebilir.")
    try:
        assert_program_operation_permission(user["username"], program_id, "program.assign_users")
        list_sections(user["username"], program_id)
        return update_section_permission_policy(program_id, payload.get("rows", []), user["username"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

@app.get("/api/programs/{program_id}/workflow/reminders")
def workflow_reminders(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return workflow_reminders_payload(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/workflow/automation/settings")
def workflow_automation_settings_endpoint(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return workflow_automation_settings(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.put("/api/programs/{program_id}/workflow/automation/settings")
def workflow_automation_settings_update(program_id: str, payload: dict[str, Any], user: dict = Depends(current_user)) -> dict:
    try:
        return update_workflow_automation_settings(user["username"], program_id, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/workflow/automation/preview")
def workflow_automation_preview_endpoint(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return workflow_automation_preview(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/workflow/automation/runs")
def workflow_automation_runs_endpoint(program_id: str, limit: int = 30, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return workflow_automation_runs(user["username"], program_id, limit)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/programs/{program_id}/workflow/automation/run")
def workflow_automation_run_endpoint(program_id: str, payload: dict[str, Any], background_tasks: BackgroundTasks, user: dict = Depends(current_user)) -> dict:
    try:
        return run_workflow_automation(user["username"], program_id, payload, background_tasks)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/notifications/inbox")
def notification_inbox_endpoint(program_id: str, limit: int = 100, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return notification_inbox(user["username"], program_id, limit)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.put("/api/programs/{program_id}/notifications/read")
def notification_read_endpoint(program_id: str, payload: NotificationReadPayload, user: dict = Depends(current_user)) -> dict:
    try:
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        return mark_notifications_read(user["username"], program_id, data.get("event_ids", []))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/audit/docx")
def audit_docx(program_id: str, user: dict = Depends(current_user)) -> Response:
    try:
        settings = get_settings(program_id)
        data = build_readiness_audit_docx(user["username"], program_id)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{safe_download_name(settings.get("audit_filename", "AKYS_hazirlik_denetimi.docx"))}"'},
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc



@app.get("/api/programs/{program_id}/compliance")
def program_compliance(program_id: str, limit: int = 500, user: dict = Depends(current_user)) -> dict:
    try:
        return compliance_audit_payload(user["username"], program_id, limit)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/compliance/docx")
def program_compliance_docx(program_id: str, user: dict = Depends(current_user)) -> Response:
    try:
        settings = get_settings(program_id)
        data = build_compliance_audit_docx(user["username"], program_id)
        filename = safe_download_name(settings.get("compliance_filename", "AKYS_uygunluk_denetimi.docx"))
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/search")
def program_search(program_id: str, q: str = "", user: dict = Depends(current_user)) -> list[dict]:
    try:
        return search_sections(user["username"], program_id, q)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/sections")
def sections(program_id: str, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return list_sections(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/report-studio")
def report_studio(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return report_studio_payload(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/programs/{program_id}/sections/{section_key}/ai/suggestions")
def section_ai_suggestions(program_id: str, section_key: str, payload: dict[str, Any] | None = None, user: dict = Depends(current_user)) -> dict:
    try:
        return quick_ai_suggestions(user["username"], program_id, section_key, str((payload or {}).get("mode", "coach")))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.") from exc


@app.post("/api/programs/{program_id}/sections/{section_key}/accreditation/gap-scan")
def section_accreditation_gap_scan(program_id: str, section_key: str, user: dict = Depends(current_user)) -> dict:
    try:
        return accreditation_gap_scan(user["username"], program_id, section_key)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.") from exc


@app.post("/api/programs/{program_id}/sections/{section_key}/accreditation/evidence-match")
def section_evidence_matching(program_id: str, section_key: str, user: dict = Depends(current_user)) -> dict:
    try:
        return evidence_matching_assistant(user["username"], program_id, section_key)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.") from exc


@app.post("/api/programs/{program_id}/sections/{section_key}/quality/recalculate")
def section_quality_recalculate(program_id: str, section_key: str, user: dict = Depends(current_user)) -> dict:
    try:
        return recalculate_section_quality(user["username"], program_id, section_key)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.") from exc


@app.get("/api/programs/{program_id}/sections/{section_key}/templates/bank")
def section_templates_bank(program_id: str, section_key: str, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return section_template_bank(user["username"], program_id, section_key)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.") from exc


@app.post("/api/programs/{program_id}/templates/bank")
def create_template_bank_item(program_id: str, payload: dict[str, Any], user: dict = Depends(current_user)) -> dict:
    try:
        return create_section_template(user["username"], program_id, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/programs/{program_id}/sections/{section_key}/collaboration/ping")
def section_collaboration_ping(program_id: str, section_key: str, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return collaboration_ping(user["username"], program_id, section_key)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.") from exc


@app.get("/api/programs/{program_id}/sections/{section_key}/collaboration")
def section_collaboration(program_id: str, section_key: str, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return active_collaborators(user["username"], program_id, section_key)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.") from exc


@app.get("/api/programs/{program_id}/sections/{section_key}/export/docx")
def section_export_docx(program_id: str, section_key: str, user: dict = Depends(current_user)) -> Response:
    try:
        data = section_docx_bytes(user["username"], program_id, section_key)
        return Response(content=data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": f'attachment; filename="{safe_download_name(section_key)}.docx"'})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.") from exc


@app.get("/api/programs/{program_id}/sections/{section_key}/export/pdf")
def section_export_pdf(program_id: str, section_key: str, user: dict = Depends(current_user)) -> Response:
    try:
        docx_data = section_docx_bytes(user["username"], program_id, section_key)
        pdf_data = convert_docx_to_pdf(docx_data, f"section_{safe_download_name(section_key)}")
        return Response(content=pdf_data, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{safe_download_name(section_key)}.pdf"'})
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.") from exc


@app.put("/api/programs/{program_id}/bulk/studio")
def bulk_studio(program_id: str, payload: dict[str, Any], user: dict = Depends(current_user)) -> dict:
    try:
        return bulk_studio_update(user["username"], program_id, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/sections/{section_key}")
def section_detail(program_id: str, section_key: str, user: dict = Depends(current_user)) -> dict:
    try:
        section = get_section(user["username"], program_id, section_key)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not section:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.")
    return section


@app.put("/api/programs/{program_id}/sections/{section_key}")
def section_update(program_id: str, section_key: str, payload: SectionUpdate, user: dict = Depends(current_user)) -> dict:
    try:
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        return update_section(user["username"], program_id, section_key, data)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.") from exc


@app.get("/api/programs/{program_id}/evidence/studio")
def evidence_studio(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return evidence_archive_studio_payload(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/evidence")
def evidence(program_id: str, section_key: str | None = None, user: dict = Depends(current_user)) -> list[dict]:
    try:
        assert_program_operation_permission(user["username"], program_id, "evidence.view")
        return list_evidence(user["username"], program_id, section_key)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/programs/{program_id}/evidence")
async def evidence_upload(
    program_id: str,
    file: UploadFile = File(...),
    section_keys: str = Form(...),
    code: str = Form(...),
    note: str = Form(default=""),
    user: dict = Depends(current_user),
) -> dict:
    try:
        raw_keys = json.loads(section_keys) if section_keys.strip().startswith("[") else section_keys.split(",")
        data = await _read_upload_limited(file, max_bytes=MEDEK_MAX_UPLOAD_BYTES, max_mb=MEDEK_MAX_UPLOAD_MB, label="Dosya")
        return save_evidence_file(
            user["username"],
            program_id,
            [str(key) for key in raw_keys],
            code,
            note,
            file.filename or "kanit",
            data,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/programs/{program_id}/evidence/link")
def evidence_link(program_id: str, payload: EvidenceLinkPayload, user: dict = Depends(current_user)) -> dict:
    try:
        assert_program_operation_permission(user["username"], program_id, "evidence.link")
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        return link_evidence_to_section(
            user["username"],
            program_id,
            data["evidence_id"],
            data["section_key"],
            data.get("code", ""),
            data.get("note", ""),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Kanıt veya başlık bulunamadı.") from exc


@app.get("/api/programs/{program_id}/evidence/{evidence_id}/download")
def evidence_download(program_id: str, evidence_id: str, user: dict = Depends(current_user)) -> FileResponse:
    try:
        path, evidence_row = evidence_file_path(user["username"], program_id, evidence_id)
        return FileResponse(path, filename=safe_download_name(evidence_row.get("original_name", path.name)))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Kanıt bulunamadı.") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Kanıt dosyası bulunamadı.") from exc


@app.delete("/api/programs/{program_id}/evidence/{evidence_id}")
def evidence_delete(program_id: str, evidence_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        assert_program_operation_permission(user["username"], program_id, "evidence.delete")
        delete_evidence_file(user["username"], program_id, evidence_id)
        return {"ok": True}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Kanıt bulunamadı.") from exc


@app.get("/api/programs/{program_id}/tables/studio")
def tables_studio(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return table_management_studio_payload(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/tables")
def tables(program_id: str, section_key: str | None = None, user: dict = Depends(current_user)) -> list[dict]:
    try:
        assert_program_operation_permission(user["username"], program_id, "table.view")
        return list_tables(user["username"], program_id, section_key)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/programs/{program_id}/tables")
def table_save(program_id: str, payload: TablePayload, user: dict = Depends(current_user)) -> dict:
    try:
        assert_program_operation_permission(user["username"], program_id, "table.edit")
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        return save_table(user["username"], program_id, data["section_key"], data["table_name"], data.get("rows", []), data.get("meta", {}), data.get("table_id", ""))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/programs/{program_id}/tables/attach")
def table_attach(program_id: str, payload: TableAttachPayload, user: dict = Depends(current_user)) -> dict:
    try:
        assert_program_operation_permission(user["username"], program_id, "table.attach")
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        return attach_table_to_section(user["username"], program_id, data["table_id"], data["section_key"], data.get("table_name", ""))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Tablo veya başlık bulunamadı.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/programs/{program_id}/tables/{table_id}")
def table_delete(program_id: str, table_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        assert_program_operation_permission(user["username"], program_id, "table.delete")
        delete_table(user["username"], program_id, table_id)
        return {"ok": True}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Tablo bulunamadı.") from exc


@app.get("/api/programs/{program_id}/control")
def control(program_id: str, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return control_rows(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/control/docx")
def control_docx(program_id: str, user: dict = Depends(current_user)) -> Response:
    try:
        settings = get_settings(program_id)
        data = build_control_docx(user["username"], program_id)
        file_name = safe_download_name(settings.get("control_filename", "AKYS_kontrol_tablosu.docx"))
        write_export_copy(get_program(program_id) or {"id": program_id}, file_name=file_name, data=data, export_type="control_docx", actor=user["username"])
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/deadlines")
def deadlines(program_id: str, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return deadline_rows(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.put("/api/programs/{program_id}/deadlines")
def deadlines_update(program_id: str, payload: DeadlinePayload, background_tasks: BackgroundTasks, user: dict = Depends(current_user)) -> list[dict]:
    try:
        before = {row.get("section_key", ""): row for row in deadline_rows(user["username"], program_id)}
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        updated = update_deadlines(user["username"], program_id, data.get("rows", []))
        changed = [
            row for row in updated
            if str(row.get("deadline", "") or "") != str((before.get(row.get("section_key", "")) or {}).get("deadline", "") or "")
        ]
        notify_deadlines_updated(user["username"], program_id, changed, background_tasks)
        return updated
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.put("/api/programs/{program_id}/bulk/status")
def bulk_status_update(program_id: str, payload: BulkStatusPayload, user: dict = Depends(current_user)) -> dict:
    try:
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        return bulk_update_status(user["username"], program_id, data.get("section_keys", []), data.get("status", ""))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/api/programs/{program_id}/bulk/advanced")
def bulk_advanced_update(program_id: str, payload: BulkAdvancedPayload, user: dict = Depends(current_user)) -> dict:
    try:
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        return bulk_update_advanced(user["username"], program_id, data.get("section_keys", []), data.get("status", ""), data.get("deadline", ""))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/preview")
def preview(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return preview_payload(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Report preview failed for program_id=%s user=%s", program_id, user.get("username"))
        raise HTTPException(status_code=500, detail=f"Rapor önizleme üretilemedi: {exc}") from exc


@app.get("/api/programs/{program_id}/report/preflight")
def report_preflight(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return report_preflight_payload(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/report/docx")
def report_docx(program_id: str, request: Request, force: bool = False, user: dict = Depends(current_user)) -> Response:
    try:
        if not force:
            assert_report_export_ready(user["username"], program_id)
        settings = get_settings(program_id)
        data = build_final_docx(user["username"], program_id, base_url=str(request.base_url).rstrip("/"))
        file_name = safe_download_name(settings.get("docx_filename", "AKYS_ODR.docx"))
        write_export_copy(get_program(program_id) or {"id": program_id}, file_name=file_name, data=data, export_type="docx", actor=user["username"])
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/report/pdf")
def report_pdf(program_id: str, request: Request, force: bool = False, user: dict = Depends(current_user)) -> Response:
    try:
        if not force:
            assert_report_export_ready(user["username"], program_id)
        settings = get_settings(program_id)
        docx_data = build_final_docx(user["username"], program_id, base_url=str(request.base_url).rstrip("/"))
        pdf_name = safe_download_name(settings.get("pdf_filename", "AKYS_ODR.pdf"))
        pdf_data = convert_docx_to_pdf(docx_data, pdf_name.rsplit(".", 1)[0])
        write_export_copy(get_program(program_id) or {"id": program_id}, file_name=pdf_name, data=pdf_data, export_type="pdf", actor=user["username"])
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{pdf_name}"'},
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/programs/{program_id}/report/jobs")
def report_job_create(
    program_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
    export_type: str = "docx",
    force: bool = False,
    user: dict = Depends(current_user),
) -> dict:
    try:
        return enqueue_export_job(
            user["username"],
            program_id,
            export_type,
            background_tasks,
            base_url=str(request.base_url).rstrip("/"),
            force=force,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/report/jobs")
def report_jobs(program_id: str, limit: int = 50, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return list_export_jobs(user["username"], program_id, limit)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/report/jobs/{job_id}")
def report_job_detail(program_id: str, job_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return get_export_job(user["username"], program_id, job_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Çıktı işi bulunamadı.") from exc


@app.get("/api/programs/{program_id}/report/jobs/{job_id}/download")
def report_job_download(program_id: str, job_id: str, user: dict = Depends(current_user)) -> FileResponse:
    try:
        path, file_name, media_type = export_job_file(user["username"], program_id, job_id)
        return FileResponse(path, filename=file_name, media_type=media_type)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Çıktı işi bulunamadı.") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Çıktı dosyası bulunamadı.") from exc


@app.get("/api/programs/{program_id}/exports")
def exports(program_id: str, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return export_history(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/activity")
def activity(program_id: str, limit: int = 100, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return activity_rows(user["username"], program_id, limit)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/system")
def system(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        return system_status(user["username"], program_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/backup/json")
def backup_json(program_id: str, user: dict = Depends(current_user)) -> JSONResponse:
    try:
        settings = get_settings(program_id)
        payload = backup_payload(user["username"], program_id)
        return JSONResponse(
            content=payload,
            headers={"Content-Disposition": f'attachment; filename="{safe_download_name(settings.get("backup_filename", "AKYS_yedek.json"))}"'},
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc




@app.get("/api/me/backup/personal.zip")
def personal_backup_all_programs(user: dict = Depends(current_user)) -> Response:
    try:
        data = build_all_personal_backup_zip(user["username"])
        filename = personal_backup_filename(user["username"])
        return Response(
            content=data,
            media_type=ZIP_MEDIA_TYPE,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/backup/personal.zip")
def personal_backup_program(program_id: str, user: dict = Depends(current_user)) -> Response:
    try:
        data = build_program_personal_backup_zip(user["username"], program_id)
        filename = personal_backup_filename(user["username"], program_id)
        return Response(
            content=data,
            media_type=ZIP_MEDIA_TYPE,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/programs/{program_id}/backup/restore")
async def backup_restore(
    program_id: str,
    file: UploadFile = File(...),
    overwrite: bool = Form(default=False),
    user: dict = Depends(current_user),
) -> dict:
    try:
        raw = await _read_upload_limited(file, max_bytes=MEDEK_MAX_BACKUP_BYTES, max_mb=MEDEK_MAX_BACKUP_MB, label="Yedek dosyası")
        payload = json.loads(raw.decode("utf-8-sig"))
        return restore_backup_payload_admin(user["username"], program_id, payload, overwrite)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Geçerli bir JSON yedek dosyası seçin.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _import_report_upload(
    program_id: str,
    file: UploadFile = File(...),
    overwrite_empty_only: bool = Form(default=True),
    user: dict = Depends(current_user),
) -> dict:
    try:
        data = await _read_upload_limited(file, max_bytes=MEDEK_MAX_UPLOAD_BYTES, max_mb=MEDEK_MAX_UPLOAD_MB, label="Rapor dosyası")
        return import_report_file(user["username"], program_id, file.filename or "rapor", data, overwrite_empty_only)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/programs/{program_id}/report/import")
async def report_import(
    program_id: str,
    file: UploadFile = File(...),
    overwrite_empty_only: bool = Form(default=True),
    user: dict = Depends(current_user),
) -> dict:
    return await _import_report_upload(program_id, file, overwrite_empty_only, user)


@app.post("/api/programs/{program_id}/docx/import")
async def docx_import(
    program_id: str,
    file: UploadFile = File(...),
    overwrite_empty_only: bool = Form(default=True),
    user: dict = Depends(current_user),
) -> dict:
    return await _import_report_upload(program_id, file, overwrite_empty_only, user)


@app.get("/api/programs/{program_id}/ai/status")
def ai_status(program_id: str, user: dict = Depends(current_user)) -> dict:
    try:
        list_sections(user["username"], program_id)
        return ollama_status()
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/programs/{program_id}/ai/sections/{section_key}/draft")
def ai_section_draft(program_id: str, section_key: str, target_words: int = 650, user: dict = Depends(current_user)) -> dict:
    try:
        return ai_draft_for_section(user["username"], program_id, section_key, target_words)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.") from exc


@app.post("/api/programs/{program_id}/ai/full-report")
def ai_full_report(program_id: str, include_all: bool = False, target_words: int = 650, user: dict = Depends(current_user)) -> list[dict]:
    try:
        return full_ai_draft_candidates(user["username"], program_id, include_all, target_words)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/programs/{program_id}/ai/sections/{section_key}/apply")
def ai_section_apply(program_id: str, section_key: str, payload: dict[str, Any], user: dict = Depends(current_user)) -> dict:
    try:
        return apply_ai_draft_to_section(user["username"], program_id, section_key, str(payload.get("text", "")))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/programs/{program_id}/approval/history")
def approval_history_endpoint(program_id: str, section_key: str = "", user: dict = Depends(current_user)) -> list[dict]:
    try:
        return approval_history(user["username"], program_id, section_key)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.post("/api/programs/{program_id}/approval")
def approval(program_id: str, payload: ApprovalRequest, background_tasks: BackgroundTasks, user: dict = Depends(current_user)) -> dict:
    try:
        section = approval_action(user["username"], program_id, payload.section_key, payload.action, payload.note)
        notify_approval_event(user["username"], program_id, payload.section_key, payload.action, payload.note, section, background_tasks)
        return section
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Başlık bulunamadı.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
