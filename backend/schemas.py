from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class UserPublic(BaseModel):
    username: str
    role: str
    full_name: str = ""
    email: str = ""
    academic_status: str = ""
    must_change_password: bool = False


class UserPayload(BaseModel):
    username: str = Field(min_length=1)
    password: str = ""
    role: str
    tenant_id: str = "tenant_default"
    tenant_scope: str = "tenant"
    faculty_name: str = ""
    full_name: str = ""
    email: str = ""
    academic_status: str = ""
    is_active: bool = True


class ProgramPayload(BaseModel):
    tenant_id: str = "tenant_default"
    university_name: str = ""
    school_name: str = ""
    faculty_name: str = ""
    department_name: str = ""
    program_name: str = Field(min_length=1)
    report_year: str = "2025"
    report_type: str = "ÖZ DEĞERLENDİRME RAPORU"
    accreditation_profile: str = "MEDEK"
    is_active: bool = True


class ProgramClonePayload(BaseModel):
    source_program_id: str = Field(min_length=1)
    tenant_id: str = ""
    faculty_name: str = ""
    program_name: str = Field(min_length=1)
    report_year: str = "2025"
    copy_text: bool = True
    copy_tables: bool = False
    copy_evidence_meta: bool = False




class TenantPayload(BaseModel):
    id: str = ""
    name: str = Field(min_length=1)
    code: str = ""
    domain: str = ""
    source_url: str = ""
    is_active: bool = True


class AcademicCatalogImportPayload(BaseModel):
    tenant_id: str = ""
    tenant_name: str = ""
    name: str = ""
    code: str = ""
    domain: str = ""
    source_url: str = ""
    report_year: str = "2025"
    create_programs: bool = True


class TenantFacultyPayload(BaseModel):
    id: str = ""
    tenant_id: str = "tenant_default"
    faculty_name: str = Field(min_length=1)
    accreditation_profile: str = "MEDEK"
    is_active: bool = True


class ProgramAssignmentPayload(BaseModel):
    username: str = Field(min_length=1)
    program_ids: list[str] = Field(default_factory=list)
    role: str
    assigned_sections: str = ""
    is_active: bool = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class ChangePasswordPayload(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=10)


class SectionUpdate(BaseModel):
    status: str
    report_text: str = ""
    planla: str = ""
    uygula: str = ""
    kontrol: str = ""
    onlem: str = ""
    notes: str = ""
    deadline: str | None = None
    is_autosave: bool = False


class ApprovalRequest(BaseModel):
    section_key: str
    action: str
    note: str = ""


class TablePayload(BaseModel):
    table_id: str = ""
    section_key: str
    table_name: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class EvidenceLinkPayload(BaseModel):
    evidence_id: str = Field(min_length=1)
    section_key: str = Field(min_length=1)
    code: str = ""
    note: str = ""


class TableAttachPayload(BaseModel):
    table_id: str = Field(min_length=1)
    section_key: str = Field(min_length=1)
    table_name: str = ""


class DeadlinePayload(BaseModel):
    rows: list[dict[str, str]] = Field(default_factory=list)


class BulkStatusPayload(BaseModel):
    section_keys: list[str] = Field(default_factory=list)
    status: str


class BulkAdvancedPayload(BaseModel):
    section_keys: list[str] = Field(default_factory=list)
    status: str = ""
    deadline: str = ""


class NotificationReadPayload(BaseModel):
    event_ids: list[str] = Field(default_factory=list)


class SettingsPayload(BaseModel):
    university: str = ""
    school: str = ""
    department: str = ""
    program: str = ""
    report_year: str = ""
    report_type: str = ""
    accreditation_profile: str = "MEDEK"
    report_no: str = ""
    doc_date: str = ""
    rev_date: str = ""
    rev_no: str = ""


class MailSettingsPayload(BaseModel):
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    clear_password: bool = False
    smtp_from: str = ""
    tls: bool = True
    ssl: bool = False
    app_base_url: str = ""


class MailTestPayload(BaseModel):
    to: str = ""
    subject: str = "MEDEK test e-postası"
    body: str = "Bu e-posta Akreditasyon Kalite Yönetim Sistemi SMTP ayarlarını test etmek için gönderilmiştir."


class ApiEnvelope(BaseModel):
    ok: bool = True
    data: Any | None = None
    message: str = ""
