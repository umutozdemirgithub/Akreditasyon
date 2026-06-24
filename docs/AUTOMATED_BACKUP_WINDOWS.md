# Windows Otomatik Yedekleme

Bu sürümde günlük otomatik `medek_data` yedeği için Windows Görev Zamanlayıcı kurulum script'i eklendi.

## Kurulum

Yönetici PowerShell açın:

```powershell
cd C:\Codes\MEDEK\web\ver_128
powershell -ExecutionPolicy Bypass -File tools\install_backup_task.ps1 -RunAt "02:30"
```

Kurulan görev adı:

```text
AKYS-Daily-Backup
```

Yedekler varsayılan olarak şuraya yazılır:

```text
medek_data\backups
```

## Manuel yedek

```powershell
powershell -ExecutionPolicy Bypass -File tools\backup_medek.ps1 -BackupDir medek_data\backups
```

## Son yedeği geri yükleme

Önce stack'i durdurun:

```powershell
docker compose --env-file .env -f docker-compose.web.yml down
```

Sonra:

```powershell
powershell -ExecutionPolicy Bypass -File tools\restore_latest_backup.ps1 -Force
```

Ardından tekrar başlatın:

```powershell
docker compose --env-file .env -f docker-compose.web.yml up -d
```

## Kontrol

```powershell
Get-ScheduledTask -TaskName "AKYS-Daily-Backup"
Get-ChildItem .\medek_data\backups
```
