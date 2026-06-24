# Premium Akıllı Rapor Stüdyosu

Bu sürüm Rapor Merkezi ekranını görsel ve iş akışı açısından premium bir çalışma alanına taşır.

## Eklenen ana iyileştirmeler

- Premium kart grid tasarımı
- İlerleme halkaları ve kalite metrikleri
- Kart üzerinde risk, deadline, sorumlu, kanıt, PUKÖ ve AI hazır etiketleri
- Rapor geneli heatmap görünümü
- Rapor geneli Pro 9.8+ hazırlık skoru
- Başlık bazlı 98+ kalite, tamamlanma, kanıt, PUKÖ, derinlik, tablo ve onay checklist'i
- 9.8+ hedefinden uzak başlıklar için öncelikli aksiyon listesi
- Sağ panelde Akıllı Asistan sekmeleri
  - AI Koç
  - Kanıt önerileri
  - Kalite skoru gerekçesi
  - 9.8+ kalite kapısı
  - Şablon bankası
- Bulk PUKÖ taslağı üretme
- Gerçek zamanlı işbirliği Seviye 2
  - Aktif kullanıcı göstergesi
  - Çakışma riski uyarısı
  - 30 saniyelik otomatik ping
- Yan yana görsel versiyon diff viewer
- Diff için AI değişiklik özeti
- Kurum/program bazlı şablon bankası altyapısı

## Yeni backend yetenekleri

- `section_template_bank` tablosu
- `GET /api/programs/{program_id}/sections/{section_key}/templates/bank`
- `POST /api/programs/{program_id}/templates/bank`
- Rapor Stüdyosu payload içinde zengin `heatmap`, `quality_dimensions`, `template_bank`, `pro_readiness`, `pro_overview`
- Versiyon karşılaştırma payload içinde `summary.ai_summary`

## Premium/Pro 9.8+ kalite kapısı

- `pro_readiness`: her başlık için 98+ kalite, 98+ tamamlanma, en az iki kanıt, kapalı PUKÖ döngüsü, 420+ kelime, tablo desteği ve onay akışı kontrolü.
- `pro_overview`: rapor genelinde ortalama Pro skor, hazır/yakın başlık sayısı, bloklayıcı sayısı ve sıradaki aksiyonlar.
- Arayüzde hero metrikleri, Pro Quality Gate paneli ve sağ asistan panelindeki `9.8+` sekmesi bu veriyi kullanır.

## Yeni yetki satırları

- `report_studio.heatmap.view`
- `report_studio.ai_coach.view`
- `report_studio.template_bank.view`
- `report_studio.template_bank.manage`

## Not

Google Docs benzeri karakter-seviyesi eşzamanlı merge editörü bu sürümde yoktur. Bu sürüm Seviye 2 işbirliği sunar: aktif kullanıcı, çakışma uyarısı ve soft collaboration awareness.
