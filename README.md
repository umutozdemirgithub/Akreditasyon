# AKYS Web ver_100.1

## Masaüstü Akreditasyon Veri Klasörü

Web stack `tools/start_web_stack.ps1` veya `tools/start_web_stack.sh` ile başlatıldığında masaüstünde `Akreditasyon` klasörü hazırlanır. Canlı PostgreSQL verileri, kanıt dosyaları, DOCX/PDF çıktıları ve zaman damgalı yedekler bu ana klasör altında tutulur. Ayrıntılar: `docs/DESKTOP_AKREDITASYON_STORAGE.md`.


## ver_100.1 - Rol ve Tema Senkronizasyonu

- Paket kökü `ver_100`, uygulama sürümü `ver_100.1-role-theme-sync` olarak standartlaştırıldı.
- Rol adları kullanıcı arayüzünde `Editör / Hazırlayıcı` ve `Denetçi` olarak tekleştirildi; eski `Editör`, `Hazırlayıcı`, `İzleyici` ve `Denetçi (İzleyici)` değerleri geriye dönük alias olarak kabul edilir.
- Birim Koordinatörü varsayılan işlem/sidebar matrisinde ayrı sütun olarak korunur ve eski matris kayıtları temizlenirken senkronize edilir.
- Sidebar role-based accent, program bağlam kartı, mini ilerleme ve dar ekranda top navigation davranışıyla güçlendirildi.
- Dashboard hero, kalite skoru, KPI trendleri, widget library ve sürükle-bırak kart sıralama deneyimiyle yenilendi.

## v103 Multi-Tenant Isolation

- Kurum/tenant ve fakülte/MYO veri modeli eklendi.
- Program, kullanıcı ve program kullanıcı atamaları `tenant_id` ile izole edildi.
- Global Admin / Tenant Admin ayrımı için `tenant_scope` eklendi.
- Admin paneline `Kurum / Fakülte İzolasyonu` sekmesi eklendi.
- Kullanıcı formuna kurum, fakülte ve tenant kapsamı alanları eklendi.
- Yeni endpointler: `/api/admin/tenants`, `/api/admin/tenant-faculties`, `/api/admin/tenant-dashboard`.

## v134 - AKYS Rol Modeli ve Varsayılan Yetki Matrisi

- Ürün adı kullanıcı arayüzünde AKYS (Akreditasyon Kalite Yönetim Sistemi) olarak güncellendi.
- Varsayılan rol sıralaması `Süper Admin > Kurum Admin > Birim Admin > Birim Koordinatörü > Editör / Hazırlayıcı > Onaylayıcı > Denetçi` olarak standartlaştırıldı.
- Varsayılan Yetki Matrisi ve Sidebar Görünürlük Matrisi kullanıcı tarafından verilen AKYS rol tablosuna göre yeniden dengelendi.
- Denetçi rolü salt okuma / watermark mantığına, Onaylayıcı rolü okuma ve resmi karar akışına, Editör / Hazırlayıcı rolü içerik üretimine odaklandı.

## v133 - Üç Kademeli Yönetici Hiyerarşisi

- Yetki sıralaması netleştirildi: Süper Admin > Kurum Admin > Birim Admin > Editör / Hazırlayıcı > Onaylayıcı > Denetçi (İzleyici).
- Süper Admin Kurum Admin sütununu belirler; Kurum Admin kendi kurumunda Birim Admin, Editör / Hazırlayıcı, Onaylayıcı ve Denetçi (İzleyici) rollerine yetki dağıtır.
- Tenant override kayıtları okuma anında Kurum Admin tavanıyla kırpılır; Süper Admin Kurum Admin yetkisini kapatırsa eski alt rol grantleri efektif olamaz.
- Birim Admin tenant-genel işlem/sidebar matrisini ezemez; yalnız kendi birim/program kapsamındaki alt işleyişleri yönetir.
- Yetki Matrisi CSV/JSON indirme özelliği korunur ve aynı hiyerarşik görünürlük sınırlarına uyar.

## v129 - Hierarchy, Faculty Scope and Studio Refinement

