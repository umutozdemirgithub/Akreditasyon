# Mobile PWA Pro Mode

Bu sürümde PWA deneyimi geliştirildi:

- Offline fallback sayfası eklendi.
- Service worker cache versiyonlaması eklendi.
- API istekleri çevrimdışıyken kontrollü `503` yanıtı döndürür.
- Kurulum istemi yakalanır ve kullanıcıya uygulama gibi kurma bildirimi gösterilir.
- Yeni service worker bulunduğunda kullanıcıya yenileme bildirimi gösterilir.
- Offline durumda üst bantta read-only uyarısı görünür.

İlk aşamada çevrimdışı düzenleme değil, güvenli **offline read-only** yaklaşımı uygulanır.
