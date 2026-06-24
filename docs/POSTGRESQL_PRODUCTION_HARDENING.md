# v109 PostgreSQL Production Hardening

Bu sürümde AKYS web stack üretim kullanımında PostgreSQL'i birinci sınıf veritabanı backend'i olarak kullanabilir hale getirildi.

## Ne değişti?

- `MEDEK_DB_BACKEND=postgresql` desteği eklendi.
- `MEDEK_DATABASE_URL` / `POSTGRES_DSN` ile PostgreSQL bağlantısı yapılabiliyor.
- Mevcut SQLite tarzı repository SQL'leri için PostgreSQL uyumluluk katmanı eklendi:
  - `?` placeholder → `%s`
  - `INSERT OR IGNORE` → `ON CONFLICT DO NOTHING`
  - `INSERT OR REPLACE` → `ON CONFLICT(...) DO UPDATE`
  - `PRAGMA table_info(...)` → `information_schema.columns`
- Docker Compose artık varsayılan olarak PostgreSQL servisiyle çalışır.
- Tenant-aware indeksler eklendi.
- SQLite → PostgreSQL geçiş araçları güncellendi.
- Cutover sonrası şema / indeks / satır sayısı kontrol aracı eklendi.

## Üretim .env örneği

```env
MEDEK_DB_BACKEND=postgresql
POSTGRES_DB=medek
POSTGRES_USER=medek
POSTGRES_PASSWORD=COK_GUCLU_POSTGRES_SIFRESI
MEDEK_DATABASE_URL=
```

## İlk kurulum

```bash
docker compose -f docker-compose.web.yml up --build -d
```

PostgreSQL container ilk açılışta `tools/postgres_schema.sql` dosyasını çalıştırır. API açılırken de `backend/db.py` içindeki idempotent şema ve indeks kontrollerini yeniden uygular.

## Mevcut SQLite verisini PostgreSQL'e taşıma

Önce sistemi durdurup yedek alın:

```bash
docker compose -f docker-compose.web.yml down
cp medek_data/medek_kys_v7_9.sqlite3 medek_data/medek_kys_v7_9.sqlite3.bak
```

PostgreSQL'i başlatın:

```bash
docker compose -f docker-compose.web.yml up -d postgres
```

Migrasyonu çalıştırın:

```bash
python tools/postgres_migrate.py \
  --sqlite medek_data/medek_kys_v7_9.sqlite3 \
  --dsn "postgresql://medek:COK_GUCLU_POSTGRES_SIFRESI@localhost:5432/medek" \
  --clear
```

Cutover kontrolü:

```bash
python tools/postgres_cutover_check.py \
  --sqlite medek_data/medek_kys_v7_9.sqlite3 \
  --dsn "postgresql://medek:COK_GUCLU_POSTGRES_SIFRESI@localhost:5432/medek" \
  --strict-counts
```

Sonra `.env` içinde PostgreSQL backend'i açık olmalı:

```env
MEDEK_DB_BACKEND=postgresql
MEDEK_DATABASE_URL=
```

Ardından stack'i başlatın:

```bash
docker compose -f docker-compose.web.yml up --build -d
```

## SQLite rollback

Acil geri dönüş için `.env` içinde:

```env
MEDEK_DB_BACKEND=sqlite
MEDEK_SQLITE_PATH=/app/medek_data/medek_kys_v7_9.sqlite3
```

Sonra:

```bash
docker compose -f docker-compose.web.yml up --build -d
```

PostgreSQL verisi silinmez; sadece API tekrar SQLite'a döner.

## Üretim notları

- `POSTGRES_PASSWORD` placeholder kalmamalı.
- PostgreSQL volume'u ayrıca yedeklenmeli: `medek_pg_data`.
- Kanıt dosyaları yine `medek_data/kanitlar` altında tutulur; veritabanı yedeği tek başına dosya kanıtlarını içermez.
- Çok kullanıcılı kurum kurulumunda `MEDEK_JOB_BACKEND=rq` ve `docker-compose.queue.yml` önerilir.
