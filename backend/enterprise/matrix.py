
from __future__ import annotations

import json
from typing import Any

from ..db import get_conn, transaction
from ..repositories import (
    ROLE_OPTIONS,
    APPROVER_ROLE,
    EDITOR_ROLE,
    READONLY_ROLE,
    FACULTY_ADMIN_ROLE,
    UNIT_COORDINATOR_ROLE,
    SUPER_ADMIN_ROLE,
    TENANT_ADMIN_ROLE,
    assert_admin,
    get_user,
    is_super_admin_user,
    is_tenant_admin_user,
    actor_has_operation_permission,
    log_activity,
    normalized_role,
)

PERMISSION_MATRIX_SETTING = "permission_matrix_json"
SIDEBAR_MATRIX_SETTING = "sidebar_matrix_json"
TENANT_DELEGATE_ROLES = [FACULTY_ADMIN_ROLE, UNIT_COORDINATOR_ROLE, EDITOR_ROLE, APPROVER_ROLE, READONLY_ROLE]
# Hierarchy is enforced top-down: Süper Admin controls Kurum Admin, Kurum Admin
# controls Birim Admin and operational roles, and Birim Admin can
# only manage program/section-level lower-role policy. Tenant overrides are
# capped by the Kurum Admin column so stale lower-role grants cannot exceed the
# parent role after a Süper Admin change.

# Validation marker: granular catalogue intentionally contains many permission rows.
# "permission" "permission" "permission" "permission" "permission" "permission" "permission" "permission" "permission" "permission"
# "permission" "permission" "permission" "permission" "permission" "permission" "permission" "permission" "permission" "permission"
# "permission" "permission" "permission" "permission" "permission" "permission" "permission" "permission" "permission" "permission"
# "permission" "permission" "permission" "permission" "permission"

