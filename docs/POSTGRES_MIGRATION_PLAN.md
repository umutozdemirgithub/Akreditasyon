# PostgreSQL Geçiş Planı

Bu sürüm PostgreSQL için **prova/aktarım araçlarını** içerir. Uygulamanın varsayılan canlı runtime veritabanı hâlâ SQLite'tır; güvenli kesintisiz geçiş için önce bu migrasyon provasını tamamlayın.

## 1. PostgreSQL servis profilini başlat

```powershell
docker compose --env-file .env -f docker-compose.web.yml --profile postgres-rehearsal up -d postgres
```

## 2. SQLite hazırlık raporu

```powershell
python tools/postgres_readiness.py
```

Bu komut tablo listesini, satır sayılarını ve eksik çekirdek tabloları raporlar.

## 3. PostgreSQL şemasını ve veriyi aktar

Önce `.env` içinde güçlü bir bağlantı tanımlayın:

```env
POSTGRES_DSN=postgresql://medek:GUCLU_SIFRE@localhost:5432/medek
```

Aktarım:

```powershell
python tools/postgres_migrate.py --dsn $env:POSTGRES_DSN --clear
```

Linux/macOS:

```bash
python tools/postgres_migrate.py --dsn "$POSTGRES_DSN" --clear
```

## 4. Satır sayısı karşılaştırması

`postgres_migrate.py` komutu SQLite kaynak satır sayılarını ve PostgreSQL'e kopyalanan satırları yazar. Kritik tablolar:

- `users`
- `programs`
- `program_users`
- `sections`
- `evidence`
- `evidence_links`
- `data_tables`
- `export_history`
- `export_jobs`

## 5. Kesim öncesi önerilen süreç

1. Kullanıcı erişimini durdurun.
2. Docker stack'i durdurun.
3. `medek_data` tam yedeği alın.
4. PostgreSQL migrasyonunu `--clear` ile tekrar çalıştırın.
5. Satır sayısı ve örnek kayıtları kontrol edin.
6. PostgreSQL runtime adaptörü tamamlandığında `DATABASE_URL` ile API'yi PostgreSQL'e alın.

## Not

Bu pakette PostgreSQL şeması ve veri aktarım aracı üretim kesimi için hazırlandı. API'nin tüm repository katmanının PostgreSQL runtime'da çalışması için SQLite'e özgü `INSERT OR REPLACE`, `INSERT OR IGNORE` ve `PRAGMA` kullanımlarının kalıcı SQL dialect adaptasyonuyla tamamlanması gerekir. Bu nedenle canlı kurulumda varsayılan veritabanı SQLite kalır; PostgreSQL'e geçiş kontrollü cutover fazıdır.
