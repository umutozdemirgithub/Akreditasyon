# SECURITY.md

## Üretim Güvenlik Politikası

Bu kurulumda aşağıdaki kontroller zorunlu kabul edilir:

- `MEDEK_API_SECRET` en az 48 karakter olmalı ve örnek/placeholder değer içermemelidir.
- `MEDEK_CORS_ORIGINS` yalnızca gerçek intranet/web adreslerini içermelidir; production ortamında `*` kullanılmaz.
- İlk admin şifresi `MEDEK_BOOTSTRAP_ADMIN_PASSWORD` veya geriye uyumluluk için `MEDEK_ADMIN_PASSWORD` ile verilir.
- Production ortamında `admin`, `admin123`, `password` gibi örnek şifreler reddedilir.
- Kullanıcı pasif hale getirilirse veya şifresi değiştirilirse `token_version` artırılır ve eski oturumlar geçersiz olur.
- Login denemeleri kilitleme mekanizmasına tabidir.
- API istekleri per-process rate limit middleware ile sınırlandırılır. Çoklu API replica senaryosunda Redis/Nginx tabanlı merkezi rate limit önerilir.

## Önerilen Minimum `.env`

```env
MEDEK_ENV=production
MEDEK_API_SECRET=CHANGE_ME_64_CHAR_RANDOM_SECRET
MEDEK_BOOTSTRAP_ADMIN_PASSWORD=CHANGE_ME_StrongAdmin_2026!
MEDEK_API_TOKEN_TTL_MINUTES=480
MEDEK_WEB_PORT=8080
MEDEK_CORS_ORIGINS=http://localhost:8080,http://192.168.1.20:8080
MEDEK_TRUSTED_HOSTS=localhost,127.0.0.1,api,web,192.168.1.20
MEDEK_LOGIN_MAX_FAILED_ATTEMPTS=5
MEDEK_LOGIN_LOCK_MINUTES=15
MEDEK_RATE_LIMIT_ENABLED=1
```

## Parola Politikası

Yeni/yenilenen kullanıcı şifreleri şu kurallara uymalıdır:

- En az 10 karakter
- En az 1 büyük harf
- En az 1 küçük harf
- En az 1 rakam
- En az 1 özel karakter
- `admin123`, `password`, `change_me` gibi örnek/zayıf değerler yasak

## Rate Limit Varsayılanları

- Login: IP başına dakikada 5 deneme
- Kanıt yükleme: kullanıcı/IP başına dakikada 20 istek
- Rapor/backup export: kullanıcı/IP başına dakikada 5 istek
- Genel API: kullanıcı/IP başına dakikada 120 istek

## Olay Kaydı

Sistem activity log ve login attempts tablolarını kullanır. Kritik işlemlerde `actor`, `program_id`, `action`, `detail`, `ts` alanları kaydedilir.
