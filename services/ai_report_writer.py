from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class GeneratedReportDraft:
    text: str
    warnings: list[str]
    evidence_codes: list[str]
    table_names: list[str]


CRITICAL_SECTION_PROFILES: dict[str, dict[str, Any]] = {
    "1.": {
        "focus": "öğrenci kabulü, öğrenci gelişimi, hareketlilik, danışmanlık ve öğrenci merkezli süreçlerin kanıta dayalı yürütülmesi",
        "actors": "program kurulu, öğrenci işleri, danışman öğretim elemanları, kalite komisyonu ve öğrenci temsilcileri",
        "evidence_need": "öğrenci kabul kayıtları, yatay/dikey geçiş duyuruları, danışmanlık kayıtları, anket/geri bildirim analizleri ve kurul kararları",
        "quality_line": "öğrenciye ilişkin her uygulama süreç, sorumlu birim, dönemsel izleme ve iyileştirme kararıyla ilişkilendirilmelidir",
        "deepening": [
            "Öğrenci odaklı başlıklarda rapor, yalnızca ilgili sürecin varlığını değil, öğrencinin programa girişinden mezuniyet aşamasına kadar izlenen destek mekanizmalarını da göstermelidir.",
            "Bu ölçütte kabul, danışmanlık, hareketlilik, geri bildirim ve memnuniyet süreçleri aynı kalite güvence zinciri içinde ele alınmalı; öğrenciden gelen verinin hangi kurul veya komisyonda değerlendirildiği açıklanmalıdır.",
        ],
    },
    "1.5": {
        "focus": "öğrenci merkezli öğrenme, öğretme ve değerlendirme",
        "actors": "program kurulu, ders sorumluları, ölçme-değerlendirme komisyonu ve öğrenci temsilcileri",
        "evidence_need": "ders izlenceleri, ölçme-değerlendirme örnekleri, öğrenci geri bildirimleri ve iyileştirme kararları",
        "quality_line": "öğrenme çıktısı, ölçme aracı, geri bildirim ve iyileştirme kararı aynı iz içinde gösterilmelidir",
        "deepening": [
            "Öğrenci merkezli yaklaşım; dersin yürütülme biçimi, öğrencinin aktif katılımı, ölçme-değerlendirme yöntemi ve geri bildirimin ders iyileştirmesine yansıması üzerinden açıklanmalıdır.",
            "Metinde klasik anlatım, uygulama, laboratuvar, staj, vaka, ödev, proje veya beceri değerlendirmesi gibi yöntemlerin hangi öğrenme çıktısına hizmet ettiği görünür olmalıdır.",
            "Öğrenci geri bildirimleri ve ölçme sonuçları yalnızca raporlanmamalı; bu bulguların ders planı, değerlendirme aracı veya uygulama sürecinde hangi iyileştirmeye yol açtığı belirtilmelidir.",
        ],
    },
    "1.8": {
        "focus": "öğretim yöntemleri ve ölçme-değerlendirme uygulamalarının tutarlılığı",
        "actors": "ders kurulları, uygulama/staj sorumluları ve kalite komisyonu",
        "evidence_need": "ders bilgi paketleri, sınav/ödev/rubrik örnekleri, uygulama değerlendirme formları ve analiz raporları",
        "quality_line": "kullanılan yöntemlerin program çıktılarıyla uyumu ve sonuçların nasıl izlendiği açık yazılmalıdır",
        "deepening": [
            "Öğretim yöntemi ve ölçme-değerlendirme başlıklarında rapor, derslerin yalnızca işlendiğini değil, öğrenme çıktılarına uygun yöntemlerle yürütüldüğünü göstermelidir.",
            "Teorik dersler, uygulamalı eğitim, laboratuvar, simülasyon, klinik/staj veya mesleki uygulama bileşenleri ayrı ayrı izlenebilir kanıtlarla desteklenmelidir.",
            "Ölçme araçlarının öğrenme çıktılarıyla uyumu, sınav/ödev/proje/rubrik/staj formu örnekleriyle ilişkilendirilmeli ve sonuçların nasıl analiz edildiği açıklanmalıdır.",
        ],
    },
    "2.": {
        "focus": "program amaçları ve program çıktılarının paydaş katılımı, izleme verileri ve iyileştirme kararlarıyla yönetilmesi",
        "actors": "program kurulu, danışma kurulu, mezunlar, işverenler, öğrenciler, ders sorumluları ve kalite birimi",
        "evidence_need": "program amacı/çıktısı dokümanları, paydaş toplantı tutanakları, PÇ matrisleri, anket analizleri, başarı verileri ve iyileştirme kararları",
        "quality_line": "amaç ve çıktılar ölçülebilir, izlenebilir ve iyileştirme kararlarına bağlanabilir şekilde kanıtlanmalıdır",
        "deepening": [
            "Program amaçları ve çıktıları başlıklarında rapor, beyan edilen hedefleri değil bu hedeflerin nasıl izlendiğini ve hangi paydaş verileriyle güncellendiğini göstermelidir.",
            "Her çıktı; ders bilgi paketi, eğitim planı, ölçme aracı, başarı verisi ve iyileştirme kararıyla ilişkilendirildiğinde MEDEK açısından daha güçlü hale gelir.",
        ],
    },
    "2.4": {
        "focus": "program amaçlarının paydaş katılımıyla izlenmesi ve güncellenmesi",
        "actors": "program danışma kurulu, mezunlar, işverenler, öğrenciler ve bölüm/program kurulu",
        "evidence_need": "paydaş toplantı tutanakları, anket analizleri, program amaçları güncelleme kararları ve duyurular",
        "quality_line": "amaçların yalnızca tanımlandığı değil, hangi veriyle izlendiği ve nasıl iyileştirildiği gösterilmelidir",
        "deepening": [
            "Program amaçları değerlendirilirken iç ve dış paydaş katılımı, mezun/işveren görüşleri ve öğrenci geri bildirimleri sistematik biçimde rapora yansıtılmalıdır.",
            "Amaçların gözden geçirilme sıklığı, hangi kurulda ele alındığı, hangi verilerin kullanıldığı ve güncelleme kararının nasıl duyurulduğu açıkça belirtilmelidir.",
            "Bu bölümde güçlü rapor dili, program amaçlarını kurumsal misyon, sektör beklentisi ve mezun yeterlilikleriyle ilişkilendirir.",
        ],
    },
    "2.7": {
        "focus": "program çıktılarının ölçülmesi, izlenmesi ve program iyileştirmelerine yansıtılması",
        "actors": "program kurulu, ölçme-değerlendirme komisyonu, ders sorumluları ve kalite birimi",
        "evidence_need": "program çıktısı matrisleri, başarı analizleri, ders değerlendirme sonuçları ve iyileştirme kararları",
        "quality_line": "her çıktı için veri kaynağı, hedef düzey, gerçekleşme ve iyileştirme bağlantısı kurulmalıdır",
        "deepening": [
            "Program çıktıları izlenirken ders-PÇ ilişkisi, ölçme araçları, başarı düzeyleri ve hedef/gerçekleşme karşılaştırması birlikte verilmelidir.",
            "Çıktıların sağlanma düzeyi yalnızca kanaatle değil; ders başarı analizleri, uygulama/staj değerlendirmeleri, anket sonuçları ve kurul kararlarıyla kanıtlanmalıdır.",
            "Gelişime açık çıktılar için alınan önlem, sorumlu birim, termin ve izleme yöntemi raporda açıkça yer almalıdır.",
        ],
    },
    "4.": {
        "focus": "sürekli iyileştirme mekanizmasının PUKÖ döngüsüyle işletilmesi",
        "actors": "birim kalite komisyonu, program kurulu, ilgili komisyonlar ve paydaş temsilcileri",
        "evidence_need": "PUKÖ izleme formları, iyileştirme kararları, toplantı tutanakları ve gerçekleşme kanıtları",
        "quality_line": "sorun, veri kaynağı, karar, sorumlu, termin ve gerçekleşme sonucu birlikte gösterilmelidir",
        "deepening": [
            "Sürekli iyileştirme ölçütlerinde rapor, PUKÖ döngüsünün yalnızca teorik olarak bilindiğini değil, programda fiilen işletildiğini göstermelidir.",
            "Her iyileştirme örneğinde problemin nasıl belirlendiği, hangi veri kaynağının kullanıldığı, hangi kurul/komisyon kararının alındığı ve sonucun nasıl izlendiği açıklanmalıdır.",
            "İyileştirme kararları sorumlu kişi/birim, termin, gerçekleşme durumu ve yeni önlem bağlantısıyla sunulduğunda rapor izlenebilirlik kazanır.",
        ],
    },
    "9.": {
        "focus": "meslek alanına özgü yeterliliklerin eğitim planı, uygulama/staj süreçleri ve ölçme araçlarıyla kanıtlanması",
        "actors": "program kurulu, alan öğretim elemanları, uygulama/staj sorumluları, dış paydaşlar ve kalite komisyonu",
        "evidence_need": "alan dersleri, uygulama/staj dosyaları, beceri kontrol listeleri, mesleki rubrikler ve dış paydaş geri bildirimleri",
        "quality_line": "her yeterlilik ders, uygulama, ölçme aracı, hedef düzey, gerçekleşme ve kanıt kodu ile eşleştirilmelidir",
        "deepening": [
            "Disipline özgü ölçütlerde rapor, programın mesleki kimliğini ve mezuna kazandırdığı alana özgü becerileri açık biçimde göstermelidir.",
            "Yeterliliklerin derslerde nasıl öğretildiği, uygulama veya stajda nasıl pekiştirildiği ve hangi ölçme aracıyla değerlendirildiği birlikte yazılmalıdır.",
        ],
    },
    "9.1": {
        "focus": "disipline özgü mesleki yeterliliklerin ders, uygulama, staj ve kanıtlarla gösterilmesi",
        "actors": "program kurulu, uygulama/staj sorumluları, meslek alanı öğretim elemanları ve dış paydaşlar",
        "evidence_need": "ders içerikleri, staj dosyaları, beceri kontrol listeleri, uygulama değerlendirme formları ve klinik/alan uygulama kayıtları",
        "quality_line": "her mesleki yeterlilik ders/uygulama/staj bağlantısı, ölçme aracı, hedef düzey ve kanıt koduyla eşleştirilmelidir",
        "deepening": [
            "Ölçüt 9.1 kapsamında programın disipline özgü yeterlilikleri, eğitim planındaki mesleki dersler ve uygulama/staj bileşenleriyle doğrudan ilişkilendirilmelidir.",
            "Ameliyathane Hizmetleri gibi uygulama ağırlıklı programlarda asepsi-antisepsi, sterilizasyon, cerrahi alan güvenliği, ekip içi görev sorumluluğu, hasta güvenliği ve tıbbi cihaz/sarf hazırlığı gibi beceriler açık satırlarla gösterilmelidir.",
            "Bu bölümde Tablo 9.1.1 yalnızca liste değil, ders-uygulama-ölçme-kanıt bağlantısını kuran temel değerlendirme aracı olarak kullanılmalıdır.",
        ],
    },
}


