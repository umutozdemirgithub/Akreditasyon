# DEPLOYMENT_CHECKLIST.md

## 1. Sunucu Hazırlığı

- Docker Desktop veya Docker Engine çalışıyor.
- Proje klasörü: `C:\Codes\MEDEK\web\ver_128` veya okul sunucusunda eşdeğeri.
- `medek_data` klasörü düzenli yedeklenecek bir diskte tutuluyor.

## 2. `.env` Kontrolü

`.env` dosyası proje kökünde olmalı:

```powershell
dir -Force
```

Listede `.env` görünmeli, `.env.txt` olmamalıdır.

Zorunlu production değerleri:

```env
MEDEK_ENV=production
MEDEK_API_SECRET=CHANGE_ME_64_CHAR_RANDOM_SECRET
MEDEK_BOOTSTRAP_ADMIN_PASSWORD=CHANGE_ME_StrongAdmin_2026!
MEDEK_WEB_PORT=8080
MEDEK_CORS_ORIGINS=http://localhost:8080
MEDEK_TRUSTED_HOSTS=localhost,127.0.0.1,api,web
```

Secret üretmek için PowerShell:

```powershell
[System.Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }))
```

## 3. Compose Config Kontrolü

```powershell
cd C:\Codes\MEDEK\web\ver_128
docker compose --env-file .env -f docker-compose.web.yml config
```

Bu komut hata vermemelidir.

## 4. Başlatma

```powershell
docker compose --env-file .env -f docker-compose.web.yml up -d --build web
```

## 5. Durum Kontrolü

```powershell
docker compose --env-file .env -f docker-compose.web.yml ps
docker compose --env-file .env -f docker-compose.web.yml logs -f api
```

Tarayıcı:

```text
http://localhost:8080
```

## 6. İlk Giriş Sonrası

- Admin şifresini güçlü bir değerle değiştir.
- Gerekli kullanıcıları oluştur.
- Her kullanıcıyı doğru programa/bölüme ata.
- Yedekleme scriptini zamanla.

## 7. Pilot Test

- Login/logout
- Program oluşturma
- Kullanıcı yetkisi
- Kanıt yükleme/indirme
- Tablo ekleme
- DOCX/PDF export
- Backup JSON
- Restore dry-run manuel kontrolü

## Sistem Şablonları Koruması

MEDEK/MÜDEK ve diğer akreditasyon profillerinin ana ölçüt iskeletleri `backend/templates/*.json` dosyalarıyla korunur. Uygulama açılışında `system_templates` tablosu otomatik seed edilir. Ayrıntı: `docs/SYSTEM_TEMPLATES.md`.

