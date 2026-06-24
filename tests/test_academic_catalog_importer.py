from __future__ import annotations

from backend.academic_importer import extract_academic_catalog_from_html, infer_accreditation_profile


def test_extract_academic_catalog_from_university_html() -> None:
    html = """
    <html><head><title>Örnek Üniversitesi Akademik Birimler</title></head><body>
      <h2>Mühendislik Fakültesi</h2>
      <a>Elektrik-Elektronik Mühendisliği Bölümü</a>
      <a>Elektrik-Elektronik Mühendisliği</a>
      <a>Enerji Sistemleri Mühendisliği Bölümü</a>
      <h2>Halil Bayraktar Sağlık Hizmetleri Meslek Yüksekokulu</h2>
      <a>Tıbbi Hizmetler ve Teknikler Bölümü</a>
      <a>İlk ve Acil Yardım Programı</a>
      <a>Anestezi Programı</a>
    </body></html>
    """
    payload = extract_academic_catalog_from_html(html)
    units = {unit["faculty_name"]: unit for unit in payload["units"]}

    assert "Mühendislik Fakültesi" in units
    assert units["Mühendislik Fakültesi"]["accreditation_profile"] == "MÜDEK"
    assert "Halil Bayraktar Sağlık Hizmetleri Meslek Yüksekokulu" in units
    assert units["Halil Bayraktar Sağlık Hizmetleri Meslek Yüksekokulu"]["accreditation_profile"] == "MEDEK"

    m_depts = {row["department_name"]: row for row in units["Mühendislik Fakültesi"]["departments"]}
    assert "Elektrik-Elektronik Mühendisliği Bölümü" in m_depts
    assert "Elektrik-Elektronik Mühendisliği" in m_depts["Elektrik-Elektronik Mühendisliği Bölümü"]["programs"]

    myo_depts = {row["department_name"]: row for row in units["Halil Bayraktar Sağlık Hizmetleri Meslek Yüksekokulu"]["departments"]}
    assert "Tıbbi Hizmetler ve Teknikler Bölümü" in myo_depts
    assert {"İlk ve Acil Yardım", "Anestezi"}.issubset(set(myo_depts["Tıbbi Hizmetler ve Teknikler Bölümü"]["programs"]))


def test_infer_accreditation_profile_for_common_units() -> None:
    assert infer_accreditation_profile("Mühendislik Fakültesi") == "MÜDEK"
    assert infer_accreditation_profile("Eğitim Fakültesi", program_name="Sınıf Öğretmenliği") == "EPDAD"
    assert infer_accreditation_profile("Tıp Fakültesi") == "TEPDAD"
    assert infer_accreditation_profile("İletişim Fakültesi", program_name="Gazetecilik") == "İLAD"


def test_discover_academic_catalog_from_domain_without_user_link(monkeypatch) -> None:
    import backend.academic_importer as importer

    pages = {
        "https://erciyes.edu.tr/": """
        <html><body>
          <a href="/akademik-birimler">Akademik Birimler</a>
        </body></html>
        """,
        "https://erciyes.edu.tr/akademik-birimler": """
        <html><body>
          <a href="/muhendislik-fakultesi">Mühendislik Fakültesi</a>
          <a href="/saglik-hizmetleri-myo">Halil Bayraktar Sağlık Hizmetleri Meslek Yüksekokulu</a>
        </body></html>
        """,
        "https://erciyes.edu.tr/muhendislik-fakultesi": """
        <html><head><title>Mühendislik Fakültesi</title></head><body>
          <h1>Mühendislik Fakültesi</h1>
          <a>Elektrik-Elektronik Mühendisliği Bölümü</a>
          <a>Elektrik-Elektronik Mühendisliği</a>
        </body></html>
        """,
        "https://erciyes.edu.tr/saglik-hizmetleri-myo": """
        <html><head><title>Halil Bayraktar Sağlık Hizmetleri Meslek Yüksekokulu</title></head><body>
          <h1>Halil Bayraktar Sağlık Hizmetleri Meslek Yüksekokulu</h1>
          <a>Tıbbi Hizmetler ve Teknikler Bölümü</a>
          <a>İlk ve Acil Yardım Programı</a>
        </body></html>
        """,
    }

    def fake_fetch(url: str) -> tuple[str, str]:
        normalized = url.replace("http://", "https://").rstrip("/")
        if normalized == "https://erciyes.edu.tr":
            normalized = "https://erciyes.edu.tr/"
        if normalized in pages:
            return pages[normalized], normalized
        raise ValueError("not found")

    monkeypatch.setattr(importer, "fetch_academic_page", fake_fetch)
    payload = importer.discover_academic_catalog_from_domain("erciyes.edu.tr")
    units = {unit["faculty_name"]: unit for unit in payload["units"]}

    assert "Mühendislik Fakültesi" in units
    assert "Halil Bayraktar Sağlık Hizmetleri Meslek Yüksekokulu" in units
    assert payload["source_url"].startswith("https://erciyes.edu.tr/")


