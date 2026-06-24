# v101 Live Enterprise Control

Bu sürüm, kurumsal kullanımda canlı durum hissini ve admin operasyonlarını güçlendirir.

## Eklenenler

- `/api/ai/status`: Admin için global Ollama/offline AI durum testi.
- `/api/programs/{program_id}/events/stream`: Program bazlı SSE canlı olay akışı.
- Rapor dışa aktarma ekranında kuyruk/progress kartları.
- Bildirim merkezi ve üst bar unread badge güncellemesi.
- Granular Permission UI için rol odağı ve arama filtresi.
- Soft-delete arşivinde program, kanıt, tablo, başlık ve program kullanıcı kayıtları.
- `backend.enterprise.facade`: modüler enterprise yüzeyi.

## SSE davranışı

Frontend `EventSource` ile canlı akışa bağlanır. Tarayıcı veya proxy SSE bağlantısını keserse mevcut polling fallback korunur.

## Export progress

Job kayıtları `export_jobs.progress`, `status`, `message` ve `error` alanlarından beslenir. RQ veya FastAPI BackgroundTasks backend'iyle çalışır.

## Güvenlik

SSE bağlantısı önce `/api/programs/{program_id}/events/session` ile kısa ömürlü HttpOnly stream cookie alır; EventSource ana API token'ını URL query string içinde taşımaz. Stream token program kapsamına ve token version değerine bağlıdır. Hassas SMTP/AI şifreleri SSE payload içinde gönderilmez.
