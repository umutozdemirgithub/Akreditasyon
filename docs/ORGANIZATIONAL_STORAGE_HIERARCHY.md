# Kurum/Birim/Fakülte/Bölüm/Program Bazlı Dosya Arşivi

Bu sürümde kanıt dosyaları, tablo JSON kopyaları ve DOCX/PDF çıktıları `medek_data/kurumlar` altında programın kurumsal hiyerarşisine göre tutulur. PostgreSQL hâlâ ana veri kaynağıdır; dosya sistemi denetim ve arşiv amaçlı okunabilir kopyaları taşır.

Örnek yapı:

```text
Akreditasyon/
└─ 00_canli_veri/
   └─ medek_data/
      └─ kurumlar/
         └─ kurum_erciyes-universitesi/
            └─ birim_halil-bayraktar-saglik-hizmetleri-myo/
               └─ fakulte_halil-bayraktar-saglik-hizmetleri-myo/
                  └─ bolum_tibbi-hizmetler-ve-teknikler/
                     └─ program_ilk-ve-acil-yardim/
                        └─ yil_2025/
                           ├─ 01_kanitlar/
                           │  └─ A.1/
                           ├─ 02_tablolar/
                           │  └─ A.1/
                           ├─ 03_rapor_ciktilari/
                           ├─ 04_rapor_metni/
                           │  ├─ A.1/latest.json
                           │  ├─ A.1/latest.md
                           │  └─ tum_rapor_latest.json
                           ├─ 05_onay_gecmisi/
                           │  └─ approval_history.jsonl
                           ├─ 06_loglar/
                           │  └─ activity_log.jsonl
                           └─ manifest.json
```

Kaydedilenler:

- Kanıt yükleme: `01_kanitlar/<başlık>/`
- Kanıt dizini: `01_kanitlar/evidence_index.json`
- Tablo kaydı: `02_tablolar/<başlık>/` içinde zaman damgalı JSON kopyası
- Doğrudan DOCX/PDF indirme ve job çıktısı: `03_rapor_ciktilari/`
- Rapor metni ve PUKÖ alanları: `04_rapor_metni/<başlık>/latest.json` ve `latest.md`
- Tam rapor metni: `04_rapor_metni/tum_rapor_latest.json`
- Onay/revizyon geçmişi: `05_onay_gecmisi/approval_history.jsonl`
- Audit log aynası: `06_loglar/activity_log.jsonl`
- Her işlemde `manifest.json` güncellenir.

Not: PostgreSQL hâlâ ana veri kaynağıdır. Dosya sistemi, denetim ve arşiv amaçlı okunabilir ayna olarak kullanılır.


## Eski kayıtları yeni klasör yapısına kopyalama

Yeni kayıtlar otomatik olarak yeni hiyerarşiye yazılır. Daha önce `medek_data/kanitlar` veya eski `exports` altında oluşmuş dosyaları yeni yapıya kopyalamak için:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\migrate_to_org_storage.ps1
```

Linux/macOS için:

```bash
bash ./tools/migrate_to_org_storage.sh
```

Bu işlem eski dosyaları silmez; kanıt ve tamamlanmış export kayıtlarının veritabanındaki dosya yolunu yeni klasöre günceller, tablolar için de zaman damgalı JSON kopyaları üretir.


## Okunabilir tam arşiv aynası

Mevcut veritabanı kayıtlarını rapor metni, PUKÖ, tablo, kanıt dizini, onay geçmişi ve audit log ile birlikte dosya sistemine dökmek için:

```powershell
powershell -ExecutionPolicy Bypass -File .	ools\mirror_full_archive.ps1
```

Ayrıntı: `docs/READABLE_ARCHIVE_MIRROR.md`
