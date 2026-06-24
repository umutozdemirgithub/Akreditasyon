# Masaüstü Akreditasyon Klasörü

Bu sürümde uygulamanın canlı verileri proje klasörü yerine masaüstündeki `Akreditasyon` klasörüne yönlendirilir.

Windows başlatma aracı `tools/start_web_stack.ps1` çalıştırıldığında `.env` içine `AKREDITASYON_ROOT` değeri otomatik yazılır. Varsayılan hedef:

```text
C:/Users/<Kullanıcı>/Desktop/Akreditasyon
```

Linux/macOS başlatma aracı `tools/start_web_stack.sh` çalıştırıldığında varsayılan hedef:

```text
~/Desktop/Akreditasyon
```

## Klasör yapısı

```text
Akreditasyon/
├─ 00_canli_veri/
│  ├─ postgresql/                  # PostgreSQL canlı veri dosyaları
│  └─ medek_data/
│     ├─ kanitlar/                 # Yüklenen kanıt dosyaları
│     ├─ exports/                  # DOCX/PDF çıktı dosyaları
│     └─ backups/                  # Uygulama içi yedek çalışma alanı
├─ 01_zaman_damgali_yedekler/      # Tam yedekler: yyyy-MM-dd_HH-mm-ss
├─ 02_dis_aktarimlar/              # Kullanıcı/kurum dışa aktarım alanı
├─ 03_loglar/                      # İşletim notları/log alanı
├─ 04_kurulum/                     # Başlatma zaman damgaları
└─ 99_arsiv/                       # Manuel arşiv alanı
```

## Docker bağlantısı

`docker-compose.web.yml` artık şu bind mount yollarını kullanır:

```yaml
${AKREDITASYON_ROOT}/00_canli_veri/postgresql:/var/lib/postgresql/data
${AKREDITASYON_ROOT}/00_canli_veri/medek_data:/app/medek_data
```

Böylece programlar, kullanıcılar, rapor metinleri ve onay kayıtları PostgreSQL tarafında; kanıt dosyaları ve DOCX/PDF çıktıları ise `medek_data` tarafında aynı ana klasör altında saklanır.

## Zaman damgalı tam yedek

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\backup_medek.ps1
```

Linux/macOS:

```bash
bash tools/backup_medek.sh
```

Yedek çıktısı örneği:

```text
Akreditasyon/01_zaman_damgali_yedekler/2026-06-23_10-30-00/
├─ postgres_medek_2026-06-23_10-30-00.sql
├─ medek_data_2026-06-23_10-30-00.zip veya .tar.gz
└─ manifest.json
```

## Not

Canlı PostgreSQL klasörü zaman damgalı yapılmaz; aksi halde her yeniden başlatmada sistem boş veritabanı ile açılabilir. Zaman damgası canlı veri üzerinde değil, güvenli yedek/snapshot klasörlerinde kullanılır.
