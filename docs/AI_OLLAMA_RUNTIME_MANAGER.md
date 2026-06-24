# AI / Ollama Runtime Manager

Bu sürümde **Ayarlar & Yedek → AI / Ollama Testi** paneli yalnızca bağlantı testi yapan pasif bir ekran olmaktan çıkarıldı.

## Eklenen yönetim işlevleri

- AI / Ollama etkinleştir / devre dışı bırak
- Ollama provider, base URL, model ve timeout değerlerini veritabanında sakla
- Yüklü Ollama modellerini listele
- Seçili modeli Ollama API üzerinden yükle / doğrula
- Seçili model yüklü değilse fallback durumunu açıkça göster
- Kurulum Sihirbazı uyarı metnini bu yeni yönetim akışına yönlendir

## Notlar

- AI kapalıyken sistem yerel şablon üreticiyle devam eder.
- Model yükleme işlemi Ollama servisinin erişilebilir olmasını gerektirir.
- Büyük modellerin yüklenmesi birkaç dakika sürebilir.
- Ayarlar `.env` yerine `settings` tablosunda tutulduğu için yeniden image build almadan değiştirilebilir.
