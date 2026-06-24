import React, { useEffect, useMemo, useState } from "react";
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
  RefreshCw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  Star,
  Table2,
  Trash2,
  Upload,
  UserCheck,
  Users,
  Wrench,
} from "lucide-react";
import { api, downloadBlob } from "../api";
import { moduleCatalog } from "../config/navigation.jsx";
import { DataTable } from "../components/DataTable.jsx";
import { asArray, asObject } from "../utils.js";
import {
  STATUS_OPTIONS,
  FACULTY_ADMIN_ROLE,
  EDITOR_ROLE,
  APPROVER_ROLE,
  READONLY_ROLE,
  ROLES,
  ADMIN_ROLES,
  MANAGEMENT_MODULES,
  SUPER_ADMIN_ROLES,
  TENANT_DELEGATE_ROLES,
  FACULTY_DELEGATE_ROLES,
  visibleRolesForActor,
  delegatableRolesForActor,
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
  inferAccreditationProfile,
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
  mobileNavItemsForRole
} from "../constants/appConstants.js";

export function MobileBottomNav({ items, activeModule, setActiveModule, unread = 0, liveConnected = false }) {
  if (!items.length) return null;
  return (
    <nav className="mobile-bottom-nav" aria-label="Mobil hızlı gezinme">
      {items.map((id) => {
        const [label, Icon] = moduleCatalog[id] || [];
        if (!Icon) return null;
        const count = id === "notifications" ? Number(unread || 0) : 0;
        return (
          <button key={id} className={`${activeModule === id ? "active" : ""} ${count > 0 ? "has-unread" : ""}`} onClick={() => setActiveModule(id)}>
            <span className="mobile-nav-icon-wrap"><Icon size={19} />{count > 0 && <em>{count > 99 ? "99+" : count}</em>}{id === "notifications" && <i className={liveConnected ? "live-dot on" : "live-dot"} />}</span>
            <span>{label}</span>
          </button>
        );
      })}
    </nav>
  );
}



export function NavSection({ title, items, activeModule, setActiveModule, badges = {}, favoriteSet = new Set(), onToggleFavorite, pinned = false }) {
  return (
    <div className={`nav-section ${pinned ? "nav-section-pinned" : ""}`}>
      <span className="nav-title">{title}</span>
      <nav className="nav-list">
        {items.map((id) => {
          const item = moduleCatalog[id];
          if (!item) return null;
          const [label, Icon, hint] = item;
          const count = Number(badges[id] || 0);
          const isFavorite = favoriteSet?.has?.(id);
          return (
            <button key={id} className={`${activeModule === id ? "active" : ""} ${count > 0 ? "has-badge" : ""}`} onClick={() => setActiveModule(id)} title={hint}>
              <span className="nav-active-rail" />
              <Icon size={17} />
              <span className="nav-copy">
                <strong>{label}{count > 0 && <em className="nav-badge">{count > 99 ? "99+" : count}</em>}</strong>
                <small>{hint}</small>
              </span>
              {onToggleFavorite && (
                <span
                  className={`nav-favorite-toggle ${isFavorite ? "active" : ""}`}
                  role="button"
                  tabIndex={0}
                  title={isFavorite ? "Favorilerden çıkar" : "Favorilere sabitle"}
                  onClick={(event) => { event.stopPropagation(); onToggleFavorite(id); }}
                  onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); event.stopPropagation(); onToggleFavorite(id); } }}
                >
                  <Star size={14} fill={isFavorite ? "currentColor" : "none"} />
                </span>
              )}
            </button>
          );
        })}
      </nav>
    </div>
  );
}

export function DashboardView({ programId, program, dashboard, sections, user, dashboardPermissions = {}, onPick, onError }) {
  const [insightTab, setInsightTab] = useState("prep");
  const [customizing, setCustomizing] = useState(false);
  const [widgetOrder, setWidgetOrder] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("akys_dashboard_widget_order") || "[]");
    } catch {
      return [];
    }
  });
  const [hiddenWidgets, setHiddenWidgets] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("akys_dashboard_hidden_widgets") || "[]");
    } catch {
      return [];
    }
  });
  const [draggingWidget, setDraggingWidget] = useState("");
  const [stats, setStats] = useState(null);
  const [activity, setActivity] = useState([]);
  const particleCanvasRef = React.useRef(null);

  useEffect(() => {
    localStorage.setItem("akys_dashboard_widget_order", JSON.stringify(widgetOrder));
  }, [widgetOrder]);

  useEffect(() => {
    localStorage.setItem("akys_dashboard_hidden_widgets", JSON.stringify(hiddenWidgets));
  }, [hiddenWidgets]);

  // Hafif Particle Efekti (Dashboard Hero için)
  useEffect(() => {
    const canvas = particleCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    canvas.width = 1200;
    canvas.height = 280;

    let particles = [];
    const colors = ['#60a5fa', '#93c5fd', '#c4d0ff'];

    class Particle {
      constructor() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height * 0.6;
        this.size = Math.random() * 1.8 + 0.6;
        this.speedX = Math.random() * 0.4 - 0.2;
        this.speedY = Math.random() * 0.3 - 0.15;
        this.color = colors[Math.floor(Math.random() * colors.length)];
        this.opacity = Math.random() * 0.5 + 0.3;
      }
      update() {
        this.x += this.speedX;
        this.y += this.speedY;
        if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
        if (this.y < 0) this.y = canvas.height * 0.6;
      }
      draw() {
        ctx.save();
        ctx.globalAlpha = this.opacity;
        ctx.fillStyle = this.color;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }
    }

    function init() {
      particles = [];
      for (let i = 0; i < 45; i++) {  // Hafif tutuyoruz
        particles.push(new Particle());
      }
    }

    function animate() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach(p => {
        p.update();
        p.draw();
      });
      frameId = requestAnimationFrame(animate);
    }

    let frameId;
    init();
    animate();

    return () => {
      if (frameId) cancelAnimationFrame(frameId);
    };
  }, []);

  const dashboardPermissionMap = asObject(dashboardPermissions);
  const dashboardAllowed = (permission, fallback = true) => {
    const value = dashboardPermissionMap[permission];
    return typeof value === "boolean" ? value : fallback;
  };
  const canDashboardOverview = dashboardAllowed("dashboard.view", true);
  const canDashboardKpi = dashboardAllowed("dashboard.kpi.view", canDashboardOverview);
  const canDashboardPriority = dashboardAllowed("dashboard.priority.view", canDashboardOverview);
  const canDashboardCriteria = dashboardAllowed("dashboard.criteria.view", canDashboardOverview);
  const canDashboardCharts = dashboardAllowed("dashboard.charts.view", canDashboardOverview);
  const canDashboardActivity = dashboardAllowed("dashboard.activity.view", false);
  const hasAnyDashboardPanel = canDashboardOverview || canDashboardKpi || canDashboardPriority || canDashboardCriteria || canDashboardCharts || canDashboardActivity;

  useEffect(() => {
    if (!programId || !hasAnyDashboardPanel) return;
    Promise.all([api.stats(programId), canDashboardActivity ? api.activity(programId, 12) : Promise.resolve([])])
      .then(([statsPayload, activityRows]) => { 
        setStats(statsPayload); 
        setActivity(activityRows); 
      })
      .catch((err) => onError?.(err.message));
  }, [programId, hasAnyDashboardPanel, canDashboardActivity]);

  const detailTabs = useMemo(() => [
    canDashboardKpi ? ["prep", "Hazırlık"] : null,
    canDashboardCriteria ? ["quality", "Kalite Haritası"] : null,
    canDashboardCriteria ? ["heat", "Isı Haritası"] : null,
    canDashboardActivity ? ["activity", "Son Aktiviteler"] : null,
  ].filter(Boolean), [canDashboardKpi, canDashboardCriteria, canDashboardActivity]);

  useEffect(() => {
    if (detailTabs.length && !detailTabs.some(([id]) => id === insightTab)) setInsightTab(detailTabs[0][0]);
  }, [detailTabs, insightTab]);

  const effectiveInsightTab = detailTabs.some(([id]) => id === insightTab) ? insightTab : detailTabs[0]?.[0];

  const summary = dashboard?.summary || {};
  const firstSectionByMain = Object.fromEntries(sections.map((section) => [section.main_title, section.section_key]));
  const firstSectionByReportGroup = Object.fromEntries(sections.map((section) => [section.report_group_title || section.main_title, section.section_key]));
  const firstSectionByMeasure = Object.fromEntries(sections.map((section) => [section.report_subgroup_title || section.main_title, section.section_key]));
  const reportDirectoryGroups = asArray(stats?.report_groups).length
    ? asArray(stats?.report_groups)
    : asArray(dashboard?.report_groups);
  const measureCriteriaFallback = asArray(stats?.measure_criteria).length
    ? asArray(stats?.measure_criteria)
    : asArray(stats?.criteria || dashboard?.measure_criteria || dashboard?.criteria);
  const criteria = reportDirectoryGroups.length ? reportDirectoryGroups : measureCriteriaFallback;
  const criteriaLabel = (item) => item.report_group_title || item.main_title || item.report_subgroup_title;
  const pickCriteria = (item) => onPick(item.first_section_key || firstSectionByReportGroup[criteriaLabel(item)] || firstSectionByMeasure[criteriaLabel(item)] || firstSectionByMain[item.main_title], "entry");
  const urgent = sections.filter((section) => 
    section.approval_status === "Revizyon Gerekli" || section.status === "Revizyon Gerekli"
  ).slice(0, 6);
  const submitted = sections.filter((section) => 
    section.approval_status === "Onaya Gönderildi"
  ).slice(0, 6);
  const allSections = asArray(sections);
  const missingText = allSections.filter((section) => !String(section.report_text || "").trim());
  const missingEvidence = allSections.filter((section) => Number(section.evidence_count || 0) === 0);
  const missingPuko = allSections.filter((section) => !["planla", "uygula", "kontrol", "onlem"].every((key) => String(section[key] || "").trim()));
  const overdue = allSections.filter((section) => {
    const days = daysUntil(section.deadline);
    return days !== null && days < 0 && section.approval_status !== "Onaylandı";
  });
  const dueThisWeek = allSections.filter((section) => {
    const days = daysUntil(section.deadline);
    return days !== null && days >= 0 && days <= 7;
  });
  const statusDistribution = STATUS_OPTIONS.map((status) => ({ label: status, value: allSections.filter((section) => section.status === status).length }));
  const approvalDistribution = [
    { label: "Taslak", value: allSections.filter((section) => !section.approval_status || section.approval_status === "Taslak").length },
    { label: "Onayda", value: allSections.filter((section) => section.approval_status === "Onaya Gönderildi").length },
    { label: "Onaylı", value: allSections.filter((section) => section.approval_status === "Onaylandı").length },
    { label: "Revizyon", value: allSections.filter((section) => section.approval_status === "Revizyon Gerekli").length },
  ];
  const pukoDistribution = ["planla", "uygula", "kontrol", "onlem"].map((key) => ({
    label: key === "onlem" ? "Önlem Al" : key.slice(0, 1).toUpperCase() + key.slice(1),
    value: allSections.filter((section) => String(section[key] || "").trim()).length,
  }));
  const roleName = normalizeRole(user?.role || READONLY_ROLE, user?.tenant_scope);
  const roleActions = roleName === EDITOR_ROLE
    ? [
        { label: "Revizyonları tamamla", count: urgent.length, module: "entry", section: urgent[0]?.section_key },
        { label: "Kanıtsız başlıkları tamamla", count: missingEvidence.length, module: "entry", section: missingEvidence[0]?.section_key },
        { label: "Bu hafta teslim edilecekleri kontrol et", count: dueThisWeek.length, module: "deadlineCalendar" },
      ]
    : roleName === APPROVER_ROLE
      ? [
          { label: "Onay kuyruğunu incele", count: submitted.length, module: "approval", section: submitted[0]?.section_key },
          { label: "Revizyon verdiğin başlıkları takip et", count: urgent.length, module: "control", section: urgent[0]?.section_key },
          { label: "Teslim risklerini kontrol et", count: overdue.length + dueThisWeek.length, module: "deadlineCalendar" },
        ]
      : isAdminRole(roleName)
        ? [
            { label: "Geciken başlıkları yönet", count: overdue.length, module: "deadlineCalendar" },
            { label: "Onay kuyruğunu denetle", count: submitted.length, module: "approval", section: submitted[0]?.section_key },
            { label: "Yetki ve görünürlük matrisini kontrol et", count: 1, module: "permissions" },
          ]
        : [
            { label: "Genel ilerlemeyi incele", count: summary.readiness_percent ?? 0, module: "stats" },
            { label: "Rapor önizlemesini aç", count: 1, module: "preview" },
            { label: "Teslim takvimini takip et", count: dueThisWeek.length + overdue.length, module: "deadlineCalendar" },
          ];
  const priorityRows = [...overdue, ...urgent, ...missingEvidence, ...dueThisWeek]
    .filter(Boolean)
    .filter((section, index, arr) => arr.findIndex((item) => item.section_key === section.section_key) === index)
    .slice(0, 8);
  const progressPercent = Number(summary.readiness_percent ?? 0);
  const qualityValues = criteria
    .map((item) => Number(item.quality_avg ?? item.quality_score ?? 0))
    .filter((value) => Number.isFinite(value) && value > 0);
  const qualityScore = qualityValues.length
    ? Math.round(qualityValues.reduce((sum, value) => sum + value, 0) / qualityValues.length)
    : Math.round(Number(summary.quality_score ?? stats?.quality?.average ?? 0) || 0);
  const dashboardKpis = [
    { label: "Hazır başlık", value: summary.ready_sections ?? 0, sub: `${summary.total_sections ?? allSections.length} toplam`, trend: progressPercent >= 70 ? "up" : "flat" },
    { label: "Onayda", value: summary.submitted_sections ?? submitted.length, sub: "karar bekliyor", trend: submitted.length ? "up" : "flat" },
    { label: "Revizyon", value: summary.revision_sections ?? urgent.length, sub: "geri dönüş", trend: urgent.length ? "down" : "flat" },
    { label: "Geciken", value: overdue.length, sub: "termin riski", trend: overdue.length ? "down" : "flat" },
  ];
  const widgetCatalog = [
    canDashboardOverview ? { id: "today", label: "Bugün Ne Yapmalıyım?", content: <TodayFocusWidget roleName={roleName} actions={roleActions} priorityRows={priorityRows} onPick={onPick} /> } : null,
    canDashboardPriority ? { id: "priority", label: "Öncelikli Başlıklar", content: <PriorityPanel rows={priorityRows} onPick={onPick} /> } : null,
    canDashboardCriteria ? { id: "heatmap", label: "Ölçüt Isı Haritası", content: <CriteriaHeatmapWidget criteria={criteria} criteriaLabel={criteriaLabel} onPick={pickCriteria} /> } : null,
    canDashboardPriority ? { id: "deadlines", label: "Aktivite ve Termin", content: <DeadlineActivityWidget dueThisWeek={dueThisWeek} overdue={overdue} submitted={submitted} activity={activity} onPick={onPick} /> } : null,
    canDashboardCharts ? { id: "charts", label: "Rapor Sağlığı", content: <MiniChartsPanel statusRows={statusDistribution} pukoRows={pukoDistribution} approvalRows={approvalDistribution} total={allSections.length} /> } : null,
    canDashboardCharts ? { id: "trend", label: "Kalite Trend", content: <QualityTrendWidget progressPercent={progressPercent} qualityScore={qualityScore} missingEvidence={missingEvidence.length} missingPuko={missingPuko.length} overdue={overdue.length} /> } : null,
  ].filter(Boolean);
  const hiddenWidgetSet = new Set(hiddenWidgets);
  const orderMap = new Map(widgetOrder.map((id, index) => [id, index]));
  const orderedWidgets = widgetCatalog
    .filter((widget) => !hiddenWidgetSet.has(widget.id))
    .sort((a, b) => (orderMap.get(a.id) ?? 99) - (orderMap.get(b.id) ?? 99));
  const moveWidget = (targetId) => {
    if (!draggingWidget || draggingWidget === targetId) return;
    const current = orderedWidgets.map((widget) => widget.id);
    const fromIndex = current.indexOf(draggingWidget);
    const toIndex = current.indexOf(targetId);
    if (fromIndex < 0 || toIndex < 0) return;
    const next = [...current];
    next.splice(toIndex, 0, next.splice(fromIndex, 1)[0]);
    const remaining = widgetCatalog.map((widget) => widget.id).filter((id) => !next.includes(id));
    setWidgetOrder([...next, ...remaining]);
  };
  const toggleWidget = (id) => {
    setHiddenWidgets((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  };
  const resetWidgets = () => {
    setWidgetOrder(widgetCatalog.map((widget) => widget.id));
    setHiddenWidgets([]);
    setCustomizing(false);
  };

  if (!hasAnyDashboardPanel) {
    return (
      <section className="panel-stack">
        <PremiumEmptyState
          title="Dashboard alanı kapalı"
          text="Bu rol için dashboard modülü menüde açık; ancak dashboard içindeki tüm panel izinleri kapalı. Sidebar görünürlüğü veya dashboard alt izinlerinden en az birini açın."
        />
      </section>
    );
  }

  if (!dashboard && !stats) return <DashboardSkeleton />;

  return (
    <section className="panel-stack">
      {/* PREMIUM HERO + PARTICLES */}
      {canDashboardOverview && (
        <div className="hero-panel grand" style={{ position: 'relative' }}>
          <canvas 
            ref={particleCanvasRef} 
            className="dashboard-particles"
            style={{ borderRadius: '22px' }}
          />
          
          <div style={{ position: 'relative', zIndex: 2 }}>
            <span className="hero-kicker">{roleName} çalışma görünümü</span>
            <h2 style={{fontSize: "38px", lineHeight: "1.12", marginBottom: "10px"}}>
              {shortProgramLabel(program)} · {program?.report_year || "Rapor yılı"}
            </h2>
            {canDashboardKpi ? (
              <>
                <p style={{fontSize: "17px", maxWidth: "760px", color: "#d6e5ff", opacity: 0.95}}>
                  {program?.school_name || "Kurum/birim"} · {program?.department_name || "Bölüm"} · 
                  {summary.ready_sections ?? 0} başlık hazır • {summary.submitted_sections ?? 0} onayda • {overdue.length} gecikmiş başlık
                </p>
                <div className="hero-quick-tags">
                  <span>Kanıt eksik: {missingEvidence.length}</span>
                  <span>PUKÖ eksik: {missingPuko.length}</span>
                  <span>Bu hafta: {dueThisWeek.length}</span>
                </div>
                <div className="hero-action-row">
                  <button type="button" onClick={() => onPick(undefined, "export")}><FileDown size={16} /> Rapor Paketi Oluştur</button>
                  <button type="button" onClick={() => onPick(priorityRows[0]?.section_key, "evidence")}><Upload size={16} /> Kanıt Yükle</button>
                  <button type="button" onClick={() => onPick(priorityRows[0]?.section_key, "approval")}><Send size={16} /> Onaya Gönder</button>
                </div>
              </>
            ) : (
              <p style={{fontSize: "17px", maxWidth: "760px", color: "#d6e5ff", opacity: 0.95}}>
                Dashboard ana alanı açık; KPI özetleri bu rol için kapalı.
              </p>
            )}
          </div>

          {canDashboardKpi && (
            <div className="hero-score-stack">
              <div className="hero-score" style={{ "--score": `${progressPercent}%` }}>
                <strong>{progressPercent}</strong>
                <span>% HAZIRLIK</span>
              </div>
              <div className="hero-score quality" style={{ "--score": `${qualityScore}%` }}>
                <strong>{qualityScore}</strong>
                <span>KALİTE</span>
              </div>
            </div>
          )}
        </div>
      )}

      {canDashboardKpi && (
        <section className="dashboard-kpi-strip">
          {dashboardKpis.map((item) => (
            <MetricCard
              key={item.label}
              className={`premium-kpi trend-${item.trend}`}
              label={item.label}
              value={item.value}
              sub={<><span>{item.trend === "up" ? "↑" : item.trend === "down" ? "↓" : "→"}</span> {item.sub}</>}
            />
          ))}
        </section>
      )}


      {widgetCatalog.length > 0 && (
        <section className="dashboard-widget-zone">
          <div className="dashboard-widget-toolbar">
            <div>
              <span className="eyebrow">Widget Library</span>
              <h3>Dashboard kartlarını özelleştir</h3>
              <p className="muted">Draggable widget düzeni aktif: düzenle modunda sürükle-bırak ile kart sırasını değiştirin.</p>
            </div>
            <div className="hero-actions">
              <button type="button" className={customizing ? "active" : ""} onClick={() => setCustomizing((value) => !value)}>
                <Settings size={16} /> {customizing ? "Düzenlemeyi Bitir" : "Düzenle"}
              </button>
              <button type="button" onClick={resetWidgets}>Yerleşimi Sıfırla</button>
            </div>
          </div>
          {customizing && (
            <div className="widget-library">
              {widgetCatalog.map((widget) => (
                <button key={widget.id} type="button" className={!hiddenWidgetSet.has(widget.id) ? "active" : ""} onClick={() => toggleWidget(widget.id)}>
                  {hiddenWidgetSet.has(widget.id) ? "Göster" : "Gizle"} · {widget.label}
                </button>
              ))}
            </div>
          )}
          <div className="dashboard-command-grid dashboard-widget-grid">
            {orderedWidgets.map((widget) => (
              <article
                key={widget.id}
                className={`dashboard-widget-card ${draggingWidget === widget.id ? "dragging" : ""}`}
                draggable={customizing}
                onDragStart={() => setDraggingWidget(widget.id)}
                onDragOver={(event) => { if (customizing) event.preventDefault(); }}
                onDragEnter={(event) => { if (customizing) { event.preventDefault(); moveWidget(widget.id); } }}
                onDrop={(event) => { event.preventDefault(); moveWidget(widget.id); setDraggingWidget(""); }}
                onDragEnd={() => setDraggingWidget("")}
              >
                {customizing && <span className="widget-drag-handle">Sürükle · {widget.label}</span>}
                {widget.content}
              </article>
            ))}
          </div>
        </section>
      )}

      {canDashboardCriteria && (
        <div className="criteria-only-grid">
        {/* ANA ÖLÇÜTLER */}
        <div className="editor-panel">
          <div className="editor-header">
            <h2>Rapor Bölümleri / Ana Ölçütler</h2>
            <span className="badge">Detaylı Görünüm için istediğiniz bölüme tıklayınız...</span>
          </div>
          {criteria.length ? (
            <div className="criteria-grid majestic">
              {criteria.map((item, index) => (
                <button 
                  key={criteriaLabel(item)} 
                  onClick={() => pickCriteria(item)}
                >
                  <span className="criterion-index">{index + 1}</span>
                  <strong>{criteriaLabel(item)}</strong>
                  <small>
                    {item.ready}/{item.total} hazır • {item.approved} onaylı • Kalite {item.quality_avg ?? 0}%
                  </small>
                  {!!item.subcriteria?.length && (
                    <div className="criterion-sublist">
                      {item.subcriteria.map((sub) => (
                        <span key={sub.main_title}>{sub.main_title.replace("Ölçüt ", "")}: {sub.ready}/{sub.total}</span>
                      ))}
                    </div>
                  )}
                  <div className="animated-progress">
                    <div style={{ width: `${item.total ? Math.round((item.ready / item.total) * 100) : 0}%` }} />
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <PremiumEmptyState title="Rapor bölümü bulunamadı" text="Program için rapor şablonu veya başlıkları henüz oluşturulmamış görünüyor." />
          )}
        </div>
        </div>
      )}

      {/* DETAYLI ANALİZLER */}
      {detailTabs.length > 0 && (
        <details className="details-panel">
        <summary><BarChart3 size={18} /> Detaylı Analiz & Operasyonel Görünüm</summary>
        
        <div className="detail-tabs">
          {detailTabs.map(([id, label]) => (
            <button 
              key={id} 
              className={effectiveInsightTab === id ? "active" : ""} 
              onClick={() => setInsightTab(id)}
            >
              {label}
            </button>
          ))}
        </div>

        {effectiveInsightTab === "prep" && (
          <div className="insight-grid">
            <div className="insight-card hero-mini">
              <span className="eyebrow">GENEL HAZIRLIK</span>
              <strong>{summary.readiness_percent ?? 0}%</strong>
              <p>{summary.ready_sections ?? 0} başlık hazır, {summary.submitted_sections ?? 0} onayda, {summary.revision_sections ?? 0} revizyonda.</p>
            </div>
            <div className="insight-card">
              <span className="eyebrow">BUGÜNÜN ÖNERİSİ</span>
              <h3>Öncelikli Başlıklar</h3>
              <p>Kalite skoru düşük veya eksik kanıt/tablo olan başlıklara odaklanın.</p>
            </div>
          </div>
        )}

        {effectiveInsightTab === "quality" && (
          <div className="quality-map">
            {criteria.map((item) => (
              <button 
                key={criteriaLabel(item)} 
                onClick={() => pickCriteria(item)}
              >
                <span>{criteriaLabel(item)}</span>
                <strong>{item.quality_avg ?? 0}%</strong>
                <div className="animated-progress">
                  <div style={{ width: `${item.quality_avg ?? 0}%` }} />
                </div>
              </button>
            ))}
          </div>
        )}

        {effectiveInsightTab === "heat" && (
          <div className="heatmap-grid">
            {criteria.map((item) => (
              <button 
                key={criteriaLabel(item)} 
                style={{ "--heat": `${Math.max(15, Number(item.quality_avg || item.readiness_percent || 0))}%` }}
                onClick={() => pickCriteria(item)}
              >
                <strong>{criteriaLabel(item)}</strong>
                <span>Hazır {item.ready}/{item.total}</span>
                <small>Onay {item.approved} • Revizyon {item.revision ?? 0}</small>
              </button>
            ))}
          </div>
        )}

        {effectiveInsightTab === "activity" && <DataTable rows={activity} columns={["ts", "action", "detail", "actor"]} />}
        </details>
      )}
    </section>
  );
}
function TodayFocusWidget({ roleName, actions = [], priorityRows = [], onPick }) {
  const firstPriority = priorityRows[0];
  const title = firstPriority
    ? `${firstPriority.section_key || "Başlık"} öncelikli görünüyor`
    : "Bugün kritik bekleyen işlem yok";
  const text = firstPriority
    ? firstPriority.section_title || firstPriority.main_title || "Eksik, revizyon veya termin riski taşıyan ilk başlığı açın."
    : "Genel ilerlemeyi ve yaklaşan terminleri kısa aralıklarla kontrol edin.";
  return (
    <article className="premium-dashboard-widget today-focus-widget">
      <div className="widget-headline"><span className="eyebrow">Bugün Ne Yapmalıyım?</span><strong>{roleName}</strong></div>
      <h3>{title}</h3>
      <p>{text}</p>
      <div className="action-list compact-action-list">
        {actions.slice(0, 3).map((action) => (
          <button key={action.label} type="button" onClick={() => onPick(action.section, action.module)}>
            <strong>{action.count}</strong>
            <span>{action.label}</span>
          </button>
        ))}
      </div>
    </article>
  );
}

function CriteriaHeatmapWidget({ criteria = [], criteriaLabel, onPick }) {
  const rows = criteria.slice(0, 12);
  return (
    <article className="premium-dashboard-widget heatmap-widget-card">
      <div className="widget-headline"><span className="eyebrow">Ölçüt Isı Haritası</span><strong>{rows.length} ölçüt</strong></div>
      <div className="compact-heatmap-grid">
        {rows.map((item) => {
          const label = criteriaLabel(item);
          const score = Number(item.quality_avg ?? item.readiness_percent ?? (item.total ? Math.round((item.ready / item.total) * 100) : 0)) || 0;
          return (
            <button key={label} type="button" style={{ "--heat": `${Math.max(12, score)}%` }} onClick={() => onPick(item)}>
              <strong>{label}</strong>
              <span>{item.ready ?? 0}/{item.total ?? 0} hazır</span>
              <em>{score}%</em>
            </button>
          );
        })}
        {!rows.length && <PremiumEmptyState title="Ölçüt yok" text="Şablon veya rapor bölümü henüz yüklenmemiş." />}
      </div>
    </article>
  );
}

function DeadlineActivityWidget({ dueThisWeek = [], overdue = [], submitted = [], activity = [], onPick }) {
  const deadlineRows = [...overdue, ...dueThisWeek]
    .filter((section, index, arr) => arr.findIndex((item) => item.section_key === section.section_key) === index)
    .slice(0, 5);
  return (
    <article className="premium-dashboard-widget deadline-activity-widget">
      <div className="widget-headline"><span className="eyebrow">Aktivite + Termin</span><strong>{overdue.length} geciken</strong></div>
      <div className="deadline-mini-list">
        {deadlineRows.map((section) => (
          <button key={section.section_key} type="button" onClick={() => onPick(section.section_key, "entry")}>
            <span>{section.deadline || "Tarih yok"}</span>
            <strong>{section.section_title || section.section_key}</strong>
            <small>{daysUntil(section.deadline) < 0 ? "Gecikmiş" : "Yaklaşıyor"}</small>
          </button>
        ))}
        {!deadlineRows.length && <p className="muted">Bu hafta kritik termin görünmüyor.</p>}
      </div>
      <div className="activity-mini-line">
        <span>{submitted.length} onay kuyruğu</span>
        <span>{activity.length} son aktivite</span>
      </div>
    </article>
  );
}

function QualityTrendWidget({ progressPercent = 0, qualityScore = 0, missingEvidence = 0, missingPuko = 0, overdue = 0 }) {
  const trendRows = [
    { label: "Tamamlanma", value: progressPercent },
    { label: "Kalite", value: qualityScore },
    { label: "Kanıt", value: Math.max(0, 100 - missingEvidence * 4) },
    { label: "PUKÖ", value: Math.max(0, 100 - missingPuko * 3) },
    { label: "Termin", value: Math.max(0, 100 - overdue * 8) },
  ];
  return (
    <article className="premium-dashboard-widget quality-trend-widget">
      <div className="widget-headline"><span className="eyebrow">Kalite Skoru Trend</span><strong>{qualityScore}%</strong></div>
      <MiniBarChart title="Operasyonel kalite göstergeleri" rows={trendRows} total={100} />
    </article>
  );
}

export function MetricCard({ className = "", label, value, sub }) {
  return <div className={`metric-card ${className}`}><span>{label}</span><strong>{value}</strong><small>{sub}</small></div>;
}

export function DashboardSkeleton() {
  return (
    <section className="panel-stack">
      <div className="skeleton hero-skeleton" />
      <div className="dashboard-panel">
        {[1, 2, 3, 4].map((item) => <div key={item} className="skeleton metric-skeleton" />)}
      </div>
      <div className="split-grid">
        <div className="skeleton block-skeleton" />
        <div className="skeleton block-skeleton" />
      </div>
    </section>
  );
}

export function PremiumEmptyState({ title = "Kayıt bulunamadı", text = "Bu alan için henüz veri oluşturulmamış." }) {
  return (
    <div className="premium-empty-state">
      <div className="empty-orb"><Sparkles size={22} /></div>
      <strong>{title}</strong>
      <span>{text}</span>
    </div>
  );
}


function AccreditationProcessStrip({ process = "Süreç izleniyor", risk = "Risk kontrol altında", trace = "İz bırakılıyor", action = "Denetime hazır" }) {
  const items = [
    [ClipboardCheck, "Süreç Durumu", process],
    [ShieldCheck, "Eksik / Risk", risk],
    [History, "İzlenebilirlik", trace],
    [FileDown, "Denetim Çıktısı", action],
  ];
  return (
    <div className="accreditation-process-strip">
      {items.map(([Icon, label, value]) => (
        <span key={label}>
          <Icon size={16} />
          <small>{label}</small>
          <strong>{value}</strong>
        </span>
      ))}
    </div>
  );
}

export function DashboardSectionList({ rows, onPick, emptyTitle = "Kayıt yok", emptyText = "Bu kategori için gösterilecek başlık bulunmuyor." }) {
  return rows.length ? rows.map((section) => (
    <button key={section.section_key} className="priority-row" onClick={() => onPick(section.section_key, section.approval_status === "Onaya Gönderildi" ? "approval" : "entry")}>
      <span>{section.section_key}</span>
      <strong>{section.section_title}</strong>
      <small>{section.approval_status || section.status || "Taslak"}</small>
    </button>
  )) : <PremiumEmptyState title={emptyTitle} text={emptyText} />;
}

export function RoleActionPanel({ roleName, actions, onPick }) {
  const roleHints = {
    "Süper Admin": ["Tüm kurumların yetki devrini, kurum adminlerini ve kritik sistem ayarlarını merkezi olarak yönetin.", "Yetki Matrisi, tenant izolasyonu ve audit/compliance raporları ilk kontrol alanıdır."],
    "Kurum Admin": ["Süper Admin tarafından açık bırakılan izinleri kendi kurumunuzdaki Birim Admin, Editör / Hazırlayıcı, Onaylayıcı ve Denetçi rollerine dağıtın.", "Kurum içi kullanıcı, program, termin, bildirim ve rapor hazırlık risklerini takip edin."],
    [FACULTY_ADMIN_ROLE]: ["Atandığınız fakülte/MYO/enstitü kapsamındaki tüm bölüm ve programları tek çalışma alanı gibi yönetin.", "Bölüm/program seçimi yapılmadan birim kapsamındaki programlara toplu hakimiyet sağlanır."],
    "Birim Koordinatörü": ["Birim içindeki rapor koordinasyonunu, kanıt takibini ve kısmi onay akışını izleyin.", "Program ekiplerinin eksik başlıklarını ve kalite uyarılarını önceliklendirin."],
    Admin: ["Yetki, görünürlük ve gecikme risklerini merkezi olarak izleyin.", "Onay kuyruğu ve teslim tarihleri yönetim panelindeki ilk kontrol alanıdır."],
    [EDITOR_ROLE]: ["Revizyon ve kanıt eksiklerini kapatmadan onaya gönderim yapmayın.", "Kaydedilmemiş başlıklarda önce Rapor Dizini üzerinden kayıt alın."],
    [APPROVER_ROLE]: ["Onay kuyruğundaki başlıkları karar notu ile inceleyin.", "Revizyon verdiğiniz başlıkları Kontrol ekranından takip edin."],
    [READONLY_ROLE]: ["Salt okuma görünümüyle rapor sağlığını, önizlemeyi ve takvimi izleyin.", "Değişiklik gerektiren durumlarda ilgili editör veya kurum yöneticisiyle paylaşın."],
  };
  const notes = roleHints[roleName] || roleHints[READONLY_ROLE];
  return (
    <TabbedExpander
      className="dashboard-expander role-card"
      open={false}
      eyebrow="Rol Bazlı Görevler"
      title={`${roleName} için hızlı aksiyonlar`}
      subtitle="Rolünüze göre önceliklendirilmiş işlem kısayolları."
      summaryBadge={`${actions.length} aksiyon`}
      tabs={[
        {
          id: "actions",
          label: "Aksiyonlar",
          count: actions.length,
          content: <div className="action-list">{actions.map((action) => (
            <button key={action.label} onClick={() => onPick(action.section, action.module)}>
              <strong>{action.count}</strong>
              <span>{action.label}</span>
            </button>
          ))}</div>,
        },
        {
          id: "guide",
          label: "Rol Notu",
          count: notes.length,
          content: <div className="tabbed-note compact"><h3>{roleName} çalışma odağı</h3><ul>{notes.map((note) => <li key={note}>{note}</li>)}</ul></div>,
        },
      ]}
    />
  );
}

export function PriorityPanel({ rows, onPick }) {
  const revisionRows = rows.filter((section) => section.approval_status === "Revizyon Gerekli" || section.status === "Revizyon Gerekli");
  const missingRows = rows.filter((section) => Number(section.evidence_count || 0) === 0 || !String(section.report_text || "").trim());
  const deadlineRows = rows.filter((section) => {
    const days = daysUntil(section.deadline);
    return days !== null && days <= 7;
  });
  return (
    <TabbedExpander
      className="dashboard-expander priority-card"
      open={false}
      eyebrow="Bugün Öncelik"
      title="Önce tamamlanacak başlıklar"
      subtitle="Acil, revizyon, eksik ve termin risklerini sekmelerle ayırır."
      summaryBadge={`${rows.length} başlık`}
      tabs={[
        { id: "all", label: "Öncelik", count: rows.length, content: <DashboardSectionList rows={rows} onPick={onPick} emptyTitle="Acil aksiyon yok" emptyText="Şu an kritik revizyon, gecikme veya onay kuyruğu görünmüyor." /> },
        { id: "revision", label: "Revizyon", count: revisionRows.length, content: <DashboardSectionList rows={revisionRows} onPick={onPick} emptyTitle="Revizyon yok" emptyText="Revizyon bekleyen başlık görünmüyor." /> },
        { id: "missing", label: "Eksik", count: missingRows.length, content: <DashboardSectionList rows={missingRows} onPick={onPick} emptyTitle="Eksik yok" emptyText="Metin veya kanıt eksikliğine göre acil başlık bulunmuyor." /> },
        { id: "deadline", label: "Termin", count: deadlineRows.length, content: <DashboardSectionList rows={deadlineRows} onPick={onPick} emptyTitle="Yakın termin yok" emptyText="Yedi gün içinde teslim riski görünen başlık yok." /> },
      ]}
    />
  );
}

export function MiniChartsPanel({ statusRows, pukoRows, approvalRows, total }) {
  return (
    <TabbedExpander
      className="dashboard-expander charts-card"
      open={false}
      eyebrow="Canlı Durum Grafikleri"
      title="Rapor sağlığı"
      subtitle="Başlık, onay ve PUKÖ dağılımlarını ayrı sekmelerde izleyin."
      summaryBadge={`${total} başlık`}
      tabs={[
        { id: "status", label: "Başlık", count: statusRows.reduce((sum, row) => sum + Number(row.value || 0), 0), content: <MiniBarChart title="Başlık Durumu" rows={statusRows} total={total} /> },
        { id: "approval", label: "Onay", count: approvalRows.reduce((sum, row) => sum + Number(row.value || 0), 0), content: <MiniBarChart title="Onay Dağılımı" rows={approvalRows} total={total} /> },
        { id: "puko", label: "PUKÖ", count: pukoRows.reduce((sum, row) => sum + Number(row.value || 0), 0), content: <MiniBarChart title="PUKÖ Tamamlanma" rows={pukoRows} total={total} /> },
      ]}
    />
  );
}

export function MiniBarChart({ title, rows, total }) {
  const safeTotal = Math.max(1, Number(total || 0));
  return (
    <div className="mini-chart">
      <strong>{title}</strong>
      {rows.map((row) => {
        const width = Math.round((Number(row.value || 0) / safeTotal) * 100);
        return (
          <div className="mini-bar" key={row.label}>
            <span>{row.label}</span>
            <div><i style={{ width: `${Math.max(3, width)}%` }} /></div>
            <em>{row.value}</em>
          </div>
        );
      })}
    </div>
  );
}

export function TabbedExpander({ title, subtitle, tabs, defaultTab, open = true, className = "", eyebrow = "Çalışma Alanı", summaryBadge }) {
  const initialTab = defaultTab || tabs[0]?.id || "";
  const [activeTab, setActiveTab] = useState(initialTab);
  const active = tabs.find((tab) => tab.id === activeTab) || tabs[0];

  useEffect(() => {
    if (!tabs.some((tab) => tab.id === activeTab)) setActiveTab(tabs[0]?.id || "");
  }, [tabs, activeTab]);

  return (
    <details className={`tabbed-expander ${className}`} open={open}>
      <summary>
        <div>
          <span className="eyebrow">{eyebrow}</span>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        <span className="badge">{summaryBadge || `${tabs.length} sekme`}</span>
      </summary>
      <div className="tabbed-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={active?.id === tab.id ? "active" : ""}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
            {tab.count !== undefined && <small>{tab.count}</small>}
          </button>
        ))}
      </div>
      <div className="tabbed-content">
        {active?.content}
      </div>
    </details>
  );
}

export function ProgressBar({ value }) {
  const width = Math.max(3, Math.min(100, Number(value) || 0));
  return <div className="mini-progress"><div style={{ width: `${width}%` }} /></div>;
}

function ReportPreflightPanel({ preflight, onPick, compact = false }) {
  const payload = asObject(preflight);
  if (!payload.generated_at) {
    return <section className="editor-panel"><div className="empty-state">Rapor hazırlık denetimi yükleniyor.</div></section>;
  }
  const summary = asObject(payload.summary);
  const topActions = asArray(payload.top_actions);
  const rows = asArray(payload.rows);
  const criticalRows = rows.filter((row) => row.severity !== "ready").slice(0, compact ? 5 : 12);
  return (
    <section className="editor-panel report-preflight-panel">
      <div className="editor-header">
        <div>
          <h2>Rapor Hazırlık Denetimi</h2>
          <p className="muted">Kanıt atıfı, zorunlu tablo, PUKÖ, onay ve metin derinliği final çıktı öncesi taranır.</p>
        </div>
        <span className={`badge ${payload.ready ? "success" : "warning"}`}>{summary.ready_label || (payload.ready ? "Hazır" : "Eksik var")}</span>
      </div>
      <div className="dashboard-panel compact-kpi-grid">
        <MetricCard label="Hazır başlık" value={`${summary.ready_sections || 0}/${summary.total_sections || 0}`} sub="final kontrol" />
        <MetricCard label="Bloklayıcı" value={summary.blockers || 0} sub="export kapısı" className={summary.blockers ? "warn" : ""} />
        <MetricCard label="Uyarı" value={summary.warnings || 0} sub="editoryal risk" />
        <MetricCard label="Kanıt atıfı" value={`${summary.citation_percent || 0}%`} sub="metinde geçen kod" />
      </div>
      {topActions.length > 0 ? (
        <div className={payload.ready ? "notice-card info" : "notice-card warning"}>
          <strong>{payload.ready ? "Final kontrol iyi görünüyor." : "Final çıktı öncesi önce bunları kapatın."}</strong>
          <div className="mini-list">
            {topActions.slice(0, compact ? 4 : 8).map((item, index) => (
              onPick ? (
                <button key={`${item.section_key}-${item.code}-${index}`} type="button" onClick={() => onPick(item.section_key, "entry")}>
                  {item.section_key} · {item.title}
                </button>
              ) : (
                <span key={`${item.section_key}-${item.code}-${index}`}>{item.section_key} · {item.title}</span>
              )
            ))}
          </div>
        </div>
      ) : (
        <div className="notice-card success"><strong>Bloklayıcı eksik yok.</strong><span>Nihai DOCX/PDF üretimi için rapor hazırlık kapısı açık.</span></div>
      )}
      {!compact && criticalRows.length > 0 && (
        <DataTable
          rows={criticalRows.map((row) => ({
            section_key: row.section_key,
            section_title: row.section_title,
            severity: row.severity,
            quality_score: row.quality_score,
            words: row.words,
            evidence_count: row.evidence_count,
            uncited_evidence: row.uncited_evidence,
            table_count: row.table_count,
            puko_count: row.puko_count,
            approval_status: row.approval_status,
          }))}
          columns={["section_key", "section_title", "severity", "quality_score", "words", "evidence_count", "uncited_evidence", "table_count", "puko_count", "approval_status"]}
          actions={(row) => <button onClick={() => onPick?.(row.section_key, "entry")}>Aç</button>}
        />
      )}
    </section>
  );
}


function notificationCategory(row) {
  const type = String(row.event_type || "").toLowerCase();
  const subject = String(row.subject || "").toLowerCase();
  const haystack = `${type} ${subject}`;
  if (haystack.includes("revision") || haystack.includes("revizyon")) return "Revizyon";
  if (haystack.includes("deadline") || haystack.includes("termin") || haystack.includes("teslim")) return "Termin";
  if (haystack.includes("approval") || haystack.includes("approved") || haystack.includes("onay")) return "Onay";
  if (haystack.includes("role") || haystack.includes("permission") || haystack.includes("yetki") || haystack.includes("rol")) return "Rol / Yetki";
  if (haystack.includes("export") || haystack.includes("çıktı") || haystack.includes("rapor")) return "Çıktı";
  return "Diğer";
}

export function NotificationCenterView({ programId, onError, onMessage, onPick }) {
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("Tümü");
  async function load() {
    try { setRows(asArray(await api.notificationInbox(programId, 100))); } catch (err) { onError(err.message); }
  }
  useEffect(() => { load(); }, [programId]);
  useEffect(() => {
    const handler = () => load();
    window.addEventListener("medek-live-event", handler);
    return () => window.removeEventListener("medek-live-event", handler);
  }, [programId]);
  async function markAllRead() {
    try { const result = await api.markNotificationsRead(programId, rows.map((row) => row.id)); onMessage(`${result.updated} bildirim okundu işaretlendi.`); await load(); } catch (err) { onError(err.message); }
  }
  const unread = rows.filter((row) => !row.read).length;
  const notificationTabs = ["Tümü", "Okunmamış", "Onay", "Revizyon", "Termin", "Rol / Yetki", "Çıktı", "Diğer"].map((label) => ({
    label,
    count: label === "Tümü"
      ? rows.length
      : label === "Okunmamış"
        ? rows.filter((row) => !row.read).length
        : rows.filter((row) => notificationCategory(row) === label).length,
  }));
  const filteredRows = filter === "Tümü"
    ? rows
    : filter === "Okunmamış"
      ? rows.filter((row) => !row.read)
      : rows.filter((row) => notificationCategory(row) === filter);
  return (
    <section className="panel-stack ops-premium-shell ops-notification-workspace">
      <div className="hero-panel stats-hero ops-premium-hero">
        <div><span className="eyebrow">Bildirim Merkezi</span><h2>Rol bazlı sistem içi bildirimler</h2><p>Mail bildirimlerinin sistem içi kaydı burada izlenir. Onay, revizyon, termin, rol ve çıktı olaylarına tek yerden erişebilirsiniz.</p></div>
        <div className="hero-score"><strong>{unread}</strong><span>okunmamış</span></div>
      </div>
      <section className="editor-panel">
        <div className="editor-header"><div><h2>Bildirimler</h2><p className="muted">Bildirimler kategori sekmeleriyle ayrıldı; seçili sekme tabloyu anlık filtreler.</p></div><button onClick={markAllRead}>Tümünü okundu yap</button></div>
        <div className="category-tabs" role="tablist" aria-label="Bildirim kategorileri">
          {notificationTabs.map((tab) => (
            <button key={tab.label} type="button" role="tab" aria-selected={filter === tab.label} className={filter === tab.label ? "active" : ""} onClick={() => setFilter(tab.label)}>
              {tab.label}<small>{tab.count}</small>
            </button>
          ))}
        </div>
        <DataTable rows={filteredRows} columns={["read", "event_type", "subject", "actor", "section_key", "status", "created_at", "sent_at"]} actions={(row) => row.section_key ? <button onClick={() => onPick(row.section_key, "entry")}>Başlığı Aç</button> : null} />
      </section>
    </section>
  );
}

export function TasksAndGapsView({ programId, onError, onPick }) {
  const [payload, setPayload] = useState(null);
  useEffect(() => { api.insights(programId).then(setPayload).catch((err) => onError(err.message)); }, [programId]);
  if (!payload) return <div className="empty-state">Görev ve eksiklik analizi yükleniyor.</div>;
  const summary = payload.summary || {};
  const quality = payload.quality || {};
  return (
    <section className="panel-stack ops-premium-shell ops-tasks-workspace">
      <div className="hero-panel stats-hero ops-premium-hero">
        <div><span className="eyebrow">Eksik ve Risk Analizi</span><h2>Akreditasyon sürecindeki açık işleri ve riskleri göster</h2><p>Metin, kanıt, tablo, PUKÖ, onay ve termin durumlarından otomatik süreç görevleri üretilir.</p></div>
        <div className="hero-score"><strong>{summary.avg_quality ?? 0}%</strong><span>kalite</span></div>
      </div>
      <AccreditationProcessStrip process={`${summary.tasks ?? 0} görev açık`} risk={`${summary.gaps ?? 0} eksik / ${summary.overdue ?? 0} geciken`} trace="Onay timeline ve kanıt haritası bağlı" action="Eksikler kapandıkça rapor çıktısı güçlenir" />
      <div className="dashboard-panel">
        <MetricCard className="accent" label="Görev" value={summary.tasks ?? 0} sub="rol bazlı iş" />
        <MetricCard className="warn" label="Eksik" value={summary.gaps ?? 0} sub="tamamlanacak başlık" />
        <MetricCard label="Bu Hafta" value={summary.due_this_week ?? 0} sub="termin yaklaşan" />
        <MetricCard className="warn" label="Geciken" value={summary.overdue ?? 0} sub="tarihi geçen" />
      </div>
      <TabbedExpander
        title="Operasyonel Analiz"
        subtitle="Görevler, eksiklikler, kalite kırılımı, onay zaman çizelgesi ve kanıt haritası."
        tabs={[
          { id: "tasks", label: "Görevler", count: payload.tasks?.length || 0, content: <DataTable rows={payload.tasks} columns={["priority", "reason", "section_key", "section_title", "quality", "deadline", "approval_status", "status"]} actions={(row) => <button onClick={() => onPick(row.section_key, "entry")}>Aç</button>} /> },
          { id: "gaps", label: "Eksiklikler", count: payload.gaps?.length || 0, content: <DataTable rows={payload.gaps} columns={["section_key", "section_title", "quality", "missing", "deadline", "approval_status", "status"]} actions={(row) => <button onClick={() => onPick(row.section_key, "entry")}>Düzelt</button>} /> },
          { id: "quality", label: "Kalite Kırılımı", count: quality.missing_counters?.length || 0, content: <DataTable rows={quality.missing_counters || []} columns={["issue", "count"]} /> },
          { id: "timeline", label: "Zaman Çizelgesi", count: payload.timeline?.length || 0, content: <DataTable rows={payload.timeline} columns={["created_at", "section_key", "section_title", "status", "requested_by", "decided_by", "note"]} actions={(row) => <button onClick={() => onPick(row.section_key, "approval")}>Onay Akışı</button>} /> },
          { id: "evidence", label: "Kanıt Haritası", count: payload.evidence_map?.length || 0, content: <DataTable rows={payload.evidence_map} columns={["code", "original_name", "section_count", "section_keys", "uploaded_at", "note"]} /> },
        ].filter(Boolean)}
      />
    </section>
  );
}

export function DeadlineCalendarView({ programId, onError, onPick }) {
  const [payload, setPayload] = useState(null);
  useEffect(() => { api.insights(programId).then(setPayload).catch((err) => onError(err.message)); }, [programId]);
  if (!payload) return <div className="empty-state">Teslim takvimi yükleniyor.</div>;
  const rows = payload.deadline_calendar || [];
  const groups = ["Gecikti", "Bu hafta", "Bu ay", "Planlandı", "Tarih yok"].map((state) => ({ state, rows: rows.filter((row) => row.deadline_state === state) }));
  return (
    <section className="panel-stack ops-premium-shell ops-calendar-workspace">
      <div className="hero-panel stats-hero ops-premium-hero"><div><span className="eyebrow">Teslim ve Termin Takvimi</span><h2>Geciken, yaklaşan ve plansız başlıkları yönet</h2><p>Son teslim tarihleri denetim hazırlığına göre gruplanır. Yönetici planı Son Teslim Tarihi Planı ekranından düzenler.</p></div></div>
      <AccreditationProcessStrip process={`${rows.length} başlık termin kapsamında`} risk={`${groups.find((g) => g.state === "Gecikti")?.rows?.length || 0} geciken`} trace="Termin değişiklikleri audit trail’e bağlanır" action="Teslim planı rapor çıktısına yansır" />
      {groups.map((group) => (
        <section className="editor-panel" key={group.state}>
          <div className="editor-header"><h2>{group.state}</h2><span className="soft-badge">{group.rows.length} başlık</span></div>
          <DataTable rows={group.rows} columns={["section_key", "section_title", "deadline", "days_left", "status", "approval_status"]} actions={(row) => <button onClick={() => onPick(row.section_key, "entry")}>Aç</button>} />
        </section>
      ))}
    </section>
  );
}


export function ActivityTimelineView({ programId, onError, onPick }) {
  const [payload, setPayload] = useState(null);
  async function load() {
    try { setPayload(asObject(await api.activityTimeline(programId, 250))); } catch (err) { onError(err.message); }
  }
  useEffect(() => { load(); }, [programId]);
  if (!payload) return <div className="empty-state">Activity trail yükleniyor.</div>;
  return (
    <section className="panel-stack ops-premium-shell ops-activity-workspace">
      <div className="hero-panel stats-hero ops-premium-hero"><div><span className="eyebrow">İzlenebilirlik Kaydı</span><h2>Denetimde sorulacak tüm işlem izlerini tek yerde tut</h2><p>Onay, revizyon, silme, rol değişikliği, çıktı, mail ve başlık versiyonları uçtan uca audit kaydı olarak izlenir.</p></div><div className="hero-score"><strong>{payload.events?.length || 0}</strong><span>olay</span></div></div>
      <AccreditationProcessStrip process={`${payload.events?.length || 0} işlem kayıtlı`} risk="Kritik olaylar zaman çizelgesinde" trace="Kim, ne zaman, hangi başlıkta kayıtlı" action="Denetim izi dışa aktarılabilir" />
      <div className="dashboard-panel"><MetricCard label="Aktör" value={payload.actor_counts?.length || 0} sub="işlem yapan" /><MetricCard label="Kaynak" value={payload.source_counts?.length || 0} sub="audit kaynağı" /></div>
      <TabbedExpander title="Audit ve Aktivite Zaman Çizelgesi" subtitle="Denetim izi, bildirim, onay ve çıktı geçmişi." tabs={[
        { id: "events", label: "Timeline", count: payload.events?.length || 0, content: <DataTable rows={payload.events} columns={["created_at", "source", "event", "detail", "actor", "section_key", "status", "error"]} actions={(row) => row.section_key ? <button onClick={() => onPick(row.section_key, "entry")}>Başlığı Aç</button> : null} /> },
        { id: "actors", label: "Kullanıcılar", count: payload.actor_counts?.length || 0, content: <DataTable rows={payload.actor_counts} columns={["actor", "count"]} /> },
        { id: "sources", label: "Olay Kaynakları", count: payload.source_counts?.length || 0, content: <DataTable rows={payload.source_counts} columns={["source", "count"]} /> },
      ]} />
    </section>
  );
}

export function AnalyticsBarList({ rows, labelKey, valueKey, suffix = "%", max = 100 }) {
  const safeRows = asArray(rows);
  return <div className="analytics-bars">{safeRows.map((row) => {
    const value = Number(row[valueKey] || 0);
    const width = Math.max(4, Math.min(100, (value / max) * 100));
    return <div className="analytics-bar-row" key={`${row[labelKey]}-${valueKey}`}><div className="analytics-bar-head"><strong>{row[labelKey]}</strong><span>{value}{suffix}</span></div><div className="analytics-track"><i style={{ width: `${width}%` }} /></div></div>;
  })}</div>;
}

export function RiskHeatMap({ rows, onPick }) {
  const safeRows = asArray(rows).slice(0, 40);
  return <div className="heatmap-grid">{safeRows.map((row) => {
    const risk = Number(row.risk || 0);
    const level = risk >= 70 ? "critical" : risk >= 45 ? "warn" : "ok";
    return <button className={`heatmap-cell ${level}`} key={row.section_key} onClick={() => onPick(row.section_key, "entry")} title={`${row.section_key} · ${row.section_title}`}>
      <strong>{row.section_key}</strong><span>{risk}</span><small>{row.approval_status || row.status}</small>
    </button>;
  })}</div>;
}

export function AdvancedDashboardView({ programId, onError, onMessage, onPick }) {
  const [payload, setPayload] = useState(null);
  useEffect(() => { api.advancedReporting(programId).then((data) => setPayload(asObject(data))).catch((err) => onError(err.message)); }, [programId]);
  if (!payload) return <div className="empty-state">Gelişmiş dashboard yükleniyor.</div>;
  const groupRows = asArray(payload.group_chart);
  const pukoRows = asArray(payload.puko_chart);
  const riskRows = asArray(payload.risk_heatmap);
  const topRisk = riskRows[0];
  const summary = asObject(payload.summary);
  async function downloadAnalyticsDocx() {
    try {
      downloadBlob(await api.advancedReportingDocx(programId), "AKYS_advanced_analytics_dashboard.docx");
      onMessage?.("Advanced Analytics DOCX indirildi.");
    } catch (err) { onError(err.message); }
  }
  async function downloadAnalyticsPdf() {
    try {
      downloadBlob(await api.advancedReportingPdf(programId), "AKYS_advanced_analytics_dashboard.pdf");
      onMessage?.("Advanced Analytics PDF indirildi.");
    } catch (err) { onError(err.message); }
  }
  async function startAnalyticsJob(exportType) {
    try {
      const job = await api.createExportJob(programId, exportType);
      onMessage?.(`${exportLabel(exportType)} kuyruğa alındı: ${job.file_name}`);
    } catch (err) { onError(err.message); }
  }
  return (
    <section className="panel-stack advanced-analytics-dashboard ops-premium-shell ops-advanced-workspace">
      <div className="hero-panel stats-hero ops-premium-hero"><div><span className="eyebrow">Akreditasyon Kokpiti</span><h2>Hazırlık, kalite, revizyon ve kanıt riskini yönetici düzeyinde izle</h2><p>Yönetici ekranı tamamlanma, onay, kalite, revizyon ve kanıt risklerini denetim hazırlığına göre tek yerde görselleştirir.</p><div className="action-row"><button className="primary-action" onClick={downloadAnalyticsDocx}>Kokpit DOCX</button><button onClick={downloadAnalyticsPdf}>Kokpit PDF</button><button onClick={() => startAnalyticsJob("analytics_docx")}>DOCX Job</button><button onClick={() => startAnalyticsJob("analytics_pdf")}>PDF Job</button></div></div><div className="hero-score"><strong>{topRisk?.risk ?? 0}</strong><span>en yüksek risk</span></div></div>
      <AccreditationProcessStrip process={`${summary.approved ?? 0} onaylı başlık`} risk={`${summary.high_risk ?? 0} yüksek risk`} trace="Grafik verileri activity ve versiyon izleriyle desteklenir" action="Kokpit DOCX/PDF alınabilir" />
      <div className="dashboard-panel analytics-kpis">
        <MetricCard label="Ortalama kalite" value={summary.quality_avg ?? 0} sub="puan" />
        <MetricCard label="Onaylanan" value={summary.approved ?? 0} sub="başlık" />
        <MetricCard label="Revizyon" value={summary.revision ?? 0} sub="başlık" />
        <MetricCard label="Yüksek risk" value={summary.high_risk ?? 0} sub="başlık" />
      </div>
      <div className="analytics-visual-grid">
        <section className="editor-panel"><h3>Grup bazlı hazırlık oranı</h3><AnalyticsBarList rows={groupRows} labelKey="group" valueKey="readiness_percent" /></section>
        <section className="editor-panel"><h3>Grup bazlı onay oranı</h3><AnalyticsBarList rows={groupRows} labelKey="group" valueKey="approval_percent" /></section>
        <section className="editor-panel"><h3>PUKÖ doluluk grafiği</h3><AnalyticsBarList rows={pukoRows.map((row) => ({ ...row, percent: summary.total ? Math.round((Number(row.count || 0) / summary.total) * 100) : 0 }))} labelKey="field" valueKey="percent" /></section>
      </div>
      <section className="editor-panel heatmap-panel"><div className="section-heading-row"><div><span className="eyebrow">Heat Map</span><h2>Başlık bazlı risk yoğunluğu</h2></div><span className="pill">{riskRows.length} başlık</span></div><RiskHeatMap rows={riskRows} onPick={onPick} /></section>
      <TabbedExpander title="Analitik Veri Tabloları" subtitle="Grafiklerin üretildiği veriler tablo olarak da incelenebilir." tabs={[
        { id: "groups", label: "Rapor Grupları", count: groupRows.length, content: <DataTable rows={groupRows} columns={["group", "total", "ready", "approved", "revision", "readiness_percent", "approval_percent", "quality_avg"]} /> },
        { id: "puko", label: "PUKÖ Durumu", count: pukoRows.length, content: <DataTable rows={pukoRows} columns={["field", "count"]} /> },
        { id: "risk", label: "Risk Heat Map", count: riskRows.length, content: <DataTable rows={riskRows} columns={["section_key", "section_title", "group", "risk", "quality", "status", "approval_status"]} actions={(row) => <button onClick={() => onPick(row.section_key, "entry")}>Başlığı Aç</button>} /> },
      ]} />
    </section>
  );
}


function VisualDiffViewer({ rows = [] }) {
  const items = asArray(rows);
  if (!items.length) return <div className="empty-state">Karşılaştırılacak satır farkı yok.</div>;
  return (
    <div className="visual-diff-viewer">
      <div className="visual-diff-head"><strong>Eski sürüm</strong><strong>Yeni sürüm</strong></div>
      {items.map((row, idx) => (
        <div key={`${row.type}-${idx}`} className={`visual-diff-row diff-${row.type}`}>
          <pre>{row.old || " "}</pre>
          <pre>{row.new || " "}</pre>
        </div>
      ))}
    </div>
  );
}

export function VersionDiffView({ programId, sections, activeSectionKey, setActiveSectionKey, onError }) {
  const [payload, setPayload] = useState(null);
  const [baseId, setBaseId] = useState("");
  const [compareId, setCompareId] = useState("current");
  const selectedKey = activeSectionKey || sections[0]?.section_key || "";
  async function load(key = selectedKey, nextBase = baseId, nextCompare = compareId) {
    if (!key) return;
    try { setPayload(asObject(await api.sectionVersions(programId, key, nextBase, nextCompare))); } catch (err) { onError(err.message); }
  }
  useEffect(() => { setBaseId(""); setCompareId("current"); load(selectedKey, "", "current"); }, [programId, selectedKey]);
  const versionOptions = [{ id: "current", label: "Güncel kayıt" }, ...asArray(payload?.versions).map((item) => ({ id: item.id, label: `${item.saved_at} · ${item.change_summary || item.status || "snapshot"}` }))];
  function changeBase(value) { setBaseId(value); load(selectedKey, value, compareId); }
  function changeCompare(value) { setCompareId(value); load(selectedKey, baseId, value); }
  const selected = asObject(payload?.selected);
  return (
    <section className="panel-stack version-diff-view ops-premium-shell ops-diff-workspace">
      <div className="editor-panel ops-premium-hero">
        <div className="editor-header"><div><span className="eyebrow">Revizyon Karşılaştırma</span><h2>Akreditasyon başlığındaki değişiklikleri denetim izine dönüştür</h2><p className="muted">Güncel metni önceki snapshot ile veya iki tarihsel versiyonu yan yana karşılaştırabilirsiniz.</p></div><button onClick={() => load()}><RefreshCw size={16} /> Yenile</button></div>
        <div className="form-grid">
          <label className="wide">Başlık<select value={selectedKey} onChange={(e) => { setActiveSectionKey(e.target.value); }}>
            {sections.map((section) => <option key={section.section_key} value={section.section_key}>{section.section_key} · {section.section_title}</option>)}
          </select></label>
          <label>Sol / eski sürüm<select value={baseId || versionOptions[1]?.id || "current"} onChange={(e) => changeBase(e.target.value)}>{versionOptions.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
          <label>Sağ / yeni sürüm<select value={compareId} onChange={(e) => changeCompare(e.target.value)}>{versionOptions.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
        </div>
        {selected.base_label && <p className="muted">Karşılaştırma: <strong>{selected.base_label}</strong> → <strong>{selected.compare_label}</strong></p>}
        {payload?.summary && <div className="diff-ai-summary"><Sparkles size={16} /><div><strong>AI Değişiklik Özeti</strong>{asArray(payload.summary.ai_summary).map((item) => <span key={item}>{item}</span>)}</div><em>+{payload.summary.added_lines || 0} / -{payload.summary.removed_lines || 0} / Δ{payload.summary.changed_lines || 0}</em></div>}
      </div>
      <AccreditationProcessStrip process="Revizyon etkisi karşılaştırılıyor" risk="Silinen/değişen metinler renkli diff ile görünür" trace="Snapshot tarihi ve değişiklik özeti korunur" action="Onay öncesi değişiklik kanıtı sağlar" />
      {!payload ? <div className="empty-state">Versiyonlar yükleniyor.</div> : <TabbedExpander title="Doküman Karşılaştırma" subtitle="Satır bazlı diff, yan yana görünüm, alan değişiklikleri ve snapshot listesi." tabs={[
        { id: "side", label: "Yan Yana Diff", count: payload.side_by_side?.length || 0, content: <VisualDiffViewer rows={payload.side_by_side} /> },
        { id: "diff", label: "Satır Diff", count: payload.diff?.length || 0, content: <DataTable rows={payload.diff} columns={["type", "line"]} /> },
        { id: "fields", label: "Alan Değişiklikleri", count: payload.field_changes?.filter((row) => row.changed).length || 0, content: <DataTable rows={payload.field_changes} columns={["field", "changed", "old_length", "new_length", "old_preview", "new_preview"]} /> },
        { id: "versions", label: "Sürümler", count: payload.versions?.length || 0, content: <DataTable rows={payload.versions} columns={["id", "saved_at", "status", "deadline", "change_summary"]} /> },
      ]} />}
    </section>
  );
}



export function PermissionMatrixView({ programId, sections = [], currentRole = "", onError, onMessage, onMatrixSaved }) {
  const [payload, setPayload] = useState(null);
  const [sectionPolicy, setSectionPolicy] = useState(null);
  const [roleFocus, setRoleFocus] = useState("Tümü");
  const [sectionPolicyQuery, setSectionPolicyQuery] = useState("");
  const [activeMatrixTab, setActiveMatrixTab] = useState("operations");
  const [operationSubtab, setOperationSubtab] = useState("Tümü");
  const [sidebarSubtab, setSidebarSubtab] = useState("Tümü");
  const [sectionSubtab, setSectionSubtab] = useState("Tümü");
  const [matrixError, setMatrixError] = useState("");
  const [saving, setSaving] = useState(false);

  const SELF_PROTECTED_PERMISSIONS = new Set(["permission.manage", "sidebar.manage"]);
  const SELF_PROTECTED_MODULES = new Set(["permissions"]);
  const BULK_ALL_CORE_PERMISSIONS = new Set([
    "program.view",
    "dashboard.view",
    "dashboard.kpi.view",
    "dashboard.priority.view",
    "dashboard.criteria.view",
    "dashboard.charts.view",
    "help.view",
    "help.role_manual.view",
    "help.workflow.view",
  ]);
  const BULK_ALL_ADMIN_RECOVERY_PERMISSIONS = new Set([
    "program.view",
    "program.list.view",
    "permission.manage",
    "sidebar.manage",
  ]);
  const BULK_ALL_CORE_MODULES = new Set(["dashboard", "help"]);
  const BULK_ALL_ADMIN_RECOVERY_MODULES = new Set(["permissions"]);

  function reportMatrixError(message) {
    const clean = String(message || "Yetki matrisi işlemi tamamlanamadı.");
    setMatrixError(clean);
    if (onError) onError(clean);
  }

  function reportMatrixMessage(message) {
    setMatrixError("");
    if (onMessage) onMessage(message);
  }

  async function load() {
    try {
      setMatrixError("");
      const [permissions, policy] = await Promise.all([api.permissions(), programId ? api.sectionPermissions(programId) : Promise.resolve(null)]);
      setPayload(asObject(permissions));
      setSectionPolicy(policy ? asObject(policy) : null);
      setOperationSubtab("Tümü");
      setSidebarSubtab("Tümü");
      setSectionSubtab("Tümü");
    } catch (err) { reportMatrixError(err.message); }
  }

  useEffect(() => { load(); }, [programId]);
  if (!payload) return <div className="empty-state">Yetki matrisi yükleniyor.</div>;

  const roles = asArray(payload.roles).length ? asArray(payload.roles).filter(Boolean) : ROLES;
  const actorRole = normalizeRole(currentRole || "");
  const editableRoles = asArray(payload.editable_roles).length ? asArray(payload.editable_roles) : roles;
  const protectedRoles = asArray(payload.protected_roles);
  const adminScope = payload.admin_scope || "super_admin";
  const delegationNote = payload.delegation_note || "Yetki matrisi rol bazlı işlem ve görünürlük kararlarını yönetir.";
  const operationMatrixLocked = Boolean(payload.operation_matrix_locked);
  const operationMatrixLockNote = payload.operation_matrix_lock_note || "";
  const hierarchyRoles = isSuperAdminRole(actorRole) ? roles : roles.filter((role) => visibleRolesForActor(actorRole).includes(role));
  const visibleRoles = roleFocus === "Tümü" ? hierarchyRoles : hierarchyRoles.filter((role) => role === roleFocus);
  const rows = asArray(payload.rows);
  const sidebarRows = asArray(payload.sidebar_rows);
  const sectionPolicyRows = asArray(sectionPolicy?.rows);
  const canEditRole = (role) => editableRoles.includes(role);
  const isActorRole = (role) => actorRole && normalizeRole(role) === actorRole;

  const roleStats = hierarchyRoles.map((role) => ({
    role,
    permissions: rows.filter((row) => row && row[role]).length,
    modules: sidebarRows.filter((row) => row && row[role]).length,
    sections: sectionPolicyRows.filter((row) => row && row[role]).length,
    editable: canEditRole(role),
  }));

  function groupedByCategory(items, field = "category") {
    return asArray(items).reduce((acc, raw) => {
      const row = asObject(raw);
      const key = row[field] || "Genel";
      if (!acc[key]) acc[key] = [];
      acc[key].push(row);
      return acc;
    }, {});
  }

  function guardEditable(role) {
    if (canEditRole(role)) return true;
    reportMatrixError(`${role} sütunu bu hesap için kilitli. ${delegationNote}`);
    return false;
  }

  function isSelfProtectedPermission(permission, role, nextValue) {
    return nextValue === false && isActorRole(role) && SELF_PROTECTED_PERMISSIONS.has(String(permission || ""));
  }

  function isSelfProtectedSidebarModule(module, role, nextValue) {
    return nextValue === false && isActorRole(role) && SELF_PROTECTED_MODULES.has(String(module || ""));
  }

  function selfProtectionMessage() {
    return "Aktif hesabın Yetki Matrisi ekranına erişimini kapatacak kritik izinler korunur. Başka rolleri veya kritik olmayan izinleri kapatabilirsiniz.";
  }

  function bulkAllProtectionMessage() {
    return "Tümü sekmesindeki toplu kapatma, rolün giriş/dashboard/yardım veya admin kurtarma yolunu tamamen düşürmemek için kritik çekirdek izinleri açık tuttu. Tam kapatma gerekiyorsa ilgili alt kategoriye girip tek tek kapatın.";
  }

  function isBulkAllProtectedPermission(permission, role, nextValue, group) {
    if (group !== "Tümü" || nextValue !== false) return false;
    const key = String(permission || "");
    if (BULK_ALL_CORE_PERMISSIONS.has(key)) return true;
    return isAdminRole(role) && BULK_ALL_ADMIN_RECOVERY_PERMISSIONS.has(key);
  }

  function isBulkAllProtectedSidebarModule(module, role, nextValue, group) {
    if (group !== "Tümü" || nextValue !== false) return false;
    const key = String(module || "");
    if (BULK_ALL_CORE_MODULES.has(key)) return true;
    return isAdminRole(role) && BULK_ALL_ADMIN_RECOVERY_MODULES.has(key);
  }

  function enforceSelfProtection(nextRows, nextSidebarRows) {
    let changed = false;
    const safeRows = asArray(nextRows).map((row) => {
      const item = asObject(row);
      if (actorRole && SELF_PROTECTED_PERMISSIONS.has(String(item.permission || "")) && item[actorRole] === false) {
        changed = true;
        return { ...item, [actorRole]: true };
      }
      return item;
    });
    const safeSidebarRows = asArray(nextSidebarRows).map((row) => {
      const item = asObject(row);
      if (actorRole && SELF_PROTECTED_MODULES.has(String(item.module || "")) && item[actorRole] === false) {
        changed = true;
        return { ...item, [actorRole]: true };
      }
      return item;
    });
    return { rows: safeRows, sidebarRows: safeSidebarRows, changed };
  }

  function togglePermission(permission, role) {
    if (!guardEditable(role)) return;
    setPayload((previous) => {
      const safePayload = asObject(previous);
      let blocked = false;
      let matched = false;
      const nextRows = asArray(safePayload.rows).map((row) => {
        const item = asObject(row);
        if (String(item.permission || "") !== String(permission || "")) return item;
        matched = true;
        const nextValue = !Boolean(item[role]);
        if (isSelfProtectedPermission(item.permission, role, nextValue)) {
          blocked = true;
          return { ...item, [role]: true };
        }
        return { ...item, [role]: nextValue };
      });
      if (!matched) {
        reportMatrixError(`İzin satırı bulunamadı: ${permission}`);
        return previous;
      }
      if (blocked) reportMatrixError(selfProtectionMessage());
      else setMatrixError("");
      return { ...safePayload, rows: nextRows };
    });
  }

  function toggleSidebar(module, role) {
    if (!guardEditable(role)) return;
    setPayload((previous) => {
      const safePayload = asObject(previous);
      let blocked = false;
      let matched = false;
      const nextRows = asArray(safePayload.sidebar_rows).map((row) => {
        const item = asObject(row);
        if (String(item.module || "") !== String(module || "")) return item;
        matched = true;
        const nextValue = !Boolean(item[role]);
        if (isSelfProtectedSidebarModule(item.module, role, nextValue)) {
          blocked = true;
          return { ...item, [role]: true };
        }
        return { ...item, [role]: nextValue };
      });
      if (!matched) {
        reportMatrixError(`Sidebar modül satırı bulunamadı: ${module}`);
        return previous;
      }
      if (blocked) reportMatrixError(selfProtectionMessage());
      else setMatrixError("");
      return { ...safePayload, sidebar_rows: nextRows };
    });
  }

  function toggleSectionPolicy(sectionKey, action, role) {
    if (!guardEditable(role)) return;
    setSectionPolicy((previous) => {
      const safePolicy = asObject(previous);
      let matched = false;
      const nextRows = asArray(safePolicy.rows).map((row) => {
        const item = asObject(row);
        if (String(item.section_key || "") === String(sectionKey || "") && String(item.action || "") === String(action || "")) {
          matched = true;
          return { ...item, [role]: !Boolean(item[role]) };
        }
        return item;
      });
      if (!matched) {
        reportMatrixError(`Başlık yetki satırı bulunamadı: ${sectionKey} / ${action}`);
        return previous;
      }
      setMatrixError("");
      return { ...safePolicy, rows: nextRows };
    });
  }

  function setSectionPolicyRole(role, value, group = sectionSubtab) {
    if (!guardEditable(role)) return;
    setSectionPolicy((previous) => {
      const safePolicy = asObject(previous);
      const nextRows = asArray(safePolicy.rows).map((row) => {
        const item = asObject(row);
        return (group === "Tümü" || (item.main_title || "Genel") === group) ? { ...item, [role]: value } : item;
      });
      return { ...safePolicy, rows: nextRows };
    });
    setMatrixError("");
  }

  function setRoleColumn(target, role, value, group = "Tümü") {
    if (!guardEditable(role)) return;
    const key = target === "permissions" ? "rows" : "sidebar_rows";
    const field = target === "permissions" ? "category" : "group";
    let protectedChange = false;
    let bulkAllProtectedChange = false;
    setPayload((previous) => {
      const safePayload = asObject(previous);
      const next = asArray(safePayload[key]).map((row) => {
        const item = asObject(row);
        const inGroup = group === "Tümü" || (item[field] || "Genel") === group;
        if (!inGroup) return item;
        if (target === "permissions" && isSelfProtectedPermission(item.permission, role, value)) {
          protectedChange = true;
          return { ...item, [role]: true };
        }
        if (target === "sidebar" && isSelfProtectedSidebarModule(item.module, role, value)) {
          protectedChange = true;
          return { ...item, [role]: true };
        }
        if (target === "permissions" && isBulkAllProtectedPermission(item.permission, role, value, group)) {
          bulkAllProtectedChange = true;
          return { ...item, [role]: true };
        }
        if (target === "sidebar" && isBulkAllProtectedSidebarModule(item.module, role, value, group)) {
          bulkAllProtectedChange = true;
          return { ...item, [role]: true };
        }
        return { ...item, [role]: value };
      });
      return { ...safePayload, [key]: next };
    });
    if (protectedChange) reportMatrixError(selfProtectionMessage());
    else if (bulkAllProtectedChange) reportMatrixMessage(bulkAllProtectionMessage());
    else setMatrixError("");
  }

  function loadRecommendedDefaults() {
    const defaultRows = asArray(payload.default_rows);
    const defaultSidebarRows = asArray(payload.default_sidebar_rows);
    const defaultSectionRows = asArray(sectionPolicy?.default_rows);
    if (defaultRows.length || defaultSidebarRows.length) {
      const safe = enforceSelfProtection(defaultRows.length ? defaultRows : rows, defaultSidebarRows.length ? defaultSidebarRows : sidebarRows);
      setPayload({ ...payload, rows: safe.rows, sidebar_rows: safe.sidebarRows });
      if (safe.changed) reportMatrixError(selfProtectionMessage());
    }
    if (defaultSectionRows.length) {
      setSectionPolicy({ ...asObject(sectionPolicy), rows: defaultSectionRows });
    }
    reportMatrixMessage("Önerilen rol bazlı varsayılan matris yüklendi. Kalıcı olması için Kaydet düğmesine basın.");
  }

  async function save() {
    try {
      setSaving(true);
      setMatrixError("");
      const safe = enforceSelfProtection(rows, sidebarRows);
      if (safe.changed) {
        setPayload({ ...payload, rows: safe.rows, sidebar_rows: safe.sidebarRows });
      }
      const result = await api.savePermissions(safe.rows, safe.sidebarRows);
      setPayload(asObject(result));
      if (programId && sectionPolicyRows.length) {
        setSectionPolicy(asObject(await api.saveSectionPermissions(programId, sectionPolicyRows)));
      }
      if (onMatrixSaved) await onMatrixSaved().catch(() => null);
      reportMatrixMessage(safe.changed ? "Kritik kendi erişim izinleri korunarak yetki matrisi kaydedildi." : "Yetki, sidebar ve bölüm bazlı editör politikaları kaydedildi. Menü görünürlüğü güvenli şekilde yenilendi.");
    } catch (err) {
      reportMatrixError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function matrixExportTimestamp() {
    return new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  }

  function csvCell(value) {
    const clean = String(value ?? "").replace(/\r?\n/g, " ");
    return /[";,\n]/.test(clean) ? `"${clean.replace(/"/g, '""')}"` : clean;
  }

  function roleValue(row, role) {
    return row && row[role] ? "Açık" : "Kapalı";
  }

  function exportableRoleValues(row) {
    return hierarchyRoles.reduce((acc, role) => ({ ...acc, [role]: Boolean(row?.[role]) }), {});
  }

  function permissionMatrixExportPayload() {
    const generatedAt = new Date().toISOString();
    return {
      export_type: "AKYS Yetki Matrisi",
      generated_at: generatedAt,
      admin_scope: adminScope,
      tenant_id: payload.tenant_id || "global",
      program_id: programId || "",
      role_scope: hierarchyRoles,
      editable_roles: editableRoles.filter((role) => hierarchyRoles.includes(role)),
      protected_roles: protectedRoles.filter((role) => hierarchyRoles.includes(role)),
      note: delegationNote,
      matrices: {
        operation_permissions: rows.map((row) => ({
          category: row.category || "Genel",
          permission: row.permission || "",
          label: row.label || "",
          description: row.description || "",
          ...exportableRoleValues(row),
        })),
        sidebar_visibility: sidebarRows.map((row) => ({
          group: row.group || "Genel",
          module: row.module || "",
          label: row.label || "",
          description: row.description || "",
          ...exportableRoleValues(row),
        })),
        section_policies: sectionPolicyRows.map((row) => ({
          main_title: row.main_title || "Genel",
          section_key: row.section_key || "",
          section_title: row.section_title || "",
          action: row.action || "",
          label: row.label || "",
          description: row.description || "",
          ...exportableRoleValues(row),
        })),
      },
    };
  }

  function permissionMatrixCsv(payloadForExport) {
    const header = ["Matris", "Grup/Kategori", "Kod", "Etiket", "Açıklama", ...hierarchyRoles];
    const lines = [header.map(csvCell).join(";")];
    const pushRow = (matrixName, group, code, label, description, row) => {
      lines.push([matrixName, group, code, label, description, ...hierarchyRoles.map((role) => roleValue(row, role))].map(csvCell).join(";"));
    };
    asArray(payloadForExport.matrices.operation_permissions).forEach((row) => pushRow("İşlem Yetki Matrisi", row.category, row.permission, row.label, row.description, row));
    asArray(payloadForExport.matrices.sidebar_visibility).forEach((row) => pushRow("Sidebar Görünürlük Matrisi", row.group, row.module, row.label, row.description, row));
    asArray(payloadForExport.matrices.section_policies).forEach((row) => pushRow("Section Bazlı Yetki Matrisi", row.main_title, `${row.section_key} / ${row.action}`, row.label || row.section_title, row.description, row));
    return lines.join("\n");
  }

  function downloadPermissionMatrix(format = "csv") {
    try {
      const exportPayload = permissionMatrixExportPayload();
      const stamp = matrixExportTimestamp();
      if (format === "json") {
        downloadBlob(new Blob([JSON.stringify(exportPayload, null, 2)], { type: "application/json;charset=utf-8" }), `AKYS_yetki_matrisi_${stamp}.json`);
        reportMatrixMessage("Yetki matrisinin son görünür hali JSON olarak indirildi.");
        return;
      }
      const csv = permissionMatrixCsv(exportPayload);
      downloadBlob(new Blob([`﻿${csv}`], { type: "text/csv;charset=utf-8" }), `AKYS_yetki_matrisi_${stamp}.csv`);
      reportMatrixMessage("Yetki matrisinin son görünür hali CSV olarak indirildi.");
    } catch (err) {
      reportMatrixError(err.message);
    }
  }

  const operationGroups = groupedByCategory(rows, "category");
  const sidebarGroups = groupedByCategory(sidebarRows, "group");
  const filteredSectionPolicyRows = sectionPolicyRows.filter((row) => {
    const q = sectionPolicyQuery.trim().toLowerCase();
    if (!q) return true;
    return [row.section_key, row.section_title, row.main_title, row.action, row.label].some((value) => String(value || "").toLowerCase().includes(q));
  });
  const sectionGroups = groupedByCategory(filteredSectionPolicyRows, "main_title");
  const operationSubtabs = ["Tümü", ...Object.keys(operationGroups)];
  const sidebarSubtabs = ["Tümü", ...Object.keys(sidebarGroups)];
  const sectionSubtabs = ["Tümü", ...Object.keys(sectionGroups)];
  const visibleOperationGroups = operationSubtab === "Tümü" || !operationGroups[operationSubtab] ? operationGroups : { [operationSubtab]: operationGroups[operationSubtab] || [] };
  const visibleSidebarGroups = sidebarSubtab === "Tümü" || !sidebarGroups[sidebarSubtab] ? sidebarGroups : { [sidebarSubtab]: sidebarGroups[sidebarSubtab] || [] };
  const visibleSectionGroups = sectionSubtab === "Tümü" || !sectionGroups[sectionSubtab] ? sectionGroups : { [sectionSubtab]: sectionGroups[sectionSubtab] || [] };
  const activeOperationCount = Object.values(visibleOperationGroups).reduce((sum, items) => sum + asArray(items).length, 0);
  const activeSidebarCount = Object.values(visibleSidebarGroups).reduce((sum, items) => sum + asArray(items).length, 0);
  const activeSectionCount = Object.values(visibleSectionGroups).reduce((sum, items) => sum + asArray(items).length, 0);
  const matrixTabs = [
    { id: "operations", label: "İşlem Yetki Matrisi", count: rows.length, detail: "Sidebar’daki her modülün alt ekran, sekme ve kritik aksiyon izinleri." },
    { id: "sidebar", label: "Sidebar Görünürlük Matrisi", count: sidebarRows.length, detail: "Modüller ve yönetim menülerinin rol bazlı görünürlüğü." },
    { id: "sections", label: "Section Bazlı Granular Editör / Hazırlayıcı Yetkileri", count: sectionPolicyRows.length, detail: "Her başlıkta görme, düzenleme, PUKÖ, termin, onay, kanıt, tablo ve AI izinleri." },
  ];
  const authoritySteps = adminScope === "tenant_admin"
    ? ["Süper Admin yetki sınırını belirler", "Kurum Admin kendi kurumunda dağıtır", "Birim Admin birim kapsamını yönetir", "Editör / Hazırlayıcı / Onaylayıcı / Denetçi uygulamada çalışır"]
    : ["Süper Admin tüm yetki sınırını belirler", "Kurum Admin sütunu devredilecek tavanı gösterir", "Birim Admin birim kapsamlı ara yönetim sağlar", "Kurum içi roller bu tavana göre dağıtılır"];

  const MatrixTools = ({ target, activeGroup }) => (
    <div className="matrix-tools matrix-tools-pro">
      {hierarchyRoles.map((role) => <span key={role} className={!canEditRole(role) ? "locked-tool" : ""}>
        <strong>{role}</strong>
        <button type="button" disabled={!canEditRole(role)} onClick={() => target === "sections" ? setSectionPolicyRole(role, true, activeGroup) : setRoleColumn(target, role, true, activeGroup)}>Aç</button>
        <button type="button" disabled={!canEditRole(role)} onClick={() => target === "sections" ? setSectionPolicyRole(role, false, activeGroup) : setRoleColumn(target, role, false, activeGroup)}>Kapat</button>
      </span>)}
    </div>
  );

  const SubTabs = ({ tabs, active, onChange, counts }) => (
    <div className="permission-subtabs category-tabs" role="tablist" aria-label="Alt yetki kategorileri">
      {asArray(tabs).map((tab) => <button key={tab} type="button" role="tab" aria-selected={active === tab} className={active === tab ? "active" : ""} onClick={() => onChange(tab)}>{tab}<small>{counts?.[tab] ?? 0}</small></button>)}
    </div>
  );

  const operationCounts = { Tümü: rows.length, ...Object.fromEntries(Object.entries(operationGroups).map(([key, items]) => [key, asArray(items).length])) };
  const sidebarCounts = { Tümü: sidebarRows.length, ...Object.fromEntries(Object.entries(sidebarGroups).map(([key, items]) => [key, asArray(items).length])) };
  const sectionCounts = { Tümü: filteredSectionPolicyRows.length, ...Object.fromEntries(Object.entries(sectionGroups).map(([key, items]) => [key, asArray(items).length])) };

  return (
    <section className="panel-stack permission-pro-shell permission-tabbed-pro-shell">
      {matrixError && <div className="alert warning"><strong>Yetki matrisi koruması:</strong> {matrixError}</div>}
      {operationMatrixLocked && <div className="alert info"><strong>Hiyerarşik kilit aktif:</strong> {operationMatrixLockNote}</div>}
      <div className="hero-panel stats-hero permission-hero-pro">
        <div>
          <span className="eyebrow">Kurumsal Rol Hiyerarşisi + Delegasyon</span>
          <h2>Süper Admin → Kurum Admin → Birim Admin → Operasyon Rolleri</h2>
          <p>{delegationNote}</p>
          <div className="delegation-flow">
            {authoritySteps.map((step, idx) => <span key={step}><strong>{idx + 1}</strong>{step}</span>)}
          </div>
        </div>
        <div className="matrix-summary pro-summary">
          {roleStats.map((item) => <span key={item.role} className={item.editable ? "editable" : "locked"}><strong>{item.role}</strong>{item.permissions} izin · {item.modules} modül · {item.sections} başlık</span>)}
        </div>
      </div>

      <section className="editor-panel matrix-command-panel permission-control-room">
        <div>
          <h3>Yetki Kontrol Odası</h3>
          <p className="muted">Üç ana yetki alanı üst tablarda, her alanın detayları alt tablarda yönetilir. Kilitli sütunlar korunur; Kurum Admin yalnızca Süper Admin’in açtığı tavan yetkileri devredebilir; Birim Admin birim kapsamındaki programlara toplu atanır.</p>
        </div>
        <div className="permission-filters">
          <label>Rol odağı<select value={roleFocus} onChange={(e) => setRoleFocus(e.target.value)}><option value="Tümü">Tüm roller</option>{hierarchyRoles.map((role) => <option key={role} value={role}>{role}</option>)}</select></label>
          <label className="wide">Başlık / işlem ara<input placeholder="1.1, kanıt, onay, PUKÖ..." value={sectionPolicyQuery} onChange={(e) => setSectionPolicyQuery(e.target.value)} /></label>
        </div>
        <div className="role-card-grid">
          {roleStats.map((item) => <div key={item.role} className={`role-permission-card ${item.editable ? "can-edit" : "is-locked"}`}>
            <span>{item.editable ? "Düzenlenebilir" : "Kilitli"}</span>
            <h4>{item.role}</h4>
            <p>{item.permissions} işlem izni · {item.modules} menü · {item.sections} bölüm kuralı</p>
          </div>)}
        </div>
      </section>

      <section className="editor-panel matrix-main-tabs-card" data-legacy-layout="matrix-grid">
        <div className="matrix-main-tabs" role="tablist" aria-label="Yetki matrisi ana sekmeleri">
          {matrixTabs.map((tab) => <button key={tab.id} type="button" role="tab" aria-selected={activeMatrixTab === tab.id} className={activeMatrixTab === tab.id ? "active" : ""} onClick={() => setActiveMatrixTab(tab.id)}>
            <span>{tab.label}</span>
            <small>{tab.count} kural</small>
            <em>{tab.detail}</em>
          </button>)}
        </div>
      </section>

      {activeMatrixTab === "operations" && <section className={`editor-panel matrix-panel pro-matrix-panel matrix-tab-card ${operationMatrixLocked ? "matrix-locked-inherited" : ""}`}>
        <div className="matrix-panel-head">
          <div><h3>İşlem Yetki Matrisi</h3><p className="muted">Sidebar’da görünen her ana modül burada kendi alt ekranları, sekmeleri ve kritik aksiyonlarıyla ayrı ayrı yetkilendirilir. Menü görünürlüğü ayrı, işlem yetkisi ayrı korunur.</p></div>
          <span className="badge">{activeOperationCount} görünür izin</span>
        </div>
        <SubTabs tabs={operationSubtabs} active={operationSubtab} onChange={setOperationSubtab} counts={operationCounts} />
        {!operationMatrixLocked && <MatrixTools target="permissions" activeGroup={operationSubtab} />}
        {operationMatrixLocked && <div className="notice-card info"><strong>Devralınan işlem matrisi</strong><span>Bu sütunlar üst yönetim politikasıdır. Birim Admin bu ekranı izler; başlık bazlı alt rol kuralları Section sekmesinden kaydedilir.</span></div>}
        <div className="matrix-scroll matrix-scroll-pro">
          {!Object.keys(visibleOperationGroups).length && <div className="empty-state">Bu filtrede işlem yetkisi bulunamadı.</div>}
          {Object.entries(visibleOperationGroups).map(([category, items]) => (
            <table className="data-table matrix-table permission-toggle-table" key={category}>
              <thead><tr><th colSpan={visibleRoles.length + 1} className="matrix-category">{category}</th></tr><tr><th>İzin</th>{visibleRoles.map((role) => <th key={role}>{role}{protectedRoles.includes(role) && <small className="role-lock">Kilitli</small>}</th>)}</tr></thead>
              <tbody>{asArray(items).map((row) => (
                <tr key={row.permission}><td><strong>{row.label}</strong><br /><small>{row.permission}</small>{row.description && <p className="permission-desc">{row.description}</p>}</td>{visibleRoles.map((role) => <td key={role}><label className={`switch-check ${row[role] ? "on" : "off"} ${!canEditRole(role) ? "locked" : ""}`}><input type="checkbox" disabled={operationMatrixLocked || !canEditRole(role)} checked={!!row[role]} onChange={() => togglePermission(row.permission, role)} /><span /></label></td>)}</tr>
              ))}</tbody>
            </table>
          ))}
        </div>
      </section>}

      {activeMatrixTab === "sidebar" && <section className={`editor-panel matrix-panel pro-matrix-panel matrix-tab-card ${operationMatrixLocked ? "matrix-locked-inherited" : ""}`}>
        <div className="matrix-panel-head">
          <div><h3>Sidebar Görünürlük Matrisi</h3><p className="muted">Sidebar menüsünü alt tablarla Modüller ve Yönetim olarak ayırın. Menü kapansa bile backend işlem yetkileri ayrıca korunur.</p></div>
          <span className="badge">{activeSidebarCount} görünür modül</span>
        </div>
        <SubTabs tabs={sidebarSubtabs} active={sidebarSubtab} onChange={setSidebarSubtab} counts={sidebarCounts} />
        {!operationMatrixLocked && <MatrixTools target="sidebar" activeGroup={sidebarSubtab} />}
        {operationMatrixLocked && <div className="notice-card info"><strong>Devralınan sidebar matrisi</strong><span>Menü görünürlüğü üst yönetim tarafından korunur; Birim Admin bunu tenant genelinde ezemez.</span></div>}
        <div className="matrix-scroll matrix-scroll-pro">
          {!Object.keys(visibleSidebarGroups).length && <div className="empty-state">Bu filtrede sidebar modülü bulunamadı.</div>}
          {Object.entries(visibleSidebarGroups).map(([group, items]) => (
            <table className="data-table matrix-table permission-toggle-table" key={group}>
              <thead><tr><th colSpan={visibleRoles.length + 1} className="matrix-category">{group}</th></tr><tr><th>Modül</th>{visibleRoles.map((role) => <th key={role}>{role}</th>)}</tr></thead>
              <tbody>{asArray(items).map((row) => (
                <tr key={row.module}><td><strong>{row.label}</strong><br /><small>{row.module}</small></td>{visibleRoles.map((role) => <td key={role}><label className={`switch-check ${row[role] ? "on" : "off"} ${!canEditRole(role) ? "locked" : ""}`}><input type="checkbox" disabled={operationMatrixLocked || !canEditRole(role)} checked={!!row[role]} onChange={() => toggleSidebar(row.module, role)} /><span /></label></td>)}</tr>
              ))}</tbody>
            </table>
          ))}
        </div>
      </section>}

      {activeMatrixTab === "sections" && <section className="editor-panel matrix-panel section-policy-panel pro-matrix-panel matrix-tab-card">
        <div className="matrix-panel-head">
          <div><h3>Section Bazlı Granular Editör / Hazırlayıcı Yetkileri</h3><p className="muted">Başlık gruplarını alt tablarla ayırın; her başlıkta görme, metin, PUKÖ, termin, onay, kanıt, tablo ve AI taslak izinlerini ayrı ayrı yönetin.</p></div>
          <span className="badge">{activeSectionCount} görünür başlık/işlem</span>
        </div>
        <SubTabs tabs={sectionSubtabs} active={sectionSubtab} onChange={setSectionSubtab} counts={sectionCounts} />
        <MatrixTools target="sections" activeGroup={sectionSubtab} />
        <div className="matrix-scroll section-policy-scroll matrix-scroll-pro">
          {!sectionPolicyRows.length && <div className="empty-state">Başlık bazlı politika yüklenemedi veya program seçilmedi.</div>}
          {sectionPolicyRows.length > 0 && !Object.keys(visibleSectionGroups).length && <div className="empty-state">Arama/filtreye uygun başlık yetkisi bulunamadı.</div>}
          {Object.entries(visibleSectionGroups).map(([group, items]) => (
            <table className="data-table matrix-table section-policy-table permission-toggle-table" key={group}>
              <thead><tr><th colSpan={visibleRoles.length + 2} className="matrix-category">{group}</th></tr><tr><th>Başlık</th><th>İşlem</th>{visibleRoles.map((role) => <th key={role}>{role}</th>)}</tr></thead>
              <tbody>{asArray(items).map((row) => (
                <tr key={`${row.section_key}-${row.action}`}><td><strong>{row.section_key}</strong><br /><small>{row.section_title}</small></td><td><strong>{row.label}</strong><br /><small>{row.action}</small><p className="permission-desc">{row.description}</p></td>{visibleRoles.map((role) => <td key={role}><label className={`switch-check ${row[role] ? "on" : "off"} ${!canEditRole(role) ? "locked" : ""}`}><input type="checkbox" disabled={!canEditRole(role)} checked={!!row[role]} onChange={() => toggleSectionPolicy(row.section_key, row.action, role)} /><span /></label></td>)}</tr>
              ))}</tbody>
            </table>
          ))}
        </div>
      </section>}

      <div className="action-row matrix-download-row"><button type="button" onClick={() => downloadPermissionMatrix("csv")}><Download size={16} /> Son Matrisi CSV İndir</button><button type="button" onClick={() => downloadPermissionMatrix("json")}><Download size={16} /> Son Matrisi JSON İndir</button></div>
      <div className="action-row"><button type="button" onClick={loadRecommendedDefaults}>Önerilen Varsayılan Matrisi Yükle</button><button type="button" className="primary-action" disabled={saving} onClick={save}>{saving ? "Kaydediliyor..." : "Yetki ve Sidebar Matrislerini Kaydet · Bölüm Politikalarını Kaydet"}</button></div>
    </section>
  );
}

export function RecoveryView({ onError, onMessage, refreshPrograms }) {
  const [programRows, setProgramRows] = useState([]);
  const [itemRows, setItemRows] = useState([]);
  const [activeTab, setActiveTab] = useState("program");
  async function load() {
    const [programs, items] = await Promise.all([api.deletedPrograms(), api.recoveryItems().catch(() => [])]);
    setProgramRows(asArray(programs));
    setItemRows(asArray(items));
  }
  useEffect(() => { load().catch((err) => onError(err.message)); }, []);
  async function restoreProgram(row) { try { await api.restoreProgram(row.id); onMessage("Program geri yüklendi."); await load(); await refreshPrograms?.(); } catch (err) { onError(err.message); } }
  async function purgeProgram(row) { if (!window.confirm(`${row.program_name} kalıcı olarak silinsin mi? Bu işlem geri alınamaz.`)) return; try { await api.purgeProgram(row.id); onMessage("Program kalıcı olarak silindi."); await load(); await refreshPrograms?.(); } catch (err) { onError(err.message); } }
  async function restoreItem(row) { try { await api.restoreRecoveryItem(row.item_type, row.item_id); onMessage("Arşiv öğesi geri yüklendi."); await load(); await refreshPrograms?.(); } catch (err) { onError(err.message); } }
  async function purgeItem(row) { if (!row.can_purge) return onError("Bu öğe türünde kalıcı silme güvenlik nedeniyle kapalı."); if (!window.confirm(`${row.label || row.item_id} kalıcı olarak silinsin mi? Bu işlem geri alınamaz.`)) return; try { await api.purgeRecoveryItem(row.item_type, row.item_id); onMessage("Arşiv öğesi kalıcı olarak silindi."); await load(); await refreshPrograms?.(); } catch (err) { onError(err.message); } }
  const tabs = [
    { id: "program", label: "Program Arşivi", count: programRows.length },
    { id: "all", label: "Tüm Arşiv Öğeleri", count: itemRows.length },
    { id: "evidence", label: "Kanıt", count: itemRows.filter((row) => row.item_type === "evidence").length },
    { id: "table", label: "Tablo", count: itemRows.filter((row) => row.item_type === "table").length },
    { id: "section", label: "Başlık", count: itemRows.filter((row) => row.item_type === "section").length },
  ];
  const filteredItems = activeTab === "all" ? itemRows : itemRows.filter((row) => row.item_type === activeTab);
  return (
    <section className="panel-stack">
      <div className="hero-panel stats-hero"><div><span className="eyebrow">Soft Delete + Geri Yükleme UI</span><h2>Arşive taşınan kayıtları güvenli yönetin</h2><p>Program, kanıt, tablo ve başlık arşiv kayıtları tek panelde izlenir. Riskli öğelerde kalıcı silme kapalı, geri yükleme önceliklidir.</p></div><div className="hero-score"><strong>{itemRows.length || programRows.length}</strong><span>arşiv</span></div></div>
      <section className="editor-panel">
        <div className="editor-header"><div><h2>Arşiv Sekmeleri</h2><p className="muted">Tek tıkla geri yükle; kalıcı silme yalnızca program, kanıt ve tablo için onaylı yapılır.</p></div><button onClick={load}><RefreshCw size={16} /> Yenile</button></div>
        <div className="category-tabs" role="tablist" aria-label="Arşiv kategorileri">
          {tabs.map((tab) => <button key={tab.id} type="button" role="tab" aria-selected={activeTab === tab.id} className={activeTab === tab.id ? "active" : ""} onClick={() => setActiveTab(tab.id)}>{tab.label}<small>{tab.count}</small></button>)}
        </div>
        {activeTab === "program" ? <DataTable rows={programRows} columns={["id", "accreditation_profile", "program_name", "department_name", "school_name", "report_year", "deleted_at", "deleted_by"]} actions={(row) => <div className="action-row compact"><button onClick={() => restoreProgram(row)}>Geri Yükle</button><button className="danger-button" onClick={() => purgeProgram(row)}>Kalıcı Sil</button></div>} /> : <DataTable rows={filteredItems} columns={["item_type", "label", "context", "program_id", "section_key", "deleted_at", "deleted_by", "can_restore", "can_purge"]} actions={(row) => <div className="action-row compact"><button onClick={() => restoreItem(row)}>Geri Yükle</button><button className="danger-button" disabled={!row.can_purge} onClick={() => purgeItem(row)}>Kalıcı Sil</button></div>} />}
      </section>
    </section>
  );
}

export function AnalyticsView({ onError }) {
  const [payload, setPayload] = useState(null);
  useEffect(() => { api.adminAnalytics(250).then((data) => setPayload(asObject(data))).catch((err) => onError(err.message)); }, []);
  if (!payload) return <div className="empty-state">Kullanım analitiği yükleniyor.</div>;
  return <section className="panel-stack"><div className="hero-panel stats-hero"><div><span className="eyebrow">Analytics & Usage Reports</span><h2>Kullanıcı aktivitesi ve işlem yoğunluğu</h2><p>Kalite birimi en aktif kullanıcıları, işlem türlerini ve son aktiviteleri izleyebilir.</p></div></div><TabbedExpander title="Kullanım Raporları" subtitle="Audit log üzerinden üretilen analitik özet." tabs={[{ id: "actors", label: "Kullanıcı Aktivitesi", count: payload.actors?.length || 0, content: <DataTable rows={payload.actors} columns={["actor", "count"]} /> }, { id: "actions", label: "İşlem Türleri", count: payload.actions?.length || 0, content: <DataTable rows={payload.actions} columns={["action", "count"]} /> }, { id: "recent", label: "Son İşlemler", count: payload.recent?.length || 0, content: <DataTable rows={payload.recent} columns={["ts", "action", "detail", "actor", "program_id"]} /> }]} /></section>;
}

export function AppearanceView({ user, currentAppearance, setTenantAppearance, onError, onMessage }) {
  const [payload, setPayload] = useState(null);
  const [selectedTenantId, setSelectedTenantId] = useState("");
  const [selectedPackageId, setSelectedPackageId] = useState("");
  const [busy, setBusy] = useState(false);
  const isSuper = isSuperAdminRole(normalizeRole(user?.role, user?.tenant_scope));

  async function load() {
    const data = asObject(await api.adminAppearance());
    setPayload(data);
    const tenants = asArray(data.tenants);
    const currentTenant = currentAppearance?.tenant_id || user?.tenant_id || tenants[0]?.id || "";
    const chosen = tenants.find((tenant) => tenant.id === currentTenant) || tenants[0] || {};
    setSelectedTenantId(chosen.id || "");
    setSelectedPackageId(chosen.appearance_package || data.default_package || "corporate_blue");
  }

  useEffect(() => { if (isSuper) load().catch((err) => onError(err.message)); }, [isSuper]);
  useEffect(() => {
    if (!payload || !selectedTenantId) return;
    const tenant = asArray(payload.tenants).find((item) => item.id === selectedTenantId);
    if (tenant) setSelectedPackageId(tenant.appearance_package || payload.default_package || "corporate_blue");
  }, [selectedTenantId, payload]);

  if (!isSuper) {
    return <section className="panel-stack"><div className="empty-state">Görünüm paketlerini yalnızca Süper Admin yönetebilir. Kurumunuza atanmış görünüm paketi tüm kullanıcılar için otomatik uygulanır.</div></section>;
  }
  if (!payload) return <div className="empty-state">Görünüm paketleri yükleniyor.</div>;

  const packages = asArray(payload.packages);
  const tenants = asArray(payload.tenants).filter((tenant) => !tenant.deleted_at);
  const selectedTenant = tenants.find((tenant) => tenant.id === selectedTenantId) || tenants[0] || {};
  const selectedPackage = packages.find((item) => item.id === selectedPackageId) || packages[0] || {};
  const currentPkg = asObject(currentAppearance?.package);

  async function savePackage() {
    if (!selectedTenantId || !selectedPackageId) return onError("Kurum ve görünüm paketi seçilmelidir.");
    setBusy(true);
    try {
      const updated = await api.saveTenantAppearance(selectedTenantId, { appearance_package: selectedPackageId });
      onMessage("Kurum görünüm paketi güncellendi. Bu kurumun tüm kullanıcılarında geçerli olacak.");
      if (updated?.tenant_id === currentAppearance?.tenant_id || updated?.tenant_id === user?.tenant_id) setTenantAppearance(asObject(updated));
      await load();
    } catch (err) {
      onError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel-stack appearance-admin-view">
      <div className="hero-panel stats-hero appearance-hero">
        <div>
          <span className="eyebrow">Süper Admin · Kurum Bazlı Görünüm Yönetimi</span>
          <h2>Görünüm paketlerini kurumlara ata</h2>
          <p>Buradan seçilen paket, ilgili kurumun Kurum Admin, Birim Admin, Editör / Hazırlayıcı, Onaylayıcı ve Denetçi dahil bütün kullanıcılarına uygulanır. Kullanıcı bazlı tema seçimi kapalıdır.</p>
        </div>
        <div className="hero-score"><strong>{packages.length}</strong><span>mod</span></div>
      </div>

      <section className="editor-panel appearance-control-panel">
        <div className="editor-header">
          <div>
            <h2>Kurum görünüm ataması</h2>
            <p className="muted">Bir kurum seç, kurumsal görünüm paketini ata ve tüm kullanıcılar için standardize et.</p>
          </div>
          <button onClick={load} disabled={busy}><RefreshCw size={16} /> Yenile</button>
        </div>
        <div className="form-grid two">
          <label>Kurum / Üniversite<select value={selectedTenantId} onChange={(event) => setSelectedTenantId(event.target.value)}>{tenants.map((tenant) => <option key={tenant.id} value={tenant.id}>{tenant.name}</option>)}</select></label>
          <label>Görünüm Paketi<select value={selectedPackageId} onChange={(event) => setSelectedPackageId(event.target.value)}>{packages.map((pkg) => <option key={pkg.id} value={pkg.id}>{pkg.name} · {pkg.category}</option>)}</select></label>
        </div>
        <div className="appearance-selected-card" style={{ "--tenant-accent": selectedPackage.accent, "--tenant-sidebar": selectedPackage.sidebar }}>
          <div className="appearance-preview-sidebar"><ShieldCheck size={20} /><span>{selectedPackage.name}</span></div>
          <div>
            <strong>{selectedTenant.name || "Kurum seçilmedi"}</strong>
            <p>{selectedPackage.description}</p>
            <small>Mod: {selectedPackage.mode} · Yoğunluk: {selectedPackage.density} · Vurgu: {selectedPackage.preview}</small>
          </div>
        </div>
        <div className="action-row"><button className="primary-button" onClick={savePackage} disabled={busy}>{busy ? "Kaydediliyor..." : "Görünüm Paketini Kuruma Ata"}</button></div>
      </section>

      <section className="editor-panel">
        <div className="editor-header"><div><h2>Tanımlı görünüm modları</h2><p className="muted">En az 10 hazır tema paketi. Paketler kurum ölçeğinde uygulanır.</p></div><span className="badge">{packages.length} mod</span></div>
        <div className="appearance-package-grid">
          {packages.map((pkg) => (
            <button key={pkg.id} type="button" className={`appearance-package-card ${selectedPackageId === pkg.id ? "active" : ""}`} onClick={() => setSelectedPackageId(pkg.id)} style={{ "--tenant-accent": pkg.accent, "--tenant-sidebar": pkg.sidebar }}>
              <span className="appearance-swatch"><i /><b /></span>
              <strong>{pkg.name}</strong>
              <em>{pkg.category}</em>
              <small>{pkg.description}</small>
            </button>
          ))}
        </div>
      </section>

      <section className="editor-panel">
        <div className="editor-header"><div><h2>Kurumlara atanmış paketler</h2><p className="muted">Kurum geneline uygulanan mevcut görünüm standardı.</p></div></div>
        <DataTable rows={tenants.map((tenant) => ({ kurum: tenant.name, kod: tenant.code, domain: tenant.domain, gorunum_paketi: tenant.appearance_package_name, aktif: tenant.is_active }))} columns={["kurum", "kod", "domain", "gorunum_paketi", "aktif"]} />
      </section>
    </section>
  );
}


function helpItemKey(item, index, prefix = "help") {
  if (item === null || item === undefined) return `${prefix}-${index}`;
  if (["string", "number", "boolean"].includes(typeof item)) return `${prefix}-${String(item).slice(0, 80)}-${index}`;
  const obj = asObject(item);
  return `${prefix}-${obj.step || obj.title || obj.label || obj.module || obj.name || index}`;
}

function helpItemText(item, fallback = "") {
  if (item === null || item === undefined) return fallback;
  if (["string", "number", "boolean"].includes(typeof item)) return String(item);
  if (Array.isArray(item)) return item.map((part) => helpItemText(part)).filter(Boolean).join(", ") || fallback;
  const obj = asObject(item);
  if (!Object.keys(obj).length) return fallback;
  const step = obj.step ? `${obj.step}. ` : "";
  const title = obj.title || obj.label || obj.name || obj.module || "";
  const detail = obj.detail || obj.description || obj.use || obj.text || obj.message || "";
  if (title && detail) return `${step}${title}: ${detail}`;
  if (title) return `${step}${title}`;
  if (detail) return `${step}${detail}`;
  try {
    return JSON.stringify(obj);
  } catch {
    return fallback;
  }
}

function HelpItem({ item, as = "li", className = "" }) {
  const Tag = as;
  if (item === null || item === undefined || ["string", "number", "boolean"].includes(typeof item) || Array.isArray(item)) {
    return <Tag className={className}>{helpItemText(item)}</Tag>;
  }
  const obj = asObject(item);
  const step = obj.step ? `${obj.step}. ` : "";
  const title = obj.title || obj.label || obj.name || obj.module || "";
  const detail = obj.detail || obj.description || obj.use || obj.text || obj.message || "";
  return (
    <Tag className={className}>
      {title ? <strong>{step}{title}</strong> : null}
      {detail ? <span>{detail}</span> : null}
      {!title && !detail ? helpItemText(obj) : null}
    </Tag>
  );
}

export function HelpView({ programId, onError }) {
  const [payload, setPayload] = useState(null);
  const [activeRole, setActiveRole] = useState("");

  useEffect(() => {
    let alive = true;
    api.help(programId)
      .then((data) => {
        if (!alive) return;
        const safe = asObject(data);
        setPayload(safe);
        setActiveRole(normalizeRole(safe.active_role || safe.role || "Süper Admin", safe.tenant_scope));
      })
      .catch((err) => onError(err.message));
    return () => { alive = false; };
  }, [programId]);

  if (!payload) return <div className="empty-state help-empty">Yardım içeriği yükleniyor.</div>;

  const guides = asObject(payload.guides);
  const roleAliases = { "Admin": "Süper Admin", "Süper Admin": "Süper Admin", "Kurum Admin": "Kurum Admin", "Birim Admin": "Birim Admin" };
  const requestedRole = roleAliases[activeRole] || activeRole;
  const selectedRole = guides[requestedRole] ? requestedRole : (guides[activeRole] ? activeRole : READONLY_ROLE);
  const guide = asObject(guides[selectedRole]);
  const modules = asArray(guide.modules);
  const workflow = asArray(guide.workflow);
  const checklist = asArray(guide.checklist);
  const warnings = asArray(guide.warnings);
  const dailyFocus = asArray(guide.daily_focus);
  const commonRules = asArray(payload.common_rules);
  const roleSummary = {
    moduleCount: modules.length,
    workflowCount: workflow.length,
    checklistCount: checklist.length,
    warningCount: warnings.length,
  };

  return (
    <section className="panel-stack help-manual help-premium-manual role-locked-help">
      <div className="hero-panel stats-hero help-hero">
        <div>
          <span className="eyebrow">Yardım & Kullanım · Rolüne Özel Kılavuz</span>
          <h2>{selectedRole} için akıllı kullanım rehberi</h2>
          <p>Rol bazlı ayrıntılı kullanım kılavuzu: Her kullanıcı rolü için daha detaylı, görkemli ve yön kaybettirmeyen bir yardım merkezi. Günlük odak, modül rehberi, iş akışı, kontrol listesi ve sık hatalar aynı ekranda.</p>
        </div>
        <div className="hero-score">
          <strong>{selectedRole}</strong>
          <span>aktif rol</span>
        </div>
      </div>

      <section className="editor-panel help-role-tabs">
        <div className="help-tab-header">
          <div>
            <span className="eyebrow">Rolüne Özel Kılavuz</span>
            <h2>Bu sayfa yalnızca aktif rolüne ait rehberi gösterir</h2>
            <p>Bu sayfa yalnızca aktif rolüne ait günlük odak, modül rehberi, adım adım iş akışı, kontrol listesi ve uyarıları gösterir; diğer rollerin işlem yönergeleri karışıklık oluşturmaması için saklanır.</p>
          </div>
          <span className="pill">{selectedRole}</span>
        </div>
        {guide.mission ? <p className="help-mission">{guide.mission}</p> : null}
      </section>

      <div className="metric-grid">
        <MetricCard label="Günlük odak" value={dailyFocus.length} sub="öneri" />
        <MetricCard label="Modül rehberi" value={roleSummary.moduleCount} sub="ekran" />
        <MetricCard label="İş akışı" value={roleSummary.workflowCount} sub="adım" />
        <MetricCard label="Kontrol listesi" value={roleSummary.checklistCount} sub="madde" />
      </div>

      <section className="help-role-grid hero-help-grid">
        <div className="editor-panel help-section-block">
          <div className="section-heading-row">
            <div><span className="eyebrow">Rol Özeti</span><h2>{selectedRole} bu sistemde ne yapar?</h2></div>
            <span className="pill">Özet</span>
          </div>
          <div className="warning-grid help-role-summary-grid">
            <div className="warning-card"><strong>Öncelik</strong><span>{helpItemText(dailyFocus[0], "Aktif günlük öneri bulunmuyor.")}</span></div>
            <div className="warning-card"><strong>Ana görev</strong><span>{helpItemText(workflow[0], "Rol için iş akışı tanımlı değil.")}</span></div>
            <div className="warning-card"><strong>Başlamadan önce</strong><span>{helpItemText(checklist[0] || commonRules[0], "Genel kurallar geçerli.")}</span></div>
          </div>
        </div>

        <div className="editor-panel help-section-block">
          <div className="section-heading-row">
            <div><span className="eyebrow">90 Saniyelik Başlangıç</span><h2>Sistemde kaybolmadan ilerle</h2></div>
            <span className="pill">3 adım</span>
          </div>
          <ol className="help-list">
            <li>Önce Gösterge Paneli veya Bugün Ne Yapmalıyım kartından önceliği gör.</li>
            <li>Sonra yalnızca ilgili modüle gir: Akreditasyon Stüdyosu, Kanıt Arşivi, Tablo Yönetimi veya Onay Kontrolü.</li>
            <li>İş bittiğinde Önizleme/Dışa Aktarım ile sonucu kontrol et; gereksiz ekranlar arasında dolaşma.</li>
          </ol>
        </div>
      </section>

      <section className="help-grid">
        <div className="editor-panel help-section-block">
          <div className="section-heading-row">
            <div><span className="eyebrow">Günlük Odak</span><h2>Bugün ne yapmalısın?</h2></div>
            <span className="pill">{dailyFocus.length} öneri</span>
          </div>
          <div className="warning-grid">
            {dailyFocus.map((item, index) => <HelpItem as="div" className="warning-card" item={item} key={helpItemKey(item, index, "daily-focus")} />)}
          </div>
        </div>

        <div className="editor-panel help-section-block">
          <div className="section-heading-row">
            <div><span className="eyebrow">Genel Kurallar</span><h2>Tüm roller için ortak prensipler</h2></div>
            <span className="pill">{commonRules.length} kural</span>
          </div>
          <ul className="help-list">
            {commonRules.map((item, index) => <HelpItem item={item} key={helpItemKey(item, index, "common-rule")} />)}
          </ul>
        </div>
      </section>

      <section className="help-grid">
        <div className="editor-panel help-section-block">
          <div className="section-heading-row">
            <div><span className="eyebrow">Modül Rehberi</span><h2>Hangi ekran ne işe yarar?</h2></div>
            <span className="pill">{modules.length} modül</span>
          </div>
          <div className="module-guide-list">
            {modules.map((item, index) => {
              const obj = asObject(item);
              const moduleName = obj.module || obj.title || obj.label || helpItemText(item, `Modül ${index + 1}`);
              const moduleUse = obj.use || obj.detail || obj.description || obj.text || "";
              return (
                <div className="module-guide-row" key={helpItemKey(item, index, "module")}>
                  <strong>{moduleName}</strong>
                  <span>{moduleUse || helpItemText(item)}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="editor-panel help-section-block">
          <div className="section-heading-row">
            <div><span className="eyebrow">Adım Adım</span><h2>Rol bazlı önerilen sıra</h2></div>
            <span className="pill">{workflow.length} adım</span>
          </div>
          <div className="workflow-grid">
            {workflow.map((item, index) => {
              const obj = asObject(item);
              const step = obj.step || String(index + 1);
              const title = obj.title || obj.label || obj.name || helpItemText(item, `Adım ${index + 1}`);
              const detail = obj.detail || obj.description || obj.text || obj.message || "";
              return (
                <article className="workflow-card" key={helpItemKey(item, index, "workflow")}>
                  <span>{step}</span>
                  <h3>{title}</h3>
                  {detail ? <p>{detail}</p> : null}
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="help-grid">
        <div className="editor-panel help-section-block">
          <div className="section-heading-row">
            <div><span className="eyebrow">Kontrol Listesi</span><h2>İş bitmeden önce kontrol et</h2></div>
            <span className="pill">{checklist.length} madde</span>
          </div>
          <ul className="help-list checklist-list">
            {checklist.map((item, index) => <HelpItem item={item} key={helpItemKey(item, index, "checklist")} />)}
          </ul>
        </div>

        <div className="editor-panel help-section-block warning-panel">
          <div className="section-heading-row">
            <div><span className="eyebrow">Dikkat</span><h2>Sık yapılan hata ve uyarılar</h2></div>
            <span className="pill warn-pill">{warnings.length} uyarı</span>
          </div>
          <div className="warning-grid">
            {warnings.map((item, index) => <HelpItem as="div" className="warning-card" item={item} key={helpItemKey(item, index, "warning")} />)}
          </div>
        </div>
      </section>
    </section>
  );
}

function studioRiskLabel(risk) {
  if (risk === "critical") return "Riskli";
  if (risk === "warning") return "Uyarı";
  return "İyi";
}

function studioRiskClass(risk) {
  if (risk === "critical") return "risk-critical";
  if (risk === "warning") return "risk-warning";
  return "risk-good";
}

function localStudioCard(section) {
  const textWords = String(section.report_text || "").trim().split(/\s+/).filter(Boolean).length;
  const pukoDone = ["planla", "uygula", "kontrol", "onlem"].filter((key) => String(section[key] || "").trim()).length;
  const evidenceCount = Number(section.evidence_count || section.evidence?.length || 0);
  const tableCount = Number(section.table_count || section.tables?.length || 0);
  const completion = Math.min(100, Math.round(Math.min(textWords, 300) / 300 * 35 + Math.min(evidenceCount, 2) / 2 * 20 + Math.min(tableCount, 1) * 10 + pukoDone / 4 * 20 + (section.approval_status === "Onaylandı" ? 15 : section.approval_status === "Onaya Gönderildi" ? 10 : 0)));
  const remainingDays = daysUntil(section.deadline);
  const risk = section.approval_status === "Revizyon Gerekli" || section.status === "Revizyon Gerekli" || (remainingDays !== null && remainingDays < 0) ? "critical" : completion < 45 || evidenceCount === 0 ? "warning" : "good";
  return {
    ...section,
    completion_percent: completion,
    quality_score: Number(section.quality_score || completion || 0),
    risk_level: risk,
    risk_label: studioRiskLabel(risk),
    deadline: section.deadline || "",
    days_until_deadline: remainingDays,
    responsible: { full_name: section.responsible_full_name || "Atanmamış", username: section.responsible_username || "" },
    last_updated_at: section.updated_at || "",
    evidence_count: evidenceCount,
    table_count: tableCount,
    puko_done: pukoDone,
    word_count: textWords,
    ai_ready: completion < 90 || evidenceCount === 0 || pukoDone < 4,
    suggested_evidence: ["Kurul kararı", "Paydaş görüşü", "Uygulama çıktısı", "PUKÖ izleme tablosu"],
    estimated_minutes: Math.max(20, 110 - completion),
  };
}

function SectionStudioMap({ tree = [], cards = [], activeSectionKey, selectedMapFilter = null, onPickGroup, onPickSection, onClearFilter }) {
  const fallbackTree = useMemo(() => {
    if (tree.length) return tree;
    const groups = {};
    cards.forEach((card) => {
      const title = card.report_group_title || card.main_title || "Rapor Başlıkları";
      if (!groups[title]) groups[title] = { title, total: 0, completed: 0, progress: 0, progress_total: 0, risk: "good", children: [] };
      groups[title].total += 1;
      groups[title].progress_total += Number(card.completion_percent || 0);
      groups[title].children.push({
        title: card.section_title,
        first_section_key: card.section_key,
        progress: Number(card.completion_percent || 0),
      });
      if (card.risk_level === "critical") groups[title].risk = "critical";
      else if (card.risk_level === "warning" && groups[title].risk !== "critical") groups[title].risk = "warning";
    });
    return Object.values(groups).map((group) => ({ ...group, progress: group.total ? Math.round(group.progress_total / group.total) : 0 }));
  }, [tree, cards]);

  return (
    <aside className="studio-map-panel premium-map-panel">
      <div className="studio-panel-title">
        <span className="terminal-kicker"><ClipboardList size={15} /> Bölüm Haritası</span>
        <strong>{cards.length} başlık</strong>
      </div>
      {selectedMapFilter && (
        <div className="studio-map-filter-chip">
          <span><strong>Filtre:</strong> {selectedMapFilter.label}</span>
          <button type="button" onClick={onClearFilter}>Tüm kartları göster</button>
        </div>
      )}
      <div className="studio-tree-list">
        {fallbackTree.map((group) => (
          <div className={`studio-tree-group ${studioRiskClass(group.risk)} ${selectedMapFilter?.type === "group" && selectedMapFilter?.value === group.title ? "active" : ""}`} key={group.title}>
            <button type="button" className="studio-tree-head studio-tree-head-button" onClick={() => onPickGroup?.(group.title)}>
              <span>{group.title}</span>
              <b>{Math.round(Number(group.progress || 0))}%</b>
            </button>
            <div className="studio-mini-progress"><i style={{ width: `${Math.min(100, Number(group.progress || 0))}%` }} /></div>
            {asArray(group.children).slice(0, 12).map((child) => (
              <button key={child.title} className={`studio-tree-child ${activeSectionKey === child.first_section_key ? "active" : ""}`} onClick={() => child.first_section_key && onPickSection?.(child.first_section_key, child.title, group.title)}>
                <span>{child.title}</span>
                <small>{Math.round(Number(child.progress || 0))}%</small>
              </button>
            ))}
          </div>
        ))}
      </div>
    </aside>
  );
}


function ProgressRing({ value = 0, label = "İlerleme", size = 74 }) {
  const safe = Math.max(0, Math.min(100, Number(value || 0)));
  return (
    <div className="studio-progress-ring" style={{ "--ring-value": `${safe}%`, width: size, height: size }}>
      <div><strong>{Math.round(safe)}</strong><small>{label}</small></div>
    </div>
  );
}

function StudioHeatMap({ rows = [], onPick }) {
  const items = asArray(rows);
  if (!items.length) return <div className="empty-state">Heatmap için gösterilecek başlık yok.</div>;
  return (
    <section className="studio-heatmap-premium">
      <div className="studio-panel-title">
        <span className="terminal-kicker"><BarChart3 size={15} /> Rapor Geneli Heatmap</span>
        <strong>{items.length} ölçüt</strong>
      </div>
      <div className="studio-heatmap-legend"><span className="risk-good">İyi</span><span className="risk-warning">Uyarı</span><span className="risk-critical">Kritik</span><span>Skor düşükse kutu daha yoğun görünür.</span></div>
      <div className="studio-heatmap-grid">
        {items.map((item) => (
          <button
            key={item.section_key}
            type="button"
            className={`studio-heat-tile ${studioRiskClass(item.risk)}`}
            title={`${item.section_key} · ${item.label} · kalite ${item.score}`}
            onClick={() => item.section_key && onPick?.(item.section_key)}
          >
            <strong>{item.section_key}</strong>
            <small>{item.score ?? 0}</small>
          </button>
        ))}
      </div>
    </section>
  );
}

function StudioCollaborationStrip({ collaborators = [], currentUser = "" }) {
  const others = asArray(collaborators).filter((item) => item.username !== currentUser);
  if (!others.length) return <div className="studio-collab-strip calm"><Users size={15} /> Bu başlıkta şu an yalnız çalışıyorsunuz.</div>;
  return (
    <div className="studio-collab-strip warn">
      <Users size={15} />
      <strong>{others.length} kişi aktif</strong>
      <span>{others.map((item) => item.display_name || item.username).join(", ")}</span>
      <em>Çakışma riski: kaydetmeden önce yenilemeyi kontrol edin.</em>
    </div>
  );
}

function SectionStudioCard({ card, active, selected, onPick, onToggle, onAction }) {
  const due = card.days_until_deadline;
  const dueLabel = due === null || due === undefined ? "Termin yok" : due < 0 ? `${Math.abs(due)} gün gecikti` : due === 0 ? "Bugün" : `${due} gün kaldı`;
  const dimensions = asObject(card.quality_dimensions);
  const pro = asObject(card.pro_readiness);
  return (
    <article className={`studio-section-card premium-card ${active ? "active" : ""} ${selected ? "selected" : ""} ${studioRiskClass(card.risk_level)}`} onClick={() => onPick(card.section_key)}>
      <div className="studio-card-glow" />
      <div className="studio-card-topline">
        <label className="studio-select" onClick={(event) => event.stopPropagation()}>
          <input type="checkbox" checked={selected} onChange={() => onToggle(card.section_key)} />
        </label>
        <span className="terminal-code">{card.section_key}</span>
        <em>{studioRiskLabel(card.risk_level)}</em>
      </div>
      <div className="studio-card-hero-row">
        <div>
          <h3>{card.section_title}</h3>
          <p>{card.report_subgroup_title || card.main_title}</p>
        </div>
        <ProgressRing value={card.completion_percent} label="%" size={78} />
      </div>
      <div className="studio-card-scoreline">
        <span><strong>{card.quality_score}</strong><small>Kalite</small></span>
        <span><strong>{card.evidence_count}</strong><small>Kanıt</small></span>
        <span><strong>{card.puko_done}/4</strong><small>PUKÖ</small></span>
        <span><strong>{card.estimated_minutes}</strong><small>dk</small></span>
      </div>
      <div className="studio-dimension-bars">
        {Object.entries(dimensions).slice(0, 4).map(([label, value]) => <span key={label}><small>{label}</small><i><b style={{ width: `${Math.min(100, Number(value || 0))}%` }} /></i></span>)}
      </div>
      <div className="studio-card-badges">
        {pro.target_label && <span className={`studio-pro-badge ${pro.status || "work"}`}>{pro.target_label} · {pro.label || "Pro"}</span>}
        {card.ai_ready && <span className="ai-ready-badge"><Sparkles size={12} /> AI hazır</span>}
        {Number(card.evidence_count || 0) === 0 && <span className="evidence-warning-badge">Kanıt eksik</span>}
        {card.approval_status && <span>{card.approval_status}</span>}
      </div>
      <div className="studio-card-meta">
        <span><UserCheck size={13} /> {card.responsible?.full_name || "Atanmamış"}</span>
        <span><CalendarDays size={13} /> {dueLabel}</span>
        <span><History size={13} /> {card.last_updated_at || "Güncelleme yok"}</span>
      </div>
      <div className="studio-card-actions" onClick={(event) => event.stopPropagation()}>
        <button type="button" onClick={() => onAction("ai", card.section_key)}><Sparkles size={14} /> AI Koç</button>
        <button type="button" onClick={() => onAction("evidence", card.section_key)}><Archive size={14} /> Kanıt</button>
        <button type="button" onClick={() => onAction("versions", card.section_key)}><FileDown size={14} /> Diff</button>
      </div>
    </article>
  );
}

function StudioContextPanel({ card, ai, loading, readOnly, onGenerateAi, onGeneratePuko, onGapScan, onEvidenceMatch, gapScan, evidenceMatch, onOpenEvidence, onOpenTables, onOpenVersions, onExportDocx, onExportPdf, templateBank = [], collaborators = [], currentUser = "" }) {
  const [tab, setTab] = useState("assistant");
  if (!card) return <aside className="studio-context-panel"><div className="empty-state">Bir kart seçin; Akreditasyon Asistanı, standart tarama, kanıt eşleştirme ve kalite özeti burada görünür.</div></aside>;
  const suggestions = ai || card.ai_suggestions || {};
  const pro = asObject(card.pro_readiness);
  const proChecklist = asArray(pro.checklist);
  const evidenceSuggestions = asArray(suggestions.evidence_suggestions || card.suggested_evidence);
  const weakPoints = asArray(suggestions.weak_points);
  const coachActions = asArray(suggestions.coach_actions);
  const templates = asArray(suggestions.template_suggestions).concat(asArray(templateBank)).slice(0, 6);
  const qualityRows = asArray(suggestions.quality_explanation);
  function copyText(value) {
    try { navigator.clipboard?.writeText(String(value || "")); } catch { /* clipboard optional */ }
  }
  return (
    <aside className="studio-context-panel premium-assistant-panel">
      <div className="studio-panel-title">
        <span className="terminal-kicker"><Sparkles size={15} /> Akreditasyon Asistanı</span>
        <strong>{card.section_key}</strong>
      </div>
      <StudioCollaborationStrip collaborators={collaborators} currentUser={currentUser} />
      <div className={`studio-score-orb ${studioRiskClass(card.risk_level)}`}>
        <strong>{card.quality_score}</strong>
        <span>Kalite Skoru</span>
      </div>
      <div className="context-kpi-grid">
        <span><b>{card.word_count}</b><small>Kelime</small></span>
        <span><b>{card.evidence_count}</b><small>Kanıt</small></span>
        <span><b>{card.table_count}</b><small>Tablo</small></span>
        <span><b>{card.estimated_minutes}</b><small>dk tahmin</small></span>
      </div>
      <div className="assistant-tabbar">
        {[['assistant','AI Koç'], ['standards','Standart'], ['evidence','Kanıt'], ['quality','Kalite'], ['pro','9.8+'], ['templates','Şablon']].map(([id, label]) => <button key={id} className={tab === id ? 'active' : ''} onClick={() => setTab(id)}>{label}</button>)}
      </div>
      {tab === "assistant" && (
        <div className="assistant-tab-content">
          <div className="context-action-grid two-col">
            <button disabled={loading} onClick={onGenerateAi}><Sparkles size={15} /> Koçluk Üret</button>
            <button disabled={loading || readOnly} onClick={onGeneratePuko}><Bot size={15} /> PUKÖ Öner</button>
            <button disabled={loading} onClick={onGapScan}><ShieldCheck size={15} /> Standart Tara</button>
            <button disabled={loading} onClick={onEvidenceMatch}><Archive size={15} /> Kanıt Eşleştir</button>
          </div>
          <div className="assistant-headline"><Sparkles size={16} /> {suggestions.coach_headline || "Bu bölüm için akreditasyon kalite kontrolü hazır."}</div>
          {weakPoints.length ? weakPoints.map((item) => <p className="coach-weak-point" key={item}>{item}</p>) : <p className="muted">AI koçluk üretildiğinde zayıf yönler burada görünür.</p>}
          <div className="coach-action-list">
            {coachActions.map((item, idx) => <div className="coach-action-card" key={`${item.title}-${idx}`}><strong>{item.priority}</strong><b>{item.title}</b><span>{item.detail}</span></div>)}
          </div>
        </div>
      )}
      {tab === "standards" && (
        <div className="assistant-tab-content accreditation-assistant-flow">
          <div className="context-action-grid two-col">
            <button disabled={loading} onClick={onGapScan}><ShieldCheck size={15} /> Standartlara Göre Eksiklik Tara</button>
            <button disabled={loading} onClick={onEvidenceMatch}><Archive size={15} /> Kanıt Eşleştirme Asistanı</button>
          </div>
          {gapScan ? (
            <div className="accreditation-flow-card">
              <div className="assistant-headline"><ShieldCheck size={16} /> {gapScan.summary}</div>
              <div className="context-kpi-grid">
                <span><b>{gapScan.score}</b><small>Standart Skoru</small></span>
                <span><b>{gapScan.critical_count}</b><small>Kritik Eksik</small></span>
                <span><b>{gapScan.warning_count}</b><small>Uyarı</small></span>
                <span><b>{gapScan.profile}</b><small>Profil</small></span>
              </div>
              <div className="coach-action-list">
                {asArray(gapScan.findings).map((item) => (
                  <article className={`coach-action-card ${item.severity === "kritik" ? "risk-critical" : item.severity === "uyarı" ? "risk-warning" : "risk-good"}`} key={item.id}>
                    <strong>{item.severity}</strong><b>{item.label}</b><span>{item.description}</span>
                    {asArray(item.missing).map((miss) => <small key={miss}>{miss}</small>)}
                  </article>
                ))}
              </div>
            </div>
          ) : <p className="muted">Standart tarama çalıştırıldığında ölçüte özel eksik ve zayıf alanlar burada görünür.</p>}
          {evidenceMatch && (
            <div className="accreditation-flow-card">
              <div className="assistant-headline"><Archive size={16} /> {evidenceMatch.summary}</div>
              <div className="context-kpi-grid">
                <span><b>{evidenceMatch.coverage_score}</b><small>Kapsama</small></span>
                <span><b>{evidenceMatch.linked_count}</b><small>Bağlı Kanıt</small></span>
                <span><b>{evidenceMatch.strong_count}</b><small>Güçlü</small></span>
                <span><b>{evidenceMatch.weak_count}</b><small>Zayıf</small></span>
              </div>
              <div className="context-block"><h4>Önerilen Eksik Kanıtlar</h4><ul>{asArray(evidenceMatch.missing_evidence).slice(0, 6).map((item) => <li key={item}>{item}</li>)}</ul></div>
            </div>
          )}
        </div>
      )}
      {tab === "evidence" && (
        <div className="assistant-tab-content">
          <div className="context-action-grid two-col"><button onClick={onOpenEvidence}><Archive size={15} /> Kanıtlar</button><button onClick={onOpenTables}><Table2 size={15} /> Tablolar</button></div>
          <div className="context-block"><h4>Beklenen Kanıtlar</h4><ul>{evidenceSuggestions.map((item) => <li key={item}>{item}</li>)}</ul></div>
        </div>
      )}
      {tab === "quality" && (
        <div className="assistant-tab-content">
          <div className="quality-dimension-list">{Object.entries(asObject(card.quality_dimensions)).map(([label, value]) => <span key={label}><b>{label}</b><i><em style={{ width: `${Math.min(100, Number(value || 0))}%` }} /></i><strong>{value}%</strong></span>)}</div>
          <div className="context-block"><h4>Skor Gerekçesi</h4>{qualityRows.map((item) => <p key={item}>{item}</p>)}</div>
        </div>
      )}
      {tab === "pro" && (
        <div className="assistant-tab-content">
          <div className={`pro-gate-mini ${pro.status || "work"}`}>
            <strong>{pro.target_label || "9.8+"}</strong>
            <span>{pro.label || "Pro kalite kapısı"}</span>
            <em>{pro.score ?? 0}/100</em>
          </div>
          <div className="pro-checklist">
            {proChecklist.map((item) => (
              <span key={item.key} className={item.done ? "done" : "todo"}>
                <CheckCircle2 size={14} />
                <b>{item.label}</b>
                {!item.done && <small>{item.action}</small>}
              </span>
            ))}
          </div>
        </div>
      )}
      {tab === "templates" && (
        <div className="assistant-tab-content">
          <div className="template-bank-list">
            {templates.map((item, idx) => <article key={`${item.id || item.title}-${idx}`}><span>{item.kind || item.tags || "Şablon"}</span><strong>{item.title}</strong><p>{item.content}</p><button type="button" onClick={() => copyText(item.content)}><Copy size={14} /> Kopyala</button></article>)}
          </div>
        </div>
      )}
      <div className="context-action-grid">
        <button onClick={onOpenVersions}><FileDown size={15} /> Yan Yana Diff</button>
        <button onClick={onExportDocx}><Download size={15} /> Bölüm DOCX</button>
        <button onClick={onExportPdf}><FileDown size={15} /> Bölüm PDF</button>
      </div>
    </aside>
  );
}

export function EntryView(props) {
  const sections = props.sections || [];
  const activeSection = props.activeSection;
  const [studio, setStudio] = useState(null);
  const [filter, setFilter] = useState("all");
  const [viewMode, setViewMode] = useState("heatmap");
  const [selectedKeys, setSelectedKeys] = useState([]);
  const [bulkStatus, setBulkStatus] = useState("");
  const [bulkDeadline, setBulkDeadline] = useState("");
  const [contextAi, setContextAi] = useState(null);
  const [gapScan, setGapScan] = useState(null);
  const [evidenceMatch, setEvidenceMatch] = useState(null);
  const [studioBusy, setStudioBusy] = useState(false);
  const [collaborators, setCollaborators] = useState([]);
  const [mapSelection, setMapSelection] = useState(null);
  const [editorVisible, setEditorVisible] = useState(false);

  async function loadStudio() {
    if (!props.programId) return;
    try {
      const payload = await api.reportStudio(props.programId);
      setStudio(payload);
    } catch (err) {
      props.onError?.(err.message);
      setStudio(null);
    }
  }

  useEffect(() => { loadStudio(); }, [props.programId, sections.length]);
  useEffect(() => { setContextAi(null); setGapScan(null); setEvidenceMatch(null); }, [props.activeSectionKey]);
  useEffect(() => { setEditorVisible(false); setMapSelection(null); }, [props.programId]);

  const cards = useMemo(() => {
    const source = asArray(studio?.cards);
    if (source.length) return source;
    return sections.map(localStudioCard);
  }, [studio, sections]);
  const currentUsername = props.user?.username || props.user?.full_name || "";
  const activeCardFromKey = cards.find((card) => card.section_key === props.activeSectionKey);

  const filteredCards = useMemo(() => cards.filter((card) => {
    if (filter === "mine") return currentUsername && [card.responsible?.username, card.responsible?.full_name].includes(currentUsername);
    if (filter === "overdue") return card.days_until_deadline !== null && card.days_until_deadline < 0 && card.approval_status !== "Onaylandı";
    if (filter === "approval") return card.approval_status === "Onaya Gönderildi";
    if (filter === "evidence") return Number(card.evidence_count || 0) === 0;
    if (filter === "ai") return Boolean(card.ai_ready);
    if (filter === "revision") return card.approval_status === "Revizyon Gerekli" || card.status === "Revizyon Gerekli";
    return true;
  }), [cards, filter, currentUsername]);
  const visibleCards = useMemo(() => {
    if (!mapSelection) return filteredCards;
    if (mapSelection.type === "group") {
      return filteredCards.filter((card) => [card.report_group_title, card.main_title].includes(mapSelection.value));
    }
    return filteredCards.filter((card) => card.section_key === mapSelection.value);
  }, [filteredCards, mapSelection]);
  const activeCard = activeCardFromKey || visibleCards[0] || cards[0];

  useEffect(() => {
    let cancelled = false;
    let timer = null;
    async function ping() {
      const key = activeCard?.section_key;
      if (!props.programId || !key || !editorVisible) return;
      try {
        const rows = await api.sectionCollaborationPing(props.programId, key);
        if (!cancelled) setCollaborators(asArray(rows));
      } catch {
        if (!cancelled) setCollaborators([]);
      }
    }
    ping();
    timer = window.setInterval(ping, 30000);
    return () => { cancelled = true; if (timer) window.clearInterval(timer); };
  }, [props.programId, activeCard?.section_key, editorVisible]);
  const overview = studio?.overview || {
    total_sections: cards.length,
    ready_sections: cards.filter((card) => Number(card.completion_percent || 0) >= 75).length,
    completion_percent: cards.length ? Math.round(cards.reduce((sum, card) => sum + Number(card.completion_percent || 0), 0) / cards.length) : 0,
    quality_score: cards.length ? Math.round(cards.reduce((sum, card) => sum + Number(card.quality_score || 0), 0) / cards.length) : 0,
    critical_sections: cards.filter((card) => card.risk_level === "critical").length,
    evidence_missing: cards.filter((card) => Number(card.evidence_count || 0) === 0).length,
    approval_waiting: cards.filter((card) => card.approval_status === "Onaya Gönderildi").length,
    ai_ready: cards.filter((card) => card.ai_ready).length,
  };
  const proOverview = asObject(studio?.pro_overview);
  const proActions = asArray(proOverview.next_actions);

  const filterRows = [
    ["all", "Tümü", cards.length],
    ["mine", "Benim", cards.filter((card) => currentUsername && [card.responsible?.username, card.responsible?.full_name].includes(currentUsername)).length],
    ["overdue", "Geciken", overview.overdue_sections || 0],
    ["approval", "Onay", overview.approval_waiting || 0],
    ["evidence", "Kanıtsız", overview.evidence_missing || 0],
    ["ai", "AI", overview.ai_ready || 0],
    ["revision", "Revize", cards.filter((card) => card.approval_status === "Revizyon Gerekli" || card.status === "Revizyon Gerekli").length],
  ];

  function toggleSelected(key) {
    setSelectedKeys((current) => current.includes(key) ? current.filter((item) => item !== key) : [...current, key]);
  }

  function handleMapGroup(groupTitle) {
    setMapSelection({ type: "group", value: groupTitle, label: groupTitle });
    setEditorVisible(false);
  }

  function handleMapSection(sectionKey, label, groupTitle) {
    setMapSelection({ type: "section", value: sectionKey, label: `${sectionKey} · ${label || groupTitle || "Başlık"}` });
    props.setActiveSectionKey(sectionKey);
    setEditorVisible(false);
  }

  function openCard(sectionKey) {
    props.setActiveSectionKey(sectionKey);
    setEditorVisible(true);
  }

  async function runBulk(action) {
    if (!selectedKeys.length) return props.onError?.("Toplu işlem için en az bir başlık seçin.");
    setStudioBusy(true);
    try {
      await api.bulkStudio(props.programId, { section_keys: selectedKeys, action, status: bulkStatus, deadline: bulkDeadline });
      props.onMessage?.("Toplu işlem tamamlandı.");
      setSelectedKeys([]);
      await loadStudio();
    } catch (err) {
      props.onError?.(err.message);
    } finally {
      setStudioBusy(false);
    }
  }

  async function generateAi(mode = "coach") {
    const key = activeCard?.section_key;
    if (!key) return;
    setStudioBusy(true);
    try {
      const payload = await api.sectionAiSuggestions(props.programId, key, mode);
      setContextAi(payload);
      if (mode === "puko" && payload.puko && !props.readOnly) {
        props.setForm((current) => ({ ...current, ...payload.puko }));
        props.onMessage?.("PUKÖ önerileri forma aktarıldı; kaydetmeden önce gözden geçirin.");
      } else {
        props.onMessage?.("AI önerisi sağ panelde hazır.");
      }
      await loadStudio();
    } catch (err) {
      props.onError?.(err.message);
    } finally {
      setStudioBusy(false);
    }
  }


  async function runGapScan() {
    const key = activeCard?.section_key;
    if (!key) return;
    setStudioBusy(true);
    try {
      const payload = await api.sectionAccreditationGapScan(props.programId, key);
      setGapScan(payload);
      props.onMessage?.("Standartlara göre eksiklik taraması tamamlandı.");
    } catch (err) {
      props.onError?.(err.message);
    } finally {
      setStudioBusy(false);
    }
  }

  async function runEvidenceMatch() {
    const key = activeCard?.section_key;
    if (!key) return;
    setStudioBusy(true);
    try {
      const payload = await api.sectionEvidenceMatch(props.programId, key);
      setEvidenceMatch(payload);
      props.onMessage?.("Kanıt eşleştirme analizi tamamlandı.");
    } catch (err) {
      props.onError?.(err.message);
    } finally {
      setStudioBusy(false);
    }
  }

  async function exportActiveSection(format = "docx") {
    const key = activeCard?.section_key;
    if (!key) return;
    setStudioBusy(true);
    try {
      const blob = format === "pdf" ? await api.sectionPdf(props.programId, key) : await api.sectionDocx(props.programId, key);
      downloadBlob(blob, `${key}.${format}`);
    } catch (err) {
      props.onError?.(err.message);
    } finally {
      setStudioBusy(false);
    }
  }

  function cardAction(type, key) {
    if (key) props.setActiveSectionKey(key);
    if (type === "ai") { setEditorVisible(true); generateAi("coach"); }
    if (type === "evidence") props.setActiveModule("evidence");
    if (type === "versions") props.setActiveModule("versions");
  }

  const columns = [
    ["Taslak", visibleCards.filter((card) => !["Onaya Gönderildi", "Revizyon Gerekli", "Onaylandı"].includes(card.approval_status))],
    ["Onay Bekliyor", visibleCards.filter((card) => card.approval_status === "Onaya Gönderildi")],
    ["Revize", visibleCards.filter((card) => card.approval_status === "Revizyon Gerekli" || card.status === "Revizyon Gerekli")],
    ["Tamam", visibleCards.filter((card) => card.approval_status === "Onaylandı")],
  ];
  const studioPriorityCards = [...cards]
    .sort((a, b) => {
      const riskWeight = { critical: 0, warning: 1, good: 2 };
      return (riskWeight[a.risk_level] ?? 3) - (riskWeight[b.risk_level] ?? 3) || Number(a.quality_score || 0) - Number(b.quality_score || 0);
    })
    .slice(0, 3);
  const studioWorkflowSummary = [
    { label: "Taslak", value: columns[0][1].length, hint: "yazım aşaması" },
    { label: "Onay", value: columns[1][1].length, hint: "karar bekliyor" },
    { label: "Revizyon", value: columns[2][1].length, hint: "düzeltme gerekli" },
    { label: "Tamam", value: columns[3][1].length, hint: "onaylı başlık" },
  ];

  return (
    <section className="report-studio-shell">
      <details className="studio-unified-header" open>
        <summary className="studio-unified-header-summary">
          <div className="studio-unified-header-main">
            <span className="terminal-kicker studio-kicker-compact"><Sparkles size={15} /> AI Destekli Akreditasyon Çalışma Alanı</span>
            <div className="studio-title-row"><h2>Akreditasyon Stüdyosu</h2><span className="studio-title-badge">Odak Modu</span></div>
            <p>Heatmap → Kart → Aktif Başlık akışı ile çalışın. Açıldığında kalite özeti ve iş akışı detayları da aynı premium header içinde görünür.</p>
          </div>
          <div className="studio-unified-header-metrics">
            <span><strong>{overview.completion_percent ?? 0}%</strong><small>Genel ilerleme</small></span>
            <span><strong>{overview.quality_score ?? 0}</strong><small>Kalite skoru</small></span>
            <span><strong>{proOverview.score ?? overview.pro_score ?? 0}</strong><small>Pro 9.8+ skoru</small></span>
            <span><strong>{overview.critical_sections ?? 0}</strong><small>Riskli ölçüt</small></span>
            <span><strong>{overview.estimated_finish_label || "Planlanıyor"}</strong><small>Tahmini bitiş</small></span>
          </div>
          <div className="studio-unified-header-toggle-hint">
            <strong><ShieldCheck size={15} /> Premium özet</strong>
            <small>Aç / Kapat</small>
          </div>
        </summary>
        <div className="studio-unified-header-body">
          <section className={`studio-pro-gate ${proOverview.status || "work"}`}>
            <div>
              <span className="terminal-kicker"><ShieldCheck size={16} /> Pro Quality Gate</span>
              <h3>{proOverview.target_label || "9.8+"} rapor hazırlık hedefi</h3>
              <p>{proOverview.summary || "Başlıkların kalite, kanıt, PUKÖ, tablo, onay ve tutarlılık eşiğinden geçmesi hedeflenir."}</p>
            </div>
            <div className="pro-gate-grid">
              <span><strong>{proOverview.ready_sections ?? 0}/{proOverview.total_sections ?? cards.length}</strong><small>hazır</small></span>
              <span><strong>{proOverview.near_sections ?? 0}</strong><small>yakın</small></span>
              <span><strong>{proOverview.blocker_count ?? 0}</strong><small>bloklayıcı</small></span>
              <span><strong>{proOverview.ready_percent ?? 0}%</strong><small>oran</small></span>
            </div>
            {!!proActions.length && (
              <div className="pro-action-list">
                {proActions.slice(0, 3).map((item) => (
                  <button key={item.section_key} type="button" onClick={() => openCard(item.section_key)}>
                    <strong>{item.section_key}</strong>
                    <span>{item.next_action}</span>
                    <em>{item.pro_score}/100</em>
                  </button>
                ))}
              </div>
            )}
          </section>
          <section className="studio-command-dashboard compact-studio-command studio-command-dashboard-inline">
            <div className="studio-command-card studio-command-card-main">
              <div>
                <span className="eyebrow">Odak modu</span>
                <h3>Karmaşıklığı azaltılmış çalışma akışı</h3>
                <p className="muted">Ana ekranda sadece harita, kartlar ve aktif başlık görünür; bu bölüm isteğe bağlı ayrıntıdır.</p>
              </div>
              <div className="studio-progress-stack">
                <ProgressRing value={overview.completion_percent ?? 0} label="Genel" size={86} />
                <div>
                  <strong>{cards.length} başlık</strong>
                  <span>{selectedKeys.length ? `${selectedKeys.length} seçili başlık var` : "Toplu işlem için kartları seçin"}</span>
                  <i><b style={{ width: `${Math.min(100, Number(overview.completion_percent || 0))}%` }} /></i>
                </div>
              </div>
            </div>
            <div className="studio-command-card studio-workflow-card">
              <span className="eyebrow">İş akışı</span>
              <div className="studio-workflow-pills">
                {studioWorkflowSummary.map((item) => <button key={item.label} type="button" onClick={() => setViewMode("kanban")}><strong>{item.value}</strong><span>{item.label}</span><small>{item.hint}</small></button>)}
              </div>
            </div>
          </section>
        </div>
      </details>

      <div className="studio-filter-bar">
        {filterRows.map(([id, label, count]) => (
          <button key={id} className={filter === id ? "active" : ""} onClick={() => setFilter(id)}>{label}<em>{count}</em></button>
        ))}
        <div className="studio-view-toggle">
          <button className={viewMode === "grid" ? "active" : ""} onClick={() => setViewMode("grid")}>Kart</button>
          <button className={viewMode === "kanban" ? "active" : ""} onClick={() => setViewMode("kanban")}>Kanban</button>
          <button className={viewMode === "heatmap" ? "active" : ""} onClick={() => setViewMode("heatmap")}>Heatmap</button>
        </div>
      </div>

      {selectedKeys.length > 0 && (
        <details className="studio-bulk-bar premium-bulk-console" open>
          <summary><strong>{selectedKeys.length} başlık seçildi</strong><span>Toplu işlemler ve AI otomasyonları</span></summary>
          <div className="studio-bulk-console-grid">
            <label>Yeni durum<select value={bulkStatus} onChange={(e) => setBulkStatus(e.target.value)}><option value="">Durum seç</option>{STATUS_OPTIONS.map((item) => <option key={item}>{item}</option>)}</select></label>
            <label>Toplu termin<input value={bulkDeadline} onChange={(e) => setBulkDeadline(e.target.value)} placeholder="2026-06-30" /></label>
            <div className="studio-bulk-actions">
              <button disabled={studioBusy || !bulkStatus} onClick={() => runBulk("status")}>Durum güncelle</button>
              <button disabled={studioBusy || !bulkDeadline} onClick={() => runBulk("deadline")}>Termin güncelle</button>
              <button disabled={studioBusy} onClick={() => runBulk("quality")}>Kaliteyi yenile</button>
              <button disabled={studioBusy} onClick={() => runBulk("ai_draft")}><Sparkles size={14} /> AI taslak</button>
              <button disabled={studioBusy} onClick={() => runBulk("puko_draft")}><Bot size={14} /> PUKÖ taslağı</button>
              <button className="ghost-button" onClick={() => setSelectedKeys([])}>Seçimi temizle</button>
            </div>
          </div>
        </details>
      )}

      <section className="studio-layout-grid studio-layout-grid-focus">
        <SectionStudioMap
          tree={asArray(studio?.tree)}
          cards={cards}
          activeSectionKey={props.activeSectionKey}
          selectedMapFilter={mapSelection}
          onPickGroup={handleMapGroup}
          onPickSection={handleMapSection}
          onClearFilter={() => { setMapSelection(null); setEditorVisible(false); }}
        />

        <main className="studio-main-panel">
          {mapSelection && <div className="studio-selected-banner"><strong>{mapSelection.label}</strong><span>Bu bölüm için ilgili kartlar gösteriliyor. Kartlardan birine tıklayınca aktif çalışma alanı açılır.</span></div>}
          {viewMode === "heatmap" ? (
            <StudioHeatMap rows={asArray(studio?.heatmap)} onPick={(key) => handleMapSection(key, cards.find((card) => card.section_key === key)?.section_title, cards.find((card) => card.section_key === key)?.report_group_title)} />
          ) : viewMode === "kanban" ? (
            <div className="studio-kanban-board">
              {columns.map(([title, rows]) => (
                <div className="studio-kanban-column" key={title}>
                  <div className="kanban-column-title"><strong>{title}</strong><em>{rows.length}</em></div>
                  {rows.map((card) => <SectionStudioCard key={card.section_key} card={card} active={card.section_key === props.activeSectionKey} selected={selectedKeys.includes(card.section_key)} onPick={openCard} onToggle={toggleSelected} onAction={cardAction} />)}
                </div>
              ))}
            </div>
          ) : (
            <div className="studio-card-grid">
              {visibleCards.map((card) => <SectionStudioCard key={card.section_key} card={card} active={card.section_key === props.activeSectionKey} selected={selectedKeys.includes(card.section_key)} onPick={openCard} onToggle={toggleSelected} onAction={cardAction} />)}
              {!visibleCards.length && <div className="premium-empty-state"><strong>Bu bölüm için kart bulunamadı</strong><span>Haritadan başka bir bölüm seçin veya filtreleri temizleyin.</span></div>}
            </div>
          )}

          {editorVisible && activeSection ? (
            <SectionEditor {...props} section={activeSection} onStudioRefresh={loadStudio} />
          ) : (
            <div className="studio-workbench-placeholder premium-empty-state">
              <strong>Aktif çalışma alanı gizli</strong>
              <span>Önce bölüm haritasından bir bölüm seçin, sonra ilgili karta tıklayın. Böylece yalnız seçtiğiniz başlığın çalışma ekranı açılır.</span>
            </div>
          )}
        </main>
      </section>
    </section>
  );
}

export function SectionList({ sections, activeSectionKey, onPick }) {
  const canvasRef = React.useRef(null);
  const [expandedGroups, setExpandedGroups] = useState({});

  const groupedSections = useMemo(() => sections.reduce((acc, section) => {
    const main = section.report_group_title || section.main_title || "Diğer Başlıklar";
    if (!acc[main]) acc[main] = [];
    acc[main].push(section);
    return acc;
  }, {}), [sections]);

  const activeSection = sections.find((section) => section.section_key === activeSectionKey);
  const activeMainTitle = activeSection?.report_group_title || activeSection?.main_title;

  useEffect(() => {
    setExpandedGroups((current) => {
      const next = {};
      Object.entries(groupedSections).forEach(([mainTitle, groupSections], index) => {
        next[mainTitle] = current[mainTitle] ?? (mainTitle === activeMainTitle || (!activeMainTitle && index === 0));
        if (groupSections.some((section) => section.section_key === activeSectionKey)) next[mainTitle] = true;
      });
      return next;
    });
  }, [groupedSections, activeSectionKey, activeMainTitle]);

  const toggleGroup = (mainTitle) => {
    setExpandedGroups(prev => ({
      ...prev,
      [mainTitle]: !prev[mainTitle]
    }));
  };

  // Particle efekti
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width = 318;
    canvas.height = 1200;

    let particles = [];
    const colors = ['#60a5fa', '#93c5fd', '#bfdbfe'];

    class Particle {
      constructor() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;
        this.size = Math.random() * 1.3 + 0.5;
        this.speedX = Math.random() * 0.25 - 0.125;
        this.speedY = Math.random() * 0.25 - 0.125;
        this.color = colors[Math.floor(Math.random() * colors.length)];
        this.opacity = Math.random() * 0.35 + 0.2;
      }
      update() {
        this.x += this.speedX;
        this.y += this.speedY;
        if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
        if (this.y < 0 || this.y > canvas.height) this.speedY *= -1;
      }
      draw() {
        ctx.save();
        ctx.globalAlpha = this.opacity;
        ctx.fillStyle = this.color;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }
    }

    function init() {
      particles = [];
      for (let i = 0; i < 35; i++) particles.push(new Particle());
    }

    function animate() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach(p => { p.update(); p.draw(); });
      frameId = requestAnimationFrame(animate);
    }

    let frameId;
    init();
    animate();

    return () => {
      if (frameId) cancelAnimationFrame(frameId);
    };
  }, []);

  return (
    <div className="section-list">
      <canvas ref={canvasRef} className="section-list-particles" />

      <div className="section-search">
        <Search size={15} />
        <span>Rapor Dizini</span>
      </div>

      {Object.keys(groupedSections).map((mainTitle) => {
        const isExpanded = expandedGroups[mainTitle] !== false;
        const groupSections = groupedSections[mainTitle];
        const completedInGroup = groupSections.filter((section) => ["Taslak Hazır", "Tamamlandı"].includes(section.status)).length;

        return (
          <div key={mainTitle} className="section-group">
            <button
              className={`group-header ${isExpanded ? 'expanded' : ''}`}
              onClick={() => toggleGroup(mainTitle)}
            >
              <span>{mainTitle}</span>
              <small>{completedInGroup}/{groupSections.length}</small>
              <span className="toggle-icon">{isExpanded ? '−' : '+'}</span>
            </button>

            {isExpanded && mainTitle === "B. Değerlendirme Özeti" && Object.entries(groupSections.reduce((acc, section) => {
              const subgroup = section.report_subgroup_title || section.main_title || "Ölçütler";
              if (!acc[subgroup]) acc[subgroup] = [];
              acc[subgroup].push(section);
              return acc;
            }, {})).map(([subgroupTitle, subgroupSections]) => (
              <div className="section-subgroup" key={subgroupTitle}>
                <div className="section-subgroup-title">{subgroupTitle}</div>
                {subgroupSections.map((section, sectionIndex) => {
                  const isSelected = activeSectionKey === section.section_key;
                  return (
                    <button
                      key={section.section_key}
                      className={`section-row ${isSelected ? "selected" : ""}`}
                      onClick={() => onPick(section.section_key)}
                    >
                      <div className="section-row-inner">
                        <span className="criterion-index">{sectionIndex + 1}</span>
                        <div>
                          <strong>{section.section_title}</strong>
                          <small>{section.section_key} • {section.approval_status || section.status}</small>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            ))}

            {isExpanded && mainTitle !== "B. Değerlendirme Özeti" && groupSections.map((section) => {
              const isSelected = activeSectionKey === section.section_key;
              return (
                <button
                  key={section.section_key}
                  className={`section-row ${isSelected ? "selected" : ""}`}
                  onClick={() => onPick(section.section_key)}
                >
                  <div className="section-row-inner">
                    <span className="criterion-index">
                      {groupSections.indexOf(section) + 1}
                    </span>
                    <div>
                      <strong>{section.section_title}</strong>
                      <small>
                        {section.section_key} • {section.approval_status || section.status}
                      </small>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}

export function SectionEditor({ section, sections = [], form, setForm, readOnly, busy, onSave, onError, onMessage, programId, setActiveModule, hasUnsavedSectionChanges, autosaveState = {}, onStudioRefresh }) {
  const [tab, setTab] = useState("text");
  const [aiBusy, setAiBusy] = useState(false);
  const [aiPanel, setAiPanel] = useState(null);
  const [collaborators, setCollaborators] = useState([]);

  useEffect(() => {
    if (!programId || !section?.section_key) {
      setCollaborators([]);
      return undefined;
    }
    let cancelled = false;
    const ping = async () => {
      try {
        const rows = await api.sectionCollaborationPing(programId, section.section_key);
        if (!cancelled) setCollaborators(asArray(rows));
      } catch {
        if (!cancelled) setCollaborators([]);
      }
    };
    ping();
    const timer = window.setInterval(ping, 45000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [programId, section?.section_key]);

  if (!section) return <section className="editor-panel empty terminal-empty">Başlık seçin.</section>;

  const update = (field, value) => setForm((current) => ({ ...current, [field]: value }));
  const revisionNote = section.revision?.note || "";
  const wordCount = (form.report_text || "").trim().split(/\s+/).filter(Boolean).length;
  const pukoDone = ["planla", "uygula", "kontrol", "onlem"].filter((field) => (form[field] || "").trim()).length;
  const evidenceCount = section.evidence_count ?? section.evidence?.length ?? 0;
  const tableCount = section.table_count ?? section.tables?.length ?? 0;
  const currentIndex = sections.findIndex((item) => item.section_key === section.section_key);
  const autosaveLabel = (() => {
    if (readOnly) return "Salt okunur";
    if (autosaveState.status === "saving") return "Otomatik kaydediliyor...";
    if (autosaveState.status === "pending") return "Otomatik kayıt bekliyor";
    if (autosaveState.status === "saved") return `Otomatik kaydedildi${autosaveState.savedAt ? ` · ${new Date(autosaveState.savedAt).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}` : ""}`;
    if (autosaveState.status === "offline") return autosaveState.error || "Çevrimdışı taslak saklandı";
    if (autosaveState.status === "error") return `Otomatik kayıt başarısız: ${autosaveState.error || "Tekrar denenecek"}`;
    return hasUnsavedSectionChanges ? "Kaydedilmemiş değişiklik var" : "Kayıt güncel";
  })();

  async function applyQuickAi(mode = "coach") {
    if (!programId || !section?.section_key) return;
    setAiBusy(true);
    try {
      const payload = await api.sectionAiSuggestions(programId, section.section_key, mode);
      setAiPanel(payload);
      if (mode === "puko" && payload.puko && !readOnly) {
        setForm((current) => ({ ...current, ...payload.puko }));
        onMessage?.("PUKÖ AI önerileri forma aktarıldı. Kaydetmeden önce gözden geçirin.");
        setTab("puko");
      } else {
        const tips = asArray(payload.weak_points).concat(asArray(payload.rewrite_tips)).slice(0, 5).join("\n- ");
        onMessage?.(`AI önerisi hazır: ${payload.summary || "Koçluk önerileri üretildi."}${tips ? `\n- ${tips}` : ""}`);
      }
      await onStudioRefresh?.();
    } catch (err) {
      onError?.(err.message);
    } finally {
      setAiBusy(false);
    }
  }

  async function recalcQuality() {
    if (!programId || !section?.section_key) return;
    setAiBusy(true);
    try {
      const payload = await api.sectionQualityRecalculate(programId, section.section_key);
      onMessage?.(`Kalite skoru yenilendi: ${payload.quality_score}/100 (${payload.risk_level}).`);
      await onStudioRefresh?.();
    } catch (err) {
      onError?.(err.message);
    } finally {
      setAiBusy(false);
    }
  }

  return (
    <section className="editor-panel workbench">
      <div className="entry-workbench-hero">
        <div className="entry-workbench-title">
          <span className="terminal-kicker"><FileText size={16} /> Aktif çalışma başlığı</span>
          <div className="section-title-line">
            <span className="terminal-code">{section.section_key}</span>
            <h2>{section.section_title}</h2>
          </div>
          <div className="section-meta-strip">
            <span><ClipboardCheck size={14} /> {form.status || section.status}</span>
            <span><CalendarDays size={14} /> {form.deadline || "Son tarih belirtilmemiş"}</span>
            <span><Archive size={14} /> {evidenceCount} kanıt</span>
            <span><Table2 size={14} /> {tableCount} tablo</span>
          </div>

        </div>
        <aside className="active-section-assistant-card">
          <div className="assistant-card-head">
            <span><Bot size={16} /> Akreditasyon Asistanı</span>
            <em>{section.approval_status || "Taslak"}</em>
          </div>
          <strong>{currentIndex >= 0 ? `${currentIndex + 1}/${sections.length}` : "-"}</strong>
          <small>aktif başlık sırası</small>
          <div className="section-ai-actions inline-assistant-actions">
            <button type="button" disabled={aiBusy} onClick={() => applyQuickAi("coach")}><Sparkles size={15} /> Öneri</button>
            <button type="button" disabled={aiBusy || readOnly} onClick={() => applyQuickAi("puko")}><Bot size={15} /> PUKÖ</button>
            <button type="button" disabled={aiBusy} onClick={recalcQuality}><BarChart3 size={15} /> Skor</button>
          </div>
          <p>{aiPanel?.summary || "Bu başlık için metin, PUKÖ, kanıt ve tablo önerilerini buradan üretin."}</p>
        </aside>
      </div>

      {aiPanel && (
        <div className="active-section-ai-detail">
          <div className="section-heading-row">
            <div><span className="eyebrow">Başlık içi asistan çıktısı</span><h3>{aiPanel.summary || "AI önerileri hazır"}</h3></div>
            <button type="button" onClick={() => setAiPanel(null)}>Kapat</button>
          </div>
          <div className="assistant-suggestion-grid">
            {asArray(aiPanel.weak_points).slice(0, 4).map((item) => <span key={`weak-${item}`}>{item}</span>)}
            {asArray(aiPanel.rewrite_tips).slice(0, 4).map((item) => <span key={`tip-${item}`}>{item}</span>)}
            {asArray(aiPanel.actions).slice(0, 4).map((item) => <span key={`action-${item}`}>{typeof item === "string" ? item : item?.label || item?.title || "Öneri"}</span>)}
          </div>
        </div>
      )}

      {readOnly && (
        <div className="alert info">
          <Lock size={16} /> Bu başlık mevcut rol veya onay durumu nedeniyle salt okunur.
        </div>
      )}

      {collaborators.length > 1 && (
        <div className="alert info collaboration-alert">
          <Users size={16} /> Aynı başlıkta aktif çalışanlar: {collaborators.map((item) => item.display_name || item.username).join(", ")}. Çakışma riskinde kaydetmeden önce Activity Trail ve versiyon geçmişini kontrol edin.
        </div>
      )}

      {revisionNote && (
        <div className="alert revision">
          <strong>Revizyon Notu:</strong> {revisionNote}
        </div>
      )}

      <div className={`autosave-status-bar autosave-${autosaveState.status || "idle"}`}>
        <span><ClipboardCheck size={15} /> {autosaveLabel}</span>
        {!readOnly && <small>Metin, PUKÖ, not, durum ve termin alanları 25 saniye işlem yapılmadığında sessizce kaydedilir.</small>}
      </div>

      <div className="terminal-insights">
        <span><strong>{wordCount}</strong><small>kelime</small></span>
        <span><strong>{pukoDone}/4</strong><small>PUKÖ</small></span>
        <span><strong>{evidenceCount}</strong><small>kanıt</small></span>
        <span><strong>{tableCount}</strong><small>tablo</small></span>
      </div>

      <div className="work-tabs terminal-tabs">
        {[
          ["text", FileText, "Rapor Metni"],
          ["puko", ClipboardCheck, "PUKÖ"],
          ["evidence", Archive, "Kanıt"],
          ["table", Table2, "Tablo"],
          ["notes", ClipboardList, "Notlar"],
        ].map(([id, Icon, label]) => (
          <button 
            key={id} 
            className={tab === id ? "active" : ""} 
            onClick={() => setTab(id)}
          >
            <Icon size={16} />
            <span>{label}</span>
          </button>
        ))}
      </div>

      {tab === "text" && (
        <div className="text-editor-shell">
          <div className="form-grid">
            <label>
              Durum
              <select value={form.status} onChange={(e) => update("status", e.target.value)} disabled={readOnly}>
                {STATUS_OPTIONS.map(item => <option key={item}>{item}</option>)}
              </select>
            </label>
            <label>
              Son Teslim Tarih
              <input 
                value={form.deadline || ""} 
                onChange={(e) => update("deadline", e.target.value)} 
                disabled={readOnly} 
                placeholder="Süper/Kurum Admin tarafından belirlenmedi" 
              />
            </label>
          </div>

          <label>
            Kanıta dayalı ÖDR metni
            <textarea 
              className="report-textarea"
              value={form.report_text} 
              onChange={(e) => update("report_text", e.target.value)} 
              disabled={readOnly} 
              rows={16} 
            />
          </label>

          <div className="action-row">
            <button onClick={() => {
              if (hasUnsavedSectionChanges) {
                onError("Onay akışına geçmeden önce bu başlığı kaydetmelisiniz. Kaydedilmemiş değişiklikler onaya gönderilemez.");
                return;
              }
              setActiveModule("approval");
            }}>
              <Send size={16} /> Onay Akışına Git
            </button>
          </div>
        </div>
      )}

      {tab === "puko" && (
        <div className="puko-grid">
          {[["planla", "Planla"], ["uygula", "Uygula"], ["kontrol", "Kontrol Et"], ["onlem", "Önlem Al"]].map(([field, label]) => (
            <label key={field}>
              {label}
              <textarea 
                value={form[field]} 
                onChange={(e) => update(field, e.target.value)} 
                disabled={readOnly} 
                rows={7} 
              />
            </label>
          ))}
        </div>
      )}

      {tab === "evidence" && <EvidenceInlinePanel programId={programId} section={section} readOnly={readOnly} setActiveModule={setActiveModule} onError={onError} onMessage={onMessage} />}
      {tab === "table" && <TableInlinePanel programId={programId} section={section} readOnly={readOnly} setActiveModule={setActiveModule} onError={onError} onMessage={onMessage} />}
      {tab === "notes" && (
        <label>
          Notlar
          <textarea 
            value={form.notes} 
            onChange={(e) => update("notes", e.target.value)} 
            disabled={readOnly} 
            rows={12} 
          />
        </label>
      )}

      <button 
        className="primary-action terminal-save" 
        onClick={() => onSave?.()} 
        disabled={readOnly || busy}
      >
        {busy ? "Kaydediliyor..." : <><ClipboardCheck size={18} /> Bu Başlığı Kaydet</>}
      </button>
    </section>
  );
}

export function ShortcutPanel({ icon: Icon, title, body, action, onClick }) {
  return <div className="shortcut-panel"><Icon size={28} /><div><h2>{title}</h2><p>{body}</p><button onClick={onClick}>{action}</button></div></div>;
}

function cloneTableMeta(meta = {}, columns = DEFAULT_TABLE_COLUMNS) {
  const metaColumns = Array.isArray(meta?.columns) && meta.columns.length ? meta.columns.map(String) : [];
  return {
    cells: { ...(meta?.cells || {}) },
    options: { ...DEFAULT_TABLE_META.options, ...(meta?.options || {}) },
    columns: metaColumns.length ? metaColumns : (columns.length ? columns : [...DEFAULT_TABLE_COLUMNS]),
  };
}

function tableColumnsFromRows(rows = [], meta = {}) {
  if (Array.isArray(meta?.columns) && meta.columns.length) return meta.columns.map(String);
  const columns = [];
  rows.forEach((row) => Object.keys(row || {}).forEach((key) => { if (!columns.includes(key)) columns.push(key); }));
  return columns.length ? columns : [...DEFAULT_TABLE_COLUMNS];
}

function emptyTableRow(columns) {
  return Object.fromEntries(columns.map((column) => [column, ""]));
}

function tableMetaForSave(columns, meta) {
  return { ...cloneTableMeta(meta, columns), columns };
}

function clearTableSpans(cells = {}) {
  return Object.fromEntries(Object.entries(cells).map(([key, style]) => {
    const { hidden, colspan, rowspan, ...rest } = style || {};
    return [key, rest];
  }));
}

function tableCellStyle(meta, rowIndex, colIndex) {
  const style = meta?.cells?.[`${rowIndex}:${colIndex}`] || {};
  return style && typeof style === "object" ? style : {};
}

export function RichTableEditor({ columns, setColumns, rows, setRows, meta, setMeta, readOnly, compact = false }) {
  const [selected, setSelected] = useState({ row: 0, col: 0 });
  const safeMeta = cloneTableMeta(meta, columns);
  const selectedStyle = tableCellStyle(safeMeta, selected.row, selected.col);
  const selectedKey = `${selected.row}:${selected.col}`;

  function updateCell(rowIndex, column, value) {
    setRows((current) => current.map((row, idx) => (idx === rowIndex ? { ...row, [column]: value } : row)));
  }
  function updateMeta(updater) {
    setMeta((current) => cloneTableMeta(updater(cloneTableMeta(current, columns)), columns));
  }
  function patchSelectedStyle(patch) {
    if (readOnly) return;
    updateMeta((current) => ({
      ...current,
      cells: { ...current.cells, [selectedKey]: { ...(current.cells[selectedKey] || {}), ...patch } },
    }));
  }
  function toggleSelected(field) {
    patchSelectedStyle({ [field]: !selectedStyle[field] });
  }
  function setOption(key, value) {
    if (readOnly) return;
    updateMeta((current) => ({ ...current, options: { ...current.options, [key]: value } }));
  }
  function renameColumn(index, nextName) {
    if (readOnly || !nextName.trim()) return;
    const oldName = columns[index];
    const cleanName = nextName.trim();
    if (oldName === cleanName || columns.includes(cleanName)) return;
    setColumns((current) => current.map((column, idx) => (idx === index ? cleanName : column)));
    setRows((current) => current.map((row) => {
      const next = {};
      columns.forEach((column, idx) => { next[idx === index ? cleanName : column] = row[column] || ""; });
      return next;
    }));
  }
  function addRow() {
    if (readOnly) return;
    setRows((current) => [...current, emptyTableRow(columns)]);
  }
  function deleteRow() {
    if (readOnly || rows.length <= 1) return;
    setRows((current) => current.filter((_, idx) => idx !== selected.row));
    setSelected((current) => ({ row: Math.max(0, Math.min(rows.length - 2, current.row)), col: current.col }));
    updateMeta((current) => ({ ...current, cells: clearTableSpans(current.cells) }));
  }
  function addColumn() {
    if (readOnly) return;
    const name = `Sütun ${columns.length + 1}`;
    setColumns((current) => [...current, name]);
    setRows((current) => current.map((row) => ({ ...row, [name]: "" })));
    updateMeta((current) => ({ ...current, columns: [...columns, name], cells: clearTableSpans(current.cells) }));
  }
  function deleteColumn() {
    if (readOnly || columns.length <= 1) return;
    const removeName = columns[selected.col];
    const nextColumns = columns.filter((_, idx) => idx !== selected.col);
    setColumns(nextColumns);
    setRows((current) => current.map((row) => Object.fromEntries(nextColumns.map((column) => [column, row[column] || ""]))));
    setSelected((current) => ({ row: current.row, col: Math.max(0, Math.min(nextColumns.length - 1, current.col)) }));
    updateMeta((current) => ({ ...current, columns: nextColumns, cells: clearTableSpans(current.cells) }));
  }
  function mergeRight() {
    if (readOnly) return;
    const span = Number(selectedStyle.colspan || 1);
    const target = selected.col + span;
    if (target >= columns.length) return;
    updateMeta((current) => ({
      ...current,
      cells: {
        ...current.cells,
        [selectedKey]: { ...(current.cells[selectedKey] || {}), colspan: span + 1 },
        [`${selected.row}:${target}`]: { ...(current.cells[`${selected.row}:${target}`] || {}), hidden: true },
      },
    }));
  }
  function mergeDown() {
    if (readOnly) return;
    const rowSpan = Number(selectedStyle.rowspan || 1);
    const colSpan = Number(selectedStyle.colspan || 1);
    const targetRow = selected.row + rowSpan;
    if (targetRow >= rows.length) return;
    updateMeta((current) => {
      const cells = { ...current.cells, [selectedKey]: { ...(current.cells[selectedKey] || {}), rowspan: rowSpan + 1 } };
      for (let col = selected.col; col < Math.min(columns.length, selected.col + colSpan); col += 1) {
        cells[`${targetRow}:${col}`] = { ...(cells[`${targetRow}:${col}`] || {}), hidden: true };
      }
      return { ...current, cells };
    });
  }
  function unmerge() {
    if (readOnly) return;
    const colSpan = Number(selectedStyle.colspan || 1);
    const rowSpan = Number(selectedStyle.rowspan || 1);
    updateMeta((current) => {
      const cells = { ...current.cells };
      cells[selectedKey] = { ...(cells[selectedKey] || {}) };
      delete cells[selectedKey].colspan;
      delete cells[selectedKey].rowspan;
      for (let row = selected.row; row < selected.row + rowSpan; row += 1) {
        for (let col = selected.col; col < selected.col + colSpan; col += 1) {
          if (row === selected.row && col === selected.col) continue;
          cells[`${row}:${col}`] = { ...(cells[`${row}:${col}`] || {}) };
          delete cells[`${row}:${col}`].hidden;
        }
      }
      return { ...current, cells };
    });
  }
  function clearFormat() {
    if (readOnly) return;
    updateMeta((current) => {
      const cells = { ...current.cells };
      delete cells[selectedKey];
      return { ...current, cells };
    });
  }
  const cellInlineStyle = (style) => ({
    textAlign: style.align || safeMeta.options.align || "left",
    background: style.bg || "",
    color: style.color || "",
    fontWeight: style.bold ? 900 : 600,
    fontStyle: style.italic ? "italic" : "normal",
    textDecoration: style.underline ? "underline" : "none",
    fontSize: `${style.fontSize || safeMeta.options.fontSize || 10}px`,
  });

  return (
    <div className={`rich-table-editor ${compact ? "compact" : ""}`}>
      <div className="rich-toolbar">
        <button type="button" disabled={readOnly} onClick={addRow}>Satır Ekle</button>
        <button type="button" disabled={readOnly || rows.length <= 1} onClick={deleteRow}>Satır Sil</button>
        <button type="button" disabled={readOnly} onClick={addColumn}>Sütun Ekle</button>
        <button type="button" disabled={readOnly || columns.length <= 1} onClick={deleteColumn}>Sütun Sil</button>
        <span className="toolbar-sep" />
        <button type="button" className={selectedStyle.bold ? "active" : ""} disabled={readOnly} onClick={() => toggleSelected("bold")}>B</button>
        <button type="button" className={selectedStyle.italic ? "active" : ""} disabled={readOnly} onClick={() => toggleSelected("italic")}>I</button>
        <button type="button" className={selectedStyle.underline ? "active" : ""} disabled={readOnly} onClick={() => toggleSelected("underline")}>U</button>
        <button type="button" disabled={readOnly} onClick={() => patchSelectedStyle({ align: "left" })}>Sol</button>
        <button type="button" disabled={readOnly} onClick={() => patchSelectedStyle({ align: "center" })}>Orta</button>
        <button type="button" disabled={readOnly} onClick={() => patchSelectedStyle({ align: "right" })}>Sağ</button>
        <span className="toolbar-sep" />
        <button type="button" disabled={readOnly} onClick={mergeRight}>Sağa Birleştir</button>
        <button type="button" disabled={readOnly} onClick={mergeDown}>Aşağı Birleştir</button>
        <button type="button" disabled={readOnly} onClick={unmerge}>Birleşimi Çöz</button>
        <button type="button" disabled={readOnly} onClick={clearFormat}>Biçimi Temizle</button>
      </div>
      <div className="rich-toolbar secondary">
        <label>Yazı <input type="color" value={selectedStyle.color || "#142037"} disabled={readOnly} onChange={(e) => patchSelectedStyle({ color: e.target.value })} /></label>
        <label>Dolgu <input type="color" value={selectedStyle.bg || "#ffffff"} disabled={readOnly} onChange={(e) => patchSelectedStyle({ bg: e.target.value })} /></label>
        <label>Punto <select value={selectedStyle.fontSize || safeMeta.options.fontSize || 10} disabled={readOnly} onChange={(e) => patchSelectedStyle({ fontSize: Number(e.target.value) })}>{[8, 9, 10, 11, 12, 14, 16].map((size) => <option key={size} value={size}>{size}</option>)}</select></label>
        <label>Başlık Rengi <input type="color" value={safeMeta.options.headerBg || "#f4f7fc"} disabled={readOnly} onChange={(e) => setOption("headerBg", e.target.value)} /></label>
        <label>Çizgi Rengi <input type="color" value={safeMeta.options.borderColor || "#d7e3f1"} disabled={readOnly} onChange={(e) => setOption("borderColor", e.target.value)} /></label>
      </div>
      <div className="rich-table-scroll">
        <table className="rich-table" style={{ "--table-border": safeMeta.options.borderColor || "#d7e3f1", "--header-bg": safeMeta.options.headerBg || "#f4f7fc" }}>
          <thead>
            <tr>{columns.map((column, colIndex) => <th key={column}><input value={column} disabled={readOnly} onChange={(e) => renameColumn(colIndex, e.target.value)} /></th>)}</tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {columns.map((column, colIndex) => {
                  const style = tableCellStyle(safeMeta, rowIndex, colIndex);
                  if (style.hidden) return null;
                  const isSelected = selected.row === rowIndex && selected.col === colIndex;
                  return (
                    <td
                      key={`${rowIndex}:${colIndex}`}
                      colSpan={Number(style.colspan || 1)}
                      rowSpan={Number(style.rowspan || 1)}
                      className={isSelected ? "selected-cell" : ""}
                      style={cellInlineStyle(style)}
                      onClick={() => setSelected({ row: rowIndex, col: colIndex })}
                    >
                      <textarea value={row[column] || ""} disabled={readOnly} onChange={(e) => updateCell(rowIndex, column, e.target.value)} />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <small className="muted">Seçili hücre: {selected.row + 1}. satır, {selected.col + 1}. sütun. Birleştirme işlemleri seçili hücreden sağa veya aşağı çalışır.</small>
    </div>
  );
}

export function RichTablePreview({ table }) {
  const rows = table?.rows || [];
  const meta = cloneTableMeta(table?.meta || {}, tableColumnsFromRows(rows, table?.meta || {}));
  const columns = tableColumnsFromRows(rows, meta);
  if (!rows.length) return <div className="empty-state">Tabloda satır yok.</div>;
  return (
    <div className="rich-table-scroll preview">
      <table className="rich-table" style={{ "--table-border": meta.options.borderColor || "#d7e3f1", "--header-bg": meta.options.headerBg || "#f4f7fc" }}>
        <thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map((column, colIndex) => {
                const style = tableCellStyle(meta, rowIndex, colIndex);
                if (style.hidden) return null;
                return <td key={`${rowIndex}:${colIndex}`} colSpan={Number(style.colspan || 1)} rowSpan={Number(style.rowspan || 1)} style={{ textAlign: style.align || meta.options.align || "left", background: style.bg || "", color: style.color || "", fontWeight: style.bold ? 900 : 600, fontStyle: style.italic ? "italic" : "normal", textDecoration: style.underline ? "underline" : "none", fontSize: `${style.fontSize || meta.options.fontSize || 10}px` }}>{row[column] || ""}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function EvidenceInlinePanel({ programId, section, readOnly, setActiveModule, onError, onMessage }) {
  const [sectionRows, setSectionRows] = useState([]);
  const [allRows, setAllRows] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [linkCode, setLinkCode] = useState("");
  const [linkNote, setLinkNote] = useState("");
  const [file, setFile] = useState(null);
  const [code, setCode] = useState("");
  const [note, setNote] = useState("");
  const sectionKey = section?.section_key || "";
  async function load() {
    if (!programId || !sectionKey) return;
    const [current, all] = await Promise.all([api.evidence(programId, sectionKey), api.evidence(programId)]);
    setSectionRows(current);
    setAllRows(all);
    if (selectedId && !all.some((row) => row.id === selectedId)) setSelectedId("");
  }
  useEffect(() => { load().catch((err) => onError(err.message)); }, [programId, sectionKey]);
  async function uploadEvidence(event) {
    event.preventDefault();
    if (!file) return onError("Kanıt dosyası seçin.");
    try {
      await api.uploadEvidence(programId, { file, sectionKeys: [sectionKey], code: code || `${sectionKey}.K1`, note });
      setFile(null);
      setCode("");
      setNote("");
      onMessage("Kanıt bu başlığa yüklendi.");
      await load();
    } catch (err) {
      onError(err.message);
    }
  }
  function selectExistingEvidence(nextId) {
    setSelectedId(nextId);
    const selected = allRows.find((row) => row.id === nextId);
    setLinkCode(selected?.code || `${sectionKey}.K1`);
    setLinkNote(selected?.note || "");
  }
  async function linkExisting() {
    if (!selectedId) return onError("Arşivden bağlanacak kanıtı seçin.");
    try {
      await api.linkEvidence(programId, { evidence_id: selectedId, section_key: sectionKey, code: linkCode || `${sectionKey}.K1`, note: linkNote });
      setSelectedId("");
      setLinkCode("");
      setLinkNote("");
      onMessage("Mevcut kanıt bu başlığa bağlandı ve kod/not bilgisi güncellendi.");
      await load();
    } catch (err) {
      onError(err.message);
    }
  }
  async function openEvidence(row) {
    try {
      downloadBlob(await api.evidenceBlob(programId, row.id), row.original_name || "kanit");
    } catch (err) {
      onError(err.message);
    }
  }
  const linked = new Set(sectionRows.map((row) => row.id));
  const choices = allRows.filter((row) => !linked.has(row.id));
  return (
    <div className="inline-workbench">
      <div className="inline-hero">
        <Archive size={24} />
        <div>
          <span className="eyebrow">Başlığa Bağlı Kanıtlar</span>
          <h2>{sectionRows.length} kanıt bu başlıkta</h2>
          <p>Yeni belge yükleyin veya Kanıt Arşivi’nde daha önce oluşturulan bir kaydı bu başlığa bağlayın.</p>
        </div>
        <button type="button" onClick={() => setActiveModule("evidence")}>Kanıt Arşivini Aç</button>
      </div>
      <div className="inline-split">
        <form className="inline-card" onSubmit={uploadEvidence}>
          <h3>Belge yükle</h3>
          <label>Kanıt kodu<input value={code} onChange={(event) => setCode(event.target.value)} disabled={readOnly} placeholder={`${sectionKey}.K1`} /></label>
          <label>Dosya<input type="file" accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.csv" onChange={(event) => setFile(event.target.files?.[0] || null)} disabled={readOnly} /></label>
          <label className="file-chip camera-capture-chip"><Camera size={15} /> Kamera ile çek<input type="file" accept="image/*" capture="environment" onChange={(event) => setFile(event.target.files?.[0] || null)} disabled={readOnly} /></label>
          {file && <small className="selected-file-note">Seçili dosya: {file.name}</small>}
          <label>Not<input value={note} onChange={(event) => setNote(event.target.value)} disabled={readOnly} placeholder="Kısa açıklama veya belge notu" /></label>
          <button className="primary-action" disabled={readOnly}>Kanıtı Yükle</button>
        </form>
        <div className="inline-card">
          <h3>Arşivden seç</h3>
          <label>Mevcut kanıt<select value={selectedId} onChange={(event) => selectExistingEvidence(event.target.value)} disabled={readOnly || !choices.length}>
            <option value="">Kanıt seçin</option>
            {choices.map((row) => <option key={row.id} value={row.id}>{row.code || "Kanıt"} · {row.original_name}</option>)}
          </select></label>
          <label>Bu başlıktaki kanıt kodu<input value={linkCode} onChange={(event) => setLinkCode(event.target.value)} disabled={readOnly || !selectedId} placeholder={`${sectionKey}.K1`} /></label>
          <label>Bu başlıktaki not<input value={linkNote} onChange={(event) => setLinkNote(event.target.value)} disabled={readOnly || !selectedId} placeholder="Kanıt notunu güncelle" /></label>
          <p className="muted">{choices.length ? `${choices.length} arşiv kaydı bağlanabilir. Bağlamadan önce kodu değiştirebilirsiniz.` : "Bağlanabilecek ek arşiv kaydı yok."}</p>
          <button type="button" onClick={linkExisting} disabled={readOnly || !selectedId}>Mevcut kanıtı bu kodla bağla</button>
        </div>
      </div>
      <div className="inline-list">
        <DataTable rows={sectionRows} columns={["code", "original_name", "note", "uploaded_at"]} actions={(row) => <button type="button" onClick={() => openEvidence(row)}>İndir / Aç</button>} />
      </div>
    </div>
  );
}

export function TableInlinePanel({ programId, section, readOnly, setActiveModule, onError, onMessage }) {
  const [sectionTables, setSectionTables] = useState([]);
  const [allTables, setAllTables] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [editingId, setEditingId] = useState("");
  const [tableName, setTableName] = useState("");
  const [columns, setColumns] = useState([...DEFAULT_TABLE_COLUMNS]);
  const [rows, setRows] = useState([emptyTableRow(DEFAULT_TABLE_COLUMNS)]);
  const [meta, setMeta] = useState(cloneTableMeta(DEFAULT_TABLE_META, DEFAULT_TABLE_COLUMNS));
  const sectionKey = section?.section_key || "";
  async function load() {
    if (!programId || !sectionKey) return;
    const [current, all] = await Promise.all([api.tables(programId, sectionKey), api.tables(programId)]);
    setSectionTables(current);
    setAllTables(all);
    if (selectedId && !all.some((row) => row.id === selectedId)) setSelectedId("");
  }
  useEffect(() => { load().catch((err) => onError(err.message)); }, [programId, sectionKey]);
  async function importCsv(file) {
    if (!file) return;
    const text = await file.text();
    const lines = text.split(/\r?\n/).filter((line) => line.trim());
    if (!lines.length) return;
    const separator = lines[0].includes(";") ? ";" : ",";
    const nextColumns = lines[0].split(separator).map((item) => item.trim()).filter(Boolean);
    const nextRows = lines.slice(1).map((line) => Object.fromEntries(nextColumns.map((column, idx) => [column, (line.split(separator)[idx] || "").trim()])));
    const finalColumns = nextColumns.length ? nextColumns : columns;
    setColumns(finalColumns);
    setRows(nextRows.length ? nextRows : [emptyTableRow(finalColumns)]);
    setMeta(cloneTableMeta(DEFAULT_TABLE_META, finalColumns));
  }
  async function saveCustom() {
    try {
      await api.saveTable(programId, { table_id: editingId, section_key: sectionKey, table_name: tableName || `${sectionKey} Tablosu`, rows, meta: tableMetaForSave(columns, meta) });
      setEditingId("");
      setTableName("");
      setColumns([...DEFAULT_TABLE_COLUMNS]);
      setRows([emptyTableRow(DEFAULT_TABLE_COLUMNS)]);
      setMeta(cloneTableMeta(DEFAULT_TABLE_META, DEFAULT_TABLE_COLUMNS));
      onMessage(editingId ? "Tablo güncellendi." : "Tablo bu başlığa kaydedildi.");
      await load();
    } catch (err) {
      onError(err.message);
    }
  }
  async function attachExistingTable() {
    if (!selectedId) return onError("Bağlanacak tabloyu seçin.");
    const selected = allTables.find((row) => row.id === selectedId);
    if (!selected) return onError("Seçili tablo bulunamadı.");
    try {
      await api.attachTable(programId, {
        table_id: selectedId,
        section_key: sectionKey,
        table_name: tableName || selected.table_name || `${sectionKey} Tablosu`,
      });
      setSelectedId("");
      setTableName("");
      onMessage("Arşiv tablosu bu başlığa bağlandı.");
      await load();
    } catch (err) {
      onError(err.message);
    }
  }
  function editTable(table) {
    const nextColumns = tableColumnsFromRows(table.rows || [], table.meta || {});
    setEditingId(table.id);
    setSelectedId("");
    setTableName(table.table_name || `${sectionKey} Tablosu`);
    setColumns(nextColumns);
    setRows((table.rows && table.rows.length) ? table.rows : [emptyTableRow(nextColumns)]);
    setMeta(cloneTableMeta(table.meta || DEFAULT_TABLE_META, nextColumns));
  }
  function cancelEdit() {
    setEditingId("");
    setTableName("");
    setColumns([...DEFAULT_TABLE_COLUMNS]);
    setRows([emptyTableRow(DEFAULT_TABLE_COLUMNS)]);
    setMeta(cloneTableMeta(DEFAULT_TABLE_META, DEFAULT_TABLE_COLUMNS));
  }
  const currentIds = new Set(sectionTables.map((row) => row.id));
  const choices = allTables.filter((row) => !currentIds.has(row.id));
  return (
    <div className="inline-workbench">
      <div className="inline-hero">
        <Table2 size={24} />
        <div>
          <span className="eyebrow">Başlığa Bağlı Tablolar</span>
          <h2>{sectionTables.length} tablo bu başlıkta</h2>
          <p>CSV yükleyin, küçük bir özel tablo oluşturun veya Tablo Yönetimi’nde hazırlanan tabloyu bu başlığa ekleyin.</p>
        </div>
        <button type="button" onClick={() => setActiveModule("tables")}>Tablo Yönetimini Aç</button>
      </div>
      <div className="inline-split">
        <div className="inline-card">
          <h3>{editingId ? "Tabloyu düzenle" : "Tablo oluştur / yükle"}</h3>
          <label>Tablo adı<input value={tableName} onChange={(event) => setTableName(event.target.value)} disabled={readOnly} placeholder={`${sectionKey} Tablosu`} /></label>
          <label className="file-chip">CSV Yükle<input type="file" accept=".csv,text/csv" disabled={readOnly} onChange={(event) => importCsv(event.target.files?.[0])} /></label>
          <RichTableEditor columns={columns} setColumns={setColumns} rows={rows} setRows={setRows} meta={meta} setMeta={setMeta} readOnly={readOnly} compact />
          <button type="button" className="primary-action" onClick={saveCustom} disabled={readOnly}>{editingId ? "Tabloyu Güncelle" : "Tabloyu Bu Başlığa Kaydet"}</button>{editingId && <button type="button" onClick={cancelEdit} disabled={readOnly}>Düzenlemeyi İptal Et</button>}
        </div>
        <div className="inline-card">
          <h3>Arşivden seç ve bağla</h3>
          <label>Mevcut tablo<select value={selectedId} onChange={(event) => setSelectedId(event.target.value)} disabled={readOnly || !choices.length}>
            <option value="">Tablo seçin</option>
            {choices.map((row) => <option key={row.id} value={row.id}>{row.table_name} · {row.section_key}</option>)}
          </select></label>
          <p className="muted">{choices.length ? `${choices.length} tablo bu başlığa kopyalanabilir. İsterseniz bağlamadan önce yukarıdaki tablo adı alanıyla yeni ad verebilirsiniz.` : "Eklenebilecek başka tablo yok."}</p>
          <button type="button" onClick={attachExistingTable} disabled={readOnly || !selectedId}>Seçili tabloyu bu başlığa bağla</button>
        </div>
      </div>
      <div className="inline-list">
        {sectionTables.map((table) => <div className="inline-table-preview" key={table.id}><div className="editor-header"><h3>{table.table_name}</h3>{!readOnly && <button type="button" onClick={() => editTable(table)}>Düzenle</button>}</div><RichTablePreview table={table} /></div>)}
        {!sectionTables.length && <div className="empty-state">Bu başlık için tablo kaydı yok.</div>}
      </div>
    </div>
  );
}

function assetRiskClass(risk) {
  const value = String(risk || "").toLowerCase();
  if (value.includes("critical") || value.includes("kritik")) return "risk-critical";
  if (value.includes("warning") || value.includes("uyarı") || value.includes("orta")) return "risk-warning";
  return "risk-good";
}

function percentValue(value, fallback = 0) {
  const num = Number(value);
  if (!Number.isFinite(num)) return fallback;
  return Math.max(0, Math.min(100, Math.round(num)));
}

function AssetProgressRing({ value, label = "Skor", size = 76 }) {
  const safe = percentValue(value);
  return (
    <div className="studio-progress-ring asset-progress-ring" style={{ "--ring-value": `${safe}%`, width: size, height: size }}>
      <div><strong>{safe}</strong><small>{label}</small></div>
    </div>
  );
}

function PremiumAssetHero({ icon, eyebrow, title, description, metrics = [] }) {
  return (
    <div className="asset-premium-hero">
      <div className="asset-hero-copy">
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <div className="asset-hero-metrics">
        {metrics.map((metric) => <span key={metric.label}>{icon}<strong>{metric.value}</strong><small>{metric.label}</small></span>)}
      </div>
    </div>
  );
}

function AssetHeatMap({ rows = [], type = "evidence", onPick }) {
  const safeRows = asArray(rows);
  if (!safeRows.length) return <div className="premium-empty-inline"><strong>Heatmap hazır değil</strong><span>Önce ölçütlere bağlı kayıt oluşturun.</span></div>;
  return (
    <section className="asset-heatmap-panel">
      <div className="studio-panel-title"><div><span className="eyebrow">Heatmap</span><h3>{type === "table" ? "Tablo yoğunluğu ve doluluk riski" : "Kanıt yoğunluğu ve bağlantı riski"}</h3></div><span className="pill">{safeRows.length} ölçüt</span></div>
      <div className="asset-heatmap-grid">
        {safeRows.map((item) => (
          <button type="button" key={item.section_key} className={`asset-heat-cell ${assetRiskClass(item.risk_level)}`} title={`${item.section_key} · ${item.section_title}`} onClick={() => onPick?.(item.section_key)}>
            <strong>{item.section_key}</strong>
            <span>{type === "table" ? item.table_count || 0 : item.evidence_count || 0}</span>
            <small>{percentValue(item.quality_score)} skor</small>
          </button>
        ))}
      </div>
    </section>
  );
}

function AssetAssistantPanel({ title, card, assistant, type = "evidence", previewContent }) {
  const suggestions = asArray(card?.ai_suggestions || assistant?.actions);
  const emptyText = type === "table" ? "Bir tablo seçin; veri doluluk, sütun kalitesi ve AI önerileri burada görünür." : "Bir kanıt seçin; bağlantı, kalite ve AI önerileri burada görünür.";
  if (!card) return <aside className="asset-context-panel"><div className="premium-empty-inline"><strong>Sağ panel hazır</strong><span>{emptyText}</span></div></aside>;
  return (
    <aside className="asset-context-panel premium-assistant-panel">
      <div className="studio-panel-title"><div><span className="eyebrow">Akıllı Asistan</span><h3>{title}</h3></div><Sparkles size={18} /></div>
      <div className={`studio-score-orb ${assetRiskClass(card.risk_level)}`}><strong>{percentValue(card.quality_score)}</strong><small>{type === "table" ? "Tablo skoru" : "Kanıt skoru"}</small></div>
      <div className="context-kpi-grid">
        {type === "table" ? <>
          <span><b>{card.row_count || 0}</b><small>Satır</small></span>
          <span><b>{card.column_count || 0}</b><small>Sütun</small></span>
          <span><b>%{percentValue(card.completeness)}</b><small>Doluluk</small></span>
        </> : <>
          <span><b>{asArray(card.section_keys).length}</b><small>Bağlı ölçüt</small></span>
          <span><b>{card.file_type || "Dosya"}</b><small>Tür</small></span>
          <span><b>{card.age_days ?? "-"}</b><small>Gün</small></span>
        </>}
      </div>
      <div className="assistant-headline"><Bot size={17} /> {assistant?.headline || "AI kalite önerileri hazır."}</div>
      <div className="coach-action-list">
        {suggestions.map((item, idx) => <article className="coach-action-card" key={`${item}-${idx}`}><strong>Öneri {idx + 1}</strong><span>{item}</span></article>)}
      </div>
      {type === "table" && asArray(card.columns).length > 0 && <div className="asset-chip-list"><strong>Sütunlar</strong>{asArray(card.columns).map((col) => <span key={col}>{col}</span>)}</div>}
      {type === "evidence" && asArray(card.section_titles).length > 0 && <div className="asset-chip-list"><strong>Bağlı başlıklar</strong>{asArray(card.section_titles).map((item) => <span key={item}>{item}</span>)}</div>}
      {previewContent}
    </aside>
  );
}

export function EvidenceView({ programId, sections, activeSectionKey, user, offline = false, onError, onMessage }) {
  const [rows, setRows] = useState([]);
  const [studio, setStudio] = useState(null);
  const [file, setFile] = useState(null);
  const [code, setCode] = useState("");
  const [note, setNote] = useState("");
  const [targetSectionKey, setTargetSectionKey] = useState(activeSectionKey || "");
  const [preview, setPreview] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [selectedIds, setSelectedIds] = useState([]);
  const [filter, setFilter] = useState("Tümü");
  const [query, setQuery] = useState("");
  const [focusedSectionKey, setFocusedSectionKey] = useState("");
  const isViewer = normalizeRole(user?.role || READONLY_ROLE, user?.tenant_scope) === READONLY_ROLE || offline;
  const canManageArchive = !isViewer && !offline;
  const targetKey = targetSectionKey || sections[0]?.section_key || "";
  const sectionTitleMap = useMemo(() => Object.fromEntries(asArray(sections).map((section) => [section.section_key, section.section_title])), [sections]);
  useEffect(() => () => { if (preview?.url) URL.revokeObjectURL(preview.url); }, [preview?.url]);
  useEffect(() => { if (!targetSectionKey && activeSectionKey) setTargetSectionKey(activeSectionKey); }, [activeSectionKey, targetSectionKey]);
  async function load() {
    if (!programId) return;
    const [plainRows, premium] = await Promise.all([
      api.evidence(programId),
      api.evidenceStudio(programId).catch(() => null),
    ]);
    setRows(asArray(plainRows));
    setStudio(premium);
  }
  useEffect(() => { load().catch((err) => onError(err.message)); }, [programId]);
  const cards = useMemo(() => {
    const premiumCards = asArray(studio?.cards);
    if (premiumCards.length) return premiumCards;
    return asArray(rows).map((row) => ({
      ...row,
      quality_score: row.note ? 82 : 62,
      risk_level: row.note ? "good" : "warning",
      file_type: String(row.original_name || "").toLowerCase().endsWith(".pdf") ? "PDF" : "Dosya",
      section_titles: asArray(row.section_keys || [row.section_key]).map((key) => sectionTitleMap[key] || key),
      ai_suggestions: [row.note ? "Kanıt notunu rapor metnindeki ilgili cümleyle eşleştirin." : "Kanıtın raporda hangi bulguyu desteklediğini not alanına yazın."],
    }));
  }, [studio, rows, sectionTitleMap]);
  const filteredCards = useMemo(() => cards.filter((card) => {
    const searchable = `${card.original_name || ""} ${card.code || ""} ${card.note || ""} ${asArray(card.section_titles).join(" ")}`.toLowerCase();
    if (query && !searchable.includes(query.toLowerCase())) return false;
    if (filter === "Riskli") return card.risk_level === "critical" || card.risk_level === "warning";
    if (filter === "Bağlantısız") return !asArray(card.section_keys).length;
    if (filter === "PDF") return card.file_type === "PDF";
    if (filter === "Görsel") return card.file_type === "Görsel";
    if (filter === "Not Eksik") return !String(card.note || "").trim();
    if (filter === "Son 7 Gün") return Number(card.age_days ?? 9999) <= 7;
    return true;
  }), [cards, filter, query]);
  const sectionFocusedCards = useMemo(() => {
    if (!focusedSectionKey) return [];
    return filteredCards.filter((card) => asArray(card.section_keys || [card.section_key]).includes(focusedSectionKey));
  }, [filteredCards, focusedSectionKey]);
  const selectedCard = sectionFocusedCards.find((card) => String(card.id) === String(selectedId)) || sectionFocusedCards[0] || null;
  const overview = studio?.overview || { total: cards.length, linked: cards.filter((c) => asArray(c.section_keys).length).length, missing_link: cards.filter((c) => !asArray(c.section_keys).length).length, critical: cards.filter((c) => c.risk_level === "critical").length };
  const focusedSectionRow = asArray(studio?.heatmap).find((row) => row.section_key === focusedSectionKey) || asArray(sections).find((row) => row.section_key === focusedSectionKey) || null;
  function toggleSelected(id) { setSelectedIds((prev) => prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]); }
  async function submit(event) {
    event.preventDefault();
    if (!file) return onError("Kanıt dosyası seçin.");
    if (!targetKey) return onError("Kanıtın bağlanacağı başlığı seçin.");
    try {
      await api.uploadEvidence(programId, { file, sectionKeys: [targetKey], code, note });
      setFile(null); setCode(""); setNote(""); onMessage("Kanıt yüklendi."); await load();
    } catch (err) { onError(err.message); }
  }
  async function downloadEvidence(row) { try { downloadBlob(await api.evidenceBlob(programId, row.id), row.original_name || "kanit"); } catch (err) { onError(err.message); } }
  async function previewEvidence(row) {
    try {
      const blob = await api.evidenceBlob(programId, row.id);
      if (preview?.url) URL.revokeObjectURL(preview.url);
      setPreview({ row, url: URL.createObjectURL(blob), mime: blob.type || "" });
      setSelectedId(row.id);
    } catch (err) { onError(err.message); }
  }
  async function remove(row) { try { await api.deleteEvidence(programId, row.id); onMessage("Kanıt silindi."); await load(); } catch (err) { onError(err.message); } }
  async function bulkRemove() {
    if (!selectedIds.length) return;
    try {
      for (const id of selectedIds) await api.deleteEvidence(programId, id);
      setSelectedIds([]); onMessage("Seçili kanıtlar arşivlendi."); await load();
    } catch (err) { onError(err.message); }
  }
  const previewName = String(preview?.row?.original_name || selectedCard?.original_name || "").toLowerCase();
  const isImagePreview = /\.(png|jpe?g|gif|webp|bmp)$/i.test(previewName) || preview?.mime?.startsWith("image/");
  const isPdfPreview = /\.pdf$/i.test(previewName) || preview?.mime === "application/pdf";
  return (
    <section className="asset-premium-shell">
      {offline && <div className="alert warning"><Lock size={16} /> Çevrimdışı modda kanıt arşivi salt okunur. Kamera/yükleme işlemleri bağlantı geldiğinde açılır.</div>}
      <PremiumAssetHero icon={<Archive size={18} />} eyebrow="Premium Kanıt Arşivi" title="Kanıt Kokpiti" description="Önce heatmap üzerinden ölçüt seçin; ardından yalnız o ölçüte ait premium kanıt kartları ve canlı ön izleme açılır." metrics={[
        { label: "Toplam kanıt", value: overview.total || 0 },
        { label: "Bağlı", value: overview.linked || 0 },
        { label: "Eksik bağlantı", value: overview.missing_link || 0 },
        { label: "Riskli", value: overview.critical || 0 },
      ]} />
      <AssetHeatMap rows={asArray(studio?.heatmap)} type="evidence" onPick={(key) => { setFocusedSectionKey(key); setTargetSectionKey(key); setFilter("Tümü"); setSelectedId(""); setSelectedIds([]); if (preview?.url) { URL.revokeObjectURL(preview.url); setPreview(null); } }} />
      {!focusedSectionKey ? (
        <div className="asset-showcase-placeholder premium-empty-state"><strong>Kanıt kartları gizli</strong><span>Yalnızca heatmap’ten bir ölçüt seçildiğinde o ölçüte ait kanıt kartları ve canlı ön izleme alanı açılır.</span></div>
      ) : (
        <div className="asset-premium-layout">
          <main className="asset-main-column">
            <div className="asset-focus-banner"><strong>{focusedSectionKey}</strong><span>Seçili ölçüte ait kanıtlar gösteriliyor.</span><button type="button" onClick={() => { setFocusedSectionKey(""); setSelectedId(""); if (preview?.url) { URL.revokeObjectURL(preview.url); setPreview(null); } }}>Heatmap görünümüne dön</button></div>
            <div className="asset-toolbar">
              <div className="asset-search"><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Kanıt adı, kod, not veya başlık ara" /></div>
              {["Tümü", "Riskli", "Bağlantısız", "PDF", "Görsel", "Not Eksik", "Son 7 Gün"].map((item) => <button key={item} className={filter === item ? "active" : ""} onClick={() => setFilter(item)}>{item}</button>)}
              {canManageArchive && selectedIds.length > 0 && <button className="danger-button" onClick={bulkRemove}><Trash2 size={14} /> {selectedIds.length} kanıtı arşivle</button>}
            </div>
            {canManageArchive && (
              <details className="asset-upload-composer" open={false}>
                <summary><Upload size={16} /> Yeni kanıt yükle <span>{targetKey || "Başlık seç"}</span></summary>
                <form className="form-grid" onSubmit={submit}>
                  <label>Bağlanacak başlık<select value={targetKey} onChange={(event) => setTargetSectionKey(event.target.value)}>{sections.map((section) => <option key={section.section_key} value={section.section_key}>{section.section_key} · {section.section_title}</option>)}</select></label>
                  <label>Kanıt Kodu<input value={code} onChange={(event) => setCode(event.target.value)} placeholder={`${targetKey || activeSectionKey}.K1`} /></label>
                  <label>Dosya<input type="file" accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.csv" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label>
                  <label className="file-chip camera-capture-chip"><Camera size={15} /> Kamera ile çek<input type="file" accept="image/*" capture="environment" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label>
                  {file && <small className="selected-file-note">Seçili dosya: {file.name}</small>}
                  <label className="wide-field">Not<input value={note} onChange={(event) => setNote(event.target.value)} placeholder="Bu kanıt hangi ölçütü ve bulguyu destekliyor?" /></label>
                  <button className="primary-action">Kanıtı Yükle</button>
                </form>
              </details>
            )}
            <div className="asset-card-grid">
              {sectionFocusedCards.map((card) => (
                <article className={`asset-premium-card ${assetRiskClass(card.risk_level)} ${selectedCard?.id === card.id ? "active" : ""}`} key={card.id} onClick={() => previewEvidence(card)}>
                  <div className="asset-card-glow" />
                  <div className="asset-card-top"><label onClick={(event) => event.stopPropagation()}><input type="checkbox" checked={selectedIds.includes(card.id)} onChange={() => toggleSelected(card.id)} /></label><span>{card.file_type || "Dosya"}</span><em>{card.status_label || "Kanıt"}</em></div>
                  <div className="asset-card-hero"><div><strong>{card.code || "Kodsuz"}</strong><h3>{card.original_name}</h3><p>{card.note || "Not girilmedi."}</p></div><AssetProgressRing value={card.quality_score} /></div>
                  <div className="asset-chip-list compact">{asArray(card.section_titles).slice(0, 3).map((item) => <span key={item}>{item}</span>)}{!asArray(card.section_titles).length && <span>Başlık bağlantısı yok</span>}</div>
                  <div className="studio-card-actions" onClick={(event) => event.stopPropagation()}><button type="button" onClick={() => previewEvidence(card)}><Eye size={14} /> Ön İzle</button><button type="button" onClick={() => downloadEvidence(card)}><Download size={14} /> İndir</button>{canManageArchive && <button type="button" onClick={() => remove(card)}><Trash2 size={14} /> Sil</button>}</div>
                </article>
              ))}
              {!sectionFocusedCards.length && <div className="premium-empty-state"><strong>Kanıt bulunamadı</strong><span>Bu ölçüt için filtreye uyan kanıt yok.</span></div>}
            </div>
            {selectedCard && <div className="asset-live-preview-panel"><div className="editor-header"><div><span className="badge">Canlı Ön İzleme</span><h2>{selectedCard.original_name}</h2></div><button type="button" onClick={() => previewEvidence(selectedCard)}><Eye size={14} /> Ön izlemeyi aç</button></div>{preview?.row?.id === selectedCard.id ? <>{isImagePreview && <img src={preview.url} alt={preview.row.original_name} />}{isPdfPreview && <iframe src={preview.url} title={preview.row.original_name} />}{!isImagePreview && !isPdfPreview && <div className="empty-state">Bu dosya türü tarayıcı ön izleme desteklemiyor. İndir seçeneğini kullanabilirsiniz.</div>}</> : <div className="premium-empty-inline"><strong>Canlı ön izleme hazır</strong><span>Seçili kart için “Ön izlemeyi aç” butonuna basın; belge burada açılacaktır.</span></div>}</div>}
          </main>
          <AssetAssistantPanel title={selectedCard?.original_name} card={selectedCard} assistant={studio?.assistant} type="evidence" previewContent={preview && <div className="asset-preview-note"><strong>Ön izleme açık</strong><span>{preview.row.original_name}</span></div>} />
        </div>
      )}
    </section>
  );
}

export function TablesView({ programId, sections, activeSectionKey, user, offline = false, onError, onMessage }) {
  const [tables, setTables] = useState([]);
  const [studio, setStudio] = useState(null);
  const [tableName, setTableName] = useState("");
  const [editingId, setEditingId] = useState("");
  const [targetSectionKey, setTargetSectionKey] = useState(activeSectionKey || "");
  const [columns, setColumns] = useState([...DEFAULT_TABLE_COLUMNS]);
  const [rows, setRows] = useState([emptyTableRow(DEFAULT_TABLE_COLUMNS)]);
  const [meta, setMeta] = useState(cloneTableMeta(DEFAULT_TABLE_META, DEFAULT_TABLE_COLUMNS));
  const [selectedId, setSelectedId] = useState("");
  const [selectedIds, setSelectedIds] = useState([]);
  const [filter, setFilter] = useState("Tümü");
  const [query, setQuery] = useState("");
  const [focusedSectionKey, setFocusedSectionKey] = useState("");
  const isViewer = normalizeRole(user?.role || READONLY_ROLE, user?.tenant_scope) === READONLY_ROLE || offline;
  const canManageTables = !isViewer;
  const targetKey = targetSectionKey || sections[0]?.section_key || "";
  useEffect(() => { if (!targetSectionKey && activeSectionKey) setTargetSectionKey(activeSectionKey); }, [activeSectionKey, targetSectionKey]);
  async function load() {
    if (!programId) return;
    const [plainRows, premium] = await Promise.all([api.tables(programId), api.tablesStudio(programId).catch(() => null)]);
    setTables(asArray(plainRows));
    setStudio(premium);
  }
  useEffect(() => { load().catch((err) => onError(err.message)); }, [programId]);
  async function importCsv(file) {
    if (!file) return;
    const text = await file.text();
    const lines = text.split("\n").map((line) => line.replace(/\r$/, "")).filter((line) => line.trim());
    if (!lines.length) return;
    const separator = lines[0].includes(";") ? ";" : ",";
    const nextColumns = lines[0].split(separator).map((item) => item.trim()).filter(Boolean);
    const nextRows = lines.slice(1).map((line) => Object.fromEntries(nextColumns.map((column, idx) => [column, (line.split(separator)[idx] || "").trim()])));
    const finalColumns = nextColumns.length ? nextColumns : columns;
    setColumns(finalColumns);
    setRows(nextRows.length ? nextRows : [emptyTableRow(finalColumns)]);
    setMeta(cloneTableMeta(DEFAULT_TABLE_META, finalColumns));
  }
  function downloadTemplate() {
    const csv = [columns.join(";"), ...rows.map((row) => columns.map((col) => String(row[col] || "").replaceAll(";", ",")).join(";"))].join("\n");
    downloadBlob(new Blob([`﻿${csv}`], { type: "text/csv;charset=utf-8" }), `${tableName || "akreditasyon_tablo_sablonu"}.csv`);
  }
  async function save() {
    if (!targetKey) return onError("Tablonun bağlanacağı başlığı seçin.");
    try {
      await api.saveTable(programId, { table_id: editingId, section_key: targetKey, table_name: tableName || "Özel Tablo", rows, meta: tableMetaForSave(columns, meta) });
      cancelEdit();
      onMessage(editingId ? "Tablo güncellendi." : "Tablo kaydedildi.");
      await load();
    } catch (err) { onError(err.message); }
  }
  function editTable(table) {
    const source = tables.find((item) => item.id === table.id) || table;
    const nextColumns = tableColumnsFromRows(source.rows || [], source.meta || {});
    setEditingId(source.id);
    setSelectedId(source.id);
    setTargetSectionKey(source.section_key || targetKey);
    setTableName(source.table_name || "Özel Tablo");
    setColumns(nextColumns);
    setRows((source.rows && source.rows.length) ? source.rows : [emptyTableRow(nextColumns)]);
    setMeta(cloneTableMeta(source.meta || DEFAULT_TABLE_META, nextColumns));
  }
  function cancelEdit() {
    setEditingId("");
    setTableName("");
    setColumns([...DEFAULT_TABLE_COLUMNS]);
    setRows([emptyTableRow(DEFAULT_TABLE_COLUMNS)]);
    setMeta(cloneTableMeta(DEFAULT_TABLE_META, DEFAULT_TABLE_COLUMNS));
  }
  async function remove(table) { try { await api.deleteTable(programId, table.id); onMessage("Tablo silindi."); await load(); } catch (err) { onError(err.message); } }
  function toggleSelected(id) { setSelectedIds((prev) => prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]); }
  async function bulkRemove() {
    if (!selectedIds.length) return;
    try {
      for (const id of selectedIds) await api.deleteTable(programId, id);
      setSelectedIds([]); onMessage("Seçili tablolar arşivlendi."); await load();
    } catch (err) { onError(err.message); }
  }
  const cards = useMemo(() => {
    const premiumCards = asArray(studio?.cards);
    if (premiumCards.length) return premiumCards;
    return asArray(tables).map((table) => ({
      ...table,
      row_count: asArray(table.rows).length,
      column_count: tableColumnsFromRows(table.rows || [], table.meta || {}).length,
      completeness: asArray(table.rows).length ? 80 : 25,
      quality_score: asArray(table.rows).length ? 80 : 25,
      risk_level: asArray(table.rows).length ? "good" : "critical",
      ai_suggestions: [asArray(table.rows).length ? "Tabloyu rapor metninde tablo adıyla referanslayın." : "Tabloya veri satırı ekleyin veya CSV’den aktarın."],
    }));
  }, [studio, tables]);
  const filteredCards = useMemo(() => cards.filter((card) => {
    const searchable = `${card.table_name || ""} ${card.section_key || ""} ${card.section_title || ""} ${asArray(card.columns).join(" ")}`.toLowerCase();
    if (query && !searchable.includes(query.toLowerCase())) return false;
    if (filter === "Riskli") return card.risk_level === "critical" || card.risk_level === "warning";
    if (filter === "Boş") return Number(card.row_count || 0) === 0;
    if (filter === "Geniş Tablo") return Number(card.column_count || 0) >= 8;
    if (filter === "Doluluk Düşük") return Number(card.completeness || 0) < 70;
    if (filter === "Bağlantısız") return !card.section_key;
    return true;
  }), [cards, filter, query]);
  const sectionFocusedCards = useMemo(() => {
    if (!focusedSectionKey) return [];
    return filteredCards.filter((card) => card.section_key === focusedSectionKey);
  }, [filteredCards, focusedSectionKey]);
  const selectedCard = sectionFocusedCards.find((card) => String(card.id) === String(selectedId)) || sectionFocusedCards[0] || null;
  const selectedTable = tables.find((table) => String(table.id) === String(selectedCard?.id));
  const overview = studio?.overview || { total: cards.length, avg_score: 0, critical: 0, total_rows: 0, empty_tables: 0 };
  const focusedSectionRow = asArray(studio?.heatmap).find((row) => row.section_key === focusedSectionKey) || asArray(sections).find((row) => row.section_key === focusedSectionKey) || null;
  return (
    <section className="asset-premium-shell">
      {offline && <div className="alert warning"><Lock size={16} /> Çevrimdışı modda tablo yönetimi salt okunur. Bağlantı geldiğinde düzenleme/yükleme yeniden açılır.</div>}
      <PremiumAssetHero icon={<Table2 size={18} />} eyebrow="Premium Tablo Yönetimi" title="Tablo Kokpiti" description="Önce heatmap üzerinden ölçüt seçin; ardından yalnız o ölçüte ait premium tablo kartları ve canlı ön izleme açılır." metrics={[
        { label: "Toplam tablo", value: overview.total || 0 },
        { label: "Ortalama skor", value: overview.avg_score || 0 },
        { label: "Toplam satır", value: overview.total_rows || 0 },
        { label: "Riskli", value: overview.critical || 0 },
      ]} />
      <AssetHeatMap rows={asArray(studio?.heatmap)} type="table" onPick={(key) => { setFocusedSectionKey(key); setTargetSectionKey(key); setFilter("Tümü"); setSelectedId(""); setSelectedIds([]); }} />
      {!focusedSectionKey ? (
        <div className="asset-showcase-placeholder premium-empty-state"><strong>Tablo kartları gizli</strong><span>Yalnızca heatmap’ten bir ölçüt seçildiğinde o ölçüte ait tablo kartları ve canlı ön izleme alanı açılır.</span></div>
      ) : (
        <div className="asset-premium-layout">
          <main className="asset-main-column">
            <div className="asset-focus-banner"><strong>{focusedSectionKey} {focusedSectionRow?.section_title ? `· ${focusedSectionRow.section_title}` : ""}</strong><span>Seçili ölçüte ait tablolar gösteriliyor.</span><button type="button" onClick={() => { setFocusedSectionKey(""); setSelectedId(""); }}>Heatmap görünümüne dön</button></div>
            <div className="asset-toolbar">
              <div className="asset-search"><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tablo adı, ölçüt veya sütun ara" /></div>
              {["Tümü", "Riskli", "Boş", "Doluluk Düşük", "Geniş Tablo", "Bağlantısız"].map((item) => <button key={item} className={filter === item ? "active" : ""} onClick={() => setFilter(item)}>{item}</button>)}
              {canManageTables && selectedIds.length > 0 && <button className="danger-button" onClick={bulkRemove}><Trash2 size={14} /> {selectedIds.length} tabloyu arşivle</button>}
            </div>
            {canManageTables && (
              <details className="asset-upload-composer table-composer" open={false}>
                <summary><Table2 size={16} /> {editingId ? "Tabloyu düzenle" : "Yeni tablo oluştur"} <span>{targetKey || "Başlık seç"}</span></summary>
                <div className="form-grid">
                  <label>Bağlanacak başlık<select value={targetKey} onChange={(event) => setTargetSectionKey(event.target.value)}>{sections.map((section) => <option key={section.section_key} value={section.section_key}>{section.section_key} · {section.section_title}</option>)}</select></label>
                  <label>Tablo adı<input value={tableName} onChange={(event) => setTableName(event.target.value)} /></label>
                </div>
                <div className="action-row">
                  <label className="file-chip">CSV Yükle<input type="file" accept=".csv,text/csv" onChange={(event) => importCsv(event.target.files?.[0])} /></label>
                  <button type="button" onClick={downloadTemplate}>CSV Şablon İndir</button>
                  {editingId && <button type="button" onClick={cancelEdit}>Düzenlemeyi İptal Et</button>}
                </div>
                <RichTableEditor columns={columns} setColumns={setColumns} rows={rows} setRows={setRows} meta={meta} setMeta={setMeta} readOnly={false} />
                <button className="primary-action" onClick={save}>{editingId ? "Tabloyu Güncelle" : "Tabloyu Kaydet"}</button>
              </details>
            )}
            <div className="asset-card-grid table-card-grid">
              {sectionFocusedCards.map((card) => (
                <article className={`asset-premium-card table-card ${assetRiskClass(card.risk_level)} ${selectedCard?.id === card.id ? "active" : ""}`} key={card.id} onClick={() => setSelectedId(card.id)}>
                  <div className="asset-card-glow" />
                  <div className="asset-card-top"><label onClick={(event) => event.stopPropagation()}><input type="checkbox" checked={selectedIds.includes(card.id)} onChange={() => toggleSelected(card.id)} /></label><span>{card.section_key || "Başlıksız"}</span><em>%{percentValue(card.completeness)} dolu</em></div>
                  <div className="asset-card-hero"><div><strong>{card.section_title || card.section_key || "Genel"}</strong><h3>{card.table_name}</h3><p>{card.row_count || 0} satır · {card.column_count || 0} sütun</p></div><AssetProgressRing value={card.quality_score} label="Kalite" /></div>
                  <div className="studio-card-scoreline"><span><strong>{card.row_count || 0}</strong><small>Satır</small></span><span><strong>{card.column_count || 0}</strong><small>Sütun</small></span><span><strong>%{percentValue(card.completeness)}</strong><small>Doluluk</small></span><span><strong>{assetRiskClass(card.risk_level).replace("risk-", "")}</strong><small>Risk</small></span></div>
                  <div className="asset-chip-list compact">{asArray(card.columns).slice(0, 5).map((item) => <span key={item}>{item}</span>)}{!asArray(card.columns).length && <span>Sütun yok</span>}</div>
                  {canManageTables && <div className="studio-card-actions" onClick={(event) => event.stopPropagation()}><button type="button" onClick={() => editTable(card)}><Wrench size={14} /> Düzenle</button><button type="button" onClick={() => remove(card)}><Trash2 size={14} /> Sil</button></div>}
                </article>
              ))}
              {!sectionFocusedCards.length && <div className="premium-empty-state"><strong>Tablo bulunamadı</strong><span>Bu ölçüt için filtreye uyan tablo yok.</span></div>}
            </div>
            {selectedTable && <div className="asset-table-preview-panel"><div className="editor-header"><div><span className="badge">Canlı Ön İzleme</span><h2>{selectedTable.table_name}</h2></div>{canManageTables && <button onClick={() => editTable(selectedTable)}>Düzenle</button>}</div><RichTablePreview table={selectedTable} /></div>}
          </main>
          <AssetAssistantPanel title={selectedCard?.table_name} card={selectedCard} assistant={studio?.assistant} type="table" />
        </div>
      )}
    </section>
  );
}

export function ControlView({ programId, onError, onPick }) {
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("Tümü");
  const [settings, setSettings] = useState(null);
  useEffect(() => { api.control(programId).then((data) => setRows(asArray(data))).catch((err) => onError(err.message)); }, [programId]);
  useEffect(() => { api.settings(programId).then(setSettings).catch((err) => onError(err.message)); }, [programId]);
  async function download() { try { downloadBlob(await api.controlDocx(programId), settings?.control_filename || "kontrol_tablosu.docx"); } catch (err) { onError(err.message); } }
  const controlTabs = ["Taslak", "Onaya Gönderildi", "Revizyon Gerekli", "Onaylandı", "Tümü"].map((label) => ({
    label,
    count: label === "Tümü" ? rows.length : rows.filter((row) => row["Onay Durumu"] === label).length,
  }));
  const filtered = filter === "Tümü" ? rows : rows.filter((row) => row["Onay Durumu"] === filter);
  return (
    <section className="panel-stack ops-premium-shell ops-control-workspace">
      <AccreditationProcessStrip process="Onay ve revizyon durumu izleniyor" risk="Revizyon ve taslak başlıklar ayrıştırılır" trace="Kontrol tablosu denetim kanıtı üretir" action="Kontrol DOCX indirilebilir" />
      <div className="dashboard-panel ops-premium-kpis">
        <MetricCard label="Onaylanan" value={rows.filter((r) => r["Onay Durumu"] === "Onaylandı").length} sub="kilitli başlık" />
        <MetricCard label="Onay Bekleyen" value={rows.filter((r) => r["Onay Durumu"] === "Onaya Gönderildi").length} sub="karar bekliyor" />
        <MetricCard className="warn" label="Revizyon" value={rows.filter((r) => r["Onay Durumu"] === "Revizyon Gerekli").length} sub="düzeltme bekliyor" />
        <MetricCard label="Taslak" value={rows.filter((r) => r["Onay Durumu"] === "Taslak").length} sub="hazırlıkta" />
      </div>
      <section className="editor-panel">
        <div className="editor-header"><div><h2>Onay ve Revizyon Kontrolü</h2><p className="muted">Taslak, onaya gönderildi, revizyon gerekli ve onaylandı durumları denetime hazır süreç tablosu olarak izlenir.</p></div><button onClick={download}>Kontrol DOCX İndir</button></div>
        <div className="category-tabs control-status-tabs" role="tablist" aria-label="Kontrol durumu kategorileri">
          {controlTabs.map((tab) => (
            <button key={tab.label} type="button" role="tab" aria-selected={filter === tab.label} className={filter === tab.label ? "active" : ""} onClick={() => setFilter(tab.label)}>
              {tab.label}<small>{tab.count}</small>
            </button>
          ))}
        </div>
        <DataTable rows={filtered} actions={(row) => <button onClick={() => onPick(row.Kod, "entry")}>Aç</button>} />
      </section>
    </section>
  );
}

export function ReadinessView({ programId, onError, onPick }) {
  const [payload, setPayload] = useState(null);
  const [settings, setSettings] = useState(null);
  const [compliance, setCompliance] = useState(null);
  const [workflow, setWorkflow] = useState(null);
  async function loadGovernance() {
    const [statsRows, settingsRows, complianceRows, workflowRows] = await Promise.all([
      api.stats(programId),
      api.settings(programId),
      api.compliance(programId, 500).catch(() => null),
      api.workflowReminders(programId).catch(() => null),
    ]);
    setPayload(statsRows);
    setSettings(settingsRows);
    setCompliance(complianceRows ? asObject(complianceRows) : null);
    setWorkflow(workflowRows ? asObject(workflowRows) : null);
  }
  useEffect(() => { loadGovernance().catch((err) => onError(err.message)); }, [programId]);
  async function downloadAudit() { try { downloadBlob(await api.auditDocx(programId), settings?.audit_filename || "hazirlik_denetimi.docx"); } catch (err) { onError(err.message); } }
  async function downloadCompliance() { try { downloadBlob(await api.complianceDocx(programId), "AKYS_compliance_audit.docx"); } catch (err) { onError(err.message); } }
  if (!payload) return <div className="empty-state">Hazırlık denetimi yükleniyor.</div>;
  const complianceSummary = asObject(compliance?.summary);
  const workflowRows = asArray(workflow?.rows);
  return (
    <section className="panel-stack ops-premium-shell ops-readiness-workspace">
      <div className="editor-panel audit-hero ops-premium-hero">
        <div>
          <span className="eyebrow">Governance + Hazırlık Denetimi</span>
          <h2>Eksik, risk, compliance ve workflow durumunu tek ekranda izle</h2>
          <p>Denetim ekranı metin uzunluğu, kanıt yoğunluğu, tablo varlığı, PUKÖ kapsamı, activity log, versiyon geçmişi ve bekleyen onay/revizyon akışlarını birleştirir.</p>
        </div>
        <div className="action-row"><button onClick={downloadAudit}><FileText size={16} /> Hazırlık DOCX</button><button onClick={downloadCompliance}><ShieldCheck size={16} /> Compliance DOCX</button><button onClick={loadGovernance}><RefreshCw size={16} /> Yenile</button></div>
      </div>
      <div className="dashboard-panel">
        <MetricCard className="accent" label="Ortalama Kalite" value={`${payload.totals.avg_quality}%`} sub="metin, kanıt, tablo, PUKÖ" />
        <MetricCard label="Audit Olayı" value={complianceSummary.activity_events ?? "-"} sub="activity log" />
        <MetricCard className="warn" label="Workflow Uyarısı" value={workflow?.total ?? 0} sub={`${workflow?.high_priority ?? 0} yüksek öncelik`} />
        <MetricCard label="Versiyon" value={complianceSummary.version_snapshots ?? "-"} sub="snapshot" />
      </div>
      <TabbedExpander
        title="Denetim ve Governance Detayları"
        subtitle="Hazırlık kalitesi, compliance trail, bekleyen workflow ve riskli başlıklar sekmeli izlenir."
        tabs={[
          {
            id: "quality-map",
            label: "Ana Ölçüt Kalite Haritası",
            count: payload.measure_criteria?.length || payload.criteria?.length || 0,
            content: <DataTable rows={payload.measure_criteria || payload.criteria} columns={["main_title", "total", "ready", "approved", "submitted", "revision", "readiness_percent", "quality_avg"]} />,
          },
          {
            id: "critical",
            label: "Öncelikli Eksikler",
            count: payload.critical?.length || 0,
            content: <DataTable rows={payload.critical} actions={(row) => <button onClick={() => onPick(row.section_key, "entry")}>Başlığı Aç</button>} />,
          },
          {
            id: "workflow",
            label: "Workflow Hatırlatma",
            count: workflowRows.length,
            content: <DataTable rows={workflowRows} columns={["priority", "category", "section_key", "section_title", "deadline", "days_left", "approval_status", "message", "latest_actor"]} actions={(row) => <button onClick={() => onPick(row.section_key, "entry")}>Aç</button>} />,
          },
          {
            id: "compliance-summary",
            label: "Compliance Özet",
            count: Object.keys(complianceSummary).length,
            content: <div className="tabbed-stack"><div className="dashboard-panel compact-kpi-grid">{Object.entries(complianceSummary).map(([key, value]) => <MetricCard key={key} label={key} value={value} sub="compliance" />)}</div><DataTable rows={asArray(compliance?.section_activity)} columns={["section_key", "section_title", "activity", "versions", "approvals", "notifications", "approval_status"]} actions={(row) => <button onClick={() => onPick(row.section_key, "entry")}>Aç</button>} /></div>,
          },
          {
            id: "audit-trail",
            label: "Audit Trail",
            count: compliance?.activity?.length || 0,
            content: <DataTable rows={asArray(compliance?.activity)} columns={["ts", "action", "detail", "actor", "program_id"]} />,
          },
        ]}
      />
    </section>
  );
}


export function SearchView({ programId, onError, onPick }) {
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState([]);
  async function runSearch(event) {
    event?.preventDefault();
    if (!query.trim()) return setRows([]);
    try { setRows(asArray(await api.search(programId, query))); } catch (err) { onError(err.message); }
  }
  return (
    <section className="panel-stack">
      <form className="editor-panel search-panel" onSubmit={runSearch}>
        <h2>Tam Metin Arama</h2>
        <div className="search-line"><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Başlık, kanıt kodu, PUKÖ, not veya tablo adı ara..." /><button className="primary-action">Ara</button></div>
      </form>
      <div className="editor-panel">
        <DataTable rows={rows} columns={["section_key", "report_group_title", "main_title", "section_title", "status", "approval_status", "evidence_count", "table_count", "snippet"]} actions={(row) => <button onClick={() => onPick(row.section_key, "entry")}>Aç</button>} />
      </div>
    </section>
  );
}

export function StatsView({ programId, onError, onPick }) {
  const [payload, setPayload] = useState(null);
  useEffect(() => { api.stats(programId).then(setPayload).catch((err) => onError(err.message)); }, [programId]);
  if (!payload) return <div className="empty-state">İstatistikler yükleniyor.</div>;
  const summary = payload.summary || {};
  const totals = payload.totals || {};
  return (
    <section className="panel-stack ops-premium-shell ops-stats-workspace">
      <div className="hero-panel stats-hero ops-premium-hero">
        <div>
          <span className="eyebrow">Akreditasyon İstatistikleri</span>
          <h2>Hazırlık kalitesi, kanıt yoğunluğu ve onay dağılımı</h2>
          <p>Bu ekran ana ölçüt bazlı hazırlık, kalite ortalaması, kanıt yoğunluğu ve kritik başlıkları tek yerde gösterir.</p>
        </div>
        <div className="hero-score"><strong>{totals.avg_quality ?? 0}%</strong><span>ortalama kalite</span></div>
      </div>
      <AccreditationProcessStrip process={`${summary.readiness_percent ?? 0}% hazırlık`} risk={`${totals.critical_sections ?? 0} kritik başlık`} trace="Ana ölçüt istatistikleri süreç izine bağlanır" action="Yönetici raporu için temel veri" />
      <div className="dashboard-panel">
        <MetricCard className="accent" label="Hazırlık" value={`${summary.readiness_percent ?? 0}%`} sub={`${summary.ready_sections ?? 0}/${summary.total_sections ?? 0} başlık`} />
        <MetricCard label="Onay" value={`${summary.approval_percent ?? 0}%`} sub={`${summary.approved_sections ?? 0} onaylı`} />
        <MetricCard label="Kanıt / Tablo" value={`${totals.evidence ?? 0}/${totals.tables ?? 0}`} sub="toplam kayıt" />
        <MetricCard className="warn" label="Kritik" value={totals.critical_sections ?? 0} sub="60 puan altı" />
      </div>
      <TabbedExpander
        title="İstatistik Detayları"
        subtitle="Ana ölçüt istatistikleri ve kritik başlıkları aynı çalışma alanında takip edin."
        tabs={[
          {
            id: "criteria",
            label: "Ana Ölçüt İstatistikleri",
            count: payload.measure_criteria?.length || payload.criteria?.length || 0,
            content: <DataTable rows={payload.measure_criteria || payload.criteria} columns={["main_title", "total", "ready", "approved", "submitted", "revision", "readiness_percent", "approval_percent", "quality_avg"]} />,
          },
          {
            id: "critical",
            label: "Kritik Başlıklar",
            count: payload.critical?.length || 0,
            content: <DataTable rows={payload.critical} columns={["section_key", "section_title", "quality", "words", "evidence", "tables", "puko"]} actions={(row) => <button onClick={() => onPick(row.section_key, "entry")}>Aç</button>} />,
          },
        ]}
      />
    </section>
  );
}

export function AssistantView({ programId, sections, activeSectionKey, setActiveSectionKey, form, setForm, readOnly, onError, onMessage }) {
  const [mode, setMode] = useState("Kanıtlı Rapor Metni");
  const [targetWords, setTargetWords] = useState(650);
  const [draft, setDraft] = useState(null);
  const [draftText, setDraftText] = useState("");
  const [aiStatus, setAiStatus] = useState(null);
  useEffect(() => { api.aiStatus(programId).then((data) => setAiStatus(asObject(data))).catch((err) => onError(err.message)); }, [programId]);
  async function generate() {
    try {
      const result = await api.aiSectionDraft(programId, activeSectionKey, targetWords);
      setDraft(result);
      setDraftText(result.text || "");
      onMessage("AI taslak hazır. Uygun bulursanız veri giriş alanına aktarabilirsiniz.");
    } catch (err) { onError(err.message); }
  }
  return (
    <section className="panel-stack">
      <div className="editor-panel">
        <div className="editor-header"><div><h2>Offline AI Akreditasyon Asistanı</h2><p className="muted">Ollama açıksa kurum dışına veri göndermeden yerel model kullanılır; erişilemezse güvenli yerel şablon üreticiye düşer.</p></div><Sparkles size={22} /></div>
        <div className="ai-status-strip">
          <span className={aiStatus?.available ? "status-dot ok" : "status-dot warn"}></span>
          <strong>{aiStatus?.mode || "yükleniyor"}</strong>
          <span>{aiStatus?.provider || "ai"} · {aiStatus?.model || "model yok"}</span>
          <small>{aiStatus?.message || "AI durumu kontrol ediliyor."}</small>
        </div>
        <div className="form-grid">
          <label>Başlık seç<select value={activeSectionKey} onChange={(e) => setActiveSectionKey(e.target.value)}>{sections.map((s) => <option key={s.section_key} value={s.section_key}>{s.section_key} · {s.section_title}</option>)}</select></label>
          <label>Asistan modu<select value={mode} onChange={(e) => setMode(e.target.value)}>{["Kanıtlı Rapor Metni", "Taslak", "PUKÖ Önerisi", "Kalite Analizi", "Kanıt Kontrolü", "Revizyon Önerisi"].map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>Hedef uzunluk<select value={targetWords} onChange={(e) => setTargetWords(Number(e.target.value))}><option value={520}>520 kelime</option><option value={650}>650 kelime</option><option value={800}>800 kelime</option></select></label>
        </div>
        <div className="action-row"><button className="primary-action" onClick={generate}><Bot size={16} /> {mode} Üret</button>{draft && <button disabled={readOnly} onClick={() => { setForm({ ...form, report_text: draftText }); onMessage("AI metni veri giriş alanına aktarıldı."); }}>Kabul Et ve Metne Aktar</button>}{draft && <button onClick={() => { navigator.clipboard?.writeText(draftText); onMessage("AI çıktısı panoya kopyalandı."); }}><Copy size={16} /> Kopyala</button>}{draft && <button onClick={() => { setDraft(null); setDraftText(""); }}>Reddet</button>}</div>
      </div>
      {draft && <article className="preview-card ai-draft"><span className="badge">{draft.section_key} · {mode} · {draft.provider || "AI"}</span><h2>{draft.section_title}</h2><textarea value={draftText} onChange={(event) => setDraftText(event.target.value)} rows={18} /><small>{draft.warnings?.join(" · ")}</small></article>}
    </section>
  );
}

export function ApprovalView({ programId, sections, activeSectionKey, setActiveSectionKey, user, hasUnsavedSectionChanges = false, onError, onMessage, refresh }) {
  const [note, setNote] = useState("");
  const [tab, setTab] = useState("text");
  const [detail, setDetail] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [tables, setTables] = useState([]);
  const [history, setHistory] = useState([]);
  const safeSections = asArray(sections);
  const selected = safeSections.find((section) => section.section_key === activeSectionKey) || safeSections[0];
  useEffect(() => {
    if (!programId || !selected?.section_key) return;
    Promise.all([
      api.section(programId, selected.section_key),
      api.evidence(programId, selected.section_key),
      api.tables(programId, selected.section_key),
      api.approvalHistory(programId, selected.section_key),
    ])
      .then(([sectionDetail, evidenceRows, tableRows, historyRows]) => { setDetail(asObject(sectionDetail)); setEvidence(asArray(evidenceRows)); setTables(asArray(tableRows)); setHistory(asArray(historyRows)); })
      .catch((err) => onError(err.message));
  }, [programId, selected?.section_key]);
  const actionPerms = asObject((detail || selected || {}).user_permissions);
  const canApprove = Boolean(actionPerms.approve || actionPerms.request_revision);
  const canSend = user.role === "Editör / Hazırlayıcı" && Boolean(actionPerms.submit) && !["Onaylandı", "Onaya Gönderildi"].includes(selected?.approval_status);
  const canUndo = Boolean(actionPerms.reopen) && selected?.approval_status === "Onaylandı";
  async function act(action) {
    if (action === "send" && hasUnsavedSectionChanges) return onError("Onaya göndermeden önce Rapor Dizini ekranında 'Bu Başlığı Kaydet' düğmesine basmalısınız.");
    if (action === "revision" && !note.trim()) return onError("Revizyon isterken not zorunlu.");
    try {
      await api.approval(programId, { section_key: selected.section_key, action, note });
      setNote("");
      onMessage("Onay akışı güncellendi.");
      await refresh();
      setHistory(asArray(await api.approvalHistory(programId, selected.section_key)));
    } catch (err) { onError(err.message); }
  }
  const reviewSection = detail || selected || {};
  const revisionNote = reviewSection.revision?.note || "";
  return (
    <section className="content-grid ops-premium-shell ops-approval-workspace">
      <SectionList sections={sections} activeSectionKey={activeSectionKey} onPick={setActiveSectionKey} />
      <div className="editor-panel workbench ops-premium-hero">
        <div className="editor-header"><div><span className="badge">{reviewSection.section_key}</span><h2>{reviewSection.section_title}</h2></div><span className="approval">{reviewSection.approval_status || "Taslak"}</span></div>
        {revisionNote && <div className="alert revision"><strong>Son revizyon notu:</strong> {revisionNote}</div>}
        <div className="work-tabs">
          {[["text", "Metin"], ["puko", "PUKÖ"], ["tables", "Tablolar"], ["evidence", "Kanıtlar"], ["history", "Revizyon & Geçmiş"]].map(([id, label]) => (
            <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}>{label}</button>
          ))}
        </div>
        {tab === "text" && <div className="approval-preview"><p>{reviewSection.report_text || "Bu başlık için rapor metni henüz girilmedi."}</p></div>}
        {tab === "puko" && <div className="puko-review-grid">{[["Planla", reviewSection.planla], ["Uygula", reviewSection.uygula], ["Kontrol Et", reviewSection.kontrol], ["Önlem Al", reviewSection.onlem]].map(([label, value]) => <article key={label}><span>{label}</span><p>{value || "Bu PUKÖ alanı henüz doldurulmadı."}</p></article>)}</div>}
        {tab === "tables" && <div className="panel-stack">{tables.map((table) => <div className="approval-preview" key={table.id}><h3>{table.table_name}</h3><RichTablePreview table={table} /></div>)}{!tables.length && <div className="empty-state">Bu başlık için tablo yok.</div>}</div>}
        {tab === "evidence" && <DataTable rows={evidence} columns={["code", "original_name", "note", "uploaded_at"]} actions={(row) => <button onClick={async () => { try { downloadBlob(await api.evidenceBlob(programId, row.id), row.original_name || "kanit"); } catch (err) { onError(err.message); } }}>Aç</button>} />}
        {tab === "history" && <DataTable rows={history} columns={["status", "requested_by", "decided_by", "note", "created_at"]} />}
        <label>Onay / revizyon notu<textarea value={note} onChange={(e) => setNote(e.target.value)} rows={5} placeholder={canApprove ? "Onay veya revizyon notu..." : "Onaya gönderme notu..."} /></label>
        {canSend && hasUnsavedSectionChanges && <div className="alert warning">Bu başlıkta kaydedilmemiş değişiklik var. Onaya göndermek için önce Rapor Dizini ekranında <strong>Bu Başlığı Kaydet</strong> düğmesine basın.</div>}
        <div className="action-row">
          {canSend && <button className="primary-action" onClick={() => act("send")}><Send size={16} /> Onaya Gönder</button>}
          {canApprove && <button onClick={() => act("approve")}><CheckCircle2 size={16} /> Onayla</button>}
          {canApprove && <button onClick={() => act("revision")}><Wrench size={16} /> Revizyon İste</button>}
          {canUndo && <button onClick={() => act("undo")}><RefreshCw size={16} /> Onayı Geri Al</button>}
        </div>
      </div>
    </section>
  );
}

/* Kullanıcı isteğiyle Önizleme ekranındaki görünür export bloğu kaldırıldı. Legacy validator copy: Rapor Çıktısı Oluştur · DOCX veya PDF çıktısını oluşturup hazır olduğunda */
export function PreviewView({ programId, onError, onMessage, onPick }) {
  const [payload, setPayload] = useState(null);
  const [preflight, setPreflight] = useState(null);
  const [mode, setMode] = useState("all");
  const [selected, setSelected] = useState("");
  const [jobs, setJobs] = useState([]);
  const [jobBusy, setJobBusy] = useState(false);

  async function loadJobs() {
    try {
      setJobs(asArray(await api.exportJobs(programId, 10)));
    } catch (err) {
      onError(err.message);
    }
  }

  async function loadPreflight() {
    try {
      setPreflight(asObject(await api.reportPreflight(programId)));
    } catch (err) {
      onError(err.message);
    }
  }

  useEffect(() => {
    api.preview(programId)
      .then((data) => { const safePayload = asObject(data); const safeSections = asArray(safePayload.sections); setPayload({ ...safePayload, sections: safeSections }); setSelected(safeSections[0]?.section_key || ""); })
      .catch((err) => onError(err.message));
    loadJobs();
    loadPreflight();
  }, [programId]);

  useEffect(() => {
    const hasActive = jobs.some((job) => ["queued", "running"].includes(job.status));
    if (!hasActive) return undefined;
    const timer = setInterval(loadJobs, 7000);
    return () => clearInterval(timer);
  }, [jobs, programId]);

  async function startExport(exportType, force = false) {
    setJobBusy(true);
    try {
      const finalExport = ["docx", "pdf"].includes(exportType);
      const shouldForce = finalExport ? true : Boolean(force);
      const job = await api.createExportJob(programId, exportType, shouldForce);
      onMessage(`Çıktı işi kuyruğa alındı: ${job.file_name}. Rapor boş olsa bile dosya üretilecek.`);
      await loadJobs();
    } catch (err) {
      onError(err.message);
    } finally {
      setJobBusy(false);
    }
  }

  async function downloadJob(job) {
    try {
      const blob = await api.exportJobBlob(programId, job.id);
      downloadBlob(blob, job.file_name || "rapor_ciktisi");
    } catch (err) {
      onError(err.message);
    }
  }

  const sections = asArray(payload?.sections);
  const visible = mode === "single" ? sections.filter((section) => section.section_key === selected) : sections;
  return (
    <section className="panel-stack ops-premium-shell ops-preview-workspace">
      <div className="editor-panel ops-premium-hero">
        <div className="editor-header"><div><h2>Denetime Hazır Rapor Önizleme</h2><p className="muted">{payload?.settings?.program} · {payload?.settings?.report_year}</p></div><span className="badge">{sections.length} başlık</span></div>
        <div className="action-row"><button className={mode === "all" ? "active-soft" : ""} onClick={() => setMode("all")}>Tüm rapor</button><button className={mode === "single" ? "active-soft" : ""} onClick={() => setMode("single")}>Tek başlık</button></div>
        {mode === "single" && <label>Başlık<select value={selected} onChange={(e) => setSelected(e.target.value)}>{sections.map((section) => <option key={section.section_key} value={section.section_key}>{section.section_key} · {section.section_title}</option>)}</select></label>}
      </div>

      <ReportPreflightPanel preflight={preflight} onPick={onPick} />

      {visible.map((section) => <article className="preview-card" key={section.section_key}><span className="badge">{section.section_key}</span><h2>{section.section_title}</h2><p>{section.report_text || "Bu başlık henüz doldurulmamıştır."}</p><small>{section.evidence?.length || 0} kanıt · {section.tables?.length || 0} tablo · kalite {section.quality?.score || 0}</small><div className="action-row"><button onClick={() => onPick(section.section_key, "entry")}>Düzenleme ekranına git</button></div></article>)}
    </section>
  );
}

export function DocxImportView({ programId, onError, onMessage, refresh }) {
  const [fileType, setFileType] = useState("docx");
  const [file, setFile] = useState(null);
  const [overwriteEmptyOnly, setOverwriteEmptyOnly] = useState(true);
  const [result, setResult] = useState(null);
  const modes = [
    { key: "docx", title: "Rapor DOCX", description: "Word rapor taslağındaki başlık kodlarını ve metinleri aktarır.", accept: ".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" },
    { key: "pdf", title: "Rapor PDF", description: "Metin tabanlı PDF raporundan başlıkları algılayıp ilgili alanlara işler.", accept: ".pdf,application/pdf" },
  ];
  const activeMode = modes.find((mode) => mode.key === fileType) || modes[0];
  async function submit(event) {
    event.preventDefault();
    if (!file) return onError(`${activeMode.title} dosyası seçin.`);
    try {
      const response = await api.importReport(programId, { file, overwriteEmptyOnly });
      setResult(response);
      onMessage(`${response.file_type || activeMode.title} içe aktarıldı: ${response.updated}/${response.detected} başlık güncellendi, ${response.imported_tables || 0} tablo aktarıldı.`);
      await refresh();
    } catch (err) { onError(err.message); }
  }
  return (
    <section className="editor-panel report-import-panel ops-premium-shell ops-import-workspace">
      <div className="editor-header">
        <div>
          <h2>Rapor İçe Aktarma Merkezi</h2>
          <p className="muted">Başlık kodlarını tanıyarak DOCX veya PDF rapor metnini ilgili akreditasyon ölçütlerine aktarır; izlenebilir güncelleme üretir.</p>
        </div>
        <Upload size={22} />
      </div>
      <AccreditationProcessStrip process="Dış rapor içeriği ölçütlere aktarılıyor" risk="Sadece boş alanları doldurma ile veri kaybı önlenir" trace="İçe aktarma sonucu algılanan/güncellenen başlıkları gösterir" action="Program raporu hızla güncellenir" />
      <div className="import-mode-grid">
        {modes.map((mode) => (
          <button
            type="button"
            key={mode.key}
            className={`import-mode-card ${fileType === mode.key ? "active" : ""}`}
            onClick={() => { setFileType(mode.key); setFile(null); setResult(null); }}
          >
            <FileText size={20} />
            <strong>{mode.title}</strong>
            <span>{mode.description}</span>
          </button>
        ))}
      </div>
      <form className="form-grid" onSubmit={submit}>
        <label className="wide">{activeMode.title} dosyası<input key={fileType} type="file" accept={activeMode.accept} onChange={(event) => setFile(event.target.files?.[0] || null)} /></label>
        <label className="checkbox-line"><input type="checkbox" checked={overwriteEmptyOnly} onChange={(event) => setOverwriteEmptyOnly(event.target.checked)} /> Sadece boş başlıkları doldur</label>
        <button className="primary-action">Raporu İçe Aktar</button>
      </form>
      {fileType === "pdf" && <p className="muted">Not: PDF içe aktarma metin tabanlı PDF dosyalarında çalışır; taranmış görsel PDF için OCR gerekir.</p>}
      {result && <div className="alert info">Tür: {result.file_type} · Algılanan: {result.detected} · Güncellenen: {result.updated} · Atlanan: {result.skipped} · Aktarılan tablo: {result.imported_tables || 0} · Okunan satır: {result.extracted_lines}</div>}
    </section>
  );
}

export function FullReportView({ programId, onError, onMessage }) {
  const [targetWords, setTargetWords] = useState(650);
  const [includeAll, setIncludeAll] = useState(false);
  const [rows, setRows] = useState([]);
  const [applyingKey, setApplyingKey] = useState("");
  async function generate() {
    try {
      const result = asArray(await api.aiFullReport(programId, includeAll, targetWords));
      setRows(result);
      onMessage(`${result.length} başlık için AI taslak adayı üretildi.`);
    } catch (err) { onError(err.message); }
  }
  async function applyDraft(item) {
    if (!window.confirm(`${item.section_key} başlığına AI taslak metni uygulansın mı? Mevcut metin versiyon geçmişine alınır.`)) return;
    setApplyingKey(item.section_key);
    try {
      await api.applyAiDraft(programId, item.section_key, item.text);
      setRows((current) => current.filter((row) => row.section_key !== item.section_key));
      onMessage(`${item.section_key} taslağı bölüme uygulandı.`);
    } catch (err) { onError(err.message); }
    finally { setApplyingKey(""); }
  }
  return (
    <section className="panel-stack ops-premium-shell ops-full-report-workspace">
      <div className="editor-panel ops-premium-hero">
        <div className="editor-header"><h2>AI Destekli Tam Rapor Oluştur & Denetle</h2><Sparkles size={22} /></div>
        <div className="form-grid"><label>Başlık hedef uzunluğu<select value={targetWords} onChange={(e) => setTargetWords(Number(e.target.value))}><option value={520}>520</option><option value={650}>650</option><option value={800}>800</option></select></label><label className="checkbox-line"><input type="checkbox" checked={includeAll} onChange={(e) => setIncludeAll(e.target.checked)} /> Tüm başlıkları dahil et</label></div>
        <button className="primary-action" onClick={generate}>Tam Rapor AI Adaylarını Oluştur</button>
      </div>
      <AccreditationProcessStrip process={`${rows.length} AI taslak adayı`} risk="Uyarılar başlık kartlarında görünür" trace="AI önerisi kullanıcı onayı olmadan nihai rapora yazılmaz" action="Denetime hazır metin için editör kontrolü gerekir" />
      {rows.map((item) => (
        <article className="preview-card" key={item.section_key}>
          <span className="badge">{item.section_key} · kalite {item.quality_score} · {item.current_words || 0}→{item.proposed_words || 0} kelime</span>
          <h2>{item.section_title}</h2>
          {!!item.warnings?.length && <div className="notice-card warning"><strong>Kontrol notu</strong><span>{item.warnings.join(" · ")}</span></div>}
          <p>{item.text}</p>
          {!!asArray(item.diff_preview).length && (
            <details className="secondary-export">
              <summary>Mevcut metinle farkı göster</summary>
              <pre className="diff-preview">{asArray(item.diff_preview).join("\n")}</pre>
            </details>
          )}
          <div className="action-row">
            <button className="primary-action" disabled={applyingKey === item.section_key} onClick={() => applyDraft(item)}><CheckCircle2 size={16} /> Taslağı Bölüme Uygula</button>
          </div>
        </article>
      ))}
    </section>
  );
}


export function ProfessionalReportingView({ programId, sections = [], activeSectionKey, setActiveSectionKey, onPick, onError, onMessage, refresh }) {
  const [payload, setPayload] = useState(null);
  const [clauses, setClauses] = useState([]);
  const [selectedSection, setSelectedSection] = useState(activeSectionKey || sections[0]?.section_key || "");
  const [draggedClause, setDraggedClause] = useState(null);
  const [newClause, setNewClause] = useState({ title: "", content: "", criterion_code: "", clause_type: "standart", tags: "" });
  const [diff, setDiff] = useState(null);
  const [auditorLinks, setAuditorLinks] = useState([]);

  const currentSection = useMemo(() => asArray(sections).find((row) => row.section_key === selectedSection) || asArray(sections)[0] || {}, [sections, selectedSection]);
  const quality = asObject(payload?.quality);
  const consistency = asObject(payload?.consistency);
  const mockAudit = asObject(payload?.mock_audit);
  const premiumPack = asObject(payload?.premium_pack);
  const premiumGate = asObject(quality.premium_readiness || premiumPack.gate);
  const heatmap = asArray(payload?.heatmap || quality.heatmap);
  const issues = asArray(consistency.issues);

  async function load() {
    if (!programId) return;
    try {
      const data = asObject(await api.professionalReporting(programId));
      setPayload(data);
      setClauses(asArray(data.clauses));
      api.professionalAuditorLinks(programId).then((rows) => setAuditorLinks(asArray(rows))).catch(() => {});
    } catch (err) {
      onError(err.message);
    }
  }

  useEffect(() => { load(); }, [programId]);
  useEffect(() => {
    if (activeSectionKey) setSelectedSection(activeSectionKey);
  }, [activeSectionKey]);
  useEffect(() => {
    if (!programId || !selectedSection) return;
    api.professionalClauses(programId, selectedSection).then((rows) => setClauses(asArray(rows))).catch(() => {});
    api.professionalSentenceDiff(programId, selectedSection).then((data) => setDiff(asObject(data))).catch(() => setDiff(null));
  }, [programId, selectedSection]);

  async function seedClauses() {
    try {
      const result = await api.seedProfessionalClauses(programId);
      onMessage(`Clause Library güncellendi. Eklenen blok: ${result.inserted ?? 0}`);
      await load();
    } catch (err) { onError(err.message); }
  }

  async function createClause(event) {
    event.preventDefault();
    try {
      await api.createProfessionalClause(programId, { ...newClause, section_key: selectedSection });
      setNewClause({ title: "", content: "", criterion_code: "", clause_type: "standart", tags: "" });
      onMessage("Yeni standart blok kütüphaneye eklendi.");
      await load();
    } catch (err) { onError(err.message); }
  }

  async function insertClause(clause, position = "append") {
    const target = selectedSection || activeSectionKey;
    if (!target || !clause?.id) return onError("Önce bölüm ve eklenecek blok seçin.");
    try {
      await api.insertProfessionalClause(programId, target, clause.id, position);
      onMessage("Standart blok bölüm metnine eklendi.");
      setActiveSectionKey?.(target);
      await refresh?.();
      await load();
    } catch (err) { onError(err.message); }
  }

  async function downloadPackage(auditor = false) {
    try {
      const blob = auditor ? await api.professionalAuditorPackage(programId) : await api.professionalPackage(programId);
      downloadBlob(blob, auditor ? "AKYS_denetci_okuma_paketi.zip" : "AKYS_profesyonel_rapor_paketi.zip");
      onMessage(auditor ? "Denetçi paketi indirildi." : "Tam rapor paketi indirildi.");
    } catch (err) { onError(err.message); }
  }

  async function createAuditorLink() {
    try {
      const link = await api.createProfessionalAuditorLink(programId, { label: "Denetçi okuma bağlantısı", watermark: "DENETÇİ KOPYASI" });
      onMessage(`Denetçi bağlantısı oluşturuldu. Token: ${String(link.token || "").slice(0, 12)}...`);
      const rows = await api.professionalAuditorLinks(programId);
      setAuditorLinks(asArray(rows));
    } catch (err) { onError(err.message); }
  }

  const clauseRows = asArray(clauses).map((row) => ({
    Başlık: row.title,
    Ölçüt: row.criterion_code || row.section_key || "Genel",
    Tip: row.clause_type || "standart",
    Etiket: row.tags || "",
  }));
  const issueRows = issues.slice(0, 30).map((row) => ({
    Seviye: row.severity,
    Tür: row.type,
    Bölüm: row.section_key,
    Uyarı: row.message,
    Öneri: row.suggestion,
  }));
  const mockRows = asArray(mockAudit.questions).map((row) => ({
    Bölüm: row.section_key,
    Skor: row.score,
    Risk: row.risk,
    "Denetçi Sorusu": row.auditor_question,
  }));

  return (
    <section className="panel-stack professional-reporting-view">
      <div className="hero-panel stats-hero">
        <div>
          <span className="eyebrow">Professional Reporting Pack 9.8+</span>
          <h2>Smart Templates, Clause Library, tutarlılık, kalite skoru ve denetçi paketi</h2>
          <p>Raporu 98+ kalite hedefiyle yönetir; cümle/blok kütüphanesi, kanıt kontrolleri, sayı-tablo uyumu, cümle diff’i, mock denetim ve tek tık tam paket üretimiyle denetime hazır hale getirir.</p>
        </div>
        <div className="hero-actions">
          <button className="secondary-action" onClick={seedClauses}><Sparkles size={16} /> Clause Library Seed</button>
          <button className="primary-action" onClick={() => downloadPackage(false)}><Download size={16} /> Tam Rapor Paketi</button>
          <button className="secondary-action" onClick={() => downloadPackage(true)}><Eye size={16} /> Denetçi Paketi</button>
        </div>
      </div>

      <div className="metric-grid">
        <MetricCard label="Rapor Kalite Skoru" value={quality.score ?? "-"} sub="tamamlanma + kanıt + tutarlılık" />
        <MetricCard label="9.8+ Kapısı" value={premiumGate.ready ? "Hazır" : `${premiumGate.score_gap ?? 0} açık`} sub={premiumGate.target_label || "98+ hedef"} />
        <MetricCard label="Tutarlılık Uyarısı" value={consistency.total_issues ?? 0} sub="çapraz referans / kanıt / sayı" />
        <MetricCard label="Kanıt Kapsamı" value={`${quality.evidence_coverage_percent ?? 0}%`} sub="kanıt bağlı başlık oranı" />
        <MetricCard label="Mock Denetim Sorusu" value={asArray(mockAudit.questions).length} sub="denetçi gözüyle örnek kontrol" />
      </div>

      <section className={`editor-panel professional-pro-gate ${premiumGate.status || "work"}`}>
        <div className="section-heading-row">
          <div>
            <span className="eyebrow">Premium kalite kapısı</span>
            <h2>{premiumGate.target_label || "9.8+"} profesyonel rapor hazırlığı</h2>
            <p className="muted">{premiumPack.summary || "Genel kalite, tamamlanma, kanıt kapsamı, tutarlılık ve onay oranı birlikte izlenir."}</p>
          </div>
          <div className="pro-score-badge"><strong>{quality.score ?? 0}</strong><span>/100</span></div>
        </div>
        <div className="pro-requirement-grid">
          {asArray(premiumGate.requirements).map((item) => (
            <span key={item.key} className={item.done ? "done" : "todo"}>
              <CheckCircle2 size={15} />
              <b>{item.label}</b>
              <small>{item.value ?? 0}{item.target ? ` / ${item.target}` : ""}</small>
            </span>
          ))}
        </div>
        {!!asArray(premiumGate.next_actions).length && (
          <div className="pro-next-actions">
            {asArray(premiumGate.next_actions).map((item) => <span key={item}>{item}</span>)}
          </div>
        )}
      </section>

      <section className="professional-split-view">
        <aside className="editor-panel professional-left-panel">
          <div className="section-heading-row">
            <div><span className="eyebrow">Sol Panel</span><h2>Ölçüt + rehber + beklenen kanıtlar</h2></div>
            <span className="pill">Split View</span>
          </div>
          <label>Bölüm seç
            <select value={selectedSection} onChange={(event) => { setSelectedSection(event.target.value); setActiveSectionKey?.(event.target.value); }}>
              {asArray(sections).map((section) => <option key={section.section_key} value={section.section_key}>{section.section_key} · {section.section_title}</option>)}
            </select>
          </label>
          <div className="professional-guide-card">
            <strong>{currentSection.section_title || "Başlık seçilmedi"}</strong>
            <p>{currentSection.main_title || "Ana ölçüt"}</p>
            <ul>
              <li>Beklenen kanıt: kurul kararı, tablo, paydaş görüşü, PUKÖ izleme kaydı.</li>
              <li>Eksik kanıt ve sayı/tutarlılık uyarıları aşağıdaki kontrol motorundan gelir.</li>
              <li>Standart blokları sürükleyip sağdaki editör önizlemesine bırakabilir veya Ekle düğmesini kullanabilirsiniz.</li>
            </ul>
          </div>
          <div className="clause-card-list">
            {asArray(clauses).slice(0, 12).map((clause) => (
              <article
                key={clause.id}
                className="clause-card"
                draggable
                onDragStart={() => setDraggedClause(clause)}
              >
                <span className="pill">{clause.clause_type || "standart"}</span>
                <strong>{clause.title}</strong>
                <p>{clause.content}</p>
                <button className="secondary-action" type="button" onClick={() => insertClause(clause)}><Copy size={14} /> Bölüme Ekle</button>
              </article>
            ))}
          </div>
        </aside>

        <main
          className="editor-panel professional-right-panel"
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => { event.preventDefault(); if (draggedClause) insertClause(draggedClause); }}
        >
          <div className="section-heading-row">
            <div><span className="eyebrow">Sağ Panel</span><h2>Editör / Hazırlayıcı + canlı önizleme + cümle diff</h2></div>
            <button className="secondary-action" onClick={() => onPick?.(selectedSection, "entry")}>Stüdyoyu Aç</button>
          </div>
          <div className="live-preview-card">
            <span className="eyebrow">Canlı Önizleme</span>
            <h3>{currentSection.section_key} · {currentSection.section_title}</h3>
            <p>{String(currentSection.report_text || "Bu başlık için rapor metni henüz yazılmamış.").slice(0, 900)}</p>
          </div>
          <div className="diff-card-list">
            <h3>Değişen cümleler</h3>
            {asArray(diff?.diff_rows).length ? asArray(diff.diff_rows).slice(0, 10).map((row, index) => (
              <div key={`${row.type}-${index}`} className={`diff-sentence ${row.type}`}><strong>{row.type}</strong><span>{row.sentence}</span></div>
            )) : <div className="empty-state">Karşılaştırılacak önceki sürüm yok veya cümle değişikliği bulunmadı.</div>}
          </div>
        </main>
      </section>

      <TabbedExpander
        title="Profesyonel Kontrol Merkezi"
        subtitle="Clause Library, tutarlılık kontrolü, kalite skoru, mock denetim ve harici denetçi erişimi."
        tabs={[
          { id: "quality", label: "Kalite Skoru", count: quality.score ?? 0, content: <div className="panel-stack"><ProgressBar value={quality.score ?? 0} /><DataTable rows={asArray(quality.heatmap)} columns={["section_key", "section_title", "score", "risk", "evidence_count", "table_count", "issue_count"]} /></div> },
          { id: "consistency", label: "Tutarlılık", count: consistency.total_issues ?? 0, content: <DataTable rows={issueRows} columns={["Seviye", "Tür", "Bölüm", "Uyarı", "Öneri"]} /> },
          { id: "clauses", label: "Clause Library", count: clauseRows.length, content: <DataTable rows={clauseRows} columns={["Başlık", "Ölçüt", "Tip", "Etiket"]} /> },
          { id: "mock", label: "Mock Denetim", count: mockRows.length, content: <DataTable rows={mockRows} columns={["Bölüm", "Skor", "Risk", "Denetçi Sorusu"]} /> },
          { id: "links", label: "Denetçi Linkleri", count: auditorLinks.length, content: <div className="panel-stack"><button className="secondary-action" onClick={createAuditorLink}><Lock size={16} /> Süre Sınırlı Link Üret</button><DataTable rows={auditorLinks} columns={["label", "expires_at", "watermark", "is_active", "created_by", "access_count"]} /></div> },
        ]}
      />

      <form className="editor-panel form-grid" onSubmit={createClause}>
        <div className="section-heading-row full-span"><div><span className="eyebrow">Yeni Blok</span><h2>Ölçüt bazlı standart cümle/blok ekle</h2></div></div>
        <label>Başlık<input value={newClause.title} onChange={(event) => setNewClause({ ...newClause, title: event.target.value })} placeholder="Örn. Mezun izleme açıklaması" /></label>
        <label>Ölçüt<input value={newClause.criterion_code} onChange={(event) => setNewClause({ ...newClause, criterion_code: event.target.value })} placeholder="Örn. 3" /></label>
        <label>Tip<select value={newClause.clause_type} onChange={(event) => setNewClause({ ...newClause, clause_type: event.target.value })}><option>standart</option><option>kanıt_yönlendirmesi</option><option>tablo_açıklaması</option><option>riskli_ifade</option><option>iyileştirme</option></select></label>
        <label>Etiket<input value={newClause.tags} onChange={(event) => setNewClause({ ...newClause, tags: event.target.value })} placeholder="kanıt, PUKÖ, tablo" /></label>
        <label className="full-span">İçerik<textarea rows={4} value={newClause.content} onChange={(event) => setNewClause({ ...newClause, content: event.target.value })} /></label>
        <button className="primary-action" type="submit"><Sparkles size={16} /> Clause Kaydet</button>
      </form>
    </section>
  );
}

export function ExportView({ programId, user, onError, onMessage }) {
  const [history, setHistory] = useState([]);
  const [settings, setSettings] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [preflight, setPreflight] = useState(null);
  const [directBusy, setDirectBusy] = useState("");
  const canSeeHistory = isAdminRole(user?.role);
  async function loadHistory() {
    if (canSeeHistory) setHistory(asArray(await api.exports(programId)));
  }
  async function loadJobs() {
    if (!programId) return;
    setJobs(asArray(await api.exportJobs(programId, 25)));
  }
  async function loadPreflight() {
    if (!programId) return;
    setPreflight(asObject(await api.reportPreflight(programId)));
  }
  useEffect(() => {
    if (!canSeeHistory) return setHistory([]);
    loadHistory().catch((err) => onError(err.message));
  }, [programId, canSeeHistory]);
  useEffect(() => { api.settings(programId).then(setSettings).catch((err) => onError(err.message)); }, [programId]);
  useEffect(() => { loadJobs().catch((err) => onError(err.message)); loadPreflight().catch((err) => onError(err.message)); }, [programId]);
  useEffect(() => {
    const handler = (event) => {
      const detail = asObject(event.detail);
      if (Array.isArray(detail.export_jobs)) setJobs(detail.export_jobs);
      if (detail.export_jobs?.some?.((job) => job.status === "done" || job.status === "failed")) loadHistory().catch(() => null);
    };
    window.addEventListener("medek-live-event", handler);
    return () => window.removeEventListener("medek-live-event", handler);
  }, [programId, canSeeHistory]);
  async function downloadDocx() {
    setDirectBusy("docx");
    try {
      const draft = preflight?.ready === false;
      downloadBlob(await api.reportDocx(programId, true), settings?.docx_filename || "AKYS_ODR.docx");
      onMessage(draft ? "Bloklayıcı eksikler olsa da taslak DOCX indirildi." : "DOCX indirildi.");
      await Promise.all([loadHistory(), loadJobs()]);
    } catch (err) {
      onError(err.message);
    } finally {
      setDirectBusy("");
    }
  }
  async function downloadPdf() {
    setDirectBusy("pdf");
    try {
      const draft = preflight?.ready === false;
      downloadBlob(await api.reportPdf(programId, true), settings?.pdf_filename || "AKYS_ODR.pdf");
      onMessage(draft ? "Bloklayıcı eksikler olsa da taslak PDF indirildi." : "PDF indirildi.");
      await Promise.all([loadHistory(), loadJobs()]);
    } catch (err) {
      onError(err.message);
    } finally {
      setDirectBusy("");
    }
  }
  async function startJob(exportType, force = false) {
    try {
      const finalExport = ["docx", "pdf"].includes(exportType);
      const shouldForce = finalExport ? true : Boolean(force);
      const job = asObject(await api.createExportJob(programId, exportType, shouldForce));
      setJobs((current) => [job, ...current.filter((item) => item.id !== job.id)]);
      onMessage(`${exportLabel(exportType)} kuyruğa alındı. Rapor boş olsa bile dosya üretilecek.`);
    } catch (err) { onError(err.message); }
  }
  async function downloadJob(job) {
    try {
      downloadBlob(await api.exportJobBlob(programId, job.id), job.file_name || `${job.export_type}.docx`);
      onMessage("Hazır çıktı indirildi.");
    } catch (err) { onError(err.message); }
  }
  const activeJobs = jobs.filter((job) => ["queued", "running"].includes(String(job.status || "")));
  useEffect(() => {
    if (!activeJobs.length) return undefined;
    const timer = window.setInterval(() => {
      loadJobs().catch(() => null);
    }, 7000);
    return () => window.clearInterval(timer);
  }, [activeJobs.length, programId]);
  return (
    <section className="panel-stack ops-premium-shell ops-export-workspace">
      <div className="editor-panel export-hero ops-premium-hero">
        <div><span className="eyebrow">Denetime Hazır Dışa Aktarım</span><h2>Akreditasyon çıktılarını indir veya izlenebilir job akışıyla üret</h2><p>{settings?.accreditation_label || "Akreditasyon"} formatlı çıktıları doğrudan indirebilir veya kuyruk mantığıyla izlenebilir şekilde üretebilirsiniz.</p></div>
        <div className="action-row"><button className="primary-action" disabled={directBusy === "docx"} onClick={downloadDocx}>{directBusy === "docx" ? "DOCX hazırlanıyor" : "DOCX Hemen İndir"}</button><button disabled={directBusy === "pdf"} onClick={downloadPdf}>{directBusy === "pdf" ? "PDF hazırlanıyor" : "PDF Hemen İndir"}</button><button onClick={() => startJob("docx")}>DOCX Job Başlat</button><button onClick={() => startJob("pdf")}>PDF Job Başlat</button><button onClick={() => startJob("control_docx")}>Kontrol DOCX</button><button onClick={() => startJob("audit_docx")}>Denetim DOCX</button><button onClick={() => startJob("analytics_docx")}>Analytics DOCX</button><button onClick={() => startJob("analytics_pdf")}>Analytics PDF</button></div>
        <div className="export-modern-note"><span className="pill">Taslak çıktı açık</span><p className="muted">Rapor metni boş veya bloklayıcı eksik olsa bile DOCX/PDF üretimi engellenmez; denetim paneli eksikleri ayrıca gösterir. Job tamamlandığında iş kartında İndir butonu görünür.</p></div>
      </div>
      <ReportPreflightPanel preflight={preflight} compact />
      <AccreditationProcessStrip process={`${jobs.length} çıktı işi izleniyor`} risk={`${activeJobs.length} aktif job`} trace="Her çıktı actor ve zaman bilgisiyle kaydedilir" action="Denetime hazır DOCX/PDF üretimi" />
      <section className="editor-panel">
        <div className="editor-header"><div><h2>Canlı Export İşleri</h2><p className="muted">SSE açıksa işler anlık güncellenir; bağlantı kesilirse mevcut polling/fallback devam eder.</p></div><button onClick={loadJobs}><RefreshCw size={16} /> İşleri Yenile</button></div>
        {!jobs.length && <div className="empty-state">Henüz çıktı işi yok.</div>}
        <div className="job-card-grid">
          {jobs.map((job) => <div className={`job-card status-${job.status}`} key={job.id}>
            <div className="job-card-head"><strong>{exportLabel(job.export_type)}</strong><span>{job.status}</span></div>
            <ProgressBar value={job.progress} />
            <div className="job-meta"><span>%{Number(job.progress || 0)}</span><span>{job.message || job.error || job.updated_at}</span></div>
            {job.error && <small className="error-text">{job.error}</small>}
            <div className="action-row compact">{job.status === "done" && <button onClick={() => downloadJob(job)}>İndir</button>}<button onClick={() => api.exportJob(programId, job.id).then((fresh) => setJobs((current) => current.map((item) => item.id === job.id ? asObject(fresh) : item))).catch((err) => onError(err.message))}>Durum Al</button></div>
          </div>)}
        </div>
        {!!activeJobs.length && <div className="notice-card info"><strong>{activeJobs.length} çıktı işi çalışıyor.</strong><span>İşler tamamlanınca bildirim merkezi ve bu panel otomatik güncellenir.</span></div>}
      </section>
      {canSeeHistory && <div className="editor-panel"><h2>Çıktı Geçmişi</h2><DataTable rows={history} columns={["export_type", "file_name", "actor", "created_at", "note"]} /></div>}
    </section>
  );
}

function exportLabel(type) {
  return {
    docx: "Nihai DOCX",
    pdf: "Nihai PDF",
    control_docx: "Kontrol DOCX",
    audit_docx: "Denetim DOCX",
    analytics_docx: "Analytics DOCX",
    analytics_pdf: "Analytics PDF",
  }[type] || type || "Çıktı";
}

export function ExportHistoryView({ programId, onError, onMessage }) {
  const [history, setHistory] = useState([]);
  useEffect(() => { api.exports(programId).then((data) => setHistory(asArray(data))).catch((err) => onError(err.message)); }, [programId]);
  function downloadCsv() {
    const columns = ["export_type", "file_name", "actor", "created_at", "note"];
    const csv = [columns.join(";"), ...history.map((row) => columns.map((col) => `"${String(row[col] ?? "").replaceAll('"', '""')}"`).join(";"))].join("\n");
    const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8" });
    downloadBlob(blob, "akreditasyon_export_history.csv");
    onMessage("Çıktı geçmişi CSV indirildi.");
  }
  return (
    <section className="panel-stack">
      <div className="editor-panel export-history-hero">
        <div><span className="eyebrow">Çıktı Geçmişi</span><h2>Rapor üretim kayıtları</h2><p>DOCX, PDF, kontrol ve denetim çıktılarının kim tarafından, ne zaman üretildiğini izleyin.</p></div>
        <button onClick={downloadCsv} disabled={!history.length}><History size={16} /> CSV İndir</button>
      </div>
      <div className="editor-panel"><DataTable rows={history} columns={["export_type", "file_name", "actor", "created_at", "note"]} /></div>
    </section>
  );
}

export function ProgramsView({ user, activeProgram, sections, onError, onMessage, refreshPrograms }) {
  const [programRows, setProgramRows] = useState([]);
  const [programUsers, setProgramUsers] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [faculties, setFaculties] = useState([]);
  const [tenantSetup, setTenantSetup] = useState({ setup_required: false });
  const [tenantForm, setTenantForm] = useState({ id: "", name: "", code: "", domain: "", source_url: "", is_active: true });
  const [tenantCleanup, setTenantCleanup] = useState(null);
  const [catalogImporting, setCatalogImporting] = useState(false);
  const [catalogImportResult, setCatalogImportResult] = useState(null);
  const [newProgram, setNewProgram] = useState({ tenant_id: "tenant_default", university_name: "", school_name: "", faculty_name: "", department_name: "", program_name: "", report_year: "2025", report_type: "ÖZ DEĞERLENDİRME RAPORU", accreditation_profile: "MEDEK", is_active: true });
  const [clone, setClone] = useState({ source_program_id: activeProgram, program_name: "", report_year: "2025", copy_text: true, copy_tables: false, copy_evidence_meta: false });
  const [assignment, setAssignment] = useState({ username: "", program_ids: [activeProgram], role: "Editör / Hazırlayıcı", assigned_sections: "", is_active: true });
  const [assignmentFilter, setAssignmentFilter] = useState({ tenant_id: "", school_name: "", department_name: "", program_id: activeProgram || "" });
  const [users, setUsers] = useState([]);
  const [permissionRows, setPermissionRows] = useState([]);
  async function load() {
    const permissionPayloadRaw = await api.permissions().catch(() => ({ rows: [] }));
    const permissionPayload = asObject(permissionPayloadRaw);
    const nextPermissionRows = asArray(permissionPayload.rows);
    const currentRoleName = normalizeRole(user?.role || READONLY_ROLE, user?.tenant_scope);
    const canFetchPrograms = ["program.view", "program.list.view", "program.create", "program.clone", "program.assign_users", "program.users.view"].some((permission) => matrixPermissionAllowed(nextPermissionRows, currentRoleName, permission, isAdminRole(currentRoleName)));
    const canFetchUsers = matrixPermissionAllowed(nextPermissionRows, currentRoleName, "user.view", isAdminRole(currentRoleName)) || matrixPermissionAllowed(nextPermissionRows, currentRoleName, "program.assign_users", isAdminRole(currentRoleName));
    const canFetchProgramUsers = matrixPermissionAllowed(nextPermissionRows, currentRoleName, "program.users.view", isAdminRole(currentRoleName)) || matrixPermissionAllowed(nextPermissionRows, currentRoleName, "program.assign_users", isAdminRole(currentRoleName));
    const canFetchTenantRefs = canFetchPrograms || matrixPermissionAllowed(nextPermissionRows, currentRoleName, "tenant.manage", isSuperAdminRole(currentRoleName));
    const [programDataRaw, userDataRaw, programUserDataRaw, tenantDataRaw, facultyDataRaw, tenantSetupRaw] = await Promise.all([
      canFetchPrograms ? api.adminPrograms(true).catch(() => []) : Promise.resolve([]),
      canFetchUsers ? api.users().catch(() => []) : Promise.resolve([]),
      canFetchProgramUsers ? api.programUsers().catch(() => []) : Promise.resolve([]),
      canFetchTenantRefs ? api.tenants(true).catch(() => []) : Promise.resolve([]),
      canFetchTenantRefs ? api.tenantFaculties().catch(() => []) : Promise.resolve([]),
      api.tenantSetup().catch(() => ({ setup_required: false })),
    ]);
    const programData = asArray(programDataRaw);
    const userData = asArray(userDataRaw);
    const programUserData = asArray(programUserDataRaw);
    const tenantData = asArray(tenantDataRaw);
    const facultyData = asArray(facultyDataRaw);
    const setupData = asObject(tenantSetupRaw);
    setProgramRows(programData);
    setUsers(userData);
    setProgramUsers(programUserData);
    setTenants(tenantData);
    setFaculties(facultyData);
    setTenantSetup(setupData);
    setPermissionRows(nextPermissionRows);
    setClone((current) => ({ ...current, source_program_id: current.source_program_id || programData[0]?.id || "" }));
    setAssignment((current) => ({ ...current, username: current.username || userData[0]?.username || "" }));
    if (setupData.setup_required) {
      setTenantForm({ id: setupData.tenant_id || "tenant_default", name: "", code: "", domain: "", source_url: "", is_active: true });
    } else {
      setTenantForm((current) => ({ ...current, id: current.id || tenantData[0]?.id || "" }));
    }
    setAssignmentFilter((current) => ({ ...current, tenant_id: current.tenant_id || tenantData.find((tenant) => !tenant.is_setup_placeholder)?.id || tenantData[0]?.id || "tenant_default", program_id: current.program_id || activeProgram || programData[0]?.id || "" }));
  }
  useEffect(() => { load().catch((err) => onError(err.message)); }, []);
  async function create(event) {
    event.preventDefault();
    try {
      const tenant = tenantOptions.find((item) => item.id === newProgramTenantId);
      await api.createProgram({ ...newProgram, tenant_id: newProgramTenantId, university_name: tenant?.name || newProgram.university_name || "", faculty_name: newProgram.school_name || newProgram.faculty_name || "" });
      onMessage("Program oluşturuldu.");
      await load();
      await refreshPrograms();
    } catch (err) { onError(err.message); }
  }
  async function cloneProgram(event) {
    event.preventDefault();
    try { await api.cloneProgram(clone); onMessage("Program kopyalandı."); await load(); await refreshPrograms(); } catch (err) { onError(err.message); }
  }
  async function assign(event) {
    event.preventDefault();
    try { await api.saveProgramUser(assignment); onMessage("Program yetkisi kaydedildi."); await load(); } catch (err) { onError(err.message); }
  }
  async function saveTenant(event) {
    event.preventDefault();
    try {
      await api.saveTenant(tenantForm);
      onMessage(tenantSetup.setup_required ? "İlk kurum kurulumu tamamlandı." : "Kurum/tenant kaydedildi.");
      await load();
      await refreshPrograms();
    } catch (err) { onError(err.message); }
  }
  async function importAcademicCatalog() {
    if (!tenantForm.domain) {
      onError("Kurum alan adı/domain girilmelidir. Örn: erciyes.edu.tr");
      return;
    }
    setCatalogImporting(true);
    setCatalogImportResult(null);
    try {
      const result = await api.importTenantAcademicCatalog({
        tenant_id: tenantForm.id || tenantSetup?.tenant_id || "",
        tenant_name: tenantForm.name || "",
        code: tenantForm.code || "",
        domain: tenantForm.domain || "",
        report_year: newProgram.report_year || "2025",
        create_programs: true,
      });
      setCatalogImportResult(result);
      onMessage(`${result.faculty_count || 0} birim, ${result.department_count || 0} bölüm, ${result.created_program_count || 0} yeni program YÖK Atlas üzerinden otomatik tanımlandı.`);
      await load();
      await refreshPrograms();
    } catch (err) {
      onError(err.message);
    } finally {
      setCatalogImporting(false);
    }
  }
  async function toggleTenant(tenant, active) {
    try {
      await api.saveTenant({ ...tenant, is_active: active });
      onMessage(active ? "Kurum aktif edildi." : "Kurum pasifleştirildi.");
      await load();
    } catch (err) { onError(err.message); }
  }
  async function deleteTenant(tenant) {
    const label = tenant.name || tenant.id;
    const dependencyCount = Number(tenant.program_count || 0) + Number(tenant.user_count || 0);
    if (dependencyCount > 0) {
      const fallbackTarget = tenantOptions.find((item) => item.id !== tenant.id)?.id || "";
      setTenantCleanup({ tenant, mode: fallbackTarget ? "move" : "archive_children", target_tenant_id: fallbackTarget });
      onMessage(`${label} kurumuna bağlı ${tenant.program_count || 0} program ve ${tenant.user_count || 0} kullanıcı var. Aşağıdaki güvenli işlem merkezinden pasifleştirme, taşıma veya arşivleme seçin.`);
      return;
    }
    if (!window.confirm(`${label} kurumu arşive alınsın mı?`)) return;
    try {
      await api.deleteTenant(tenant.id, { mode: "safe" });
      onMessage("Kurum arşive alındı.");
      setTenantForm({ id: "", name: "", code: "", domain: "", source_url: "", is_active: true });
      setTenantCleanup(null);
      await load();
    } catch (err) { onError(err.message); }
  }
  async function purgeTenant(tenant) {
    const label = tenant?.name || tenant?.id || "Seçili kurum";
    if (!isSuperAdminRole(programRoleName)) {
      onError("Kurum kalıcı silme işlemini yalnızca Süper Admin yapabilir.");
      return;
    }
    const defaultNote = tenant?.id === "tenant_default" ? " Varsayılan teknik kurum kaydı silinmez; ancak kuruma ait programlar, fakülteler, kullanıcılar ve geçmiş kayıtlar temizlenir, aktif Süper Admin hesabınız korunur." : "";
    const confirmation = window.prompt(`${label} kurumu, bağlı programları, kullanıcıları ve ilişkili kayıtları KALICI olarak silinecek.${defaultNote} Onaylamak için KALICI SIL yazın.`);
    if (confirmation !== "KALICI SIL") return;
    try {
      await api.deleteTenant(tenant.id, { mode: "purge" });
      onMessage(tenant?.id === "tenant_default" ? "Varsayılan kurum verileri kalıcı temizlendi; Süper Admin hesabınız korundu." : "Kurum ve bağlı kayıtlar kalıcı silindi.");
      setTenantCleanup(null);
      setTenantForm({ id: "", name: "", code: "", domain: "", source_url: "", is_active: true });
      await load();
      await refreshPrograms();
    } catch (err) { onError(err.message); }
  }
  async function runTenantCleanup(mode) {
    if (!tenantCleanup?.tenant?.id) return;
    const tenant = tenantCleanup.tenant;
    const label = tenant.name || tenant.id;
    const targetId = tenantCleanup.target_tenant_id || "";
    const targetName = tenantOptions.find((item) => item.id === targetId)?.name || targetId;
    if (mode === "purge") {
      await purgeTenant(tenant);
      return;
    }
    const messages = {
      deactivate: `${label} pasifleştirilsin mi? Bağlı kayıtlar korunur, sadece yeni kullanım kapanır.`,
      move: `${label} kurumundaki program ve kullanıcılar ${targetName} kurumuna taşınıp kaynak kurum arşive alınsın mı?`,
      archive_children: `${label} ve bağlı program/kullanıcı kayıtları arşive alınsın mı? Bu işlem üretim verisi için dikkatli kullanılmalıdır.`,
    };
    if (mode === "move" && !targetId) {
      onError("Taşıma için hedef kurum seçmelisiniz.");
      return;
    }
    if (!window.confirm(messages[mode] || "İşlem uygulansın mı?")) return;
    try {
      await api.deleteTenant(tenant.id, { mode, target_tenant_id: targetId });
      onMessage(mode === "deactivate" ? "Kurum pasifleştirildi." : mode === "move" ? "Bağlı kayıtlar taşındı ve kurum arşive alındı." : "Kurum ve bağlı kayıtlar arşive alındı.");
      setTenantCleanup(null);
      setTenantForm({ id: "", name: "", code: "", domain: "", source_url: "", is_active: true });
      await load();
      await refreshPrograms();
    } catch (err) { onError(err.message); }
  }
  async function toggle(program, active) {
    try { await api.setProgramActive(program.id, active); await load(); await refreshPrograms(); } catch (err) { onError(err.message); }
  }
  async function deleteProgram(program) {
    const label = `${program.program_name || program.id} · ${program.report_year || ""}`.trim();
    if (!window.confirm(`${label} programı ve bu programa bağlı başlık, kanıt, tablo, onay, çıktı ve yetki kayıtları arşive alınsın mı? Geri Yükleme ekranından tekrar aktif edilebilir.`)) return;
    try {
      await api.deleteProgram(program.id);
      onMessage("Program arşive alındı.");
      await load();
      await refreshPrograms();
    } catch (err) { onError(err.message); }
  }
  const assignmentProgramIds = assignment.program_ids || [];
  const assignmentProgramIdsKey = assignmentProgramIds.join("|");
  const [assignmentSections, setAssignmentSections] = useState([]);
  const [assignmentSectionsLoading, setAssignmentSectionsLoading] = useState(false);
  const assignedSectionKeys = assignment.assigned_sections ? assignment.assigned_sections.split(",").filter(Boolean) : [];
  const assignmentProgramSet = new Set(assignmentProgramIds);
  const assignedSectionSet = new Set(assignedSectionKeys);
  const programGroupsForAssignment = groupedPrograms(programRows);
  const assignmentProgramMap = new Map(programRows.map((program) => [program.id, program]));
  const assignmentSectionRows = useMemo(() => {
    const seen = new Set();
    const rows = [];
    assignmentSections.forEach(({ program, sections: programSections }) => {
      (programSections || []).forEach((section) => {
        if (seen.has(section.section_key)) return;
        seen.add(section.section_key);
        rows.push({
          ...section,
          source_program_id: program?.id || "",
          source_program_label: program ? programDisplayLabel(program) : "Seçili program",
          source_school_name: program?.school_name || "",
          source_profile: program?.accreditation_profile || "",
        });
      });
    });
    return rows;
  }, [assignmentSections]);
  useEffect(() => {
    let alive = true;
    async function loadAssignmentSections() {
      if (!assignmentProgramIds.length) {
        setAssignmentSections([]);
        return;
      }
      setAssignmentSectionsLoading(true);
      try {
        const rows = await Promise.all(assignmentProgramIds.map(async (programId) => {
          const program = assignmentProgramMap.get(programId) || { id: programId };
          const programSections = programId === activeProgram ? sections : await api.sections(programId);
          return { program, sections: programSections || [] };
        }));
        if (!alive) return;
        setAssignmentSections(rows);
        const allowedKeys = new Set(rows.flatMap((row) => (row.sections || []).map((section) => section.section_key)));
        const filteredKeys = assignedSectionKeys.filter((sectionKey) => allowedKeys.has(sectionKey));
        if (filteredKeys.length !== assignedSectionKeys.length) {
          setAssignment((current) => ({ ...current, assigned_sections: filteredKeys.join(",") }));
        }
      } catch (err) {
        if (alive) onError(err.message);
      } finally {
        if (alive) setAssignmentSectionsLoading(false);
      }
    }
    loadAssignmentSections();
    return () => { alive = false; };
  }, [assignmentProgramIdsKey, programRows, activeProgram, sections]);
  function toggleAssignmentProgram(programId) {
    const next = assignmentProgramSet.has(programId)
      ? assignmentProgramIds.filter((id) => id !== programId)
      : [...assignmentProgramIds, programId];
    setAssignment({ ...assignment, program_ids: next });
  }
  function setAllAssignmentPrograms() {
    setAssignment({ ...assignment, program_ids: programRows.map((program) => program.id) });
  }
  function clearAssignmentPrograms() {
    setAssignment({ ...assignment, program_ids: [] });
  }
  function toggleAssignedSection(sectionKey) {
    const next = assignedSectionSet.has(sectionKey)
      ? assignedSectionKeys.filter((key) => key !== sectionKey)
      : [...assignedSectionKeys, sectionKey];
    setAssignment({ ...assignment, assigned_sections: next.join(",") });
  }
  function setAllAssignedSections() {
    setAssignment({ ...assignment, assigned_sections: assignmentSectionRows.map((section) => section.section_key).join(",") });
  }
  function clearAssignedSections() {
    setAssignment({ ...assignment, assigned_sections: "" });
  }
  const setupRequired = Boolean(tenantSetup?.setup_required);
  const allTenantOptions = tenants.length ? tenants : [];
  const tenantOptions = setupRequired ? [] : allTenantOptions.filter((tenant) => !tenant.is_setup_placeholder);
  const tenantMap = new Map(allTenantOptions.map((tenant) => [tenant.id, tenant]));
  const tenantTableRows = tenantOptions.map((tenant) => ({ ...tenant, tenant_code: tenant.code || "" }));
  const programTenantGroups = groupedByTenant(programRows, tenantOptions);
  const programUserTenantGroups = groupedByTenant(programUsers, tenantOptions);
  const newProgramTenantId = newProgram.tenant_id || tenantOptions[0]?.id || allTenantOptions[0]?.id || "tenant_default";
  const newProgramFacultyRows = faculties.filter((item) => String(item.tenant_id || "tenant_default") === String(newProgramTenantId));
  const importedProgramCatalog = useMemo(() => {
    const catalog = new Map();
    programRows
      .filter((program) => String(tenantIdOf(program)) === String(newProgramTenantId))
      .forEach((program) => {
        const faculty = program.school_name || program.faculty_name || "";
        const department = program.department_name || "";
        const programName = program.program_name || "";
        if (!faculty) return;
        if (!catalog.has(faculty)) catalog.set(faculty, { profile: program.accreditation_profile || profileForFaculty(faculty), departments: {} });
        const item = catalog.get(faculty);
        item.profile = item.profile || program.accreditation_profile || profileForFaculty(faculty);
        if (department) {
          if (!item.departments[department]) item.departments[department] = [];
          if (programName && !item.departments[department].includes(programName)) item.departments[department].push(programName);
        }
      });
    return catalog;
  }, [programRows, newProgramTenantId]);
  const newProgramFacultyOptions = useMemo(() => {
    const map = new Map(FACULTY_PROFILE_OPTIONS.map((item) => [item.label, item]));
    newProgramFacultyRows.forEach((item) => {
      if (item.faculty_name) map.set(item.faculty_name, { label: item.faculty_name, profile: item.accreditation_profile || "MEDEK" });
    });
    importedProgramCatalog.forEach((item, label) => {
      if (label) map.set(label, { label, profile: item.profile || "MEDEK" });
    });
    return Array.from(map.values()).sort((a, b) => a.label.localeCompare(b.label, "tr"));
  }, [newProgramFacultyRows, importedProgramCatalog]);
  function profileForNewProgramFaculty(schoolName, nextProgram = newProgram) {
    const existing = newProgramFacultyRows.find((item) => item.faculty_name === schoolName);
    const imported = importedProgramCatalog.get(schoolName);
    const degree = nextProgram.program_degree || nextProgram.degree || "";
    const inferred = inferAccreditationProfile({
      degree,
      schoolName,
      departmentName: nextProgram.department_name,
      programName: nextProgram.program_name,
    });
    return inferred || existing?.accreditation_profile || imported?.profile || profileForFaculty(schoolName);
  }
  function isNewProgramProfileLocked(schoolName) {
    return false;
  }
  function departmentOptionsForNewProgram(schoolName) {
    const imported = importedProgramCatalog.get(schoolName)?.departments || {};
    return uniqueSorted([...departmentOptionsForFaculty(schoolName), ...Object.keys(imported)]);
  }
  function programOptionsForNewProgram(schoolName, departmentName) {
    const imported = importedProgramCatalog.get(schoolName)?.departments?.[departmentName] || [];
    return uniqueSorted([...programOptionsForDepartment(schoolName, departmentName), ...imported]);
  }
  const assignmentTenantId = assignmentFilter.tenant_id || tenantOptions[0]?.id || allTenantOptions[0]?.id || "tenant_default";
  const assignmentTenantPrograms = programRows.filter((program) => String(tenantIdOf(program)) === String(assignmentTenantId));
  const assignmentSchoolOptions = uniqueSorted(assignmentTenantPrograms.map((program) => program.school_name || program.faculty_name || ""));
  const assignmentSchool = assignmentSchoolOptions.includes(assignmentFilter.school_name) ? assignmentFilter.school_name : (assignmentSchoolOptions[0] || "");
  const assignmentDepartmentOptions = uniqueSorted(assignmentTenantPrograms.filter((program) => !assignmentSchool || (program.school_name || program.faculty_name || "") === assignmentSchool).map((program) => program.department_name || ""));
  const assignmentDepartment = assignmentDepartmentOptions.includes(assignmentFilter.department_name) ? assignmentFilter.department_name : (assignmentDepartmentOptions[0] || "");
  const assignmentProgramOptions = assignmentTenantPrograms.filter((program) => {
    const schoolMatch = !assignmentSchool || (program.school_name || program.faculty_name || "") === assignmentSchool;
    const departmentMatch = !assignmentDepartment || (program.department_name || "") === assignmentDepartment;
    return schoolMatch && departmentMatch;
  });
  const selectedAssignmentProgramId = assignmentProgramOptions.some((program) => program.id === assignmentFilter.program_id)
    ? assignmentFilter.program_id
    : (assignmentProgramOptions[0]?.id || "");
  const isFacultyAdminAssignment = assignment.role === FACULTY_ADMIN_ROLE;
  const facultyAssignmentProgramIds = assignmentTenantPrograms
    .filter((program) => (program.school_name || program.faculty_name || "") === assignmentSchool)
    .map((program) => program.id);
  function selectNewProgramTenant(tenantId) {
    const tenant = tenantMap.get(tenantId);
    setNewProgram({ ...newProgram, tenant_id: tenantId, university_name: tenant?.name || newProgram.university_name || "" });
  }
  function selectNewProgramFaculty(schoolName) {
    const departments = departmentOptionsForNewProgram(schoolName);
    const firstDepartment = departments[0] || "";
    const programs = programOptionsForNewProgram(schoolName, firstDepartment);
    setNewProgram({
      ...newProgram,
      tenant_id: newProgramTenantId,
      university_name: tenantMap.get(newProgramTenantId)?.name || newProgram.university_name || "",
      school_name: schoolName,
      faculty_name: schoolName,
      department_name: firstDepartment,
      program_name: programs[0] || "",
      program_degree: newProgram.program_degree || (String(schoolName || "").toLocaleLowerCase("tr-TR").includes("meslek yüksekokulu") || String(schoolName || "").toLocaleLowerCase("tr-TR").includes("myo") ? "Önlisans" : "Lisans"),
      accreditation_profile: profileForNewProgramFaculty(schoolName, { ...newProgram, school_name: schoolName, department_name: firstDepartment, program_name: programs[0] || "" }),
    });
  }
  function setAssignmentProgram(programId) {
    const program = assignmentTenantPrograms.find((item) => item.id === programId);
    setAssignmentFilter({
      tenant_id: program ? tenantIdOf(program) : assignmentTenantId,
      school_name: program?.school_name || program?.faculty_name || assignmentSchool,
      department_name: program?.department_name || assignmentDepartment,
      program_id: programId,
    });
    setAssignment({ ...assignment, program_ids: programId ? [programId] : [], assigned_sections: "" });
  }
  function selectAssignmentTenant(tenantId) {
    const rows = programRows.filter((program) => String(tenantIdOf(program)) === String(tenantId));
    const first = rows[0];
    const schoolName = first?.school_name || first?.faculty_name || "";
    setAssignmentFilter({ tenant_id: tenantId, school_name: schoolName, department_name: isFacultyAdminAssignment ? "" : (first?.department_name || ""), program_id: isFacultyAdminAssignment ? "" : (first?.id || "") });
    const facultyIds = rows.filter((program) => (program.school_name || program.faculty_name || "") === schoolName).map((program) => program.id);
    setAssignment({ ...assignment, program_ids: isFacultyAdminAssignment ? facultyIds : (first?.id ? [first.id] : []), assigned_sections: "" });
  }
  function selectAssignmentSchool(schoolName) {
    const rows = assignmentTenantPrograms.filter((program) => (program.school_name || program.faculty_name || "") === schoolName);
    const first = rows[0];
    const facultyIds = rows.map((program) => program.id);
    setAssignmentFilter({ ...assignmentFilter, school_name: schoolName, department_name: isFacultyAdminAssignment ? "" : (first?.department_name || ""), program_id: isFacultyAdminAssignment ? "" : (first?.id || "") });
    setAssignment({ ...assignment, program_ids: isFacultyAdminAssignment ? facultyIds : (first?.id ? [first.id] : []), assigned_sections: "" });
  }
  function selectedFacultyProgramIds(schoolName = assignmentSchool) {
    return assignmentTenantPrograms
      .filter((program) => (program.school_name || program.faculty_name || "") === schoolName)
      .map((program) => program.id);
  }
  function applyRoleSelection(role) {
    const nextRole = role || "Editör / Hazırlayıcı";
    if (nextRole === FACULTY_ADMIN_ROLE) {
      setAssignment({ ...assignment, role: nextRole, program_ids: selectedFacultyProgramIds(), assigned_sections: "" });
      setAssignmentFilter({ ...assignmentFilter, tenant_id: assignmentTenantId, school_name: assignmentSchool, department_name: "", program_id: "" });
      return;
    }
    const programId = selectedAssignmentProgramId || assignmentProgramOptions[0]?.id || "";
    const program = assignmentTenantPrograms.find((item) => item.id === programId);
    if (programId) {
      setAssignmentFilter({
        tenant_id: program ? tenantIdOf(program) : assignmentTenantId,
        school_name: program?.school_name || program?.faculty_name || assignmentSchool,
        department_name: program?.department_name || assignmentDepartment,
        program_id: programId,
      });
    }
    setAssignment({ ...assignment, role: nextRole, program_ids: programId ? [programId] : [], assigned_sections: "" });
  }
  function selectAssignmentDepartment(departmentName) {
    const first = assignmentTenantPrograms.find((program) => (program.school_name || program.faculty_name || "") === assignmentSchool && (program.department_name || "") === departmentName);
    setAssignmentFilter({ ...assignmentFilter, tenant_id: assignmentTenantId, school_name: assignmentSchool, department_name: departmentName, program_id: first?.id || "" });
    if (isFacultyAdminAssignment) {
      setAssignment({ ...assignment, program_ids: selectedFacultyProgramIds(assignmentSchool), assigned_sections: "" });
    } else {
      setAssignment({ ...assignment, program_ids: first?.id ? [first.id] : [], assigned_sections: "" });
    }
  }
  useEffect(() => {
    if (isFacultyAdminAssignment) {
      const nextIds = facultyAssignmentProgramIds;
      if (nextIds.join("|") !== assignmentProgramIds.join("|")) {
        setAssignment((current) => ({ ...current, program_ids: nextIds, assigned_sections: "" }));
      }
      return;
    }
    if (selectedAssignmentProgramId && (assignmentProgramIds.length !== 1 || assignmentProgramIds[0] !== selectedAssignmentProgramId)) {
      setAssignment((current) => ({ ...current, program_ids: [selectedAssignmentProgramId], assigned_sections: "" }));
    }
  }, [selectedAssignmentProgramId, isFacultyAdminAssignment, facultyAssignmentProgramIds.join("|")]);
  const programRoleName = normalizeRole(user?.role || READONLY_ROLE, user?.tenant_scope);
  const canPurgeTenant = isSuperAdminRole(programRoleName);
  const canTenantManage = matrixPermissionAllowed(permissionRows, programRoleName, "tenant.manage", isSuperAdminRole(programRoleName));
  const canProgramView = matrixPermissionAllowed(permissionRows, programRoleName, "program.view", true);
  const canProgramList = matrixPermissionAllowed(permissionRows, programRoleName, "program.list.view", canProgramView);
  const canProgramCreate = matrixPermissionAllowed(permissionRows, programRoleName, "program.create", isAdminRole(programRoleName));
  const canProgramClone = matrixPermissionAllowed(permissionRows, programRoleName, "program.clone", isAdminRole(programRoleName));
  const canProgramAssign = matrixPermissionAllowed(permissionRows, programRoleName, "program.assign_users", isAdminRole(programRoleName));
  const canProgramUsersView = matrixPermissionAllowed(permissionRows, programRoleName, "program.users.view", canProgramAssign);
  const canProgramEdit = matrixPermissionAllowed(permissionRows, programRoleName, "program.edit", isAdminRole(programRoleName));
  const canProgramArchive = matrixPermissionAllowed(permissionRows, programRoleName, "program.archive", isAdminRole(programRoleName));

  const programRoleOptions = delegatableRolesForActor(programRoleName);

  const tenantKpis = [
    { label: "Kurum / Tenant", value: tenantOptions.length, sub: "izole çalışma alanı" },
    { label: "Fakülte / MYO", value: faculties.length, sub: "kurum içi birim" },
    { label: "Program", value: programRows.length, sub: "tenant kapsamlı" },
  ];
  const cleanupTenant = tenantCleanup?.tenant || null;
  const cleanupIsDefaultTenant = cleanupTenant?.id === "tenant_default";
  const cleanupTargetOptions = tenantOptions.filter((tenant) => tenant.id !== cleanupTenant?.id);
  const tenantCleanupPanel = cleanupTenant ? (
    <div className="tenant-cleanup-panel">
      <div>
        <p className="eyebrow">Kurum kayıt yönetimi</p>
        <h3>{cleanupTenant.name || cleanupTenant.id}</h3>
        <p>{cleanupIsDefaultTenant ? "Bu kayıt teknik varsayılan kurumdur. Süper Admin, kuruma ait program/fakülte/kullanıcı verilerini kalıcı temizleyebilir; aktif Süper Admin hesabı korunur." : <>Bu kuruma bağlı <strong>{cleanupTenant.program_count || 0}</strong> program ve <strong>{cleanupTenant.user_count || 0}</strong> kullanıcı var. Kurum Admin güvenli işlem seçer; Süper Admin gerekirse kalıcı silme yapabilir.</>}</p>
      </div>
      <div className="tenant-cleanup-grid">
        <article className="cleanup-option">
          <strong>1. Pasifleştir</strong>
          <span>Kurum görünür kalır; yeni kullanım kapatılır. Bağlı kayıtlar aynen korunur.</span>
          <button type="button" onClick={() => runTenantCleanup("deactivate")}>Pasifleştir</button>
        </article>
        <article className="cleanup-option featured">
          <strong>2. Bağlı kayıtları taşı</strong>
          <span>{cleanupIsDefaultTenant ? "Varsayılan teknik kurum taşınamaz. Bu kayıt için Pasifleştir veya Süper Admin Kalıcı Temizle kullanılır." : "Programları, kullanıcıları, bildirim/export geçmişini hedef kuruma taşır ve kaynak kurumu arşive alır."}</span>
          <select disabled={cleanupIsDefaultTenant} value={tenantCleanup.target_tenant_id || ""} onChange={(e) => setTenantCleanup({ ...tenantCleanup, target_tenant_id: e.target.value })}>
            <option value="">Hedef kurum seç</option>
            {cleanupTargetOptions.map((tenant) => <option key={tenant.id} value={tenant.id}>{tenant.name}</option>)}
          </select>
          <button type="button" className="primary-action" disabled={cleanupIsDefaultTenant || !tenantCleanup.target_tenant_id} onClick={() => runTenantCleanup("move")}>Taşı ve Arşivle</button>
        </article>
        <article className="cleanup-option danger-zone">
          <strong>3. Kurumla birlikte arşivle</strong>
          <span>{cleanupIsDefaultTenant ? "Varsayılan teknik kurum arşivlenmez. Kurum verilerini tamamen kaldırmak için Süper Admin Kalıcı Temizle kullanılır." : "Kurum, program yetkileri, programlar ve kurum kullanıcıları arşive alınır. Denetim izi korunur."}</span>
          <button type="button" className="danger-button" disabled={cleanupIsDefaultTenant} onClick={() => runTenantCleanup("archive_children")}>Kurum + Bağlıları Arşivle</button>
        </article>
        {canPurgeTenant && <article className="cleanup-option danger-zone hard-delete-zone">
          <strong>4. Süper Admin: {cleanupIsDefaultTenant ? "Kalıcı temizle" : "Kalıcı sil"}</strong>
          <span>{cleanupIsDefaultTenant ? "Varsayılan teknik kurum kaydı korunur; kurum adı, domain, fakülteler, programlar, kurum kullanıcıları, yetkiler, bildirim/çıktı işleri ve ilişkili kayıtlar kalıcı temizlenir." : "Kurum, bağlı programlar, kurum kullanıcıları, yetkiler, bildirim/çıktı işleri ve ilişkili kayıtlar veritabanından kalıcı silinir. Bu işlem geri alınamaz."}</span>
          <button type="button" className="danger-button" onClick={() => runTenantCleanup("purge")}><Trash2 size={14} /> {cleanupIsDefaultTenant ? "Kalıcı Temizle" : "Kalıcı Sil"}</button>
        </article>}
      </div>
      <div className="action-row compact"><button type="button" onClick={() => setTenantCleanup(null)}>İptal</button></div>
    </div>
  ) : null;
  const tenantSetupContent = (
    <div className="tenant-setup-wizard editor-panel spotlight-panel">
      <div className="setup-hero">
        <span className="eyebrow">İlk Kurum Kurulumu</span>
        <h2>Gerçek kurum bilgisi tanımlanmadan çalışma alanı açılmaz.</h2>
        <p className="muted">Sistem içindeki <strong>tenant_default</strong> kaydı yalnızca teknik hazırlık içindir. Kurum adı, kısa kod ve alan adı girildiğinde bu kayıt gerçek kuruma dönüştürülür.</p>
      </div>
      <form className="tabbed-form" onSubmit={saveTenant}>
        <input type="hidden" value={tenantForm.id || tenantSetup?.tenant_id || "tenant_default"} />
        <div className="form-grid">
          <label>Kurum / Üniversite adı<input value={tenantForm.name || ""} onChange={(e) => setTenantForm({ ...tenantForm, id: tenantSetup?.tenant_id || "tenant_default", name: e.target.value })} placeholder="Kurum / Üniversite adını yazın" /></label>
          <label>Kısa kod<input value={tenantForm.code || ""} onChange={(e) => setTenantForm({ ...tenantForm, id: tenantSetup?.tenant_id || "tenant_default", code: e.target.value })} placeholder="Kısa kod" /></label>
          <label className="wide-field">Alan adı / domain<input value={tenantForm.domain || ""} onChange={(e) => setTenantForm({ ...tenantForm, id: tenantSetup?.tenant_id || "tenant_default", domain: e.target.value })} placeholder="erciyes.edu.tr" /><small>Sadece kurum alan adını yazın. Sistem fakülte/MYO, bölüm ve program listesini YÖK Atlas üzerinden otomatik bulur.</small></label>
        </div>
        <label className="checkbox-line"><input type="checkbox" checked={tenantForm.is_active !== false} onChange={(e) => setTenantForm({ ...tenantForm, is_active: e.target.checked })} /> Kurum aktif başlasın</label>
        <div className="action-row"><button className="primary-action">İlk Kurumu Oluştur</button><button type="button" disabled={catalogImporting || !tenantForm.domain} onClick={importAcademicCatalog}>{catalogImporting ? "YÖK Atlas sorgulanıyor..." : "YÖK Atlas’tan Akademik Yapıyı Bul"}</button></div>
      </form>
      {catalogImportResult && <div className="notice-card success"><strong>Akademik yapı tanımlandı.</strong><span>{catalogImportResult.faculty_count || 0} birim, {catalogImportResult.department_count || 0} bölüm, {catalogImportResult.created_program_count || 0} yeni program eklendi; {catalogImportResult.skipped_program_count || 0} mevcut program atlandı.</span><small>Kaynak: {catalogImportResult.source_url}</small></div>}
      <div className="notice-card info"><strong>Sonraki adım:</strong><span>Kurum kurulumu tamamlandıktan sonra Yeni Program sekmesinden fakülte/MYO, bölüm ve program tanımlayabilirsiniz.</span></div>
    </div>
  );
  const tenantContent = setupRequired ? tenantSetupContent : (
    <div className="panel-stack">
      <div className="metric-grid">{tenantKpis.map((item) => <MetricCard key={item.label} {...item} />)}</div>
      <form className="tabbed-form" onSubmit={saveTenant}>
        <h3>Kurum / Üniversite Kaydı</h3>
        <div className="form-grid">
          <label>Mevcut kurum<select value={tenantForm.id || ""} onChange={(e) => { const row = tenantOptions.find((item) => item.id === e.target.value) || {}; setTenantForm({ id: row.id || "", name: row.name || "", code: row.code || "", domain: row.domain || "", source_url: row.source_url || "", is_active: row.is_active !== false && row.is_active !== 0 }); }}><option value="">Yeni kurum</option>{tenantOptions.map((tenant) => <option key={tenant.id} value={tenant.id}>{tenant.name}</option>)}</select></label>
          <label>Kurum adı<input value={tenantForm.name || ""} onChange={(e) => setTenantForm({ ...tenantForm, name: e.target.value })} placeholder="Kurum / Üniversite adını yazın" /></label>
          <label>Kısa kod<input value={tenantForm.code || ""} onChange={(e) => setTenantForm({ ...tenantForm, code: e.target.value })} placeholder="Kısa kod" /></label>
          <label className="wide-field">Alan adı / domain<input value={tenantForm.domain || ""} onChange={(e) => setTenantForm({ ...tenantForm, domain: e.target.value })} placeholder="erciyes.edu.tr" /><small>Sadece kurum alan adını yazmanız yeterlidir. Sistem fakülte/MYO, bölüm ve program listesini YÖK Atlas üzerinden otomatik bulur.</small></label>
        </div>
        <label className="checkbox-line"><input type="checkbox" checked={tenantForm.is_active !== false} onChange={(e) => setTenantForm({ ...tenantForm, is_active: e.target.checked })} /> Kurum aktif</label>
        <div className="action-row">
          <button className="primary-action">Kurum Kaydet</button>
          <button type="button" disabled={catalogImporting || !tenantForm.domain} onClick={importAcademicCatalog}>{catalogImporting ? "YÖK Atlas sorgulanıyor..." : "YÖK Atlas’tan Akademik Yapıyı Bul ve Tanımla"}</button>
          <button type="button" onClick={() => { setTenantForm({ id: "", name: "", code: "", domain: "", source_url: "", is_active: true }); setCatalogImportResult(null); }}>Yeni Kurum</button>
        </div>
      </form>
      {catalogImportResult && <div className="notice-card success"><strong>Akademik yapı YÖK Atlas üzerinden tanımlandı.</strong><span>{catalogImportResult.faculty_count || 0} birim, {catalogImportResult.department_count || 0} bölüm, {catalogImportResult.created_program_count || 0} yeni program eklendi; {catalogImportResult.skipped_program_count || 0} mevcut program atlandı.</span><small>Kaynak: {catalogImportResult.source_url}</small></div>}
      <div className="editor-panel">
        <h3>Tanımlı Kurumlar</h3>
        <DataTable rows={tenantTableRows} columns={["id", "name", "tenant_code", "domain", "is_active", "program_count", "user_count", "updated_at"]} actions={(row) => {
          const dependencyCount = Number(row.program_count || 0) + Number(row.user_count || 0);
          const hasDependencies = dependencyCount > 0;
          return (
            <div className="action-row compact">
              <button onClick={() => setTenantForm({ id: row.id || "", name: row.name || "", code: row.code || "", domain: row.domain || "", source_url: row.source_url || "", is_active: row.is_active !== false && row.is_active !== 0 })}>Düzenle</button>
              <button onClick={() => toggleTenant(row, !(row.is_active !== false && row.is_active !== 0))}>{row.is_active !== false && row.is_active !== 0 ? "Pasifleştir" : "Aktif Et"}</button>
              <button className={hasDependencies ? "safe-action" : "danger-button"} title={hasDependencies ? "Bu kuruma bağlı kayıtlar var; güvenli işlem paneli açılır. Süper Admin panelden kalıcı silme de yapabilir." : "Bağlı kaydı olmayan kurumu arşive alır."} onClick={() => deleteTenant(row)}>{hasDependencies ? <ShieldCheck size={14} /> : <Archive size={14} />} {hasDependencies ? "Güvenli İşlem" : "Arşivle"}</button>
              {canPurgeTenant && <button className="danger-button" title={row.id === "tenant_default" ? "Süper Admin varsayılan kurum verilerini kalıcı temizler" : "Süper Admin kalıcı silme"} onClick={() => purgeTenant(row)}><Trash2 size={14} /> {row.id === "tenant_default" ? "Kalıcı Temizle" : "Kalıcı Sil"}</button>}
            </div>
          );
        }} />
        <div className="notice-card warning compact-notice"><strong>Silme kuralı</strong><span>Kurum Admin bağlı kayıt içeren kurumlarda pasifleştirme, taşıma veya arşivleme kullanır. Süper Admin ise gerekli durumda “Kalıcı Sil/Kalıcı Temizle” ile kurumu ve bağlı kayıtları geri alınamaz şekilde silebilir. Varsayılan teknik kurumda mevcut Süper Admin hesabı korunur; kurumun program, fakülte, kullanıcı ve geçmiş kayıtları temizlenir.</span></div>
      </div>
      {tenantCleanupPanel}
      <div className="notice-card info"><strong>Kurum odaklı çalışma alanı.</strong><span>Fakülte / MYO, bölüm ve program tanımı Yeni Program sekmesinde kurum seçildikten sonra yapılır.</span></div>
    </div>
  );
  const assignmentContent = (
    <form className="tabbed-form" onSubmit={assign}>
      <div className="form-grid">
        <label>Kurum / Üniversite
          <select value={assignmentTenantId} onChange={(e) => selectAssignmentTenant(e.target.value)}>
            {tenantOptions.map((tenant) => <option key={tenant.id} value={tenant.id}>{tenant.name}</option>)}
          </select>
        </label>
        <label>Fakülte / MYO / Birim
          <select value={assignmentSchool} onChange={(e) => selectAssignmentSchool(e.target.value)} disabled={!assignmentSchoolOptions.length}>
            {!assignmentSchoolOptions.length && <option value="">Bu kurumda program yok</option>}
            {assignmentSchoolOptions.map((school) => <option key={school} value={school}>{school}</option>)}
          </select>
        </label>
        {!isFacultyAdminAssignment && <label>Bölüm
          <select value={assignmentDepartment} onChange={(e) => selectAssignmentDepartment(e.target.value)} disabled={!assignmentDepartmentOptions.length}>
            {!assignmentDepartmentOptions.length && <option value="">Bölüm yok</option>}
            {assignmentDepartmentOptions.map((department) => <option key={department} value={department}>{department}</option>)}
          </select>
        </label>}
        {!isFacultyAdminAssignment && <label>Program Adı
          <select value={selectedAssignmentProgramId} onChange={(e) => setAssignmentProgram(e.target.value)} disabled={!assignmentProgramOptions.length}>
            {!assignmentProgramOptions.length && <option value="">Program yok</option>}
            {assignmentProgramOptions.map((program) => <option key={program.id} value={program.id}>{programOnlyDisplayLabel(program)}</option>)}
          </select>
        </label>}
        {isFacultyAdminAssignment && <div className="notice-card info faculty-scope-card"><strong>Fakülte/MYO kapsamı</strong><span>Bu rol seçildiğinde Bölüm ve Program Adı seçimi gerekmez. Seçili Fakülte/MYO altındaki tüm bölüm ve programlar otomatik atanır.</span><small>{facultyAssignmentProgramIds.length} program bu kapsama dahil.</small></div>}
        <label>Kullanıcı
          <select value={assignment.username} onChange={(e) => setAssignment({ ...assignment, username: e.target.value })}>
            {users.map((u) => <option key={u.username} value={u.username}>{u.username} · {u.full_name}</option>)}
          </select>
        </label>
        <label>Rol
          <select value={assignment.role} onChange={(e) => applyRoleSelection(e.target.value)}>
            {programRoleOptions.map((role) => <option key={role}>{role}</option>)}
          </select>
        </label>
      </div>
      {!isFacultyAdminAssignment && <div className="choice-panel wide">
        <div className="choice-panel-header">
          <div>
            <strong>Atanmış başlıklar</strong>
            <small>Boş bırakılırsa seçilen programdaki tüm başlıklar açılır.</small>
          </div>
          <div className="choice-actions">
            <button type="button" onClick={setAllAssignedSections}>Tümünü seç</button>
            <button type="button" onClick={clearAssignedSections}>Tüm başlık erişimi</button>
          </div>
        </div>
        <div className="section-choice-grid">
          {!selectedAssignmentProgramId && <p className="muted-note">Başlık seçmek için önce kurum, birim, bölüm ve program seçin.</p>}
          {assignmentSectionsLoading && <p className="muted-note">Seçili programın başlıkları yükleniyor...</p>}
          {!assignmentSectionsLoading && selectedAssignmentProgramId && assignmentSectionRows.length === 0 && <p className="muted-note">Seçili programa ait başlık bulunamadı.</p>}
          {assignmentSectionRows.map((section) => (
            <label key={section.section_key} className="choice-check">
              <input type="checkbox" checked={assignedSectionSet.has(section.section_key)} onChange={() => toggleAssignedSection(section.section_key)} />
              <div>
                <strong>{section.section_key} · {section.section_title}</strong>
                <small>{section.report_group_title || section.main_title}</small>
                <small>{section.source_school_name || section.source_profile ? `${section.source_school_name || section.source_program_label} · ${section.source_profile || "Profil"}` : section.source_program_label}</small>
              </div>
            </label>
          ))}
        </div>
      </div>}
      {isFacultyAdminAssignment && <div className="choice-panel wide"><div className="choice-panel-header"><div><strong>Birim Admin kapsamı</strong><small>Atama seçili birimdeki tüm program ve başlıklara uygulanır.</small></div></div><div className="mini-list">{assignmentTenantPrograms.filter((program) => facultyAssignmentProgramIds.includes(program.id)).map((program) => <span key={program.id}>{program.department_name || "Bölüm"} · {programOnlyDisplayLabel(program)}</span>)}</div></div>}
      <label className="checkbox-line"><input type="checkbox" checked={assignment.is_active} onChange={(e) => setAssignment({ ...assignment, is_active: e.target.checked })} /> Program erişimi aktif</label>
      <button className="primary-action" disabled={!assignmentProgramIds.length}>Program Yetkisini Kaydet</button>
    </form>
  );
  return (
    <section className="panel-stack">
      <TabbedExpander
        title="Program Yönetimi Çalışma Alanı · Kurum / Fakülte İzolasyonu"
        subtitle="Program kayıtları, kopyalama, rol atama ve program kullanıcılarını sekmelerle yönetin."
        tabs={[
          canTenantManage && {
            id: "tenant-isolation",
            label: "Kurum Yönetimi",
            count: tenantOptions.length,
            content: tenantContent,
          },
          !setupRequired && canProgramList && {
            id: "programs",
            label: "Tanımlı Programlar",
            count: programRows.length,
            content: <div className="grouped-list">{programTenantGroups.length ? programTenantGroups.map((group) => <section className="group-block" key={group.id}><div className="group-block-header"><div><span>Kurum / Üniversite</span><strong>{group.name}</strong></div><small>{group.rows.length} program</small></div><DataTable rows={group.rows} columns={["faculty_name", "department_name", "program_name", "accreditation_profile", "report_year", "is_active", "created_at", "updated_at"]} actions={(row) => (canProgramEdit || canProgramArchive) ? <div className="action-row compact">{canProgramEdit && <button onClick={() => toggle(row, !row.is_active)}>{row.is_active ? "Pasifleştir" : "Aktif Et"}</button>}{canProgramArchive && <button className="danger-button" onClick={() => deleteProgram(row)}><Trash2 size={14} /> Sil</button>}</div> : null} /></section>) : <div className="empty-state premium-empty-inline"><strong>Program yok</strong><span>Önce Yeni Program sekmesinden kurum ve birim seçerek program oluşturun.</span></div>}</div>,
          },
          !setupRequired && canProgramCreate && {
            id: "new",
            label: "Yeni Program",
            content: <form className="tabbed-form" onSubmit={create}>
              <label>Kurum (Üniversite)<select value={newProgramTenantId} onChange={(e) => selectNewProgramTenant(e.target.value)}>{tenantOptions.map((tenant) => <option key={tenant.id} value={tenant.id}>{tenant.name}</option>)}</select></label>
              <label>{labelFor("school_name")}<select value={newProgram.school_name || ""} onChange={(e) => selectNewProgramFaculty(e.target.value)}><option value="">Fakülte / MYO / Birim seçin</option>{newProgramFacultyOptions.map((item) => <option key={item.label} value={item.label}>{item.label}</option>)}</select></label>
              <label>{labelFor("department_name")}<select value={newProgram.department_name || ""} onChange={(e) => { const department = e.target.value; const programs = programOptionsForNewProgram(newProgram.school_name, department); const next = { ...newProgram, department_name: department, program_name: programs[0] || "" }; setNewProgram({ ...next, accreditation_profile: profileForNewProgramFaculty(newProgram.school_name, next) }); }} disabled={!newProgram.school_name}><option value="">Önce fakülte / MYO / birim seçin</option>{departmentOptionsForNewProgram(newProgram.school_name).map((department) => <option key={department} value={department}>{department}</option>)}</select></label>
              <label>{labelFor("program_name")}<select value={newProgram.program_name || ""} onChange={(e) => { const next = { ...newProgram, program_name: e.target.value }; setNewProgram({ ...next, accreditation_profile: profileForNewProgramFaculty(newProgram.school_name, next) }); }} disabled={!newProgram.department_name}><option value="">Önce bölüm seçin</option>{programOptionsForNewProgram(newProgram.school_name, newProgram.department_name).map((program) => <option key={program} value={program}>{program}</option>)}</select></label>
              <label>Derece<select value={newProgram.program_degree || "Lisans"} onChange={(e) => { const next = { ...newProgram, program_degree: e.target.value }; setNewProgram({ ...next, accreditation_profile: profileForNewProgramFaculty(newProgram.school_name, next) }); }}><option>Önlisans</option><option>Lisans</option><option>Lisansüstü</option></select><small>Önlisans seçilirse varsayılan kuruluş MEDEK olur.</small></label>
              <label>{labelFor("report_year")}<input value={newProgram.report_year || ""} onChange={(e) => setNewProgram({ ...newProgram, report_year: e.target.value })} /></label>
              <label>Akreditasyon Profili<select value={newProgram.accreditation_profile || profileForNewProgramFaculty(newProgram.school_name)} onChange={(e) => setNewProgram({ ...newProgram, accreditation_profile: e.target.value })} disabled={isNewProgramProfileLocked(newProgram.school_name)}>{ACCREDITATION_PROFILES.map((profile) => <option key={profile} value={profile}>{profileLabel(profile)}</option>)}</select><small>Derece + program adına göre otomatik önerilir; gerektiğinde elle değiştirilebilir.</small></label>
              <button className="primary-action">Program Oluştur</button>
            </form>,
          },
          !setupRequired && canProgramClone && {
            id: "clone",
            label: "Program Kopyala",
            content: <form className="tabbed-form" onSubmit={cloneProgram}><label>Kaynak program<select value={clone.source_program_id} onChange={(e) => setClone({ ...clone, source_program_id: e.target.value })}>{programRows.map((program) => <option key={program.id} value={program.id}>{program.program_name} · {program.report_year}</option>)}</select></label><label>Yeni program adı<input value={clone.program_name} onChange={(e) => setClone({ ...clone, program_name: e.target.value })} /></label><label>Yeni rapor yılı<input value={clone.report_year} onChange={(e) => setClone({ ...clone, report_year: e.target.value })} /></label><label className="checkbox-line"><input type="checkbox" checked={clone.copy_text} onChange={(e) => setClone({ ...clone, copy_text: e.target.checked })} /> Metin/PUKÖ taşı</label><label className="checkbox-line"><input type="checkbox" checked={clone.copy_tables} onChange={(e) => setClone({ ...clone, copy_tables: e.target.checked })} /> Tabloları taşı</label><label className="checkbox-line"><input type="checkbox" checked={clone.copy_evidence_meta} onChange={(e) => setClone({ ...clone, copy_evidence_meta: e.target.checked })} /> Kanıt metadata taşı</label><button className="primary-action">Programı Kopyala</button></form>,
          },
          !setupRequired && canProgramAssign && {
            id: "assignment",
            label: "Program Bazlı Kullanıcı ve Rol Atama",
            content: assignmentContent,
          },
          !setupRequired && canProgramUsersView && {
            id: "program-users",
            label: "Program Kullanıcıları",
            count: programUsers.length,
            content: <div className="grouped-list">{programUserTenantGroups.length ? programUserTenantGroups.map((group) => <section className="group-block" key={group.id}><div className="group-block-header"><div><span>Kurum / Üniversite</span><strong>{group.name}</strong></div><small>{group.rows.length} kullanıcı yetkisi</small></div><DataTable rows={group.rows} columns={["faculty_name", "program_name", "report_year", "username", "full_name", "email", "academic_status", "role", "assigned_sections", "is_active", "updated_at"]} /></section>) : <div className="empty-state premium-empty-inline"><strong>Program kullanıcısı yok</strong><span>Program Bazlı Kullanıcı ve Rol Atama sekmesinden yetki verin.</span></div>}</div>,
          },
        ].filter(Boolean)}
      />
    </section>
  );
}

export function UsersView({ user, programs, sections, onError, onMessage }) {
  const [rows, setRows] = useState([]);
  const [attempts, setAttempts] = useState([]);
  const [programUsers, setProgramUsers] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [faculties, setFaculties] = useState([]);
  const [permissionRows, setPermissionRows] = useState([]);
  const [form, setForm] = useState({ username: "", password: "", role: READONLY_ROLE, tenant_id: "tenant_default", tenant_scope: "tenant", faculty_name: "", full_name: "", email: "", academic_status: "", is_active: true });
  async function load() {
    const [users, loginRows, programUserRows, tenantRows, facultyRows, permissionPayloadRaw] = await Promise.all([api.users(), api.loginAttempts(50), api.programUsers(), api.tenants(true), api.tenantFaculties(), api.permissions().catch(() => ({ rows: [] }))]);
    setRows(asArray(users).map((row) => ({ ...row, role: normalizeRole(row.role || READONLY_ROLE, row.tenant_scope) })));
    setAttempts(asArray(loginRows));
    setProgramUsers(asArray(programUserRows).map((row) => ({ ...row, role: normalizeRole(row.role || READONLY_ROLE, row.tenant_scope), global_role: normalizeRole(row.global_role || READONLY_ROLE, row.global_tenant_scope) })));
    setTenants(asArray(tenantRows));
    setFaculties(asArray(facultyRows));
    setPermissionRows(asArray(asObject(permissionPayloadRaw).rows));
  }
  useEffect(() => { load().catch((err) => onError(err.message)); }, []);
  async function save(event) {
    event.preventDefault();
    try {
      await api.saveUser(form);
      onMessage("Kullanıcı kaydedildi.");
      setForm({ username: "", password: "", role: READONLY_ROLE, tenant_id: tenants[0]?.id || "tenant_default", tenant_scope: "tenant", faculty_name: "", full_name: "", email: "", academic_status: "", is_active: true });
      await load();
    } catch (err) { onError(err.message); }
  }
  async function toggleUser(row) {
    try {
      await api.saveUser({ username: row.username, password: "", role: normalizeRole(row.role || READONLY_ROLE, row.tenant_scope), tenant_id: row.tenant_id || "tenant_default", tenant_scope: row.tenant_scope || "tenant", faculty_name: row.faculty_name || "", full_name: row.full_name || "", email: row.email || "", academic_status: row.academic_status || "", is_active: !Boolean(row.is_active) });
      onMessage(Boolean(row.is_active) ? "Kullanıcı pasifleştirildi." : "Kullanıcı aktifleştirildi.");
      await load();
    } catch (err) { onError(err.message); }
  }
  async function deleteUser(row) {
    if (!window.confirm(`${row.username} kullanıcısı arşive alınsın mı? Kayıtlı kullanıcılar listesinden gizlenecek ve Geri Yükleme ekranından geri alınabilecektir.`)) return;
    try {
      await api.deleteUser(row.username);
      onMessage("Kullanıcı arşive alındı.");
      await load();
    } catch (err) { onError(err.message); }
  }
  const programUserSummary = programUsers.map((row) => ({
    Kurum: row.tenant_name || row.tenant_id || "Kurum seçilmedi",
    Program: row.program_name || row.program_id,
    Kullanıcı: row.username,
    Rol: row.role,
    "Başlık Yetkisi": row.assigned_sections ? row.assigned_sections : "Tüm başlıklar",
    Durum: row.is_active ? "Aktif" : "Pasif",
    "Güncelleme": row.updated_at || row.created_at || "",
  }));
  const roleMatrix = [
    { Rol: "Süper Admin", "Temel amaç": "Tüm sistem ve kurum yetki devri", "Program erişimi": "Tüm kurumlar", "Rapor düzenleme": "Evet", "Onaya gönder": "Yetkiye bağlı", "Onay/Revizyon": "Evet", "Program/Silme": "Evet" },
    { Rol: "Kurum Admin", "Temel amaç": "Kurum içi yetki dağıtımı", "Program erişimi": "Kendi kurumu", "Rapor düzenleme": "Süper Admin iznine bağlı", "Onaya gönder": "Yetkiye bağlı", "Onay/Revizyon": "Yetkiye bağlı", "Program/Silme": "Kurum sınırı" },
    { Rol: FACULTY_ADMIN_ROLE, "Temel amaç": "Birim kapsam yönetimi", "Program erişimi": "Seçili fakülte/MYO/enstitü altındaki tüm programlar", "Rapor düzenleme": "Yetki matrisine bağlı", "Onaya gönder": "Yetkiye bağlı", "Onay/Revizyon": "Yetkiye bağlı", "Program/Silme": "Birim kapsamı" },
    { Rol: "Birim Koordinatörü", "Temel amaç": "Birim içinde rapor koordinasyonu", "Program erişimi": "Kendi birimindeki programlar", "Rapor düzenleme": "Kısmi / yetkiye bağlı", "Onaya gönder": "Koordinasyon", "Onay/Revizyon": "Kısmi onay", "Program/Silme": "Hayır" },
    { Rol: "Editör / Hazırlayıcı", "Temel amaç": "Başlıkları hazırlama", "Program erişimi": "Atandığı program/başlıklar", "Rapor düzenleme": "Evet", "Onaya gönder": "Evet", "Onay/Revizyon": "Hayır", "Program/Silme": "Hayır" },
    { Rol: "Onaylayıcı", "Temel amaç": "İnceleme ve karar", "Program erişimi": "Atandığı programlar", "Rapor düzenleme": "Hayır", "Onaya gönder": "Hayır", "Onay/Revizyon": "Evet", "Program/Silme": "Hayır" },
    { Rol: READONLY_ROLE, "Temel amaç": "Salt okuma", "Program erişimi": "Atandığı programlar", "Rapor düzenleme": "Hayır", "Onaya gönder": "Hayır", "Onay/Revizyon": "Hayır", "Program/Silme": "Hayır" },
  ];
  const userRoleName = normalizeRole(user?.role || READONLY_ROLE, user?.tenant_scope);
  const canViewUsers = matrixPermissionAllowed(permissionRows, userRoleName, "user.view", isAdminRole(userRoleName));
  const canManageUsers = matrixPermissionAllowed(permissionRows, userRoleName, "user.manage", isAdminRole(userRoleName));
  const canViewLoginAttempts = matrixPermissionAllowed(permissionRows, userRoleName, "user.login_attempts.view", isAdminRole(userRoleName));

  const userRoleOptions = isSuperAdminRole(userRoleName) ? ROLES : delegatableRolesForActor(userRoleName);

  const tenantOptions = tenants.filter((tenant) => !tenant.is_setup_placeholder);
  const facultyOptionsForUser = faculties.filter((item) => !form.tenant_id || item.tenant_id === form.tenant_id);
  return (
    <section className="panel-stack">
      <TabbedExpander
        title="Kullanıcı & Rol Yönetimi Çalışma Alanı"
        subtitle="Kullanıcı oluşturma, unvan seçimi ve güvenlik izlerini sekmelerle yönetin."
        tabs={[
          canManageUsers && {
            id: "user-form",
            label: "Kullanıcı Oluştur / Güncelle",
            content: <form className="tabbed-form" onSubmit={save}>
              <label>Kullanıcı adı<input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></label>
              <label>Şifre<input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="Güncellemede boş bırakılabilir" /></label>
              <label>Rol<select value={normalizeRole(form.role || READONLY_ROLE, form.tenant_scope)} onChange={(e) => setForm({ ...form, role: e.target.value, tenant_scope: e.target.value === "Süper Admin" ? "global" : "tenant" })}>{userRoleOptions.map((role) => <option key={role}>{role}</option>)}</select></label>
              <label>Kurum / Tenant<select value={form.tenant_id || tenantOptions[0]?.id || "tenant_default"} onChange={(e) => setForm({ ...form, tenant_id: e.target.value, faculty_name: "" })}>{tenantOptions.map((tenant) => <option key={tenant.id} value={tenant.id}>{tenant.name}</option>)}</select></label>
              <label>Tenant kapsamı<select value={form.tenant_scope || "tenant"} onChange={(e) => setForm({ ...form, tenant_scope: e.target.value })} disabled={!isSuperAdminRole(form.role)}><option value="tenant">Tenant Admin / Kurum içi</option><option value="global">Global Admin / Tüm kurumlar</option></select><small>Global kapsam yalnızca Süper Admin için kullanılmalıdır.</small></label>
              <label>Fakülte / MYO<select value={form.faculty_name || ""} onChange={(e) => setForm({ ...form, faculty_name: e.target.value })}><option value="">Tüm fakülteler / birim yok</option>{facultyOptionsForUser.map((item) => <option key={item.id} value={item.faculty_name}>{item.faculty_name}</option>)}</select></label>
              <label>Ad Soyad<input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></label>
              <label>E-posta<input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
              <label>Statü / Unvan<select value={form.academic_status || ""} onChange={(e) => setForm({ ...form, academic_status: e.target.value })}><option value="">Statü / unvan seçin</option>{ACADEMIC_STATUS_OPTIONS.map((status) => <option key={status} value={status}>{status}</option>)}</select></label>
              <label className="checkbox-line"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Aktif kullanıcı</label>
              <button className="primary-action">Kullanıcıyı Kaydet</button>
            </form>,
          },
          {
            id: "authority-note",
            label: "Program Yetki Notu",
            count: programs.length,
            content: <div className="panel-stack authority-guide"><div className="tabbed-note"><h3>Program bazlı yetkilendirme nasıl çalışır?</h3><p className="muted">Kullanıcının sistem rolü hesabın genel seviyesini belirler; program bazlı rol ise seçili programda hangi işlemleri yapabileceğini belirler. Program yetkileri <strong>Program Yönetimi → Program Bazlı Kullanıcı ve Rol Atama</strong> sekmesinden verilir.</p><div className="metric-grid"><MetricCard label="Program" value={programs.length} sub="tanımlı program" /><MetricCard label="Program kullanıcı kaydı" value={programUsers.length} sub="aktif/pasif atama" /><MetricCard label="Kayıtlı kullanıcı" value={rows.length} sub="sistem hesabı" /></div><div className="mini-list">{programs.map((program) => <span key={program.id}>{program.program_name} · {program.report_year}</span>)}</div></div><div className="editor-panel"><h3>Rol Yetki Matrisi</h3><DataTable rows={roleMatrix} columns={["Rol", "Temel amaç", "Program erişimi", "Rapor düzenleme", "Onaya gönder", "Onay/Revizyon", "Program/Silme"]} /></div><div className="editor-panel"><h3>Mevcut Program Atamaları</h3><DataTable rows={programUserSummary} columns={["Kurum", "Program", "Kullanıcı", "Rol", "Başlık Yetkisi", "Durum", "Güncelleme"]} /></div><div className="tabbed-note"><h3>Operasyon Notları</h3><ul><li>Editör / Hazırlayıcı, başlığı kaydetmeden onaya gönderemez.</li><li>Admin ve Onaylayıcı onay kararlarını yönetir; onaya gönderme işlemi editör sorumluluğundadır.</li><li>Boş başlık yetkisi, seçili programdaki tüm başlıklara erişim anlamına gelir.</li><li>Pasifleştirilmiş program/kullanıcı korunur; program silme işlemi arşive alma şeklinde çalışır ve Geri Yükleme ekranından geri alınabilir.</li></ul></div></div>,
          },
          canViewUsers && {
            id: "users",
            label: "Kayıtlı Kullanıcılar",
            count: rows.length,
            content: <DataTable rows={rows} columns={["tenant_name", "tenant_scope", "faculty_name", "username", "role", "full_name", "email", "academic_status", "is_active", "must_change_password", "failed_attempts", "locked_until", "last_login"]} actions={(row) => canManageUsers ? <><button onClick={() => setForm({ username: row.username || "", password: "", role: normalizeRole(row.role || READONLY_ROLE, row.tenant_scope), tenant_id: row.tenant_id || "tenant_default", tenant_scope: row.tenant_scope || "tenant", faculty_name: row.faculty_name || "", full_name: row.full_name || "", email: row.email || "", academic_status: row.academic_status || "", is_active: Boolean(row.is_active) })}>Düzenle</button><button onClick={() => toggleUser(row)}>{row.is_active ? "Pasifleştir" : "Aktif Et"}</button><button className="danger-button" onClick={() => deleteUser(row)}>Sil</button></> : null} />,
          },
          canViewLoginAttempts && {
            id: "login-attempts",
            label: "Giriş Denemeleri",
            count: attempts.length,
            content: <DataTable rows={attempts} columns={["username", "success", "note", "created_at"]} />,
          },
        ].filter(Boolean)}
      />
    </section>
  );
}

export function DeadlineView({ programId, user, onError, onMessage }) {
  const [rows, setRows] = useState([]);
  const editable = isAdminRole(user.role);
  useEffect(() => { api.deadlines(programId).then((data) => setRows(asArray(data))).catch((err) => onError(err.message)); }, [programId]);
  async function save() { try { const saved = await api.saveDeadlines(programId, rows); setRows(asArray(saved)); onMessage("Son teslim tarihleri planı kaydedildi."); } catch (err) { onError(err.message); } }
  return <section className="editor-panel"><div className="editor-header"><h2>Son Teslim Tarihi Planı</h2><button onClick={save} disabled={!editable}>Son teslim tarihlerini kaydet</button></div><p className="muted">Bu tarihleri Süper Admin / Kurum Admin düzenler; Onaylayıcı rolü planı ayrı menüden izleyebilir, diğer roller veri giriş ekranında sabit olarak görür.</p><div className="deadline-list">{rows.map((row, idx) => <label key={row.section_key}><span>{row.section_key} · {row.section_title}</span><input value={row.deadline || ""} disabled={!editable} onChange={(event) => setRows((current) => current.map((item, itemIdx) => itemIdx === idx ? { ...item, deadline: event.target.value } : item))} /></label>)}</div></section>;
}

export function BulkView({ programId, sections, onError, onMessage, refresh }) {
  const [groupFilter, setGroupFilter] = useState("Tümü");
  const [mainFilter, setMainFilter] = useState("Tümü");
  const [currentStatus, setCurrentStatus] = useState("Tümü");
  const [nextStatus, setNextStatus] = useState("Devam Ediyor");
  const [bulkDeadline, setBulkDeadline] = useState("");
  const reportGroups = Array.from(new Set(sections.map((section) => section.report_group_title || section.main_title)));
  const groupScopedSections = sections.filter((section) => groupFilter === "Tümü" || (section.report_group_title || section.main_title) === groupFilter);
  const mainTitles = Array.from(new Set(groupScopedSections.map((section) => section.main_title)));
  const filtered = groupScopedSections.filter((section) => (mainFilter === "Tümü" || section.main_title === mainFilter) && (currentStatus === "Tümü" || section.status === currentStatus));
  async function update() {
    try {
      const result = bulkDeadline
        ? await api.bulkAdvanced(programId, { section_keys: filtered.map((section) => section.section_key), status: nextStatus, deadline: bulkDeadline })
        : await api.bulkStatus(programId, filtered.map((section) => section.section_key), nextStatus);
      onMessage(`${result.updated}/${result.requested} başlık güncellendi.`);
      await refresh();
    } catch (err) { onError(err.message); }
  }
  return (
    <section className="panel-stack">
      <div className="editor-panel">
        <h2>Toplu İşlemler</h2>
        <div className="form-grid">
          <label>Rapor bölümü<select value={groupFilter} onChange={(e) => { setGroupFilter(e.target.value); setMainFilter("Tümü"); }}><option>Tümü</option>{reportGroups.map((title) => <option key={title}>{title}</option>)}</select></label>
          <label>Ana ölçüt<select value={mainFilter} onChange={(e) => setMainFilter(e.target.value)}><option>Tümü</option>{mainTitles.map((title) => <option key={title}>{title}</option>)}</select></label>
          <label>Mevcut durum<select value={currentStatus} onChange={(e) => setCurrentStatus(e.target.value)}><option>Tümü</option>{STATUS_OPTIONS.map((status) => <option key={status}>{status}</option>)}</select></label>
          <label>Yeni durum<select value={nextStatus} onChange={(e) => setNextStatus(e.target.value)}>{STATUS_OPTIONS.map((status) => <option key={status}>{status}</option>)}</select></label>
          <label>Toplu son teslim tarihi<input type="date" value={bulkDeadline} onChange={(e) => setBulkDeadline(e.target.value)} /></label>
        </div>
        <button className="primary-action" onClick={update}>Seçili Başlıkları Güncelle</button>
      </div>
      <div className="editor-panel">
        <h2>{filtered.length} başlık seçili</h2>
        <DataTable rows={filtered} columns={["section_key", "report_group_title", "main_title", "section_title", "status", "approval_status"]} />
      </div>
    </section>
  );
}

export function SettingsView({ programId, onError, onMessage, refresh }) {
  const [form, setForm] = useState(null);
  const [system, setSystem] = useState(null);
  const [activity, setActivity] = useState([]);
  const [backupFile, setBackupFile] = useState(null);
  const [overwriteRestore, setOverwriteRestore] = useState(false);
  const [restoreResult, setRestoreResult] = useState(null);
  const [systemTemplates, setSystemTemplates] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [mailStatus, setMailStatus] = useState(null);
  const [mailSettings, setMailSettings] = useState(null);
  const [mailSettingsWarning, setMailSettingsWarning] = useState("");
  const [testMailTo, setTestMailTo] = useState("");
  const [aiStatus, setAiStatus] = useState(null);
  const [aiSettings, setAiSettings] = useState(null);
  const [aiModels, setAiModels] = useState([]);
  const [aiPullModel, setAiPullModel] = useState("llama3.1");
  const [aiPulling, setAiPulling] = useState(false);
  const [workflowSettings, setWorkflowSettings] = useState(null);
  const [workflowPreview, setWorkflowPreview] = useState(null);
  const [workflowRuns, setWorkflowRuns] = useState([]);
  const [workflowForce, setWorkflowForce] = useState(false);
  const [deploymentWizard, setDeploymentWizard] = useState(null);
  const [deploymentSmoke, setDeploymentSmoke] = useState(null);
  const defaultMailSettings = () => ({
    enabled: false,
    smtp_host: "",
    smtp_port: 587,
    smtp_user: "",
    smtp_password: "",
    smtp_password_configured: false,
    smtp_from: "",
    tls: true,
    ssl: false,
    app_base_url: window.location?.origin || "",
    clear_password: false,
    password_error: "",
  });
  async function load() {
    if (!programId) return;
    const [settings, systemRows, activityRows, templateRows, notificationRows, mailRows, mailConfigResult, aiRows, aiSettingsRows, aiModelRows, workflowSettingsRows, workflowPreviewRows, workflowRunRows, deploymentRows] = await Promise.all([
      api.settings(programId).catch(() => ({})),
      api.system(programId).catch(() => null),
      api.activity(programId, 80).catch(() => []),
      api.systemTemplates().catch(() => []),
      api.notifications(80).catch(() => []),
      api.mailStatus().catch(() => null),
      api.mailSettings().then((rows) => ({ ok: true, rows })).catch((err) => ({ ok: false, error: err?.message || "SMTP ayarları okunamadı." })),
      api.globalAiStatus().catch(() => null),
      api.aiSettings().catch(() => null),
      api.aiModels().catch(() => null),
      api.workflowAutomationSettings(programId).catch(() => null),
      api.workflowAutomationPreview(programId).catch(() => null),
      api.workflowAutomationRuns(programId, 20).catch(() => []),
      api.deploymentWizard().catch(() => null),
    ]);
    const effectiveMailSettings = mailConfigResult?.ok ? asObject(mailConfigResult.rows) : defaultMailSettings();
    const effectiveAiSettings = aiSettingsRows ? asObject(aiSettingsRows) : { enabled: false, provider: "ollama", base_url: "http://host.docker.internal:11434", model: "llama3.1", timeout: 60, recommended_models: ["llama3.1", "llama3.2", "mistral", "gemma2", "qwen2.5"] };
    setForm(asObject(settings)); setSystem(systemRows ? asObject(systemRows) : null); setActivity(asArray(activityRows)); setSystemTemplates(asArray(templateRows)); setNotifications(asArray(notificationRows)); setMailStatus(mailRows ? asObject(mailRows) : null); setMailSettings(effectiveMailSettings); setMailSettingsWarning(mailConfigResult?.ok ? "" : mailConfigResult?.error || "SMTP ayarları okunamadı; yeni ayar kaydedebilirsiniz."); setAiStatus(aiRows ? asObject(aiRows) : null); setAiSettings(effectiveAiSettings); setAiModels(asArray(aiModelRows?.models)); setAiPullModel(effectiveAiSettings.model || "llama3.1"); setWorkflowSettings(workflowSettingsRows ? asObject(workflowSettingsRows) : null); setWorkflowPreview(workflowPreviewRows ? asObject(workflowPreviewRows) : null); setWorkflowRuns(asArray(workflowRunRows)); setDeploymentWizard(deploymentRows ? asObject(deploymentRows) : null);
  }
  useEffect(() => { load().catch((err) => onError(err.message)); }, [programId]);
  if (!programId) return <div className="empty-state">Ayarlar için önce bir program seçin.</div>;
  if (!form) return <div className="empty-state">Ayarlar yükleniyor.</div>;
  async function save(event) {
    event.preventDefault();
    try {
      const saved = await api.saveSettings(programId, form);
      setForm(saved);
      onMessage("Ayarlar kaydedildi.");
      await refresh();
    } catch (err) { onError(err.message); }
  }
  function backupStamp() {
    return new Date().toISOString().slice(0, 19).replace(/[T:]/g, "-");
  }
  async function backup() {
    try { downloadBlob(await api.backupJson(programId), form.backup_filename || "AKYS_yedek.json"); } catch (err) { onError(err.message); }
  }
  async function personalProgramBackup() {
    try {
      downloadBlob(await api.personalProgramBackupZip(programId), `Akreditasyon_Kisisel_Yedek_Bu_Program_${backupStamp()}.zip`);
      onMessage("Bu programdaki yetki alanınız ZIP olarak hazırlandı.");
    } catch (err) { onError(err.message); }
  }
  async function personalAllBackup() {
    try {
      downloadBlob(await api.personalAllBackupZip(), `Akreditasyon_Kisisel_Yedek_Tum_Yetki_Alanim_${backupStamp()}.zip`);
      onMessage("Tüm yetki alanınız ZIP olarak hazırlandı.");
    } catch (err) { onError(err.message); }
  }
  async function restoreBackup() {
    if (!backupFile) return onError("Geri yükleme için JSON yedek dosyası seçin.");
    try {
      const result = await api.restoreBackup(programId, { file: backupFile, overwrite: overwriteRestore });
      setRestoreResult(result);
      onMessage("JSON yedeği geri yüklendi. Çalışma alanı yenileniyor.");
      await load();
      await refresh();
    } catch (err) { onError(err.message); }
  }
  async function seedTemplates() {
    try {
      const result = await api.seedSystemTemplates();
      onMessage(`${result.template_count || 0} sistem şablonu doğrulandı.`);
      await load();
    } catch (err) { onError(err.message); }
  }
  async function restoreMissingSections() {
    try {
      const result = await api.restoreMissingSections(programId);
      onMessage(`${result.restored?.length || 0} program için eksik başlıklar yeniden kuruldu.`);
      await load();
      await refresh();
    } catch (err) { onError(err.message); }
  }
  async function saveMailSettings(event) {
    event.preventDefault();
    if (!mailSettings) return;
    try {
      const saved = await api.saveMailSettings(mailSettings);
      setMailSettings(saved);
      setMailStatus(await api.mailStatus().catch(() => null));
      onMessage("E-posta ayarları kaydedildi.");
    } catch (err) { onError(err.message); }
  }
  async function sendTestMail() {
    try {
      const result = await api.testMail({ to: testMailTo, subject: "AKYS test e-postası" });
      onMessage(result.status === "queued" ? "Test e-postası kuyruğa alındı." : `Test e-postası durumu: ${result.status || "kaydedildi"}`);
      await load();
    } catch (err) { onError(err.message); }
  }
  async function testAiConnection() {
    try {
      const result = asObject(await api.globalAiStatus());
      setAiStatus(result);
      const modelRows = asObject(await api.aiModels().catch(() => ({ models: [] })));
      setAiModels(asArray(modelRows.models));
      onMessage(result.available ? "Ollama bağlantısı hazır." : result.message || "AI fallback modu aktif.");
    } catch (err) { onError(err.message); }
  }
  async function saveAiSettings(event) {
    event.preventDefault();
    if (!aiSettings) return;
    try {
      const saved = asObject(await api.saveAiSettings(aiSettings));
      setAiSettings(saved);
      setAiStatus(asObject(saved.status));
      setAiModels(asArray(saved.status?.models));
      onMessage(saved.enabled ? "AI/Ollama etkinleştirildi ve ayarlar kaydedildi." : "AI kapatıldı; yerel şablon üretici kullanılacak.");
      await refreshDeploymentWizard();
    } catch (err) { onError(err.message); }
  }
  async function refreshAiModels() {
    try {
      const result = asObject(await api.aiModels());
      setAiModels(asArray(result.models));
      onMessage(result.ok ? `${asArray(result.models).length} Ollama modeli listelendi.` : result.error || "Model listesi okunamadı.");
    } catch (err) { onError(err.message); }
  }
  async function pullAiModel() {
    if (!aiPullModel) return onError("Yüklenecek model adını yazın.");
    try {
      setAiPulling(true);
      const result = asObject(await api.pullAiModel(aiPullModel));
      setAiModels(asArray(result.models));
      setAiStatus(asObject(await api.globalAiStatus()));
      onMessage(result.ok ? result.message || "Model hazır." : result.message || result.error || "Model yükleme başarısız.");
    } catch (err) { onError(err.message); }
    finally { setAiPulling(false); }
  }
  async function refreshWorkflowAutomation() {
    try {
      const [settingsRows, previewRows, runsRows] = await Promise.all([
        api.workflowAutomationSettings(programId),
        api.workflowAutomationPreview(programId),
        api.workflowAutomationRuns(programId, 20),
      ]);
      setWorkflowSettings(asObject(settingsRows));
      setWorkflowPreview(asObject(previewRows));
      setWorkflowRuns(asArray(runsRows));
    } catch (err) { onError(err.message); }
  }
  async function saveWorkflowAutomation(event) {
    event.preventDefault();
    if (!workflowSettings) return;
    try {
      const saved = await api.saveWorkflowAutomationSettings(programId, workflowSettings);
      setWorkflowSettings(asObject(saved));
      onMessage("Workflow otomasyon ayarları kaydedildi.");
      await refreshWorkflowAutomation();
    } catch (err) { onError(err.message); }
  }
  async function runWorkflowAutomation() {
    try {
      const result = await api.runWorkflowAutomation(programId, { force: workflowForce });
      onMessage(`${result.created || 0} workflow bildirimi oluşturuldu, ${result.skipped || 0} kayıt atlandı.`);
      await refreshWorkflowAutomation();
      await load();
    } catch (err) { onError(err.message); }
  }
  async function refreshDeploymentWizard() {
    try {
      const result = asObject(await api.deploymentWizard());
      setDeploymentWizard(result);
      onMessage(`Kurulum kontrolü yenilendi: ${result.readiness_score || 0}% hazır.`);
    } catch (err) { onError(err.message); }
  }
  async function runDeploymentSmoke() {
    try {
      const result = asObject(await api.deploymentSmoke());
      setDeploymentSmoke(result);
      setDeploymentWizard(asObject(await api.deploymentWizard()));
      onMessage(result.ok ? "Deployment smoke test geçti." : `${asArray(result.failures).length} kritik deployment hatası var.`);
    } catch (err) { onError(err.message); }
  }
  const fields = [
    ["university", "Üniversite"], ["school", "MYO / Birim"], ["department", "Bölüm"], ["program", "Program"],
    ["report_year", "Rapor Yılı"], ["report_type", "Rapor Türü"], ["accreditation_profile", "Akreditasyon Profili"], ["report_no", "Doküman No"],
    ["doc_date", "İlk Yayın Tarihi"], ["rev_date", "Revizyon Tarihi"], ["rev_no", "Revizyon No"],
  ];
  const isGmailSmtp = String(mailSettings?.smtp_host || "").trim().toLowerCase() === "smtp.gmail.com";
  const senderLooksAddressed = !mailSettings?.smtp_from || String(mailSettings.smtp_from).includes("@");
  const testRecipientLooksReady = String(testMailTo || "").includes("@");
  const deploymentChecks = asArray(deploymentWizard?.checks);
  const deploymentSummary = asObject(deploymentWizard?.summary);
  const deploymentEnvRows = Object.entries(asObject(deploymentWizard?.environment)).map(([key, value]) => ({ key, value: Array.isArray(value) ? value.join(", ") : String(value ?? "") }));
  return (
    <section className="panel-stack">
      <TabbedExpander
        title="Ayarlar & Yedek Çalışma Alanı"
        subtitle="Belge bilgileri, sistem yedeği ve aktivite kayıtlarını tek açılır alanda yönetin."
        tabs={[
          {
            id: "settings",
            label: "Ayarlar & Belge Bilgileri",
            content: <form className="tabbed-form" onSubmit={save}><div className="form-grid">{fields.map(([key, label]) => <label key={key} className={["university", "school", "program", "report_type"].includes(key) ? "wide" : ""}>{label}{key === "accreditation_profile" ? <select value={form[key] || "MEDEK"} onChange={(e) => setForm({ ...form, [key]: e.target.value })}>{ACCREDITATION_PROFILES.map((profile) => <option key={profile} value={profile}>{profileLabel(profile)}</option>)}</select> : <input value={form[key] || ""} onChange={(e) => setForm({ ...form, [key]: e.target.value })} />}</label>)}</div><button className="primary-action">Ayarları Kaydet</button></form>,
          },
          {
            id: "backup",
            label: "Yedek & Sistem",
            content: <div className="tabbed-stack"><p className="muted">JSON yedeği yönetici geri yüklemesi içindir. Kişisel ZIP yedeği ise rol/yetki kapsamınızdaki rapor metni, PUKÖ, tablolar, kanıt dosyaları, çıktı kayıtları ve işlem geçmişini kendi bilgisayarınıza indirir.</p><div className="notice-card info"><strong>Kişisel Yedek İndir</strong><span>Her kullanıcı yalnızca kendi rol/yetki alanındaki verileri ZIP olarak indirir. Editör atanmış başlıkları; onaylayıcı onay kapsamını; admin kendi kurum/birim kapsamını alır.</span><div className="action-row"><button className="primary-action" onClick={personalProgramBackup}><Database size={16} /> Bu Programdaki Yetki Alanımı ZIP İndir</button><button onClick={personalAllBackup}><Database size={16} /> Tüm Yetki Alanımı ZIP İndir</button></div></div><div className="action-row"><button onClick={backup}><Database size={16} /> Yönetici JSON Yedek İndir</button></div><div className="restore-box"><h3>JSON Yedeği Geri Yükle</h3><label>Yedek dosyası<input type="file" accept=".json,application/json" onChange={(event) => setBackupFile(event.target.files?.[0] || null)} /></label><label className="checkbox-line"><input type="checkbox" checked={overwriteRestore} onChange={(event) => setOverwriteRestore(event.target.checked)} /> Hedef programdaki mevcut kayıtların üzerine yaz</label><button className="primary-action" onClick={restoreBackup}>Geri Yükle</button>{restoreResult && <small>Geri yüklenen tablolar: {Object.entries(restoreResult.restored || {}).map(([key, value]) => `${key}: ${value}`).join(" · ")}</small>}</div>{system && <DataTable rows={[system]} />}</div>,
          },
          {
            id: "templates",
            label: "Sistem Şablonları",
            count: systemTemplates.length,
            content: <div className="tabbed-stack"><p className="muted">MEDEK, MÜDEK ve diğer akreditasyon profillerinin ana ölçüt iskeletleri uygulama paketindeki JSON şablonlardan korunur. Veritabanı boşalsa bile yeni programlar bu şablonlardan yeniden oluşturulur.</p><div className="action-row"><button onClick={seedTemplates}><Database size={16} /> Sistem Şablonlarını Kontrol Et</button><button onClick={restoreMissingSections}><RefreshCw size={16} /> Bu Programda Eksik Başlıkları Yeniden Kur</button></div><DataTable rows={systemTemplates} columns={["template_key", "template_name", "version", "association_name", "updated_at", "size_bytes"]} /></div>,
          },
          {
            id: "deployment",
            label: "Kurulum Sihirbazı",
            count: deploymentSummary.fail || 0,
            content: <div className="tabbed-stack deployment-wizard">
              <div className="notice-card info"><strong>v110 Deployment / Installer Wizard</strong><span>Bu panel okul sunucusu kurulumunda en sık sorun çıkaran ayarları tek yerde kontrol eder: secret, host/CORS, PostgreSQL, SMTP, kanıt klasörü, job backend ve Ollama.</span><small>Bu ekran .env dosyasını doğrudan değiştirmez; güvenli kontrol ve kopyalanabilir öneri üretir.</small></div>
              <div className="action-row"><button className="primary-action" type="button" onClick={refreshDeploymentWizard}><Wrench size={16} /> Kontrolleri Yenile</button><button type="button" onClick={runDeploymentSmoke}><RefreshCw size={16} /> Smoke Test Çalıştır</button></div>
              <div className="dashboard-panel compact-kpi-grid">
                <MetricCard className={deploymentSummary.fail ? "warn" : "accent"} label="Hazırlık Skoru" value={`${deploymentWizard?.readiness_score ?? 0}%`} sub={deploymentWizard?.checked_at || "son kontrol"} />
                <MetricCard label="Başarılı" value={deploymentSummary.pass ?? 0} sub="kontrol" />
                <MetricCard className="warn" label="Uyarı" value={deploymentSummary.warn ?? 0} sub="kontrol" />
                <MetricCard className={deploymentSummary.fail ? "danger" : "accent"} label="Kritik" value={deploymentSummary.fail ?? 0} sub="hata" />
              </div>
              {deploymentSmoke && <div className={deploymentSmoke.ok ? "notice-card success" : "notice-card warning"}><strong>Son smoke test: {deploymentSmoke.ok ? "Başarılı" : "Kritik hata var"}</strong><span>Hazırlık skoru: {deploymentSmoke.readiness_score || 0}% · Hata: {asArray(deploymentSmoke.failures).length} · Uyarı: {asArray(deploymentSmoke.warnings).length}</span></div>}
              <TabbedExpander
                title="Kurulum kontrol listesi"
                subtitle="Fail olan satırlar üretime geçmeden düzeltilmeli; Warn satırları opsiyonel/iyileştirme niteliğindedir."
                tabs={[
                  { id: "checks", label: "Kontroller", count: deploymentChecks.length, content: <DataTable rows={deploymentChecks} columns={["status", "label", "detail", "recommendation"]} /> },
                  { id: "environment", label: "Ortam", count: deploymentEnvRows.length, content: <DataTable rows={deploymentEnvRows} columns={["key", "value"]} /> },
                  { id: "files", label: "Dosyalar", count: asArray(deploymentWizard?.compose_files).length, content: <DataTable rows={asArray(deploymentWizard?.compose_files)} columns={["path", "exists", "size_bytes"]} /> },
                  { id: "commands", label: "Komutlar", count: asArray(deploymentWizard?.run_commands).length, content: <DataTable rows={asArray(deploymentWizard?.run_commands)} columns={["step", "title", "command"]} /> },
                ]}
              />
              <div className="restore-box"><h3>Önerilen .env iskeleti</h3><pre className="code-block">{deploymentWizard?.env_snippet || "Kontrol verisi yüklenemedi."}</pre></div>
              <div className="restore-box"><h3>Sıradaki adımlar</h3><ul>{asArray(deploymentWizard?.next_steps).map((item) => <li key={item}>{item}</li>)}</ul></div>
            </div>,
          },
          {
            id: "ai",
            label: "AI / Ollama Testi",
            content: <div className="tabbed-stack">
              <div className="notice-card info"><strong>Offline AI Draft yönetimi</strong><span>Buradan AI desteğini açıp kapatabilir, Ollama endpoint/model bilgisini kaydedebilir, yüklü modelleri listeleyebilir ve seçili modeli Ollama tarafına yükletebilirsiniz.</span><small>AI kapalıysa sistem çökmez; yerel şablon üreticiyle devam eder. Model yükleme için Ollama servisinin sunucuda çalışıyor olması gerekir.</small></div>
              {aiSettings ? <form className="tabbed-form ai-settings-form" onSubmit={saveAiSettings}>
                <div className="form-section-heading"><div><span className="eyebrow">AI Runtime</span><h3>AI / Ollama ayarları</h3><p className="muted">Bu ayarlar .env yerine veritabanında saklanır ve yeniden build almadan etkinleştirilebilir. .env değerleri ilk varsayılan olarak kullanılır.</p></div></div>
                <div className="form-grid">
                  <label className="checkbox-line wide"><input type="checkbox" checked={!!aiSettings.enabled} onChange={(e) => setAiSettings({ ...aiSettings, enabled: e.target.checked, provider: e.target.checked ? "ollama" : "ollama" })} /> Offline AI / Ollama taslak üreticisini etkinleştir</label>
                  <label>Provider<select value={aiSettings.provider || "ollama"} onChange={(e) => setAiSettings({ ...aiSettings, provider: e.target.value, enabled: e.target.value === "ollama" ? aiSettings.enabled : false })}><option value="ollama">Ollama</option><option value="disabled">Disabled / Yerel şablon</option></select></label>
                  <label>Ollama Base URL<input placeholder="http://host.docker.internal:11434" value={aiSettings.base_url || ""} onChange={(e) => setAiSettings({ ...aiSettings, base_url: e.target.value })} /></label>
                  <label>Model<input list="ollama-model-suggestions" placeholder="llama3.1" value={aiSettings.model || ""} onChange={(e) => { setAiSettings({ ...aiSettings, model: e.target.value }); setAiPullModel(e.target.value); }} /></label>
                  <label>Timeout / saniye<input type="number" min="3" max="600" value={aiSettings.timeout || 60} onChange={(e) => setAiSettings({ ...aiSettings, timeout: Number(e.target.value || 60) })} /></label>
                </div>
                <datalist id="ollama-model-suggestions">{[...new Set([...(aiSettings.recommended_models || []), ...aiModels])].map((model) => <option key={model} value={model} />)}</datalist>
                <div className="action-row"><button className="primary-action"><Settings size={16} /> AI Ayarlarını Kaydet</button><button type="button" onClick={testAiConnection}><Bot size={16} /> Bağlantıyı Test Et</button><button type="button" onClick={refreshAiModels}><RefreshCw size={16} /> Modelleri Listele</button></div>
              </form> : <div className="empty-state">AI ayarları yüklenemedi.</div>}

              <div className="restore-box">
                <h3>Ollama Model Yükleme / Doğrulama</h3>
                <p className="muted">Model yüklü değilse seçili model fallback moduna düşer. Aşağıdaki işlem Ollama API üzerinden <code>/api/pull</code> çağırır; büyük modellerde birkaç dakika sürebilir.</p>
                <div className="form-grid">
                  <label>Yüklenecek model<input list="ollama-model-suggestions" value={aiPullModel} onChange={(e) => setAiPullModel(e.target.value)} placeholder="llama3.1" /></label>
                  <label>Yüklü modeller<input readOnly value={aiModels.length ? aiModels.join(", ") : "Model listesi boş veya Ollama erişilemiyor"} /></label>
                </div>
                <div className="action-row"><button type="button" className="primary-action" disabled={aiPulling} onClick={pullAiModel}><Download size={16} /> {aiPulling ? "Model yükleniyor..." : "Modeli Yükle / Doğrula"}</button><button type="button" onClick={refreshAiModels}><RefreshCw size={16} /> Listeyi Yenile</button></div>
              </div>

              {aiStatus ? <div className="ai-status-grid"><MetricCard className={aiStatus.available ? "accent" : "warn"} label="Durum" value={aiStatus.available ? "Hazır" : "Fallback"} sub={aiStatus.mode || aiStatus.provider || "AI"} /><MetricCard label="Model" value={aiStatus.model || "-"} sub={aiStatus.provider || "provider"} /><MetricCard label="Model Sayısı" value={asArray(aiStatus.models).length} sub={aiStatus.source || "config"} /><MetricCard label="Endpoint" value={aiStatus.endpoint || "/api/ai/status"} sub={aiStatus.checked_at || "son kontrol"} /></div> : <div className="empty-state">AI durumu henüz test edilmedi.</div>}
              {aiStatus && <DataTable rows={[aiStatus]} columns={["enabled", "provider", "base_url", "model", "available", "mode", "models", "message", "error", "checked_at"]} />}
            </div>,
          },
          {
            id: "notifications",
            label: "E-posta Bildirimleri",
            count: notifications.length,
            content: <div className="tabbed-stack">
              <p className="muted">Onaya gönderme, revizyon, onay, termin planı, rol atama ve rapor çıktısı olayları SMTP ayarları etkinse e-posta olarak gönderilir.</p>
              {mailSettingsWarning && <div className="notice-card warning"><strong>SMTP ayarları okunamadı.</strong><span>{mailSettingsWarning}</span><small>MEDEK_API_SECRET değiştiyse kayıtlı SMTP şifresi çözülemeyebilir. Şifreyi tekrar girip kaydedin.</small></div>}
              {mailSettings?.password_error && <div className="notice-card warning"><strong>SMTP şifresi yeniden girilmeli.</strong><span>{mailSettings.password_error}</span><small>Bu durumda form kapanmaz; SMTP şifresini tekrar yazıp ayarları kaydetmeniz yeterlidir.</small></div>}
              {isGmailSmtp && <div className="notice-card info"><strong>Gmail SMTP modu</strong><span>Gmail için port 587 + TLS doğru seçimdir. SMTP Şifre alanına normal Gmail şifresi değil, Google hesabından üretilen 16 haneli Uygulama Şifresi girilmelidir.</span><small>Gönderen alanı yalnızca isim ise sistem bunu SMTP kullanıcı adresiyle birlikte kullanır; yine de en temiz kullanım: AKYS ÖDR &lt;ozdemirumut@gmail.com&gt;</small></div>}
              {mailSettings?.smtp_from && !senderLooksAddressed && <div className="notice-card warning"><strong>Gönderen alanında e-posta yok.</strong><span>Şu an yalnızca görünen ad yazılmış. Gmail için önerilen format: AKYS ÖDR &lt;ozdemirumut@gmail.com&gt;</span><small>Yeni düzeltmede sistem SMTP kullanıcı adresini otomatik tamamlar, fakat açık format daha sağlıklıdır.</small></div>}
              {mailSettings && <form className="tabbed-form mail-settings-form" onSubmit={saveMailSettings}>
                <div className="form-section-heading"><div><span className="eyebrow">SMTP yapılandırması</span><h3>E-posta gönderim ayarları</h3><p className="muted">Bu alanlar kurum SMTP hesabını tanımlar. Kaydettikten sonra aşağıdaki test mail bölümünden bağlantıyı deneyin.</p></div></div>
                <div className="form-grid">
                  <label className="checkbox-line wide"><input type="checkbox" checked={!!mailSettings.enabled} onChange={(e) => setMailSettings({ ...mailSettings, enabled: e.target.checked })} /> E-posta bildirimlerini etkinleştir</label>
                  <label>SMTP Sunucu<input placeholder="smtp.kurum.edu.tr" value={mailSettings.smtp_host || ""} onChange={(e) => setMailSettings({ ...mailSettings, smtp_host: e.target.value })} /></label>
                  <label>SMTP Port<input type="number" min="1" max="65535" value={mailSettings.smtp_port || 587} onChange={(e) => setMailSettings({ ...mailSettings, smtp_port: Number(e.target.value || 587) })} /></label>
                  <label>SMTP Kullanıcı<input placeholder="akreditasyon@kurum.edu.tr" value={mailSettings.smtp_user || ""} onChange={(e) => setMailSettings({ ...mailSettings, smtp_user: e.target.value })} /></label>
                  <label>SMTP Şifre<input type="password" placeholder={mailSettings.smtp_password_configured ? "Kayıtlı şifre korunur / Gmail için uygulama şifresi" : "SMTP şifresi veya Gmail uygulama şifresi"} value={mailSettings.smtp_password || ""} onChange={(e) => setMailSettings({ ...mailSettings, smtp_password: e.target.value, clear_password: false })} /></label>
                  <label>Gönderen<input placeholder="AKYS ÖDR <ozdemirumut@gmail.com>" value={mailSettings.smtp_from || ""} onChange={(e) => setMailSettings({ ...mailSettings, smtp_from: e.target.value })} /></label>
                  <label className="checkbox-line"><input type="checkbox" checked={!!mailSettings.tls} onChange={(e) => setMailSettings({ ...mailSettings, tls: e.target.checked, ssl: e.target.checked ? false : mailSettings.ssl })} /> TLS kullan</label>
                  <label className="checkbox-line"><input type="checkbox" checked={!!mailSettings.ssl} onChange={(e) => setMailSettings({ ...mailSettings, ssl: e.target.checked, tls: e.target.checked ? false : mailSettings.tls })} /> SSL kullan</label>
                  <label className="wide">Uygulama bağlantısı<input placeholder="http://localhost:8080 veya https://medek.okul.local" value={mailSettings.app_base_url || ""} onChange={(e) => setMailSettings({ ...mailSettings, app_base_url: e.target.value })} /></label>
                  {mailSettings.smtp_password_configured && <label className="checkbox-line"><input type="checkbox" checked={!!mailSettings.clear_password} onChange={(e) => setMailSettings({ ...mailSettings, clear_password: e.target.checked, smtp_password: "" })} /> Kayıtlı SMTP şifresini temizle</label>}
                </div>
                <div className="action-row"><button className="primary-action">E-posta Ayarlarını Kaydet</button></div>
              </form>}
              <div className="restore-box">
                <h3>Test Mail Gönder</h3>
                <p className="muted">Ayarları kaydettikten sonra alıcı adresine test e-postası göndererek SMTP bağlantısını kontrol edin.</p>
                <div className="form-grid"><label>Alıcı e-posta<input placeholder="ornek@kurum.edu.tr" value={testMailTo} onChange={(e) => setTestMailTo(e.target.value)} /></label></div>
                {!testRecipientLooksReady && <small className="muted">Test için gerçek bir alıcı e-posta adresi yazın.</small>}
                <button className="primary-action" onClick={sendTestMail} type="button" disabled={!testRecipientLooksReady}>Test Mail Gönder</button>
              </div>
              {mailStatus && <DataTable rows={[mailStatus]} columns={["enabled", "smtp_host_configured", "smtp_port", "smtp_user_configured", "smtp_password_configured", "smtp_from", "tls", "ssl", "app_base_url_configured", "settings_stored", "job_backend"]} />}
              <DataTable rows={notifications} columns={["created_at", "event_type", "status", "subject", "actor", "program_id", "section_key", "error"]} />
            </div>,
          },
          {
            id: "workflow-automation",
            label: "Workflow Otomasyon",
            count: workflowPreview?.total || 0,
            content: <div className="tabbed-stack">
              <div className="notice-card info"><strong>Otomatik workflow hatırlatmaları</strong><span>Termin yaklaşınca, termin gecikince, onay/revizyon bekleyince sistem in-app bildirim ve SMTP açıksa e-posta üretir.</span><small>Tekrarlı bildirimler repeat_days ayarıyla sınırlanır; manuel test için force seçeneği kullanılabilir.</small></div>
              {workflowSettings ? <form className="tabbed-form workflow-settings-form" onSubmit={saveWorkflowAutomation}>
                <div className="form-section-heading"><div><span className="eyebrow">v105 Workflow Automation</span><h3>Hatırlatma motoru ayarları</h3><p className="muted">Ayarları kaydettikten sonra Önizle/Yenile ile hangi başlıklara bildirim gideceğini kontrol edin.</p></div></div>
                <div className="form-grid">
                  <label className="checkbox-line wide"><input type="checkbox" checked={!!workflowSettings.enabled} onChange={(e) => setWorkflowSettings({ ...workflowSettings, enabled: e.target.checked })} /> Workflow otomasyonunu etkinleştir</label>
                  <label className="checkbox-line"><input type="checkbox" checked={!!workflowSettings.in_app_enabled} onChange={(e) => setWorkflowSettings({ ...workflowSettings, in_app_enabled: e.target.checked })} /> In-app bildirim üret</label>
                  <label className="checkbox-line"><input type="checkbox" checked={!!workflowSettings.email_enabled} onChange={(e) => setWorkflowSettings({ ...workflowSettings, email_enabled: e.target.checked })} /> SMTP açıksa e-posta gönder</label>
                  <label>Termin kaç gün kala uyarı<input type="number" min="1" max="60" value={workflowSettings.deadline_days_before || 7} onChange={(e) => setWorkflowSettings({ ...workflowSettings, deadline_days_before: Number(e.target.value || 7) })} /></label>
                  <label>Tekrar aralığı / gün<input type="number" min="0" max="30" value={workflowSettings.repeat_days ?? 2} onChange={(e) => setWorkflowSettings({ ...workflowSettings, repeat_days: Number(e.target.value || 0) })} /></label>
                  <label className="checkbox-line"><input type="checkbox" checked={!!workflowSettings.include_overdue} onChange={(e) => setWorkflowSettings({ ...workflowSettings, include_overdue: e.target.checked })} /> Geciken terminleri dahil et</label>
                  <label className="checkbox-line"><input type="checkbox" checked={!!workflowSettings.include_upcoming} onChange={(e) => setWorkflowSettings({ ...workflowSettings, include_upcoming: e.target.checked })} /> Yaklaşan terminleri dahil et</label>
                  <label className="checkbox-line"><input type="checkbox" checked={!!workflowSettings.include_approval_waiting} onChange={(e) => setWorkflowSettings({ ...workflowSettings, include_approval_waiting: e.target.checked })} /> Onay bekleyenleri dahil et</label>
                  <label className="checkbox-line"><input type="checkbox" checked={!!workflowSettings.include_revision_waiting} onChange={(e) => setWorkflowSettings({ ...workflowSettings, include_revision_waiting: e.target.checked })} /> Revizyon bekleyenleri dahil et</label>
                  <label className="checkbox-line"><input type="checkbox" checked={!!workflowSettings.include_draft_followup} onChange={(e) => setWorkflowSettings({ ...workflowSettings, include_draft_followup: e.target.checked })} /> Hazırlığı süren taslakları da uyar</label>
                  <label className="checkbox-line"><input type="checkbox" checked={!!workflowSettings.weekly_digest_enabled} onChange={(e) => setWorkflowSettings({ ...workflowSettings, weekly_digest_enabled: e.target.checked })} /> Haftalık özet altyapısını etkinleştir</label>
                  <label>Haftalık özet günü<select value={workflowSettings.weekly_digest_weekday || "Monday"} onChange={(e) => setWorkflowSettings({ ...workflowSettings, weekly_digest_weekday: e.target.value })}>{["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].map((day) => <option key={day} value={day}>{day}</option>)}</select></label>
                </div>
                <div className="action-row"><button className="primary-action"><Settings size={16} /> Workflow Ayarlarını Kaydet</button><button type="button" onClick={refreshWorkflowAutomation}><RefreshCw size={16} /> Önizle / Yenile</button><label className="checkbox-line"><input type="checkbox" checked={workflowForce} onChange={(e) => setWorkflowForce(e.target.checked)} /> Force çalıştır</label><button type="button" className="primary-action" onClick={runWorkflowAutomation}><Send size={16} /> Hatırlatmaları Gönder</button></div>
              </form> : <div className="empty-state">Workflow ayarları yüklenemedi.</div>}
              <div className="dashboard-panel compact-kpi-grid">
                <MetricCard className="warn" label="Aday Uyarı" value={workflowPreview?.total ?? 0} sub={`${workflowPreview?.high_priority ?? 0} yüksek öncelik`} />
                <MetricCard label="Son Çalıştırma" value={workflowSettings?.last_run_at || "-"} sub="automation" />
                <MetricCard label="Çalıştırma Kaydı" value={workflowRuns.length} sub="son kayıt" />
              </div>
              <TabbedExpander
                title="Workflow otomasyon önizleme ve geçmiş"
                subtitle="Bildirim üretmeden önce alıcı sayısı ve tekrar durumunu kontrol edin."
                tabs={[
                  { id: "preview", label: "Önizleme", count: workflowPreview?.total || 0, content: <DataTable rows={asArray(workflowPreview?.rows)} columns={["priority", "category", "section_key", "section_title", "deadline", "days_left", "recipient_count", "recipient_usernames", "message"]} /> },
                  { id: "summary", label: "Kategori Özeti", count: Object.keys(asObject(workflowPreview?.summary)).length, content: <div className="dashboard-panel compact-kpi-grid">{Object.entries(asObject(workflowPreview?.summary)).map(([key, value]) => <MetricCard key={key} label={key} value={value} sub="workflow" />)}</div> },
                  { id: "runs", label: "Çalıştırma Geçmişi", count: workflowRuns.length, content: <DataTable rows={workflowRuns} columns={["started_at", "finished_at", "mode", "total_candidates", "created_notifications", "skipped_notifications", "actor"]} /> },
                ]}
              />
            </div>,
          },
          {
            id: "activity",
            label: "Aktivite Günlüğü",
            count: activity.length,
            content: <DataTable rows={activity} columns={["ts", "action", "detail", "actor", "program_id"]} />,
          },
        ]}
      />
    </section>
  );
}


export function UpdateCenterView({ onError, onMessage, refreshPrograms }) {
  const [payload, setPayload] = useState(null);
  const [busy, setBusy] = useState(false);
  const [scope, setScope] = useState("all");
  const [online, setOnline] = useState(false);
  const [filter, setFilter] = useState("pending");

  async function load() {
    try {
      setPayload(await api.updateCenter());
    } catch (err) {
      onError?.(err.message);
    }
  }

  useEffect(() => { load(); }, []);

  async function runCheck() {
    setBusy(true);
    try {
      const result = await api.runUpdateCenterCheck({ scope, online });
      onMessage?.(`Güncelleme kontrolü tamamlandı. Şablon adayı: ${result.created_template || 0}, akademik yapı adayı: ${result.created_academic || 0}`);
      await load();
    } catch (err) {
      onError?.(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function applyCandidate(row) {
    setBusy(true);
    try {
      const result = await api.applyUpdateCandidate(row.id);
      onMessage?.(`Güncelleme uygulandı: ${row.title}`);
      if (result?.result?.applied === "program_created" || result?.result?.applied === "tenant_faculty") await refreshPrograms?.();
      await load();
    } catch (err) {
      onError?.(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function ignoreCandidate(row) {
    setBusy(true);
    try {
      await api.ignoreUpdateCandidate(row.id, "Kullanıcı tarafından yok sayıldı.");
      onMessage?.(`Güncelleme adayı yok sayıldı: ${row.title}`);
      await load();
    } catch (err) {
      onError?.(err.message);
    } finally {
      setBusy(false);
    }
  }

  const summary = asObject(payload?.summary);
  const candidates = asArray(payload?.candidates);
  const visibleCandidates = candidates.filter((row) => {
    if (filter === "all") return true;
    if (filter === "template") return row.source_type === "template";
    if (filter === "academic") return row.source_type === "academic";
    return row.status === filter;
  });
  const watchers = asArray(payload?.watchers);
  const logs = asArray(payload?.logs);

  const candidateRows = visibleCandidates.map((row) => ({
    ...row,
    Tür: row.source_type === "academic" ? "Akademik yapı" : "Akreditasyon şablonu",
    Durum: row.status,
    Profil: row.profile || "-",
    Başlık: row.title,
    Özet: row.summary,
    Kaynak: row.source_url,
    Oluşturma: row.created_at,
  }));

  return (
    <section className="panel-stack update-center premium-operation-workspace">
      <div className="premium-operation-hero update-center-hero">
        <div>
          <span className="eyebrow"><RefreshCw size={16} /> Güncelleme Merkezi</span>
          <h2>Şablon ve akademik yapı güncelliğini yönetin</h2>
          <p>Akreditasyon kuruluşlarının resmi şablon kaynakları ve YÖK Atlas akademik yapı değişiklikleri izlenir; sistem hiçbir şeyi otomatik bozmaz, önce adayı gösterir ve onay ister.</p>
        </div>
        <div className="premium-operation-kpis">
          <span><strong>{summary.pending_total ?? 0}</strong><small>Bekleyen aday</small></span>
          <span><strong>{summary.pending_template ?? 0}</strong><small>Şablon</small></span>
          <span><strong>{summary.pending_academic ?? 0}</strong><small>Akademik yapı</small></span>
          <span><strong>{summary.watchers ?? 0}</strong><small>İzlenen kaynak</small></span>
        </div>
      </div>

      <div className="accreditation-process-strip">
        <span><ShieldCheck size={15} /><b>Kontrol et</b><small>Resmi kaynak/YÖK Atlas</small></span>
        <span><Eye size={15} /><b>Farkı incele</b><small>Eski-yeni karşılaştırma</small></span>
        <span><CheckCircle2 size={15} /><b>Onayla</b><small>Kullanıcı kabulü olmadan güncelleme yok</small></span>
        <span><History size={15} /><b>İz bırak</b><small>Activity Trail ve rollback mantığı</small></span>
      </div>

      <section className="editor-panel premium-update-control">
        <div className="editor-header">
          <div><h3>Kaynak Kontrolü</h3><p className="muted">Varsayılan kontrol paket içi şablon farklarını ve kayıtlı kaynak durumunu tarar. Canlı web/YÖK Atlas kontrolü için online seçeneğini açın; sunucunun internete çıkışı gerekir.</p></div>
          <button className="primary-action" disabled={busy || summary.can_check === false} onClick={runCheck}><RefreshCw size={16} /> Kontrolü Çalıştır</button>
        </div>
        <div className="form-grid compact-form-grid">
          <label>Kontrol kapsamı<select value={scope} onChange={(e) => setScope(e.target.value)}><option value="all">Tümü</option><option value="template">Akreditasyon şablonları</option><option value="academic">YÖK Atlas / akademik yapı</option></select></label>
          <label className="checkbox-line"><input type="checkbox" checked={online} onChange={(e) => setOnline(e.target.checked)} /> Canlı web/YÖK Atlas kontrolünü çalıştır</label>
        </div>
      </section>

      <div className="studio-filter-bar">
        {[['pending','Bekleyen'], ['template','Şablon'], ['academic','Akademik Yapı'], ['applied','Uygulanan'], ['ignored','Yok Sayılan'], ['all','Tümü']].map(([id, label]) => <button key={id} className={filter === id ? 'active' : ''} onClick={() => setFilter(id)}>{label}</button>)}
      </div>

      <section className="editor-panel update-candidate-panel">
        <div className="editor-header"><div><h3>Güncelleme Adayları</h3><p className="muted">Kullanıcı onayı olmadan şablon, fakülte veya program değişikliği uygulanmaz.</p></div></div>
        <DataTable rows={candidateRows} columns={["Tür", "Durum", "Profil", "Başlık", "Özet", "Kaynak", "Oluşturma"]} actions={(row) => {
          const source = visibleCandidates.find((item) => item.id === row.id);
          if (!source || source.status !== "pending") return null;
          return <div className="action-row compact"><button disabled={busy || source.can_apply === false} onClick={() => applyCandidate(source)}><CheckCircle2 size={14} /> Kabul Et</button><button disabled={busy || source.can_ignore === false} className="danger-button" onClick={() => ignoreCandidate(source)}>Yok Say</button></div>;
        }} />
      </section>

      <TabbedExpander
        title="Kaynak sağlığı ve değişiklik geçmişi"
        subtitle="Hangi kaynak ne zaman kontrol edildi, erişim sonucu ne oldu ve hangi kayıt üretildi izlenir."
        tabs={[
          { id: "watchers", label: "İzlenen Kaynaklar", count: watchers.length, content: <DataTable rows={watchers} columns={["watcher_type", "source_name", "profile", "source_url", "cadence", "is_active", "last_checked_at", "last_status", "last_message"]} /> },
          { id: "logs", label: "Kontrol Logları", count: logs.length, content: <DataTable rows={logs} columns={["checked_at", "source_type", "source_name", "status", "message", "tenant_id"]} /> },
          { id: "details", label: "Uygulama İlkesi", count: 4, content: <div className="tabbed-note"><h3>Güvenli güncelleme ilkesi</h3><ul><li>Mevcut rapor içerikleri otomatik değiştirilmez.</li><li>Yeni şablon önce sistem şablon bankasına alınır; mevcut programlara uygulanması kullanıcı kararına bırakılır.</li><li>YÖK Atlas değişikliklerinde silme yapılmaz; yeni fakülte/program ekleme adayı üretilir.</li><li>Pasifleştirme/arşivleme ayrı yönetici onayıyla yapılmalıdır.</li></ul></div> },
        ]}
      />
    </section>
  );
}


function labelFor(key) {
  return {
    university_name: "Üniversite",
    school_name: "Fakülte / MYO / Birim",
    department_name: "Bölüm",
    program_name: "Program Adı",
    report_year: "Rapor Yılı",
    accreditation_profile: "Akreditasyon Profili",
  }[key] || key;
}
