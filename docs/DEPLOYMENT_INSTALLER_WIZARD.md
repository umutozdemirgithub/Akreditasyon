# v110 Deployment / Installer Wizard

Bu modül okul sunucusuna kurulum sırasında en sık hata veren ayarları Admin panelinden kontrol eder.

## Konum

`Ayarlar & Yedek → Kurulum Sihirbazı`

## Kontrol edilen başlıklar

- `MEDEK_API_SECRET` gücü ve placeholder kontrolü
- `MEDEK_APP_BASE_URL`, `MEDEK_CORS_ORIGINS`, `MEDEK_TRUSTED_HOSTS` uyumu
- PostgreSQL / SQLite backend durumu ve canlı DB smoke testi
- `medek_data` ve kanıt klasörü yazma izni
- SMTP yapılandırma durumu
- Ollama/Offline AI bağlantı durumu
- Docker compose ve migration araçlarının paket içinde bulunması
- Export job backend seçimi (`background` veya `rq`)

## Endpointler

```txt
GET  /api/admin/deployment/wizard
POST /api/admin/deployment/smoke
```

Bu endpointler yalnızca Admin rolüyle erişilebilir. Secret ve parola değerleri maskelenir; ham gizli değer dönmez.

## Kullanım önerisi

1. `.env.web.example` dosyasını `.env` olarak kopyalayın.
2. `MEDEK_API_SECRET`, PostgreSQL parolası, `MEDEK_APP_BASE_URL`, CORS ve trusted host değerlerini düzenleyin.
3. Stack'i başlatın.
4. Admin panelinden Kurulum Sihirbazı sekmesine girin.
5. `Smoke Test Çalıştır` ile üretim öncesi temel kontrolleri doğrulayın.

## Not

Sihirbaz `.env` dosyasını doğrudan değiştirmez. Güvenli şekilde kontrol sonucu, önerilen `.env` iskeleti ve kopyalanabilir komut listesi üretir.
