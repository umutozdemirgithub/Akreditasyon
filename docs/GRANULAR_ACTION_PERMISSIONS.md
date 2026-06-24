# Granular Action Permissions

Bu sürümde yetkilendirme yalnızca sidebar modülü seviyesinde bırakılmadı. Dashboard ve yönetim ekranları içindeki sekmeler/aksiyonlar da `permission_matrix_json` üzerinden ayrı ayrı yönetilebilir hale getirildi.

## Program Yönetimi sekmeleri

`Program Yönetimi` ekranında aşağıdaki izinler ayrı satırlar olarak yönetilir:

- `program.list.view` — Tanımlı Programlar
- `program.create` — Yeni Program
- `program.clone` — Program Kopyala
- `program.assign_users` — Program Bazlı Kullanıcı ve Rol Atama
- `program.users.view` — Program Kullanıcıları
- `program.edit` — Program aktif/pasif düzenleme
- `program.archive` — Programı arşive/silme akışı
- `program.restore` — Program geri yükleme
- `program.purge` — Kalıcı silme

## Dashboard alt alanları

Aşağıdaki ekranlar sidebar görünürlüğünden bağımsız backend aksiyon izinlerine de bağlanmıştır:

- `notification.view` — Bildirim Merkezi
- `quality.view` — Görev & Eksik Analizi
- `stats.view` — İstatistikler
- `advanced_dashboard.view` — Gelişmiş Dashboard
- `activity_trail.view` — Tam Activity Trail
- `version_compare.view` — Versiyon Karşılaştırma

## Güvenlik kuralı

Sidebar görünürlüğü sadece menüyü gösterir/gizler. Veri erişimi ayrıca backend tarafında şu kurallarla korunur:

1. Kullanıcı ilgili programa veya hiyerarşik kapsama erişebilmelidir.
2. Kullanıcının etkin rolü ilgili aksiyon iznine sahip olmalıdır.
3. Editör / Hazırlayıcı gibi dar kapsamlı roller için başlık/section filtresi ayrıca uygulanır.

Bu sayede örneğin bir kullanıcı Program Yönetimi menüsünü görse bile `program.clone` kapalıysa Program Kopyala sekmesini kullanamaz; `version_compare.view` kapalıysa doğrudan API isteğiyle de sürüm diff verisini çekemez.
