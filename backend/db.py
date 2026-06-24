from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
import os
from typing import Any, Iterator

from .config import DATA_DIR, EVIDENCE_DIR, ORG_STORAGE_DIR, SQLITE_PATH, MEDEK_DATABASE_URL, MEDEK_DB_BACKEND


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_conn():
    if MEDEK_DB_BACKEND == "postgresql":
        from .db_postgres import connect_postgres
        return connect_postgres(MEDEK_DATABASE_URL)
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.DatabaseError:
        pass
    return conn


def db_backend() -> str:
    return MEDEK_DB_BACKEND


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [row_to_dict(row) or {} for row in rows]


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT DEFAULT '',
    domain TEXT DEFAULT '',
    source_url TEXT DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT '',
    deleted_at TEXT DEFAULT '',
    deleted_by TEXT DEFAULT '',
    created_by TEXT DEFAULT '',
    setup_completed_at TEXT DEFAULT '',
    appearance_package TEXT DEFAULT 'corporate_blue',
    appearance_config_json TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS tenant_faculties (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    faculty_name TEXT NOT NULL,
    accreditation_profile TEXT DEFAULT 'MEDEK',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT '',
    deleted_at TEXT DEFAULT '',
    deleted_by TEXT DEFAULT '',
    UNIQUE(tenant_id, faculty_name)
);

CREATE TABLE IF NOT EXISTS activity_log (
    id TEXT PRIMARY KEY,
    ts TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT DEFAULT '',
    actor TEXT DEFAULT '',
    program_id TEXT DEFAULT '',
    tenant_id TEXT DEFAULT 'tenant_default'
);

CREATE TABLE IF NOT EXISTS data_tables (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    section_key TEXT NOT NULL,
    table_name TEXT NOT NULL,
    data_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT DEFAULT '',
    deleted_by TEXT DEFAULT '',
    UNIQUE(program_id, section_key, table_name)
);

CREATE TABLE IF NOT EXISTS edit_locks (
    program_id TEXT NOT NULL,
    section_key TEXT NOT NULL,
    actor TEXT NOT NULL,
    locked_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    PRIMARY KEY(program_id, section_key)
);

CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    section_key TEXT NOT NULL,
    code TEXT NOT NULL,
    original_name TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    note TEXT DEFAULT '',
    uploaded_at TEXT NOT NULL,
    deleted_at TEXT DEFAULT '',
    deleted_by TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS evidence_links (
    program_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    section_key TEXT NOT NULL,
    PRIMARY KEY(program_id, evidence_id, section_key)
);

CREATE TABLE IF NOT EXISTS export_history (
    id TEXT PRIMARY KEY,
    program_id TEXT DEFAULT '',
    export_type TEXT NOT NULL,
    file_name TEXT NOT NULL,
    actor TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    note TEXT DEFAULT '',
    tenant_id TEXT DEFAULT 'tenant_default'
);

