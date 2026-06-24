# Denetime Hazır Dışa Aktarım ve 429 düzeltmesi

Bu düzeltme iki kullanıcı hatasını kapatır:

1. **Rapor metni boşken çıktı alınamaması**
   - `Denetime Hazır Dışa Aktarım` ekranına `DOCX Hemen İndir` ve `PDF Hemen İndir` butonları geri eklendi.
   - Bu butonlar final çıktı endpointlerini `force=true` ile çağırır; böylece rapor boş veya bloklayıcı eksik olsa bile taslak DOCX/PDF indirilebilir.
   - DOCX/PDF job başlatma da final raporlar için otomatik `force=true` kullanır. Kullanıcı her seferinde engelleyici uyarı/confirm ile durdurulmaz.
   - Job akışı korunur; iş tamamlandığında iş kartındaki `İndir` butonu görünür.

2. **Sık 429 / Çok fazla istek uyarısı**
   - Rate limit sınıflandırması ayrıldı.
   - `/report/preflight`, `/report/jobs` ve job durum okuma çağrıları artık dosya üretim limitiyle değil genel API limitiyle değerlendirilir.
   - Dosya üretimi/indirme ve yedekleme çağrıları hâlâ export limitindedir.
   - Varsayılan limitler intranet kullanımı için artırıldı: genel 300/dk, export 30/dk.
   - Global hata bildirimi kapatılabilir hale getirildi; başarılı işlem mesajı geldiğinde eski hata temizlenir.

Kontrol komutları:

```bash
python -m pytest tests/test_export_download_empty_report_and_rate_limit.py tests/test_role_based_help_manual.py -q
cd frontend && npm ci --no-audit --no-fund && npm run build
```
