-- Auto-generated from backend.db SCHEMA_SQL + INDEX_SQL. Keep this file in sync with runtime init_db().


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
    role TEXT NOT NULL DEFAULT 'İzleyici',
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
    role TEXT NOT NULL DEFAULT 'Editör',
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

