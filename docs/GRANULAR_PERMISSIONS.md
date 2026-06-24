# Granular Permission + Section Bazlı Editör / Hazırlayıcı

Yetki modeli üç katmandan oluşur:

1. **İşlem Yetki Matrisi:** Rolün genel olarak hangi işlem ailesine erişebileceğini tanımlar.
2. **Sidebar Görünürlük Matrisi:** Kullanıcının sol menüde hangi modülleri göreceğini belirler.
3. **Section Bazlı Editör / Hazırlayıcı Politikası:** Seçili programdaki her rapor başlığı için görme, metin, PUKÖ, termin, onay, revizyon, kanıt, tablo ve AI taslak izinlerini ayrı ayrı yönetir.

Admin panelinde `Yetki Matrisi` ekranının altında yeni `Granular Permission + Section Bazlı Editör / Hazırlayıcı` tablosu bulunur.

## Varsayılan davranış

- Admin: tüm başlıklarda tam yetki.
- Editör / Hazırlayıcı: atanmış başlıklarda metin/PUKÖ/durum/kanıt/tablo/AI taslak ve onaya gönderme.
- Onaylayıcı: görme, termin, onay, revizyon ve onayı geri alma.
- Denetçi (İzleyici): salt okuma.

Program bazlı kullanıcı atamasındaki `assigned_sections` alanı hâlâ uygulanır. Section bazlı politika, bu kapsamın içinde daha ayrıntılı işlem izni sağlar.
