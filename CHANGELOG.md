
## v100.11-readable-archive-mirror-import-fix

- Fixed `tools/mirror_full_archive.py` import path when executed inside the API container.
- Updated PowerShell and shell wrappers to run with `/app` as working directory and `PYTHONPATH=/app`.
- PowerShell wrapper now stops on non-zero Docker/Python exit codes instead of printing a false success message.

## ver_100.1 - Rol ve Tema Senkronizasyonu

- Paket adı, uygulama sürümü, frontend metadata ve release zip varsayılanı `ver_100` çizgisine alındı.
- `Denetçi (İzleyici)` görünen rol adı `Denetçi` olarak sadeleştirildi; eski değerler alias olarak korunur.
- Birim Koordinatörü sütunu işlem, sidebar ve section bazlı matris temizleyicilerinde senkronize edildi.
- Sidebar role-based accent, program bağlam kartı, badge/hover davranışı ve top navigation daralma sınıflarıyla güçlendirildi.
- Dashboard hero, kalite skoru, KPI trendleri, widget library ve sürükle-bırak kart sıralama deneyimi eklendi.

## v135 - Preview JSON Safety Hotfix

- Denetime Hazır Rapor Önizleme endpointi JSON güvenli hale getirildi; `NaN`, `Infinity`, bytes/path/datetime gibi değerler 500 hatasına neden olmadan temizlenir.
- Tablo kaydetme ve tablo listeleme akışları `allow_nan=False` uyumlu çalışacak şekilde sertleştirildi.
- Preview endpointinde beklenmeyen hatalar loglanır ve kullanıcıya okunabilir Türkçe hata detayı döner.
- Frontend API hata gösterimi HTTP kodu ve backend `detail` mesajını birlikte gösterecek şekilde iyileştirildi.
- Regresyon testi: tablo içinde `NaN`/`Infinity` olsa bile preview payload strict JSON olarak üretilebilir.

## v134 - AKYS Rol Modeli ve Varsayılan Yetki Matrisi

- Ürün adı kullanıcı arayüzünde AKYS (Akreditasyon Kalite Yönetim Sistemi) olarak güncellendi.
- Rol seti `Süper Admin`, `Kurum Admin`, `Birim Admin`, `Birim Koordinatörü`, `Editör / Hazırlayıcı`, `Onaylayıcı`, `Denetçi (İzleyici)` olarak standartlaştırıldı.
- Varsayılan Yetki Matrisi ve Sidebar Görünürlük Matrisi bu rol modeline göre güncellendi.
- Eski `Fakülte/MYO Admin`, `Editör` ve `İzleyici` değerleri geriye dönük alias olarak normalize edilir.

## v133 - Üç Kademeli Yönetici Hiyerarşisi

- Yetki ve görünürlük sıralaması Süper Admin > Kurum Admin > Birim Admin > Editör / Hazırlayıcı > Onaylayıcı > Denetçi (İzleyici) olarak tekleştirildi.
- Kurum Admin artık Yetki Matrisi içinde Birim Admin sütununu, Süper Admin tarafından kendisine açık bırakılan Kurum Admin tavanını aşmadan yönetebilir.
- Tenant matrix override okuması Kurum Admin tavanıyla kırpılır; eski/stale alt rol izinleri üst rütbe kapatıldığında efektif kalamaz.
- Frontend rol sıralaması ve backend `ROLE_RANK` aynı sıraya getirildi.
- Regresyon testleri tenant admin -> faculty admin delegation ve stale lower grant cap senaryolarını kapsayacak şekilde güncellendi.

## v131 - Permission Matrix Download

- Yetki Matrisi ekranına son görünür matrisi CSV ve JSON olarak indirme eklendi.
- İndirme çıktısı İşlem Yetki Matrisi, Sidebar Görünürlük Matrisi ve program seçiliyken Section Bazlı Yetki Matrisi satırlarını kapsar.
- Export rol hiyerarşisine göre filtrelenir; Kurum/Fakülte adminleri üst rütbe sütunlarını indiremez.
- Backend için `/api/admin/permissions/download?format=csv|json&program_id=...` endpointi eklendi.
- Yeni regresyon testi: `tests/test_permission_matrix_download_export.py`.

## v129 - Hierarchy, Faculty Scope and Studio Refinement

- Birim Admin Program Yönetimi kapsam hatası giderildi; `list_programs_admin`, `list_program_users_admin`, program oluşturma/kopyalama/arşivleme ve atama işlemleri fakülte kapsamını uygular.
- Rol hiyerarşisi ve alt rol görünürlüğü eklendi; üst rütbe kararları alt rütbe tarafından ezilemez.
- Birim Admin için tenant-genel operation/sidebar matrix kalıcı kaydı kilitlendi; program bazlı section policy ayrı korunur.
- Program rapor ayarları program-scoped `program_setting:{program_id}:...` anahtarlarıyla ayrıştırıldı.
- Akreditasyon Stüdyosu dashboard'una komut paneli, iş akışı özeti ve öncelikli başlık kartları eklendi.
- Yeni regresyon testleri `tests/test_faculty_admin_role.py` içine eklendi.


