# AKYS Web Mimarisi

Bu paket AKYS için web tabanlı intranet mimarisini içerir.

## Bileşenler

- Backend: FastAPI
- Frontend: React + Vite
- Proxy/statik yayın: Nginx
- Veri katmanı: SQLite, PostgreSQL geçiş provası için ek araçlar
- Dosyalar: `medek_data/kanitlar`

## Çalışan İş Akışları

- Kimlik doğrulama ve token tabanlı oturum
- Program listesi ve dashboard
- Başlık okuma/yazma, PUKÖ ve not alanları
- Kanıt yükleme, bağlama, indirme ve silme
- Tablo oluşturma, başlığa bağlama, kaydetme ve silme
- Kontrol tablosu, hazırlık denetimi ve nihai DOCX/PDF raporları
- Termin planı, toplu durum güncelleme, arama ve istatistikler
- JSON yedek indirme/geri yükleme
- Yerel kural tabanlı MEDEK taslak üretimi

## Docker ile Çalıştırma

```bash
cp .env.web.example .env
docker compose -f docker-compose.web.yml up --build -d
```

Tarayıcı:

```text
http://SUNUCU_IP:8080
```

## Yerel Geliştirme

```bash
pip install -r requirements-dev.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
cd frontend
npm ci
VITE_API_BASE_URL=http://localhost:8000/api npm run dev
```
