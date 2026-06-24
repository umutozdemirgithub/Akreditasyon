# Sistem Şablonları ve Veritabanı Kaybı Koruması

Bu sürümde MEDEK, MÜDEK, SABAD, EPDAD, İLEDAK, SABAK, EDEK, AA, SPORAK, TURAK, ECZAKDER ve TEPDAD rapor iskeletleri uygulama paketindeki JSON dosyalarıyla korunur.

## Nerede tutulur?

Sistem şablonları şu klasördedir:

```text
backend/templates/
```

Her dosya bir akreditasyon profilini içerir:

```text
MEDEK.json
MUDEK.json
EPDAD.json
...
```

Bu dosyalarda profil adı, sürüm, kurum bilgisi ve başlık/ana ölçüt listesi bulunur.

## Veritabanı silinirse ne olur?

Veritabanı silinirse kullanıcıların oluşturduğu programlar, rapor metinleri, kanıt bağlantıları, tablolar, onaylar ve kullanıcılar kaybolur. Ancak sistem şablon JSON dosyaları uygulama paketinde kaldığı için yeni veritabanı açılışında şablon kayıtları yeniden oluşturulur.

Yani:

- Sistem şablon iskeletleri korunur.
- Kullanıcıların doldurduğu özel içerikler yalnızca backup varsa geri döner.
- Kanıt dosyaları fiziksel olarak kalsa bile DB bağlantıları silinmişse uygulama hangi başlığa bağlı olduklarını bilemez.

## Otomatik seed

Uygulama açılışında `system_templates` tablosu otomatik doldurulur. Bu işlem mevcut program verisini ezmez.

## Admin ekranı

Admin kullanıcıları `Ayarlar & Yedek > Sistem Şablonları` sekmesinden şunları yapabilir:

- Sistem şablonlarını kontrol et / yeniden seed et.
- Seçili programda başlık listesi tamamen silinmişse eksik başlıkları yeniden kur.

## Backup önerisi

Tam geri dönüş için sadece SQLite dosyası değil, şu klasörler birlikte yedeklenmelidir:

```text
medek_data/medek.sqlite3
medek_data/evidence/
medek_data/backups/
medek_data/exports/
```

JSON şablon dosyaları release paketinde tutulduğu için ayrıca uygulama kaynak kodu/release zip'i de saklanmalıdır.
