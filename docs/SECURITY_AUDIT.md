# AKYS Web Güvenlik Notları

## Uygulanan Kontroller

- Token imzalama için `MEDEK_API_SECRET` kullanılır.
- Üretim compose dosyası `MEDEK_API_SECRET` değerini zorunlu ister.
- Kanıt yüklemede uzantı, boyut ve temel dosya imzası doğrulanır.
- Dosya indirme path'i `medek_data/kanitlar` altında doğrulanır.
- Bölüm atanmış Editör / Hazırlayıcı kullanıcılar kanıt/tablo arşivinde yalnızca erişilebilir başlık kapsamını görür.
- Kanıt bağlama endpoint'i kod/not bilgisini korur.
- Tablo bağlama akışı API endpoint'i üzerinden kopyalama yapar.
- JSON yedek indirme, JSON geri yükleme ve sistem durumu Admin rolüyle sınırlandırılmıştır.

## Kalan Riskler

- Dosya imza kontrolü malware taraması değildir.
- SQLite yüksek eşzamanlı yazma için uzun vadeli çözüm değildir.
- LocalStorage tabanlı token saklama XSS riskine hassastır; yeni dinamik HTML eklenirken React'in güvenli render yaklaşımı korunmalıdır.
- İntranet dışı yayınlarda HTTPS, IP allowlist/VPN ve ek rate limit zorunlu kabul edilmelidir.

## Üretim Kontrol Listesi

1. `.env` dosyasında güçlü `MEDEK_API_SECRET` belirle.
2. `MEDEK_CORS_ORIGINS` değerini gerçek adreslerle sınırla.
3. `docker compose -f docker-compose.web.yml config` ile yapılandırmayı kontrol et.
4. `docker compose -f docker-compose.web.yml up --build -d` ile başlat.
5. `http://localhost:8080/api/health` endpoint'ini kontrol et.
6. `medek_data/` klasörü için düzenli offline yedek al.
7. İlk admin girişinden sonra gereksiz kullanıcıları pasifleştir.
