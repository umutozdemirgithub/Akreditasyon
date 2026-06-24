# Kurum Bazlı Görünüm Paketleri

Görünüm ayarları yalnızca Süper Admin tarafından yönetilir. Süper Admin, tanımlı kurumlara hazır görünüm paketlerinden birini atar. Atanan paket o kurumun Kurum Admin, Birim Admin, Editör / Hazırlayıcı, Onaylayıcı ve Denetçi (İzleyici) dahil tüm kullanıcılarına uygulanır.

Hazır paketler: Kurumsal Mavi, Executive Lacivert, Zümrüt Kalite, Sağlık MYO Turkuaz, Mühendislik Indigo, Eğitim Fakültesi Sky, Bordo Akreditasyon, Modern Mor, Amber Odak, Grafit Minimal, Yüksek Kontrast.

Endpointler:

- `GET /api/appearance/current`
- `GET /api/admin/appearance`
- `PUT /api/admin/appearance/tenants/{tenant_id}`

`/api/admin/appearance` ve güncelleme endpointi sadece Süper Admin içindir.
