from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from .db import get_conn, now_iso, row_to_dict, rows_to_dicts, transaction
from .repositories import (
    ADMIN_ROLE,
    TENANT_ADMIN_ROLE,
    FACULTY_ADMIN_ROLE,
    UNIT_COORDINATOR_ROLE,
    SUPER_ADMIN_ROLE,
    APPROVER_ROLE,
    EDITOR_ROLE,
    READONLY_ROLE,
    APPROVED,
    SUBMITTED,
    REVISION,
    COMPLETED,
    READY,
    assert_program_access,
    assert_program_operation_permission,
    get_program,
    get_user,
    list_evidence,
    list_sections,
    list_tables,
    quality_for_section,
)
from .visibility_scope import section_visible_to_user, visible_section_keys


def _parse_day(value: str | None) -> date | None:
    text = str(value or '').strip()
    if not text:
        return None
    for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _section_label(section: dict[str, Any]) -> str:
    key = str(section.get('section_key', '') or '')
    title = str(section.get('section_title', '') or section.get('main_title', '') or '')
    return f'{key} - {title}'.strip(' -')


def _missing_items(section: dict[str, Any], quality: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    text = str(section.get('report_text', '') or '').strip()
    if len(text.split()) < 80:
        missing.append('Rapor metni kısa/eksik')
    if int(quality.get('evidence', 0) or 0) == 0:
        missing.append('Kanıt yok')
    if int(quality.get('puko', 0) or 0) < 4:
        missing.append('PUKÖ alanları eksik')
    if int(quality.get('tables', 0) or 0) == 0:
        missing.append('Tablo yok')
    if not str(section.get('deadline', '') or '').strip():
        missing.append('Son teslim tarihi yok')
    if section.get('approval_status') == REVISION or section.get('status') == REVISION:
        missing.append('Revizyon bekliyor')
    return missing


def _deadline_state(deadline: str | None) -> tuple[str, int | None]:
    day = _parse_day(deadline)
    if not day:
        return ('Tarih yok', None)
    delta = (day - date.today()).days
    if delta < 0:
        return ('Gecikti', delta)
    if delta <= 7:
        return ('Bu hafta', delta)
    if delta <= 30:
        return ('Bu ay', delta)
    return ('Planlandı', delta)


def program_insights(username: str, program_id: str) -> dict[str, Any]:
    role = assert_program_access(username, program_id)
    program = get_program(program_id) or {}
    sections = list_sections(username, program_id)
    quality_rows = [quality_for_section(username, program_id, section) for section in sections]
    evidence_rows = list_evidence(username, program_id)
    table_rows = list_tables(username, program_id)

    gaps: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []
    deadline_calendar: list[dict[str, Any]] = []
    score_total = 0
    quality_distribution = {'0-39': 0, '40-59': 0, '60-79': 0, '80-100': 0}
    missing_counters: dict[str, int] = {}

    for section, quality in zip(sections, quality_rows):
        key = str(section.get('section_key', '') or '')
        score = int(quality.get('score', 0) or 0)
        score_total += score
        if score < 40:
            quality_distribution['0-39'] += 1
        elif score < 60:
            quality_distribution['40-59'] += 1
        elif score < 80:
            quality_distribution['60-79'] += 1
        else:
            quality_distribution['80-100'] += 1
        missing = _missing_items(section, quality)
        for item in missing:
            missing_counters[item] = missing_counters.get(item, 0) + 1
        state, days_left = _deadline_state(str(section.get('deadline', '') or ''))
        deadline_calendar.append({
            'section_key': key,
            'section_title': section.get('section_title', ''),
            'report_group_title': section.get('report_group_title', ''),
            'main_title': section.get('main_title', ''),
            'deadline': section.get('deadline', ''),
            'deadline_state': state,
            'days_left': days_left,
            'status': section.get('status', ''),
            'approval_status': section.get('approval_status', ''),
        })
        if missing or score < 70:
            gaps.append({
                'section_key': key,
                'section_title': section.get('section_title', ''),
                'report_group_title': section.get('report_group_title', ''),
                'main_title': section.get('main_title', ''),
                'quality': score,
                'missing': ', '.join(missing) if missing else 'Kalite puanı düşük',
                'status': section.get('status', ''),
                'approval_status': section.get('approval_status', ''),
                'deadline': section.get('deadline', ''),
            })
        # Role-aware task stream.
        if role == EDITOR_ROLE:
            if section.get('approval_status') == REVISION or section.get('status') == REVISION:
                priority = 'Yüksek'
                reason = 'Revizyon istenen başlık'
            elif missing or score < 70:
                priority = 'Orta'
                reason = 'Tamamlanması gereken eksikler var'
            else:
                continue
        elif role == APPROVER_ROLE:
            if section.get('approval_status') != SUBMITTED:
                continue
            priority = 'Yüksek'
            reason = 'Onay kararı bekliyor'
        elif role in {SUPER_ADMIN_ROLE, TENANT_ADMIN_ROLE, FACULTY_ADMIN_ROLE}:
            if state == 'Gecikti':
                priority = 'Yüksek'
                reason = 'Son teslim tarihi geçmiş'
            elif section.get('approval_status') == SUBMITTED:
                priority = 'Orta'
                reason = 'Onay kuyruğunda'
            elif not str(section.get('deadline', '') or '').strip():
                priority = 'Düşük'
                reason = 'Termin planı eksik'
            else:
                continue
        else:
            if missing or score < 60:
                priority = 'Bilgi'
                reason = 'İzleme için kritik başlık'
            else:
                continue
        tasks.append({
            'priority': priority,
            'reason': reason,
            'section_key': key,
            'section_title': section.get('section_title', ''),
            'quality': score,
            'deadline': section.get('deadline', ''),
            'approval_status': section.get('approval_status', ''),
            'status': section.get('status', ''),
        })

    gaps.sort(key=lambda row: (int(row.get('quality', 0) or 0), str(row.get('deadline', '') or '9999-99-99')))
    priority_order = {'Yüksek': 0, 'Orta': 1, 'Düşük': 2, 'Bilgi': 3}
    tasks.sort(key=lambda row: (priority_order.get(str(row.get('priority', '')), 9), int(row.get('quality', 0) or 0)))
    deadline_calendar.sort(key=lambda row: (row.get('days_left') is None, row.get('days_left') if row.get('days_left') is not None else 999999))

    visible_keys = visible_section_keys(username, program_id)
    with get_conn() as conn:
        history_rows = conn.execute(
            """SELECT sa.*, s.main_title, s.section_title
               FROM section_approvals sa
               LEFT JOIN sections s ON s.program_id=sa.program_id AND s.section_key=sa.section_key
               WHERE sa.program_id=?
               ORDER BY sa.created_at DESC LIMIT 200""",
            (program_id,),
        ).fetchall()
    timeline = [row for row in rows_to_dicts(history_rows) if str(row.get('section_key', '') or '') in visible_keys]
    timeline = timeline[:80]
    for item in timeline:
        item["report_group_title"] = item.get("main_title", "")

    evidence_map = []
    for evidence in evidence_rows:
        keys = evidence.get('section_keys') or []
        evidence_map.append({
            'code': evidence.get('code', ''),
            'original_name': evidence.get('original_name', ''),
            'section_count': len(keys),
            'section_keys': ', '.join(keys),
            'uploaded_at': evidence.get('uploaded_at', ''),
            'note': evidence.get('note', ''),
        })

    total = len(sections)
    avg_quality = round(score_total / total, 1) if total else 0
    return {
        'program': program,
        'summary': {
            'total_sections': total,
            'tasks': len(tasks),
            'gaps': len(gaps),
            'avg_quality': avg_quality,
            'evidence': len(evidence_rows),
            'tables': len(table_rows),
            'overdue': sum(1 for row in deadline_calendar if row.get('deadline_state') == 'Gecikti'),
            'due_this_week': sum(1 for row in deadline_calendar if row.get('deadline_state') == 'Bu hafta'),
            'submitted': sum(1 for row in sections if row.get('approval_status') == SUBMITTED),
            'revision': sum(1 for row in sections if row.get('approval_status') == REVISION or row.get('status') == REVISION),
        },
        'tasks': tasks[:80],
        'gaps': gaps[:120],
        'quality': {
            'average': avg_quality,
            'distribution': quality_distribution,
            'missing_counters': [{'issue': key, 'count': value} for key, value in sorted(missing_counters.items(), key=lambda item: item[1], reverse=True)],
        },
        'timeline': timeline,
        'deadline_calendar': deadline_calendar,
        'evidence_map': evidence_map,
        'help': program_help(username, program_id),
    }


def program_help(username: str, program_id: str) -> dict[str, Any]:
    role = assert_program_access(username, program_id)
    role_order = [SUPER_ADMIN_ROLE, TENANT_ADMIN_ROLE, FACULTY_ADMIN_ROLE, UNIT_COORDINATOR_ROLE, EDITOR_ROLE, APPROVER_ROLE, READONLY_ROLE]

    common_rules = [
        'Her başlıkta rapor metni, PUKÖ alanları, kanıt ve tablo durumunu birlikte kontrol edin.',
        'Onay/revizyon kararlarından önce ilgili başlığın Revizyon & Geçmiş sekmesini inceleyin.',
        'Rapor çıktısı almadan önce Görev & Eksik Analizi ekranında kritik eksik kalmadığını doğrulayın.',
        'Mail ve uygulama içi bildirimleri kaçırmamak için Bildirim Merkezi sayacını düzenli kontrol edin.',
    ]

    guides = {
        SUPER_ADMIN_ROLE: {
            'label': 'Süper Admin',
            'subtitle': 'Tüm kurumlar, tenant izolasyonu, görünüm paketleri, yetki devri ve sistem yönetimi',
            'mission': 'Süper Admin rolü platformun en üst yöneticisidir. Kurumları açar, Kurum Admin yetkilerini belirler, görünüm paketlerini kurumlara atar, sistem ayarlarını ve denetim izlerini kontrol eder.',
            'daily_focus': [
                'Gösterge Paneli ve Gelişmiş Dashboard üzerinden genel hazırlık, revizyon ve gecikme risklerini kontrol et.',
                'Görev & Eksik Analizi ekranında kritik eksikleri ve son tarihi geçmiş başlıkları program bazında takip et.',
                'Bildirim Merkezi, Tam Activity Trail ve Kullanım Analitiği ile sistem hareketlerini izle.',
                'Onaylayıcı ve editör atamalarının doğru programlarla sınırlı olduğundan emin ol.',
            ],
            'workflow': [
                {'step': '1', 'title': 'Programı yapılandır', 'detail': 'Program Yönetimi ekranından akreditasyon profili, fakülte/MYO, bölüm, program ve rapor yılını oluştur veya kopyala.'},
                {'step': '2', 'title': 'Kullanıcıları ve rolleri ata', 'detail': 'Kullanıcı & Rol Yönetimi ve Program Yönetimi > Program Bazlı Kullanıcı ve Rol Atama sekmelerinden kullanıcıları programa bağla.'},
                {'step': '3', 'title': 'Yetki matrisini denetle', 'detail': 'Yetki Matrisi ekranında işlem yetkileri ile sidebar görünürlüğünün kurum politikasına uygun olduğunu kontrol et.'},
                {'step': '4', 'title': 'Son teslim tarihlerini planla', 'detail': 'Son Teslim Tarihi Planı veya Toplu İşlemler ile başlıkların tarihlerini belirle; geciken başlıkları Teslim Takvimi ekranından izle.'},
                {'step': '5', 'title': 'Rapor sürecini izle', 'detail': 'Dashboard, Görev & Eksik Analizi, Kontrol ve Onay Akışı ekranlarından hazırlık durumunu takip et.'},
                {'step': '6', 'title': 'Çıktı ve yedekleri kontrol et', 'detail': 'Rapor Önizleme/Rapor Dışa Aktar ile DOCX/PDF üret; Ayarlar & Yedek bölümünden yedek ve SMTP durumlarını izle.'},
            ],
            'modules': [
                {'module': 'Program Yönetimi', 'use': 'Program oluşturma, kopyalama, pasifleştirme, geri yükleme ve program bazlı rol atama.'},
                {'module': 'Kullanıcı & Rol Yönetimi', 'use': 'Kullanıcı oluşturma, şifre yenileme, rol ve hesap durumlarını yönetme.'},
                {'module': 'Yetki Matrisi', 'use': 'Rol bazlı işlem izinleri ve sidebar görünürlüklerini kurum politikasına göre düzenleme.'},
                {'module': 'Son Teslim Tarihi Planı', 'use': 'Başlık bazında tarih atama ve tarih planını güncelleme.'},
                {'module': 'Tam Activity Trail', 'use': 'Kritik işlemlerin kim, ne zaman, ne yaptı bilgisiyle izlenmesi.'},
                {'module': 'Geri Yükleme', 'use': 'Soft delete ile arşive taşınan programları geri alma veya kalıcı temizleme.'},
                {'module': 'Ayarlar & Yedek', 'use': 'SMTP, mail bildirimi, sistem şablonları, belge ayarları ve yedek operasyonları.'},
            ],
            'checklist': [
                'Program doğru akreditasyon profiliyle oluşturuldu mu?',
                'Editör / Hazırlayıcı ve onaylayıcılar yalnızca ilgili programlara atandı mı?',
                'Yetki matrisi ve sidebar matrisi kurum politikasına uygun mu?',
                'Tüm kritik başlıklara son teslim tarihi verildi mi?',
                'Mail/SMPP ayarları test edildi ve bildirim kayıtları izleniyor mu?',
                'Rapor çıktısı öncesi kritik eksik ve revizyon kalmadı mı?',
                'Yedekleme ve geri yükleme prosedürü test edildi mi?',
            ],
            'warnings': [
                'Kalıcı silme işlemini sadece yedek aldıktan sonra kullanın.',
                'Admin, onay sürecini yönetebilir; ancak editörün hazırlık sorumluluğunu üstlenmemelidir.',
                'SMTP şifresi değiştirilirse mail ayarlarını yeniden test edin.',
            ],
        },
        TENANT_ADMIN_ROLE: {
            'label': 'Kurum Admin',
            'subtitle': 'Kendi kurumunda kullanıcı, program ve yetki dağıtımı',
            'mission': 'Kurum Admin, Süper Admin tarafından izin verilen sınırlar içinde kendi kurumundaki Birim Admin, Editör / Hazırlayıcı, Onaylayıcı ve Denetçi rollerini yönetir. Kurum dışı veriye erişmez ve tavan yetkisini aşamaz.',
            'daily_focus': [
                'Kendi kurumundaki program hazırlık durumlarını ve geciken başlıkları kontrol et.',
                'Kullanıcı & Rol Yönetimi ekranında yalnızca kurumundaki kullanıcıları yönet.',
                'Yetki Matrisi üzerinden Süper Admin tarafından açılan yetkileri alt rollere dağıt.',
                'Giriş denemeleri ve bildirimleri sadece kurum kapsamına göre izle.',
            ],
            'workflow': [
                {'step': '1', 'title': 'Kurum kapsamını kontrol et', 'detail': 'Sidebar ve Program Yönetimi ekranlarında sadece kendi kurumunun göründüğünü doğrula.'},
                {'step': '2', 'title': 'Programları hazırla', 'detail': 'Yetkin varsa Yeni Program veya Program Kopyala sekmelerinden kurum içi programları oluştur.'},
                {'step': '3', 'title': 'Kullanıcıları yönet', 'detail': 'Kurumundaki kullanıcılara Birim Admin, Editör / Hazırlayıcı, Onaylayıcı veya Denetçi rolü ver.'},
                {'step': '4', 'title': 'Yetki devri yap', 'detail': 'Yetki Matrisi ekranında sadece Süper Adminin sana verdiği izinleri alt rollere dağıt.'},
                {'step': '5', 'title': 'Süreci izle', 'detail': 'Gösterge Paneli, Kontrol ve Bildirim Merkezi üzerinden kurum geneli durumu takip et.'},
            ],
            'modules': [
                {'module': 'Program Yönetimi', 'use': 'Kurum içi program oluşturma, kopyalama ve program kullanıcı atama.'},
                {'module': 'Kullanıcı & Rol Yönetimi', 'use': 'Kurum kapsamındaki kullanıcıları yönetme.'},
                {'module': 'Yetki Matrisi', 'use': 'Kurum içinde alt rollere izin dağıtma.'},
                {'module': 'Kontrol', 'use': 'Onay/revizyon durumlarını kurum bazında izleme.'},
                {'module': 'Bildirim Merkezi', 'use': 'Kurum kapsamındaki sistem içi bildirimleri takip etme.'},
            ],
            'checklist': [
                'Kurum dışı program veya kullanıcı görünmediğinden emin ol.',
                'Alt rollere sadece gerekli minimum yetkileri verdin mi?',
                'Birim Admin atamaları doğru birimle sınırlı mı?',
                'Onaylayıcı ve editörler doğru programlara bağlı mı?',
                'Geciken başlıklar için hatırlatma ve bildirimler takip ediliyor mu?',
            ],
            'warnings': [
                'Kurum Admin Süper Admin oluşturamaz ve kendi tavan yetkisini aşamaz.',
                'Kurum Yönetimi sekmesi yalnızca Süper Admin izin verirse görünür.',
                'Yetki değişikliklerinden sonra ilgili kullanıcıların yeniden giriş yapması gerekebilir.',
            ],
        },
        FACULTY_ADMIN_ROLE: {
            'label': 'Birim Admin',
            'subtitle': 'Atandığı Fakülte/MYO altındaki bölüm ve programların koordinasyonu',
            'mission': 'Birim Admin, seçili birim altındaki tüm bölüm ve programların hazırlık, kanıt, onay ve revizyon süreçlerini koordine eder. Bölüm veya program seçimine bağlı kalmadan birim kapsamını izler.',
            'daily_focus': [
                'Atandığın Fakülte/MYO altındaki programların hazırlık ve revizyon durumunu kontrol et.',
                'Editör / Hazırlayıcı ve onaylayıcıların eksik başlıklardaki ilerlemesini takip et.',
                'Kanıt, PUKÖ ve tablo eksiklerini birim bazında izle.',
                'Teslim tarihi yaklaşan programlar için ilgili rolleri bilgilendir.',
            ],
            'workflow': [
                {'step': '1', 'title': 'Birim kapsamını seç', 'detail': 'Sidebar üzerinden kurum ve Fakülte/MYO bağlamını kontrol et.'},
                {'step': '2', 'title': 'Programları izle', 'detail': 'Birim altındaki tüm programların gösterge paneli, kontrol ve teslim takvimi durumlarını takip et.'},
                {'step': '3', 'title': 'Eksikleri yönlendir', 'detail': 'Görev & Eksik Analizi ekranındaki kritik başlıkları ilgili editörlere bildir.'},
                {'step': '4', 'title': 'Onay akışını koordine et', 'detail': 'Onay bekleyen ve revizyon gereken başlıkların sürede tamamlanmasını takip et.'},
            ],
            'modules': [
                {'module': 'Gösterge Paneli', 'use': 'Fakülte/MYO kapsamındaki programların genel durumunu izleme.'},
                {'module': 'Görev & Eksik Analizi', 'use': 'Birim altındaki eksik kanıt, metin, tablo ve PUKÖ risklerini takip etme.'},
                {'module': 'Kontrol', 'use': 'Onay/revizyon dağılımını birim kapsamıyla izleme.'},
                {'module': 'Teslim Takvimi', 'use': 'Geciken ve yaklaşan başlıkları birim bazında yönetme.'},
                {'module': 'Bildirim Merkezi', 'use': 'Birim kapsamındaki kritik olayları takip etme.'},
            ],
            'checklist': [
                'Birim altındaki tüm programlar görünür durumda mı?',
                'Revizyon bekleyen başlıklar ilgili editörlere iletildi mi?',
                'Yaklaşan terminler için hatırlatma yapıldı mı?',
                'Kanıt ve PUKÖ eksikleri kritik seviyede mi?',
                'Onay kuyruğu gereksiz bekliyor mu?',
            ],
            'warnings': [
                'Birim Admin yetkisi kurum geneline değil, atanmış birime uygulanır.',
                'Kurum veya sistem ayarları bu rolün doğal kapsamı değildir.',
                'Program dışı yetki gerekiyorsa Kurum Admin veya Süper Admin ile iletişime geç.',
            ],
        },

        UNIT_COORDINATOR_ROLE: {
            'label': 'Birim Koordinatörü',
            'subtitle': 'Birim içinde rapor koordinasyonu, eksik takibi ve kısmi onay akışı',
            'mission': 'Birim Koordinatörü, kendi birimindeki programların rapor hazırlama sürecini koordine eder; metin, kanıt, tablo ve PUKÖ eksiklerini izler, ilgili hazırlayıcı ve onaylayıcılara yönlendirme yapar.',
            'daily_focus': [
                'Birimindeki programların hazırlık yüzdesini ve kritik eksiklerini kontrol et.',
                'Revizyon ve onay bekleyen başlıkları gecikmeden ilgili kişilere yönlendir.',
                'Kanıt ve tablo eksiklerini program bazında önceliklendir.',
                'Denetime yakın başlıklar için dışa aktarım öncesi kalite skorunu kontrol et.',
            ],
            'workflow': [
                {'step': '1', 'title': 'Birim kapsamını izle', 'detail': 'Gösterge Paneli ve Akreditasyon Stüdyosu üzerinden birimindeki programları takip et.'},
                {'step': '2', 'title': 'Eksikleri yönlendir', 'detail': 'Görev & Eksik Analizi ve kalite uyarılarını ilgili hazırlayıcılarla paylaş.'},
                {'step': '3', 'title': 'Onay akışını koordine et', 'detail': 'Onaya gönderilen ve revizyon isteyen başlıkların zamanında kapatılmasını takip et.'},
            ],
            'modules': [
                {'module': 'Gösterge Paneli', 'use': 'Birim içi program durumunu izleme.'},
                {'module': 'Akreditasyon Stüdyosu', 'use': 'Rapor metni, kanıt ve PUKÖ durumlarını kontrol etme.'},
                {'module': 'Onay ve Revizyon Merkezi', 'use': 'Başlık karar ve revizyon akışını koordine etme.'},
                {'module': 'Denetime Hazır Dışa Aktarım', 'use': 'Çıktı öncesi son kontrol ve export alma.'},
            ],
            'checklist': [
                'Birimdeki programlarda kritik eksik kaldı mı?',
                'Revizyon bekleyen başlıklar ilgili hazırlayıcıya iletildi mi?',
                'Kanıt, tablo ve PUKÖ alanları kalite kontrolünden geçti mi?',
            ],
            'warnings': [
                'Birim Koordinatörü kurum genelindeki yetki matrisini ve kullanıcı rollerini değiştirmez.',
                'Program oluşturma/silme işlemleri Birim Admin veya üst rollerin kapsamındadır.',
            ],
        },
        EDITOR_ROLE: {
            'label': 'Editör / Hazırlayıcı',
            'subtitle': 'Başlık hazırlama, kanıt yükleme, tablo doldurma ve onaya gönderme',
            'mission': 'Editör / Hazırlayıcı rolü rapor içeriğini hazırlar. Başlık metnini yazar, PUKÖ alanlarını doldurur, kanıt ve tablo ekler; kaydettikten sonra başlığı onaya gönderir.',
            'daily_focus': [
                'Görev & Eksik Analizi ekranında sana aksiyon gerektiren eksikleri kontrol et.',
                'Rapor Dizini’nde başlık metni, PUKÖ, kanıt ve tablo alanlarını tamamla.',
                'Revizyon istenen başlıkları önceliklendir ve revizyon notunu yanıtlayacak şekilde güncelle.',
                'Kaydetmeden onaya göndermeye çalışma; sistem kaydı zorunlu tutar.',
            ],
            'workflow': [
                {'step': '1', 'title': 'Başlığı seç', 'detail': 'Rapor Dizini’nde ilgili ana bölüm ve alt başlığı aç.'},
                {'step': '2', 'title': 'Metni hazırla', 'detail': 'Rapor Metni sekmesinde kanıta dayalı, kurum/program özelinde açıklayıcı metni yaz.'},
                {'step': '3', 'title': 'PUKÖ alanlarını doldur', 'detail': 'Planla, Uygula, Kontrol Et, Önlem Al alanlarını boş bırakma; her alanı başlıkla ilişkilendir.'},
                {'step': '4', 'title': 'Kanıt ve tablo ekle', 'detail': 'Kanıt Arşivi ve Tablo Yönetimi üzerinden ilgili dosyaları ve tabloları başlığa bağla.'},
                {'step': '5', 'title': 'Başlığı kaydet', 'detail': 'Bu Başlığı Kaydet butonuyla son metni, durum bilgisini ve PUKÖ alanlarını kaydet.'},
                {'step': '6', 'title': 'Onaya gönder', 'detail': 'Kaydedilmiş ve hazır başlıkları Onaya Gönder butonuyla onaylayıcıya ilet.'},
            ],
            'modules': [
                {'module': 'Rapor Dizini', 'use': 'Başlık metni, PUKÖ, durum ve not girişleri.'},
                {'module': 'Kanıt Arşivi', 'use': 'Belge yükleme, başlıklarla ilişkilendirme ve kanıt notu girme.'},
                {'module': 'Tablo Yönetimi', 'use': 'Hazır/özel tabloları doldurma ve başlıklara bağlama.'},
                {'module': 'Görev & Eksik Analizi', 'use': 'Eksik metin, kanıt, tablo, PUKÖ ve son tarih risklerini görme.'},
                {'module': 'Onay Akışı', 'use': 'Onaya gönderilen/revizyon dönen başlıkların durumunu izleme.'},
                {'module': 'Bildirim Merkezi', 'use': 'Revizyon, onay ve son teslim bildirimlerini takip etme.'},
            ],
            'checklist': [
                'Başlık metni yeterince açıklayıcı ve kanıta dayalı mı?',
                'PUKÖ alanlarının dördü de dolu mu?',
                'En az bir ilgili kanıt dosyası bağlı mı?',
                'Gerekli tablo/özet veri başlığa eklendi mi?',
                'Son teslim tarihi geçmeden işlem tamamlandı mı?',
                'Başlık kaydedildi mi?',
                'Revizyon notu varsa doğrudan bu nota cevap verecek düzeltme yapıldı mı?',
            ],
            'warnings': [
                'Kaydedilmemiş değişiklikler onaya gönderilemez.',
                'Sadece metin yazmak yeterli değildir; kanıt ve PUKÖ eksikleri kalite skorunu düşürür.',
                'Yanlış başlığa yüklenen kanıtlar rapor çıktısında karışıklık oluşturabilir.',
            ],
        },
        APPROVER_ROLE: {
            'label': 'Onaylayıcı',
            'subtitle': 'Başlık inceleme, revizyon isteme, onaylama ve kalite kontrol',
            'mission': 'Onaylayıcı rolü, editörlerin hazırladığı başlıkları değerlendirir. İçerik uygunsa onaylar; eksik veya hatalıysa açık revizyon notuyla editöre geri gönderir.',
            'daily_focus': [
                'Onay Akışı ekranında onay bekleyen başlıkları incele.',
                'Revizyon notlarında açık, ölçülebilir ve uygulanabilir geri bildirim ver.',
                'Rapor Önizleme ile başlığın nihai raporda nasıl görüneceğini kontrol et.',
                'Teslim Takvimi ve Bildirim Merkezi ile yaklaşan/geciken kararları takip et.',
            ],
            'workflow': [
                {'step': '1', 'title': 'Onay kuyruğunu aç', 'detail': 'Onay Akışı ekranından onaya gönderilen başlıkları listele.'},
                {'step': '2', 'title': 'İçeriği incele', 'detail': 'Metin, PUKÖ, kanıt ve tablo sekmelerini birlikte kontrol et; sadece metne bakarak karar verme.'},
                {'step': '3', 'title': 'Geçmişi kontrol et', 'detail': 'Revizyon & Geçmiş veya Versiyon Karşılaştırma ekranından önceki değişiklikleri incele.'},
                {'step': '4', 'title': 'Karar ver', 'detail': 'Uygun başlıkları Onayla; eksik başlıklar için Revizyon İste.'},
                {'step': '5', 'title': 'Notu açık yaz', 'detail': 'Revizyon isterken hangi kanıt, tablo veya metin parçasının eksik olduğunu net belirt.'},
            ],
            'modules': [
                {'module': 'Onay Akışı', 'use': 'Onay, revizyon ve karar notu süreçleri.'},
                {'module': 'Kontrol', 'use': 'Onay/revizyon durumlarının program genelinde izlenmesi.'},
                {'module': 'Versiyon Karşılaştırma', 'use': 'Editör / Hazırlayıcı değişikliklerini önceki sürümle karşılaştırma.'},
                {'module': 'Rapor Önizleme', 'use': 'Başlığın rapor çıktısındaki görünümünü kontrol etme.'},
                {'module': 'Teslim Takvimi', 'use': 'Onay bekleyen ve tarihi yaklaşan başlıkları takip etme.'},
                {'module': 'Bildirim Merkezi', 'use': 'Onay kuyruğu ve revizyon dönüşlerini izleme.'},
            ],
            'checklist': [
                'Başlık, ilgili akreditasyon ölçütünü doğrudan karşılıyor mu?',
                'Metin somut kanıtlarla desteklenmiş mi?',
                'Kanıt dosyaları başlıkla gerçekten ilişkili mi?',
                'PUKÖ döngüsü mantıklı ve tamam mı?',
                'Tablo/veri gerekiyorsa eklenmiş mi?',
                'Revizyon istenecekse not net, kısa ve uygulanabilir mi?',
                'Onay kararı sonrası başlığın durumu doğru yansıyor mu?',
            ],
            'warnings': [
                'Belirsiz revizyon notları editörün süreci uzatmasına neden olur.',
                'Onaylayıcı rolünde onaya gönderme yapılmaz; karar verme yapılır.',
                'Kanıtı olmayan kritik başlıkları onaylamadan önce eksikliği mutlaka not düş.',
            ],
        },
        READONLY_ROLE: {
            'label': READONLY_ROLE,
            'subtitle': 'Salt okunur takip, rapor önizleme ve genel ilerleme izleme',
            'mission': 'Denetçi rolü rapor hazırlık sürecini takip eder. İçerik veya karar değişikliği yapmaz; ilerleme, kalite, teslim ve çıktı durumlarını görüntüler.',
            'daily_focus': [
                'Gösterge Paneli üzerinden genel hazırlık oranını ve riskleri takip et.',
                'Rapor Önizleme ile nihai rapor görünümünü kontrol et.',
                'İstatistikler ve Gelişmiş Dashboard ile programın ilerlemesini izle.',
                'Bildirim Merkezi üzerinden sadece kendini ilgilendiren duyuruları takip et.',
            ],
            'workflow': [
                {'step': '1', 'title': 'Genel durumu izle', 'detail': 'Gösterge Paneli ve Gelişmiş Dashboard ekranlarından hazırlık yüzdesini ve riskleri görüntüle.'},
                {'step': '2', 'title': 'Raporu oku', 'detail': 'Rapor Önizleme ile başlıkları salt okunur biçimde incele.'},
                {'step': '3', 'title': 'İstatistiklere bak', 'detail': 'İstatistikler ekranında kalite, onay ve eksiklik dağılımını takip et.'},
                {'step': '4', 'title': 'Çıktıları indir', 'detail': 'Yetki verildiyse Rapor Dışa Aktar ekranından hazırlanmış DOCX/PDF çıktıları indir.'},
            ],
            'modules': [
                {'module': 'Gösterge Paneli', 'use': 'Genel hazırlık durumu, risk ve ilerleme takibi.'},
                {'module': 'Rapor Önizleme', 'use': 'Nihai rapor görünümünü salt okunur inceleme.'},
                {'module': 'İstatistikler', 'use': 'Tamamlanma, kalite ve durum dağılımlarını takip etme.'},
                {'module': 'Rapor Dışa Aktar', 'use': 'Hazır çıktıları indirme.'},
                {'module': 'Bildirim Merkezi', 'use': 'Sistemin gönderdiği bilgilendirmeleri takip etme.'},
            ],
            'checklist': [
                'Genel hazırlık oranı beklenen seviyede mi?',
                'Revizyon veya gecikme sayısı artıyor mu?',
                'Rapor önizlemede kritik başlıklar boş görünüyor mu?',
                'Çıktı alınacak rapor güncel mi?',
                'Gözlemlediğin eksikleri ilgili admin/editörle paylaştın mı?',
            ],
            'warnings': [
                'Denetçi rolü içerik düzenleme veya onay kararı vermez.',
                'Rapor çıktısı indirirken güncel tarihli çıktıyı seçtiğinden emin ol.',
                'Yetki eksikliği görürsen admin ile iletişime geç.',
            ],
        },
    }

    return {
        'role': role,
        'role_order': role_order,
        'active_role': role if role in guides else READONLY_ROLE,
        'common_rules': common_rules,
        'guides': guides,
    }

def notification_inbox(username: str, program_id: str, limit: int = 100) -> list[dict[str, Any]]:
    role = assert_program_operation_permission(username, program_id, "notification.view")
    user = get_user(username) or {}
    user_email = str(user.get('email', '') or '').lower()
    admin_scope_roles = {SUPER_ADMIN_ROLE, TENANT_ADMIN_ROLE, FACULTY_ADMIN_ROLE}
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT ne.id,ne.event_type,ne.program_id,ne.section_key,ne.actor,ne.recipients_json,
                      ne.subject,ne.status,ne.error,ne.created_at,ne.sent_at,
                      nr.read_at
               FROM notification_events ne
               LEFT JOIN notification_reads nr ON nr.event_id=ne.id AND nr.username=?
               WHERE ne.program_id=? OR ne.program_id=''
               ORDER BY ne.created_at DESC LIMIT ?""",
            (username, program_id, max(int(limit) * 3, 100)),
        ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows_to_dicts(rows):
        recipients = []
        try:
            recipients = json.loads(row.get('recipients_json') or '[]')
        except Exception:
            recipients = []
        recipient_usernames = {str(item.get('username', '') or '').lower() for item in recipients if isinstance(item, dict)}
        recipient_emails = {str(item.get('email', '') or '').lower() for item in recipients if isinstance(item, dict)}
        recipient_match = username.lower() in recipient_usernames or (user_email and user_email in recipient_emails)
        row_program_id = str(row.get('program_id', '') or '')
        section_key = str(row.get('section_key', '') or '')
        if row_program_id == program_id:
            visible = role in admin_scope_roles or recipient_match or not recipients
            if visible and not section_visible_to_user(username, program_id, section_key):
                visible = False
        else:
            # Global notifications are visible to Super Admin, or to explicitly
            # addressed recipients. This prevents tenant/faculty/user inboxes from
            # inheriting unscoped system-wide rows.
            visible = role == SUPER_ADMIN_ROLE or recipient_match
        if not visible:
            continue
        row['recipients'] = len(recipients)
        row['read'] = bool(row.get('read_at'))
        result.append(row)
        if len(result) >= int(limit):
            break
    return result

def mark_notifications_read(username: str, program_id: str, event_ids: list[str] | None = None) -> dict[str, Any]:
    assert_program_access(username, program_id)
    visible_ids = {str(row['id']) for row in notification_inbox(username, program_id, 500)}
    requested = [str(item).strip() for item in (event_ids or []) if str(item).strip()]
    ids = [event_id for event_id in requested if event_id in visible_ids] if requested else list(visible_ids)
    with transaction() as conn:
        for event_id in ids:
            conn.execute(
                "INSERT OR IGNORE INTO notification_reads(event_id, username, read_at) VALUES(?,?,?)",
                (event_id, username, now_iso()),
            )
    return {'updated': len(ids)}
