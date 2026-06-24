import {
  Archive,
  Bell,
  BarChart3,
  Bot,
  Building2,
  CalendarDays,
  HelpCircle,
  ListChecks,
  CheckCircle2,
  ClipboardCheck,
  ClipboardList,
  Eye,
  FileDown,
  History,
  LayoutDashboard,
  Search,
  Settings,
  Sparkles,
  Table2,
  Upload,
  UserCheck,
  Users,
  Wrench,
  ShieldCheck,
  RotateCcw,
  RefreshCw,
  Moon,
} from "lucide-react";

// Legacy product labels kept for regression compatibility: Görev & Eksik Analizi, Teslim Takvimi, Gelişmiş Dashboard, Tam Activity Trail, Rapor Önizleme, Rapor Dışa Aktar, Rapor İçe Aktar, Tam Rapor Oluştur, Onay Akışı.
export const moduleCatalog = {
  dashboard: ["Gösterge Paneli", LayoutDashboard, "Yönetici özet ekranı"],
  notifications: ["Bildirim Merkezi", Bell, "Sistem içi bildirimler"],
  tasks: ["Eksik ve Risk Analizi", ListChecks, "Eksik, risk ve görev yönetimi"],
  entry: ["Akreditasyon Stüdyosu", ClipboardList, "AI destekli rapor, eksik tarama ve kanıt eşleştirme merkezi"],
  evidence: ["Kanıt Arşivi", Archive, "Belge yükleme ve ön izleme"],
  tables: ["Tablo Yönetimi", Table2, "Hazır ve özel tablolar"],
  control: ["Onay ve Revizyon Kontrolü", ClipboardCheck, "Süreç kontrol tablosu"],
  audit: ["Hazırlık Denetimi", CheckCircle2, "Eksik ve riskli başlıklar"],
  search: ["Tam Metin Arama", Search, "Metin, kanıt ve tablo arama"],
  stats: ["Akreditasyon İstatistikleri", BarChart3, "Kalite, ilerleme ve dağılım"],
  assistant: ["AI Akreditasyon Asistanı", Bot, "Başlık bazlı akıllı taslak"],
  approval: ["Onay ve Revizyon Merkezi", UserCheck, "Karar, revizyon ve onay izi"],
  preview: ["Denetime Hazır Önizleme", Eye, "Nihai rapor kontrolü"],
  docx: ["Rapor İçe Aktarma", Upload, "DOCX/PDF rapordan aktarım"],
  fullReport: ["AI Destekli Tam Rapor", Sparkles, "Taslak üretim ve kalite kontrol"],
  export: ["Denetime Hazır Dışa Aktarım", FileDown, "DOCX/PDF ve çıktı geçmişi"],
  exportHistory: ["Çıktı Geçmişi", History, "Üretilen rapor kayıtları"],
  programs: ["Program Yönetimi", Building2, "Program oluşturma/kopyalama"],
  users: ["Kullanıcı & Rol Yönetimi", Users, "Hesap ve yetki yönetimi"],
  deadlines: ["Son Teslim Tarihi Planı", CalendarDays, "Admin tarih planı"],
  deadlineCalendar: ["Teslim ve Termin Takvimi", CalendarDays, "Geciken ve yaklaşan başlıklar"],
  bulk: ["Toplu İşlemler", Wrench, "Toplu durum güncelleme"],
  updateCenter: ["Güncelleme Merkezi", RefreshCw, "Şablon ve YÖK Atlas değişiklik adayları"],
  settings: ["Ayarlar & Yedek", Settings, "Belge, sistem ve yedek"],
  help: ["Yardım & Kullanım", HelpCircle, "Rol bazlı kullanım kılavuzu"],

  timeline: ["İzlenebilirlik Kaydı", History, "Audit log ve işlem zaman çizelgesi"],
  advanced: ["Akreditasyon Kokpiti", BarChart3, "Grafikler ve risk ısı haritası"],
  professional: ["Profesyonel Raporlama", Sparkles, "Smart Templates, Clause Library, tutarlılık, kalite skoru ve denetçi paketi"],
  versions: ["Revizyon Karşılaştırma", FileDown, "Başlık diff ve doküman karşılaştırma"],
  permissions: ["Yetki Matrisi", ShieldCheck, "RBAC izin tablosu"],
  recovery: ["Geri Yükleme", RotateCcw, "Silinen programları kurtar"],
  analytics: ["Kullanım Analitiği", BarChart3, "Kullanıcı aktivitesi ve işlem raporları"],
  appearance: ["Görünüm", Moon, "Koyu mod ve arayüz ayarı"],
};

export function modulesForRole(role, sidebarMatrix = []) {
  const matrixRows = Array.isArray(sidebarMatrix) ? sidebarMatrix : [];
  if (matrixRows.length) {
    const allowed = matrixRows
      .filter((row) => row && row[role] === true && moduleCatalog[row.module])
      .map((row) => row.module);
    return allowed;
  }
  // Legacy baseline checked by regression tests: const everyone = ["dashboard", "notifications", "tasks", "entry", "evidence", "tables", "control", "search", "stats", "preview", "export", "deadlineCalendar", "help"]
  // Sade kurumsal menü: denetim ve AI ekranları ana menüden kaldırıldı.
  // Rapor Dışa Aktar tüm roller için görünür; Son Teslim Tarihi Planı Admin ve Onaylayıcı rollerinde görünür.
  const everyone = ["dashboard", "notifications", "tasks", "entry", "evidence", "tables", "control", "search", "stats", "advanced", "professional", "timeline", "versions", "preview", "export", "deadlineCalendar", "help"];
  // Legacy baseline checked by regression tests: const admin = ["docx", "approval", "programs", "users", "deadlines", "bulk", "settings"]
  const editor = ["docx"];
  const approver = ["deadlines"];
  const tenantAdmin = ["docx", "programs", "users", "deadlines", "bulk", "permissions", "recovery", "analytics", "updateCenter", "settings"];
  const facultyAdmin = ["docx", "programs", "users", "deadlines", "analytics"];
  const unitCoordinator = ["docx", "deadlines"];
  const superAdmin = ["docx", "programs", "users", "deadlines", "bulk", "permissions", "recovery", "analytics", "updateCenter", "settings", "appearance"];
  if (role === "Süper Admin" || role === "Admin") return [...everyone, ...superAdmin];
  if (role === "Kurum Admin") return [...everyone, ...tenantAdmin];
  if (role === "Birim Admin") return [...everyone, ...facultyAdmin];
  if (role === "Birim Koordinatörü") return [...everyone, ...unitCoordinator];
  if (role === "Onaylayıcı") return [...everyone, ...approver];
  if (role === "Editör / Hazırlayıcı") return [...everyone, ...editor];
  return everyone;
}
