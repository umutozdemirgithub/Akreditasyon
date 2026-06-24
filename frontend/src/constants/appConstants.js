import { moduleCatalog } from "../config/navigation.jsx";
import { asArray, asObject } from "../utils.js";

export const STATUS_OPTIONS = ["Başlamadı", "Devam Ediyor", "Taslak Hazır", "Revizyon Gerekli", "Tamamlandı"];
export const FACULTY_ADMIN_ROLE = "Birim Admin";
export const UNIT_COORDINATOR_ROLE = "Birim Koordinatörü";
export const EDITOR_ROLE = "Editör / Hazırlayıcı";
export const APPROVER_ROLE = "Onaylayıcı";
export const READONLY_ROLE = "Denetçi";
export const ROLES = ["Süper Admin", "Kurum Admin", FACULTY_ADMIN_ROLE, UNIT_COORDINATOR_ROLE, EDITOR_ROLE, APPROVER_ROLE, READONLY_ROLE];
export const ADMIN_ROLES = new Set(["Süper Admin", "Kurum Admin", "Admin"]);
export const MANAGEMENT_MODULES = new Set(["programs", "users", "deadlines", "bulk", "permissions", "recovery", "analytics", "settings", "appearance"]);
export const SUPER_ADMIN_ROLES = new Set(["Süper Admin", "Admin"]);
export const TENANT_DELEGATE_ROLES = [FACULTY_ADMIN_ROLE, UNIT_COORDINATOR_ROLE, EDITOR_ROLE, APPROVER_ROLE, READONLY_ROLE];
export const FACULTY_DELEGATE_ROLES = [UNIT_COORDINATOR_ROLE, EDITOR_ROLE, APPROVER_ROLE, READONLY_ROLE];
export const ROLE_RANK = { "Süper Admin": 0, "Kurum Admin": 10, [FACULTY_ADMIN_ROLE]: 20, [UNIT_COORDINATOR_ROLE]: 30, [EDITOR_ROLE]: 40, [APPROVER_ROLE]: 50, [READONLY_ROLE]: 60 };
export function visibleRolesForActor(role) {
  const normalized = normalizeRole(role || READONLY_ROLE);
  const rank = ROLE_RANK[normalized] ?? ROLE_RANK[READONLY_ROLE];
  return ROLES.filter((candidate) => (ROLE_RANK[candidate] ?? 999) >= rank);
}
export function delegatableRolesForActor(role) {
  const normalized = normalizeRole(role || READONLY_ROLE);
  if (isSuperAdminRole(normalized)) return ROLES.filter((item) => item !== "Süper Admin");
  if (normalized === "Kurum Admin") return TENANT_DELEGATE_ROLES;
  if (normalized === FACULTY_ADMIN_ROLE) return FACULTY_DELEGATE_ROLES;
  return [];
}
export function normalizeRole(role, tenantScope = "") {
  const aliases = {
    Admin: tenantScope === "global" ? "Süper Admin" : "Kurum Admin",
    "Fakülte/MYO Admin": FACULTY_ADMIN_ROLE,
    "Birim/Fakülte Admin": FACULTY_ADMIN_ROLE,
    "Editör": EDITOR_ROLE,
    "Hazırlayıcı": EDITOR_ROLE,
    "İzleyici": READONLY_ROLE,
    "Denetçi (İzleyici)": READONLY_ROLE,
    "Denetçi": READONLY_ROLE,
  };
  const normalized = aliases[role] || role;
  return ROLES.includes(normalized) ? normalized : READONLY_ROLE;
}
export function isAdminRole(role) { return ADMIN_ROLES.has(role); }
export function isSuperAdminRole(role) { return SUPER_ADMIN_ROLES.has(role); }
export function matrixPermissionAllowed(permissionRows, role, permission, fallback = false) {
  const normalized = normalizeRole(role || READONLY_ROLE);
  if (isSuperAdminRole(normalized)) return true;
  const row = asArray(permissionRows).find((item) => item.permission === permission);
  if (!row) return fallback;
  return row[normalized] === true;
}

export function matrixModuleAllowed(sidebarRows, role, module, fallback = false) {
  const normalized = normalizeRole(role || READONLY_ROLE);
  if (isSuperAdminRole(normalized)) return true;
  const row = asArray(sidebarRows).find((item) => item.module === module);
  if (!row) return fallback;
  return row[normalized] === true;
}

