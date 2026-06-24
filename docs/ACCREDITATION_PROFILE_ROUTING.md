# Akreditasyon Profili Otomatik Eşleştirme

Bu sürümde program oluşturma ve akademik katalog içe aktarma akışına derece + program adına dayalı akreditasyon kuruluşu eşleştirme motoru eklendi.

## Ana kural

1. Derece `Önlisans` ise varsayılan kuruluş `MEDEK` olur.
2. Derece `Lisans` veya `Lisansüstü` ise önce program adı taranır.
3. Birden fazla aday çıktığında daha özel program eşleşmesi genel fakülte/alan eşleşmesine göre önceliklidir.
4. Eşleşme bulunamazsa birim/fakülte adına göre ikinci seviye tahmin yapılır; yine bulunamazsa güvenli varsayılan `MEDEK` olur.

## Program adı kuralları

| Program adı içerir | Varsayılan profil |
|---|---|
| Mühendisliği | MÜDEK |
| Tıp | TEPDAD |
| Diş Hekimliği | DEPAD |
| Eczacılık | ECZAKDER |
| Hemşirelik | HEPDAK |
| Ebelik | EPDAK |
| Fizyoterapi | FTR-AD |
| Sağlık Yönetimi | SAYAK |
| Mimarlık | MİAK |
| Peyzaj Mimarlığı | PEMDER |
| Veteriner | VEDEK |
| Ziraat | ZİDEK |
| Turizm / Gastronomi | TURAK |
| İletişim / Gazetecilik / Radyo / Yeni Medya | İLAD |
| İlahiyat / İslami İlimler | AA / İAA |
| Psikoloji | TPD |
| PDR / Rehberlik ve Psikolojik Danışmanlık | PDR-DER |
| Öğretmenliği | EPDAD |
| Matematik / Fizik / Kimya / Biyoloji / Tarih / Edebiyat | FEDEK |
| Sosyal Hizmet / Sosyoloji / İşletme / İktisat / Kamu Yönetimi vb. | STAR |

## Dosyalar

- `backend/accreditation.py`: profil kataloğu, alias listesi, eşleştirme motoru ve şablon üretimi.
- `backend/academic_importer.py`: YÖK Atlas/katalog içe aktarma sırasında yeni eşleştirme motorunu kullanır.
- `backend/repositories.py`: program oluştururken profil boş/otomatik bırakılırsa derece + program adına göre tahmin eder.
- `frontend/src/constants/appConstants.js`: frontend tarafında anlık profil önerisi üretir.
- `backend/templates/*.json`: eksik akreditasyon profilleri için sistem içi ÖDR iskeletleri.

## Şablon notu

Şablon JSON dosyaları sistem içi iskelet, rehber soru, beklenen kanıt ve tablo önerisi sağlamak için hazırlanmıştır. Akreditasyon başvurusu öncesinde ilgili kuruluşun resmi Word/PDF şablonu ile son kontrol yapılmalıdır. Resmi kuruluşlar zaman zaman ölçüt, sürüm ve başlık güncellemesi yapabilir.
