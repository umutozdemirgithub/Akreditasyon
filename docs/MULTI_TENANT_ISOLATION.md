# v103 Multi-Tenant / Kurum-Fakülte İzolasyonu

Bu sürüm, tek kurulum içinde birden fazla kurum/fakülte/programın güvenli şekilde yönetilebilmesi için tenant-aware veri modelini ekler.

## Yeni veri modeli

- `tenants`: kurum / üniversite çalışma alanı
- `tenant_faculties`: tenant altındaki fakülte, MYO veya birim kayıtları
- `programs.tenant_id`, `programs.faculty_name`
- `users.tenant_id`, `users.tenant_scope`, `users.faculty_name`
- `program_users.tenant_id`

Mevcut tek kurumlu kurulumlar otomatik olarak `tenant_default` altında çalışmaya devam eder.

## Yetki yaklaşımı

- `tenant_scope=global` olan Admin tüm kurumları yönetebilir.
- `tenant_scope=tenant` olan Admin yalnızca kendi `tenant_id` kapsamındaki kullanıcı, program ve atamaları görebilir.
- Editör / Hazırlayıcı / Onaylayıcı / Denetçi (İzleyici) program ataması üzerinden çalışır; program ve kullanıcı tenant eşleşmesi backend seviyesinde kontrol edilir.

## Admin paneli

`Program Yönetimi → Kurum / Fakülte İzolasyonu` sekmesinde:

- kurum/tenant oluşturma ve güncelleme,
- fakülte/MYO birimi tanımlama,
- tenant bazlı program ve kullanıcı sayıları,
- tenant-aware program listesi görüntülenir.

`Kullanıcı & Rol Yönetimi` ekranında kullanıcıya kurum, tenant kapsamı ve fakülte/MYO atanabilir.

## Backend endpointleri

- `GET /api/admin/tenants`
- `POST /api/admin/tenants`
- `GET /api/admin/tenant-faculties`
- `POST /api/admin/tenant-faculties`
- `GET /api/admin/tenant-dashboard`

## Güvenlik notu

Tenant izolasyonu yalnızca frontend filtresi değildir. Program listesi, admin program listesi, kullanıcı listesi, program kullanıcı atamaları ve program erişim kontrolü backend tarafında `tenant_id` ile sınırlandırılır.