## v1.2.9-accreditation-studio

- Rapor Merkezi ürün dili Akreditasyon Stüdyosu olarak güncellendi.
- Sağ panel Akreditasyon Asistanı haline getirildi.
- Standartlara Göre Eksiklik Tarama backend endpointi ve frontend akışı eklendi.
- Kanıt Eşleştirme Asistanı backend endpointi ve frontend akışı eklendi.
- Yetki matrisine `report_studio.standards_scan` ve `report_studio.evidence_match` izinleri eklendi.
- `docs/ACCREDITATION_STUDIO.md` dokümantasyonu eklendi.

## v100.5 - Granular Action Permission Matrix

- Program Yönetimi sekmeleri ayrı yetkilere bağlandı: Tanımlı Programlar, Yeni Program, Program Kopyala, Program Bazlı Kullanıcı ve Rol Atama, Program Kullanıcıları.
- Dashboard içi kritik alanlar backend aksiyon izinleriyle korundu: Bildirim Merkezi, Görev & Eksik Analizi, İstatistikler, Gelişmiş Dashboard, Tam Activity Trail, Versiyon Karşılaştırma.
- `assert_program_operation_permission` ve `assert_any_operation_permission` guard fonksiyonları eklendi.
- Frontend Program Yönetimi sekmeleri permission matrix sonucuna göre ayrı ayrı gösterilir.
- Yeni regresyon testleri: `tests/test_granular_action_permissions.py`.

## v128 - Enterprise Hardening Release

- Follow-up hardening: removed backend EventSource access-token query fallback, added streamed request body guard, exposed `MEDEK_COOKIE_SECURE`, aligned Nginx body limit to 60 MB, and enabled Uvicorn proxy headers in the API container.
- Standardized runtime/release versioning as `v128-enterprise-hardening`.
- Added database-backed readiness healthcheck at `/api/health/ready` and Docker healthcheck wiring.
- Replaced frontend EventSource bearer-token query usage with a short-lived HttpOnly stream session cookie.
- Added request body and chunked upload size guards for evidence, report import, DOCX import, and backup restore flows.
- Added Redis healthcheck and RQ worker dependency healthcheck command.
- Hardened clean release packaging so `.env`, data, node modules, build artifacts, and archives are excluded.


## v117 - Tenant Admin Matrix Scope

- Kurum Admin için Kurum Yönetimi sekmesi `tenant.manage` iznine bağlandı ve varsayılan olarak kapatıldı.
- Kullanıcı & Rol Yönetimi sekmeleri `user.view`, `user.manage`, `user.login_attempts.view` izinlerine göre ayrıldı.
- Giriş Denemeleri backend tarafında tenant-aware filtrelendi; Kurum Admin sadece kendi kurumundaki kullanıcıların denemelerini görür.
- Program Yönetimi alt sekmeleri işlem yetkileriyle ilişkilendirildi.
- Kullanıcı kayıtlarına `created_by` alanı eklendi.

## v114 User Archive Visibility Fix

- Kullanıcı silme işlemi soft delete/arşiv mantığıyla netleştirildi.
- Silinen kullanıcılar artık Kayıtlı Kullanıcılar listesinde görünmez.
- Arşiv/Geri Yükleme ekranına silinen kullanıcı kayıtları eklendi.
- Kullanıcı geri yükleme akışı, kullanıcının program yetki kayıtlarını da güvenli şekilde geri açar.


## v109 PostgreSQL Production Hardening

- PostgreSQL runtime backend eklendi (`MEDEK_DB_BACKEND=postgresql`).
- Docker Compose PostgreSQL servisi ve healthcheck ile güncellendi.
- SQLite uyumlu repository SQL'leri için PostgreSQL compatibility layer eklendi.
- Tenant-aware PostgreSQL indeksleri ve üretim şeması güncellendi.
- SQLite → PostgreSQL migration ve cutover doğrulama araçları eklendi.
- Detay: `docs/POSTGRESQL_PRODUCTION_HARDENING.md`.

# v106 Advanced Analytics Export

- Advanced Analytics Dashboard için DOCX/PDF export endpointleri eklendi.
- Export job sistemine `analytics_docx` ve `analytics_pdf` tipleri eklendi.
- Analytics payload trend, durum dağılımı ve onay dağılımı ile genişletildi.
- Frontend dashboard ve Rapor Dışa Aktar ekranlarına Analytics export butonları eklendi.


## v105 - Workflow Automation