export function roleClassName(role) {
  return normalizeRole(role || READONLY_ROLE).toLocaleLowerCase("tr-TR")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/ı/g, "i")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "") || "denetci";
}

export function roleAccentForRole(role) {
  const normalized = normalizeRole(role || READONLY_ROLE);
  if (normalized === "Kurum Admin") return { accent: "#0f2f66", sidebar: "#071a3d" };
  if (normalized === FACULTY_ADMIN_ROLE) return { accent: "#059669", sidebar: "#052e2b" };
  if (normalized === UNIT_COORDINATOR_ROLE) return { accent: "#0f766e", sidebar: "#073b3a" };
  if (normalized === EDITOR_ROLE) return { accent: "#4f46e5", sidebar: "#1e1b4b" };
  if (normalized === APPROVER_ROLE) return { accent: "#b45309", sidebar: "#451a03" };
  if (normalized === READONLY_ROLE) return { accent: "#64748b", sidebar: "#172033" };
  return { accent: "#2563eb", sidebar: "#0d2b68" };
}

export const ACCREDITATION_PROFILES = [
  "MEDEK", "MÜDEK", "TEPDAD", "DEPAD", "ECZAKDER", "HEPDAK", "EPDAK", "FTR-AD", "SAYAK",
  "MİAK", "PEMDER", "VEDEK", "ZİDEK", "TURAK", "İLAD", "AA", "TPD", "PDR-DER", "EPDAD", "FEDEK", "STAR", "SABAK", "SPORAK", "İLEDAK"
];
export const PROFILE_LABELS = {
  "MÜDEK": "MÜDEK (Mühendislik)",
  EPDAD: "EPDAD (Öğretmenlik/Eğitim)",
  MEDEK: "MEDEK (Önlisans/MYO)",
  SPORAK: "SPORAK (Spor Bilimleri)",
  ECZAKDER: "ECZAKDER (Eczacılık)",
  TEPDAD: "TEPDAD (Tıp)",
  DEPAD: "DEPAD (Diş Hekimliği)",
  HEPDAK: "HEPDAK (Hemşirelik)",
  EPDAK: "EPDAK (Ebelik)",
  "FTR-AD": "FTR-AD (Fizyoterapi)",
  SAYAK: "SAYAK (Sağlık Yönetimi)",
  "MİAK": "MİAK (Mimarlık)",
  PEMDER: "PEMDER (Peyzaj Mimarlığı)",
  VEDEK: "VEDEK (Veteriner)",
  "ZİDEK": "ZİDEK (Ziraat)",
  TURAK: "TURAK (Turizm/Gastronomi)",
  "İLAD": "İLAD / İLEDAK (İletişim)",
  "İLEDAK": "İLEDAK (eski profil uyumluluğu)",
  AA: "İAA / AA (İlahiyat)",
  TPD: "Türk Psikologlar Derneği (Psikoloji)",
  "PDR-DER": "Türk PDR-Der (PDR)",
  FEDEK: "FEDEK (Fen/Edebiyat/Fen-Edebiyat)",
  STAR: "STAR (Sosyal/Beşeri/İİBF vb.)",
  SABAK: "SABAK (Sağlık Bilimleri - genel)",
};
export const ERU_UNIT_PROGRAM_CATALOG = [
  {
    label: "Mühendislik Fakültesi",
    profile: "MÜDEK",
    departments: {
      "Bilgisayar Mühendisliği Bölümü": ["Bilgisayar Mühendisliği"],
      "Biyomedikal Mühendisliği Bölümü": ["Biyomedikal Mühendisliği"],
      "Elektrik-Elektronik Mühendisliği Bölümü": ["Elektrik-Elektronik Mühendisliği"],
      "Endüstri Mühendisliği Bölümü": ["Endüstri Mühendisliği"],
      "Enerji Sistemleri Mühendisliği Bölümü": ["Enerji Sistemleri Mühendisliği"],
      "Gıda Mühendisliği Bölümü": ["Gıda Mühendisliği"],
      "Harita Mühendisliği Bölümü": ["Harita Mühendisliği"],
      "İnşaat Mühendisliği Bölümü": ["İnşaat Mühendisliği"],
      "Makine Mühendisliği Bölümü": ["Makine Mühendisliği"],
      "Malzeme Bilimi ve Mühendisliği Bölümü": ["Malzeme Bilimi ve Mühendisliği"],
      "Mekatronik Mühendisliği Bölümü": ["Mekatronik Mühendisliği"],
      "Tekstil Mühendisliği Bölümü": ["Tekstil Mühendisliği"],
    },
  },
  {
    label: "Eğitim Fakültesi",
    profile: "EPDAD",
    departments: {
      "Eğitim Bilimleri Bölümü": ["Rehberlik ve Psikolojik Danışmanlık"],
      "Matematik ve Fen Bilimleri Eğitimi Bölümü": ["Fen Bilgisi Öğretmenliği", "İlköğretim Matematik Öğretmenliği"],
      "Temel Eğitim Bölümü": ["Okul Öncesi Öğretmenliği", "Sınıf Öğretmenliği"],
      "Türkçe ve Sosyal Bilimler Eğitimi Bölümü": ["Sosyal Bilgiler Öğretmenliği", "Türkçe Öğretmenliği"],
      "Yabancı Diller Eğitimi Bölümü": ["İngilizce Öğretmenliği"],
    },
  },
  {
    label: "Halil Bayraktar Sağlık Hizmetleri Meslek Yüksekokulu",
    profile: "MEDEK",
    departments: {
      "Dişçilik Hizmetleri Bölümü": ["Ağız ve Diş Sağlığı"],
      "Tıbbi Hizmetler ve Teknikler Bölümü": [
        "Ameliyathane Hizmetleri",
        "Anestezi",
        "Elektronörofizyoloji",
        "İlk ve Acil Yardım",
        "Odyometri",
        "Radyoterapi",
        "Tıbbi Dokümantasyon ve Sekreterlik",
        "Tıbbi Görüntüleme Teknikleri",
        "Tıbbi Laboratuvar Teknikleri",
      ],
    },
  },
  {
    label: "Spor Bilimleri Fakültesi",
    profile: "SPORAK",
    departments: {
      "Antrenörlük Eğitimi Bölümü": ["Antrenörlük Eğitimi"],
      "Beden Eğitimi ve Spor Bölümü": ["Beden Eğitimi ve Spor Öğretmenliği"],
      "Rekreasyon Bölümü": ["Rekreasyon"],
      "Spor Yöneticiliği Bölümü": ["Spor Yöneticiliği"],
    },
  },
  {
    label: "Eczacılık Fakültesi",
    profile: "ECZAKDER",
    departments: {
      "Eczacılık Meslek Bilimleri Bölümü": ["Eczacılık"],
      "Eczacılık Teknolojisi Bölümü": ["Eczacılık"],
      "Temel Eczacılık Bilimleri Bölümü": ["Eczacılık"],
    },
  },
  {
    label: "Tıp Fakültesi",
    profile: "TEPDAD",
    departments: {
      "Tıp Programı": ["Tıp"],
    },
  },
  {
    label: "Turizm Fakültesi",
    profile: "TURAK",
    departments: {
      "Gastronomi ve Mutfak Sanatları Bölümü": ["Gastronomi ve Mutfak Sanatları"],
      "Turizm İşletmeciliği Bölümü": ["Turizm İşletmeciliği"],
      "Turizm Rehberliği Bölümü": ["Turizm Rehberliği"],
    },
  },
  {
    label: "İlahiyat Fakültesi",
    profile: "AA",
    departments: {
      "İlahiyat Bölümü": ["İlahiyat"],
    },
  },
  {
    label: "Sağlık Bilimleri Fakültesi",
    profile: "SABAK",
    departments: {
      "Beslenme ve Diyetetik Bölümü": ["Beslenme ve Diyetetik"],
      "Ebelik Bölümü": ["Ebelik"],
      "Hemşirelik Bölümü": ["Hemşirelik"],
      "Sağlık Yönetimi Bölümü": ["Sağlık Yönetimi"],
    },
  },
  {
    label: "İletişim Fakültesi",
    profile: "İLAD",
    departments: {
      "Gazetecilik Bölümü": ["Gazetecilik"],
      "Halkla İlişkiler ve Tanıtım Bölümü": ["Halkla İlişkiler ve Tanıtım"],
      "Radyo, Televizyon ve Sinema Bölümü": ["Radyo, Televizyon ve Sinema"],
    },
  },
];
export const FACULTY_PROFILE_OPTIONS = ERU_UNIT_PROGRAM_CATALOG.map(({ label, profile }) => ({ label, profile }));
export const FACULTY_TO_PROFILE = Object.fromEntries(FACULTY_PROFILE_OPTIONS.map((item) => [item.label, item.profile]));
export const FACULTY_CATALOG_BY_LABEL = Object.fromEntries(ERU_UNIT_PROGRAM_CATALOG.map((item) => [item.label, item]));
export const ACADEMIC_STATUS_OPTIONS = [
  "Prof. Dr.",
  "Doç. Dr.",
  "Dr. Öğretim Üyesi",
  "Dr. Araştırma Görevlisi",
  "Dr. Öğretim Görevlisi",
  "Araştırma Görevlisi",
  "Öğretim Görevlisi",
  "İdari Personel",
];

