import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Archive,
  BarChart3,
  Bell,
  Bot,
  Building2,
  CalendarDays,
  Camera,
  CheckCircle2,
  ClipboardCheck,
  ClipboardList,
  Copy,
  Database,
  Download,
  Eye,
  FileDown,
  FileText,
  History,
  LayoutDashboard,
  Lock,
  LogOut,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Command,
  Star,
  X,
  RefreshCw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  Table2,
  Trash2,
  Upload,
  UserCheck,
  Users,
  Wrench,
} from "lucide-react";
import { api, getStoredToken, setStoredToken } from "./api";
import { ChangePasswordScreen, LoginScreen } from "./views/AuthScreens";
import { moduleCatalog, modulesForRole } from "./config/navigation.jsx";
import { ErrorBoundary } from "./components/ErrorBoundary.jsx";
import { useAdaptiveViewport } from "./hooks/useAdaptiveViewport.js";
import { useSidebarCollapse } from "./hooks/useSidebarCollapse.js";
import { TenantThemeProvider, useTenantTheme } from "./theme/ThemeContext.jsx";
import { asArray, asObject } from "./utils.js";
import { clearMedekCaches } from "./registerServiceWorker.js";
import {
  STATUS_OPTIONS,
  FACULTY_ADMIN_ROLE,
  READONLY_ROLE,
  ROLES,
  ADMIN_ROLES,
  MANAGEMENT_MODULES,
  SUPER_ADMIN_ROLES,
  TENANT_DELEGATE_ROLES,
  normalizeRole,
  isAdminRole,
  isSuperAdminRole,
  matrixPermissionAllowed,
  matrixModuleAllowed,
  ACCREDITATION_PROFILES,
  PROFILE_LABELS,
  ERU_UNIT_PROGRAM_CATALOG,
  FACULTY_PROFILE_OPTIONS,
  FACULTY_TO_PROFILE,
  FACULTY_CATALOG_BY_LABEL,
  ACADEMIC_STATUS_OPTIONS,
  emptySection,
  DEFAULT_TABLE_COLUMNS,
  DEFAULT_TABLE_META,
  profileLabel,
  profileForFaculty,
  unitCatalogForFaculty,
  departmentOptionsForFaculty,
  programOptionsForDepartment,
  updateProgramFaculty,
  updateProgramDepartment,
  programSchoolLabel,
  programDisplayLabel,
  groupedPrograms,
  tenantIdOf,
  tenantNameOf,
  groupedByTenant,
  uniqueSorted,
  departmentOptionsForPrograms,
  programOnlyDisplayLabel,
  shortProgramLabel,
  daysUntil,
  computeModuleBadges,
  NAV_GROUPS,
  groupedNavItems,
  MOBILE_PRIMARY_BY_ROLE,
  mobileNavItemsForRole,
  roleAccentForRole,
  roleClassName
} from "./constants/appConstants.js";
import {
  MobileBottomNav,
  NavSection,
  DashboardView,
  MetricCard,
  DashboardSkeleton,
  PremiumEmptyState,
  DashboardSectionList,
  RoleActionPanel,
  PriorityPanel,
  MiniChartsPanel,
  MiniBarChart,
  TabbedExpander,
  ProgressBar,
  NotificationCenterView,
  TasksAndGapsView,
  DeadlineCalendarView,
  ActivityTimelineView,
  AnalyticsBarList,
  RiskHeatMap,
  AdvancedDashboardView,
  ProfessionalReportingView,
  VersionDiffView,
  PermissionMatrixView,
  RecoveryView,
  AnalyticsView,
  UpdateCenterView,
  AppearanceView,
  HelpView,
  EntryView,
  SectionList,
  SectionEditor,
  ShortcutPanel,
  RichTableEditor,
  RichTablePreview,
  EvidenceInlinePanel,
  TableInlinePanel,
  EvidenceView,
  TablesView,
  ControlView,
  ReadinessView,
  SearchView,
  StatsView,
  AssistantView,
  ApprovalView,
  PreviewView,
  DocxImportView,
  FullReportView,
  ExportView,
  ExportHistoryView,
  ProgramsView,
  UsersView,
  DeadlineView,
  BulkView,
  SettingsView
} from "./views/AppViews.jsx";
import "./styles.css";