- Workflow otomasyon motoru eklendi.
- Admin paneline `Ayarlar & Yedek → Workflow Otomasyon` sekmesi eklendi.
- Geciken/yaklaşan termin, onay bekleyen ve revizyon bekleyen başlıklar için otomatik hatırlatma üretimi eklendi.
- In-app notification ve SMTP e-posta akışı aynı `workflow_reminder` olayı üzerinden çalışır.
- Workflow ayarları, önizleme, manuel çalıştırma ve çalıştırma geçmişi endpointleri eklendi.
- `workflow_runs` ve `workflow_run_items` tabloları eklendi.
- Otomasyon tekrarlarını sınırlayan `repeat_days` koruması ve manuel `force` modu eklendi.
- Otomasyon regresyon testi eklendi.


## v103 Multi-Tenant Isolation

- Kurum/tenant ve fakülte/MYO veri modeli eklendi.
- Program, kullanıcı ve program kullanıcı atamaları `tenant_id` ile izole edildi.
- Global Admin / Tenant Admin ayrımı için `tenant_scope` eklendi.
- Admin paneline `Kurum / Fakülte İzolasyonu` sekmesi eklendi.
- Kullanıcı formuna kurum, fakülte ve tenant kapsamı alanları eklendi.
- Yeni endpointler: `/api/admin/tenants`, `/api/admin/tenant-faculties`, `/api/admin/tenant-dashboard`.


## 2026-06-12 - v101 Live Enterprise Control

- Admin paneline `/api/ai/status` üzerinden çalışan Ollama bağlantı testi eklendi.
- Program bazlı SSE canlı olay akışı eklendi; bildirim rozeti ve export işleri anlık güncellenir.
- Rapor Dışa Aktar ekranı job progress kartları, yüzde bilgisi, durum yenileme ve hazır dosya indirme akışıyla güçlendirildi.
- Granular Permission ekranına rol odağı ve başlık/işlem araması eklendi; dar ekranda checkbox matrisi daha yönetilebilir hale getirildi.
- Geri Yükleme ekranı program dışında kanıt, tablo, başlık ve program kullanıcı arşiv kayıtlarını da gösterir hale getirildi.
- `enterprise/` modülleri için yeni `backend.enterprise.facade` yüzeyi eklendi; eski `enterprise_features.py` uyumluluğu korundu.


## 2026-06-12 - SMTP Ayar Formu Görünürlük Düzeltmesi

- E-posta Bildirimleri sekmesinde SMTP ayarları endpoint'i hata verse bile ayar formu artık gizlenmez.
- `MEDEK_API_SECRET` değişimi sonrası kayıtlı SMTP şifresi çözülemezse ekran kullanıcıya açık uyarı gösterir ve şifrenin yeniden girilmesine izin verir.
- SMTP durum çıktısına `password_error` tanı bilgisi eklendi.


## 2026-06-12 - Otomatik Çözünürlük Algılama ve En İyi Yerleşim Motoru
- Frontend tarafına `useAdaptiveViewport` hook'u eklendi.
- Sistem artık kullanıcının CSS viewport genişliği/yüksekliği, cihaz piksel oranı, ekran yönü, pointer tipi ve kısa ekran durumuna göre otomatik karar veriyor.
- Dashboard kolon sayısı otomatik belirleniyor: uygun genişlikte 3 kolon, orta/kısa ekranda 2 kolon, dar ekranda 1 kolon.
- Sidebar masaüstünde sabit, tablet/mobil veya dar viewport durumunda üstten akışa giren yapıya dönüşüyor.
- Tablo yoğunluğu ekran durumuna göre `table-wide-scroll`, `table-dense-scroll`, `table-mobile-scroll` modlarına ayrıldı.
- Kısa laptop ekranlarında kompakt kart/menü/başlık davranışı güçlendirildi.


## 2026-06-12 - Responsive Viewport Release

- Added viewport-aware layout classes (`screen-xs` / `screen-sm` / `screen-md` / `screen-lg` / `screen-xl`) for resolution-based UI behavior.
- Added compact density mode for short-height laptop screens such as 1366x768.
- Improved Dashboard command panels so Role Tasks, Priority Headings and Live Status Charts stay 3 columns on wide screens, 2 columns on medium screens, and 1 column on small screens.
- Improved notification and control tab bars with horizontal overflow protection on small displays.
- Hardened data tables with per-column minimum width, horizontal scroll, sticky action column, and dark-mode compatible table backgrounds.
- Added adaptive spacing, title size and card padding with CSS clamp variables.


## 2026-06-11 - Role workflow and program management polish

