# HTTPS ve Kurum İçi Ağ Yayını

Bu dosya, çalışan `docker-compose.web.yml` yığınının önüne isteğe bağlı Caddy reverse proxy koymak içindir.

## Nginx mi Caddy mi?

İkisi aynı görevi yapmaz:

- `frontend/nginx.conf` varsayılan web container içindedir; React statik dosyalarını servis eder ve `/api` isteklerini `api:8000` adresine yollar. Lokal/pilot kullanım için yeterlidir.
- `Caddyfile` opsiyonel dış reverse proxy katmanıdır; kurum içi alan adı ve HTTPS/TLS gerekiyorsa Nginx'in önünde çalışır.

Varsayılan tercih: `docker-compose.web.yml`.
HTTPS/domain gerekiyorsa: `docker-compose.web.yml` + `docker-compose.https.yml`.

## Yerel HTTPS / kurum alan adı

`.env` içine kurum alan adını veya intranet DNS adını ekleyin:

```env
MEDEK_DOMAIN=medek.okul.local
MEDEK_HTTP_PORT=80
MEDEK_HTTPS_PORT=443
MEDEK_CORS_ORIGINS=https://medek.okul.local
MEDEK_TRUSTED_HOSTS=medek.okul.local,localhost,127.0.0.1,api,web
```

Başlatma:

```powershell
docker compose --env-file .env -f docker-compose.web.yml -f docker-compose.https.yml up --build -d
```

Caddy, gerçek bir public DNS ve 80/443 erişimi varsa otomatik sertifika almaya çalışır. Sadece kurum içi `.local` adlarda genellikle kurum CA veya DNS/TLS politikası gerekir.

## Windows güvenlik duvarı

Yönetici PowerShell:

```powershell
New-NetFirewallRule -DisplayName "AKYS HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
New-NetFirewallRule -DisplayName "AKYS HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
New-NetFirewallRule -DisplayName "AKYS 8080" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
```

## Sabit IP önerisi

Kurum içi kullanımda sunucu bilgisayar için sabit IP veya DHCP reservation kullanın. Kullanıcılar şu biçimde erişir:

```text
https://medek.okul.local
```

veya geçici testte:

```text
http://SUNUCU_IP:8080
```

## Kontrol

```powershell
docker compose --env-file .env -f docker-compose.web.yml -f docker-compose.https.yml ps
docker logs --tail 80 akys-caddy
```
