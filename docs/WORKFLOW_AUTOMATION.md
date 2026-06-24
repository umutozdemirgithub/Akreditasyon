# v105 Workflow Automation

Bu modül AKYS içinde onay akışı, revizyon ve termin süreçleri için otomatik hatırlatma üretir.

## Amaç

- Geciken terminleri ilgili editörlere ve adminlere bildirmek.
- Yaklaşan son teslim tarihlerini önceden hatırlatmak.
- Onay bekleyen başlıkları onaylayıcı/admin tarafına taşımak.
- Revizyon bekleyen başlıkları editörlere tekrar görünür yapmak.
- In-app Notification Center ve SMTP e-posta akışını aynı olay kaydı üzerinden beslemek.

## Backend endpointleri

```txt
GET  /api/programs/{program_id}/workflow/reminders
GET  /api/programs/{program_id}/workflow/automation/settings
PUT  /api/programs/{program_id}/workflow/automation/settings
GET  /api/programs/{program_id}/workflow/automation/preview
GET  /api/programs/{program_id}/workflow/automation/runs
POST /api/programs/{program_id}/workflow/automation/run
```

## Yönetim paneli

Konum:

```txt
Ayarlar & Yedek → Workflow Otomasyon
```

Bu sekmede şunlar yönetilir:

- Workflow otomasyonunu aç/kapat.
- In-app bildirim üretimi.
- SMTP açıksa e-posta gönderimi.
- Termin kaç gün kala uyarı üretileceği.
- Aynı başlık/kategori için tekrar aralığı.
- Geciken termin, yaklaşan termin, onay bekleyen, revizyon bekleyen ve taslak takip kategorileri.
- Manuel çalıştırma ve force modu.
- Çalıştırma geçmişi.

## Bildirim mantığı

Her otomasyon çalıştırması aşağıdaki kategorilere göre aday üretir:

| Kategori | Alıcılar |
|---|---|
| Geciken termin | İlgili editörler + adminler |
| Yaklaşan termin | İlgili editörler + adminler |
| Onay bekliyor | Onaylayıcılar + adminler |
| Revizyon bekliyor | İlgili editörler + son aktör + adminler |
| Hazırlık devam ediyor | İlgili editörler + adminler |

`repeat_days` ayarı aynı başlık/kategoriye kısa sürede tekrar bildirim gitmesini engeller. Force çalıştırma bu korumayı bypass eder.

## Üretilen kayıtlar

Yeni tablolar:

```txt
workflow_runs
workflow_run_items
```

Notification Center tarafında olay tipi:

```txt
workflow_reminder
```

SMTP kapalıysa olay yine Notification Center içinde görünür; e-posta gönderimi sistem ayarlarına bağlıdır.