- Program Yönetimi > Tanımlı Programlar tablosuna kalıcı Sil işlemi eklendi. Silme işlemi programla ilişkili başlık, kanıt, tablo, onay, çıktı, bildirim ve yetki kayıtlarını temizler.
- Onaya gönderme işlemi yalnızca Editör / Hazırlayıcı rolüne indirildi; Admin ve Onaylayıcı artık onaya gönder butonu görmez ve API düzeyinde de gönderemez.
- Editör / Hazırlayıcı, Rapor Dizini'nde kaydedilmemiş değişiklik varken başlığı onaya gönderemez; önce “Bu Başlığı Kaydet” uyarısı gösterilir.
- Kullanıcı & Rol Yönetimi > Program Yetki Notu sekmesi rol matrisi, program atama özeti ve operasyon notlarıyla genişletildi.
- Rapor Önizleme içindeki teknik kuyruk açıklaması sade kullanıcı metnine dönüştürüldü.


## 2026-06-11 - Role visibility update

- `Rapor Dışa Aktar` menüsü tüm rollere açıldı.
- `Son Teslim Tarihi Planı` Onaylayıcı rolüne de görünür hale getirildi.
- Son teslim tarihi düzenleme yetkisi Admin rolünde bırakıldı.

## Security hardening follow-up

- Added root-level `SECURITY.md` that links to the detailed `docs/SECURITY.md`.
- Removed wildcard `*` from the default `MEDEK_TRUSTED_HOSTS` fallback.
- Production startup now rejects `MEDEK_TRUSTED_HOSTS=*`.
- Program-level role/section assignments now increment `token_version` to invalidate stale authorization tokens.
- Global role / active-status / academic-status changes now increment `token_version` even when password is unchanged.
- Added `backend/repos/` compatibility modules to start the repository-layer split without breaking existing imports.

# Changelog

## v100 Web-Only

- Paket yalnızca FastAPI, React/Vite, Nginx ve Docker web dağıtım dosyalarını içerecek şekilde sadeleştirildi.
- Eski yerel arayüz dosyaları, tek dosyalı uygulama kalıntıları, eski compose dosyası ve eski bağımlılık dosyaları dağıtım paketinden çıkarıldı.
- Kanıt arşivinden mevcut kanıt bağlarken `code` ve `note` alanlarının API katmanından repository katmanına aktarılması düzeltildi.
- Tablo arşivinden başlığa tablo ekleme akışı gerçek `/tables/attach` endpoint'ini kullanacak şekilde düzeltildi.
- Bölüm atanmış Editör / Hazırlayıcı kullanıcılar için kanıt ve tablo listeleme kapsamı erişilebilir başlıklarla sınırlandı.
- Ayar okuma endpoint'i program erişim kontrolü yapacak şekilde güncellendi.
- JSON yedek indirme ve sistem durumu endpoint'leri Admin rolüyle sınırlandı.
- Proje doğrulama aracı ve test kapsamı web-only paket yapısına göre güncellendi.

## v100-security-hardening

- Added token_version-based session invalidation. Password changes and active-status changes revoke older tokens.
- Added active/locked account checks in current_user.
- Added password strength validation for new and changed users.
- Added login lockout compatibility with existing users table migrations.
- Added in-memory API rate limiting middleware for login, upload, export, and general API calls.
- Added Nginx security headers and CSP baseline.
- Added production environment validation for API secret and CORS wildcard usage.
- Updated Docker Compose environment handling; PostgreSQL rehearsal password no longer blocks web-only startup interpolation.
- Added SECURITY.md, DEPLOYMENT_CHECKLIST.md, and CI_CD.md operational documents.
## Table Editing Fix
- Imported/linked tables can now be loaded back into the rich table editor from both the section inline table panel and the global Table Management screen.
- Existing table records are updated by `table_id`, so renaming a table while editing no longer silently creates a separate copy.

## v100 Sidebar report import/export restore

- Sidebar'a `Rapor Dışa Aktar` modülü tekrar eklendi.
- Admin ve Editör / Hazırlayıcı rolleri için `Rapor İçe Aktar` modülü tekrar görünür hale getirildi.
- Rapor İçe Aktar veri değiştirdiği için Denetçi (İzleyici) rolünden gizli bırakıldı.

## Sistem Şablonları Koruması

MEDEK/MÜDEK ve diğer akreditasyon profillerinin ana ölçüt iskeletleri `backend/templates/*.json` dosyalarıyla korunur. Uygulama açılışında `system_templates` tablosu otomatik seed edilir. Ayrıntı: `docs/SYSTEM_TEMPLATES.md`.


## v100.4 - Deleted medek_data recovery hardening