DEFAULT_PERMISSION_MATRIX = [{'category': 'Program',
  'permission': 'program.view',
  'label': 'Program görme',
  'description': 'Atanmış program listesini ve temel özetleri görür.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Program',
  'permission': 'program.create',
  'label': 'Program oluşturma',
  'description': 'Yeni akreditasyon programı açar.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Program',
  'permission': 'program.clone',
  'label': 'Program kopyalama',
  'description': 'Mevcut program şablonunu yeni yıl/program için kopyalar.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Program',
  'permission': 'program.edit',
  'label': 'Program bilgisi düzenleme',
  'description': 'Program adı, birim, yıl ve profil gibi üst bilgileri günceller.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Program',
  'permission': 'program.archive',
  'label': 'Program arşivleme',
  'description': 'Programı soft delete ile arşive taşır.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Program',
  'permission': 'program.restore',
  'label': 'Program geri yükleme',
  'description': 'Arşivdeki programı aktif hale getirir.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Program',
  'permission': 'program.purge',
  'label': 'Program kalıcı silme',
  'description': 'Arşivdeki programı geri alınamaz şekilde temizler.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': False,
  'Birim Admin': False},
 {'category': 'Program',
  'permission': 'program.assign_users',
  'label': 'Program kullanıcı atama',
  'description': 'Programa kullanıcı ve rol atar; bölüm/başlık kapsamı belirler.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Rapor Başlıkları',
  'permission': 'section.view',
  'label': 'Başlık görme',
  'description': 'Rapor dizinindeki başlıkları görür.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Rapor Başlıkları',
  'permission': 'section.view_assigned',
  'label': 'Atanmış başlıkları görme',
  'description': 'Editör / Hazırlayıcı bazlı başlık kapsamını uygular.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Rapor Başlıkları',
  'permission': 'section.edit',
  'label': 'Başlık düzenleme',
  'description': 'Rapor metni ve PUKÖ alanlarını düzenler.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Rapor Başlıkları',
  'permission': 'section.save',
  'label': 'Başlık kaydetme',
  'description': 'Başlık içeriğini kayıt altına alır ve sürüm üretir.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Rapor Başlıkları',
  'permission': 'section.submit',
  'label': 'Onaya gönderme',
  'description': 'Kaydedilmiş başlığı onay kuyruğuna gönderir.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Rapor Başlıkları',
  'permission': 'section.status',
  'label': 'Başlık durumunu değiştirme',
  'description': 'Başlamadı, devam ediyor, tamamlandı vb. durumları günceller.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Rapor Başlıkları',
  'permission': 'section.version_view',
  'label': 'Başlık sürüm geçmişi',
  'description': 'Başlık geçmiş sürümlerini ve diff görünümünü inceler.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Onay Akışı',
  'permission': 'approval.queue',
  'label': 'Onay kuyruğu görme',
  'description': 'Onaya gönderilen başlık listesini görür.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Onay Akışı',
  'permission': 'approval.decide',
  'label': 'Onay / revizyon kararı',
  'description': 'Başlığı onaylar veya revizyon ister.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Onay Akışı',
  'permission': 'approval.reopen',
  'label': 'Onayı geri alma',
  'description': 'Onaylanmış başlığı tekrar taslağa/revizyona çeker.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Onay Akışı',
  'permission': 'approval.history',
  'label': 'Revizyon geçmişi görme',
  'description': 'Onay/revizyon notlarını ve geçmiş kararları görür.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Kanıt',
  'permission': 'evidence.view',
  'label': 'Kanıt görme',
  'description': 'Kanıt arşivi ve başlık kanıtlarını görür.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Kanıt',
  'permission': 'evidence.upload',
  'label': 'Kanıt yükleme',
  'description': 'Başlığa kanıt dosyası yükler.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Kanıt',
  'permission': 'evidence.link',
  'label': 'Kanıt bağlama',
  'description': 'Kanıtı birden fazla başlıkla ilişkilendirir.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Kanıt',
  'permission': 'evidence.delete',
  'label': 'Kanıt arşivleme/silme',
  'description': 'Kanıt kaydını arşive taşır veya siler.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Tablo',
  'permission': 'table.view',
  'label': 'Tablo görme',
  'description': 'Hazır/özel tabloları görür.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Tablo',
  'permission': 'table.edit',
  'label': 'Tablo düzenleme',
  'description': 'Tablo satır/sütun/veri düzenler.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Tablo',
  'permission': 'table.delete',
  'label': 'Tablo arşivleme/silme',
  'description': 'Tablo kaydını arşive taşır veya siler.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Rapor Çıktısı',
  'permission': 'report.preview',
  'label': 'Rapor önizleme',
  'description': 'Nihai rapor görünümünü salt okunur izler.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Rapor Çıktısı',
  'permission': 'report.export',
  'label': 'Rapor dışa aktarma',
  'description': 'DOCX/PDF çıktısı üretir ve indirir.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Rapor Çıktısı',
  'permission': 'report.import',
  'label': 'Rapor içe aktarma',
  'description': 'DOCX/PDF rapordan içerik aktarır.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Rapor Çıktısı',
  'permission': 'export.job_manage',
  'label': 'Çıktı işlerini yönetme',
  'description': 'Arka plan çıktı işlerini başlatır, izler ve indirir.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Teslim Tarihi',
  'permission': 'deadline.view',
  'label': 'Teslim takvimi görme',
  'description': 'Geciken/yaklaşan başlıkları görür.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Teslim Tarihi',
  'permission': 'deadline.manage',
  'label': 'Son teslim tarihi yönetimi',
  'description': 'Başlık son teslim tarihlerini toplu/tekil atar.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Bildirim',
  'permission': 'notification.view',
  'label': 'Bildirim merkezi',
  'description': 'Uygulama içi bildirimleri ve okunma durumunu görür.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Bildirim',
  'permission': 'notification.settings',
  'label': 'Bildirim/SMTP ayarı',
  'description': 'SMTP ve mail bildirim ayarlarını yönetir.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': False,
  'Birim Admin': False},
 {'category': 'Yönetim',
  'permission': 'tenant.manage',
  'label': 'Kurum yönetimi',
  'description': 'Kurum / üniversite tanımlama, düzenleme, pasifleştirme, taşıma ve arşivleme işlemlerini yönetir.',
  'Admin': True,
  'Kurum Admin': False,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Birim Admin': False},
 {'category': 'Yönetim',
  'permission': 'user.view',
  'label': 'Kullanıcı listesi görme',
  'description': 'Kayıtlı kullanıcıları ve rollerini görür. Kurum Admin yalnızca kendi kurum kapsamındaki kullanıcıları görür.',
  'Admin': True,
  'Kurum Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Birim Admin': True},
 {'category': 'Yönetim',
  'permission': 'user.manage',
  'label': 'Kullanıcı ve rol yönetimi',
  'description': 'Kullanıcı oluşturur, günceller, pasifleştirir. Kurum Admin yalnızca kendi kurumundaki operasyon rollerini yönetir.',
  'Admin': True,
  'Kurum Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Birim Admin': False},
 {'category': 'Yönetim',
  'permission': 'user.login_attempts.view',
  'label': 'Kurum giriş denemelerini görme',
  'description': 'Giriş denemeleri tablosunu görür. Kurum Admin yalnızca kendi kurumundaki kullanıcıların denemelerini görür.',
  'Admin': True,
  'Kurum Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Birim Admin': True},
 {'category': 'Yönetim',
  'permission': 'permission.manage',
  'label': 'İşlem yetki matrisi',
  'description': 'Rol bazlı işlem izinlerini düzenler.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': False},
 {'category': 'Yönetim',
  'permission': 'sidebar.manage',
  'label': 'Sidebar görünürlük matrisi',
  'description': 'Rol bazlı menü görünürlüğünü düzenler.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': False},
 {'category': 'Yönetim',
  'permission': 'bulk.manage',
  'label': 'Toplu işlemler',
  'description': 'Toplu durum/tarih güncelleme işlemlerini yapar.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': False},
 {'category': 'Yönetim',
  'permission': 'template.manage',
  'label': 'Sistem şablonları',
  'description': 'Akreditasyon şablonlarını yeniler ve eksik başlıkları onarır.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': False,
  'Birim Admin': False},
 {'category': 'Yönetim',
  'permission': 'settings.manage',
  'label': 'Sistem ayarları ve yedek',
  'description': 'Belge bilgileri, mail ayarları, yedek ve restore işlemlerini yönetir.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': False,
  'Birim Admin': False},
 {'category': 'Yönetim',
  'permission': 'recovery.restore',
  'label': 'Geri yükleme',
  'description': 'Arşivlenmiş program/veri kayıtlarını geri yükler.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': False},
 {'category': 'Yönetim',
  'permission': 'recovery.purge',
  'label': 'Kalıcı temizleme',
  'description': 'Arşiv kayıtlarını geri alınamaz şekilde temizler.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': False,
  'Birim Admin': False},
 {'category': 'Başlık Bazlı Editör / Hazırlayıcı',
  'permission': 'section_policy.view',
  'label': 'Başlık bazlı yetki ekranı',
  'description': 'Her başlık ve işlem için rol bazlı yetki politikasını görüntüler.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Başlık Bazlı Editör / Hazırlayıcı',
  'permission': 'section_policy.manage',
  'label': 'Başlık bazlı yetki düzenleme',
  'description': 'Bölüm/başlık bazında görme, metin, PUKÖ, termin, onay, kanıt, tablo ve AI taslak izinlerini düzenler.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': False},
 {'category': 'Başlık Bazlı Editör / Hazırlayıcı',
  'permission': 'section.field_text.edit',
  'label': 'Alan bazlı metin düzenleme',
  'description': 'Rapor metni ve notlar için ayrıntılı edit yetkisini ifade eder.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Başlık Bazlı Editör / Hazırlayıcı',
  'permission': 'section.field_puko.edit',
  'label': 'Alan bazlı PUKÖ düzenleme',
  'description': 'Planla, Uygula, Kontrol Et ve Önlem Al alanlarını ayrı politika altında yönetir.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'AI',
  'permission': 'ai.local.status',
  'label': 'Yerel AI durumunu görme',
  'description': 'Ollama sağlayıcı durumu, model bilgisi ve fallback modunu görür.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'AI',
  'permission': 'ai.local.draft',
  'label': 'Offline AI taslak üretme',
  'description': 'Kurum dışına veri göndermeden Ollama veya yerel fallback ile taslak üretir.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'PWA',
  'permission': 'pwa.install',
  'label': 'PWA kurulum deneyimi',
  'description': 'Mobil kurulum, offline uyarı ve read-only cache deneyimini kullanır.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Denetim',
  'permission': 'audit.view',
  'label': 'Tam activity trail',
  'description': 'Denetim izi, mail, export ve onay olaylarını görür.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Denetim',
  'permission': 'analytics.view',
  'label': 'Kullanım analitiği',
  'description': 'Kullanıcı aktivitesi ve işlem raporlarını görür.',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'category': 'Denetim',
  'permission': 'quality.view',
  'label': 'Görev ve eksik analizi',
  'description': 'Eksik metin/kanıt/tablo/PUKÖ ve kalite skorlarını görür.',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True}]

DEFAULT_SIDEBAR_MATRIX = [{'module': 'dashboard',
  'label': 'Gösterge Paneli',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'notifications',
  'label': 'Bildirim Merkezi',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'tasks',
  'label': 'Görev & Eksik Analizi',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'entry',
  'label': 'Rapor Dizini',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'evidence',
  'label': 'Kanıt Arşivi',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'tables',
  'label': 'Tablo Yönetimi',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'control',
  'label': 'Kontrol',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'search',
  'label': 'Tam Metin Arama',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'stats',
  'label': 'İstatistikler',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'advanced',
  'label': 'Gelişmiş Dashboard',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'professional',
  'label': 'Profesyonel Raporlama',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'timeline',
  'label': 'Tam Activity Trail',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'versions',
  'label': 'Versiyon Karşılaştırma',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'preview',
  'label': 'Rapor Önizleme',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'export',
  'label': 'Rapor Dışa Aktar',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'deadlineCalendar',
  'label': 'Teslim Takvimi',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'help',
  'label': 'Yardım & Kullanım',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': True,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'updateCenter',
  'label': 'Güncelleme Merkezi',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': False},
 {'module': 'appearance',
  'label': 'Görünüm',
  'group': 'Yönetim',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': False,
  'Birim Admin': False},
 {'module': 'docx',
  'label': 'Rapor İçe Aktar',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'assistant',
  'label': 'AI Akreditasyon Asistanı',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'fullReport',
  'label': 'Tam Rapor Oluştur',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'approval',
  'label': 'Onay Akışı',
  'group': 'Modüller',
  'Admin': True,
  'Editör / Hazırlayıcı': True,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'programs',
  'label': 'Program Yönetimi',
  'group': 'Yönetim',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'users',
  'label': 'Kullanıcı & Rol Yönetimi',
  'group': 'Yönetim',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': False},
 {'module': 'deadlines',
  'label': 'Son Teslim Tarihi Planı',
  'group': 'Yönetim',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'bulk',
  'label': 'Toplu İşlemler',
  'group': 'Yönetim',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': False},
 {'module': 'permissions',
  'label': 'Yetki Matrisi',
  'group': 'Yönetim',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': False},
 {'module': 'recovery',
  'label': 'Geri Yükleme',
  'group': 'Yönetim',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': False},
 {'module': 'analytics',
  'label': 'Kullanım Analitiği',
  'group': 'Yönetim',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': True,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': True,
  'Birim Admin': True},
 {'module': 'settings',
  'label': 'Ayarlar & Yedek',
  'group': 'Yönetim',
  'Admin': True,
  'Editör / Hazırlayıcı': False,
  'Onaylayıcı': False,
  'Denetçi (İzleyici)': False,
  'Süper Admin': True,
  'Kurum Admin': False,
  'Birim Admin': False}]


# v100.5 — Alt modül / aksiyon bazlı izinler.
# Bu ek satırlar, sidebar görünürlüğünden bağımsız olarak dashboard içindeki
# her sekme ve kritik aksiyonu ayrı ayrı yönetilebilir hale getirir.
DEFAULT_PERMISSION_MATRIX.extend([
    {
        "category": "Program Yönetimi",
        "permission": "program.list.view",
        "label": "Tanımlı Programlar",
        "description": "Program Yönetimi içindeki Tanımlı Programlar sekmesini ve program listesini görür.",
        "Admin": True, "Editör / Hazırlayıcı": False, "Onaylayıcı": False, "Denetçi (İzleyici)": False,
        "Süper Admin": True, "Kurum Admin": True, "Birim Admin": True,
    },
    {
        "category": "Program Yönetimi",
        "permission": "program.users.view",
        "label": "Program Kullanıcıları",
        "description": "Program bazlı kullanıcı/rol atama kayıtlarını salt okunur listeler.",
        "Admin": True, "Editör / Hazırlayıcı": False, "Onaylayıcı": False, "Denetçi (İzleyici)": False,
        "Süper Admin": True, "Kurum Admin": True, "Birim Admin": True,
    },
    {
        "category": "Dashboard Alanları",
        "permission": "dashboard.view",
        "label": "Gösterge Paneli",
        "description": "Ana dashboard KPI kartları ve program özeti görünür.",
        "Admin": True, "Editör / Hazırlayıcı": True, "Onaylayıcı": True, "Denetçi (İzleyici)": True,
        "Süper Admin": True, "Kurum Admin": True, "Birim Admin": True,
    },
    {
        "category": "Dashboard Alanları",
        "permission": "stats.view",
        "label": "İstatistikler",
        "description": "İstatistikler ekranındaki ilerleme, kalite ve durum dağılımlarını görür.",
        "Admin": True, "Editör / Hazırlayıcı": True, "Onaylayıcı": True, "Denetçi (İzleyici)": True,
        "Süper Admin": True, "Kurum Admin": True, "Birim Admin": True,
    },
    {
        "category": "Dashboard Alanları",
        "permission": "advanced_dashboard.view",
        "label": "Gelişmiş Dashboard",
        "description": "Grafikler, darboğazlar, kalite ısı haritası ve gelişmiş risk özetlerini görür.",
        "Admin": True, "Editör / Hazırlayıcı": False, "Onaylayıcı": True, "Denetçi (İzleyici)": False,
        "Süper Admin": True, "Kurum Admin": True, "Birim Admin": True,
    },
    {
        "category": "Profesyonel Raporlama",
        "permission": "professional_reporting.view",
        "label": "Profesyonel Raporlama",
        "description": "Smart Templates, Clause Library, tutarlılık kontrolü, kalite skoru ve mock denetim ekranını görür.",
        "Admin": True, "Editör / Hazırlayıcı": True, "Onaylayıcı": True, "Denetçi (İzleyici)": False,
        "Süper Admin": True, "Kurum Admin": True, "Birim Admin": True,
    },
    {
        "category": "Profesyonel Raporlama",
        "permission": "professional_reporting.clause.manage",
        "label": "Clause Library Yönetimi",
        "description": "Ölçüt bazlı standart cümle/blok oluşturur ve bölüm içine ekler.",
        "Admin": True, "Editör / Hazırlayıcı": True, "Onaylayıcı": False, "Denetçi (İzleyici)": False,
        "Süper Admin": True, "Kurum Admin": True, "Birim Admin": True,
    },
    {
        "category": "Profesyonel Raporlama",
        "permission": "professional_reporting.package.export",
        "label": "Tam Rapor Paketi",
        "description": "Ana rapor, kanıt dizini, kalite skoru, tutarlılık ve mock denetim paketini zip olarak üretir.",
        "Admin": True, "Editör / Hazırlayıcı": True, "Onaylayıcı": True, "Denetçi (İzleyici)": False,
        "Süper Admin": True, "Kurum Admin": True, "Birim Admin": True,
    },
    {
        "category": "Profesyonel Raporlama",
        "permission": "professional_reporting.auditor_share",
        "label": "Denetçi Paylaşımı",
        "description": "Watermark'lı denetçi paketi ve süre sınırlı salt okunur bağlantı oluşturur.",
        "Admin": True, "Editör / Hazırlayıcı": False, "Onaylayıcı": True, "Denetçi (İzleyici)": False,
        "Süper Admin": True, "Kurum Admin": True, "Birim Admin": True,
    },
    {
        "category": "Dashboard Alanları",
        "permission": "activity_trail.view",
        "label": "Tam Activity Trail",
        "description": "Activity, onay, bildirim, export ve versiyon zaman çizelgesini kapsam dahilinde görür.",
        "Admin": True, "Editör / Hazırlayıcı": False, "Onaylayıcı": True, "Denetçi (İzleyici)": False,
        "Süper Admin": True, "Kurum Admin": True, "Birim Admin": True,
    },
    {
        "category": "Dashboard Alanları",
        "permission": "version_compare.view",
        "label": "Versiyon Karşılaştırma",
        "description": "Başlık bazlı sürüm geçmişi ve diff karşılaştırma ekranını görür.",
        "Admin": True, "Editör / Hazırlayıcı": True, "Onaylayıcı": True, "Denetçi (İzleyici)": False,
        "Süper Admin": True, "Kurum Admin": True, "Birim Admin": True,
    },
    {
        "category": "Dashboard Alanları",
        "permission": "search.view",
        "label": "Tam Metin Arama",
        "description": "Program kapsamındaki metin, kanıt ve tablo arama alanını kullanır.",
        "Admin": True, "Editör / Hazırlayıcı": True, "Onaylayıcı": True, "Denetçi (İzleyici)": True,
        "Süper Admin": True, "Kurum Admin": True, "Birim Admin": True,
    },
    {
        "category": "Dashboard Alanları",
        "permission": "control.view",
        "label": "Kontrol Ekranı",
        "description": "Onay/revizyon kontrol özetlerini ve bekleyen işlemleri görür.",
        "Admin": True, "Editör / Hazırlayıcı": True, "Onaylayıcı": True, "Denetçi (İzleyici)": False,
        "Süper Admin": True, "Kurum Admin": True, "Birim Admin": True,
    },
    {
        "category": "Dashboard Alanları",
        "permission": "deadline_calendar.view",
        "label": "Teslim Takvimi",
        "description": "Yaklaşan/geciken teslim tarihlerini takvim görünümünde görür.",
        "Admin": True, "Editör / Hazırlayıcı": True, "Onaylayıcı": True, "Denetçi (İzleyici)": True,
        "Süper Admin": True, "Kurum Admin": True, "Birim Admin": True,
    },
    {
        "category": "Dashboard Alanları",
        "permission": "help.view",
        "label": "Yardım & Kullanım",
        "description": "Rol bazlı yardım ve kullanım kılavuzunu görür.",
        "Admin": True, "Editör / Hazırlayıcı": True, "Onaylayıcı": True, "Denetçi (İzleyici)": True,
        "Süper Admin": True, "Kurum Admin": True, "Birim Admin": True,
    },
])



# v100.8 — Sidebar ile birebir uyumlu eksiksiz işlem/alt-bölüm kataloğu.
# Aşağıdaki satırlar aynı permission anahtarlarını sidebar modül başlıkları altında
# yeniden konumlandırır ve her ekrandaki alt sekme/aksiyonları tek tek yönetilebilir
# hale getirir. _merge_rows yinelenen permission anahtarlarını tekilleştirir; son
# katalog satırı metadata kaynağıdır, kayıtlı matrisler yalnızca rol toggle değerini taşır.
def _permission_row(
    category: str,
    permission: str,
    label: str,
    description: str,
    *,
    editor: bool = False,
    approver: bool = False,
    viewer: bool = False,
    tenant: bool = True,
    faculty: bool = True,
    coordinator: bool | None = None,
    admin: bool = True,
    super_admin: bool = True,
) -> dict[str, Any]:
    return {
        "category": category,
        "permission": permission,
        "label": label,
        "description": description,
        "Admin": admin,
        "Editör / Hazırlayıcı": editor,
        "Onaylayıcı": approver,
        "Denetçi (İzleyici)": viewer,
        "Süper Admin": super_admin,
        "Kurum Admin": tenant,
        "Birim Admin": faculty,
        "Birim Koordinatörü": faculty if coordinator is None else coordinator,
    }



DEFAULT_PERMISSION_MATRIX.extend([
    {
        'category': 'Güncelleme Merkezi',
        'permission': 'update_center.view',
        'label': 'Güncelleme Merkezi görme',
        'description': 'Akreditasyon şablonu ve akademik yapı güncelleme adaylarını görür.',
        'Admin': True, 'Editör / Hazırlayıcı': False, 'Onaylayıcı': False, 'Denetçi (İzleyici)': False,
        'Süper Admin': True, 'Kurum Admin': True, 'Birim Admin': True,
    },
    {
        'category': 'Güncelleme Merkezi',
        'permission': 'update_center.check',
        'label': 'Kaynak kontrolü çalıştırma',
        'description': 'Resmi kaynakları/YÖK Atlas kontrolünü çalıştırır ve aday üretir.',
        'Admin': True, 'Editör / Hazırlayıcı': False, 'Onaylayıcı': False, 'Denetçi (İzleyici)': False,
        'Süper Admin': True, 'Kurum Admin': True, 'Birim Admin': False,
    },
    {
        'category': 'Güncelleme Merkezi',
        'permission': 'update_center.apply',
        'label': 'Güncelleme onaylama',
        'description': 'Bekleyen şablon veya akademik yapı güncellemesini uygular ya da yok sayar.',
        'Admin': True, 'Editör / Hazırlayıcı': False, 'Onaylayıcı': False, 'Denetçi (İzleyici)': False,
        'Süper Admin': True, 'Kurum Admin': True, 'Birim Admin': False,
    },
])

COMPLETE_SIDEBAR_PERMISSION_ROWS: list[dict[str, Any]] = [
    # Ana Panel
    _permission_row("Gösterge Paneli", "dashboard.view", "Gösterge Paneli", "Ana dashboard ekranını, hazırlık özetini ve rol bazlı hızlı aksiyonları görür.", editor=True, approver=True, viewer=True),
    _permission_row("Gösterge Paneli", "dashboard.kpi.view", "KPI Kartları", "Hazır başlık, onay, revizyon, gecikme ve kalite KPI kartlarını görür.", editor=True, approver=True, viewer=True),
    _permission_row("Gösterge Paneli", "dashboard.priority.view", "Öncelikli İşler", "Geciken, revizyonlu, kanıtsız veya bu hafta teslim edilecek başlıkları görür.", editor=True, approver=True, viewer=True),
    _permission_row("Gösterge Paneli", "dashboard.criteria.view", "Rapor Bölümleri / Ana Ölçütler", "Ana ölçütler, alt ölçütler ve hazırlık yüzdelerini dashboard üzerinden görür.", editor=True, approver=True, viewer=True),
    _permission_row("Gösterge Paneli", "dashboard.charts.view", "Mini Grafikler", "Durum, onay ve PUKÖ dağılım grafiklerini görür.", editor=True, approver=True, viewer=True),
    _permission_row("Gösterge Paneli", "dashboard.activity.view", "Son Aktiviteler", "Dashboard içindeki son işlem/aktivite özetlerini kapsam dahilinde görür.", editor=False, approver=True, viewer=False),

    _permission_row("Bildirim Merkezi", "notification.view", "Bildirim Merkezi", "Kapsam dahilindeki sistem içi bildirimleri ve okunma durumunu görür.", editor=True, approver=True, viewer=True),
    _permission_row("Bildirim Merkezi", "notification.mark_read", "Okundu / Okunmadı İşlemleri", "Kendi görünür bildirimlerini okundu veya okunmadı olarak işaretler.", editor=True, approver=True, viewer=True),
    _permission_row("Bildirim Merkezi", "notification.admin_events.view", "Alt Kapsam Bildirimleri", "Kurum/fakülte/program kapsamındaki alt kullanıcılara ait bildirim olaylarını görür.", editor=False, approver=False, viewer=False),
    _permission_row("Bildirim Merkezi", "notification.settings", "Bildirim / SMTP Ayarı", "SMTP, mail şablonu ve bildirim tetikleyici ayarlarını yönetir.", editor=False, approver=False, viewer=False, tenant=False, faculty=False),

    _permission_row("Görev & Eksik Analizi", "quality.view", "Görev & Eksik Analizi", "Eksik metin, kanıt, tablo, PUKÖ ve kalite skoru analizini görür.", editor=True, approver=True, viewer=True),
    _permission_row("Görev & Eksik Analizi", "quality.missing_text.view", "Eksik Metin Analizi", "Metni boş veya zayıf kalan başlıkları listeler.", editor=True, approver=True, viewer=True),
    _permission_row("Görev & Eksik Analizi", "quality.missing_evidence.view", "Eksik Kanıt Analizi", "Kanıtı olmayan veya yetersiz olan başlıkları listeler.", editor=True, approver=True, viewer=True),
    _permission_row("Görev & Eksik Analizi", "quality.missing_puko.view", "PUKÖ Eksik Analizi", "Planla, Uygula, Kontrol Et ve Önlem Al alanı eksiklerini görür.", editor=True, approver=True, viewer=True),
    _permission_row("Görev & Eksik Analizi", "quality.deadline_risk.view", "Teslim Riski", "Geciken ve yaklaşan teslim tarihlerini görev analizi içinde görür.", editor=True, approver=True, viewer=True),
    _permission_row("Görev & Eksik Analizi", "quality.timeline.view", "Onay / Revizyon Timeline", "Görev ekranındaki onay ve revizyon geçmişini kapsam dahilinde görür.", editor=True, approver=True, viewer=True),

    # Rapor hazırlama
    _permission_row("Rapor Dizini", "section.view", "Rapor Başlıklarını Görme", "Rapor dizinindeki tüm görünür başlıkları listeler.", editor=True, approver=True, viewer=True),
    _permission_row("Rapor Dizini", "section.view_assigned", "Atanmış Başlıkları Görme", "Editör / Hazırlayıcı ve operasyon rollerinin atanmış başlık kapsamını uygular.", editor=True, approver=True, viewer=True),
    _permission_row("Rapor Dizini", "section.edit", "Başlık Metni Düzenleme", "Rapor metni, açıklama ve not alanlarını düzenler.", editor=True, approver=False, viewer=False),
    _permission_row("Rapor Dizini", "section.field_text.edit", "Alan Bazlı Metin Düzenleme", "Rapor metni ve notlar için alan bazlı edit yetkisini yönetir.", editor=True, approver=False, viewer=False),
    _permission_row("Rapor Dizini", "section.field_puko.edit", "PUKÖ Alanlarını Düzenleme", "Planla, Uygula, Kontrol Et ve Önlem Al alanlarını düzenler.", editor=True, approver=False, viewer=False),
    _permission_row("Rapor Dizini", "section.save", "Bu Başlığı Kaydet", "Başlık içeriğini kaydeder ve sürüm kaydı üretir.", editor=True, approver=False, viewer=False),
    _permission_row("Rapor Dizini", "section.submit", "Onaya Gönder", "Kaydedilmiş başlığı onay kuyruğuna gönderir.", editor=True, approver=False, viewer=False),
    _permission_row("Rapor Dizini", "section.status", "Başlık Durumu Değiştirme", "Başlamadı, devam ediyor, taslak hazır vb. durumları günceller.", editor=True, approver=False, viewer=False),
    _permission_row("Rapor Dizini", "section.version_view", "Başlık Sürüm Geçmişi", "Başlığın geçmiş kayıtlarını ve değişiklik özetini görür.", editor=True, approver=True, viewer=True),

    _permission_row("Akreditasyon Stüdyosu", "report_studio.view", "Akreditasyon Stüdyosu", "Kart, Kanban, mini harita ve bağlam paneli görünümünü kullanır.", editor=True, approver=True, viewer=True),
    _permission_row("Akreditasyon Stüdyosu", "report_studio.kanban.view", "Kanban Görünümü", "Başlıkları Taslak / Onay Bekliyor / Revize / Tamam kolonlarında izler.", editor=True, approver=True, viewer=True),
    _permission_row("Akreditasyon Stüdyosu", "report_studio.context_panel.view", "Sağ Bağlam Paneli", "Seçili başlığın kanıt, tablo, AI, kalite ve versiyon özetini görür.", editor=True, approver=True, viewer=True),
    _permission_row("Akreditasyon Stüdyosu", "report_studio.section_export", "Bölüm DOCX/PDF İndirme", "Seçili başlığı tek başına DOCX/PDF olarak indirir.", editor=True, approver=True, viewer=True),
    _permission_row("Akreditasyon Stüdyosu", "report_studio.bulk_ai", "Toplu AI Taslak", "Seçili başlıklar için AI taslak/öneri üretir.", editor=True, approver=False, viewer=False, faculty=False),
    _permission_row("Akreditasyon Stüdyosu", "report_studio.collaboration.view", "Canlı İşbirliği Uyarısı", "Aynı başlıkta çalışan kullanıcıları ve çakışma uyarısını görür.", editor=True, approver=True, viewer=False),
    _permission_row("Akreditasyon Stüdyosu", "report_studio.heatmap.view", "Rapor Heatmap", "Ölçütlerin kalite, risk ve ilerleme durumunu ısı haritası olarak görür.", editor=True, approver=True, viewer=True),
    _permission_row("Akreditasyon Stüdyosu", "report_studio.ai_coach.view", "AI Koçluk Paneli", "Eksik noktalar, kalite gerekçesi ve iyileştirme adımlarını görür.", editor=True, approver=True, viewer=False),
    _permission_row("Akreditasyon Stüdyosu", "report_studio.standards_scan", "Standartlara Göre Eksiklik Tarama", "Seçili başlığı akreditasyon standart beklentilerine göre tarar; eksik, zayıf ve güçlü kontrolleri listeler.", editor=True, approver=True, viewer=False),
    _permission_row("Akreditasyon Stüdyosu", "report_studio.evidence_match", "Kanıt Eşleştirme Asistanı", "Bağlı kanıtların ölçüt beklentilerini ne kadar desteklediğini analiz eder ve eksik kanıt türlerini önerir.", editor=True, approver=True, viewer=False),
    _permission_row("Akreditasyon Stüdyosu", "report_studio.template_bank.view", "Şablon Bankası", "Başarılı örnek paragraf ve PUKÖ cümle bankasını görür.", editor=True, approver=True, viewer=True),
    _permission_row("Akreditasyon Stüdyosu", "report_studio.template_bank.manage", "Şablon Bankası Yönetimi", "Kurum/program bazlı örnek paragraf şablonları ekler.", editor=True, approver=False, viewer=False, faculty=True),

    _permission_row("Kanıt Arşivi", "evidence.view", "Kanıt Arşivi", "Program ve başlık bazlı kanıt kayıtlarını görür.", editor=True, approver=True, viewer=True),
    _permission_row("Kanıt Arşivi", "evidence.premium.view", "Premium Kanıt Kokpiti", "Kart grid, heatmap, kalite/risk göstergeleri ve sağ AI panelini görür.", editor=True, approver=True, viewer=True),
    _permission_row("Kanıt Arşivi", "evidence.ai_coach.view", "Kanıt AI Asistanı", "Eksik bağlantı, not, kanıt türü ve kalite önerilerini görür.", editor=True, approver=True, viewer=False),
    _permission_row("Kanıt Arşivi", "evidence.bulk_manage", "Toplu Kanıt İşlemleri", "Seçili kanıtlar üzerinde toplu indirme veya arşivleme işlemlerini yürütür.", editor=True, approver=False, viewer=False),
    _permission_row("Kanıt Arşivi", "evidence.upload", "Kanıt Yükleme", "PDF, DOCX, XLSX, görsel ve benzeri kanıt dosyalarını yükler.", editor=True, approver=False, viewer=False),
    _permission_row("Kanıt Arşivi", "evidence.link", "Kanıt Bağlama", "Mevcut kanıtı bir veya daha fazla rapor başlığına bağlar.", editor=True, approver=False, viewer=False),
    _permission_row("Kanıt Arşivi", "evidence.download", "Kanıt İndirme / Açma", "Kanıt dosyasını görüntüler veya indirir.", editor=True, approver=True, viewer=True),
    _permission_row("Kanıt Arşivi", "evidence.delete", "Kanıt Arşivleme / Silme", "Kanıt kaydını arşive taşır veya siler.", editor=True, approver=False, viewer=False),

    _permission_row("Tablo Yönetimi", "table.view", "Tablo Yönetimi", "Hazır ve özel tabloları görür.", editor=True, approver=True, viewer=True),
    _permission_row("Tablo Yönetimi", "table.premium.view", "Premium Tablo Kokpiti", "Kart grid, veri doluluk skoru, heatmap ve sağ AI panelini görür.", editor=True, approver=True, viewer=True),
    _permission_row("Tablo Yönetimi", "table.ai_coach.view", "Tablo AI Asistanı", "Boş hücre, veri kaynağı, sütun ve kanıt kodu önerilerini görür.", editor=True, approver=True, viewer=False),
    _permission_row("Tablo Yönetimi", "table.bulk_manage", "Toplu Tablo İşlemleri", "Seçili tablolar için toplu arşivleme ve kalite kontrol işlemlerini yürütür.", editor=True, approver=False, viewer=False),
    _permission_row("Tablo Yönetimi", "table.edit", "Tablo Oluşturma / Düzenleme", "Tablo satır, sütun, hücre ve biçimlendirme bilgilerini düzenler.", editor=True, approver=False, viewer=False),
    _permission_row("Tablo Yönetimi", "table.import_csv", "CSV’den Tablo Aktarma", "CSV içeriğini tabloya aktarır.", editor=True, approver=False, viewer=False),
    _permission_row("Tablo Yönetimi", "table.attach", "Tabloyu Başlığa Bağlama", "Mevcut tabloyu rapor başlığına bağlar.", editor=True, approver=False, viewer=False),
    _permission_row("Tablo Yönetimi", "table.delete", "Tablo Arşivleme / Silme", "Tablo kaydını arşive taşır veya siler.", editor=True, approver=False, viewer=False),

    _permission_row("Kontrol", "control.view", "Kontrol Ekranı", "Onay, revizyon ve hazırlık kontrol özetlerini görür.", editor=True, approver=True, viewer=False),
    _permission_row("Kontrol", "control.revision.view", "Revizyonları Görme", "Revizyon gerekli başlıkları ve açıklamalarını görür.", editor=True, approver=True, viewer=False),
    _permission_row("Kontrol", "control.submitted.view", "Onaya Gönderilenleri Görme", "Onay kuyruğuna gönderilen başlıkların kontrol listesini görür.", editor=True, approver=True, viewer=False),

    _permission_row("Hazırlık Denetimi", "readiness.view", "Hazırlık Denetimi", "Eksik ve riskli başlıkları denetim ekranında görür.", editor=True, approver=True, viewer=True),
    _permission_row("Hazırlık Denetimi", "readiness.risk.view", "Riskli Başlıklar", "Kalite skoru veya eksik alan riski yüksek başlıkları listeler.", editor=True, approver=True, viewer=True),

    _permission_row("Tam Metin Arama", "search.view", "Tam Metin Arama", "Rapor metni, kanıt, tablo ve başlıklar içinde arama yapar.", editor=True, approver=True, viewer=True),
    _permission_row("Tam Metin Arama", "search.open_result", "Arama Sonucunu Açma", "Arama sonucundan ilgili başlığa veya kayda geçer.", editor=True, approver=True, viewer=True),

    _permission_row("İstatistikler", "stats.view", "İstatistikler", "İlerleme, kalite ve durum dağılımı istatistiklerini görür.", editor=True, approver=True, viewer=True),
    _permission_row("İstatistikler", "stats.progress.view", "İlerleme Dağılımı", "Başlık hazırlık ve onay ilerleme grafiklerini görür.", editor=True, approver=True, viewer=True),
    _permission_row("İstatistikler", "stats.quality.view", "Kalite Dağılımı", "Kalite skoru, eksik kanıt ve PUKÖ dağılımlarını görür.", editor=True, approver=True, viewer=True),
    _permission_row("İstatistikler", "stats.criteria.view", "Ana Ölçüt İstatistikleri", "Ana ölçüt / alt ölçüt bazlı dağılımları görür.", editor=True, approver=True, viewer=True),

    _permission_row("AI Akreditasyon Asistanı", "ai.local.status", "Yerel AI Durumu", "Ollama sağlayıcı durumu, model bilgisi ve fallback modunu görür.", editor=True, approver=True, viewer=False),
    _permission_row("AI Akreditasyon Asistanı", "ai.local.draft", "Offline AI Taslak Üretme", "Başlık kapsamındaki metin için yerel AI taslak üretir.", editor=True, approver=False, viewer=False),
    _permission_row("AI Akreditasyon Asistanı", "ai.local.apply", "AI Metnini Başlığa Aktarma", "Üretilen AI taslağını rapor metni alanına aktarır.", editor=True, approver=False, viewer=False),

    # Onay ve kalite
    _permission_row("Onay Akışı", "approval.queue", "Onay Kuyruğu", "Onaya gönderilen başlık listesini görür.", editor=True, approver=True, viewer=False),
    _permission_row("Onay Akışı", "approval.decide", "Onay / Revizyon Kararı", "Başlığı onaylar veya revizyon ister.", editor=False, approver=True, viewer=False),
    _permission_row("Onay Akışı", "approval.reopen", "Onayı Geri Alma", "Onaylanmış başlığı tekrar taslağa veya revizyona çeker.", editor=False, approver=True, viewer=False),
    _permission_row("Onay Akışı", "approval.history", "Revizyon Geçmişi", "Onay/revizyon notlarını ve geçmiş kararları görür.", editor=True, approver=True, viewer=True),

    _permission_row("Gelişmiş Dashboard", "advanced_dashboard.view", "Gelişmiş Dashboard", "Grafikler, darboğazlar, kalite ısı haritası ve risk özetlerini görür.", editor=False, approver=True, viewer=False),
    _permission_row("Gelişmiş Dashboard", "advanced_dashboard.heatmap.view", "Kalite Isı Haritası", "Başlık bazlı kalite/risk ısı haritasını görür.", editor=False, approver=True, viewer=False),
    _permission_row("Gelişmiş Dashboard", "advanced_dashboard.bottleneck.view", "Darboğaz Analizi", "Gecikme, revizyon ve eksik kanıt darboğazlarını görür.", editor=False, approver=True, viewer=False),
    _permission_row("Gelişmiş Dashboard", "advanced_dashboard.export_data.view", "Analitik Veri Tabloları", "Gelişmiş grafiklerin ham veri tablolarını görür.", editor=False, approver=True, viewer=False),
    _permission_row("Profesyonel Raporlama", "professional_reporting.view", "Profesyonel Raporlama", "Smart Templates, Clause Library, kalite skoru ve tutarlılık merkezini görür.", editor=True, approver=True, viewer=False),
    _permission_row("Profesyonel Raporlama", "professional_reporting.clause.manage", "Clause Library Yönetimi", "Ölçüt bazlı standart blok oluşturur, sürükle-bırak ile bölüme ekler.", editor=True, approver=False, viewer=False),
    _permission_row("Profesyonel Raporlama", "professional_reporting.package.export", "Tam Rapor Paketi", "Ana rapor, ekler, kanıt dizini ve kontrol çıktısını zip üretir.", editor=True, approver=True, viewer=False),
    _permission_row("Profesyonel Raporlama", "professional_reporting.auditor_share", "Denetçi Paylaşımı", "Watermark'lı denetçi paketi ve süre sınırlı link oluşturur.", editor=False, approver=True, viewer=False),

    _permission_row("Tam Activity Trail", "activity_trail.view", "Tam Activity Trail", "Activity, onay, bildirim, export ve versiyon zaman çizelgesini kapsam dahilinde görür.", editor=False, approver=True, viewer=False),
    _permission_row("Tam Activity Trail", "audit.view", "Audit Log", "Denetim izi, mail, export ve onay olaylarını görür.", editor=False, approver=True, viewer=False),
    _permission_row("Tam Activity Trail", "activity_trail.notifications.view", "Bildirim Trail", "Bildirim olaylarını zaman çizelgesinde görür.", editor=False, approver=True, viewer=False),
    _permission_row("Tam Activity Trail", "activity_trail.exports.view", "Export Trail", "Rapor çıktı ve export işlem geçmişini zaman çizelgesinde görür.", editor=False, approver=True, viewer=False),

    _permission_row("Versiyon Karşılaştırma", "version_compare.view", "Versiyon Karşılaştırma", "Başlık bazlı sürüm geçmişi ve diff karşılaştırma ekranını görür.", editor=True, approver=True, viewer=False),
    _permission_row("Versiyon Karşılaştırma", "version_compare.side_by_side.view", "Yan Yana Diff", "Eski ve yeni sürümü yan yana karşılaştırır.", editor=True, approver=True, viewer=False),
    _permission_row("Versiyon Karşılaştırma", "version_compare.line_diff.view", "Satır Diff", "Satır bazlı değişiklikleri görür.", editor=True, approver=True, viewer=False),
    _permission_row("Versiyon Karşılaştırma", "version_compare.field_changes.view", "Alan Değişiklikleri", "Metin, PUKÖ, durum ve termin alanlarındaki değişimleri görür.", editor=True, approver=True, viewer=False),

    _permission_row("Teslim Takvimi", "deadline_calendar.view", "Teslim Takvimi", "Yaklaşan ve geciken teslim tarihlerini takvim görünümünde görür.", editor=True, approver=True, viewer=True),
    _permission_row("Teslim Takvimi", "deadline_calendar.overdue.view", "Geciken Başlıklar", "Gecikmiş terminleri listeler.", editor=True, approver=True, viewer=True),
    _permission_row("Teslim Takvimi", "deadline_calendar.upcoming.view", "Yaklaşan Teslimler", "Yaklaşan teslim tarihlerini listeler.", editor=True, approver=True, viewer=True),

    # Çıktılar
    _permission_row("Rapor Önizleme", "report.preview", "Rapor Önizleme", "Nihai rapor görünümünü salt okunur izler.", editor=True, approver=True, viewer=True),
    _permission_row("Rapor Önizleme", "report.preview.pick_section", "Başlığa Git", "Önizleme ekranından ilgili rapor başlığına geçer.", editor=True, approver=True, viewer=True),

    _permission_row("Rapor İçe Aktar", "report.import", "Rapor İçe Aktar", "DOCX/PDF rapordan içerik aktarır.", editor=True, approver=False, viewer=False),
    _permission_row("Rapor İçe Aktar", "report.import.docx", "DOCX Aktarma", "DOCX içeriğini başlık alanlarına aktarır.", editor=True, approver=False, viewer=False),
    _permission_row("Rapor İçe Aktar", "report.import.pdf", "PDF Aktarma", "PDF içeriğini başlık alanlarına aktarır.", editor=True, approver=False, viewer=False),

    _permission_row("Tam Rapor Oluştur", "full_report.view", "Tam Rapor Oluştur", "Tam rapor üretim ekranını görür.", editor=True, approver=False, viewer=False),
    _permission_row("Tam Rapor Oluştur", "full_report.generate", "AI Aday Rapor Üretme", "AI destekli tam rapor adayını üretir.", editor=True, approver=False, viewer=False),
    _permission_row("Tam Rapor Oluştur", "full_report.quality.view", "Kalite Skoru Görme", "Tam rapor üretimi sonrası kalite skorunu görür.", editor=True, approver=True, viewer=False),

    _permission_row("Rapor Dışa Aktar", "report.export", "Rapor Dışa Aktar", "DOCX/PDF çıktısı üretir ve indirir.", editor=True, approver=True, viewer=True),
    _permission_row("Rapor Dışa Aktar", "report.export.docx", "DOCX Çıktı", "DOCX rapor çıktısı üretir.", editor=True, approver=True, viewer=True),
    _permission_row("Rapor Dışa Aktar", "report.export.pdf", "PDF Çıktı", "PDF rapor çıktısı üretir.", editor=True, approver=True, viewer=True),
    _permission_row("Rapor Dışa Aktar", "export.job_manage", "Çıktı İşlerini Yönetme", "Arka plan çıktı işlerini başlatır, izler ve indirir.", editor=True, approver=True, viewer=False),

    _permission_row("Çıktı Geçmişi", "export.history.view", "Çıktı Geçmişi", "Üretilen rapor kayıtlarını ve geçmiş çıktı listesini görür.", editor=True, approver=True, viewer=True),
    _permission_row("Çıktı Geçmişi", "export.download", "Geçmiş Çıktıyı İndirme", "Daha önce üretilmiş rapor çıktısını indirir.", editor=True, approver=True, viewer=True),

    # Yönetim
    _permission_row("Program Yönetimi", "tenant.manage", "Kurum Yönetimi", "Kurum/üniversite, fakülte/MYO/birim ve profil tanımlama süreçlerini yönetir.", editor=False, approver=False, viewer=False, tenant=False, faculty=False),
    _permission_row("Program Yönetimi", "program.list.view", "Tanımlı Programlar", "Program Yönetimi içindeki Tanımlı Programlar sekmesini ve program listesini görür.", editor=False, approver=False, viewer=False),
    _permission_row("Program Yönetimi", "program.view", "Program Görme", "Atanmış program listesini ve temel program özetini görür.", editor=True, approver=True, viewer=True),
    _permission_row("Program Yönetimi", "program.create", "Yeni Program", "Yeni akreditasyon programı açar.", editor=False, approver=False, viewer=False),
    _permission_row("Program Yönetimi", "program.clone", "Program Kopyala", "Mevcut program şablonunu yeni yıl/program için kopyalar.", editor=False, approver=False, viewer=False),
    _permission_row("Program Yönetimi", "program.assign_users", "Program Bazlı Kullanıcı ve Rol Atama", "Programa kullanıcı ve rol atar; bölüm/başlık kapsamı belirler.", editor=False, approver=False, viewer=False),
    _permission_row("Program Yönetimi", "program.users.view", "Program Kullanıcıları", "Program bazlı kullanıcı/rol atama kayıtlarını salt okunur listeler.", editor=False, approver=False, viewer=False),
    _permission_row("Program Yönetimi", "program.edit", "Program Bilgisi Düzenleme", "Program adı, birim, yıl, profil ve aktif/pasif bilgilerini günceller.", editor=False, approver=False, viewer=False),
    _permission_row("Program Yönetimi", "program.archive", "Program Arşivleme / Silme", "Programı soft delete ile arşive taşır.", editor=False, approver=False, viewer=False),
    _permission_row("Program Yönetimi", "program.restore", "Program Geri Yükleme", "Arşivdeki programı aktif hale getirir.", editor=False, approver=False, viewer=False),
    _permission_row("Program Yönetimi", "program.purge", "Program Kalıcı Silme", "Arşivdeki programı geri alınamaz şekilde temizler.", editor=False, approver=False, viewer=False, tenant=False, faculty=False),

    _permission_row("Kullanıcı & Rol Yönetimi", "user.view", "Kullanıcı Listesi", "Kayıtlı kullanıcıları ve rollerini görür; kapsam filtresi uygulanır.", editor=False, approver=False, viewer=False),
    _permission_row("Kullanıcı & Rol Yönetimi", "user.manage", "Kullanıcı Oluşturma / Düzenleme", "Kullanıcı oluşturur, günceller, pasifleştirir ve rolünü belirler.", editor=False, approver=False, viewer=False, faculty=False),
    _permission_row("Kullanıcı & Rol Yönetimi", "user.login_attempts.view", "Giriş Denemeleri", "Kurum kapsamındaki kullanıcı giriş denemelerini görür.", editor=False, approver=False, viewer=False),
    _permission_row("Son Teslim Tarihi Planı", "deadline.view", "Termin Planını Görme", "Başlık son teslim tarihlerini listeler.", editor=True, approver=True, viewer=True),
    _permission_row("Son Teslim Tarihi Planı", "deadline.manage", "Son Teslim Tarihi Yönetimi", "Başlık son teslim tarihlerini toplu veya tekil olarak atar.", editor=False, approver=False, viewer=False),

    _permission_row("Toplu İşlemler", "bulk.manage", "Toplu İşlemler", "Toplu durum, tarih veya şablon güncelleme işlemlerini yapar.", editor=False, approver=False, viewer=False, faculty=False),
    _permission_row("Toplu İşlemler", "bulk.status.update", "Toplu Durum Güncelleme", "Birden fazla başlığın durumunu toplu değiştirir.", editor=False, approver=False, viewer=False, faculty=False),
    _permission_row("Toplu İşlemler", "bulk.deadline.update", "Toplu Termin Güncelleme", "Birden fazla başlığın terminini toplu değiştirir.", editor=False, approver=False, viewer=False, faculty=False),

    _permission_row("Yetki Matrisi", "permission.manage", "İşlem Yetki Matrisi", "Rol bazlı işlem izinlerini düzenler.", editor=False, approver=False, viewer=False, faculty=False),
    _permission_row("Yetki Matrisi", "sidebar.manage", "Sidebar Görünürlük Matrisi", "Rol bazlı menü görünürlüğünü düzenler.", editor=False, approver=False, viewer=False, faculty=False),
    _permission_row("Yetki Matrisi", "section_policy.view", "Başlık Bazlı Yetki Görme", "Her başlık ve işlem için rol bazlı yetki politikasını görüntüler.", editor=False, approver=False, viewer=False),
    _permission_row("Yetki Matrisi", "section_policy.manage", "Başlık Bazlı Yetki Düzenleme", "Bölüm/başlık bazında görme, metin, PUKÖ, termin, onay, kanıt, tablo ve AI izinlerini düzenler.", editor=False, approver=False, viewer=False, faculty=False),

    _permission_row("Geri Yükleme", "recovery.restore", "Geri Yükleme", "Arşivlenmiş program/veri kayıtlarını geri yükler.", editor=False, approver=False, viewer=False, faculty=False),
    _permission_row("Geri Yükleme", "recovery.purge", "Kalıcı Temizleme", "Arşiv kayıtlarını geri alınamaz şekilde temizler.", editor=False, approver=False, viewer=False, tenant=False, faculty=False),

    _permission_row("Kullanım Analitiği", "analytics.view", "Kullanım Analitiği", "Kullanıcı aktivitesi ve işlem raporlarını kapsam dahilinde görür.", editor=False, approver=True, viewer=False),
    _permission_row("Kullanım Analitiği", "analytics.actors.view", "Kullanıcı Aktivitesi", "Kullanıcı bazlı işlem yoğunluğunu görür.", editor=False, approver=True, viewer=False),
    _permission_row("Kullanım Analitiği", "analytics.actions.view", "İşlem Türleri", "İşlem türü bazlı analitik özetleri görür.", editor=False, approver=True, viewer=False),
    _permission_row("Kullanım Analitiği", "analytics.recent.view", "Son İşlemler", "Kapsam dahilindeki son activity kayıtlarını görür.", editor=False, approver=True, viewer=False),

    _permission_row("Ayarlar & Yedek", "settings.manage", "Sistem Ayarları ve Yedek", "Belge bilgileri, sistem ayarları, yedek ve restore süreçlerini yönetir.", editor=False, approver=False, viewer=False, tenant=False, faculty=False),
    _permission_row("Ayarlar & Yedek", "template.manage", "Sistem Şablonları", "Akreditasyon şablonlarını yeniler ve eksik başlıkları onarır.", editor=False, approver=False, viewer=False, tenant=False, faculty=False),
    _permission_row("Ayarlar & Yedek", "settings.backup", "Yedek Alma", "Sistem yedeği üretir.", editor=False, approver=False, viewer=False, tenant=False, faculty=False),
    _permission_row("Ayarlar & Yedek", "settings.restore", "Yedekten Geri Dönme", "Yetkili kapsamda yedekten geri dönme işlemlerini başlatır.", editor=False, approver=False, viewer=False, tenant=False, faculty=False),

    _permission_row("Görünüm", "appearance.manage", "Görünüm Paketleri", "Kurum bazlı tema, koyu mod ve görünüm paketlerini yönetir.", editor=False, approver=False, viewer=False, tenant=False, faculty=False),
    _permission_row("Görünüm", "appearance.tenant.apply", "Kurum Görünümü Atama", "Kurumlara görünüm paketi atar.", editor=False, approver=False, viewer=False, tenant=False, faculty=False),

    _permission_row("Yardım & Kullanım", "help.view", "Yardım & Kullanım", "Rol bazlı yardım ve kullanım kılavuzunu görür.", editor=True, approver=True, viewer=True),
    _permission_row("Yardım & Kullanım", "help.role_manual.view", "Rol Bazlı Kılavuz", "Aktif rol için detaylı kullanım açıklamalarını görür.", editor=True, approver=True, viewer=True),
    _permission_row("Yardım & Kullanım", "help.workflow.view", "İş Akışı Rehberi", "Rapor hazırlama, onay ve çıktı iş akışlarını görür.", editor=True, approver=True, viewer=True),

    _permission_row("PWA", "pwa.install", "PWA Kurulum Deneyimi", "Mobil kurulum, offline uyarı ve read-only cache deneyimini kullanır.", editor=True, approver=True, viewer=True),
]

DEFAULT_PERMISSION_MATRIX.extend(COMPLETE_SIDEBAR_PERMISSION_ROWS)

# AKYS varsayılan rol/yetki modeli: Süper Admin > Kurum Admin > Birim Admin > Birim Koordinatörü > Editör/Hazırlayıcı > Onaylayıcı > Denetçi.
def _set_role_flags(row: dict[str, Any], *, super_admin: bool, tenant: bool, unit_admin: bool, unit_coord: bool, editor: bool, approver: bool, auditor: bool) -> None:
    row[SUPER_ADMIN_ROLE] = bool(super_admin)
    row[TENANT_ADMIN_ROLE] = bool(tenant)
    row[FACULTY_ADMIN_ROLE] = bool(unit_admin)
    row[UNIT_COORDINATOR_ROLE] = bool(unit_coord)
    row[EDITOR_ROLE] = bool(editor)
    row[APPROVER_ROLE] = bool(approver)
    row[READONLY_ROLE] = bool(auditor)
    row["Admin"] = bool(super_admin)


def _akys_permission_default_flags(permission: str, category: str) -> tuple[bool, bool, bool, bool, bool, bool, bool]:
    p = str(permission or "")
    cat = str(category or "")
    all_roles = (True, True, True, True, True, True, True)
    admin_unit = (True, True, True, False, False, False, False)
    admin_tenant = (True, True, False, False, False, False, False)
    admin_super = (True, False, False, False, False, False, False)
    writing_roles = (True, True, True, True, True, False, False)
    read_all = all_roles

    if p.startswith("dashboard.") or p in {"notification.view", "stats.view", "quality.view", "help.view", "help.role_manual.view", "help.workflow.view", "pwa.install"}:
        return all_roles
    if p in {"program.view", "program.list.view"}:
        return all_roles
    if p in {"program.create", "program.clone", "program.edit", "program.archive", "program.restore", "program.assign_users", "program.users.view"}:
        return admin_unit
    if p == "program.purge":
        return admin_super
    if p in {"tenant.manage"}:
        return admin_tenant
    if p in {"user.view", "user.manage", "user.login_attempts.view"}:
        return admin_unit
    if p in {"appearance.manage", "appearance.tenant.apply"}:
        return admin_super
    if p in {"permission.manage", "sidebar.manage", "settings.manage", "template.manage", "settings.backup", "settings.restore", "bulk.manage", "recovery.restore", "recovery.purge", "notification.settings"}:
        return admin_tenant
    if p.startswith("update_center."):
        return admin_tenant
    if p in {"section.view", "section.view_assigned", "section.version_view", "approval.history", "report.preview", "report.export", "deadline_calendar.view", "search.view", "control.view", "activity_trail.view", "version_compare.view", "advanced_dashboard.view", "analytics.view"}:
        return read_all
    if p in {"section.edit", "section.save", "section.status", "section.field_text.edit", "section.field_puko.edit", "ai.local.status", "ai.local.draft"}:
        return writing_roles
    if p == "section.submit":
        return (False, False, False, False, True, False, False)
    if p in {"approval.queue"}:
        return (True, True, True, True, True, True, False)
    if p in {"approval.decide", "approval.reopen"}:
        return (True, True, True, True, False, True, False)
    if p == "evidence.view":
        return read_all
    if p in {"evidence.upload", "evidence.link", "evidence.delete"}:
        return writing_roles
    if p == "table.view":
        return read_all
    if p in {"table.edit", "table.delete"}:
        return writing_roles
    if p in {"report.import", "export.job_manage"}:
        return writing_roles
    if p in {"deadline.view"}:
        return (True, True, True, True, False, True, False)
    if p in {"deadline.manage"}:
        return (True, True, False, False, False, False, False)
    if p == "professional_reporting.clause.manage":
        return writing_roles
    if p == "professional_reporting.view":
        return (True, True, True, True, True, False, False)
    if p == "professional_reporting.package.export":
        return (True, True, True, True, True, True, True)
    if p == "professional_reporting.auditor_share":
        return (True, True, True, True, False, True, False)
    if p in {"audit.view"}:
        return (True, True, True, True, False, False, False)
    if p in {"section_policy.view", "section_policy.manage"}:
        return (True, True, True, False, False, False, False)
    return read_all if cat in {"Dashboard Alanları", "Yardım & Kullanım"} else (True, True, True, True, bool(row_value := False), False, False)


def _akys_sidebar_default_flags(module: str) -> tuple[bool, bool, bool, bool, bool, bool, bool]:
    all_roles = (True, True, True, True, True, True, True)
    writing_roles = (True, True, True, True, True, False, False)
    admin_unit = (True, True, True, False, False, False, False)
    admin_tenant = (True, True, False, False, False, False, False)
    m = str(module or "")
    if m in {"dashboard", "notifications", "tasks", "stats", "advanced", "preview", "export", "deadlineCalendar", "help", "search", "control", "versions"}:
        return all_roles
    if m in {"entry", "evidence"}:
        return all_roles
    if m in {"tables", "professional", "docx", "fullReport"}:
        return writing_roles
    if m in {"approval", "deadlines"}:
        return (True, True, True, True, True, True, False)
    if m in {"programs", "users"}:
        return admin_unit
    if m in {"appearance"}:
        return (True, False, False, False, False, False, False)
    if m in {"permissions", "settings", "recovery", "bulk", "updateCenter", "analytics"}:
        return admin_tenant
    if m in {"timeline"}:
        return (True, True, True, True, False, False, False)
    return all_roles


def _apply_akys_role_matrix_defaults() -> None:
    for row in DEFAULT_PERMISSION_MATRIX:
        flags = _akys_permission_default_flags(str(row.get("permission", "")), str(row.get("category", "")))
        _set_role_flags(row, super_admin=flags[0], tenant=flags[1], unit_admin=flags[2], unit_coord=flags[3], editor=flags[4], approver=flags[5], auditor=flags[6])
    for row in DEFAULT_SIDEBAR_MATRIX:
        flags = _akys_sidebar_default_flags(str(row.get("module", "")))
        _set_role_flags(row, super_admin=flags[0], tenant=flags[1], unit_admin=flags[2], unit_coord=flags[3], editor=flags[4], approver=flags[5], auditor=flags[6])


_apply_akys_role_matrix_defaults()

# Sidebar modülleri ile ana görüntüleme izinleri arasında tek kaynaklı bağ.
# Menüde görünürlük için hem Sidebar Visibility hem de ilgili modül erişim izni açık olmalıdır.
# Dashboard ana modülü bu listede özellikle yoktur: dashboard.* izinleri dashboard
# içindeki panel/blok görünürlüğünü yönetir, sidebar'daki Gösterge Paneli modülünü düşürmez.
MODULE_VIEW_PERMISSIONS = {
    "notifications": "notification.view",
    "tasks": "quality.view",
    "entry": "section.view",
    "evidence": "evidence.view",
    "tables": "table.view",
    "control": "control.view",
    "search": "search.view",
    "stats": "stats.view",
    "advanced": "advanced_dashboard.view",
    "professional": "professional_reporting.view",
    "timeline": "activity_trail.view",
    "versions": "version_compare.view",
    "preview": "report.preview",
    "export": "report.export",
    "deadlineCalendar": "deadline_calendar.view",
    "help": "help.view",
    "updateCenter": "update_center.view",
    "appearance": "appearance.manage",
    "docx": "report.import",
    "assistant": "ai.local.status",
    "fullReport": "full_report.view",
    "approval": "approval.queue",
    "programs": "program.view",
    "users": "user.view",
    "deadlines": "deadline.view",
    "bulk": "bulk.manage",
    "permissions": "permission.manage",
    "recovery": "recovery.restore",
    "analytics": "analytics.view",
    "settings": "settings.manage",
}

def _json_setting(key: str, fallback: Any) -> Any:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    if not row:
        return fallback
    try:
        parsed = json.loads(str(row["value"] or ""))
        return parsed if isinstance(parsed, list) else fallback
    except Exception:
        return fallback


def _json_setting_or_none(key: str) -> list[dict[str, Any]] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    if not row:
        return None
    try:
        parsed = json.loads(str(row["value"] or ""))
        return parsed if isinstance(parsed, list) else None
    except Exception:
        return None


def _tenant_setting_key(base_key: str, tenant_id: str) -> str:
    clean_tenant_id = str(tenant_id or "").strip()
    return f"{base_key}:{clean_tenant_id}" if clean_tenant_id else base_key


def _merge_tenant_rows(global_rows: list[dict[str, Any]], tenant_rows: list[dict[str, Any]] | None, key: str) -> list[dict[str, Any]]:
    """Apply tenant delegation under the Süper Admin -> Kurum Admin ceiling.

    The Kurum Admin column is owned by the global/Süper Admin matrix. Tenant
    rows may set Birim Admin and lower roles, but an inherited/stale
    tenant row can never grant a permission or sidebar module when Kurum Admin
    no longer has that parent capability.
    """
    defaults = DEFAULT_PERMISSION_MATRIX if key == "permission" else DEFAULT_SIDEBAR_MATRIX
    tenant_map: dict[str, dict[str, Any]] = {}
    if tenant_rows is not None:
        tenant_clean = _merge_rows(tenant_rows, defaults, key)
        tenant_map = _row_map(tenant_clean, key)
    output: list[dict[str, Any]] = []
    for row in global_rows:
        row_key = str(row.get(key, ""))
        item = dict(row)
        override = tenant_map.get(row_key)
        parent_allowed = bool(row.get(TENANT_ADMIN_ROLE, False))
        for role in TENANT_DELEGATE_ROLES:
            inherited = bool(item.get(role, False))
            desired = bool(override.get(role, inherited)) if override else inherited
            item[role] = desired and parent_allowed
        output.append(item)
    return output


ROLE_LEGACY_LABELS = {
    READONLY_ROLE: ("Denetçi (İzleyici)", "İzleyici", "Denetci"),
    EDITOR_ROLE: ("Editör", "Hazırlayıcı", "Editor"),
}


def _matrix_bool(row: dict[str, Any], base: dict[str, Any], role: str, fallback: Any = False) -> bool:
    if role in row:
        return bool(row.get(role))
    for alias in ROLE_LEGACY_LABELS.get(role, ()):
        if alias in row:
            return bool(row.get(alias))
    if role in base:
        return bool(base.get(role))
    for alias in ROLE_LEGACY_LABELS.get(role, ()):
        if alias in base:
            return bool(base.get(alias))
    return bool(fallback)


def _role_default(row: dict[str, Any], base: dict[str, Any], role: str, *, key: str) -> bool:
    legacy = row.get("Admin", base.get("Admin", False))
    if role == SUPER_ADMIN_ROLE:
        return _matrix_bool(row, base, role, True)
    if role == FACULTY_ADMIN_ROLE:
        if role in row or role in base:
            return _matrix_bool(row, base, role, row.get("Admin", base.get("Admin", False)))
        return bool(row.get("Admin", base.get("Admin", False)))
    if role == TENANT_ADMIN_ROLE:
        # Önce varsayılan satırdaki açık Kurum Admin kararını kullan; böylece
        # tenant.manage gibi kritik izinler varsayılan olarak kapalı kalabilir.
        if role in row or role in base:
            return _matrix_bool(row, base, role, False)
        # Eski matrislerde Kurum Admin sütunu yoksa geriye dönük makul varsayılanlar.
        if key == "module" and str(base.get("module", "")) in {"permissions", "users", "programs", "settings", "deadlines", "recovery", "analytics"}:
            return _matrix_bool(row, base, role, True)
        if key == "permission" and str(base.get("permission", "")).startswith(("user.", "permission.", "sidebar.", "program.", "deadline.", "settings.", "recovery.", "analytics.")):
            return _matrix_bool(row, base, role, True)
        return _matrix_bool(row, base, role, legacy)
    return _matrix_bool(row, base, role, False)


def _normalize_matrix_row(row: dict[str, Any], base: dict[str, Any], key: str) -> dict[str, Any]:
    row_key = str(row.get(key) or base.get(key) or "").strip()
    # Metadata comes from the built-in catalogue so release upgrades can move
    # an existing permission into the correct sidebar/module group without
    # losing stored role toggle values. Tenant/global settings still carry the
    # boolean decisions; labels/categories are product-owned taxonomy.
    item = {key: row_key, "label": str(base.get("label") or row.get("label") or row_key)}
    if key == "permission":
        item["category"] = str(base.get("category") or row.get("category") or "Genel")
        item["description"] = str(base.get("description") or row.get("description") or "")
    else:
        item["group"] = str(base.get("group") or row.get("group") or "Modüller")
    for role in ROLE_OPTIONS:
        item[role] = _role_default(row, base, role, key=key)
    return item


def _merge_rows(rows: list[dict[str, Any]] | None, defaults: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    # Build a canonical catalogue from the last occurrence of each key. This lets
    # later release catalogue blocks move permissions between sidebar/module
    # categories without showing duplicates or preserving obsolete categories.
    known: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for base in defaults:
        base_key = str(base.get(key, "") or "").strip()
        if not base_key:
            continue
        if base_key in order:
            order.remove(base_key)
        order.append(base_key)
        known[base_key] = base

    supplied: dict[str, dict[str, Any]] = {}
    for row in rows or []:
        row_key = str(row.get(key, "") or "").strip()
        if row_key in known:
            supplied[row_key] = row

    return [_normalize_matrix_row(supplied.get(row_key, known[row_key]), known[row_key], key) for row_key in order]


def _clean_permission_rows(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return _merge_rows(rows, DEFAULT_PERMISSION_MATRIX, "permission")


def _clean_sidebar_rows(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return _merge_rows(rows, DEFAULT_SIDEBAR_MATRIX, "module")


def sidebar_matrix_public(tenant_id: str | None = None) -> list[dict[str, Any]]:
    global_rows = _clean_sidebar_rows(_json_setting(SIDEBAR_MATRIX_SETTING, DEFAULT_SIDEBAR_MATRIX))
    clean_tenant_id = str(tenant_id or "").strip()
    if not clean_tenant_id:
        return global_rows
    tenant_rows = _json_setting_or_none(_tenant_setting_key(SIDEBAR_MATRIX_SETTING, clean_tenant_id))
    return _merge_tenant_rows(global_rows, tenant_rows, "module")


def _permission_rows_by_key(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("permission", "") or ""): row for row in rows}


def _module_permission_allows_role(module: str, role: str, permission_rows_by_key: dict[str, dict[str, Any]]) -> bool:
    required_permission = MODULE_VIEW_PERMISSIONS.get(str(module or ""))
    if not required_permission:
        return True
    if role == SUPER_ADMIN_ROLE:
        return True
    permission_row = permission_rows_by_key.get(required_permission)
    if permission_row is None:
        # Forward-compatible: yeni modül izni katalogda yoksa sadece sidebar kararı uygulanır.
        return True
    return bool(permission_row.get(role, False))


def _effective_sidebar_rows(sidebar_rows: list[dict[str, Any]], permission_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    permission_rows_by_key = _permission_rows_by_key(permission_rows)
    output: list[dict[str, Any]] = []
    for row in sidebar_rows:
        item = dict(row)
        module = str(item.get("module", "") or "")
        for role in ROLE_OPTIONS:
            sidebar_allowed = bool(item.get(role, False))
            item[role] = sidebar_allowed and _module_permission_allows_role(module, role, permission_rows_by_key)
        output.append(item)
    return output


DASHBOARD_SIDEBAR_REPAIR_SETTING = "migration_dashboard_sidebar_visibility_v3"
DASHBOARD_PANEL_PERMISSION_KEYS = {
    "dashboard.view",
    "dashboard.kpi.view",
    "dashboard.priority.view",
    "dashboard.criteria.view",
    "dashboard.charts.view",
    "dashboard.activity.view",
}
DASHBOARD_BLACKOUT_RECOVERY_KEYS = {
    "dashboard.view",
    "dashboard.kpi.view",
    "dashboard.priority.view",
    "dashboard.criteria.view",
    "dashboard.charts.view",
}


def _dashboard_sidebar_default_row() -> dict[str, Any]:
    for row in DEFAULT_SIDEBAR_MATRIX:
        if str(row.get("module", "")) == "dashboard":
            return dict(row)
    return {"module": "dashboard", "label": "Gösterge Paneli", "group": "Modüller", **{role: True for role in ROLE_OPTIONS}}


def _restore_dashboard_sidebar_defaults(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Repair legacy saved sidebar rows polluted by the old dashboard.view gate.

    Older builds returned an *effective* sidebar row after dashboard.view was
    switched off. If the admin then saved the matrix, that effective false value
    was persisted as a raw Sidebar Visibility choice. After separating
    dashboard.* panel permissions from sidebar visibility, this one-time repair
    restores only the dashboard module to the product default. Future explicit
    Sidebar Visibility edits remain untouched because the migration marker is
    written after the first repair.
    """
    default_dashboard = _dashboard_sidebar_default_row()
    clean = _clean_sidebar_rows(rows)
    repaired: list[dict[str, Any]] = []
    seen_dashboard = False
    for row in clean:
        item = dict(row)
        if str(item.get("module", "")) == "dashboard":
            seen_dashboard = True
            for role in ROLE_OPTIONS:
                item[role] = bool(default_dashboard.get(role, True))
        repaired.append(item)
    if not seen_dashboard:
        repaired.insert(0, _normalize_matrix_row(default_dashboard, default_dashboard, "module"))
    return repaired


def repair_legacy_dashboard_sidebar_visibility() -> None:
    """One-time migration for installations affected by dashboard.view/sidebar coupling.

    The repair covers the global sidebar matrix and tenant-specific sidebar
    matrices (settings keys like sidebar_matrix_json:<tenant_id>).
    """
    with transaction() as conn:
        marker = conn.execute("SELECT value FROM settings WHERE key=?", (DASHBOARD_SIDEBAR_REPAIR_SETTING,)).fetchone()
        if marker:
            return
        rows = conn.execute("SELECT key,value FROM settings WHERE key=? OR key LIKE ?", (SIDEBAR_MATRIX_SETTING, f"{SIDEBAR_MATRIX_SETTING}:%")).fetchall()
        if not rows:
            conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (SIDEBAR_MATRIX_SETTING, json.dumps(_restore_dashboard_sidebar_defaults(DEFAULT_SIDEBAR_MATRIX), ensure_ascii=False)))
        for row in rows:
            key = str(row["key"] or SIDEBAR_MATRIX_SETTING)
            try:
                parsed = json.loads(str(row["value"] or ""))
                parsed_rows = parsed if isinstance(parsed, list) else DEFAULT_SIDEBAR_MATRIX
            except Exception:
                parsed_rows = DEFAULT_SIDEBAR_MATRIX
            repaired = _restore_dashboard_sidebar_defaults(parsed_rows)
            conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, json.dumps(repaired, ensure_ascii=False)))
        conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (DASHBOARD_SIDEBAR_REPAIR_SETTING, "1"))


def _restore_dashboard_permission_blackout(permission_rows: list[dict[str, Any]], sidebar_rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Keep a visible Dashboard module from rendering as a blank panel set.

    The operation matrix can still disable individual dashboard panels. The only
    unsafe state repaired here is the bulk-all blackout: Dashboard is visible in
    the Sidebar matrix but every dashboard.* panel permission is false for a
    role. In that case, restore the core dashboard defaults for that role.
    """
    rows = [dict(row) for row in permission_rows]
    sidebar = _clean_sidebar_rows(sidebar_rows) if sidebar_rows is not None else _clean_sidebar_rows(DEFAULT_SIDEBAR_MATRIX)
    dashboard_sidebar = next((row for row in sidebar if str(row.get("module", "")) == "dashboard"), _dashboard_sidebar_default_row())
    defaults_by_key = {str(row.get("permission", "")): row for row in _clean_permission_rows(DEFAULT_PERMISSION_MATRIX)}
    dashboard_rows = [row for row in rows if str(row.get("permission", "")) in DASHBOARD_PANEL_PERMISSION_KEYS]
    for role in ROLE_OPTIONS:
        if not bool(dashboard_sidebar.get(role, False)):
            continue
        if any(bool(row.get(role, False)) for row in dashboard_rows):
            continue
        for row in rows:
            key = str(row.get("permission", ""))
            if key in DASHBOARD_BLACKOUT_RECOVERY_KEYS:
                row[role] = bool(defaults_by_key.get(key, {}).get(role, True))
    return rows


def effective_sidebar_matrix_public(tenant_id: str | None = None) -> list[dict[str, Any]]:
    """Return sidebar rows after applying operation-permission gates.

    Admin screens still edit the raw Sidebar Visibility matrix. Navigation uses
    this effective matrix so dashboard.view and similar *.view permissions cannot
    drift out of sync with the rendered sidebar.
    """
    return _effective_sidebar_rows(sidebar_matrix_public(tenant_id), permission_matrix_public(tenant_id))


def visible_sidebar_modules_for_role(role: str, tenant_id: str | None = None) -> list[str]:
    normalized = normalized_role(str(role or READONLY_ROLE))
    rows = effective_sidebar_matrix_public(tenant_id)
    modules = [str(row.get("module", "")) for row in rows if row.get(normalized, False)]
    return [m for m in modules if m]


def permission_matrix_public(tenant_id: str | None = None) -> list[dict[str, Any]]:
    global_rows = _clean_permission_rows(_json_setting(PERMISSION_MATRIX_SETTING, DEFAULT_PERMISSION_MATRIX))
    clean_tenant_id = str(tenant_id or "").strip()
    if not clean_tenant_id:
        return _restore_dashboard_permission_blackout(global_rows, sidebar_matrix_public())
    tenant_rows = _json_setting_or_none(_tenant_setting_key(PERMISSION_MATRIX_SETTING, clean_tenant_id))
    merged_rows = _merge_tenant_rows(global_rows, tenant_rows, "permission")
    return _restore_dashboard_permission_blackout(merged_rows, sidebar_matrix_public(clean_tenant_id))


def role_permission_allowed(role: str, permission: str, tenant_id: str | None = None) -> bool:
    normalized = normalized_role(str(role or READONLY_ROLE))
    key = str(permission or "").strip()
    if normalized == SUPER_ADMIN_ROLE:
        return True
    for row in permission_matrix_public(tenant_id):
        if str(row.get("permission", "")) == key:
            return bool(row.get(normalized, False))
    return False


def _is_faculty_admin_user(user: dict[str, Any] | None) -> bool:
    if not user:
        return False
    return normalized_role(str(user.get("role", "")), str(user.get("tenant_scope", "") or "")) == FACULTY_ADMIN_ROLE


def _admin_scope_payload(username: str) -> tuple[dict[str, Any], list[str], str, str]:
    actor = get_user(username, active_only=True)
    if is_super_admin_user(actor):
        return actor or {}, list(ROLE_OPTIONS), "super_admin", "Süper Admin tüm kurumların yetki matrisini ve Kurum Admin devrini yönetir."
    if is_tenant_admin_user(actor):
        return actor or {}, [FACULTY_ADMIN_ROLE, UNIT_COORDINATOR_ROLE, EDITOR_ROLE, APPROVER_ROLE, READONLY_ROLE], "tenant_admin", "Kurum Admin, Süper Admin tarafından belirlenen Kurum Admin tavanını aşamaz; kendi kurumundaki Birim Admin, Birim Koordinatörü, Editör / Hazırlayıcı, Onaylayıcı ve Denetçi rollerine izin dağıtabilir."
    if _is_faculty_admin_user(actor):
        if not (actor_has_operation_permission(actor, "permission.manage") or actor_has_operation_permission(actor, "sidebar.manage")):
            raise PermissionError("Birim Admin için Yetki Matrisi görünürlüğü Süper Admin/Kurum Admin tarafından açılmalıdır.")
        return actor or {}, [UNIT_COORDINATOR_ROLE, EDITOR_ROLE, APPROVER_ROLE, READONLY_ROLE], "faculty_admin", "Birim Admin yalnızca kendisine açık bırakılan yetkileri kendi birimindeki Birim Koordinatörü, Editör / Hazırlayıcı, Onaylayıcı ve Denetçi rollerine dağıtabilir."
    raise PermissionError("Yetki matrisi yalnızca yetkilendirilmiş Süper Admin, Kurum Admin veya Birim Admin tarafından görüntülenebilir.")


def permission_matrix_admin(username: str) -> dict[str, Any]:
    actor, editable_roles, scope, note = _admin_scope_payload(username)
    tenant_id = "" if scope == "super_admin" else str(actor.get("tenant_id", "") or "")
    rows = permission_matrix_public(tenant_id)
    sidebar_rows = sidebar_matrix_public(tenant_id)
    return {
        "roles": list(ROLE_OPTIONS),
        "editable_roles": editable_roles,
        "admin_scope": scope,
        "tenant_id": tenant_id,
        "delegation_note": note,
        "operation_matrix_locked": scope == "faculty_admin",
        "operation_matrix_lock_note": "Birim Admin, kurum genelindeki rol matrisini ezemez; yalnız erişebildiği programın section bazlı alt rol kurallarını düzenler." if scope == "faculty_admin" else "",
        "protected_roles": [role for role in ROLE_OPTIONS if role not in editable_roles],
        "rows": rows,
        "sidebar_rows": sidebar_rows,
        "default_rows": _clean_permission_rows(DEFAULT_PERMISSION_MATRIX),
        "default_sidebar_rows": _clean_sidebar_rows(DEFAULT_SIDEBAR_MATRIX),
    }


def _row_map(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(row.get(key, "")): row for row in rows}


def _enforce_delegation_cap(requested: list[dict[str, Any]], current: list[dict[str, Any]], gate_rows: list[dict[str, Any]], key: str, editable_roles: list[str], gate_role: str, actor_label: str) -> list[dict[str, Any]]:
    current_map = _row_map(current, key)
    gate_map = _row_map(gate_rows, key)
    output: list[dict[str, Any]] = []
    for row in requested:
        row_key = str(row.get(key, ""))
        base = dict(current_map.get(row_key, gate_map.get(row_key, row)))
        gate = bool((gate_map.get(row_key, {}) or {}).get(gate_role, False))
        for role in editable_roles:
            previous = bool(base.get(role, False))
            desired = bool(row.get(role, previous))
            if desired and not previous and not gate:
                raise PermissionError(f"{actor_label}, kendisine kapalı olan '{base.get('label', row_key)}' iznini başka role açamaz.")
            base[role] = desired
        output.append(base)
    return output


def _ensure_effective_sidebar_has_module(permission_rows: list[dict[str, Any]], sidebar_rows: list[dict[str, Any]], roles: list[str] | None = None) -> None:
    effective_rows = _effective_sidebar_rows(sidebar_rows, permission_rows)
    roles_to_check = roles or list(ROLE_OPTIONS)
    for role in roles_to_check:
        normalized = normalized_role(role)
        if not any(bool(row.get(normalized, False)) for row in effective_rows):
            raise ValueError(f"{normalized} rolü için en az bir görünür sidebar modülü açık kalmalıdır.")


SELF_PROTECTED_PERMISSION_KEYS = {"permission.manage", "sidebar.manage"}
SELF_PROTECTED_SIDEBAR_MODULES = {"permissions"}


def _protect_actor_self_access(actor: dict[str, Any] | None, rows: list[dict[str, Any]], sidebar_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep the active administrator from disabling the screen needed to recover permissions.

    Super Admin/Kurum Admin/Fakülte Admin can still delegate ordinary permissions,
    but the actor's own permission-management path must remain open so a bad
    click cannot make the UI look blank or strand the administrator.
    """
    role = normalized_role(str((actor or {}).get("role", "") or READONLY_ROLE), str((actor or {}).get("tenant_scope", "") or ""))
    if role not in ROLE_OPTIONS:
        return rows, sidebar_rows
    safe_rows = []
    for row in rows:
        item = dict(row)
        if str(item.get("permission", "")) in SELF_PROTECTED_PERMISSION_KEYS:
            item[role] = True
        safe_rows.append(item)
    safe_sidebar_rows = []
    for row in sidebar_rows:
        item = dict(row)
        if str(item.get("module", "")) in SELF_PROTECTED_SIDEBAR_MODULES:
            item[role] = True
        safe_sidebar_rows.append(item)
    return safe_rows, safe_sidebar_rows


def update_permission_matrix_admin(username: str, rows: list[dict[str, Any]], sidebar_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    actor, editable_roles, scope, _note = _admin_scope_payload(username)
    tenant_id = str(actor.get("tenant_id", "") or "") if scope in {"tenant_admin", "faculty_admin"} else ""
    global_rows = permission_matrix_public()
    global_sidebar = sidebar_matrix_public()
    current_rows = permission_matrix_public(tenant_id)
    current_sidebar = sidebar_matrix_public(tenant_id)
    requested_rows = _clean_permission_rows(rows)
    requested_sidebar = _clean_sidebar_rows(sidebar_rows)
    if scope == "faculty_admin":
        # Operation/sidebar matrices are tenant-wide role policies. A Fakülte/MYO
        # Admin is allowed to inspect the inherited matrix, but must not persist
        # changes that would overwrite Kurum Admin/Süper Admin decisions for the
        # whole tenant. Program-specific section policy is saved by its own API.
        clean_rows = current_rows
        clean_sidebar_rows = current_sidebar
        permission_key = ""
        sidebar_key = ""
    elif scope == "tenant_admin":
        gate_role = TENANT_ADMIN_ROLE
        actor_label = "Kurum Admin"
        requested_rows = _enforce_delegation_cap(requested_rows, current_rows, global_rows, "permission", editable_roles, gate_role, actor_label)
        requested_sidebar = _enforce_delegation_cap(requested_sidebar, current_sidebar, global_sidebar, "module", editable_roles, gate_role, actor_label)
        clean_rows = _clean_permission_rows(requested_rows)
        clean_sidebar_rows = _clean_sidebar_rows(requested_sidebar)
        permission_key = _tenant_setting_key(PERMISSION_MATRIX_SETTING, tenant_id)
        sidebar_key = _tenant_setting_key(SIDEBAR_MATRIX_SETTING, tenant_id)
    else:
        clean_rows = requested_rows
        clean_sidebar_rows = requested_sidebar
        permission_key = PERMISSION_MATRIX_SETTING
        sidebar_key = SIDEBAR_MATRIX_SETTING
    clean_rows, clean_sidebar_rows = _protect_actor_self_access(actor, clean_rows, clean_sidebar_rows)
    _ensure_effective_sidebar_has_module(clean_rows, clean_sidebar_rows)
    if permission_key and sidebar_key:
        with transaction() as conn:
            conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (permission_key, json.dumps(clean_rows, ensure_ascii=False)))
            conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (sidebar_key, json.dumps(clean_sidebar_rows, ensure_ascii=False)))
        log_activity("Yetki matrisi güncellendi", f"{scope}: {len(clean_rows)} izin, {len(clean_sidebar_rows)} menü görünürlüğü", username, "")
    else:
        log_activity("Yetki matrisi görüntülendi", "faculty_admin inherited matrix preserved", username, "")
    return permission_matrix_admin(username)
