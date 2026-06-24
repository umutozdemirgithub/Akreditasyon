# E-posta Bildirimleri

Bu sürümde roller arası iş akışı olayları için SMTP tabanlı bildirim sistemi vardır. Varsayılan olarak kapalıdır; SMTP ayarları yapılmadan hiçbir e-posta gönderilmez.

## Bildirim verilen olaylar

Onaya gönderme, revizyon, onay ve son teslim tarihi gibi kritik olaylar bildirim üretir.

| Olay | Alıcılar |
|---|---|
| Başlık onaya gönderildi | Onaylayıcılar + Adminler |
| Başlık onaylandı | Son gönderen kullanıcı + Adminler |
| Revizyon istendi | Son gönderen kullanıcı + ilgili editörler + Adminler |
| Onay geri alındı | Son gönderen kullanıcı + Adminler |
| Son teslim tarihi planı güncellendi | Program kullanıcıları + Adminler |
| Program yetkisi/rolü atandı | İlgili kullanıcı |
| Kullanıcı hesabı güncellendi | İlgili kullanıcı |
| Rapor çıktısı hazırlandı | Rapor işini başlatan kullanıcı |

## Yönetim ekranından SMTP ayarı

Admin rolüyle **Ayarlar & Yedek → E-posta Bildirimleri** sekmesine girerek SMTP bilgileri doğrudan arayüzden kaydedilebilir. Ekranda şu alanlar bulunur:

- E-posta bildirimlerini etkinleştir
- SMTP sunucu
- SMTP port
- SMTP kullanıcı
- SMTP şifre
- Gönderen adresi
- TLS / SSL seçimi
- Uygulama bağlantısı
- Test Mail Gönder

SMTP şifresi veritabanında düz metin olarak saklanmaz; `MEDEK_API_SECRET` anahtarından türetilen uygulama anahtarıyla şifrelenir. Bu nedenle production ortamında `MEDEK_API_SECRET` değeri değiştirilirse kayıtlı SMTP şifresinin de yeniden girilmesi gerekir.

## .env fallback ayarları

SMTP bilgileri arayüzden kaydedilmemişse sistem `.env` değerlerini fallback olarak kullanır:

```env
MEDEK_MAIL_ENABLED=true
MEDEK_SMTP_HOST=smtp.kurum.edu.tr
MEDEK_SMTP_PORT=587
MEDEK_SMTP_USER=akreditasyon@kurum.edu.tr
MEDEK_SMTP_PASSWORD=SMTP_SIFRESI
MEDEK_SMTP_FROM=Akreditasyon Kalite Yönetimi <akreditasyon@kurum.edu.tr>
MEDEK_SMTP_TLS=true
MEDEK_SMTP_SSL=false
MEDEK_APP_BASE_URL=http://localhost:8080
```

Kurum Outlook/Exchange, Gmail Workspace veya üniversite SMTP servisi kullanılabilir. Parola ve token gibi gizli bilgiler e-posta içeriğine yazılmaz.

## Queue davranışı

`MEDEK_JOB_BACKEND=background` olduğunda e-postalar FastAPI BackgroundTasks ile gönderilir. Tek API container için yeterlidir.

`MEDEK_JOB_BACKEND=rq` olduğunda bildirim işleri Redis + RQ kuyruğuna alınır. Çoklu API instance / kurumsal production kullanımında tercih edilir:

```powershell
docker compose --env-file .env -f docker-compose.web.yml -f docker-compose.queue.yml up --build -d
```

## Yönetim ekranı

Admin rolüyle **Ayarlar & Yedek → E-posta Bildirimleri** sekmesinden SMTP ayarlarını kaydedebilir, test mail gönderebilir, SMTP durumunu ve son bildirim kayıtlarını görebilirsiniz. E-posta bildirimleri kapalıyken kayıtlar `disabled` durumuna düşer; bu, sistemin e-posta göndermediğini ama olayları kaydettiğini gösterir.

## Güvenlik notları

- E-postada şifre, JWT token, dosya yolu veya gizli sistem bilgisi gönderilmez.
- Alıcılar kullanıcı kayıtlarındaki `email` alanından alınır.
- SMTP parolası arayüzden kaydedilirse şifrelenmiş olarak veritabanında tutulur.
- SMTP parolası `.env` fallback olarak da verilebilir; clean release paketinde gerçek `.env` dosyası bulunmaz.