- Added startup data directory self-healing for `medek_data`, `kanitlar`, `exports`, and `backups`.
- Added clearer production error when a fresh database is detected without a strong `MEDEK_BOOTSTRAP_ADMIN_PASSWORD`.
- Added `docs/DATABASE_RECOVERY.md` and `tools/recover_deleted_medek_data.ps1`.
## UI profile routing update
- Program Yönetimi > Yeni Program ekranında Fakülte / MYO / Birim alanı açılır menüye çevrildi.
- Fakülte/MYO seçimine göre akreditasyon profili otomatik atanır: Mühendislik=MÜDEK, Eğitim=EPDAD, MYO=MEDEK, Spor=SPORAK, Eczacılık=ECZAKDER, Tıp=TEPDAD, Turizm=TURAK, İlahiyat=AA, Sağlık Bilimleri=SABAK, İletişim=İLEDAK.
- EDEK ve SABAD aktif akreditasyon profili seçeneklerinden ve sistem şablonu seed listesinden çıkarıldı.
- Kullanıcı & Rol Yönetimi ekranındaki sistem rolü alanı gizlendi; rol atamaları Program Yönetimi içindeki program bazlı atama sekmesine bırakıldı.
- Statü / Unvan alanı standart akademik/idari unvan listesinden seçilebilir hale getirildi.

# ver_100 hardened patch notes

Bu paket üzerinde uygulanan ana düzeltmeler:

- Frontend Dockerfile kalıcı olarak düzeltildi; Vite artık `npm install` + `npm run build` akışıyla kurulup derlenir.
- Üretim `health` endpoint'i sadeleştirildi; dosya sistemi/veritabanı yolu dışarı verilmez.
- Kullanıcı public modeli `must_change_password` bilgisini döndürür.
- `/api/me/change-password` endpoint'i eklendi.
- İlk/yenilenmiş şifreyle giriş yapan kullanıcılar şifre değiştirmeden diğer API endpointlerine geçemez.
- Frontend'e zorunlu şifre değiştirme ekranı eklendi.
- Sidebar sadeleştirildi; Hazırlık Denetimi, Rapor Dışa Aktar ve AI menüleri ana menüden kaldırıldı.
- Dashboard ana ölçüt kartları `measure_criteria` verisini kullanacak şekilde düzeltildi.
- Dashboard içindeki AI başlığı tarafsız stratejik öncelik özetine dönüştürüldü.
- Section editor içindeki AI taslak butonu kaldırıldı.
- Test kapsamı 20'den 22 teste çıkarıldı.
- `pytest`, `tools/validate_project.py` ve `npm run build` başarıyla çalıştırıldı.

Temiz release üretimi için:

```powershell
powershell -ExecutionPolicy Bypass -File tools\make_release_zip.ps1
```

## v100 enterprise-ops hardening

- Added persisted background export jobs table and API endpoints.
- Added background DOCX/PDF export controls to the Report Preview screen.
- Split backend imports in `backend/main.py` to focused `backend.repos.*` facade modules.
- Extracted authentication screens into `frontend/src/views/AuthScreens.jsx` as the first frontend modularization slice.
- Added PostgreSQL migration copy tool `tools/postgres_migrate.py` and aligned PostgreSQL schema with current SQLite tables.
- Added optional HTTPS/intranet Caddy reverse proxy compose overlay and documentation.
- Added Windows Task Scheduler backup installer and latest-backup restore helper.

## Runtime navigation safety fix

- Sidebar module transitions are now wrapped with a React error boundary so a single module render problem cannot collapse the entire app into a blank page.
- API list responses are normalized on the frontend before map/filter/table rendering.
- DataTable is hardened against malformed/non-array rows.
- The project validator and tests now check the runtime safety guards.


## Ürünleşme Modülleri

- Bildirim Merkezi eklendi.
- Görev & Eksik Analizi ekranı eklendi.
- Teslim Takvimi ve Yardım & Kullanım ekranları eklendi.
- Toplu işlemlere toplu son teslim tarihi atama desteği eklendi.
- Kanıt haritası, onay zaman çizelgesi ve kalite kırılımı `insights` endpoint'i ile tekleştirildi.

## Premium UI Polish Pack

- Sidebar modülleri görev odaklı gruplara ayrıldı: Ana Panel, Rapor Hazırlama, Onay & Kalite, Çıktılar ve Yönetim.
- Sidebar program bağlam kartı, hazırlık yüzdesi ve canlı rozet/sayaç sistemi eklendi.
- Dashboard hero alanı rol bazlı çalışma görünümü, hızlı durum etiketleri ve daha güçlü KPI diliyle yenilendi.
- Dashboard'a rol bazlı hızlı aksiyonlar, bugün öncelikli işler ve CSS tabanlı mini grafikler eklendi.
- Rapor bölümü kartları, boş durum ekranları, skeleton loading ve responsive davranışlar iyileştirildi.
- Mobil görünüm, koyu tema uyumluluğu, hover/mikro animasyonlar ve premium kart stili güçlendirildi.

## v100.4 - Enterprise workflow expansion

