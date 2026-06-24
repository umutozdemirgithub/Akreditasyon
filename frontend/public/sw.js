const CACHE_PREFIX = 'akys-';

self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key.startsWith(CACHE_PREFIX)).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
      .then(() => self.registration.unregister())
      .then(() => self.clients.matchAll({ type: 'window', includeUncontrolled: true }))
      .then((clients) => {
        clients.forEach((client) => {
          if (client && client.url) client.navigate(client.url);
        });
      })
  );
});

self.addEventListener('fetch', () => {
  // v132: Eski PWA önbelleği boş ekran üretebildiği için fetch müdahalesi kapatıldı.
});
