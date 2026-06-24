# Güncelleme Merkezi

Güncelleme Merkezi, akreditasyon şablon kaynaklarını ve YÖK Atlas akademik yapı değişikliklerini güvenli şekilde izler.

## Temel ilke

Sistem hiçbir resmi/akademik veriyi kullanıcı onayı olmadan değiştirmez.

Akış:

1. Kaynak kontrol edilir.
2. Fark varsa güncelleme adayı oluşturulur.
3. Yönetici adayı inceler.
4. Kabul ederse uygulanır; yok sayarsa kayıt arşivlenir.
5. Activity Trail’e işlem kaydı düşer.

## İzlenen alanlar

- Akreditasyon kuruluşlarının şablon/kılavuz kaynakları
- Paket içindeki `backend/templates/*.json` şablonları
- YÖK Atlas kaynaklı fakülte/MYO/bölüm/program değişiklikleri

## Güvenli uygulama

- Mevcut rapor metinleri otomatik değiştirilmez.
- Resmi web kaynağı değişirse kaynak baz sürümü güncellenir; yapılandırılmış JSON şablonu yoksa manuel şablon doğrulaması gerekir.
- YÖK Atlas yeni program tespit ederse yeni program adayı üretir; silme/pasifleştirme otomatik yapılmaz.
- Fakülte/program ekleme kullanıcı onayı gerektirir.

## API

```text
GET  /api/admin/update-center
POST /api/admin/update-center/check
POST /api/admin/update-center/candidates/{candidate_id}/apply
POST /api/admin/update-center/candidates/{candidate_id}/ignore
```

`POST /api/admin/update-center/check` gövdesi:

```json
{ "scope": "all", "online": false }
```

`online=false` paket içi şablon farklarını ve kayıtlı kaynak durumunu kontrol eder. `online=true` sunucunun internet çıkışı varsa resmi web kaynakları ve YÖK Atlas kontrolünü de çalıştırır.

## Yetkiler

```text
update_center.view
update_center.check
update_center.apply
```

Varsayılan olarak Süper Admin ve Kurum Admin yetkilidir.
