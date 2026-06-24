# v107 Mobile PWA Pro

Bu sürüm AKYS arayüzünü mobil cihazlarda sahada kullanılabilir hale getiren PWA iyileştirmelerini içerir.

## Eklenenler

- Rol bazlı mobil alt gezinme çubuğu.
- Editör / Hazırlayıcı, Onaylayıcı, Admin ve Denetçi (İzleyici) için farklı hızlı menü öncelikleri.
- Kamera ile kanıt yükleme (`capture="environment"`).
- Kanıt arşivi ve başlık içi kanıt panelinde mobil dosya/kamera akışı.
- Çevrimdışı modda güvenli salt-okunur davranış.
- Service worker içinde GET API yanıtları için network-first/offline-cache davranışı.
- PWA manifest kısayolları: Dashboard, Rapor Dizini, Kanıt Yükle, Bildirimler.
- Mobilde sticky topbar, touch-friendly tablar, bottom safe-area desteği.

## Güvenlik kararı

Çevrimdışı modda yazma işlemleri kapalıdır:

- bölüm kaydetme,
- kanıt yükleme,
- tablo düzenleme,
- onay/revizyon,
- export.

Bunun sebebi akreditasyon verilerinde çakışma ve veri bütünlüğü riskini azaltmaktır. Offline mod ilk aşamada `read-only` olarak tasarlanmıştır.

## Kullanım

Mobil tarayıcıdan uygulamayı açın ve tarayıcının “Ana ekrana ekle / Uygulama olarak kur” seçeneğini kullanın. Destekleyen tarayıcılarda uygulama içinden kurulum bildirimi de gösterilir.

## Teknik notlar

- Bottom navigation CSS ile sadece mobil/tablet veya coarse pointer cihazlarda görünür.
- API GET önbelleği sadece JSON okuma endpointleri için kullanılır.
- Event stream, dosya indirme ve DOCX/PDF çıktıları önbelleğe alınmaz.