def _profile_for_section(section_key: str) -> dict[str, Any] | None:
    if section_key in CRITICAL_SECTION_PROFILES:
        return CRITICAL_SECTION_PROFILES[section_key]
    for prefix in ("1.", "2.", "9."):
        if section_key.startswith(prefix):
            return CRITICAL_SECTION_PROFILES[prefix]
    if section_key.startswith("4."):
        return CRITICAL_SECTION_PROFILES["4."]
    return None


def _value(row: Mapping[str, Any] | Any, key: str, default: str = "") -> Any:
    try:
        return row[key]
    except Exception:
        return default


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _clip(value: str, limit: int = 240) -> str:
    clean = _clean(value)
    if not clean:
        return ""
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"


def _sentence_join(parts: Sequence[str]) -> str:
    return " ".join([_clean(p) for p in parts if _clean(p)])


def _extract_table_snapshot(table: Mapping[str, Any] | Any, max_cells: int = 6) -> str:
    raw = _value(table, "data_json", "")
    if not raw:
        return ""
    try:
        data = json.loads(raw)
        columns = [str(c) for c in data.get("columns", [])]
        rows = data.get("data", [])[:2]
        cells: list[str] = []
        for row in rows:
            for val in row:
                txt = _clean(val)
                if txt:
                    cells.append(txt)
                if len(cells) >= max_cells:
                    break
            if len(cells) >= max_cells:
                break
        col_part = ", ".join(columns[:5])
        cell_part = ", ".join(cells[:max_cells])
        if col_part and cell_part:
            return f"Sütunlar: {col_part}; örnek veri: {cell_part}"
        if col_part:
            return f"Sütunlar: {col_part}"
    except Exception:
        return ""
    return ""