export default function App() {
  const [tokenReady, setTokenReady] = useState(Boolean(getStoredToken()));
  const [user, setUser] = useState(null);
  const [programs, setPrograms] = useState([]);
  const [workspaceTenants, setWorkspaceTenants] = useState([]);
  const [workspaceTenantId, setWorkspaceTenantId] = useState("");
  const [activeProgram, setActiveProgram] = useState("");
  const [dashboard, setDashboard] = useState(null);
  const [sections, setSections] = useState([]);
  const [activeSectionKey, setActiveSectionKey] = useState("");
  const [activeSection, setActiveSection] = useState(null);
  const [form, setForm] = useState(emptySection);
  const [activeModule, setActiveModule] = useState("dashboard");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem("medek_theme") === "dark");
  const [tenantAppearance, setTenantAppearance] = useState(null);
  const [notificationUnreadCount, setNotificationUnreadCount] = useState(0);
  const [liveConnected, setLiveConnected] = useState(false);
  const adaptiveViewport = useAdaptiveViewport();
  const sidebarCollapse = useSidebarCollapse(adaptiveViewport);
  const [manualSidebarCollapsed, setManualSidebarCollapsed] = useState(() => localStorage.getItem("akys_sidebar_collapsed") === "1");
  const [favoriteModules, setFavoriteModules] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem("akys_favorite_modules") || "[]");
      return Array.isArray(saved) ? saved : [];
    } catch {
      return [];
    }
  });
  const [quickSearchOpen, setQuickSearchOpen] = useState(false);
  const [quickSearchQuery, setQuickSearchQuery] = useState("");
  const [isOnline, setIsOnline] = useState(() => navigator.onLine);
  const [installPrompt, setInstallPrompt] = useState(null);
  const [swUpdateReady, setSwUpdateReady] = useState(false);

  useEffect(() => {
    localStorage.setItem("medek_theme", darkMode ? "dark" : "light");
  }, [darkMode]);

  useEffect(() => {
    localStorage.setItem("akys_sidebar_collapsed", manualSidebarCollapsed ? "1" : "0");
  }, [manualSidebarCollapsed]);

  useEffect(() => {
    localStorage.setItem("akys_favorite_modules", JSON.stringify(favoriteModules));
  }, [favoriteModules]);

  useEffect(() => {
    const onKeyDown = (event) => {
      const target = event.target;
      const typing = target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setQuickSearchOpen(true);
        return;
      }
      if (event.key === "Escape") setQuickSearchOpen(false);
      if (typing) return;
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    const online = () => setIsOnline(true);
    const offline = () => setIsOnline(false);
    const beforeInstall = (event) => { event.preventDefault(); setInstallPrompt(event); };
    const swUpdate = () => setSwUpdateReady(true);
    window.addEventListener("online", online);
    window.addEventListener("offline", offline);
    window.addEventListener("beforeinstallprompt", beforeInstall);
    window.addEventListener("medek-sw-update", swUpdate);
    return () => {
      window.removeEventListener("online", online);
      window.removeEventListener("offline", offline);
      window.removeEventListener("beforeinstallprompt", beforeInstall);
      window.removeEventListener("medek-sw-update", swUpdate);
    };
  }, []);

  async function installPwa() {
    if (!installPrompt) return;
    installPrompt.prompt();
    await installPrompt.userChoice.catch(() => null);
    setInstallPrompt(null);
  }


  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const moduleParam = params.get("module");
    if (moduleParam && moduleCatalog[moduleParam]) setActiveModule(moduleParam);
  }, []);

  const activeProgramObj = useMemo(
    () => programs.find((program) => program.id === activeProgram),
    [programs, activeProgram]
  );
  const activeProgramRole = normalizeRole(activeProgramObj?.user_role || user?.role || READONLY_ROLE, user?.tenant_scope);
  const dashboardPermissions = useMemo(() => {
    const byRole = asObject(user?.dashboard_permissions_by_role);
    return asObject(byRole[activeProgramRole] || user?.dashboard_permissions);
  }, [user, activeProgramRole]);

  const sidebarMatrix = useMemo(() => asArray(user?.sidebar_matrix), [user]);
  const visibleModules = useMemo(() => modulesForRole(activeProgramRole, sidebarMatrix), [activeProgramRole, sidebarMatrix]);
  const sessionAdminCanKeepMatrixOpen = activeModule === "permissions" && isAdminRole(activeProgramRole);
  const activeModuleCanRender = visibleModules.includes(activeModule) || sessionAdminCanKeepMatrixOpen;
  const renderModule = activeModuleCanRender ? activeModule : "";
  const firstVisibleModule = visibleModules[0] || "";
  const readOnly = useMemo(() => {
    if (!user || !activeSection) return true;
    const perms = asObject(activeSection.user_permissions);
    const canEditAnyField = Boolean(perms.edit_text || perms.edit_puko || perms.edit_status || perms.edit_deadline);
    if (!canEditAnyField) return true;
    if (activeSection.approval_status === "Onaya Gönderildi" && !isAdminRole(activeProgramRole)) return true;
    if (activeSection.approval_status === "Onaylandı" && !isAdminRole(activeProgramRole)) return true;
    return false;
  }, [user, activeSection, activeProgramRole]);

  const effectiveReadOnly = readOnly || !isOnline;
  const mobileNavItems = useMemo(() => mobileNavItemsForRole(activeProgramRole, visibleModules), [activeProgramRole, visibleModules]);
  const autosaveTimerRef = useRef(null);
  const autosaveRequestRef = useRef(0);
  const [autosaveState, setAutosaveState] = useState({ status: "idle", savedAt: "", error: "" });

  function sectionDraftKey(programId = activeProgram, sectionKey = activeSectionKey) {
    if (!programId || !sectionKey || !user?.username) return "";
    return `medek:auto-draft:${user.username}:${programId}:${sectionKey}`;
  }

  function normalizeSectionDraftPayload(payload = {}) {
    return {
      status: payload.status || "Başlamadı",
      report_text: payload.report_text || "",
      planla: payload.planla || "",
      uygula: payload.uygula || "",
      kontrol: payload.kontrol || "",
      onlem: payload.onlem || "",
      notes: payload.notes || "",
      deadline: payload.deadline || "",
    };
  }

  function sectionPayloadSignature(payload = {}) {
    return JSON.stringify(normalizeSectionDraftPayload(payload));
  }

  const savedSectionForm = useMemo(() => ({
    status: activeSection?.status || "Başlamadı",
    report_text: activeSection?.report_text || "",
    planla: activeSection?.planla || "",
    uygula: activeSection?.uygula || "",
    kontrol: activeSection?.kontrol || "",
    onlem: activeSection?.onlem || "",
    notes: activeSection?.notes || "",
    deadline: activeSection?.deadline || "",
  }), [activeSection]);
  const hasUnsavedSectionChanges = useMemo(() => {
    if (!activeSection || activeProgramRole !== "Editör / Hazırlayıcı") return false;
    return ["status", "report_text", "planla", "uygula", "kontrol", "onlem", "notes", "deadline"].some((key) => String(form?.[key] || "") !== String(savedSectionForm?.[key] || ""));
  }, [activeSection, activeProgramRole, form, savedSectionForm]);

  useEffect(() => {
    if (!tokenReady) return;
    api.me()
      .then((payload) => {
        const safe = asObject(payload);
        setUser(safe);
        setTenantAppearance(asObject(safe.appearance));
      })
      .catch(() => {
        setStoredToken("");
        setTokenReady(false);
      });
  }, [tokenReady]);

  useEffect(() => {
    if (!tokenReady || !user) return;
    api.currentAppearance()
      .then((payload) => setTenantAppearance(asObject(payload)))
      .catch(() => {});
  }, [tokenReady, user?.tenant_id]);

  useEffect(() => {
    if (!tokenReady || !activeProgram) {
      setNotificationUnreadCount(0);
      return;
    }
    let cancelled = false;
    const poll = async () => {
      try {
        const count = await api.notificationUnreadCount(activeProgram);
        if (!cancelled) setNotificationUnreadCount(Number(count || 0));
      } catch {
        if (!cancelled) setNotificationUnreadCount(0);
      }
    };
    poll();
    const timer = window.setInterval(poll, 30000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [tokenReady, activeProgram]);

  useEffect(() => {
    if (!tokenReady || !activeProgram || typeof window.EventSource === "undefined") {
      setLiveConnected(false);
      return;
    }
    let source = null;
    let cancelled = false;
    api.openEventStreamSession(activeProgram)
      .then(() => {
        if (cancelled) return;
        source = new EventSource(api.eventStreamUrl(activeProgram), { withCredentials: true });
        source.onopen = () => setLiveConnected(true);
        source.addEventListener("medek", (event) => {
          try {
            const payload = JSON.parse(event.data || "{}");
            setNotificationUnreadCount(Number(payload.unread_count || 0));
            window.dispatchEvent(new CustomEvent("medek-live-event", { detail: payload }));
          } catch {
            // Ignore malformed live payloads; fallback polling remains active.
          }
        });
        source.addEventListener("medek-error", () => setLiveConnected(false));
        source.onerror = () => setLiveConnected(false);
      })
      .catch(() => setLiveConnected(false));
    return () => {
      cancelled = true;
      if (source) source.close();
      setLiveConnected(false);
    };
  }, [tokenReady, activeProgram]);

  async function reloadWorkspaceOptions({ preserveProgram = true } = {}) {
    const [programRowsRaw, tenantRowsRaw] = await Promise.all([
      api.programs(),
      api.tenants(false).catch(() => []),
    ]);
    const safeRows = asArray(programRowsRaw);
    const safeTenants = asArray(tenantRowsRaw).filter((tenant) => !tenant.is_setup_placeholder);
    setPrograms(safeRows);
    setWorkspaceTenants(safeTenants);
    setWorkspaceTenantId((current) => current || (safeRows[0] ? tenantIdOf(safeRows[0]) : safeTenants[0]?.id || ""));
    setActiveProgram((current) => {
      if (preserveProgram && current && safeRows.some((program) => program.id === current)) return current;
      return safeRows[0]?.id || "";
    });
  }

  useEffect(() => {
    if (!user || user.must_change_password) return;
    reloadWorkspaceOptions().catch((err) => setError(err.message));
  }, [user]);

  useEffect(() => {
    // Yetki Matrisi içinde çalışırken anlık sidebar görünürlük değişiklikleri ana
    // çalışma alanını boş bırakmamalı. Backend erişimi zaten ayrıca kontrol ediyor;
    // burada sadece görünür modül listesi ile aktif ekran arasındaki geçici farkı
    // güvenli şekilde yönetiyoruz.
    if (activeModule === "permissions" && isAdminRole(activeProgramRole)) return;
    if (!visibleModules.includes(activeModule)) setActiveModule(firstVisibleModule);
  }, [visibleModules, activeModule, activeProgramRole, firstVisibleModule]);

  async function refreshProgram(programId = activeProgram) {
    if (!programId) return;
    const [dash, sectionRows] = await Promise.all([api.dashboard(programId), api.sections(programId)]);
    const safeSections = asArray(sectionRows);
    setDashboard(asObject(dash));
    setSections(safeSections);
    setActiveSectionKey((current) => current || safeSections[0]?.section_key || "");
  }

  useEffect(() => {
    if (!user || user.must_change_password) return;
    refreshProgram(activeProgram).catch((err) => setError(err.message));
  }, [activeProgram, user?.must_change_password]);

  useEffect(() => {
    if (!activeProgram || !activeSectionKey) return;
    api.section(activeProgram, activeSectionKey)
      .then((section) => {
        const safeSection = asObject(section);
        const serverForm = normalizeSectionDraftPayload(safeSection);
        let nextForm = serverForm;
        const key = sectionDraftKey(activeProgram, activeSectionKey);
        if (key) {
          try {
            const draft = JSON.parse(window.localStorage.getItem(key) || "null");
            const draftPayload = normalizeSectionDraftPayload(draft?.payload || {});
            const draftTime = Date.parse(draft?.saved_at || "");
            const serverTime = Date.parse(safeSection.updated_at || "");
            if (draft?.pending && sectionPayloadSignature(draftPayload) !== sectionPayloadSignature(serverForm) && (!serverTime || draftTime > serverTime)) {
              nextForm = draftPayload;
              setAutosaveState({ status: "pending", savedAt: draft.saved_at || "", error: "Yerel taslak geri yüklendi; bağlantı uygunsa otomatik kaydedilecek." });
            } else if (sectionPayloadSignature(draftPayload) === sectionPayloadSignature(serverForm)) {
              window.localStorage.removeItem(key);
            }
          } catch {
            window.localStorage.removeItem(key);
          }
        }
        setActiveSection(safeSection);
        setForm(nextForm);
      })
      .catch((err) => setError(err.message));
  }, [activeProgram, activeSectionKey, user?.username]);

  function resetMessages() {
    setMessage("");
    setError("");
  }

  function showMessage(text) {
    setError("");
    setMessage(text);
  }

  async function handleLogin(username, password) {
    resetMessages();
    setBusy(true);
    try {
      const response = await api.login(username, password);
      setStoredToken(response.access_token);
      setUser(asObject(response.user));
      setTokenReady(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleChangePassword(currentPassword, newPassword) {
    resetMessages();
    setBusy(true);
    try {
      const response = await api.changePassword(currentPassword, newPassword);
      setStoredToken(response.access_token);
      setUser(asObject(response.user));
      setPrograms([]);
      setWorkspaceTenants([]);
      setWorkspaceTenantId("");
      setActiveProgram("");
      setMessage("Şifreniz güncellendi. Çalışma alanı yükleniyor.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveSection(options = {}) {
    if (!activeProgram || !activeSectionKey) return;
    const silent = Boolean(options.silent);
    const source = options.source || (silent ? "autosave" : "manual");
    const payload = normalizeSectionDraftPayload(options.payloadOverride || form);
    const draftKey = sectionDraftKey(activeProgram, activeSectionKey);
    const requestId = ++autosaveRequestRef.current;

    if (!silent) {
      resetMessages();
      setBusy(true);
    } else {
      setAutosaveState({ status: "saving", savedAt: "", error: "" });
    }

    try {
      const saved = asObject(await api.saveSection(activeProgram, activeSectionKey, payload, { autosave: silent || source === "autosave" }));
      if (requestId >= autosaveRequestRef.current) {
        setActiveSection(saved);
        setSections((current) => asArray(current).map((section) => section.section_key === activeSectionKey ? { ...section, ...saved } : section));
        setAutosaveState({ status: "saved", savedAt: new Date().toISOString(), error: "" });
      }
      if (draftKey) window.localStorage.removeItem(draftKey);
      if (!silent) {
        setMessage("Başlık kaydedildi.");
        await refreshProgram(activeProgram);
      }
      return saved;
    } catch (err) {
      if (silent) {
        setAutosaveState({ status: "error", savedAt: "", error: err.message || "Otomatik kayıt yapılamadı." });
      } else {
        setError(err.message);
      }
      throw err;
    } finally {
      if (!silent) setBusy(false);
    }
  }

  useEffect(() => {
    if (autosaveTimerRef.current) {
      window.clearTimeout(autosaveTimerRef.current);
      autosaveTimerRef.current = null;
    }
    if (!activeProgram || !activeSectionKey || effectiveReadOnly || !hasUnsavedSectionChanges) return undefined;

    const payload = normalizeSectionDraftPayload(form);
    const key = sectionDraftKey(activeProgram, activeSectionKey);
    const savedAt = new Date().toISOString();
    if (key) {
      try {
        window.localStorage.setItem(key, JSON.stringify({ pending: true, saved_at: savedAt, payload }));
      } catch {
        // Local draft backup can fail when storage is full; server autosave still runs.
      }
    }

    setAutosaveState((current) => ({ ...current, status: "pending", error: "" }));
    autosaveTimerRef.current = window.setTimeout(() => {
      if (!navigator.onLine) {
        setAutosaveState({ status: "offline", savedAt: "", error: "Çevrimdışı; yerel taslak saklandı." });
        return;
      }
      saveSection({ silent: true, source: "autosave", payloadOverride: payload }).catch(() => null);
    }, 25000);

    return () => {
      if (autosaveTimerRef.current) {
        window.clearTimeout(autosaveTimerRef.current);
        autosaveTimerRef.current = null;
      }
    };
  }, [activeProgram, activeSectionKey, effectiveReadOnly, hasUnsavedSectionChanges, form, user?.username]);

  useEffect(() => {
    const warnBeforeUnload = (event) => {
      if (!hasUnsavedSectionChanges) return undefined;
      event.preventDefault();
      event.returnValue = "Kaydedilmemiş değişiklikler var. Otomatik taslak kaydı bekleniyor olabilir.";
      return event.returnValue;
    };
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [hasUnsavedSectionChanges]);

  function openSection(sectionKey, module = "entry") {
    if (sectionKey) setActiveSectionKey(sectionKey);
    setActiveModule(module);
  }

  async function refreshCurrentUser() {
    const safe = asObject(await api.me());
    setUser(safe);
    setTenantAppearance(asObject(safe.appearance));
    return safe;
  }

  async function reloadAll() {
    resetMessages();
    try {
      await Promise.all([refreshProgram(activeProgram), refreshCurrentUser().catch(() => null)]);
      setError("");
      setMessage("Çalışma alanı yenilendi.");
    } catch (err) {
      setError(err.message);
    }
  }

  function logout() {
    setStoredToken("");
    clearMedekCaches().catch(() => {});
    setTokenReady(false);
    setUser(null);
    setPrograms([]);
    setActiveProgram("");
  }

  function toggleFavoriteModule(moduleId) {
    setFavoriteModules((current) => {
      const clean = current.filter((item) => visibleModules.includes(item));
      return clean.includes(moduleId) ? clean.filter((item) => item !== moduleId) : [...clean, moduleId];
    });
  }

  const appearancePackage = asObject(tenantAppearance?.package);
  const roleAccent = roleAccentForRole(activeProgramRole);
  const themeValue = useTenantTheme(appearancePackage, roleAccent, adaptiveViewport.cssVars);
  const appearanceId = String(themeValue.packageId || "corporate_blue").replace(/[^a-zA-Z0-9_-]/g, "_");
  const appearanceMode = themeValue.mode || "light";
  const appearanceVars = themeValue.vars;

  if (!user) return <LoginScreen onLogin={handleLogin} busy={busy} error={error} />;
  if (user.must_change_password) {
    return <ChangePasswordScreen user={user} onSubmit={handleChangePassword} onLogout={logout} busy={busy} error={error} message={message} />;
  }

  const tenantGroups = groupedByTenant(programs, workspaceTenants).filter((group) => group.is_active !== false);
  const activeTenantId = activeProgramObj ? tenantIdOf(activeProgramObj) : (workspaceTenantId || tenantGroups[0]?.id || "");
  const activeTenantGroup = tenantGroups.find((group) => group.id === activeTenantId) || tenantGroups[0] || { rows: [], id: "", name: "Kurum seçilmedi" };
  const tenantPrograms = activeTenantGroup.rows || [];
  const programGroups = groupedPrograms(tenantPrograms);
  const schoolOptions = Object.keys(programGroups);
  const activeSchool = activeProgramObj && tenantIdOf(activeProgramObj) === activeTenantGroup.id
    ? programSchoolLabel(activeProgramObj)
    : (schoolOptions[0] || "");
  const schoolPrograms = programGroups[activeSchool] || [];
  const departmentOptions = departmentOptionsForPrograms(schoolPrograms);
  const activeDepartment = activeProgramObj && tenantIdOf(activeProgramObj) === activeTenantGroup.id
    ? (activeProgramObj.department_name || departmentOptions[0] || "")
    : (departmentOptions[0] || "");
  const departmentPrograms = schoolPrograms.filter((program) => (program.department_name || "Bölüm belirtilmedi") === activeDepartment);
  function selectActiveTenant(tenantId) {
    setWorkspaceTenantId(tenantId);
    const firstProgram = tenantGroups.find((group) => group.id === tenantId)?.rows?.[0];
    if (firstProgram) {
      setActiveProgram(firstProgram.id);
      return;
    }
    setActiveProgram("");
    setDashboard(null);
    setSections([]);
    setActiveSectionKey("");
    setActiveSection(null);
  }
  function selectActiveSchool(school) {
    const firstProgram = programGroups[school]?.[0];
    if (firstProgram) setActiveProgram(firstProgram.id);
  }
  function selectActiveDepartment(department) {
    const firstProgram = (programGroups[activeSchool] || []).find((program) => (program.department_name || "Bölüm belirtilmedi") === department);
    if (firstProgram) setActiveProgram(firstProgram.id);
  }
  const title = moduleCatalog[activeModule]?.[0] || "Akreditasyon Çalışma Alanı";
  const moduleHint = moduleCatalog[activeModule]?.[2] || "Program çalışma alanı";
  const programUser = { ...user, role: activeProgramRole, system_role: user.role };
  const effectiveDarkMode = appearanceMode === "dark" || (appearanceMode !== "light" && darkMode);
  const isSuperAdmin = isSuperAdminRole(normalizeRole(user.role, user.tenant_scope));
  const favoriteSet = new Set(favoriteModules.filter((id) => visibleModules.includes(id)));
  const favoriteVisibleModules = favoriteModules.filter((id) => visibleModules.includes(id));
  const navigationGroups = groupedNavItems(visibleModules.filter((id) => !favoriteSet.has(id)));
  const sidebarProgress = Math.max(0, Math.min(100, Number(dashboard?.summary?.readiness_percent ?? 0)));

  return (
    <TenantThemeProvider value={themeValue}>
    <div className={`app-shell pwa-mobile-pro appearance-${appearanceId} appearance-density-${themeValue.density || "comfort"} role-${roleClassName(activeProgramRole)} ${effectiveDarkMode ? "theme-dark" : ""} ${manualSidebarCollapsed ? "sidebar-user-collapsed" : ""} ${!isOnline ? "is-offline" : ""} ${adaptiveViewport.className} ${sidebarCollapse.className}`} style={appearanceVars} data-screen={adaptiveViewport.screen} data-density={adaptiveViewport.density} data-layout={adaptiveViewport.layout} data-appearance={appearanceId}>
      <QuickSearchOverlay
        open={quickSearchOpen}
        query={quickSearchQuery}
        setQuery={setQuickSearchQuery}
        modules={visibleModules}
        activeModule={activeModule}
        onClose={() => setQuickSearchOpen(false)}
        onSelect={(moduleId) => { setActiveModule(moduleId); setQuickSearchOpen(false); setQuickSearchQuery(""); }}
      />
      <aside className="sidebar">
        <div className="brand-card premium-brand-card">
          <div className="brand-icon"><ShieldCheck size={22} /></div>
          <div className="brand-copy">
            <strong>Akreditasyon KYS</strong>
            <span>{themeValue.packageName} · {activeProgramRole}</span>
          </div>
          <button
            type="button"
            className="sidebar-collapse-button"
            onClick={() => setManualSidebarCollapsed((value) => !value)}
            title={manualSidebarCollapsed ? "Sidebar genişlet" : "Sidebar daralt"}
          >
            {manualSidebarCollapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
          </button>
        </div>

        <div className="program-box">
          <label className="field-label">Kurum / Üniversite</label>
          <select value={activeTenantGroup.id || ""} onChange={(event) => selectActiveTenant(event.target.value)} disabled={tenantGroups.length <= 1}>
            {tenantGroups.map((tenant) => <option key={tenant.id} value={tenant.id}>{tenant.name}</option>)}
          </select>
          <label className="field-label">Fakülte / MYO</label>
          <select value={activeSchool} onChange={(event) => selectActiveSchool(event.target.value)} disabled={!schoolOptions.length}>
            {!schoolOptions.length && <option value="">Fakülte / MYO tanımlanmadı</option>}
            {schoolOptions.map((school) => <option key={school} value={school}>{school}</option>)}
          </select>
          <label className="field-label">Bölüm</label>
          <select value={activeDepartment} onChange={(event) => selectActiveDepartment(event.target.value)} disabled={!departmentOptions.length}>
            {!departmentOptions.length && <option value="">Bölüm tanımlanmadı</option>}
            {departmentOptions.map((department) => (
              <option key={department} value={department}>{department}</option>
            ))}
          </select>
          <label className="field-label">Program</label>
          <select value={activeProgram} onChange={(event) => setActiveProgram(event.target.value)} disabled={!departmentPrograms.length}>
            {!departmentPrograms.length && <option value="">Program tanımlanmadı</option>}
            {departmentPrograms.map((program) => (
              <option key={program.id} value={program.id}>{programOnlyDisplayLabel(program)}</option>
            ))}
          </select>
          <div className="program-context-card">
            <span>{activeTenantGroup.name || tenantNameOf(activeProgramObj)} · {activeProgramObj?.accreditation_profile || "Profil"} · {activeProgramObj?.report_year || "-"}</span>
            <strong>{shortProgramLabel(activeProgramObj)}</strong>
            <small>{activeProgramObj?.department_name || "Bölüm belirtilmedi"}</small>
            <em>{activeProgramRole}</em>
            <div className="program-context-progress"><i style={{ width: `${sidebarProgress}%` }} /></div>
          </div>
        </div>

        <div className="sidebar-progress-card">
          <span>Program Hazırlığı</span>
          <strong>{sidebarProgress}%</strong>
          <div className="sidebar-progress"><i style={{ width: `${sidebarProgress}%` }} /></div>
          <small>{dashboard?.summary?.ready_sections ?? 0}/{dashboard?.summary?.total_sections ?? 0} başlık hazır</small>
        </div>

        <button type="button" className="quick-search-trigger" onClick={() => setQuickSearchOpen(true)}>
          <Command size={16} />
          <span>Hızlı arama</span>
          <kbd>Ctrl K</kbd>
        </button>

        {favoriteVisibleModules.length > 0 && (
          <NavSection
            title="Favoriler"
            items={favoriteVisibleModules}
            activeModule={activeModule}
            setActiveModule={setActiveModule}
            badges={computeModuleBadges({ sections, dashboard, unread: notificationUnreadCount })}
            favoriteSet={favoriteSet}
            onToggleFavorite={toggleFavoriteModule}
            pinned
          />
        )}

        {navigationGroups.map((group) => (
          <NavSection
            key={group.title}
            title={group.title}
            items={group.items}
            activeModule={activeModule}
            setActiveModule={setActiveModule}
            badges={computeModuleBadges({ sections, dashboard, unread: notificationUnreadCount })}
            favoriteSet={favoriteSet}
            onToggleFavorite={toggleFavoriteModule}
          />
        ))}

        <div className="user-card">
          <div className="avatar">{(user.full_name || user.username || "U").slice(0, 1).toUpperCase()}</div>
          <strong>{user.full_name || user.username}</strong>
          <span>{user.username}</span>
          <em className="role-chip">{activeProgramRole}</em>
          <button className="ghost-button" onClick={logout}><LogOut size={16} /> Çıkış</button>
        </div>
      </aside>

      <main className={`workspace module-${activeModule}`}>
        <header className="topbar">
          <div>
            <span className="eyebrow">Kurumsal Akreditasyon Yönetimi</span>
            <h1>{title}</h1>
            <p className="topbar-subtitle">{moduleHint}</p>
          </div>
          
          <div className="topbar-actions">
            <div className="user-info" style={{ textAlign: 'right', marginRight: '15px' }}>
              <div className="eyebrow">{activeProgramRole}</div>
              <div style={{ fontSize: '0.9em', fontWeight: 'bold' }}>{user.academic_status} • {user.full_name}</div>
            </div>
            <button className={`bell-button ${notificationUnreadCount ? "has-unread" : ""}`} onClick={() => setActiveModule("notifications")} title={liveConnected ? "Canlı bildirim bağlantısı açık" : "Bildirim merkezi"}>
              <Bell size={16} />
              <span>Bildirim</span>
              {notificationUnreadCount > 0 && <em>{notificationUnreadCount > 99 ? "99+" : notificationUnreadCount}</em>}
              <i className={liveConnected ? "live-dot on" : "live-dot"} />
            </button>
            {isSuperAdmin && <button onClick={() => setActiveModule("appearance")}><Moon size={16} /> Görünüm</button>}<button onClick={reloadAll}><RefreshCw size={16} /> Yenile</button>
          </div>
        </header>
             

        {!isOnline && <div className="alert warning pwa-status">Çevrimdışı moddasınız. Mobil/PWA güvenliği için düzenleme ve yükleme işlemleri geçici olarak salt okunur moda alındı.</div>}
        {swUpdateReady && <div className="alert success pwa-status">Yeni sürüm hazır. <button onClick={() => window.location.reload()}>Şimdi yenile</button></div>}
        {installPrompt && <div className="alert success pwa-status">Bu sistemi mobil/masaüstü uygulama gibi kurabilirsiniz. <button onClick={installPwa}>Kur</button></div>}
        {error && <div className="alert error"><span>{error}</span><button type="button" onClick={() => setError("")}>Kapat</button></div>}
        {message && <div className="alert success">{message}</div>}

        <ErrorBoundary resetKey={activeModule} onReset={() => setActiveModule(firstVisibleModule)}>
        {renderModule === "dashboard" && <DashboardView programId={activeProgram} program={activeProgramObj} dashboard={dashboard} sections={sections} user={programUser} dashboardPermissions={dashboardPermissions} onPick={openSection} onError={setError} />}
        {renderModule === "notifications" && <NotificationCenterView programId={activeProgram} onError={setError} onMessage={showMessage} onPick={openSection} />}
        {renderModule === "tasks" && <TasksAndGapsView programId={activeProgram} onError={setError} onPick={openSection} />}
        {renderModule === "entry" && (
          <EntryView
            user={programUser}
            sections={sections}
            activeSectionKey={activeSectionKey}
            setActiveSectionKey={setActiveSectionKey}
            activeSection={activeSection}
            form={form}
            setForm={setForm}
            readOnly={effectiveReadOnly}
            busy={busy}
            onSave={saveSection}
            onError={setError}
            onMessage={showMessage}
            programId={activeProgram}
            setActiveModule={setActiveModule}
            hasUnsavedSectionChanges={hasUnsavedSectionChanges}
            autosaveState={autosaveState}
          />
        )}
        {renderModule === "evidence" && <EvidenceView programId={activeProgram} sections={sections} activeSectionKey={activeSectionKey} user={programUser} offline={!isOnline} onError={setError} onMessage={showMessage} />}
        {renderModule === "tables" && <TablesView programId={activeProgram} sections={sections} activeSectionKey={activeSectionKey} user={programUser} offline={!isOnline} onError={setError} onMessage={showMessage} />}
        {renderModule === "control" && <ControlView programId={activeProgram} onError={setError} onPick={openSection} />}
        {renderModule === "audit" && <ReadinessView programId={activeProgram} onError={setError} onPick={openSection} />}
        {renderModule === "search" && <SearchView programId={activeProgram} onError={setError} onPick={openSection} />}
        {renderModule === "stats" && <StatsView programId={activeProgram} onError={setError} onPick={openSection} />}
        {renderModule === "advanced" && <AdvancedDashboardView programId={activeProgram} onError={setError} onMessage={showMessage} onPick={openSection} />}
        {renderModule === "professional" && <ProfessionalReportingView programId={activeProgram} sections={sections} activeSectionKey={activeSectionKey} setActiveSectionKey={setActiveSectionKey} onPick={openSection} onError={setError} onMessage={showMessage} refresh={() => refreshProgram(activeProgram)} />}
        {renderModule === "timeline" && <ActivityTimelineView programId={activeProgram} onError={setError} onPick={openSection} />}
        {renderModule === "versions" && <VersionDiffView programId={activeProgram} sections={sections} activeSectionKey={activeSectionKey} setActiveSectionKey={setActiveSectionKey} onError={setError} />}
        {renderModule === "assistant" && <AssistantView programId={activeProgram} sections={sections} activeSectionKey={activeSectionKey} setActiveSectionKey={setActiveSectionKey} form={form} setForm={setForm} readOnly={readOnly} onError={setError} onMessage={showMessage} />}
        {renderModule === "approval" && <ApprovalView programId={activeProgram} sections={sections} activeSectionKey={activeSectionKey} setActiveSectionKey={setActiveSectionKey} user={programUser} hasUnsavedSectionChanges={hasUnsavedSectionChanges} onError={setError} onMessage={showMessage} refresh={() => refreshProgram(activeProgram)} />}
        {renderModule === "preview" && <PreviewView programId={activeProgram} onError={setError} onMessage={showMessage} onPick={openSection} />}
        {renderModule === "docx" && <DocxImportView programId={activeProgram} onError={setError} onMessage={showMessage} refresh={() => refreshProgram(activeProgram)} />}
        {renderModule === "fullReport" && <FullReportView programId={activeProgram} onError={setError} onMessage={showMessage} />}
        {renderModule === "export" && <ExportView programId={activeProgram} user={programUser} onError={setError} onMessage={showMessage} />}
        {renderModule === "exportHistory" && <ExportHistoryView programId={activeProgram} onError={setError} onMessage={showMessage} />}
        {renderModule === "programs" && <ProgramsView user={user} activeProgram={activeProgram} sections={sections} onError={setError} onMessage={showMessage} refreshPrograms={async () => { await reloadWorkspaceOptions({ preserveProgram: true }); }} />}
        {renderModule === "users" && <UsersView user={user} programs={programs} sections={sections} onError={setError} onMessage={showMessage} />}
        {renderModule === "deadlines" && <DeadlineView programId={activeProgram} user={programUser} onError={setError} onMessage={showMessage} />}
        {renderModule === "deadlineCalendar" && <DeadlineCalendarView programId={activeProgram} onError={setError} onPick={openSection} />}
        {renderModule === "bulk" && <BulkView programId={activeProgram} sections={sections} onError={setError} onMessage={showMessage} refresh={() => refreshProgram(activeProgram)} />}
        {renderModule === "permissions" && <PermissionMatrixView programId={activeProgram} sections={sections} currentRole={normalizeRole(user.role, user.tenant_scope)} onError={setError} onMessage={showMessage} onMatrixSaved={refreshCurrentUser} />}
        {renderModule === "recovery" && <RecoveryView onError={setError} onMessage={showMessage} refreshPrograms={async () => { await reloadWorkspaceOptions({ preserveProgram: true }); }} />}
        {renderModule === "analytics" && <AnalyticsView onError={setError} />}
        {renderModule === "updateCenter" && <UpdateCenterView onError={setError} onMessage={showMessage} refreshPrograms={async () => { await reloadWorkspaceOptions({ preserveProgram: true }); }} />}
        {renderModule === "appearance" && <AppearanceView user={user} currentAppearance={tenantAppearance} setTenantAppearance={setTenantAppearance} onError={setError} onMessage={showMessage} />}
        {renderModule === "settings" && <SettingsView programId={activeProgram} onError={setError} onMessage={showMessage} refresh={() => refreshProgram(activeProgram)} />}
        {renderModule === "help" && <HelpView programId={activeProgram} onError={setError} />}
        {visibleModules.length === 0 && !sessionAdminCanKeepMatrixOpen && (
          <section className="editor-panel error-panel">
            <div className="editor-header">
              <div>
                <span className="badge warning">Menü görünürlüğü kapalı</span>
                <h2>Bu rol için görünür modül bulunmuyor.</h2>
              </div>
            </div>
            <p className="muted">Yetki Matrisi veya Sidebar Visibility ayarlarında bu rol için en az bir modül açılmalıdır.</p>
          </section>
        )}
        {!activeModuleCanRender && visibleModules.length > 0 && moduleCatalog[activeModule] && (
          <section className="editor-panel error-panel">
            <div className="editor-header">
              <div>
                <span className="badge warning">Modül erişimi güncellendi</span>
                <h2>Bu ekran artık menü görünürlüğünde değil.</h2>
              </div>
              <button type="button" onClick={() => setActiveModule(firstVisibleModule)}>Görünür ilk ekrana dön</button>
            </div>
            <p className="muted">Yetki Matrisi veya sidebar görünürlüğü değiştiğinde aktif ekran geçici olarak görünür listeden çıkabilir. Sayfa boş kalmaması için bu güvenli uyarı gösterilir.</p>
          </section>
        )}
        {activeModule && !moduleCatalog[activeModule] && <div className="empty-state">Bu modül bulunamadı.</div>}
        </ErrorBoundary>
      </main>
      <MobileBottomNav items={mobileNavItems} activeModule={activeModule} setActiveModule={setActiveModule} unread={notificationUnreadCount} liveConnected={liveConnected} />
    </div>
    </TenantThemeProvider>
  );
}

function QuickSearchOverlay({ open, query, setQuery, modules, activeModule, onClose, onSelect }) {
  if (!open) return null;
  const normalizedQuery = String(query || "").toLocaleLowerCase("tr-TR").trim();
  const rows = modules
    .map((id) => ({ id, item: moduleCatalog[id] }))
    .filter(({ item }) => item)
    .filter(({ id, item }) => {
      if (!normalizedQuery) return true;
      const [label, , hint] = item;
      return `${id} ${label} ${hint}`.toLocaleLowerCase("tr-TR").includes(normalizedQuery);
    })
    .slice(0, 10);
  return (
    <div className="quick-search-backdrop" onMouseDown={onClose}>
      <div className="quick-search-modal" onMouseDown={(event) => event.stopPropagation()}>
        <div className="quick-search-input-row">
          <Search size={18} />
          <input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Modül, rapor, kanıt veya yönetim ekranı ara..."
          />
          <button type="button" onClick={onClose} aria-label="Hızlı aramayı kapat"><X size={17} /></button>
        </div>
        <div className="quick-search-results">
          {rows.map(({ id, item }) => {
            const [label, Icon, hint] = item;
            return (
              <button key={id} type="button" className={activeModule === id ? "active" : ""} onClick={() => onSelect(id)}>
                <Icon size={18} />
                <span><strong>{label}</strong><small>{hint}</small></span>
              </button>
            );
          })}
          {!rows.length && <div className="quick-search-empty">Sonuç bulunamadı.</div>}
        </div>
      </div>
    </div>
  );
}
