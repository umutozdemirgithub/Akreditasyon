from __future__ import annotations

from backend.accreditation import ACCREDITATION_PROFILES, infer_accreditation_profile_by_rule, profile_section_template


def test_degree_based_associate_program_defaults_to_medek() -> None:
    assert infer_accreditation_profile_by_rule(degree="Önlisans", program_name="Ağız ve Diş Sağlığı") == "MEDEK"


def test_program_specific_rules_take_priority() -> None:
    cases = {
        "Bilgisayar Mühendisliği": "MÜDEK",
        "Tıp": "TEPDAD",
        "Diş Hekimliği": "DEPAD",
        "Eczacılık": "ECZAKDER",
        "Hemşirelik": "HEPDAK",
        "Ebelik": "EPDAK",
        "Fizyoterapi ve Rehabilitasyon": "FTR-AD",
        "Sağlık Yönetimi": "SAYAK",
        "Peyzaj Mimarlığı": "PEMDER",
        "Mimarlık": "MİAK",
        "Veteriner Fakültesi": "VEDEK",
        "Ziraat Mühendisliği": "ZİDEK",
        "Gastronomi ve Mutfak Sanatları": "TURAK",
        "Yeni Medya ve İletişim": "İLAD",
        "İslami İlimler": "AA",
        "Psikoloji": "TPD",
        "Rehberlik ve Psikolojik Danışmanlık": "PDR-DER",
        "Sınıf Öğretmenliği": "EPDAD",
        "Kimya": "FEDEK",
        "İşletme": "STAR",
    }
    for program, expected in cases.items():
        assert infer_accreditation_profile_by_rule(degree="Lisans", program_name=program) == expected


def test_all_profiles_have_section_templates() -> None:
    missing = [profile for profile in ACCREDITATION_PROFILES if not profile_section_template(profile)]
    assert missing == []