def test_validate_public_url_allows_split_dns_for_edu_tr(monkeypatch) -> None:
    import socket
    import backend.academic_importer as importer

    def fake_getaddrinfo(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.10.10.10', 443))]

    monkeypatch.setattr(importer.socket, 'getaddrinfo', fake_getaddrinfo)
    assert importer._validate_public_url('https://erciyes.edu.tr/fakultebolumler/bolumler')


def test_validate_public_url_rejects_private_literal_ip() -> None:
    import pytest
    import backend.academic_importer as importer

    with pytest.raises(ValueError):
        importer._validate_public_url('http://10.0.0.5/akademik')


def test_extract_uppercase_erciyes_faculty_department_page() -> None:
    from backend.academic_importer import extract_academic_catalog_from_html

    html = '''
    <html><body>
      <h1>FAKÜLTE BÖLÜMLER</h1>
      <button>İKTİSADİ VE İDARİ BİLİMLER FAKÜLTESİ</button>
      <div>İKTİSAT</div>
      <div>İŞLETME</div>
      <div>MALİYE</div>
      <button>MÜHENDİSLİK FAKÜLTESİ</button>
      <div>ELEKTRİK-ELEKTRONİK MÜHENDİSLİĞİ</div>
      <div>MAKİNE MÜHENDİSLİĞİ</div>
    </body></html>
    '''
    payload = extract_academic_catalog_from_html(html)
    units = {unit['faculty_name']: unit for unit in payload['units']}
    assert 'İktisadi ve İdari Bilimler Fakültesi' in units
    iibf_programs = {program for department in units['İktisadi ve İdari Bilimler Fakültesi']['departments'] for program in department['programs']}
    assert {'İktisat', 'İşletme', 'Maliye'}.issubset(iibf_programs)
    muh_programs = {program for department in units['Mühendislik Fakültesi']['departments'] for program in department['programs']}
    assert 'Elektrik-Elektronik Mühendisliği' in muh_programs


def test_discover_academic_catalog_from_yokatlas_builds_units(monkeypatch) -> None:
    import backend.academic_importer as importer

    def fake_yokatlas(path: str, *, method: str = "GET", body=None):
        if path.endswith("/universiteler"):
            return [
                {"universiteId": 1035, "universiteAdi": "ERCİYES ÜNİVERSİTESİ"},
                {"universiteId": 1100, "universiteAdi": "ANKARA YILDIRIM BEYAZIT ÜNİVERSİTESİ"},
            ]
        assert path.endswith("/search")
        assert method == "POST"
        level = body["filters"]["birimTuruId"]
        if level == 46:
            return {
                "content": [
                    {"universiteId": 1035, "universiteAdi": "ERCİYES ÜNİVERSİTESİ", "fymkAdi": "Mühendislik Fakültesi", "birimAdi": "Elektrik-Elektronik Mühendisliği", "birimTuruAdi": "LISANS", "kilavuzKodu": 103510341},
                    {"universiteId": 1035, "universiteAdi": "ERCİYES ÜNİVERSİTESİ", "fymkAdi": "Eğitim Fakültesi", "birimAdi": "Türkçe Öğretmenliği", "birimTuruAdi": "LISANS", "kilavuzKodu": 103510095},
                ],
                "totalPages": 1,
            }
        return {
            "content": [
                {"universiteId": 1035, "universiteAdi": "ERCİYES ÜNİVERSİTESİ", "fymkAdi": "Halil Bayraktar Sağlık Hizmetleri Meslek Yüksekokulu", "birimAdi": "İlk ve Acil Yardım", "birimTuruAdi": "ONLISANS", "kilavuzKodu": 103550931},
            ],
            "totalPages": 1,
        }

    monkeypatch.setattr(importer, "_yokatlas_json_request", fake_yokatlas)
    payload = importer.discover_academic_catalog_from_yokatlas("erciyes.edu.tr", tenant_name="Erciyes Üniversitesi", code="ERU")
    units = {unit["faculty_name"]: unit for unit in payload["units"]}

    assert payload["source"] == "YÖK Atlas"
    assert payload["yokatlas_university_id"] == 1035
    assert "Mühendislik Fakültesi" in units
    assert units["Mühendislik Fakültesi"]["accreditation_profile"] == "MÜDEK"
    assert "Halil Bayraktar Sağlık Hizmetleri Meslek Yüksekokulu" in units
    myo_programs = {program for department in units["Halil Bayraktar Sağlık Hizmetleri Meslek Yüksekokulu"]["departments"] for program in department["programs"]}
    assert "İlk ve Acil Yardım" in myo_programs


def test_import_catalog_prefers_yokatlas_before_legacy(monkeypatch) -> None:
    import backend.academic_importer as importer

    calls = {"yokatlas": 0, "legacy": 0}

    def fake_yokatlas(domain: str, *, tenant_name: str = "", code: str = ""):
        calls["yokatlas"] += 1
        assert domain == "erciyes.edu.tr"
        assert tenant_name == "Erciyes Üniversitesi"
        return {
            "title": "Erciyes - YÖK Atlas",
            "source": "YÖK Atlas",
            "source_url": "https://yokatlas.yok.gov.tr/lisans-univ.php?u=1035",
            "source_urls": ["https://yokatlas.yok.gov.tr/lisans-univ.php?u=1035"],
            "domain": domain,
            "units": [{
                "faculty_name": "Mühendislik Fakültesi",
                "accreditation_profile": "MÜDEK",
                "departments": [{"department_name": "Elektrik-Elektronik Mühendisliği Bölümü", "programs": ["Elektrik-Elektronik Mühendisliği"]}],
            }],
            "summary": {"unit_count": 1, "department_count": 1, "program_count": 1},
        }

    def fake_legacy(domain: str):
        calls["legacy"] += 1
        raise AssertionError("legacy discovery should not run when YÖK Atlas succeeds")

    monkeypatch.setattr(importer, "discover_academic_catalog_from_yokatlas", fake_yokatlas)
    monkeypatch.setattr(importer, "discover_academic_catalog_from_domain", fake_legacy)
    monkeypatch.setattr(importer, "require_tenant_management", lambda username: {"username": username, "role": "Süper Admin"})
    monkeypatch.setattr(importer, "user_is_global_admin", lambda actor: True)
    monkeypatch.setattr(importer, "save_tenant_admin", lambda username, payload: {"id": "tenant_erciyes", "name": payload["name"]})
    monkeypatch.setattr(importer, "_program_exists", lambda *args, **kwargs: False)
    monkeypatch.setattr(importer, "_upsert_faculty", lambda *args, **kwargs: None)
    monkeypatch.setattr(importer, "create_program_admin", lambda username, payload: {"id": "program1", **payload})

    class DummyTransaction:
        def __enter__(self):
            return object()

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(importer, "transaction", lambda: DummyTransaction())
    result = importer.import_academic_catalog_admin("admin", {"tenant_name": "Erciyes Üniversitesi", "domain": "erciyes.edu.tr", "code": "ERU"})

    assert calls == {"yokatlas": 1, "legacy": 0}
    assert result["source"] == "YÖK Atlas"
    assert result["created_program_count"] == 1