CREATE TABLE IF NOT EXISTS export_jobs (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    tenant_id TEXT DEFAULT 'tenant_default',
    export_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    file_name TEXT NOT NULL DEFAULT '',
    file_path TEXT NOT NULL DEFAULT '',
    actor TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    error TEXT DEFAULT '',
    progress INTEGER NOT NULL DEFAULT 0,
    message TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id TEXT PRIMARY KEY,
    username TEXT DEFAULT '',
    success INTEGER NOT NULL,
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notification_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    program_id TEXT DEFAULT '',
    section_key TEXT DEFAULT '',
    actor TEXT DEFAULT '',
    recipients_json TEXT NOT NULL DEFAULT '[]',
    subject TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'queued',
    tenant_id TEXT DEFAULT 'tenant_default',
    error TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    sent_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS notification_reads (
    event_id TEXT NOT NULL,
    username TEXT NOT NULL,
    read_at TEXT NOT NULL,
    PRIMARY KEY(event_id, username)
);


CREATE TABLE IF NOT EXISTS program_users (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    username TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Denetçi',
    tenant_id TEXT DEFAULT 'tenant_default',
    assigned_sections TEXT DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    deleted_at TEXT DEFAULT '',
    deleted_by TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT '',
    UNIQUE(program_id, username)
);

CREATE TABLE IF NOT EXISTS programs (
    id TEXT PRIMARY KEY,
    university_name TEXT NOT NULL DEFAULT '',
    school_name TEXT NOT NULL DEFAULT '',
    department_name TEXT DEFAULT '',
    program_name TEXT NOT NULL,
    report_year TEXT DEFAULT '2025',
    report_type TEXT DEFAULT 'ÖZ DEĞERLENDİRME RAPORU',
    is_active INTEGER NOT NULL DEFAULT 1,
    deleted_at TEXT DEFAULT '',
    deleted_by TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT '',
    accreditation_profile TEXT NOT NULL DEFAULT 'MEDEK',
    tenant_id TEXT DEFAULT 'tenant_default',
    faculty_name TEXT DEFAULT '',
    program_degree TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS section_approvals (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    section_key TEXT NOT NULL,
    status TEXT NOT NULL,
    requested_by TEXT DEFAULT '',
    decided_by TEXT DEFAULT '',
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS section_comments (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    section_key TEXT NOT NULL,
    actor TEXT DEFAULT '',
    comment TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS section_collaboration_sessions (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    section_key TEXT NOT NULL,
    username TEXT NOT NULL,
    display_name TEXT DEFAULT '',
    started_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    status TEXT DEFAULT 'editing',
    tenant_id TEXT DEFAULT 'tenant_default',
    UNIQUE(program_id, section_key, username)
);

CREATE TABLE IF NOT EXISTS section_template_bank (
    id TEXT PRIMARY KEY,
    tenant_id TEXT DEFAULT 'tenant_default',
    program_id TEXT DEFAULT '',
    section_key TEXT DEFAULT '',
    profile TEXT DEFAULT '',
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT DEFAULT '',
    source TEXT DEFAULT 'manual',
    created_by TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS section_versions (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    section_key TEXT NOT NULL,
    saved_at TEXT NOT NULL,
    status TEXT NOT NULL,
    report_text TEXT DEFAULT '',
    planla TEXT DEFAULT '',
    uygula TEXT DEFAULT '',
    kontrol TEXT DEFAULT '',
    onlem TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    deadline TEXT DEFAULT '',
    change_summary TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sections (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    section_key TEXT NOT NULL,
    main_title TEXT NOT NULL,
    section_title TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'Başlamadı',
    report_text TEXT DEFAULT '',
    planla TEXT DEFAULT '',
    uygula TEXT DEFAULT '',
    kontrol TEXT DEFAULT '',
    onlem TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    deadline TEXT DEFAULT '',
    approval_status TEXT DEFAULT 'Taslak',
    approved_by TEXT DEFAULT '',
    approved_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT '',
    responsible_username TEXT DEFAULT '',
    quality_score INTEGER NOT NULL DEFAULT 0,
    risk_level TEXT DEFAULT '',
    ai_suggestions_json TEXT DEFAULT '{}',
    last_ai_review_at TEXT DEFAULT '',
    deleted_at TEXT DEFAULT '',
    deleted_by TEXT DEFAULT '',
    UNIQUE(program_id, section_key)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workflow_runs (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    actor TEXT DEFAULT '',
    started_at TEXT NOT NULL,
    finished_at TEXT DEFAULT '',
    mode TEXT DEFAULT 'manual',
    total_candidates INTEGER NOT NULL DEFAULT 0,
    created_notifications INTEGER NOT NULL DEFAULT 0,
    skipped_notifications INTEGER NOT NULL DEFAULT 0,
    summary_json TEXT DEFAULT '{}',
    tenant_id TEXT DEFAULT 'tenant_default'
);

CREATE TABLE IF NOT EXISTS workflow_run_items (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    program_id TEXT NOT NULL,
    section_key TEXT DEFAULT '',
    category TEXT DEFAULT '',
    priority TEXT DEFAULT '',
    recipient_count INTEGER NOT NULL DEFAULT 0,
    notification_id TEXT DEFAULT '',
    status TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    tenant_id TEXT DEFAULT 'tenant_default'
);




CREATE TABLE IF NOT EXISTS source_watchers (
    id TEXT PRIMARY KEY,
    tenant_id TEXT DEFAULT 'global',
    watcher_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT DEFAULT '',
    profile TEXT DEFAULT '',
    cadence TEXT DEFAULT 'weekly',
    is_active INTEGER NOT NULL DEFAULT 1,
    last_checked_at TEXT DEFAULT '',
    last_status TEXT DEFAULT '',
    last_message TEXT DEFAULT '',
    last_hash TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS update_candidates (
    id TEXT PRIMARY KEY,
    tenant_id TEXT DEFAULT 'global',
    source_type TEXT NOT NULL,
    candidate_kind TEXT NOT NULL,
    profile TEXT DEFAULT '',
    title TEXT NOT NULL,
    summary TEXT DEFAULT '',
    old_version TEXT DEFAULT '',
    new_version TEXT DEFAULT '',
    old_hash TEXT DEFAULT '',
    new_hash TEXT DEFAULT '',
    source_url TEXT DEFAULT '',
    payload_json TEXT DEFAULT '{}',
    diff_json TEXT DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT '',
    applied_by TEXT DEFAULT '',
    applied_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS source_check_logs (
    id TEXT PRIMARY KEY,
    tenant_id TEXT DEFAULT 'global',
    source_type TEXT NOT NULL,
    source_name TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT DEFAULT '',
    details_json TEXT DEFAULT '{}',
    checked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clause_library (
    id TEXT PRIMARY KEY,
    tenant_id TEXT DEFAULT 'tenant_default',
    program_id TEXT DEFAULT '',
    section_key TEXT DEFAULT '',
    profile TEXT DEFAULT '',
    criterion_code TEXT DEFAULT '',
    title TEXT NOT NULL,
    clause_type TEXT DEFAULT 'standart',
    content TEXT NOT NULL,
    tags TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    version INTEGER NOT NULL DEFAULT 1,
    created_by TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT '',
    deleted_at TEXT DEFAULT '',
    deleted_by TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS content_blocks (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    section_key TEXT NOT NULL,
    block_type TEXT DEFAULT 'paragraph',
    source_clause_id TEXT DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0,
    content TEXT DEFAULT '',
    metadata_json TEXT DEFAULT '{}',
    created_by TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT DEFAULT '',
    deleted_at TEXT DEFAULT '',
    deleted_by TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS content_block_versions (
    id TEXT PRIMARY KEY,
    block_id TEXT NOT NULL,
    program_id TEXT NOT NULL,
    section_key TEXT NOT NULL,
    version_no INTEGER NOT NULL DEFAULT 1,
    old_content TEXT DEFAULT '',
    new_content TEXT DEFAULT '',
    changed_by TEXT DEFAULT '',
    changed_at TEXT NOT NULL,
    change_summary TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS consistency_check_runs (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    issue_count INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT DEFAULT '{}',
    created_by TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS report_quality_snapshots (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT DEFAULT '{}',
    created_by TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auditor_share_links (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    label TEXT DEFAULT '',
    expires_at TEXT DEFAULT '',
    watermark TEXT DEFAULT 'DENETÇİ KOPYASI',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_by TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    last_access_at TEXT DEFAULT '',
    access_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS system_templates (
    template_key TEXT PRIMARY KEY,
    template_name TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '',
    association_name TEXT DEFAULT '',
    system_name TEXT DEFAULT '',
    report_type TEXT DEFAULT '',
    data_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Editör / Hazırlayıcı',
    tenant_id TEXT DEFAULT 'tenant_default',
    tenant_scope TEXT DEFAULT 'tenant',
    faculty_name TEXT DEFAULT '',
    full_name TEXT DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    must_change_password INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    email TEXT DEFAULT '',
    academic_status TEXT DEFAULT '',
    failed_attempts INTEGER DEFAULT 0,
    locked_until TEXT DEFAULT '',
    last_login TEXT DEFAULT '',
    password_changed_at TEXT DEFAULT '',
    token_version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT DEFAULT '',
    deleted_at TEXT DEFAULT '',
    deleted_by TEXT DEFAULT '',
    created_by TEXT DEFAULT ''
);
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_programs_tenant_active ON programs(tenant_id, is_active, deleted_at);
CREATE INDEX IF NOT EXISTS idx_programs_tenant_faculty ON programs(tenant_id, faculty_name);
CREATE INDEX IF NOT EXISTS idx_users_tenant_role ON users(tenant_id, role, is_active);
CREATE INDEX IF NOT EXISTS idx_users_scope ON users(tenant_scope, tenant_id);
CREATE INDEX IF NOT EXISTS idx_program_users_tenant_program ON program_users(tenant_id, program_id, is_active);
CREATE INDEX IF NOT EXISTS idx_program_users_user_program ON program_users(username, program_id);
CREATE INDEX IF NOT EXISTS idx_sections_program_status ON sections(program_id, status, approval_status);
CREATE INDEX IF NOT EXISTS idx_sections_program_key ON sections(program_id, section_key);
CREATE INDEX IF NOT EXISTS idx_sections_deadline ON sections(program_id, deadline);
CREATE INDEX IF NOT EXISTS idx_collab_section_seen ON section_collaboration_sessions(program_id, section_key, last_seen_at);
CREATE INDEX IF NOT EXISTS idx_template_bank_scope ON section_template_bank(tenant_id, program_id, section_key);
CREATE INDEX IF NOT EXISTS idx_evidence_program_section ON evidence(program_id, section_key);
CREATE INDEX IF NOT EXISTS idx_tables_program_section ON data_tables(program_id, section_key);
CREATE INDEX IF NOT EXISTS idx_activity_tenant_program_ts ON activity_log(tenant_id, program_id, ts);
CREATE INDEX IF NOT EXISTS idx_notifications_tenant_status ON notification_events(tenant_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_notifications_program_created ON notification_events(program_id, created_at);
CREATE INDEX IF NOT EXISTS idx_export_jobs_tenant_program_status ON export_jobs(tenant_id, program_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_program_started ON workflow_runs(program_id, started_at);
CREATE INDEX IF NOT EXISTS idx_workflow_items_run_program ON workflow_run_items(run_id, program_id);

CREATE INDEX IF NOT EXISTS idx_source_watchers_type_active ON source_watchers(watcher_type, is_active, last_checked_at);
CREATE INDEX IF NOT EXISTS idx_update_candidates_status_tenant ON update_candidates(status, tenant_id, source_type, created_at);
CREATE INDEX IF NOT EXISTS idx_source_check_logs_tenant_type ON source_check_logs(tenant_id, source_type, checked_at);

CREATE INDEX IF NOT EXISTS idx_clause_library_scope ON clause_library(tenant_id, profile, program_id, section_key, status);
CREATE INDEX IF NOT EXISTS idx_content_blocks_section ON content_blocks(program_id, section_key, sort_order);
CREATE INDEX IF NOT EXISTS idx_content_block_versions_section ON content_block_versions(program_id, section_key, changed_at);
CREATE INDEX IF NOT EXISTS idx_consistency_runs_program ON consistency_check_runs(program_id, created_at);
CREATE INDEX IF NOT EXISTS idx_quality_snapshots_program ON report_quality_snapshots(program_id, created_at);
CREATE INDEX IF NOT EXISTS idx_auditor_links_program ON auditor_share_links(program_id, is_active, expires_at);
"""


def _ensure_column(conn, table: str, column: str, definition: str) -> None:
    existing = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _apply_lightweight_migrations(conn) -> None:
    # Existing installations may have a users table created before the
    # hardening release. CREATE TABLE IF NOT EXISTS does not add new columns,
    # so keep these additive migrations explicit and idempotent.
    _ensure_column(conn, "users", "must_change_password", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "users", "failed_attempts", "INTEGER DEFAULT 0")
    _ensure_column(conn, "users", "locked_until", "TEXT DEFAULT ''")
    _ensure_column(conn, "users", "last_login", "TEXT DEFAULT ''")
    _ensure_column(conn, "users", "password_changed_at", "TEXT DEFAULT ''")
    _ensure_column(conn, "users", "token_version", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(conn, "users", "updated_at", "TEXT DEFAULT ''")
    _ensure_column(conn, "programs", "deleted_at", "TEXT DEFAULT ''")
    _ensure_column(conn, "programs", "deleted_by", "TEXT DEFAULT ''")
    _ensure_column(conn, "export_jobs", "progress", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "export_jobs", "message", "TEXT DEFAULT ''")
    _ensure_column(conn, "users", "deleted_at", "TEXT DEFAULT ''")
    _ensure_column(conn, "users", "deleted_by", "TEXT DEFAULT ''")
    _ensure_column(conn, "users", "created_by", "TEXT DEFAULT ''")
    _ensure_column(conn, "users", "tenant_id", "TEXT DEFAULT 'tenant_default'")
    _ensure_column(conn, "users", "tenant_scope", "TEXT DEFAULT 'tenant'")
    _ensure_column(conn, "users", "faculty_name", "TEXT DEFAULT ''")
    _ensure_column(conn, "tenants", "setup_completed_at", "TEXT DEFAULT ''")
    _ensure_column(conn, "tenants", "source_url", "TEXT DEFAULT ''")
    _ensure_column(conn, "tenants", "appearance_package", "TEXT DEFAULT 'corporate_blue'")
    _ensure_column(conn, "tenants", "appearance_config_json", "TEXT DEFAULT '{}'")
    _ensure_column(conn, "programs", "tenant_id", "TEXT DEFAULT 'tenant_default'")
    _ensure_column(conn, "programs", "faculty_name", "TEXT DEFAULT ''")
    _ensure_column(conn, "programs", "program_degree", "TEXT DEFAULT ''")
    _ensure_column(conn, "program_users", "tenant_id", "TEXT DEFAULT 'tenant_default'")
    _ensure_column(conn, "activity_log", "tenant_id", "TEXT DEFAULT 'tenant_default'")
    _ensure_column(conn, "notification_events", "tenant_id", "TEXT DEFAULT 'tenant_default'")
    _ensure_column(conn, "export_history", "tenant_id", "TEXT DEFAULT 'tenant_default'")
    _ensure_column(conn, "export_jobs", "tenant_id", "TEXT DEFAULT 'tenant_default'")
    _ensure_column(conn, "program_users", "deleted_at", "TEXT DEFAULT ''")
    _ensure_column(conn, "program_users", "deleted_by", "TEXT DEFAULT ''")
    _ensure_column(conn, "sections", "deleted_at", "TEXT DEFAULT ''")
    _ensure_column(conn, "sections", "deleted_by", "TEXT DEFAULT ''")
    _ensure_column(conn, "sections", "responsible_username", "TEXT DEFAULT ''")
    _ensure_column(conn, "sections", "quality_score", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "sections", "risk_level", "TEXT DEFAULT ''")
    _ensure_column(conn, "sections", "ai_suggestions_json", "TEXT DEFAULT '{}'")
    _ensure_column(conn, "sections", "last_ai_review_at", "TEXT DEFAULT ''")
    _ensure_column(conn, "section_template_bank", "tenant_id", "TEXT DEFAULT 'tenant_default'")
    _ensure_column(conn, "section_template_bank", "program_id", "TEXT DEFAULT ''")
    _ensure_column(conn, "section_template_bank", "section_key", "TEXT DEFAULT ''")
    _ensure_column(conn, "section_template_bank", "profile", "TEXT DEFAULT ''")
    _ensure_column(conn, "section_template_bank", "tags", "TEXT DEFAULT ''")
    _ensure_column(conn, "section_template_bank", "source", "TEXT DEFAULT 'manual'")
    _ensure_column(conn, "section_template_bank", "created_by", "TEXT DEFAULT ''")
    _ensure_column(conn, "section_template_bank", "updated_at", "TEXT DEFAULT ''")
    _ensure_column(conn, "evidence", "deleted_at", "TEXT DEFAULT ''")
    _ensure_column(conn, "evidence", "deleted_by", "TEXT DEFAULT ''")
    _ensure_column(conn, "data_tables", "deleted_at", "TEXT DEFAULT ''")
    _ensure_column(conn, "data_tables", "deleted_by", "TEXT DEFAULT ''")
    _ensure_column(conn, "workflow_runs", "tenant_id", "TEXT DEFAULT 'tenant_default'")
    _ensure_column(conn, "workflow_run_items", "tenant_id", "TEXT DEFAULT 'tenant_default'")

    for table, columns in {
        "source_watchers": {
            "tenant_id": "TEXT DEFAULT 'global'", "last_status": "TEXT DEFAULT ''", "last_message": "TEXT DEFAULT ''", "last_hash": "TEXT DEFAULT ''", "updated_at": "TEXT DEFAULT ''"
        },
        "update_candidates": {
            "tenant_id": "TEXT DEFAULT 'global'", "profile": "TEXT DEFAULT ''", "old_hash": "TEXT DEFAULT ''", "new_hash": "TEXT DEFAULT ''", "source_url": "TEXT DEFAULT ''", "payload_json": "TEXT DEFAULT '{}'", "diff_json": "TEXT DEFAULT '[]'", "applied_by": "TEXT DEFAULT ''", "applied_at": "TEXT DEFAULT ''"
        },
        "source_check_logs": {"tenant_id": "TEXT DEFAULT 'global'", "details_json": "TEXT DEFAULT '{}'"},
    }.items():
        try:
            for column, definition in columns.items():
                _ensure_column(conn, table, column, definition)
        except Exception:
            pass

    for table, columns in {
        "clause_library": {
            "tenant_id": "TEXT DEFAULT 'tenant_default'", "program_id": "TEXT DEFAULT ''", "section_key": "TEXT DEFAULT ''", "profile": "TEXT DEFAULT ''", "criterion_code": "TEXT DEFAULT ''", "clause_type": "TEXT DEFAULT 'standart'", "tags": "TEXT DEFAULT ''", "status": "TEXT DEFAULT 'active'", "version": "INTEGER NOT NULL DEFAULT 1", "updated_at": "TEXT DEFAULT ''", "deleted_at": "TEXT DEFAULT ''", "deleted_by": "TEXT DEFAULT ''"
        },
        "content_blocks": {
            "source_clause_id": "TEXT DEFAULT ''", "metadata_json": "TEXT DEFAULT '{}'", "updated_at": "TEXT DEFAULT ''", "deleted_at": "TEXT DEFAULT ''", "deleted_by": "TEXT DEFAULT ''"
        },
        "auditor_share_links": {
            "label": "TEXT DEFAULT ''", "watermark": "TEXT DEFAULT 'DENETÇİ KOPYASI'", "last_access_at": "TEXT DEFAULT ''", "access_count": "INTEGER NOT NULL DEFAULT 0"
        },
    }.items():
        try:
            for column, definition in columns.items():
                _ensure_column(conn, table, column, definition)
        except Exception:
            pass
    # v111 role split: legacy Admin is migrated into Süper Admin / Kurum Admin by tenant scope.
    try:
        conn.execute("UPDATE users SET role='Süper Admin' WHERE role='Admin' AND COALESCE(tenant_scope,'tenant')='global'")
        conn.execute("UPDATE users SET role='Kurum Admin' WHERE role='Admin' AND COALESCE(tenant_scope,'tenant')<>'global'")
        conn.execute("UPDATE program_users SET role='Kurum Admin' WHERE role='Admin'")
    except Exception:
        pass


def ensure_data_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    ORG_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "exports").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "backups").mkdir(parents=True, exist_ok=True)


def init_db() -> None:
    ensure_data_directories()
    with transaction() as conn:
        conn.executescript(SCHEMA_SQL)
        conn.executescript(INDEX_SQL)
        _apply_lightweight_migrations(conn)
        from .template_seed import seed_system_templates
        from .tenancy import ensure_default_tenant, DEFAULT_TENANT_ID, GLOBAL_SCOPE
        seed_system_templates(conn)
        ensure_default_tenant(conn)
        user_count = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        if int(user_count or 0) > 0:
            return
        password = (os.getenv("MEDEK_BOOTSTRAP_ADMIN_PASSWORD", "") or os.getenv("MEDEK_ADMIN_PASSWORD", "")).strip()
        placeholder_values = {"change-this-initial-admin-password", "admin", "admin123", "password"}
        production = os.getenv("MEDEK_ENV", "").lower() == "production"
        if not password or (production and password in placeholder_values):
            if production:
                raise RuntimeError(
                    "Fresh database detected but MEDEK_BOOTSTRAP_ADMIN_PASSWORD is missing or weak. "
                    "Set MEDEK_BOOTSTRAP_ADMIN_PASSWORD to a strong value in .env, then restart the stack. "
                    "Example: MEDEK_BOOTSTRAP_ADMIN_PASSWORD=MedekAdmin_2026!Guclu"
                )
            password = "admin123"
        from .security import hash_password, validate_password_strength
        if production:
            validate_password_strength(password)

        conn.execute(
            """INSERT INTO users(
                username, password_hash, role, tenant_id, tenant_scope, faculty_name, full_name, is_active, must_change_password,
                created_at, email, academic_status, failed_attempts, locked_until, last_login,
                password_changed_at, token_version, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "admin",
                hash_password(password),
                "Süper Admin",
                DEFAULT_TENANT_ID,
                GLOBAL_SCOPE,
                "",
                "Sistem Yöneticisi",
                1,
                1,
                now_iso(),
                "",
                "",
                0,
                "",
                "",
                now_iso(),
                1,
                now_iso(),
            ),
        )