export const emptySection = {
  status: "Başlamadı",
  report_text: "",
  planla: "",
  uygula: "",
  kontrol: "",
  onlem: "",
  notes: "",
  deadline: "",
};

export const DEFAULT_TABLE_COLUMNS = ["Başlık", "Açıklama", "Kanıt Kodu"];
export const DEFAULT_TABLE_META = {
  cells: {},
  options: {
    fontSize: 10,
    headerBg: "#f4f7fc",
    borderColor: "#d7e3f1",
    align: "left",
  },
};

export function profileLabel(profile) {
  return PROFILE_LABELS[profile] || profile;
}

function normalizeMatchText(value) {
  return String(value || "")
    .toLocaleLowerCase("tr-TR")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/ı/g, "i");
}

function containsAny(value, patterns) {
  const text = normalizeMatchText(value);
  return patterns.some((pattern) => text.includes(normalizeMatchText(pattern)));
}

export function inferAccreditationProfile({ degree = "", schoolName = "", departmentName = "", programName = "" } = {}) {
  const degreeText = normalizeMatchText(`${degree} ${schoolName}`);
  if (degreeText.includes("onlisans") || degreeText.includes("on lisans") || degreeText.includes("myo") || degreeText.includes("meslek yuksekokulu")) return "MEDEK";
  const program = programName || `${schoolName} ${departmentName}`;
  const rules = [
    ["DEPAD", ["Diş Hekimliği", "Dis Hekimligi"]],
    ["TEPDAD", ["Tıp", "Tip"]],
    ["ECZAKDER", ["Eczacılık", "Eczacilik"]],
    ["HEPDAK", ["Hemşirelik", "Hemsirelik"]],
    ["EPDAK", ["Ebelik"]],
    ["FTR-AD", ["Fizyoterapi"]],
    ["SAYAK", ["Sağlık Yönetimi", "Saglik Yonetimi"]],
    ["PEMDER", ["Peyzaj Mimarlığı", "Peyzaj Mimarligi"]],
    ["MİAK", ["Mimarlık", "Mimarlik"]],
    ["VEDEK", ["Veteriner"]],
    ["ZİDEK", ["Ziraat", "Tarım", "Tarim"]],
    ["TURAK", ["Turizm", "Gastronomi"]],
    ["İLAD", ["İletişim", "Iletisim", "Gazetecilik", "Radyo", "Yeni Medya"]],
    ["AA", ["İlahiyat", "İslami İlimler", "Ilahiyat", "Islami Ilimler"]],
    ["PDR-DER", ["PDR", "Rehberlik ve Psikolojik Danışmanlık", "Psikolojik Danışmanlık ve Rehberlik"]],
    ["TPD", ["Psikoloji"]],
    ["EPDAD", ["Öğretmenliği", "Ogretmenligi"]],
    ["FEDEK", ["Matematik", "Fizik", "Kimya", "Biyoloji", "Tarih", "Edebiyat", "Sosyoloji"]],
    ["MÜDEK", ["Mühendisliği", "Muhendisligi", "Mühendislik", "Muhendislik"]],
    ["STAR", ["Sosyal Hizmet", "İşletme", "İktisat", "Kamu Yönetimi", "Maliye", "Uluslararası İlişkiler", "Siyaset Bilimi", "Felsefe"]],
  ];
  for (const [profile, patterns] of rules) if (containsAny(program, patterns)) return profile;
  return FACULTY_TO_PROFILE[schoolName] || "MEDEK";
}

