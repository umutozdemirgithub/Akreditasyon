# AKYS Web Risk Register

## 1. SQLite Ölçek Sınırı

SQLite tek-node kurum içi kullanım için uygundur. Yoğun eşzamanlı yazma, birden fazla birimde aktif kullanım veya yüksek rapor üretim yükü oluşursa PostgreSQL geçiş provası uygulanmalıdır.

**Azaltım:** `tools/postgres_readiness.py`, `tools/postgres_export.py` ve `docs/POSTGRES_MIGRATION_PLAN.md` ile geçiş hazırlığı sürdürülür.

## 2. Kanıt Dosyaları

Dosya uzantısı, boyutu ve temel imza kontrolü yapılır; bu antivirüs taraması değildir.

**Azaltım:** Kurum dışına açılan senaryolarda reverse proxy, antivirüs veya object storage taraması eklenmelidir.

## 3. Yerel AI Taslak Servisi

Mevcut taslak üretimi yerel kural tabanlıdır ve harici LLM API çağrısı yapmaz.

**Azaltım:** Harici LLM entegrasyonu eklenirse API anahtarları secret manager üzerinden yönetilmeli, tenant/program ayrımı korunmalı, hassas veri maskeleme ve audit log zorunlu olmalıdır.

## 4. Yetki Kapsamı

Bölüm atanmış kullanıcıların arşiv ve rapor verilerini kendi kapsamlarıyla görmesi gerekir.

**Azaltım:** Kanıt ve tablo listeleme endpoint'leri bölüm erişim kontrolü uygular; hassas yedek ve sistem endpoint'leri Admin rolüyle sınırlandırılır.

## 5. Mobil Kullanılabilirlik

Web arayüzü responsive tasarlanmıştır; yine de gerçek cihaz kabul testi gerekir.

**Test matrisi:** iPhone Safari/Chrome, Android Chrome, 1366x768 dizüstü, geniş ekran tarayıcı, tablo düzenleme ve dosya yükleme akışları.