- Birim Admin Program Yönetimi erişimi fakülte kapsamıyla düzeltildi; yetki açıldığında yalnız kendi birimindeki programları görebilir ve yönetebilir.
- Rol hiyerarşisi netleştirildi: Süper Admin > Kurum Admin > Birim Admin > Editör / Hazırlayıcı > Onaylayıcı > Denetçi (İzleyici). Her rol kendi ve altındaki rollerin işleyişini görür.
- Birim Admin'in Kurum Admin/Süper Admin tarafından belirlenen tenant genelindeki işlem/sidebar matrisini ezmesi engellendi.
- Rapor belge metadata alanları (`report_no`, `doc_date`, `rev_date`, `rev_no`) program bazlı saklanır; farklı programlara sızmaz.
- Akreditasyon Stüdyosu komut paneli, öncelik kartları, iş akışı özetleri ve görsel iyileştirmelerle daha kullanışlı hale getirildi.

## v128 - Enterprise Hardening Release

- Ana sürüm standardı `v128-enterprise-hardening` olarak tekleştirildi.
- SSE canlı akışta ana API token'ının query string ile taşınması kaldırıldı; kısa ömürlü HttpOnly stream cookie kullanılır.
- Upload/restore/import uçlarına request body ve chunk bazlı boyut sınırı eklendi.
- API readiness healthcheck veritabanını doğrular; Redis/RQ worker için healthcheck eklendi.
- Temiz release paketi `.env`, veritabanı, kanıt dosyası, `node_modules` ve build çıktısı içermez.

Bu paket AKYS (Akreditasyon Kalite Yönetim Sistemi) web dağıtımını içerir. Uygulama FastAPI tabanlı API, React/Vite tabanlı web arayüzü, Nginx reverse proxy, PostgreSQL üretim veritabanı ve isteğe bağlı Redis/RQ worker ile çalışır.

## İçerik

- `backend/`: FastAPI API, yetki kontrolleri, kanıt/tablo işlemleri, DOCX/PDF raporlama.
- `frontend/`: React web çalışma alanı ve Nginx statik yayın/proxy yapılandırması.
- `services/`: Yerel kural tabanlı AKYS rapor taslak ve kalite hesaplama servisleri.
- `tools/`: Kurulum, yedekleme, doğrulama ve PostgreSQL geçiş prova araçları.
- `docs/`: Web kurulum, operasyon, güvenlik, yedekleme ve geçiş dokümantasyonu.
- `docs/LIVE_ENTERPRISE_CONTROL.md`: SSE canlı bildirim, export progress, Ollama test paneli ve arşiv UI notları.
- `medek_data/`: SQLite veritabanı ve kanıt dosyaları için veri alanı.

Eski tek dosyalı yerel arayüz dosyaları bu pakette yer almaz.

## Hızlı Başlangıç

1. Ortam dosyasını oluşturun:

```bash
cp .env.web.example .env
```

2. `.env` içinde güçlü değerler verin:

```env
MEDEK_API_SECRET=uzun-rastgele-en-az-48-karakterlik-gizli-deger
MEDEK_BOOTSTRAP_ADMIN_PASSWORD=ilk-admin-icin-guclu-gecici-sifre
POSTGRES_PASSWORD=yalnizca-prova-profili-icin-guclu-sifre
MEDEK_WEB_PORT=8080
MEDEK_COOKIE_SECURE=false
```

3. Web yığınını başlatın:

```bash
docker compose --env-file .env -f docker-compose.web.yml up --build -d
```

4. Tarayıcıdan açın:

```text
http://localhost:8080
```

## Geliştirme

