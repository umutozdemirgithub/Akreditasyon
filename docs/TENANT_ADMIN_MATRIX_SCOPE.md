# v117 — Kurum Admin Matrix Scope

Bu sürüm Kurum Admin yetkilerinin ekrandaki görünürlük ve backend erişim davranışını Yetki Matrisi ile daha net bağlar.

## Değişiklikler

- `tenant.manage` işlem izni eklendi. Kurum Yönetimi sekmesi artık yalnızca bu izin açıksa görünür.
- Kurum Admin için `tenant.manage` varsayılan olarak kapalıdır; Süper Admin isterse Yetki Matrisi üzerinden açabilir.
- `user.login_attempts.view` işlem izni eklendi. Giriş Denemeleri sekmesi artık bu izne bağlıdır.
- Kurum Admin giriş denemelerinde yalnızca kendi kurumundaki kullanıcıların kayıtlarını görür.
- Kullanıcı & Rol Yönetimi sekmeleri artık `user.view`, `user.manage` ve `user.login_attempts.view` izinlerine göre açılır/kapanır.
- Program Yönetimi sekmeleri artık `tenant.manage`, `program.view`, `program.create`, `program.clone` ve `program.assign_users` izinlerine göre açılır/kapanır.
- Kullanıcı kayıtlarında `created_by` alanı izlenir; Kurum Admin’in oluşturduğu kullanıcılar kurum sınırı içinde yönetilir.

## Rol kuralı

- Süper Admin: tüm kurum ve matris kapsamını yönetebilir.
- Kurum Admin: kendi kurumu içinde, Süper Admin’in Yetki Matrisi ile açık bıraktığı izinler kadar işlem yapabilir.
- Editör / Hazırlayıcı / Onaylayıcı / Denetçi (İzleyici): Kurum Admin veya Süper Admin tarafından verilen program ve başlık yetkileriyle çalışır.
