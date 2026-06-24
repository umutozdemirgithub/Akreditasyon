# Offline AI Draft / Ollama

Bu sürümde AI taslak üretimi sağlayıcı tabanlı hale getirildi. Varsayılan olarak kapalıdır ve kapalıyken sistem yerel şablon tabanlı güvenli taslak üreticiyle çalışır.

## Etkinleştirme

`.env` dosyasına şunları ekleyin:

```env
MEDEK_AI_ENABLED=true
MEDEK_AI_PROVIDER=ollama
MEDEK_OLLAMA_BASE_URL=http://localhost:11434
MEDEK_OLLAMA_MODEL=llama3.1
MEDEK_OLLAMA_TIMEOUT=45
```

Ardından Ollama üzerinde modeli hazır edin:

```bash
ollama pull llama3.1
ollama serve
```

## Güvenlik davranışı

- AI çıktısı otomatik olarak rapora kaydedilmez.
- Kullanıcı önce taslağı inceler, sonra isterse metin alanına aktarır.
- Ollama erişilemezse sistem hata ile kapanmaz; yerel şablon üreticiye düşer.
- Başlık bazlı editör politikasında `AI taslak üretir` izni kapalıysa ilgili rol AI taslak alamaz.

## Endpointler

- `GET /api/programs/{program_id}/ai/status`
- `POST /api/programs/{program_id}/ai/sections/{section_key}/draft`
