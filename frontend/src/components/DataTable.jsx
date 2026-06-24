import React from "react";

const COLUMN_LABELS = {
  id: "Kimlik",
  name: "Kurum",
  tenant_code: "Kısa Kod",
  domain: "Alan Adı",
  tenant_name: "Kurum",
  faculty_name: "Fakülte / MYO",
  username: "Kullanıcı Adı",
  full_name: "Ad Soyad",
  email: "E-posta",
  role: "Rol",
  academic_status: "Akademik Durum",
  is_active: "Aktif",
  user_active: "Kullanıcı Aktif",
  must_change_password: "Şifre Değişimi Zorunlu",
  failed_attempts: "Hatalı Giriş",
  locked_until: "Kilit Bitişi",
  last_login: "Son Giriş",
  program_id: "Program Kimliği",
  program_name: "Program",
  department_name: "Bölüm",
  school_name: "Birim",
  university_name: "Üniversite",
  accreditation_profile: "Akreditasyon Profili",
  report_year: "Rapor Yılı",
  assigned_sections: "Atanan Başlıklar",
  section_key: "Başlık Kodu",
  section_title: "Başlık",
  report_group_title: "Rapor Bölümü",
  report_subgroup_title: "Alt Ölçüt",
  main_title: "Ana Ölçüt",
  status: "Durum",
  approval_status: "Onay Durumu",
  total: "Toplam",
  ready: "Hazır",
  approved: "Onaylandı",
  submitted: "Onaya Gönderildi",
  revision: "Revizyon",
  readiness_percent: "Hazırlık Yüzdesi",
  approval_percent: "Onay Yüzdesi",
  quality_avg: "Kalite Ortalaması",
  quality: "Kalite",
  words: "Kelime",
  evidence: "Kanıt",
  evidence_count: "Kanıt Sayısı",
  tables: "Tablo",
  table_count: "Tablo Sayısı",
  puko: "PUKÖ",
  snippet: "Özet",
  code: "Kanıt Kodu",
  original_name: "Dosya Adı",
  uploaded_at: "Yüklenme Tarihi",
  note: "Not",
  export_type: "Çıktı Türü",
  file_name: "Dosya Adı",
  actor: "İşlemi Yapan",
  requested_by: "Gönderen",
  decided_by: "Karar Veren",
  created_at: "Oluşturulma Tarihi",
  updated_at: "Güncellenme Tarihi",
  action: "İşlem",
  detail: "Detay",
  success: "Başarılı",
  active_programs: "Aktif Program",
  active_users: "Aktif Kullanıcı",
  activity_rows: "Aktivite Kaydı",
  login_rows: "Giriş Kaydı",
  database: "Veritabanı",
  database_exists: "Veritabanı Var",
  evidence_dir: "Kanıt Klasörü",
};

const VALUE_LABELS = {
  Login: "Giriş",
  "User saved": "Kullanıcı kaydedildi",
  "User deleted": "Kullanıcı silindi",
  "Settings updated": "Ayarlar güncellendi",
  "Program created": "Program oluşturuldu",
  "Program cloned": "Program kopyalandı",
  "Program active changed": "Program aktifliği değişti",
  "Program user assigned": "Program kullanıcısı atandı",
  "Section updated": "Başlık güncellendi",
  "Evidence uploaded": "Kanıt yüklendi",
  "Evidence linked": "Kanıt bağlandı",
  "Evidence deleted": "Kanıt silindi",
  "Table saved": "Tablo kaydedildi",
  "Table attached": "Tablo bağlandı",
  "Table deleted": "Tablo silindi",
  "Deadlines updated": "Son Teslim tarihi planı güncellendi",
  "Bulk status": "Toplu durum güncellendi",
  "JSON backup restored": "JSON yedeği geri yüklendi",
  "DOCX imported": "DOCX içe aktarıldı",
  "Approval action": "Onay işlemi",
};

export function DataTable({ rows, columns, actions }) {
  const safeRows = Array.isArray(rows) ? rows : [];
  const cols = columns || Array.from(new Set(safeRows.flatMap((row) => {
    if (!row || typeof row !== "object" || Array.isArray(row)) return [];
    return Object.keys(row).filter((key) => !["data_json", "stored_path"].includes(key));
  })));
  if (!safeRows.length) return <div className="empty-state premium-empty-inline"><strong>Kayıt yok</strong><span>Bu alanda henüz gösterilecek veri bulunmuyor.</span></div>;
  const minWidth = Math.max(760, Math.min(2400, cols.length * 138 + (actions ? 132 : 0)));
  const tableClass = `data-table ${actions ? "has-actions" : ""} cols-${Math.min(cols.length, 12)}`;
  return (
    <div className="data-table-wrap responsive-table" data-cols={cols.length} style={{ "--table-min-width": `${minWidth}px` }}>
      <table className={tableClass}>
        <thead>
          <tr>{cols.map((col) => <th key={col}>{COLUMN_LABELS[col] || col}</th>)}{actions && <th>İşlem</th>}</tr>
        </thead>
        <tbody>{safeRows.map((row, idx) => {
          const safeRow = row && typeof row === "object" && !Array.isArray(row) ? row : { value: row };
          return <tr key={safeRow.id || safeRow.section_key || safeRow.username || idx}>{cols.map((col) => <td key={col}>{renderCell(safeRow[col])}</td>)}{actions && <td className="table-actions">{actions(safeRow)}</td>}</tr>;
        })}</tbody>
      </table>
    </div>
  );
}

function renderCell(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? "Evet" : "Hayır";
  if (typeof value === "object") return JSON.stringify(value);
  return VALUE_LABELS[String(value)] || String(value);
}