export function profileForFaculty(schoolName) {
  return FACULTY_TO_PROFILE[schoolName] || "MEDEK";
}

export function unitCatalogForFaculty(schoolName) {
  return FACULTY_CATALOG_BY_LABEL[schoolName] || null;
}

export function departmentOptionsForFaculty(schoolName) {
  const catalog = unitCatalogForFaculty(schoolName);
  return catalog ? Object.keys(catalog.departments || {}) : [];
}

export function programOptionsForDepartment(schoolName, departmentName) {
  const catalog = unitCatalogForFaculty(schoolName);
  if (!catalog || !departmentName) return [];
  return catalog.departments?.[departmentName] || [];
}

export function updateProgramFaculty(program, schoolName) {
  const departmentOptions = departmentOptionsForFaculty(schoolName);
  const firstDepartment = departmentOptions[0] || "";
  const programOptions = programOptionsForDepartment(schoolName, firstDepartment);
  return {
    ...program,
    school_name: schoolName,
    department_name: firstDepartment,
    program_name: programOptions[0] || "",
    accreditation_profile: profileForFaculty(schoolName),
  };
}

export function updateProgramDepartment(program, departmentName) {
  const programOptions = programOptionsForDepartment(program.school_name, departmentName);
  return {
    ...program,
    department_name: departmentName,
    program_name: programOptions[0] || "",
  };
}

