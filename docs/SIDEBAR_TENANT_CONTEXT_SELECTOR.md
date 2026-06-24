# Sidebar Kurum / Üniversite Seçici

Bu sürümde çalışma alanı seçici hiyerarşisi kurum bazlı hale getirildi.

## Yeni seçim sırası

1. Kurum / Üniversite
2. Fakülte / MYO
3. Bölüm
4. Program

## Davranış

- Süper Admin birden fazla kurum görebiliyorsa sidebar'da kurum seçebilir.
- Kurum Admin sadece yetkili olduğu kurumun programlarını görür; tek kurum varsa seçim pasif görünür.
- Arşivlenmiş/pasif kurum ve programlar aktif çalışma alanı seçicisinde görünmez.
- Kurum değiştirildiğinde sistem otomatik olarak o kuruma ait ilk programa geçer.
- Program bilgi kartında kurum, akreditasyon profili ve rapor yılı birlikte gösterilir.

## Güvenlik

Bu geliştirme yalnızca görünüm değil, mevcut backend tenant izolasyonuyla birlikte çalışır. Kullanıcı frontend'de kurum seçimini görse bile backend yetkisi olmayan programlara erişemez.
