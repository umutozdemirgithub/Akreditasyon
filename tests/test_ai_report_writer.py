from __future__ import annotations

from services.ai_report_writer import build_evidence_based_report_draft, build_metric9_competency_rows, build_puko_narrative
from services.full_report_generator import build_full_report_draft_candidates
from services.report_quality import build_report_quality_scorecard


def test_evidence_based_report_draft_uses_codes_and_warns_without_tables():
    section = {
        "section_key": "1.1.1",
        "section_title": "Programa öğrenci kabul süreçleri",
        "report_text": "Programa öğrenci kabulü merkezi yerleştirme ve yatay geçiş süreçleriyle yürütülür.",
        "planla": "Başvuru koşulları ve sorumlu birimler tanımlanır.",
        "uygula": "YKS-TYT ve yatay geçiş duyuruları işletilir.",
        "kontrol": "Kontenjan ve başvuru sonuçları izlenir.",
        "onlem": "Eksikler kurul kararlarıyla iyileştirilir.",
    }
    guide = {
        "question": "Programa hangi süreçlerle öğrenci kabul edildiğini açıklayın.",
        "evidence": ["YÖK/ÖSYM yerleştirme kılavuzu", "Yatay geçiş duyurusu"],
        "table": True,
    }
    evidence = [{"code": "1.1.1.K1", "original_name": "YÖK ÖSYM kılavuzu.pdf", "note": ""}]
    draft = build_evidence_based_report_draft(section, guide, evidence, [], target_words=300)
    assert "1.1.1.K1" in draft.text
    assert "Programa hangi süreçlerle" in draft.text
    assert any("tablo" in warning.lower() for warning in draft.warnings)


def test_puko_narrative_requires_real_puko_fields():
    assert build_puko_narrative({"planla": "", "uygula": "", "kontrol": "", "onlem": ""}) == ""
    text = build_puko_narrative({"planla": "hedef belirlenir", "uygula": "uygulama yürütülür", "kontrol": "", "onlem": ""})
    assert "Planlama aşamasında" in text
    assert "Uygulama aşamasında" in text


def test_critical_section_profiles_create_longer_medek_narrative():
    section = {
        "section_key": "9.1",
        "section_title": "Disipline özgü ölçütler",
        "report_text": "",
        "planla": "Mesleki yeterlilikler program kurulu tarafından tanımlanır.",
        "uygula": "Ders, laboratuvar ve staj uygulamalarıyla yürütülür.",
        "kontrol": "Beceri kontrol listeleriyle izlenir.",
        "onlem": "Eksikler iyileştirme kararına bağlanır.",
    }
    guide = {"question": "Disipline özgü yeterlilikleri açıklayın.", "evidence": ["Beceri kontrol listesi"], "table": True}
    draft = build_evidence_based_report_draft(section, guide, [{"code": "9.1.K1", "original_name": "beceri-formu.pdf"}], [], target_words=300)
    assert "Disipline özgü ölçütlerde" in draft.text
    assert "Tablo 9.1.1" in draft.text
    assert len(draft.text.split()) > 220


def test_metric9_competency_rows_match_official_columns():
    rows = build_metric9_competency_rows(["9.1.K9"])
    assert len(rows) >= 5
    assert rows[0]["Kanıt Kodu"] == "9.1.K9"
    assert "Disipline Özgü Yeterlilik" in rows[0]
    assert "Ölçme-Değerlendirme Aracı" in rows[0]


def test_full_report_generator_creates_review_candidates_without_saving():
    section = {
        "section_key": "2.4",
        "section_title": "Program amaçlarının izlenmesi",
        "main_title": "2. Program Amaçları",
        "report_text": "",
        "planla": "",
        "uygula": "",
        "kontrol": "",
        "onlem": "",
    }
    candidates = build_full_report_draft_candidates(
        [section],
        {"2.4": {"question": "Program amaçlarını nasıl izlediğinizi açıklayın.", "evidence": ["Paydaş toplantısı"], "table": False}},
        {"2.4": [{"code": "2.4.K1", "original_name": "paydas.pdf"}]},
        {"2.4": []},
        {"2.4": {"words": 0, "score": 20, "risk": ["Metin kısa"]}},
        include_all=False,
        target_words=650,
    )
    assert len(candidates) == 1
    assert candidates[0].section_key == "2.4"
    assert "paydaş" in candidates[0].draft.text.lower()


def test_report_quality_scorecard_uses_text_evidence_puko_table_and_approval():
    section = {
        "section_key": "1.5",
        "section_title": "Öğrenci merkezli öğrenme",
        "approval_status": "Onaya Gönderildi",
    }
    rows, summary = build_report_quality_scorecard(
        [section],
        {"1.5": {"table": True}},
        {"1.5": 2},
        {"1.5": 1},
        {"1.5": {"words": 420, "puko": 4, "uncited_evidence": 0, "risk": []}},
    )
    assert rows[0]["Toplam"] >= 80
    assert summary["total"] == 1