- Granular Permission + Section Bazlı Editör / Hazırlayıcı eklendi. Her başlık için görme, metin, PUKÖ, termin, onay, revizyon, kanıt, tablo ve AI taslak izinleri ayrı yönetilebilir.
- Offline AI Draft / Ollama entegrasyonu eklendi. `MEDEK_AI_ENABLED=true` ve `MEDEK_AI_PROVIDER=ollama` ile kurum içi yerel model kullanılabilir; erişilemezse sistem güvenli şablon üreticiye düşer.
- Mobile PWA iyileştirmeleri eklendi: offline fallback, cache versiyonlama, install prompt, update bildirimi ve offline read-only uyarısı.
- Advanced Analytics Dashboard güçlendirildi: KPI kartları, bar grafik görünümü ve başlık bazlı risk heat map eklendi.
- `validate_project.py` onay akışı kontrolü yeni granular permission modeliyle uyumlu hale getirildi.

## SMTP Gmail AUTH düzeltmesi

- SMTP gönderiminde STARTTLS sonrası ikinci `EHLO` eklendi; Gmail/Office365 gibi sunucularda görülebilen yanlış `SMTP AUTH extension not supported by server` hatası giderildi.
- Gmail için daha açıklayıcı hata mesajları eklendi: 587+TLS, 465+SSL ve Google Uygulama Şifresi uyarıları.
- Gönderen alanına yalnızca görünen ad yazılırsa SMTP kullanıcı e-postasıyla otomatik RFC uyumlu `From` başlığı oluşturulur.
- E-posta ayar ekranına Gmail modu bilgilendirmesi ve alıcı adresi doğrulaması eklendi.


## v102 Governance Audit Versioning

- Compliance audit payload ve DOCX export eklendi.
- Workflow reminder önizleme altyapısı eklendi.
- Version Control ekranı iki snapshot/güncel kayıt arasında yan yana diff gösterecek şekilde güçlendirildi.
- Hazırlık Denetimi ekranı governance, workflow ve compliance verilerini tek panele aldı.

## v107 Mobile PWA Pro

- Rol bazlı mobil bottom navigation eklendi.
- Kamera ile kanıt yükleme akışı eklendi.
- Mobil/tablet için sticky topbar, touch-friendly tablar ve safe-area desteği eklendi.
- Service worker GET API cache ile offline read-only deneyimi güçlendirildi.
- Manifest kısayolları Rapor Dizini ve Kanıt Yükle seçenekleriyle genişletildi.

## v110 Deployment / Installer Wizard

- Admin paneline `Ayarlar & Yedek → Kurulum Sihirbazı` sekmesi eklendi.
- Yeni endpointler eklendi: `GET /api/admin/deployment/wizard` ve `POST /api/admin/deployment/smoke`.
- Sihirbaz secret gücü, base URL, CORS, trusted host, PostgreSQL bağlantısı, kanıt klasörü yazma izni, SMTP, Ollama ve job backend kontrollerini tek ekranda gösterir.
- Güvenli `.env` iskeleti ve kopyalanabilir deployment komutları üretildi.
- Secret/DSN değerleri maskelenerek gösterilir; ham parola veya token dönmez.


## v111 Role Delegation Matrix Pro

- Rol yapısı Süper Admin / Kurum Admin / Editör / Hazırlayıcı / Onaylayıcı / Denetçi (İzleyici) olarak yeniden düzenlendi.
- Süper Admin tüm yetki sınırlarını belirler; Kurum Admin sadece kendi kurumunda ve kendisine açık bırakılan izinleri Editör / Hazırlayıcı / Onaylayıcı / Denetçi (İzleyici) rollerine dağıtabilir.
- Yetki Matrisi ekranı pro delegasyon akışı, rol kartları, kilitli sütunlar, kategori filtresi ve modern toggle kontrolleriyle güçlendirildi.
- İşlem, sidebar ve section bazlı editör yetkileri aynı çalışma alanında yönetilebilir hale getirildi.


## v112 Tenant Safe Delete Center

- Kurum silme akışı bağlı kayıt farkındalıklı hale getirildi.
- Bağlı program/kullanıcı varsa doğrudan hata yerine güvenli işlem paneli açılır.
- Pasifleştir, bağlı kayıtları başka kuruma taşı ve kurumla birlikte arşivle seçenekleri eklendi.
- Backend tarafında `mode=safe|deactivate|move|archive_children` kontrolleri eklendi.

## v113 - Permission Matrix Tabbed Pro

- Yetki Matrisi ekranı üç ana sekmeye ayrıldı: İşlem Yetki Matrisi, Sidebar Görünürlük Matrisi, Section Bazlı Granular Editör / Hazırlayıcı Yetkileri.
- Her ana sekmeye alt sekme yapısı eklendi: işlem izinleri kategori bazlı, sidebar görünürlüğü modül/yönetim bazlı, section politikaları ana başlık bazlı ayrıldı.
- Toplu aç/kapat işlemleri artık aktif alt sekme kapsamına göre uygulanabilir hale getirildi.
- Rol odağı, arama, kilitli sütun koruması ve Süper Admin → Kurum Admin yetki devri davranışı korunarak daha pro bir arayüz sağlandı.