export function programSchoolLabel(program) {
  return program?.school_name || program?.university_name || "Birim belirtilmedi";
}

export function programDisplayLabel(program) {
  const department = program?.department_name ? `${program.department_name} / ` : "";
  return `${department}${program?.program_name || "Program"} · ${program?.report_year || "-"}`;
}

export function groupedPrograms(programRows) {
  return programRows.reduce((acc, program) => {
    const school = programSchoolLabel(program);
    if (!acc[school]) acc[school] = [];
    acc[school].push(program);
    return acc;
  }, {});
}

export function tenantIdOf(row) {
  return row?.tenant_id || "tenant_default";
}

export function tenantNameOf(row, tenantMap = new Map()) {
  return row?.tenant_name || tenantMap.get(tenantIdOf(row))?.name || row?.university_name || "Kurum seçilmedi";
}

export function groupedByTenant(rows, tenantOptions = []) {
  const safeTenants = Array.isArray(tenantOptions) ? tenantOptions : [];
  const tenantMap = new Map(safeTenants.map((tenant) => [tenant.id, tenant]));
  const groups = [];
  const index = new Map();
  safeTenants.forEach((tenant) => {
    if (!tenant?.id || tenant.is_setup_placeholder) return;
    const group = {
      id: tenant.id,
      name: tenant.name || tenant.id,
      is_active: tenant.is_active !== false && tenant.is_active !== 0,
      rows: [],
    };
    index.set(tenant.id, group);
    groups.push(group);
  });
  (Array.isArray(rows) ? rows : []).forEach((row) => {
    const id = tenantIdOf(row);
    if (!index.has(id)) {
      const tenant = tenantMap.get(id);
      const group = {
        id,
        name: tenantNameOf(row, tenantMap),
        is_active: tenant ? tenant.is_active !== false && tenant.is_active !== 0 : true,
        rows: [],
      };
      index.set(id, group);
      groups.push(group);
    }
    index.get(id).rows.push(row);
  });
  return groups.sort((a, b) => a.name.localeCompare(b.name, "tr"));
}

export function uniqueSorted(values) {
  return Array.from(new Set(values.filter(Boolean))).sort((a, b) => a.localeCompare(b, "tr"));
}

export function departmentOptionsForPrograms(programRows) {
  const seen = new Set();
  return programRows
    .map((program) => program.department_name || "Bölüm belirtilmedi")
    .filter((department) => {
      if (seen.has(department)) return false;
      seen.add(department);
      return true;
    });
}

