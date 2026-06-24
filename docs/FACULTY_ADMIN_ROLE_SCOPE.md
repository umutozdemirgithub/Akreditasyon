# Birim Admin Rol Kapsamı

Bu sürümde rol hiyerarşisine **Birim Admin** eklendi.

## Rol hiyerarşisi

- Süper Admin
- Kurum Admin
- Birim Admin
- Editör / Hazırlayıcı
- Onaylayıcı
- Denetçi (İzleyici)

## Atama davranışı

Program Yönetimi → Program Bazlı Kullanıcı ve Rol Atama ekranında rol **Birim Admin** seçildiğinde Bölüm ve Program Adı seçimleri gizlenir. Seçili Fakülte/MYO altındaki tüm programlar otomatik olarak atama kapsamına alınır.

Bu rol tek bir Fakülte/MYO kapsamına bağlıdır. Farklı fakültelere ait programlar aynı Birim Admin atamasına birlikte dahil edilemez.

## Yetki Matrisi

Birim Admin rolü Yetki Matrisi içinde ayrı bir sütun olarak görünür. Süper Admin bu rolün yapabileceği işlemleri merkezi olarak belirleyebilir. Kurum Admin, Süper Admin tarafından kendisine açılan sınırlar içinde kendi kurumundaki Birim Admin, Editör / Hazırlayıcı, Onaylayıcı ve Denetçi (İzleyici) rollerine yetki devredebilir.
