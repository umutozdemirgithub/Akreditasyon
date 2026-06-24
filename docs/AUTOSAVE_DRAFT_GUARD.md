# Otomatik Taslak Kaydı

Bu sürümde editör/hazırlayıcı başlık metni üzerinde çalışırken veri kaybını azaltmak için otomatik taslak kaydı eklendi.

## Kapsam

Otomatik kayıt şu alanları kapsar:

- Durum
- Rapor metni
- PUKÖ alanları: Planla, Uygula, Kontrol Et, Önlem Al
- Notlar
- Son teslim tarihi

Kanıt ve tablo işlemleri zaten kendi yükleme/kaydetme aksiyonlarında kalıcı kayda gider.

## Çalışma Şekli

1. Kullanıcı başlıkta değişiklik yapar.
2. Değişiklik anında tarayıcı localStorage alanına geçici taslak olarak yazılır.
3. Kullanıcı 25 saniye işlem yapmazsa sistem aynı başlığı sessizce backend'e kaydeder.
4. Backend kaydı başarılı olursa localStorage taslağı temizlenir.
5. Bağlantı koparsa yerel taslak tutulur; aynı başlık tekrar açıldığında daha yeni yerel taslak geri yüklenir.

## Güvenlik ve Yetki

Otomatik kayıt mevcut `PUT /api/programs/{program_id}/sections/{section_key}` endpointini kullanır. Bu yüzden tüm rol, program, başlık ve alan bazlı izin kontrolleri aynen geçerlidir.

Onaya gönderilmiş veya onaylanmış başlıklarda normal kullanıcı için salt okunur kuralı devam eder; otomatik kayıt çalışmaz.

## Audit / Sürüm Geçmişi

Backend otomatik kayıt isteklerini `is_autosave=true` olarak alır.

- `section_versions.change_summary`: `Otomatik taslak kaydı`
- audit/activity log: `Başlık otomatik kaydedildi`

Manuel kayıtlar ise `Manuel başlık kaydı` ve `Başlık güncellendi` olarak kaydedilir.