export function programOnlyDisplayLabel(program) {
  return `${program?.program_name || "Program"} · ${program?.report_year || "-"}`;
}

export function shortProgramLabel(program) {
  return program?.program_name || "Program seçilmedi";
}

export function daysUntil(dateValue) {
  if (!dateValue) return null;
  const target = new Date(`${dateValue}T23:59:59`);
  if (Number.isNaN(target.getTime())) return null;
  return Math.ceil((target.getTime() - Date.now()) / 86400000);
}

export function computeModuleBadges({ sections = [], dashboard = {}, unread = 0 }) {
  const rows = asArray(sections);
  const summary = asObject(dashboard?.summary);
  const revision = rows.filter((section) => section.approval_status === "Revizyon Gerekli" || section.status === "Revizyon Gerekli").length;
  const submitted = rows.filter((section) => section.approval_status === "Onaya Gönderildi").length;
  const missingEvidence = rows.filter((section) => Number(section.evidence_count || 0) === 0).length;
  const upcoming = rows.filter((section) => {
    const days = daysUntil(section.deadline);
    return days !== null && days >= 0 && days <= 7;
  }).length;
  const overdue = rows.filter((section) => {
    const days = daysUntil(section.deadline);
    return days !== null && days < 0 && section.approval_status !== "Onaylandı";
  }).length;
  return {
    notifications: unread,
    tasks: revision + missingEvidence + overdue,
    approval: submitted,
    deadlineCalendar: upcoming + overdue,
    control: submitted + revision,
    evidence: missingEvidence,
    stats: Number(summary.revision_sections || 0),
    professional: missingEvidence + revision,
  };
}

export const NAV_GROUPS = [
  { title: "Ana Panel", ids: ["dashboard", "notifications", "tasks"] },
  { title: "Rapor Hazırlama", ids: ["entry", "evidence", "tables", "search"] },
  { title: "Onay & Kalite", ids: ["control", "approval", "stats", "advanced", "professional", "timeline", "versions", "deadlineCalendar"] },
  { title: "Çıktılar", ids: ["preview", "export", "docx", "exportHistory", "fullReport"] },
  { title: "Yönetim", ids: ["programs", "users", "deadlines", "bulk", "permissions", "recovery", "analytics", "updateCenter", "settings", "appearance", "help"] },
];

export function groupedNavItems(visibleModules) {
  const visible = Array.isArray(visibleModules) ? visibleModules : [];
  return NAV_GROUPS.map((group) => ({
    ...group,
    items: group.ids.filter((id) => visible.includes(id)),
  })).filter((group) => group.items.length);
}




export const MOBILE_PRIMARY_BY_ROLE = {
  "Süper Admin": ["dashboard", "notifications", "advanced", "programs", "updateCenter"],
  "Kurum Admin": ["dashboard", "notifications", "programs", "users", "updateCenter"],
  [FACULTY_ADMIN_ROLE]: ["dashboard", "notifications", "advanced", "control", "programs"],
  [UNIT_COORDINATOR_ROLE]: ["dashboard", "notifications", "entry", "approval", "advanced"],
  Admin: ["dashboard", "notifications", "advanced", "programs", "settings"],
  [APPROVER_ROLE]: ["dashboard", "notifications", "control", "approval", "advanced"],
  [EDITOR_ROLE]: ["dashboard", "entry", "evidence", "approval", "notifications"],
  [READONLY_ROLE]: ["dashboard", "preview", "notifications", "stats", "help"],
};

export function mobileNavItemsForRole(role, visibleModules = []) {
  const visible = new Set(Array.isArray(visibleModules) ? visibleModules : []);
  const preferred = MOBILE_PRIMARY_BY_ROLE[normalizeRole(role)] || MOBILE_PRIMARY_BY_ROLE[READONLY_ROLE];
  const selected = preferred.filter((id) => visible.has(id) && moduleCatalog[id]);
  if (selected.length >= 5) return selected.slice(0, 5);
  const fallback = ["dashboard", "entry", "evidence", "notifications", "export", "help"];
  for (const id of fallback) {
    if (selected.length >= 5) break;
    if (visible.has(id) && moduleCatalog[id] && !selected.includes(id)) selected.push(id);
  }
  return selected.slice(0, 5);
}