def build_evidence_context(evidence_rows: Sequence[Mapping[str, Any] | Any]) -> tuple[list[str], str]:
    codes = [_clean(_value(ev, "code", "")) for ev in evidence_rows]
    codes = [code for code in codes if code]
    labels = []
    for ev in evidence_rows[:6]:
        code = _clean(_value(ev, "code", ""))
        name = _clean(_value(ev, "original_name", ""))
        note = _clean(_value(ev, "note", ""))
        if code:
            labels.append(f"{code} ({_clip(name or note or 'kanıt kaydı', 90)})")
    return codes, ", ".join(labels)


def build_table_context(table_rows: Sequence[Mapping[str, Any] | Any]) -> tuple[list[str], str]:
    names = [_clean(_value(t, "table_name", "")) for t in table_rows]
    names = [name for name in names if name]
    snapshots = []
    for table in table_rows[:3]:
        name = _clean(_value(table, "table_name", "Tablo"))
        snap = _extract_table_snapshot(table)
        snapshots.append(f"{name}: {snap}" if snap else name)
    return names, "; ".join(snapshots)


def build_puko_narrative(section: Mapping[str, Any] | Any) -> str:
    """Turn Planla/Uygula/Kontrol/Önlem fields into a formal report paragraph."""
    parts = []
    fields = [
        ("Planlama", _value(section, "planla", "")),
        ("Uygulama", _value(section, "uygula", "")),
        ("Kontrol", _value(section, "kontrol", "")),
        ("Önlem", _value(section, "onlem", "")),
    ]
    for label, value in fields:
        text = _clip(value, 320)
        if text:
            parts.append(f"{label} aşamasında {text}")
    if not parts:
        return ""
    return "PUKÖ döngüsü açısından " + " ".join(parts)