## v115 - Tenant Archive Visibility Guard

- Program Yönetimi > Program Kullanıcıları ekranında arşivlenen/silinen kuruma bağlı yetki kayıtlarının görünmeye devam etmesi düzeltildi.
- Admin program ve program kullanıcıları sorguları artık arşivlenmiş tenant, program, kullanıcı ve program yetkisi kayıtlarını varsayılan listelerden dışlar.
- Kurum + bağlıları arşivleme akışı için regresyon testi eklendi.

## v116 - Sidebar Tenant Context Selector

- Sidebar çalışma alanı seçicisine **Kurum / Üniversite** alanı eklendi.
- Seçim hiyerarşisi `Kurum → Fakülte / MYO → Bölüm → Program` şeklinde düzenlendi.
- Süper Admin çok kurumlu çalışma alanları arasında geçiş yapabilir.
- Kurum Admin tek kurumla sınırlı çalışır; tek kurum varsa kurum seçimi kilitli/pasif görünür.
- Program bilgi kartında kurum adı, profil ve rapor yılı birlikte gösterilir.
- Arşivlenmiş/pasif kurumlara ait programlar aktif çalışma alanında görünmez.


## v118 First Institution Setup Wizard

- İlk açılışta teknik `tenant_default` kaydı artık hazır kurum gibi gösterilmez.
- Süper Admin için İlk Kurum Kurulumu ekranı eklendi.
- Kurum kurulumu tamamlanmadan program/fakülte/program kullanıcı sekmeleri açılmaz.
- `setup_completed_at` alanı ile ilk kurum kurulumunun tamamlanma durumu izlenir.

## v119 Sidebar Institution Refresh Fix
- Sidebar çalışma alanı seçicisi artık program olmasa bile aktif kurumları tenant listesinden yükler.
- İlk kurum kurulumu sonrası kurum seçimi otomatik güncellenir; fakülte/bölüm/program henüz yoksa bilgilendirici placeholder gösterilir.
- Kurum değişiminde program yoksa eski program bağlamı temizlenir.


## v120 - Birim Admin Rol Kapsamı

- Rol yapısına **Birim Admin** eklendi.
- Program Bazlı Kullanıcı ve Rol Atama ekranında bu rol seçildiğinde Bölüm ve Program Adı alanları gizlenir.
- Seçili Fakülte/MYO altındaki tüm programlar otomatik atama kapsamına alınır.
- Backend, Birim Admin atamasının tek bir Fakülte/MYO kapsamıyla sınırlı kalmasını doğrular.
- Yetki Matrisi artık Birim Admin rolünü ayrı sütun olarak destekler.


## v121 - Rol Bazlı Varsayılan Yetki Matrisi

- Süper Admin / Kurum Admin / Fakülte-MYO Admin / Editör / Hazırlayıcı / Onaylayıcı / Denetçi (İzleyici) için önerilen varsayılan işlem matrisi ayarlandı.
- Sidebar görünürlük matrisi rol hiyerarşisine göre yeniden dengelendi.
- Section bazlı granular editör yetkilerinde varsayılan rol davranışı güncellendi.
- Mevcut kurulumlarda uygulanabilmesi için Yetki Matrisi ekranına “Önerilen Varsayılan Matrisi Yükle” aksiyonu eklendi.
- Detay: docs/ROLE_DEFAULT_PERMISSION_PRESET.md

## v122 - Tenant Appearance Packages
- Görünüm ayarları yalnızca Süper Admin'e taşındı.
- Tanımlı kurumlara atanabilen 11 hazır görünüm paketi eklendi.
- Kurum görünüm paketi o kurumdaki tüm kullanıcılara otomatik uygulanır.
- Tenant tablosuna `appearance_package` ve `appearance_config_json` alanları eklendi.

## v123 - Tenant appearance applied to full dashboard

- Kurum bazlı görünüm paketleri artık sadece sidebar'a değil, ana çalışma alanı, dashboard, bildirim merkezi, hero kartları, tab yapıları, tablolar, formlar ve KPI kartlarına da uygulanır.
- Tema değişkenleri `--tenant-accent` ve `--tenant-sidebar` üzerinden tüm yüzeye yayıldı.
- Koyu tema ve yüksek kontrast görünüm paketleri için ana içerik arka planı ve tablo başlıkları iyileştirildi.

## v124 Dashboard & Role Help Refinement

