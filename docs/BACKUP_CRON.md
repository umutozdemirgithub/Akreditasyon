# MEDEK Backup Cron Örneği

JSON yedeği tek başına yeterli değildir; `medek_data/kanitlar/` klasörü ve SQLite veritabanı birlikte saklanmalıdır.

## Önerilen günlük arşiv scripti

```bash
#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/medek"
BACKUP_DIR="/var/backups/medek"
STAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"
cd "$APP_DIR"

tar -czf "$BACKUP_DIR/medek_full_$STAMP.tar.gz" \
  medek_data/medek_kys_v7_9.sqlite3 \
  medek_data/kanitlar \
  medek_data/backups

find "$BACKUP_DIR" -name 'medek_full_*.tar.gz' -mtime +30 -delete
```

## Cron kaydı

Her gece 02:30:

```cron
30 2 * * * /opt/medek/tools/backup_medek.sh >> /var/log/medek_backup.log 2>&1
```

## Restore kontrol listesi

1. Uygulamayı durdurun.
2. Mevcut `medek_data` klasörünün ayrıca kopyasını alın.
3. Arşivden SQLite dosyasını, `kanitlar/` ve `backups/` klasörlerini birlikte geri yükleyin.
4. Uygulamayı başlatın.
5. Yönetim ekranında DB sağlık kontrolünü inceleyin.

## Windows Task Scheduler

Windows sunucuda otomatik görev kurmak için:

```powershell
powershell -ExecutionPolicy Bypass -File tools\install_backup_task.ps1 -RunAt "02:30"
```

Ayrıntı: `docs/AUTOMATED_BACKUP_WINDOWS.md`.
