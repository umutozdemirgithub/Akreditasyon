# Premium Kanıt Arşivi ve Tablo Yönetimi

Bu sürümde Kanıt Arşivi ve Tablo Yönetimi, Akıllı Rapor Stüdyosu ile aynı görsel ve işlevsel seviyeye taşınmıştır.

## Kanıt Arşivi

Eklenen deneyimler:

- Premium Kanıt Kokpiti hero alanı
- Kanıt kart grid görünümü
- Kanıt kalite skoru
- Risk göstergesi: iyi / uyarı / kritik
- Bağlı ölçüt sayısı, dosya türü ve yaş bilgisi
- Kanıt heatmap görünümü
- Sağ panelde Akıllı Kanıt Asistanı
- Eksik bağlantı, eksik not ve kod standardı önerileri
- Hızlı filtreler: riskli, bağlantısız, PDF, görsel, not eksik, son 7 gün
- Toplu kanıt arşivleme altyapısı

## Tablo Yönetimi

Eklenen deneyimler:

- Premium Tablo Kokpiti hero alanı
- Tablo kart grid görünümü
- Satır/sütun/doluluk/kalite skorları
- Tablo heatmap görünümü
- Sağ panelde Akıllı Tablo Asistanı
- Boş hücre, eksik sütun, veri kaynağı ve kanıt kodu önerileri
- Hızlı filtreler: riskli, boş, doluluk düşük, geniş tablo, bağlantısız
- Canlı tablo ön izleme paneli
- Toplu tablo arşivleme altyapısı

## Yeni Backend Endpointleri

```text
GET /api/programs/{program_id}/evidence/studio
GET /api/programs/{program_id}/tables/studio
```

## Yeni Yetki Matrisi Satırları

```text
evidence.premium.view
evidence.ai_coach.view
evidence.bulk_manage
table.premium.view
table.ai_coach.view
table.bulk_manage
```

## Yetki Notu

Kanıt ve tablo temel endpointleri artık yalnızca program erişimine değil, ilgili granular işlem iznine de bakar:

```text
evidence.view
evidence.upload
evidence.link
evidence.download
evidence.delete
table.view
table.edit
table.attach
table.delete
```

Bu sayede sidebar görünürlüğü ile backend işlem güvenliği aynı matrise bağlanır.