def build_metric9_competency_rows(evidence_codes: Sequence[str] | None = None) -> list[dict[str, str]]:
    """Return a discipline-specific starter table for operating-room oriented programs."""
    codes = [code for code in (evidence_codes or []) if _clean(code)]
    fallback_codes = ["9.1.K1", "9.1.K2", "9.1.K3", "9.1.K4", "9.1.K5"]
    code_pool = codes or fallback_codes

    competencies = [
        (
            "Asepsi-antisepsi kurallarını güvenli biçimde uygulama",
            "Ameliyathane Teknikleri, Cerrahi Uygulamalar, Enfeksiyon Kontrolü",
            "Beceri laboratuvarı, ameliyathane uygulaması ve staj",
            "Beceri kontrol listesi, uygulama gözlem formu, staj değerlendirme formu",
        ),
        (
            "Sterilizasyon, dezenfeksiyon ve cerrahi alan güvenliği süreçlerini yürütme",
            "Sterilizasyon İlkeleri, Cerrahi Uygulamalar, Hasta Güvenliği",
            "Sterilizasyon ünitesi gözlemi, laboratuvar uygulaması ve klinik staj",
            "Uygulama değerlendirme formu, süreç kontrol listesi",
        ),
        (
            "Cerrahi ekip içinde görev, sorumluluk ve iletişim süreçlerini yerine getirme",
            "Ameliyathane Uygulamaları, Mesleki İletişim, Sağlıkta Etik",
            "Ameliyathane stajı, ekip içi simülasyon ve vaka temelli uygulama",
            "Staj değerlendirmesi, vaka sunumu, eğitici gözlem formu",
        ),
        (
            "Cerrahi alet, cihaz ve sarf malzemelerini doğru hazırlama ve izleme",
            "Cerrahi Alet Bilgisi, Tıbbi Cihaz Kullanımı, Ameliyathane Uygulamaları",
            "Beceri laboratuvarı, cihaz hazırlık uygulaması ve klinik uygulama",
            "Beceri sınavı, demirbaş/sarf kontrol formu, uygulama rubriği",
        ),
        (
            "Hasta güvenliği ve mesleki etik ilkelerine uygun çalışma",
            "Hasta Güvenliği, Sağlık Hukuku ve Etik, Mesleki Uygulama",
            "Simülasyon, klinik staj, kalite ve güvenlik uygulamaları",
            "Rubrik, staj dosyası, olay/geri bildirim analiz formu",
        ),
    ]

    rows: list[dict[str, str]] = []
    for idx, (competency, courses, practice, assessment) in enumerate(competencies):
        rows.append({
            "Disipline Özgü Yeterlilik": competency,
            "İlişkili Ders(ler)": courses,
            "Uygulama/Lab/Staj Bağlantısı": practice,
            "Ölçme-Değerlendirme Aracı": assessment,
            "Hedef Düzey": "Program çıktısı ile uyumlu yeterli düzey",
            "Gerçekleşen Düzey": "Program verileri ve uygulama değerlendirmeleriyle doldurulacak",
            "İyileştirme Kararı": "İzleme sonuçlarına göre kurul/komisyon kararıyla güncellenecek",
            "Kanıt Kodu": code_pool[idx % len(code_pool)],
        })
    return rows