- Gösterge Paneli'ndeki tekrar eden KPI kartları kaldırıldı; aynı özet hero alanında korunur.
- Rol Bazlı Görevler, Bugün Öncelik ve Canlı Durum Grafikleri expander'ları varsayılan kapalı hale getirildi.
- Rapor Bölümleri / Ana Ölçütler yanındaki Bugün Ne Yapılmalı paneli kaldırıldı.
- Detaylı Analiz & Operasyonel Görünüm expander'ı varsayılan kapalı hale getirildi.
- Kurum Yönetimi KPI kartları Kurum/Tenant, Fakülte/MYO ve Program olarak yan yana gösterilir.
- Yardım & Kullanım ekranı artık sadece aktif kullanıcının rolüne özel kılavuzu gösterir.


## v126 AI / Ollama Runtime Manager
- AI / Ollama Testi paneline enable/disable, runtime ayar kaydı, model listeleme ve model yükleme/doğrulama eklendi.
- Kurulum Sihirbazı AI uyarısı artık kullanıcıyı bu panele yönlendirir.


## v127 - First Setup Blank Tenant Fix

- Varsayılan teknik tenant artık yeni kurulumda gerçek kurum adıyla önceden doldurulmaz.
- İlk Kurum Kurulumu ekranı boş form ile açılır; Süper Admin kurum adını, kısa kodu ve domaini kendisi girer.
- Eski sürümlerde setup tamamlanmamış placeholder üzerinde oluşmuş örnek kurum adı/kodu otomatik temizlenir.
- Program Yönetimi ve sidebar, kurum kurulumu tamamlanana kadar gerçek kurum varmış gibi davranmaz.

## v129 Professional Reporting Pack

- Smart Templates + Clause Library eklendi: ölçüt bazlı standart cümle/blok kütüphanesi, seed ve kullanıcı tanımlı clause kayıtları.
- Split View raporlama ekranı eklendi: sol panelde rehber/kanıt/Clause Library, sağ panelde canlı önizleme ve cümle diff.
- Otomatik tutarlılık kontrolleri eklendi: çapraz referans, eksik kanıt, deadline, tablo boşluğu ve sayı-tablo tutarlılığı uyarıları.
- Rapor Kalite Skoru v1 eklendi: tamamlanma, kanıt kapsamı, tutarlılık, onay oranı ve başlık heatmap'i.
- Tek tık tam rapor paketi eklendi: Ana Rapor DOCX/PDF, Kanıt Dizini CSV, Kalite Skoru, Tutarlılık Kontrolü ve Mock Denetim JSON çıktıları.
- Denetçi okuma paketi eklendi: watermark notlu DOCX/PDF ve salt okunur denetçi linki altyapısı.
- Paragraf/blok tabanlı veri modeli hazırlandı: content_blocks ve content_block_versions tabloları.
- Önceki bulgu düzeltildi: section submit varsayılanı yalnızca Editör / Hazırlayıcı rolüne çekildi.
- Önceki bulgu düzeltildi: section_versions snapshot parametre dizilimi kontrol edildi.
- PostgreSQL şema dosyası runtime SCHEMA_SQL ile yeniden senkronize edildi.


## Kurumsal Dosya Hiyerarşisi
- `medek_data/kurumlar` altında kurum/birim/fakülte/bölüm/program/yıl bazlı klasörleme eklendi.
- Kanıtlar, tablo JSON kopyaları ve DOCX/PDF çıktıları zaman damgalı dosya adlarıyla bu hiyerarşiye yazılır.
- Her program klasörüne `manifest.json` üretilir.

## ver_100_11_readable_archive_mirror

- Rapor metni ve PUKÖ alanları artık `04_rapor_metni/<başlık>/latest.json` ve `latest.md` olarak okunabilir dosya aynasına yazılır.
- Manuel başlık kayıtları ve onay işlemleri için `04_rapor_metni/<başlık>/versions/` altında zaman damgalı JSON/Markdown versiyonları oluşturulur.
- Tüm başlıkların birleşik arşiv kopyası `04_rapor_metni/tum_rapor_latest.json` olarak güncellenir.
- Onay/revizyon geçmişi `05_onay_gecmisi/approval_history.jsonl` ve zaman damgalı JSON dosyalarıyla aynalanır.
- Audit log kayıtları `06_loglar/activity_log.jsonl` dosyasına eklenir.
- Mevcut veritabanı kayıtlarını klasör yapısına dökmek için `tools/mirror_full_archive.py`, `.ps1` ve `.sh` eklendi.

## ver_100_11_personal_role_backup

- Rol bazlı kişisel ZIP yedek endpointleri eklendi.
- Kullanıcılar seçili programdaki veya tüm yetki alanındaki verileri kendi bilgisayarına ZIP olarak indirebilir.
- ZIP içinde rapor metni, PUKÖ, tablolar, kanıt dosyaları, çıktı kayıtları, onay/yorum/sürüm ve işlem geçmişi bulunur.
- Yönetici JSON yedeği korunurken kişisel ZIP yedek yalnızca okunabilir kullanıcı arşivi olarak tasarlandı.
