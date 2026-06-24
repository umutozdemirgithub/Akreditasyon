# Professional Reporting Pack

Bu sürüm rapor üretimini yalnızca DOCX/PDF çıktısı olmaktan çıkarıp ölçüt bazlı kalite kontrol, standart blok yönetimi ve denetçi hazırlığı merkezi haline getirir.

## Eklenen ana yetenekler

- Smart Templates + Clause Library: ölçüt bazlı standart cümle/blok kütüphanesi, seed ve kullanıcı tanımlı clause kayıtları.
- Split View: sol panelde ölçüt rehberi, beklenen kanıtlar ve Clause Library; sağ panelde canlı önizleme ve cümle diff.
- Otomatik Tutarlılık Kontrolleri: çapraz referans, kanıt eksikliği, deadline, tablo boşluğu ve sayı/tablo uyumu.
- Rapor Kalite Skoru: tamamlanma, kanıt kapsamı, tutarlılık, onay oranı ve başlık bazlı heatmap.
- Premium/Pro 9.8+ Hazırlık Kapısı: genel kalite, tamamlanma, kanıt kapsamı, tutarlılık, onay ve zayıf başlık kriterlerini 98+ hedefiyle izler.
- Mock Denetim Modu: zayıf başlıklardan denetçi gözüyle örnek soru ve hazırlık maddesi üretir.
- Tam Rapor Paketi: Ana Rapor, PDF dönüşüm sonucu veya dönüşüm notu, kanıt dizini, kalite skoru, Premium 98 readiness, tutarlılık kontrolü ve mock denetim çıktıları tek ZIP içinde üretilir.
- Denetçi Paketi: watermark notlu salt okunur okuma kopyası ve süre sınırlı denetçi bağlantısı altyapısı.

## Premium/Pro 9.8+ standardı

- Hedef kalite skoru `98` ve kullanıcı etiketi `9.8+` olarak sabitlendi.
- `quality.premium_readiness` alanı 9.8+ kapısının hazır/yakın/aksiyon gerekli durumunu, kalan açıkları ve sıradaki aksiyonları döndürür.
- Profesyonel rapor ekranında 9.8+ kapısı, kriter kartları ve önerilen aksiyonlar görünür.
- Tam rapor ZIP paketi artık `Premium_98_Readiness.json` dosyasını da içerir.

## Backend API özetleri

- `GET /api/programs/{program_id}/professional-reporting`
- `GET /api/programs/{program_id}/professional-reporting/consistency`
- `GET /api/programs/{program_id}/professional-reporting/quality`
- `GET /api/programs/{program_id}/professional-reporting/mock-audit`
- `GET /api/programs/{program_id}/professional-reporting/clauses`
- `POST /api/programs/{program_id}/professional-reporting/clauses`
- `POST /api/programs/{program_id}/sections/{section_key}/professional-reporting/clauses/{clause_id}/insert`
- `GET /api/programs/{program_id}/sections/{section_key}/professional-reporting/sentence-diff`
- `GET /api/programs/{program_id}/professional-reporting/package.zip`
- `GET /api/programs/{program_id}/professional-reporting/auditor-package.zip`
- `GET/POST /api/programs/{program_id}/professional-reporting/auditor-links`

## Veri modeli

- `clause_library`
- `content_blocks`
- `content_block_versions`
- `consistency_check_runs`
- `report_quality_snapshots`
- `auditor_share_links`

## Test durumu

- `python -m pytest -q` → 141 passed
- `npm.cmd run build` → passed
- `npm.cmd audit --audit-level=high` → 0 vulnerability
- `python tools/validate_project.py` → all PASS

## Güvenlik notu

Temiz release paketi `.env`, veritabanı dosyaları, node_modules, dist ve ara çıktı ziplerini içermez. Dağıtım için `tools/make_release_zip.py` kullanılmalıdır.