def build_evidence_based_report_draft(
    section: Mapping[str, Any] | Any,
    guide: Mapping[str, Any],
    evidence_rows: Sequence[Mapping[str, Any] | Any],
    table_rows: Sequence[Mapping[str, Any] | Any],
    target_words: int = 420,
) -> GeneratedReportDraft:
    """Create a local, evidence-controlled MEDEK report draft without inventing facts."""
    section_key = _clean(_value(section, "section_key", ""))
    section_title = _clean(_value(section, "section_title", ""))
    profile = _profile_for_section(section_key)
    question = _clean(guide.get("question", ""))
    expected_evidence = ", ".join([_clean(x) for x in guide.get("evidence", []) if _clean(x)])
    evidence_codes, evidence_context = build_evidence_context(evidence_rows)
    table_names, table_context = build_table_context(table_rows)
    puko_narrative = build_puko_narrative(section)
    existing_text = _clip(_value(section, "report_text", ""), 420)

    warnings: list[str] = []
    if not evidence_codes:
        warnings.append("Bu başlıkta kayıtlı kanıt yok; metinde kanıt kodu yerine kanıt ihtiyacı açık belirtildi.")
    if guide.get("table") and not table_names:
        warnings.append("Bu başlık için tablo bekleniyor; taslak tablo/veri girişi tamamlandıktan sonra güçlenir.")
    if not puko_narrative:
        warnings.append("PUKÖ alanları boş; taslak genel PUKÖ önerisi içerir ama gerçek izleme kararlarıyla tamamlanmalıdır.")
    if profile:
        target_words = max(target_words, 520)

    evidence_sentence = (
        f"Bu açıklama {evidence_context} kanıtlarıyla desteklenmektedir."
        if evidence_context
        else "Bu iddianın resmi kabulü için ilgili kurul kararı, yönerge, analiz raporu veya uygulama kaydı kanıt olarak yüklenmelidir."
    )
    table_sentence = (
        f"Kayıtlı tablo/veri seti olarak {table_context} kullanılmıştır."
        if table_context
        else ("Bu başlıkta beklenen tablo/veri seti henüz kaydedilmediği için nicel karşılaştırma rapora eklenmemiştir." if guide.get("table") else "")
    )
    puko_sentence = puko_narrative or (
        "PUKÖ yaklaşımında süreç önce sorumlu birim ve ölçülebilir göstergelerle planlanmalı, uygulama kayıtlarıyla yürütülmeli, sonuçlar tablo/kanıtlar üzerinden kontrol edilmeli ve gelişim alanları için iyileştirme kararı alınmalıdır."
    )

    paragraphs = [
        (
            f"{section_key}. {section_title} başlığı kapsamında programın mevcut uygulamaları MEDEK ölçüt beklentileriyle ilişkili olarak ele alınmaktadır. "
            f"Bu başlıkta yanıtlanması gereken temel beklenti şudur: {question or section_title}. "
            "Rapor dili; sürecin tanımı, sorumlu birim, uygulama yöntemi, izleme mekanizması, kanıt bağlantısı ve iyileştirme yaklaşımını birlikte gösterecek şekilde kurulmuştur."
        ),
        (
            f"Sürecin yürütülmesinde program kurulu, ilgili komisyonlar, öğrenci işleri, kalite birimi ve ders/staj uygulamalarından gelen kayıtlar birlikte değerlendirilir. "
            f"{evidence_sentence} "
            f"{table_sentence}".strip()
        ),
        (
            f"{puko_sentence} "
            "Bu nedenle metinde yer alan her iddia doğrudan kanıt kodları, tablo kayıtları veya tarihli kararlarla ilişkilendirilmelidir."
        ),
    ]
    if profile:
        paragraphs.insert(1,
            (
                f"Bu başlığın değerlendirme odağı {profile['focus']} olarak ele alınmalıdır. "
                f"Sürecin sahipleri {profile['actors']} olup, rapor metni bu aktörlerin görev paylaşımını ve karar mekanizmasını görünür kılmalıdır. "
                f"Bu nedenle beklenen kanıt zemini {profile['evidence_need']} üzerinden kurulmalı; {profile['quality_line']}."
            )
        )
        paragraphs.append(
            (
                "MEDEK üslubu açısından bu bölümde yalnızca uygulamanın varlığı değil, uygulamanın izlenebilirliği ve sürdürülebilirliği açıklanmalıdır. "
                "Metin; dönem/yıl bilgisi, sorumlu kurul veya komisyon, kullanılan veri kaynağı, ulaşılan bulgu ve varsa alınan iyileştirme kararını aynı akış içinde sunmalıdır. "
                "Sayısal değerler veya gerçekleşme düzeyleri kurum kayıtlarından doğrulandıktan sonra tablo ve kanıt kodlarıyla birlikte nihai rapora yerleştirilmelidir."
            )
        )
        for deepening in profile.get("deepening", []):
            paragraphs.append(str(deepening))
        if section_key == "9.1":
            paragraphs.append(
                "Disipline özgü ölçütlerde ayrıca mesleki yeterliliklerin ders, uygulama/laboratuvar/staj bağlantısı ve ölçme-değerlendirme aracıyla açıkça eşleştirilmesi gerekir. "
                "Tablo 9.1.1 bu amaçla kullanılmalı; her yeterlilik için hedef düzey, gerçekleşen düzey, iyileştirme kararı ve kanıt kodu ayrı satırda gösterilmelidir. "
                "Bu yaklaşım, programın mezun yeterliliklerini yalnızca beyan etmediğini, eğitim planı ve uygulama kayıtlarıyla kanıtladığını gösterir."
            )
    if existing_text:
        paragraphs.append(
            f"Mevcut metinde yer alan kuruma özgü bilgi korunmalıdır: {existing_text} "
            "Bu bilgi nihai rapora alınırken tarih, sayı, kurul/komisyon adı ve ilgili kanıt koduyla netleştirilmelidir."
        )
    if expected_evidence:
        paragraphs.append(
            f"Bu başlık için beklenen kanıt türleri {expected_evidence} olarak izlenmelidir. "
            "Eksik kanıtlar tamamlandıktan sonra rapor metni yeniden gözden geçirilmeli ve kanıt kodları cümle sonlarına eklenmelidir."
        )

    text = "\n\n".join(paragraphs)
    words = len(re.findall(r"\w+", text, flags=re.UNICODE))
    if words < max(220, target_words - 120):
        text += (
            "\n\nSonuç olarak bu başlık, yalnızca uygulamanın yapıldığını beyan etmekle sınırlı kalmamalı; uygulamanın hangi verilerle izlendiğini, "
            "hangi kurul/komisyon kararlarıyla değerlendirildiğini ve elde edilen sonuçların hangi iyileştirme adımlarına dönüştürüldüğünü açıkça göstermelidir. "
            "Bu yapı, MEDEK değerlendirmesinde izlenebilirlik, kanıt yeterliliği ve sürekli iyileştirme bütünlüğünü güçlendirir."
        )

    return GeneratedReportDraft(
        text=text.strip(),
        warnings=warnings,
        evidence_codes=evidence_codes,
        table_names=table_names,
    )


