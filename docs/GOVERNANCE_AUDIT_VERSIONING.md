# v102 Governance, Audit and Versioning

Bu sürüm, v101 canlı kontrol altyapısının üzerine governance katmanını ekler.

## Yeni backend endpointleri

- `GET /api/programs/{program_id}/compliance`
  - Activity log, onay/revizyon geçmişi, bildirimler, export geçmişi ve versiyon snapshot kayıtlarını tek denetim payload'ında döndürür.
- `GET /api/programs/{program_id}/compliance/docx`
  - Denetim/uyum raporunu DOCX olarak üretir.
- `GET /api/programs/{program_id}/workflow/reminders`
  - Geciken termin, yaklaşan termin, bekleyen onay ve revizyon aksiyonlarını üretir.
- `GET /api/programs/{program_id}/sections/{section_key}/versions?base_id=...&compare_id=...`
  - Güncel kayıt veya iki tarihsel snapshot arasında karşılaştırma yapar.

## Arayüz yenilikleri

- Hazırlık Denetimi ekranına Compliance DOCX ve Workflow Hatırlatma sekmeleri eklendi.
- Version Control ekranı artık iki sürüm seçerek yan yana karşılaştırma yapabilir.
- Diff çıktısı satır bazlı, yan yana ve alan değişiklikleri olarak görüntülenir.

## Kapsam dışı kalanlar

Bu sürüm otomatik zamanlanmış e-posta göndermez; hatırlatma listesi üretir. Otomatik gönderim sonraki workflow automation fazında planlanmıştır.
