# v100.2 Theme, Sidebar and Dashboard Polish

Bu sürüm, rol/tema senkronizasyon paketinin üzerine kullanıcıyı yormayan daha sade ve premium bir çalışma alanı katmanı ekler.

## Yetki düzeltmeleri

- Program kalıcı silme işlemi artık `program.purge` iznine bağlıdır.
- `deadline.manage` varsayılanı backend davranışıyla uyumlu olarak Süper Admin ve Kurum Admin kapsamına indirildi.
- Görünüm yönetimi menüsü ve `appearance.*` izinleri Süper Admin kapsamına indirildi.

## Tema motoru

- `backend/appearance.py` her görünüm paketi için tam CSS variable seti döndürür.
- Frontend `ThemeContext` üzerinden kurum temasını tüm çalışma alanına uygular.
- Desteklenen ana tokenlar: `--accent`, `--accent-2`, `--sidebar-bg`, `--card-bg`, `--workspace-bg`, `--text-primary`, `--text-secondary`, `--border`, `--success`, `--warning`, `--danger`.

## Sidebar

- Kullanıcı kontrollü daralt/aç davranışı eklendi.
- Ctrl+K hızlı modül araması eklendi.
- Favori modüller yıldız ile sabitlenebilir.
- Program bağlam kartı, rol çipi ve ilerleme bilgisi sadeleştirildi.

## Dashboard

- Hero alanı program adı, rapor yılı, hazırlık ve kalite skorlarını öne çıkarır.
- Hızlı aksiyonlar: rapor paketi oluşturma, kanıt yükleme, onaya gönderme.
- Widget seti: Bugün Ne Yapmalıyım, Öncelikli Başlıklar, Ölçüt Isı Haritası, Aktivite + Termin, Rapor Sağlığı, Kalite Trend.
- Kart hover, skeleton loading ve responsive polish iyileştirildi.

## Doğrulama

- `python tools/validate_project.py`
- `npm run build`
- Seçili regression testleri ve yeni polish regression testleri geçmiştir.
