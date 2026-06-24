# Okunabilir Tam Arşiv Aynası

Bu sürümde veritabanı ana kaynak olarak korunur; buna ek olarak rapor metni, PUKÖ alanları, tablo kopyaları, kanıt dizini, onay geçmişi ve audit log kayıtları `medek_data/kurumlar/...` altında insan tarafından okunabilir dosyalar halinde aynalanır.

## Klasör yapısı

```text
Akreditasyon/
└─ 00_canli_veri/
   └─ medek_data/
      └─ kurumlar/
         └─ kurum_<kurum>/
            └─ birim_<birim>/
               └─ fakulte_<fakulte>/
                  └─ bolum_<bolum>/
                     └─ program_<program>/
                        └─ yil_<yil>/
                           ├─ 01_kanitlar/
                           │  ├─ A.1/
                           │  └─ evidence_index.json
                           ├─ 02_tablolar/
                           │  └─ A.1/*.json
                           ├─ 03_rapor_ciktilari/
                           ├─ 04_rapor_metni/
                           │  ├─ A.1/latest.json
                           │  ├─ A.1/latest.md
                           │  ├─ A.1/versions/*.json
                           │  ├─ A.1/versions/*.md
                           │  └─ tum_rapor_latest.json
                           ├─ 05_onay_gecmisi/
                           │  └─ approval_history.jsonl
                           ├─ 06_loglar/
                           │  └─ activity_log.jsonl
                           └─ manifest.json
```

## Ne zaman yazılır?

- Başlık manuel kaydedildiğinde `04_rapor_metni/<başlık>/latest.json` ve `latest.md` güncellenir; ayrıca `versions/` altında zaman damgalı kopya oluşur.
- Otomatik taslak kaydında `latest.json` ve `latest.md` güncellenir; gereksiz dosya şişmesini önlemek için varsayılan olarak versiyon dosyası oluşturulmaz.
- Tablo kaydedildiğinde PostgreSQL kaydı yanında `02_tablolar/<başlık>/` altında zaman damgalı JSON kopyası oluşur.
- Kanıt yüklendiğinde dosya `01_kanitlar/<başlık>/` altına kaydedilir; kanıt metadata bağlantısı PostgreSQL’de kalır.
- Onaya gönderme, revizyon, onay veya geri alma işleminde `05_onay_gecmisi/approval_history.jsonl` ve zaman damgalı JSON kopyası güncellenir.
- Program işlemlerinde `06_loglar/activity_log.jsonl` audit aynası güncellenir.
- Her önemli işlemde `manifest.json` son işlem bilgisiyle yenilenir.

## Mevcut verileri tek seferde aynalama

Önceden veritabanında bulunan kayıtları okunabilir arşive dökmek için:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\mirror_full_archive.ps1
```

Linux/macOS için:

```bash
bash ./tools/mirror_full_archive.sh
```

Bu komut eski verileri silmez. Sadece PostgreSQL/SQLite içindeki mevcut rapor metinlerini, tabloları, onay geçmişini, audit log kayıtlarını ve kanıt indeksini klasör yapısına yazar.

## Veri güvenliği notu

PostgreSQL hâlâ ana ve ilişkisel veri kaynağıdır. Okunabilir dosyalar denetim, yedek inceleme ve kurum içi arşiv kolaylığı içindir. Tam yedek için yine `tools/backup_medek.ps1` çalıştırılmalıdır.
