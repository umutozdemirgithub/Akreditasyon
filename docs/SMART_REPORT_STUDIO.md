# Akıllı Rapor Stüdyosu / Rapor Merkezi

Bu sürümde Rapor Dizini, premium görünümlü **Rapor Merkezi** haline getirildi. Amaç; rapor metni, PUKÖ, kanıt, tablo, kalite skoru, AI önerisi, versiyon ve toplu işlemleri tek çalışma ekranında toplamak.

## Eklenen UX Özellikleri

- Modern kart grid görünümü: Her başlık bir karttır.
- Kanban görünümü: Taslak / Onay Bekliyor / Revize / Tamam kolonları.
- Progress overview hero: Genel ilerleme, kalite skoru, riskli ölçüt ve tahmini bitiş.
- Hızlı filtreler: Tümü, benim sorumluluklarım, gecikenler, onay bekleyenler, kanıt eksik, AI hazır, revize.
- Sol mini bölüm haritası: Rapor hiyerarşisi + ilerleme yüzdesi + risk rengi.
- Sağ bağlam paneli: Seçili başlığın kalite, kanıt, tablo, AI ve versiyon kısayolları.
- Bulk action bar: Çoklu seçimle durum, termin, kalite yenileme ve AI taslak üretme.
- Mikro animasyonlar ve tenant accent uyumlu modern kart tasarımı.
- Dark mode uyumlu stüdyo bileşenleri.

## Eklenen AI / Kalite Özellikleri

- Hızlı AI önerisi: Başlığın zayıf noktalarını, kanıt önerilerini ve yazım ipuçlarını üretir.
- PUKÖ önerisi: Planla / Uygula / Kontrol Et / Önlem Al alanları için taslak öneri verir.
- Kanıt öneri motoru: Başlık içeriğine göre beklenen kanıt tiplerini listeler.
- Otomatik kalite skoru: Metin uzunluğu, kanıt, tablo, PUKÖ ve onay durumundan 0-100 skor üretir.
- Risk seviyesi: iyi / uyarı / riskli sınıflandırması.
- AI öneri geçmişi için section alanları: `ai_suggestions_json`, `last_ai_review_at`.

## İşbirliği ve Versiyon

- Canlı işbirliği ping altyapısı: Aynı başlıkta çalışan kullanıcılar editörde uyarı olarak görünür.
- Section export: Seçili başlık tek başına DOCX/PDF olarak indirilebilir.
- Versiyon diff kısayolu: Sağ panel ve kart aksiyonlarından versiyon karşılaştırmaya geçilir.

## Backend Endpointleri

- `GET /api/programs/{program_id}/report-studio`
- `POST /api/programs/{program_id}/sections/{section_key}/ai/suggestions`
- `POST /api/programs/{program_id}/sections/{section_key}/quality/recalculate`
- `PUT /api/programs/{program_id}/bulk/studio`
- `POST /api/programs/{program_id}/sections/{section_key}/collaboration/ping`
- `GET /api/programs/{program_id}/sections/{section_key}/collaboration`
- `GET /api/programs/{program_id}/sections/{section_key}/export/docx`
- `GET /api/programs/{program_id}/sections/{section_key}/export/pdf`

## Yetki Matrisi

Yeni granular izinler:

- `report_studio.view`
- `report_studio.kanban.view`
- `report_studio.context_panel.view`
- `report_studio.section_export`
- `report_studio.bulk_ai`
- `report_studio.collaboration.view`

Bu izinler İşlem Yetki Matrisi içinde **Rapor Merkezi** kategorisi altında görünür. Backend kontrolleri yalnızca sidebar görünürlüğüne bağlı değildir; API seviyesinde de uygulanır.

## Veritabanı Alanları

`sections` tablosuna eklenen alanlar:

- `responsible_username`
- `quality_score`
- `risk_level`
- `ai_suggestions_json`
- `last_ai_review_at`

Yeni tablo:

- `section_collaboration_sessions`
