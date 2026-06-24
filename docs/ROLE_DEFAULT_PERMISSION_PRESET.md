# Rol Bazlı Varsayılan Yetki Matrisi

Bu sürümde işlem yetkileri, sidebar görünürlüğü ve section bazlı granular editör yetkileri için rol hiyerarşisine uygun önerilen varsayılanlar tanımlandı.

## Varsayılan rol mantığı

- **Süper Admin:** tüm kurumlar, tüm ayarlar, tüm matrise tam erişim.
- **Kurum Admin:** kendi kurumu içinde program, kullanıcı, rol dağıtımı, yetki delegasyonu, denetim ve operasyon yönetimi; kurum oluşturma/silme ve teknik sistem ayarları varsayılan kapalı.
- **Birim Admin:** atandığı Fakülte/MYO kapsamındaki tüm bölüm ve programlarda içerik, onay, kanıt, tablo, termin ve rapor operasyonlarına hakim; global kurum/teknik ayarlara erişmez.
- **Editör / Hazırlayıcı:** atanmış başlıklarda içerik üretir, kanıt/tablo ekler, PUKÖ doldurur ve onaya gönderir; onay kararı vermez.
- **Onaylayıcı:** onay kuyruğunu, revizyonları, kalite durumunu ve raporu inceler; onay/revizyon/kilidi açma kararlarını verir; içerik yazmaz.
- **Denetçi (İzleyici):** salt okunur izleme, rapor önizleme/dışa aktarma, kalite durumu ve yardım ekranlarına erişir; değişiklik yapmaz.

## Var olan kurulumlarda uygulama

Mevcut veritabanında daha önce kaydedilmiş matris varsa sistem onu korur. Yeni varsayılanları uygulamak için:

1. Süper Admin ile **Yetki Matrisi** ekranına girin.
2. **Önerilen Varsayılan Matrisi Yükle** düğmesine basın.
3. Kontrol edin.
4. **Yetki ve Sidebar Matrislerini Kaydet · Bölüm Politikalarını Kaydet** düğmesine basın.

Bu yaklaşım özel kurum ayarlarının yanlışlıkla ezilmesini engeller.
