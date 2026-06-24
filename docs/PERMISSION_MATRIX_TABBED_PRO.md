# Permission Matrix Tabbed Pro

Bu sürümde Yetki Matrisi ekranı üç ana yönetim alanına ayrılmıştır:

1. **İşlem Yetki Matrisi**
   - Program
   - Rapor Başlıkları
   - Onay Akışı
   - Kanıt
   - Tablo
   - Rapor Çıktısı
   - Denetim
   - Bildirim
   - AI
   - Yönetim

2. **Sidebar Görünürlük Matrisi**
   - Modüller
   - Yönetim

3. **Section Bazlı Granular Editör / Hazırlayıcı Yetkileri**
   - Ana ölçüt / başlık grubu bazlı alt sekmeler
   - Görme, metin düzenleme, PUKÖ, termin, onay, revizyon, kanıt, tablo ve AI taslak izinleri

## Yetki devri

- Süper Admin tüm rollere ve Kurum Admin tavan yetkisine karar verir.
- Kurum Admin yalnızca kendisine Süper Admin tarafından açık bırakılan Kurum Admin tavanını aşmadan kendi kurumundaki Birim Admin, Editör / Hazırlayıcı, Onaylayıcı ve Denetçi (İzleyici) rollerine dağıtım yapabilir.
- Kilitli sütunlar frontend’de pasif gösterilir; backend tarafındaki koruma devam eder.

## Kullanım

Ana sekmeden yetki alanı seçilir. Alt sekmeden kategori/başlık grubu seçilir. Rol odağı ile tablo tek role indirgenebilir. Aktif alt sekmede toplu Aç/Kapat işlemi yapılabilir.
