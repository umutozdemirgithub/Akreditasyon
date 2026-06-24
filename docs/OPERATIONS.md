# Operasyon Notları

## Rate Limiting

Rate limit reverse proxy katmanında uygulanmalıdır. `docs/NGINX_EXAMPLE.md` dosyasında temel `limit_req` örneği vardır.

## Log Rotasyonu

Docker logları için `docker-compose.web.yml` içinde örnek logging bloğu bulunur:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "5"
```

Uygulama içi `activity_log` ve `login_attempts` tabloları düzenli izlenmelidir. Gerekirse arşivleme/budama işi ayrı bakım görevi olarak planlanmalıdır.

## SQLite Sınırı

SQLite tek-node ve düşük/orta eşzamanlılık için uygundur. Yoğun eşzamanlı tablo düzenleme, çok birimli kullanım veya yüksek rapor üretim yükü oluşursa `docs/POSTGRES_MIGRATION_PLAN.md` uygulanmalıdır.

## Üretim Ortamı

1. `.env.web.example` dosyasını `.env` olarak kopyalayın.
2. `MEDEK_API_SECRET` ve `POSTGRES_PASSWORD` değerlerini güçlü, benzersiz değerlerle değiştirin.
3. `MEDEK_CORS_ORIGINS` değerini gerçek intranet adresine göre ayarlayın.
4. Web yığınını başlatın:

```bash
docker compose -f docker-compose.web.yml up --build -d
```

5. Sağlık kontrolü:

```bash
curl http://localhost:8080/api/health
```

## Yedekleme

JSON yedek yalnızca veritabanı kayıtlarını taşır. Tam yedek için `medek_data/` klasörü düzenli ve offline olarak saklanmalıdır. Örnekler `tools/backup_medek.sh`, `tools/backup_medek.ps1` ve `docs/BACKUP_CRON.md` içindedir.


## Rapor job kuyruğu

Varsayılan kurulum `MEDEK_JOB_BACKEND=background` kullanır ve tek API container için yeterlidir. Çoklu instance veya yoğun export yükü için Redis + RQ overlay'i kullanılmalıdır:

```powershell
docker compose --env-file .env -f docker-compose.web.yml -f docker-compose.queue.yml up --build -d
```

Detaylı operasyon notları: `docs/JOB_QUEUE.md`.
