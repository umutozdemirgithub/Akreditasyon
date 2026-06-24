# Kurum Görünüm Paketlerinin Tüm Çalışma Alanına Uygulanması

v123 ile kurum bazlı görünüm paketi yalnızca sol sidebar üzerinde değil, uygulamanın ana çalışma alanında da etkili olur.

## Kapsam

- Sol sidebar
- Üst başlık/topbar
- Dashboard ve bildirim hero kartları
- KPI kartları
- Form panelleri
- Tab ve alt tab yapıları
- Veri tabloları
- Arama, filtre ve aksiyon butonları
- Mobil/PWA alt navigasyon renkleri

## Tasarım Mantığı

Frontend, backend'den gelen kurum görünüm paketindeki iki ana renk değişkenini kullanır:

```css
--tenant-accent
--tenant-sidebar
```

Bu değişkenlerden yüzey, kenarlık, gölge, tablo başlığı, aktif tab ve buton renkleri türetilir.

## Yönetim

Görünüm paketlerini yalnızca Süper Admin yönetir. Süper Admin'in bir kuruma atadığı görünüm paketi o kurumun tüm kullanıcıları için geçerlidir.
