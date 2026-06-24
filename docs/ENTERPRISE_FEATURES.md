# Enterprise Özellik Paketi

Bu pakette demo kurulum sihirbazı ve antivirüs hariç şu ürünleşme özellikleri eklenmiştir:

- Soft Delete + Recovery
- Tam Activity Trail
- RBAC / Permission Matrix UI
- Export Job Progress
- Version Diff Viewer
- Advanced Reporting Dashboard
- E-posta + uygulama içi bildirim merkezi
- Mobile responsive + PWA manifest/service worker
- Dark mode
- Backup encryption scripts
- Analytics & Usage Reports

SSO/LDAP ve gerçek multi-tenant izolasyon için güvenli canlı geçiş ayrı faz olarak planlanmalıdır; mevcut program bazlı yetkilendirme kurumsal pilotlar için korunmuştur.


## Granular Permission Matrix + Sidebar Visibility

Yetki Matrisi ekranı iki matristen oluşur: işlem yetkileri ve sidebar görünürlüğü. İşlem matrisi program, başlık, onay, kanıt, tablo, rapor, bildirim, yönetim ve denetim kategorilerine ayrılmış ayrıntılı bir izin kataloğu sunar. Sidebar matrisi ise kullanıcının sol menüde hangi modülleri göreceğini belirler. Menü görünürlüğü kullanıcı deneyimi içindir; backend güvenlik kontrolleri ayrıca korunur.

## Soft Delete Kapsamı

Program soft delete mantığına ek olarak kullanıcı, program kullanıcı yetkisi, kanıt ve tablo silme işlemleri de arşivleme yaklaşımına yaklaştırılmıştır. Kanıt dosyası fiziksel olarak hemen silinmez; kayıt görünür listelerden çıkarılır ve audit trail üzerinde arşivleme işlemi izlenir.

## Bildirim Polling

Sidebar’daki Bildirim Merkezi için okunmamış bildirim sayısı periyodik olarak güncellenir. Varsayılan polling aralığı 30 saniyedir; SSE/WebSocket gerektirmeden kararlı bir canlılık sağlar.
