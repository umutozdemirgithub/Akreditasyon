# Rol Delegasyonu ve Profesyonel Yetki Matrisi

Bu sürümde rol modeli kurumsal hiyerarşiye göre yeniden düzenlendi:

- Süper Admin
- Kurum Admin
- Editör / Hazırlayıcı
- Onaylayıcı
- Denetçi (İzleyici)

## Yetki devri modeli

Süper Admin tüm kurumları ve yetki sınırlarını yönetir. Kurum Admin rolü ise yalnızca Süper Admin tarafından kendisine açık bırakılan izinleri kendi kurumundaki Editör / Hazırlayıcı, Onaylayıcı ve Denetçi (İzleyici) rollerine dağıtabilir.

Kurum Admin aşağıdaki işlemleri kendi kurum sınırında yapabilir:

- Kurum içi kullanıcıları ve program atamalarını yönetme
- Editör / Hazırlayıcı / Onaylayıcı / Denetçi (İzleyici) rollerine izin dağıtma
- Sidebar görünürlüğünü kurum içi roller için düzenleme
- Section bazlı editör yetkilerini kurum içi roller için düzenleme

Kurum Admin şunları yapamaz:

- Süper Admin oluşturma
- Süper Admin yetkisini değiştirme
- Kendi Kurum Admin tavanını aşan izni alt role verme
- Başka kuruma ait kullanıcı veya programlara yetki verme

## Yetki Matrisi Pro UI

Yetki Matrisi ekranı artık üç katmanlıdır:

1. İşlem Yetki Matrisi
2. Sidebar Görünürlük Matrisi
3. Section Bazlı Granular Editör / Hazırlayıcı Yetkileri

Ekranda rol odağı, kategori filtresi, bölüm/işlem araması, kilitli sütunlar, pro toggle kontrolleri ve yetki devri akışı görünür.
