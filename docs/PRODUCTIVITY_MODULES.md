# Ürünleşme Modülleri

Bu sürümde demo veri/kurulum sihirbazı ve antivirüs taraması dışında kalan ürünleşme önerileri bir araya getirildi.

## Bildirim Merkezi

E-posta bildirimlerine ek olarak sistem içi bildirim kayıtları kullanıcıya gösterilir. Okundu/okunmadı takibi `notification_reads` tablosunda tutulur.

## Görev & Eksik Analizi

`/api/programs/{program_id}/insights` endpoint'i metin, kanıt, tablo, PUKÖ, son teslim tarihi, onay ve kalite verilerini birleştirerek görev listesi, eksiklik listesi, kalite kırılımı, zaman çizelgesi ve kanıt haritası üretir.

## Teslim Takvimi

Son teslim tarihleri `Gecikti`, `Bu hafta`, `Bu ay`, `Planlandı` ve `Tarih yok` gruplarıyla gösterilir.

## Yardım & Kullanım

Rol bazlı kısa kullanım kartları ve başlık teslim kontrol listesi arayüzde gösterilir.

## Toplu İşlemler

Toplu durum güncellemeye ek olarak toplu son teslim tarihi atama desteği eklendi.

## PostgreSQL notu

SQLite varsayılan runtime olarak korunmuştur. PostgreSQL geçiş araçları ve şema dosyaları korunur; çok kullanıcılı kurumsal yayında tam PostgreSQL runtime adapter fazı ayrıca kontrollü biçimde tamamlanmalıdır.
