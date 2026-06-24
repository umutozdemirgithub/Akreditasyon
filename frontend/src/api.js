const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

function apiUrl(path) {
  return `${API_BASE}${path}`;
}

async function errorMessageFromResponse(response) {
  let message = response.statusText || `HTTP ${response.status}`;
  try {
    const body = await response.clone().json();
    message = body.detail || body.message || message;
  } catch {
    try {
      const text = await response.clone().text();
      if (text) message = text;
    } catch {
      // keep default message
    }
  }
  return `${response.status} ${message}`.trim();
}

export function getStoredToken() {
  return localStorage.getItem("medek_token") || "";
}

export function setStoredToken(token) {
  if (token) localStorage.setItem("medek_token", token);
  else localStorage.removeItem("medek_token");
}

async function request(path, options = {}) {
  const token = getStoredToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(apiUrl(path), {
    credentials: "include",
    ...options,
    headers,
  });

  if (!response.ok) {
    throw new Error(await errorMessageFromResponse(response));
  }

  return response.json();
}

async function requestBlob(path) {
  const token = getStoredToken();
  const response = await fetch(apiUrl(path), {
    credentials: "include",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    throw new Error(await errorMessageFromResponse(response));
  }
  return response.blob();
}

async function upload(path, formData) {
  const token = getStoredToken();
  const response = await fetch(apiUrl(path), {
    method: "POST",
    credentials: "include",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!response.ok) {
    throw new Error(await errorMessageFromResponse(response));
  }
  return response.json();
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  login: (username, password) =>
    request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  me: () => request("/me"),
  changePassword: (currentPassword, newPassword) =>
    request("/me/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),
  users: () => request("/users"),
  saveUser: (payload) =>
    request("/users", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteUser: (username) =>
    request(`/users/${encodeURIComponent(username)}`, { method: "DELETE" }),
  programs: () => request("/programs"),
  adminPrograms: (includeInactive = true) => request(`/admin/programs?include_inactive=${includeInactive ? "true" : "false"}`),
  createProgram: (payload) =>
    request("/admin/programs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  cloneProgram: (payload) =>
    request("/admin/programs/clone", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  setProgramActive: (programId, active) =>
    request(`/admin/programs/${programId}/active?active=${active ? "true" : "false"}`, {
      method: "PUT",
    }),
  deleteProgram: (programId) =>
    request(`/admin/programs/${encodeURIComponent(programId)}`, { method: "DELETE" }),

  deletedPrograms: () => request("/admin/programs/deleted"),
  restoreProgram: (programId) => request(`/admin/programs/${encodeURIComponent(programId)}/restore`, { method: "PUT" }),
  purgeProgram: (programId) => request(`/admin/programs/${encodeURIComponent(programId)}/purge`, { method: "DELETE" }),
  recoveryItems: () => request("/admin/recovery/items"),
  restoreRecoveryItem: (itemType, itemId) => request(`/admin/recovery/items/${encodeURIComponent(itemType)}/${encodeURIComponent(itemId)}/restore`, { method: "PUT" }),
  purgeRecoveryItem: (itemType, itemId) => request(`/admin/recovery/items/${encodeURIComponent(itemType)}/${encodeURIComponent(itemId)}/purge`, { method: "DELETE" }),
  currentAppearance: () => request("/appearance/current"),
  adminAppearance: () => request("/admin/appearance"),
  saveTenantAppearance: (tenantId, payload) =>
    request(`/admin/appearance/tenants/${encodeURIComponent(tenantId)}`, { method: "PUT", body: JSON.stringify(payload) }),

  updateCenter: () => request("/admin/update-center"),
  runUpdateCenterCheck: (payload = {}) => request("/admin/update-center/check", { method: "POST", body: JSON.stringify(payload) }),
  applyUpdateCandidate: (candidateId) => request(`/admin/update-center/candidates/${encodeURIComponent(candidateId)}/apply`, { method: "POST" }),
  ignoreUpdateCandidate: (candidateId, note = "") => request(`/admin/update-center/candidates/${encodeURIComponent(candidateId)}/ignore`, { method: "POST", body: JSON.stringify({ note }) }),
  permissions: () => request("/admin/permissions"),
  permissionMatrixDownload: (format = "csv", programId = "") =>
    requestBlob(`/admin/permissions/download?format=${encodeURIComponent(format)}${programId ? `&program_id=${encodeURIComponent(programId)}` : ""}`),
  savePermissions: (rows, sidebarRows = []) => request("/admin/permissions", { method: "PUT", body: JSON.stringify({ rows, sidebar_rows: sidebarRows }) }),
  sectionPermissions: (programId) => request(`/programs/${programId}/section-permissions`),
  saveSectionPermissions: (programId, rows = []) => request(`/programs/${programId}/section-permissions`, { method: "PUT", body: JSON.stringify({ rows }) }),
  adminAnalytics: (limit = 200) => request(`/admin/analytics?limit=${limit}`),
  deploymentWizard: () => request("/admin/deployment/wizard"),
  deploymentSmoke: () => request("/admin/deployment/smoke", { method: "POST" }),
  tenants: (includeInactive = true) => request(`/admin/tenants?include_inactive=${includeInactive ? "true" : "false"}`),
  saveTenant: (payload) => request("/admin/tenants", { method: "POST", body: JSON.stringify(payload) }),
  importTenantAcademicCatalog: (payload) => request("/admin/tenants/import-academic-catalog", { method: "POST", body: JSON.stringify(payload) }),
  deleteTenant: (tenantId, options = {}) => {
    const params = new URLSearchParams();
    if (options.mode) params.set("mode", options.mode);
    if (options.target_tenant_id) params.set("target_tenant_id", options.target_tenant_id);
    const suffix = params.toString() ? `?${params.toString()}` : "";
    return request(`/admin/tenants/${encodeURIComponent(tenantId)}${suffix}`, { method: "DELETE" });
  },
  tenantFaculties: (tenantId = "") => request(`/admin/tenant-faculties${tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : ""}`),
  saveTenantFaculty: (payload) => request("/admin/tenant-faculties", { method: "POST", body: JSON.stringify(payload) }),
  tenantDashboard: () => request("/admin/tenant-dashboard"),
  tenantSetup: () => request("/admin/tenant-setup"),
  programUsers: (programId = "") =>
    request(`/admin/program-users${programId ? `?program_id=${encodeURIComponent(programId)}` : ""}`),
  saveProgramUser: (payload) =>
    request("/admin/program-users", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  loginAttempts: (limit = 100) => request(`/admin/login-attempts?limit=${limit}`),
  notifications: (limit = 100) => request(`/admin/notifications?limit=${limit}`),
  mailStatus: () => request("/admin/mail/status"),
  mailSettings: () => request("/admin/mail/settings"),
  saveMailSettings: (payload) =>
    request("/admin/mail/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  testMail: (payload) =>
    request("/admin/mail/test", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  systemTemplates: () => request("/admin/system-templates"),
  seedSystemTemplates: () => request("/admin/system-templates/seed", { method: "POST" }),
  restoreMissingSections: (programId = "") =>
    request(`/admin/system-templates/restore-missing-sections${programId ? `?program_id=${encodeURIComponent(programId)}` : ""}`, { method: "POST" }),
  settings: (programId) => request(`/programs/${programId}/settings`),
  saveSettings: (programId, payload) =>
    request(`/programs/${programId}/settings`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  dashboard: (programId) => request(`/programs/${programId}/dashboard`),
  stats: (programId) => request(`/programs/${programId}/stats`),
  insights: (programId) => request(`/programs/${programId}/insights`),
  help: (programId) => request(`/programs/${programId}/help`),

  activityTimeline: (programId, limit = 200) => request(`/programs/${programId}/activity-timeline?limit=${limit}`),
  advancedReporting: (programId) => request(`/programs/${programId}/advanced-reporting`),
  advancedReportingDocx: (programId) => requestBlob(`/programs/${programId}/advanced-reporting/docx`),
  advancedReportingPdf: (programId) => requestBlob(`/programs/${programId}/advanced-reporting/pdf`),
  professionalReporting: (programId) => request(`/programs/${programId}/professional-reporting`),
  professionalConsistency: (programId) => request(`/programs/${programId}/professional-reporting/consistency`),
  professionalQuality: (programId) => request(`/programs/${programId}/professional-reporting/quality`),
  professionalMockAudit: (programId, sampleSize = 5) => request(`/programs/${programId}/professional-reporting/mock-audit?sample_size=${sampleSize}`),
  professionalClauses: (programId, sectionKey = "") => request(`/programs/${programId}/professional-reporting/clauses${sectionKey ? `?section_key=${encodeURIComponent(sectionKey)}` : ""}`),
  seedProfessionalClauses: (programId) => request(`/programs/${programId}/professional-reporting/clauses/seed`, { method: "POST" }),
  createProfessionalClause: (programId, payload) => request(`/programs/${programId}/professional-reporting/clauses`, { method: "POST", body: JSON.stringify(payload) }),
  insertProfessionalClause: (programId, sectionKey, clauseId, position = "append") => request(`/programs/${programId}/sections/${encodeURIComponent(sectionKey)}/professional-reporting/clauses/${encodeURIComponent(clauseId)}/insert`, { method: "POST", body: JSON.stringify({ position }) }),
  professionalSentenceDiff: (programId, sectionKey, baseId = "") => request(`/programs/${programId}/sections/${encodeURIComponent(sectionKey)}/professional-reporting/sentence-diff?base_id=${encodeURIComponent(baseId)}`),
  professionalPackage: (programId) => requestBlob(`/programs/${programId}/professional-reporting/package.zip`),
  professionalAuditorPackage: (programId) => requestBlob(`/programs/${programId}/professional-reporting/auditor-package.zip`),
  professionalAuditorLinks: (programId) => request(`/programs/${programId}/professional-reporting/auditor-links`),
  createProfessionalAuditorLink: (programId, payload) => request(`/programs/${programId}/professional-reporting/auditor-links`, { method: "POST", body: JSON.stringify(payload) }),
  sectionVersions: (programId, sectionKey, baseId = "", compareId = "current") => request(`/programs/${programId}/sections/${encodeURIComponent(sectionKey)}/versions?base_id=${encodeURIComponent(baseId)}&compare_id=${encodeURIComponent(compareId)}`),
  notificationInbox: (programId, limit = 100) => request(`/programs/${programId}/notifications/inbox?limit=${limit}`),
  notificationUnreadCount: (programId) => request(`/programs/${programId}/notifications/inbox?limit=50`).then((rows) => Array.isArray(rows) ? rows.filter((row) => !row.read).length : 0),
  markNotificationsRead: (programId, eventIds = []) =>
    request(`/programs/${programId}/notifications/read`, {
      method: "PUT",
      body: JSON.stringify({ event_ids: eventIds }),
    }),
  search: (programId, query) => request(`/programs/${programId}/search?q=${encodeURIComponent(query)}`),
  sections: (programId) => request(`/programs/${programId}/sections`),
  reportStudio: (programId) => request(`/programs/${programId}/report-studio`),
  sectionAiSuggestions: (programId, sectionKey, mode = "coach") =>
    request(`/programs/${programId}/sections/${encodeURIComponent(sectionKey)}/ai/suggestions`, {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),
  sectionQualityRecalculate: (programId, sectionKey) =>
    request(`/programs/${programId}/sections/${encodeURIComponent(sectionKey)}/quality/recalculate`, { method: "POST" }),
  sectionAccreditationGapScan: (programId, sectionKey) =>
    request(`/programs/${programId}/sections/${encodeURIComponent(sectionKey)}/accreditation/gap-scan`, { method: "POST" }),
  sectionEvidenceMatch: (programId, sectionKey) =>
    request(`/programs/${programId}/sections/${encodeURIComponent(sectionKey)}/accreditation/evidence-match`, { method: "POST" }),
  sectionCollaborationPing: (programId, sectionKey) =>
    request(`/programs/${programId}/sections/${encodeURIComponent(sectionKey)}/collaboration/ping`, { method: "POST" }),
  sectionCollaboration: (programId, sectionKey) =>
    request(`/programs/${programId}/sections/${encodeURIComponent(sectionKey)}/collaboration`),
  sectionTemplateBank: (programId, sectionKey) =>
    request(`/programs/${programId}/sections/${encodeURIComponent(sectionKey)}/templates/bank`),
  createSectionTemplate: (programId, payload) =>
    request(`/programs/${programId}/templates/bank`, { method: "POST", body: JSON.stringify(payload) }),
  sectionDocx: (programId, sectionKey) => requestBlob(`/programs/${programId}/sections/${encodeURIComponent(sectionKey)}/export/docx`),
  sectionPdf: (programId, sectionKey) => requestBlob(`/programs/${programId}/sections/${encodeURIComponent(sectionKey)}/export/pdf`),
  bulkStudio: (programId, payload) =>
    request(`/programs/${programId}/bulk/studio`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  section: (programId, sectionKey) => request(`/programs/${programId}/sections/${encodeURIComponent(sectionKey)}`),
  saveSection: (programId, sectionKey, payload, options = {}) =>
    request(`/programs/${programId}/sections/${encodeURIComponent(sectionKey)}`, {
      method: "PUT",
      body: JSON.stringify({ ...payload, is_autosave: Boolean(options.autosave) }),
    }),
  evidenceStudio: (programId) => request(`/programs/${programId}/evidence/studio`),
  evidence: (programId, sectionKey) =>
    request(`/programs/${programId}/evidence${sectionKey ? `?section_key=${encodeURIComponent(sectionKey)}` : ""}`),
  uploadEvidence: (programId, { file, sectionKeys, code, note }) => {
    const form = new FormData();
    form.append("file", file);
    form.append("section_keys", JSON.stringify(sectionKeys));
    form.append("code", code);
    form.append("note", note || "");
    return upload(`/programs/${programId}/evidence`, form);
  },
  linkEvidence: (programId, payload) =>
    request(`/programs/${programId}/evidence/link`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteEvidence: (programId, evidenceId) =>
    request(`/programs/${programId}/evidence/${evidenceId}`, { method: "DELETE" }),
  evidenceDownloadUrl: (programId, evidenceId) => `${API_BASE}/programs/${programId}/evidence/${evidenceId}/download`,
  evidenceBlob: (programId, evidenceId) => requestBlob(`/programs/${programId}/evidence/${evidenceId}/download`),
  tablesStudio: (programId) => request(`/programs/${programId}/tables/studio`),
  tables: (programId, sectionKey) =>
    request(`/programs/${programId}/tables${sectionKey ? `?section_key=${encodeURIComponent(sectionKey)}` : ""}`),
  saveTable: (programId, payload) =>
    request(`/programs/${programId}/tables`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  attachTable: (programId, payload) =>
    request(`/programs/${programId}/tables/attach`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteTable: (programId, tableId) =>
    request(`/programs/${programId}/tables/${tableId}`, { method: "DELETE" }),
  control: (programId) => request(`/programs/${programId}/control`),
  controlDocx: (programId) => requestBlob(`/programs/${programId}/control/docx`),
  auditDocx: (programId) => requestBlob(`/programs/${programId}/audit/docx`),
  compliance: (programId, limit = 500) => request(`/programs/${programId}/compliance?limit=${limit}`),
  complianceDocx: (programId) => requestBlob(`/programs/${programId}/compliance/docx`),
  workflowReminders: (programId) => request(`/programs/${programId}/workflow/reminders`),
  workflowAutomationSettings: (programId) => request(`/programs/${programId}/workflow/automation/settings`),
  saveWorkflowAutomationSettings: (programId, payload) => request(`/programs/${programId}/workflow/automation/settings`, { method: "PUT", body: JSON.stringify(payload) }),
  workflowAutomationPreview: (programId) => request(`/programs/${programId}/workflow/automation/preview`),
  workflowAutomationRuns: (programId, limit = 30) => request(`/programs/${programId}/workflow/automation/runs?limit=${limit}`),
  runWorkflowAutomation: (programId, payload = {}) => request(`/programs/${programId}/workflow/automation/run`, { method: "POST", body: JSON.stringify(payload) }),
  deadlines: (programId) => request(`/programs/${programId}/deadlines`),
  saveDeadlines: (programId, rows) =>
    request(`/programs/${programId}/deadlines`, {
      method: "PUT",
      body: JSON.stringify({ rows }),
    }),
  bulkStatus: (programId, sectionKeys, status) =>
    request(`/programs/${programId}/bulk/status`, {
      method: "PUT",
      body: JSON.stringify({ section_keys: sectionKeys, status }),
    }),
  bulkAdvanced: (programId, payload) =>
    request(`/programs/${programId}/bulk/advanced`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  preview: (programId) => request(`/programs/${programId}/preview`),
  reportPreflight: (programId) => request(`/programs/${programId}/report/preflight`),
  reportDocx: (programId, force = false) => requestBlob(`/programs/${programId}/report/docx${force ? "?force=true" : ""}`),
  reportPdf: (programId, force = false) => requestBlob(`/programs/${programId}/report/pdf${force ? "?force=true" : ""}`),
  createExportJob: (programId, exportType = "docx", force = false) =>
    request(`/programs/${programId}/report/jobs?export_type=${encodeURIComponent(exportType)}${force ? "&force=true" : ""}`, { method: "POST" }),
  exportJobs: (programId, limit = 50) => request(`/programs/${programId}/report/jobs?limit=${limit}`),
  exportJob: (programId, jobId) => request(`/programs/${programId}/report/jobs/${encodeURIComponent(jobId)}`),
  exportJobBlob: (programId, jobId) => requestBlob(`/programs/${programId}/report/jobs/${encodeURIComponent(jobId)}/download`),
  exports: (programId) => request(`/programs/${programId}/exports`),
  activity: (programId, limit = 100) => request(`/programs/${programId}/activity?limit=${limit}`),
  system: (programId) => request(`/programs/${programId}/system`),
  backupJson: (programId) => requestBlob(`/programs/${programId}/backup/json`),
  personalProgramBackupZip: (programId) => requestBlob(`/programs/${programId}/backup/personal.zip`),
  personalAllBackupZip: () => requestBlob(`/me/backup/personal.zip`),
  restoreBackup: (programId, { file, overwrite }) => {
    const form = new FormData();
    form.append("file", file);
    form.append("overwrite", overwrite ? "true" : "false");
    return upload(`/programs/${programId}/backup/restore`, form);
  },
  importReport: (programId, { file, overwriteEmptyOnly }) => {
    const form = new FormData();
    form.append("file", file);
    form.append("overwrite_empty_only", overwriteEmptyOnly ? "true" : "false");
    return upload(`/programs/${programId}/report/import`, form);
  },
  importDocx: (programId, { file, overwriteEmptyOnly }) => {
    const form = new FormData();
    form.append("file", file);
    form.append("overwrite_empty_only", overwriteEmptyOnly ? "true" : "false");
    return upload(`/programs/${programId}/docx/import`, form);
  },
  globalAiStatus: () => request("/ai/status"),
  aiSettings: () => request("/admin/ai/settings"),
  saveAiSettings: (payload) => request("/admin/ai/settings", { method: "PUT", body: JSON.stringify(payload) }),
  aiModels: () => request("/admin/ai/models"),
  pullAiModel: (model) => request("/admin/ai/models/pull", { method: "POST", body: JSON.stringify({ model }) }),
  aiStatus: (programId) => request(`/programs/${programId}/ai/status`),
  openEventStreamSession: (programId) => request(`/programs/${programId}/events/session`, { method: "POST" }),
  eventStreamUrl: (programId) => apiUrl(`/programs/${programId}/events/stream`),
  aiSectionDraft: (programId, sectionKey, targetWords = 650) =>
    request(`/programs/${programId}/ai/sections/${encodeURIComponent(sectionKey)}/draft?target_words=${targetWords}`, { method: "POST" }),
  aiFullReport: (programId, includeAll = false, targetWords = 650) =>
    request(`/programs/${programId}/ai/full-report?include_all=${includeAll ? "true" : "false"}&target_words=${targetWords}`, { method: "POST" }),
  applyAiDraft: (programId, sectionKey, text) =>
    request(`/programs/${programId}/ai/sections/${encodeURIComponent(sectionKey)}/apply`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  approvalHistory: (programId, sectionKey = "") =>
    request(`/programs/${programId}/approval/history${sectionKey ? `?section_key=${encodeURIComponent(sectionKey)}` : ""}`),
  approval: (programId, payload) =>
    request(`/programs/${programId}/approval`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