API bağımlılıkları:

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt
python tools/validate_project.py
python -m pytest -q
```

Frontend:

```bash
cd frontend
npm ci
npm run build
```

Yerel API geliştirme için:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Vite geliştirme sunucusu kullanılacaksa:

```bash
cd frontend
VITE_API_BASE_URL=http://localhost:8000/api npm run dev
```

## Güvenlik Notları

- `.env` canlı gizli değer içerir; temiz dağıtım zip'ine konulmaz. Kurulumda `.env.web.example` dosyasından yerelde oluşturulmalıdır.
- `MEDEK_API_SECRET` üretim ortamında zorunlu, placeholder olmayan ve en az 48 karakterlik rastgele bir değer olmalıdır.
- İlk/yenilenmiş şifreyle giriş yapan kullanıcılar çalışma alanına geçmeden önce güçlü şifre belirlemek zorundadır.
- `/api/health` üretim ortamında yalnızca temel sağlık yanıtı verir; dosya yolu gibi iç detayları sızdırmaz.
- Kanıt yüklemelerinde uzantı, boyut ve temel dosya imzası doğrulanır.
- Bölüm atanmış Editör / Hazırlayıcı kullanıcılar kanıt/tablo arşivinde yalnızca erişebildikleri başlık kapsamını görür.
- JSON yedek indirme ve sistem durumu gibi hassas işlemler Admin rolüyle sınırlıdır.
- JSON yedek veritabanı kayıtlarını içerir; tam yedek için `medek_data/` klasörü ayrıca saklanmalıdır.

## Doğrulanan Kontroller

```bash
python tools/validate_project.py
python -m compileall -q backend services core tools
python -m pytest -q
python -m pytest tests/test_static_security.py -q
cd frontend
npm.cmd ci
npm.cmd audit --audit-level=high
npm.cmd run build
```

## Temiz Dağıtım Paketi

Canlı `.env`, SQLite veritabanı, kanıt dosyaları, cache dosyaları ve eski zip arşivleri dağıtım paketine konulmamalıdır. Temiz paket üretmek için:

```powershell
powershell -ExecutionPolicy Bypass -File tools\make_release_zip.ps1
```

Çıktı `outputs/ver_100_role_theme_sync.zip` dosyasıdır. Zip üretimi tamamlandıktan sonra paket otomatik denetlenir; `.env`, SQLite veritabanı, kanıt dosyaları, cache, `node_modules`, `dist`, `outputs`, `work` veya eski zip arşivleri bulunursa üretim hata verir. Elle doğrulamak için:

```powershell
python tools\verify_release_zip.py outputs\ver_100_role_theme_sync.zip
```

Temiz kurulumda ilk admin kullanıcısı `admin` adıyla oluşturulur; bunun için sunucuda oluşturulan `.env` içinde `MEDEK_BOOTSTRAP_ADMIN_PASSWORD` güçlü bir değer olmalıdır. İlk girişten sonra admin kullanıcısı zorunlu şifre değiştirme ekranına yönlendirilir.

## Sistem Şablonları Koruması

MEDEK/MÜDEK ve diğer akreditasyon profillerinin ana ölçüt iskeletleri `backend/templates/*.json` dosyalarıyla korunur. Uygulama açılışında `system_templates` tablosu otomatik seed edilir. Ayrıntı: `docs/SYSTEM_TEMPLATES.md`.


### Deleted `medek_data` recovery

If `medek_data` is deleted, system templates are automatically restored from `backend/templates/*.json`, but users/program data requires backup. In production, set a strong `MEDEK_BOOTSTRAP_ADMIN_PASSWORD` before restart. See `docs/DATABASE_RECOVERY.md`.

## Enterprise Ops Additions

### Arka plan rapor çıktısı

`Rapor Önizleme` ekranında DOCX/PDF üretimi kuyruk işi olarak başlatılabilir. API endpointleri:

```text
POST /api/programs/{program_id}/report/jobs?export_type=docx
POST /api/programs/{program_id}/report/jobs?export_type=pdf
GET  /api/programs/{program_id}/report/jobs
GET  /api/programs/{program_id}/report/jobs/{job_id}/download
```

### Otomatik yedekleme

Windows Görev Zamanlayıcı kurulumu:

```powershell
powershell -ExecutionPolicy Bypass -File tools\install_backup_task.ps1 -RunAt "02:30"
```

Ayrıntı: `docs/AUTOMATED_BACKUP_WINDOWS.md`.

### HTTPS / kurum içi alan adı

Opsiyonel Caddy proxy:

```powershell
docker compose --env-file .env -f docker-compose.web.yml -f docker-compose.https.yml up --build -d
```

Ayrıntı: `docs/HTTPS_AND_INTRANET.md`.

### PostgreSQL aktarım provası

```powershell
python tools/postgres_readiness.py
python tools/postgres_migrate.py --dsn $env:POSTGRES_DSN --clear
```

Ayrıntı: `docs/POSTGRES_MIGRATION_PLAN.md`.

### Rol görünürlüğü notu

- `Rapor Dışa Aktar` menüsü tüm roller için görünür.
- `Son Teslim Tarihi Planı` Admin ve Onaylayıcı rollerinde görünür; tarih düzenleme yetkisi yalnızca Admin rolündedir.

### Redis/RQ üretim kuyruğu

Varsayılan rapor işi backend'i tek API container için `BackgroundTasks` olarak kalır. Birden fazla API instance, uzun süren PDF/DOCX üretimi veya daha güvenli job ayrıştırması gerektiğinde Redis + RQ kuyruğu kullanılmalıdır:

```powershell
docker compose --env-file .env -f docker-compose.web.yml -f docker-compose.queue.yml up --build -d
```

Ayrıntı: `docs/JOB_QUEUE.md`.

### Nginx ve Caddy rol ayrımı

- `frontend/nginx.conf`: container içindeki React statik dosyalarını yayınlar ve `/api` isteklerini API container'a proxy eder. Varsayılan lokal/pilot kurulum budur.
- `Caddyfile` + `docker-compose.https.yml`: isteğe bağlı kurum içi HTTPS/domain reverse proxy katmanıdır. Caddy, Nginx'in yerine geçmez; önünde TLS/proxy katmanı olarak çalışır.


## E-posta Bildirimleri

Onaya gönderme, revizyon, onay, son teslim tarihi, rol atama ve rapor çıktısı olayları için SMTP tabanlı bildirim desteği vardır. Ayrıntılar için `docs/EMAIL_NOTIFICATIONS.md` dosyasına bakın.


## Ürünleşme Modülleri

- Bildirim Merkezi eklendi.
- Görev & Eksik Analizi ekranı eklendi.
- Teslim Takvimi ve Yardım & Kullanım ekranları eklendi.
- Toplu işlemlere toplu son teslim tarihi atama desteği eklendi.
- Kanıt haritası, onay zaman çizelgesi ve kalite kırılımı `insights` endpoint'i ile tekleştirildi.

### Enterprise v100.4 Modülleri

Bu pakette dört kurumsal modül genişletildi:

1. **Granular Permission + Section Bazlı Editör / Hazırlayıcı:** Admin, seçili programdaki her başlık için rol bazlı görme/düzenleme/onay/kanıt/tablo/AI izinlerini ayrı ayrı yönetebilir.
2. **Offline AI Draft / Ollama:** Yerel Ollama modeliyle kurum dışına veri göndermeden taslak üretilebilir. Kapalıyken veya Ollama erişilemezken sistem yerel şablon tabanlı üreticiyle çalışır.
3. **Mobile PWA Pro:** Offline fallback, kurulum istemi, yeni sürüm bildirimi ve çevrimdışı read-only uyarısı eklendi.
4. **Advanced Analytics Dashboard:** Yönetici KPI kartları, grup bazlı grafikler ve risk heat map ile güçlendirildi.

Ollama kullanmak için `.env` içine şunları ekleyin:

```env
MEDEK_AI_ENABLED=true
MEDEK_AI_PROVIDER=ollama
MEDEK_OLLAMA_BASE_URL=http://localhost:11434
MEDEK_OLLAMA_MODEL=llama3.1
MEDEK_OLLAMA_TIMEOUT=45
```

Ayrıntılar için:

- `docs/GRANULAR_PERMISSIONS.md`
- `docs/OFFLINE_AI_OLLAMA.md`
- `docs/PWA_PRO_MODE.md`


## v102 Governance Audit Versioning

- Compliance audit payload ve DOCX export eklendi.
- Workflow reminder önizleme altyapısı eklendi.
- Version Control ekranı iki snapshot/güncel kayıt arasında yan yana diff gösterecek şekilde güçlendirildi.
- Hazırlık Denetimi ekranı governance, workflow ve compliance verilerini tek panele aldı.

## v105 Workflow Automation

Bu sürümde termin, onay ve revizyon süreçleri için otomatik hatırlatma motoru eklendi. Admin panelinde `Ayarlar & Yedek → Workflow Otomasyon` sekmesinden ayarlar yapılabilir, aday bildirimler önizlenebilir ve manuel çalıştırma yapılabilir. Ayrıntılar: `docs/WORKFLOW_AUTOMATION.md`.



## v106 Advanced Analytics Export

Advanced Analytics Dashboard artık DOCX/PDF olarak dışa aktarılabilir. Export job sistemine `analytics_docx` ve `analytics_pdf` tipleri eklendi. Yönetici raporu KPI özeti, risk heat map, PUKÖ dağılımı, trend tabloları ve öneriler içerir.

### v107 Mobile PWA Pro

Mobil kullanım için rol bazlı bottom navigation, kamera ile kanıt yükleme, offline read-only PWA cache ve touch-friendly editör davranışı eklendi. Ayrıntılar için `docs/MOBILE_PWA_PRO.md` dosyasına bakın.

## v109 PostgreSQL Production Hardening

- PostgreSQL runtime backend eklendi (`MEDEK_DB_BACKEND=postgresql`).
- Docker Compose PostgreSQL servisi ve healthcheck ile güncellendi.
- SQLite uyumlu repository SQL'leri için PostgreSQL compatibility layer eklendi.
- Tenant-aware PostgreSQL indeksleri ve üretim şeması güncellendi.
- SQLite → PostgreSQL migration ve cutover doğrulama araçları eklendi.
- Detay: `docs/POSTGRESQL_PRODUCTION_HARDENING.md`.


## v110 Deployment / Installer Wizard

Okul sunucusuna kurulumdan sonra Admin panelinde `Ayarlar & Yedek → Kurulum Sihirbazı` sekmesini açın. Bu panel PostgreSQL bağlantısı, CORS/trusted host ayarı, SMTP hazırlığı, Ollama durumu, kanıt klasörü yazma izni ve Docker deployment dosyalarını tek yerde kontrol eder. Detay: `docs/DEPLOYMENT_INSTALLER_WIZARD.md`.

Yeni backend endpointleri:

```txt
GET  /api/admin/deployment/wizard
POST /api/admin/deployment/smoke
```


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


## v118 First Institution Setup Wizard

- İlk açılışta teknik `tenant_default` kaydı artık hazır kurum gibi gösterilmez.
- Süper Admin için İlk Kurum Kurulumu ekranı eklendi.
- Kurum kurulumu tamamlanmadan program/fakülte/program kullanıcı sekmeleri açılmaz.
- `setup_completed_at` alanı ile ilk kurum kurulumunun tamamlanma durumu izlenir.


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


## v126 AI / Ollama Runtime Manager
- AI / Ollama Testi paneline enable/disable, runtime ayar kaydı, model listeleme ve model yükleme/doğrulama eklendi.
- Kurulum Sihirbazı AI uyarısı artık kullanıcıyı bu panele yönlendirir.


### İlk kurum kurulumu davranışı

Yeni kurulumda `tenant_default` teknik bir placeholder olarak tutulur; kurum adı, kısa kod ve domain alanları önceden doldurulmaz. Süper Admin ilk kurum bilgisini Program Yönetimi → Kurum Yönetimi ekranındaki İlk Kurum Kurulumu üzerinden tanımlar.

### Professional Reporting Pack

Bu paket Smart Templates + Clause Library, otomatik tutarlılık kontrolleri, rapor kalite skoru, cümle bazlı diff, mock denetim modu ve tek tık tam rapor/denetçi zip çıktısını içerir. Premium/Pro 9.8+ standardı için 98+ kalite kapısı, başlık bazlı Pro readiness, profesyonel rapor hazırlık paneli ve `Premium_98_Readiness.json` çıktısı eklidir. Ayrıntılar için `docs/PROFESSIONAL_REPORTING_PACK.md` ve `docs/PREMIUM_REPORT_STUDIO.md` dosyalarına bakın.

### Okunabilir tam arşiv aynası

Kurum/birim/fakülte/bölüm/program klasör yapısı artık kanıt ve çıktı dosyalarının yanında rapor metni, PUKÖ alanları, tablo JSON kopyaları, onay geçmişi ve audit log aynasını da tutar.

Yeni canlı kayıtlar otomatik aynalanır. Eski veritabanı kayıtlarını dosya sistemine dökmek için:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\mirror_full_archive.ps1
```

Ayrıntılar: `docs/READABLE_ARCHIVE_MIRROR.md`
