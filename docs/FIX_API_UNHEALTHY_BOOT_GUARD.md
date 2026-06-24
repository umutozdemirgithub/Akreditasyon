# API unhealthy boot guard

Bu düzeltme, Desktop/Akreditasyon veri klasörüne geçişten sonra yeni PostgreSQL dizini oluştuğunda API'nin ilk admin üretimi için gerekli gizli değerler eksikse `akys-api` container'ının kapanmasını önler.

## Değişiklikler

- `tools/start_web_stack.ps1` ve `tools/start_web_stack.sh` artık eksik veya placeholder değerleri otomatik tamamlar:
  - `MEDEK_API_SECRET`
  - `MEDEK_BOOTSTRAP_ADMIN_PASSWORD`
  - `POSTGRES_PASSWORD`
  - PostgreSQL varsayılanları
  - Rate limit varsayılanları
- İlk admin şifresi otomatik üretildiyse terminalde yalnızca ilk kurulum anında gösterilir.
- `docker-compose.web.yml` API healthcheck bekleme süresi artırıldı.
- Rate limit varsayılanları güncellendi:
  - Genel API: 300/dk
  - Export/indirme: 30/dk
- `tools/diagnose_stack.ps1` ve `tools/diagnose_stack.sh` eklendi.

## Kullanım

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\start_web_stack.ps1
```

Sorun devam ederse:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\diagnose_stack.ps1
```
