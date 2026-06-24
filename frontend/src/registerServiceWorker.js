const PWA_ENABLED = import.meta.env.VITE_ENABLE_PWA === "true";

async function unregisterExistingServiceWorkers() {
  if (!("serviceWorker" in navigator)) return;
  try {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map((registration) => registration.unregister()));
  } catch {
    // PWA temizliği opsiyoneldir; giriş ekranını engellememelidir.
  }
}

export function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return;

  window.addEventListener("load", () => {
    if (!PWA_ENABLED) {
      unregisterExistingServiceWorkers();
      clearMedekCaches();
      return;
    }

    navigator.serviceWorker
      .register("/sw.js", { updateViaCache: "none" })
      .then((registration) => {
        registration.addEventListener("updatefound", () => {
          window.dispatchEvent(new CustomEvent("medek-sw-update"));
        });
      })
      .catch(() => {
        // Service worker kayıt hatası uygulamayı veya giriş ekranını engellememelidir.
      });
  });
}

export async function clearMedekCaches() {
  if (!("caches" in window)) return;
  try {
    const keys = await caches.keys();
    await Promise.all(keys.filter((key) => key.startsWith("akys-")).map((key) => caches.delete(key)));
  } catch {
    // Cache temizliği yardımcı işlemdir.
  }
}
