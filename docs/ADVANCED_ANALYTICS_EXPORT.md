# Advanced Analytics Export

Bu sürüm Advanced Analytics Dashboard için yönetici özeti üretir.

## Endpointler

- `GET /api/programs/{program_id}/advanced-reporting`
- `GET /api/programs/{program_id}/advanced-reporting/docx`
- `GET /api/programs/{program_id}/advanced-reporting/pdf`

## Export job tipleri

- `analytics_docx`
- `analytics_pdf`

## İçerik

- Yönetici KPI özeti
- Grup bazlı hazırlık ve onay oranları
- PUKÖ doluluk dağılımı
- Onay/hazırlık durum dağılımları
- Bölüm versiyon trendleri
- Aktivite trendleri
- Risk heat map
- Yönetici yorum ve önerileri

PDF üretimi için diğer PDF çıktılarında olduğu gibi sunucuda LibreOffice/soffice bulunmalıdır.