def build_criterion1_report_draft(section: Mapping[str, Any] | Any, guide: Mapping[str, Any], evidence_rows: Sequence[Mapping[str, Any] | Any], table_rows: Sequence[Mapping[str, Any] | Any]) -> GeneratedReportDraft:
    return build_evidence_based_report_draft(section, guide, evidence_rows, table_rows, target_words=680)


def build_criterion2_report_draft(section: Mapping[str, Any] | Any, guide: Mapping[str, Any], evidence_rows: Sequence[Mapping[str, Any] | Any], table_rows: Sequence[Mapping[str, Any] | Any]) -> GeneratedReportDraft:
    return build_evidence_based_report_draft(section, guide, evidence_rows, table_rows, target_words=700)


def build_criterion4_report_draft(section: Mapping[str, Any] | Any, guide: Mapping[str, Any], evidence_rows: Sequence[Mapping[str, Any] | Any], table_rows: Sequence[Mapping[str, Any] | Any]) -> GeneratedReportDraft:
    return build_evidence_based_report_draft(section, guide, evidence_rows, table_rows, target_words=720)


def build_criterion9_report_draft(section: Mapping[str, Any] | Any, guide: Mapping[str, Any], evidence_rows: Sequence[Mapping[str, Any] | Any], table_rows: Sequence[Mapping[str, Any] | Any]) -> GeneratedReportDraft:
    return build_evidence_based_report_draft(section, guide, evidence_rows, table_rows, target_words=760)


def build_specialized_report_draft(section: Mapping[str, Any] | Any, guide: Mapping[str, Any], evidence_rows: Sequence[Mapping[str, Any] | Any], table_rows: Sequence[Mapping[str, Any] | Any], target_words: int = 650) -> GeneratedReportDraft:
    """Route criteria 1, 2, 4 and 9 through dedicated MEDEK writing profiles."""
    key = _clean(_value(section, "section_key", ""))
    if key.startswith("1."):
        return build_criterion1_report_draft(section, guide, evidence_rows, table_rows)
    if key.startswith("2."):
        return build_criterion2_report_draft(section, guide, evidence_rows, table_rows)
    if key.startswith("4."):
        return build_criterion4_report_draft(section, guide, evidence_rows, table_rows)
    if key.startswith("9."):
        return build_criterion9_report_draft(section, guide, evidence_rows, table_rows)
    return build_evidence_based_report_draft(section, guide, evidence_rows, table_rows, target_words=target_words)
