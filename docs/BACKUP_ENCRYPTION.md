# Şifreli Yedekleme

Bu sürümde JSON/SQLite yedekleri için PowerShell tabanlı AES-256 şifreleme yardımcıları eklendi.

## Şifreleme

```powershell
powershell -ExecutionPolicy Bypass -File tools\encrypt_backup.ps1 -InputPath medek_data\backups\backup_latest.zip -Passphrase "CokGucluYedekParolasi"
```

## Çözme

```powershell
powershell -ExecutionPolicy Bypass -File tools\decrypt_backup.ps1 -InputPath medek_data\backups\backup_latest.zip.enc -Passphrase "CokGucluYedekParolasi"
```

Parolayı `.env`, GitHub veya zip paket içine koymayın. Kurum içinde parola saklama prosedürü oluşturun.
