# AKYS School Server Setup

Bu belge okul ici sunucu kurulumuna gecmeden once ve kurulum sirasinda izlenecek pratik kontrol listesidir.

## 1. Sunucu Bilgileri

Kurulumdan once su bilgiler netlesmeli:

- Sunucu isletim sistemi: Windows Server veya Linux
- Sunucu IP adresi
- Kullanilacak intranet adresi: ornek `medek.okul.local`
- Uygulama portu: varsayilan `8080`
- HTTPS kullanilacaksa sertifika kaynagi
- Yedeklerin alinacagi klasor veya NAS yolu
- PDF uretimi icin LibreOffice kullanimi

## 2. Gerekli Yazilimlar

- Docker Engine
- Docker Compose v2
- Git veya zip dosyasi ile manuel aktarim
- Linux icin `bash`
- Windows icin PowerShell 5+ veya PowerShell 7+

API container icinde LibreOffice kurulacak sekilde hazirlandi. Bu nedenle PDF uretimi icin ayrica host makineye Office kurmak zorunlu degildir.

## 3. Paket Hazirlama

Kodlar sunucuya kopyalandiktan sonra proje kokunde su dosyalar olmalidir:

- `docker-compose.web.yml`
- `Dockerfile.api`
- `frontend/Dockerfile`
- `.env`
- `medek_data/`

`.env` dosyasi icin:

```bash
cp .env.web.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.web.example .env
```

Sonra `.env` icindeki secret ve adresleri duzenleyin.

## 4. Kurulum Oncesi Kontrol

Linux:

```bash
bash tools/school_preflight.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File tools/school_preflight.ps1
```

## 5. Web Stack Baslatma

Linux:

```bash
bash tools/start_web_stack.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File tools/start_web_stack.ps1
```

Manuel komut:

```bash
docker compose --env-file .env -f docker-compose.web.yml up --build -d
```

## 6. Ilk Kontrol

Tarayici:

```text
http://SUNUCU_IP:8080
```

API health:

```text
http://SUNUCU_IP:8080/api/health
```

## 7. Yedekleme

SQLite ve kanit dosyalari `medek_data/` altindadir. Kurulumdan sonra bu klasor duzenli yedeklenmelidir.

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File tools/backup_medek.ps1
```

Linux:

```bash
bash tools/backup_medek.sh
```

## 8. Kurulumdan Sonra Yapilacaklar

- Varsayilan admin sifresini degistirin.
- Okul ici DNS kaydi yapin.
- HTTPS icin kurum sertifikasi veya reverse proxy ayarlayin.
- Yedekleme gorevini zamanlayin.
- Bir test kullanicisi ile login, kanit yukleme, DOCX export ve PDF export deneyin.
