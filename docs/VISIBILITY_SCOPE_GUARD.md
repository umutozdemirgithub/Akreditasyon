# Role-Based Visibility Scope Guard

Bu sürümde Bildirim Merkezi, Görev & Eksik Analizi, Kullanım Analitiği, Tam Activity Trail ve Versiyon Karşılaştırma akışları ortak bir backend kapsam katmanına bağlandı.

## Kural

Her kullanıcı yalnızca kendi yetki kapsamındaki kayıtları görür:

- **Süper Admin:** tüm kurumlar, programlar, bildirimler, activity ve versiyon geçmişi.
- **Kurum Admin:** sadece kendi kurumuna bağlı programlar, kullanıcılar, bildirimler ve activity kayıtları.
- **Birim Admin:** sadece kendi fakülte/MYO kapsamındaki programlar ve alt kayıtlar.
- **Onaylayıcı / Denetçi (İzleyici):** program erişimi olan kayıtları salt yetki kapsamında görür.
- **Editör / Hazırlayıcı:** program içinde yalnızca atanmış başlıklar ve kendi işlemleri görünür.

## Teknik Değişiklikler

- `backend/visibility_scope.py` eklendi.
- `section_versions_diff()` artık yalnızca program erişimini değil, başlık/section erişimini de kontrol eder.
- `activity_timeline()` section-aware filtre uygular; editor atanmadığı başlıkların geçmişini göremez.
- `program_insights()` içindeki approval timeline atanmış başlık kapsamına göre filtrelenir.
- `notification_inbox()` ve `mark_notifications_read()` yalnızca görünür bildirimleri işler.
- `list_notification_events_admin()` tenant/faculty/program kapsamına göre filtrelenir.
- `usage_analytics_admin()` tenant/faculty/program kapsamına göre filtrelenir; Birim Admin için de scope-safe çalışır.

## Regresyon Testleri

Yeni test dosyası: `tests/test_visibility_scope_guards.py`

Kapsanan riskler:

1. Editör / Hazırlayıcı atanmadığı başlığın versiyon diff verisini çekemez.
2. Görev & Eksik Analizi approval timeline atanmış başlıklarla sınırlıdır.
3. Bildirim inbox ve okundu işlemi section kapsamını aşamaz.
4. Kurum Admin kullanım analitiği ve admin bildirim listesinde başka kurum programlarını göremez.
