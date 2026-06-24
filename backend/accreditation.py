from __future__ import annotations

from pathlib import Path
import json
import os
from typing import Any


def _ascii_key(value: str) -> str:
    return (
        str(value or "")
        .strip()
        .upper()
        .translate(str.maketrans({"İ": "I", "I": "I", "Ü": "U", "Ö": "O", "Ç": "C", "Ş": "S", "Ğ": "G"}))
    )


def _profile(label: str, association: str, prefix: str | None = None) -> dict[str, str]:
    file_prefix = prefix or _ascii_key(label).replace(" ", "_")
    return {
        "label": label,
        "association_name": association,
        "system_name": f"{label} Akreditasyon Yönetimi",
        "report_short": "ÖDR",
        "report_type": "ÖZ DEĞERLENDİRME RAPORU",
        "docx_filename": f"{file_prefix}_ODR.docx",
        "pdf_filename": f"{file_prefix}_ODR.pdf",
        "backup_filename": f"{file_prefix}_yedek.json",
        "control_filename": f"{file_prefix}_kontrol_tablosu.docx",
        "audit_filename": f"{file_prefix}_hazirlik_denetimi.docx",
    }


ACCREDITATION_PROFILES: dict[str, dict[str, str]] = {
    "MEDEK": {
        **_profile("MEDEK", "MEDEK Mesleki Eğitim Değerlendirme ve Akreditasyon Derneği"),
        "system_name": "MEDEK Kalite Yönetim Sistemi",
    },
    "MÜDEK": _profile("MÜDEK", "MÜDEK Mühendislik Eğitim Programları Değerlendirme ve Akreditasyon Derneği", "MUDEK"),
    "EPDAD": _profile("EPDAD", "EPDAD Eğitim Fakülteleri Programları Değerlendirme ve Akreditasyon Derneği"),
    "İLEDAK": _profile("İLEDAK", "İLEDAK İletişim Eğitimi Değerlendirme Akreditasyon Kurulu", "ILEDAK"),
    "SABAK": _profile("SABAK", "SABAK Sağlık Bilimleri Eğitim Programları Değerlendirme ve Akreditasyon Kurulu"),
    "AA": _profile("AA", "AA İlahiyat Fakültesi Akreditasyon Profili"),
    "SPORAK": _profile("SPORAK", "SPORAK Spor Bilimleri Eğitim Programları Akreditasyon Profili"),
    "TURAK": _profile("TURAK", "TURAK Turizm Eğitimi Değerlendirme ve Akreditasyon Kurulu"),
    "ECZAKDER": _profile("ECZAKDER", "ECZAKDER Eczacılık Eğitimi Programlarını Değerlendirme ve Akreditasyon Derneği"),
    "TEPDAD": _profile("TEPDAD", "TEPDAD Tıp Eğitimi Programlarını Değerlendirme ve Akreditasyon Derneği"),
    "DEPAD": _profile("DEPAD", "DEPAD Diş Hekimliği Eğitim Programları Akreditasyon Derneği"),
    "HEPDAK": _profile("HEPDAK", "HEPDAK Hemşirelik Eğitim Programları Değerlendirme ve Akreditasyon Derneği"),
    "EPDAK": _profile("EPDAK", "EPDAK Ebelik Eğitim Programları Değerlendirme ve Akreditasyon Derneği"),
    "FTR-AD": _profile("FTR-AD", "FTR-AD Fizyoterapi ve Rehabilitasyon Eğitim Programları Değerlendirme ve Akreditasyon Derneği", "FTR_AD"),
    "SAYAK": _profile("SAYAK", "SAYAK Sağlık Yönetimi Eğitimi Programları Değerlendirme ve Akreditasyon Derneği"),
    "MİAK": _profile("MİAK", "MİAK Mimarlık Akreditasyon Kurulu", "MIAK"),
    "PEMDER": _profile("PEMDER", "PEMDER Peyzaj Mimarlığı Eğitim Programları Akreditasyon Profili"),
    "VEDEK": _profile("VEDEK", "VEDEK Veteriner Hekimliği Eğitim Kurumları ve Programları Değerlendirme ve Akreditasyon Derneği"),
    "ZİDEK": _profile("ZİDEK", "ZİDEK Ziraat Fakülteleri Eğitim Programları Değerlendirme ve Akreditasyon Derneği", "ZIDEK"),
    "FEDEK": _profile("FEDEK", "FEDEK Fen, Edebiyat, Fen-Edebiyat, Dil ve Tarih-Coğrafya Fakülteleri Programları Değerlendirme ve Akreditasyon Derneği"),
    "STAR": _profile("STAR", "STAR Sosyal, Beşeri ve Temel Bilimler Akreditasyon ve Rating Derneği"),
    "TPD": _profile("TPD", "Türk Psikologlar Derneği Psikoloji Lisans Programları Akreditasyon Birimi"),
    "PDR-DER": _profile("PDR-DER", "Türk Psikolojik Danışma ve Rehberlik Derneği PDR-EPDAB", "PDR_DER"),
    "İLAD": _profile("İLAD", "İLAD / İLEDAK İletişim Eğitimi Değerlendirme Akreditasyon Kurulu", "ILAD"),
}

PROFILE_ALIASES = {
    "MEDEK": "MEDEK",
    "MUDEK": "MÜDEK",
    "MÜDEK": "MÜDEK",
    "EPDAD": "EPDAD",
    "ILEDAK": "İLEDAK",
    "İLEDAK": "İLEDAK",
    "ILAD": "İLAD",
    "İLAD": "İLAD",
    "SABAK": "SABAK",
    "AA": "AA",
    "SPORAK": "SPORAK",
    "TURAK": "TURAK",
    "ECZAKDER": "ECZAKDER",
    "TEPDAD": "TEPDAD",
    "DEPAD": "DEPAD",
    "DEDAK": "DEPAD",
    "HEPDAK": "HEPDAK",
    "EPDAK": "EPDAK",
    "FTR-AD": "FTR-AD",
    "FTR_AD": "FTR-AD",
    "FTRAD": "FTR-AD",
    "SAYAK": "SAYAK",
    "MIAK": "MİAK",
    "MİAK": "MİAK",
    "PEMDER": "PEMDER",
    "VEDEK": "VEDEK",
    "ZIDEK": "ZİDEK",
    "ZİDEK": "ZİDEK",
    "FEDEK": "FEDEK",
    "STAR": "STAR",
    "TPD": "TPD",
    "TURK PSIKOLOGLAR DERNEGI": "TPD",
    "TÜRK PSİKOLOGLAR DERNEĞİ": "TPD",
    "PDR-DER": "PDR-DER",
    "PDR_DER": "PDR-DER",
    "PDRDER": "PDR-DER",
    "TURK PDR-DER": "PDR-DER",
    "TÜRK PDR-DER": "PDR-DER",
    "IAA": "AA",
    "İAA": "AA",
}

BASE_GENERAL_SECTIONS = [
    "Program ve kurum tanıtımı",
    "Programın kısa tarihçesi ve önemli değişiklikler",
    "Önceki değerlendirme / akreditasyon bilgileri",
    "Program değerlendirici iletişim bilgileri",
]

BASE_APPENDIX_I = [
    "Ders bilgi paketleri",
    "Öğretim elemanı özgeçmişleri",
    "Kanıt dizini ve ek belge listesi",
]

BASE_APPENDIX_II = [
    "Kurumun genel profili",
    "Kurum kalite güvence sistemi",
    "Kurumsal altyapı ve destek hizmetleri",
]

PROFILE_CRITERIA: dict[str, list[str]] = {
    "MEDEK": [
        "Ölçüt 1. Öğrenciler",
        "Ölçüt 2. Program Eğitim Amaçları",
        "Ölçüt 3. Program Çıktıları",
        "Ölçüt 4. Sürekli İyileştirme",
        "Ölçüt 5. Eğitim Planı",
        "Ölçüt 6. Öğretim Kadrosu",
        "Ölçüt 7. Altyapı",
        "Ölçüt 8. Yönetim ve İdari Birimlerin Yapısı",
        "Ölçüt 9. Programa Özgü Ölçütler",
    ],
    "MÜDEK": [
        "Ölçüt 1. Öğrenciler",
        "Ölçüt 2. Program Eğitim Amaçları",
        "Ölçüt 3. Program Çıktıları",
        "Ölçüt 4. Sürekli İyileştirme",
        "Ölçüt 5. Eğitim Planı",
        "Ölçüt 6. Öğretim Kadrosu",
        "Ölçüt 7. Altyapı",
        "Ölçüt 8. Kurum Desteği ve Parasal Kaynaklar",
        "Ölçüt 9. Organizasyon ve Karar Alma Süreçleri",
    ],
    "SABAD": [
        "Ölçüt 1. Program Amaçları",
        "Ölçüt 2. Program Çıktıları",
        "Ölçüt 3. Eğitim Programı",
        "Ölçüt 4. Öğrenciler",
        "Ölçüt 5. Öğretim Elemanları",
        "Ölçüt 6. Altyapı ve Uygulama Alanları",
        "Ölçüt 7. Yönetim ve Kurumsal Destek",
        "Ölçüt 8. Kalite Güvencesi ve Sürekli İyileştirme",
        "Ölçüt 9. Mesleğe Özgü Ölçütler",
    ],
    "EPDAD": [
        "Ölçüt 1. Programın Tasarımı ve Onayı",
        "Ölçüt 2. Öğretim Programı",
        "Ölçüt 3. Öğrenciler",
        "Ölçüt 4. Öğretim Elemanları",
        "Ölçüt 5. Öğrenme Ortamları ve Kaynaklar",
        "Ölçüt 6. Ölçme ve Değerlendirme",
        "Ölçüt 7. Kalite Güvencesi ve Sürekli İyileştirme",
        "Ölçüt 8. Yönetim ve Organizasyon",
        "Ölçüt 9. Paydaş Katılımı ve Mezun İzleme",
    ],
    "İLEDAK": [
        "Ölçüt 1. Program Amaçları",
        "Ölçüt 2. Program Çıktıları",
        "Ölçüt 3. Eğitim Planı",
        "Ölçüt 4. Öğrenciler",
        "Ölçüt 5. Öğretim Kadrosu",
        "Ölçüt 6. Altyapı ve Uygulama Olanakları",
        "Ölçüt 7. Kurum Desteği ve Yönetim",
        "Ölçüt 8. Kalite Güvencesi",
        "Ölçüt 9. İletişim Alanına Özgü Ölçütler",
    ],
    "SABAK": [
        "Ölçüt 1. Program Amaçları",
        "Ölçüt 2. Program Çıktıları",
        "Ölçüt 3. Eğitim Programı",
        "Ölçüt 4. Öğrenciler",
        "Ölçüt 5. Öğretim Elemanları",
        "Ölçüt 6. Klinik / Uygulama Alanları ve Altyapı",
        "Ölçüt 7. Yönetim ve Kurumsal Destek",
        "Ölçüt 8. Kalite Güvencesi",
        "Ölçüt 9. Sağlık Alanına Özgü Ölçütler",
    ],
    "EDEK": [
        "Ölçüt 1. Program Amaçları",
        "Ölçüt 2. Program Çıktıları",
        "Ölçüt 3. Öğretim Programı",
        "Ölçüt 4. Öğrenciler",
        "Ölçüt 5. Öğretim Kadrosu",
        "Ölçüt 6. Altyapı ve Kaynaklar",
        "Ölçüt 7. Bilimsel / Sanatsal Etkinlikler",
        "Ölçüt 8. Yönetim ve Kalite Güvencesi",
        "Ölçüt 9. Disipline Özgü Ölçütler",
    ],
    "AA": [
        "Ölçüt 1. Misyon ve Program Amaçları",
        "Ölçüt 2. Program Çıktıları",
        "Ölçüt 3. Müfredat ve Ders İçerikleri",
        "Ölçüt 4. Öğrenciler",
        "Ölçüt 5. Öğretim Elemanları",
        "Ölçüt 6. Uygulama ve Mesleki Yeterlilikler",
        "Ölçüt 7. Fiziki ve Teknolojik Altyapı",
        "Ölçüt 8. Yönetim, Kalite Güvencesi ve Sürekli İyileştirme",
        "Ölçüt 9. İlahiyat Alanına Özgü Ölçütler",
    ],
    "SPORAK": [
        "Ölçüt 1. Program Amaçları",
        "Ölçüt 2. Program Çıktıları",
        "Ölçüt 3. Eğitim Planı",
        "Ölçüt 4. Öğrenciler",
        "Ölçüt 5. Öğretim Elemanları",
        "Ölçüt 6. Spor Tesisleri ve Uygulama Alanları",
        "Ölçüt 7. Yönetim ve Kurumsal Destek",
        "Ölçüt 8. Kalite Güvencesi",
        "Ölçüt 9. Spor Alanına Özgü Ölçütler",
    ],
    "TURAK": [
        "Ölçüt 1. Program Amaçları",
        "Ölçüt 2. Program Çıktıları",
        "Ölçüt 3. Eğitim Planı",
        "Ölçüt 4. Öğrenciler",
        "Ölçüt 5. Öğretim Elemanları",
        "Ölçüt 6. Uygulama, Staj ve Sektör İşbirliği",
        "Ölçüt 7. Altyapı ve Kaynaklar",
        "Ölçüt 8. Yönetim ve Kalite Güvencesi",
        "Ölçüt 9. Turizm Alanına Özgü Ölçütler",
    ],
    "ECZAKDER": [
        "Ölçüt 1. Misyon, Amaç ve Hedefler",
        "Ölçüt 2. Program Çıktıları",
        "Ölçüt 3. Eğitim Programı",
        "Ölçüt 4. Öğrenciler",
        "Ölçüt 5. Akademik Kadro",
        "Ölçüt 6. Laboratuvarlar ve Uygulama Altyapısı",
        "Ölçüt 7. Kurumsal Kaynaklar ve Yönetim",
        "Ölçüt 8. Değerlendirme ve Sürekli İyileştirme",
        "Ölçüt 9. Staj ve Mesleki Uygulamalar",
        "Ölçüt 10. Eczacılık Alanına Özgü Ölçütler",
    ],
    "TEPDAD": [
        "Ölçüt 1. Amaç ve Hedefler",
        "Ölçüt 2. Eğitim Programı",
        "Ölçüt 3. Öğrencilerin Değerlendirilmesi",
        "Ölçüt 4. Öğrenciler",
        "Ölçüt 5. Program Değerlendirme",
        "Ölçüt 6. Öğretim Elemanları",
        "Ölçüt 7. Eğitsel Kaynak ve Olanaklar",
        "Ölçüt 8. Yönetim ve Yürütme",
        "Ölçüt 9. Sürekli Yenilenme ve Gelişim",
    ],
    "DEPAD": [
        "Standart 1. Amaç, Hedefler ve Program Çıktıları",
        "Standart 2. Eğitim Programı ve Öğrenme-Öğretme Süreçleri",
        "Standart 3. Öğrenciler ve Öğrenci Desteği",
        "Standart 4. Ölçme, Değerlendirme ve Program Değerlendirme",
        "Standart 5. Öğretim Elemanları",
        "Standart 6. Klinik Eğitim, Uygulama Olanakları ve Hasta Güvenliği",
        "Standart 7. Altyapı, Laboratuvarlar ve Kaynaklar",
        "Standart 8. Yönetim, Kurumsal Destek ve Kalite Güvencesi",
        "Standart 9. Sürekli İyileştirme ve Mezun İzleme",
    ],
    "HEPDAK": [
        "Standart 1. Program Amaçları ve Çıktıları",
        "Standart 2. Eğitim Programı",
        "Standart 3. Öğrenciler",
        "Standart 4. Öğretim Elemanları",
        "Standart 5. Eğitim ve Uygulama Kaynakları",
        "Standart 6. Yönetim ve Organizasyon",
        "Standart 7. Kalite Güvencesi ve Sürekli İyileştirme",
        "Standart 8. Mezun İzleme ve Paydaş Katılımı",
        "Standart 9. Hemşirelik Alanına Özgü Uygulamalar",
    ],
    "EPDAK": [
        "Standart 1. Amaç, Hedef ve Program Çıktıları",
        "Standart 2. Eğitim Programı",
        "Standart 3. Öğrenciler",
        "Standart 4. Öğretim Elemanları",
        "Standart 5. Klinik / Uygulama Alanları",
        "Standart 6. Ölçme Değerlendirme",
        "Standart 7. Yönetim ve Kalite Güvencesi",
        "Standart 8. Sürekli İyileştirme",
        "Standart 9. Ebelik Alanına Özgü Ölçütler",
    ],
    "FTR-AD": [
        "Standart 1. Program Amaçları ve Çıktıları",
        "Standart 2. Eğitim Programı",
        "Standart 3. Öğrenciler ve Öğrenci Desteği",
        "Standart 4. Öğretim Elemanları",
        "Standart 5. Klinik Uygulama ve Mesleki Beceriler",
        "Standart 6. Altyapı ve Uygulama Olanakları",
        "Standart 7. Ölçme, Değerlendirme ve Program Değerlendirme",
        "Standart 8. Yönetim, Kalite Güvencesi ve Sürekli İyileştirme",
        "Standart 9. Fizyoterapi ve Rehabilitasyon Alanına Özgü Ölçütler",
    ],
    "SAYAK": [
        "Standart 1. Amaçlar ve Program Çıktıları",
        "Standart 2. Eğitim Programı",
        "Standart 3. Öğrenciler",
        "Standart 4. Öğretim Elemanları",
        "Standart 5. Uygulama, Staj ve Saha Çalışmaları",
        "Standart 6. Altyapı ve Öğrenme Kaynakları",
        "Standart 7. Yönetim ve Kurumsal Destek",
        "Standart 8. Kalite Güvencesi ve Sürekli İyileştirme",
        "Standart 9. Sağlık Yönetimi Alanına Özgü Ölçütler",
    ],
    "MİAK": [
        "Koşul 1. Programın Kimliği ve Amaçları",
        "Koşul 2. Program Çıktıları ve Yetkinlikler",
        "Koşul 3. Mimarlık Eğitimi Programı",
        "Koşul 4. Öğrenciler ve Öğrenme Kültürü",
        "Koşul 5. Öğretim Kadrosu",
        "Koşul 6. Fiziksel Kaynaklar ve Stüdyo Ortamları",
        "Koşul 7. Yönetim, Kalite Güvencesi ve Sürekli İyileştirme",
        "Koşul 8. Mesleki Uygulama, Etik ve Toplumsal Sorumluluk",
    ],
    "PEMDER": [
        "Ölçüt 1. Program Amaçları",
        "Ölçüt 2. Program Çıktıları",
        "Ölçüt 3. Eğitim Planı ve Stüdyo / Tasarım Süreçleri",
        "Ölçüt 4. Öğrenciler",
        "Ölçüt 5. Öğretim Elemanları",
        "Ölçüt 6. Uygulama Alanları, Atölye ve Teknik Altyapı",
        "Ölçüt 7. Kurumsal Destek ve Yönetim",
        "Ölçüt 8. Kalite Güvencesi ve Sürekli İyileştirme",
        "Ölçüt 9. Peyzaj Mimarlığı Alanına Özgü Ölçütler",
    ],
    "VEDEK": [
        "Ölçüt 1. Amaç ve Hedefler",
        "Ölçüt 2. Eğitim Programı",
        "Ölçüt 3. Öğrenciler ve Öğrenci Desteği",
        "Ölçüt 4. Ölçme ve Değerlendirme",
        "Ölçüt 5. Öğretim Elemanları",
        "Ölçüt 6. Klinik / Uygulama, Hayvan Hastanesi ve Laboratuvar Olanakları",
        "Ölçüt 7. Altyapı, Kaynaklar ve Güvenlik",
        "Ölçüt 8. Yönetim ve Kalite Güvencesi",
        "Ölçüt 9. Sürekli İyileştirme ve Mezun İzleme",
    ],
    "ZİDEK": [
        "Ölçüt 1. Öğrenciler",
        "Ölçüt 2. Program Eğitim Amaçları",
        "Ölçüt 3. Program Çıktıları",
        "Ölçüt 4. Eğitim Planı",
        "Ölçüt 5. Öğretim Kadrosu",
        "Ölçüt 6. Altyapı ve Uygulama Olanakları",
        "Ölçüt 7. Kurum Desteği ve Parasal Kaynaklar",
        "Ölçüt 8. Yönetim ve Karar Alma Süreçleri",
        "Ölçüt 9. Sürekli İyileştirme",
        "Ölçüt 10. Ziraat Alanına Özgü Ölçütler",
    ],
    "FEDEK": [
        "Ölçüt 1. Öğrenciler",
        "Ölçüt 2. Program Eğitim Amaçları",
        "Ölçüt 3. Program Çıktıları",
        "Ölçüt 4. Öğretim Planı",
        "Ölçüt 5. Öğretim Kadrosu",
        "Ölçüt 6. Altyapı ve Kaynaklar",
        "Ölçüt 7. Kurum Desteği ve Parasal Kaynaklar",
        "Ölçüt 8. Organizasyon ve Karar Alma Süreçleri",
        "Ölçüt 9. Sürekli İyileştirme",
        "Ölçüt 10. Programa Özgü Ölçütler",
    ],
    "STAR": [
        "Ölçüt 1. Programın Amaçları ve Çıktıları",
        "Ölçüt 2. Eğitim Programı ve Öğretim Süreci",
        "Ölçüt 3. Öğrenciler",
        "Ölçüt 4. Öğretim Elemanları",
        "Ölçüt 5. Öğrenme Kaynakları ve Altyapı",
        "Ölçüt 6. Yönetim, Organizasyon ve Kurumsal Destek",
        "Ölçüt 7. Kalite Güvencesi ve Sürekli İyileştirme",
        "Ölçüt 8. Paydaş Katılımı, Mezun İzleme ve Toplumsal Katkı",
        "Ölçüt 9. Alan / Programa Özgü Ölçütler",
    ],
    "TPD": [
        "Ölçüt 1. Amaçlar ve Program Çıktıları",
        "Ölçüt 2. Psikoloji Lisans Eğitim Programı",
        "Ölçüt 3. Öğrenciler",
        "Ölçüt 4. Öğretim Elemanları",
        "Ölçüt 5. Ölçme, Değerlendirme ve Araştırma Yetkinlikleri",
        "Ölçüt 6. Laboratuvar, Uygulama ve Öğrenme Kaynakları",
        "Ölçüt 7. Yönetim ve Kalite Güvencesi",
        "Ölçüt 8. Etik, Mesleki Gelişim ve Sürekli İyileştirme",
    ],
    "PDR-DER": [
        "Standart 1. Program Amaçları ve Ulusal Standartlarla Uyum",
        "Standart 2. Eğitim Programı ve Ders İçerikleri",
        "Standart 3. Öğrenciler ve Rehberlik Hizmetleri",
        "Standart 4. Öğretim Elemanları",
        "Standart 5. Psikolojik Danışma Uygulamaları ve Süpervizyon",
        "Standart 6. Ölçme Değerlendirme ve Program Değerlendirme",
        "Standart 7. Yönetim, Kalite Güvencesi ve Sürekli İyileştirme",
    ],
    "İLAD": [
        "Ölçüt 1. Program Amaçları",
        "Ölçüt 2. Program Çıktıları",
        "Ölçüt 3. Eğitim Planı",
        "Ölçüt 4. Öğrenciler",
        "Ölçüt 5. Öğretim Kadrosu",
        "Ölçüt 6. Altyapı ve Uygulama Olanakları",
        "Ölçüt 7. Kurum Desteği ve Yönetim",
        "Ölçüt 8. Kalite Güvencesi",
        "Ölçüt 9. İletişim Alanına Özgü Ölçütler",
    ],
}


def _criterion_short_title(title: str) -> str:
    return title.split(". ", 1)[1] if ". " in title else title


def _prefixed_item(prefix: str, main_title: str, item: str, sort_order: int) -> dict[str, Any]:
    key, title = item.split(" ", 1)
    if prefix and key.endswith("."):
        key = key[:-1]
    return {
        "section_key": f"{prefix}{key}" if prefix else key,
        "main_title": main_title,
        "section_title": title.strip(),
        "sort_order": sort_order,
    }


def _build_mudek_sections() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    order = 10
    for item in [
        "1. İletişim Bilgileri",
        "2. Program Başlıkları",
        "3. Programdaki Eğitim Dili",
        "4. Programın Kısa Tarihçesi ve Değişiklikler",
        "5. Önceki Yetersizliklerin ve Gözlemlerin Giderilmesi Amacıyla Alınan Önlemler",
    ]:
        rows.append(_prefixed_item("A.", "Programa İlişkin Genel Bilgiler", item, order))
        order += 10

    criteria_groups = [
        (
            "Ölçüt 1. Öğrenciler",
            [
                "1.1 Öğrenci Kabulleri",
                "1.2 Yatay ve Dikey Geçişler, Çift Anadal ve Ders Sayma",
                "1.3 Öğrenci Değişimi",
                "1.4 Danışmanlık ve İzleme",
                "1.5 Başarı Değerlendirmesi",
                "1.6 Mezuniyet Koşulları",
            ],
        ),
        (
            "Ölçüt 2. Program Eğitim Amaçları",
            [
                "2.1 Tanımlanan Program Eğitim Amaçları",
                "2.2a Program Eğitim Amaçlarının MÜDEK Tanımına Uyması",
                "2.2b Kurum Özgörevleriyle Tutarlılık",
                "2.2c Program Eğitim Amaçlarını Belirleme ve Güncelleme Yöntemi",
                "2.2d Program Eğitim Amaçlarının Yayımlanması",
                "2.3 Program Eğitim Amaçlarına Ulaşma",
            ],
        ),
        (
            "Ölçüt 3. Program Çıktıları",
            [
                "3.1 Tanımlanan Program Çıktıları",
                "3.2 Program Çıktılarının Ölçme ve Değerlendirme Süreci",
                "3.3 Program Çıktılarına Ulaşma",
            ],
        ),
        (
            "Ölçüt 4. Sürekli İyileştirme",
            [
                "4.1 Sürekli İyileştirme Süreci",
                "4.2 Sürekli İyileştirme Çalışmaları",
            ],
        ),
        (
            "Ölçüt 5. Eğitim Planı",
            [
                "5.1 Eğitim Planı (Müfredat)",
                "5.2 Eğitim Planını Uygulama Yöntemi",
                "5.3 Eğitim Planı Yönetim Sistemi",
                "5.4 Eğitim Planının Bileşenleri",
                "5.5 Ana Tasarım Deneyimi",
            ],
        ),
        (
            "Ölçüt 6. Öğretim Kadrosu",
            [
                "6.1 Öğretim Kadrosunun Sayıca Yeterliliği",
                "6.2 Öğretim Kadrosunun Nitelikleri",
                "6.3 Atama ve Yükseltme",
            ],
        ),
        (
            "Ölçüt 7. Altyapı",
            [
                "7.1 Eğitim için Kullanılan Alanlar ve Donanım",
                "7.2 Diğer Alanlar ve Altyapı",
                "7.3 Modern Mühendislik Araçları, Bilgisayar ve Bilişim Altyapısı",
                "7.4 Kütüphane",
                "7.5 Özel Önlemler",
            ],
        ),
        (
            "Ölçüt 8. Kurum Desteği ve Parasal Kaynaklar",
            [
                "8.1 Kurumsal Destek ve Bütçe Süreci",
                "8.2 Bütçenin Öğretim Kadrosu Açısından Yeterliliği",
                "8.3 Altyapı ve Donanım Desteği",
                "8.4 Teknik, İdari ve Hizmet Kadrosu Desteği",
            ],
        ),
        (
            "Ölçüt 9. Organizasyon ve Karar Alma Süreçleri",
            [
                "9.1 Organizasyon ve Karar Alma Süreçleri",
            ],
        ),
    ]
    for main_title, items in criteria_groups:
        for item in items:
            rows.append(_prefixed_item("", main_title, item, order))
            order += 10

    for item in [
        "I.1 Ders İzlenceleri",
        "I.2 Öğretim Elemanların Özgeçmişleri",
        "I.3 Donanım",
        "I.4 Bölüm Belge Odası",
        "I.5 Diğer Bilgiler",
    ]:
        rows.append(_prefixed_item("", "Ek I. Programa İlişkin Ek Bilgiler", item, order))
        order += 10

    for item in [
        "II.1 Kuruma İlişkin Bilgiler",
        "II.2 Fakülteye İlişkin Bilgiler",
        "II.3 Personel ve Personel Politikaları",
        "II.4 Öğretim Üyelerinin Yükleri",
        "II.5 Yarı Zamanlı ve Ek Görevli Öğretim Elemanlarının İzlenmesi",
        "II.6 Öğrenci Kayıt ve Mezuniyet Bilgileri",
        "II.7 Kredi Tanımı",
        "II.8 Kabul, Yatay ve Dikey Geçiş, Çift Anadal ve Mezuniyet Koşulları",
        "II.9 Fakülte Belge Odası",
    ]:
        rows.append(_prefixed_item("", "Ek II. Kurum Profili", item, order))
        order += 10
    return rows


def _section_row(section_key: str, main_title: str, section_title: str, sort_order: int) -> dict[str, Any]:
    return {
        "section_key": section_key,
        "main_title": main_title,
        "section_title": section_title,
        "sort_order": sort_order,
    }


def _build_epdad_sections() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    order = 10
    general_title = "Programa \u0130li\u015fkin Genel Bilgiler"
    for key, title in [
        ("A.1", "\u0130leti\u015fim Bilgileri"),
        ("A.2", "Program Ba\u015fl\u0131klar\u0131"),
        ("A.3", "Program\u0131n T\u00fcr\u00fc"),
        ("A.4", "Program\u0131n E\u011fitim Dili"),
        ("A.5", "Program\u0131n K\u0131sa Tarih\u00e7esi ve De\u011fi\u015fiklikler"),
        (
            "A.6",
            "\u00d6nceki Geli\u015fmeye A\u00e7\u0131k Y\u00f6nlerin \u0130yile\u015ftirilmesi ve G\u00fc\u00e7l\u00fc Y\u00f6nlerin S\u00fcrd\u00fcr\u00fclmesi Amac\u0131yla Yap\u0131lan \u00c7al\u0131\u015fmalar",
        ),
    ]:
        rows.append(_section_row(key, general_title, title, order))
        order += 10

    standard_areas = [
        ("1", "\u00d6\u011fretimin Planlanmas\u0131, Uygulanmas\u0131 ve De\u011ferlendirilmesi"),
        ("2", "\u00d6\u011fretim Elemanlar\u0131 ve Yeti\u015ftirilmesi"),
        ("3", "\u00d6\u011frenciler: \u00d6\u011frenci Al\u0131m\u0131, Geli\u015fimi ve Ba\u015far\u0131s\u0131, Destek ve Rehberlik Hizmetleri"),
        ("4", "Fak\u00fclte-Okul \u0130\u015f Birli\u011fi"),
        ("5", "Tesisler, \u00d6\u011frenme Ortamlar\u0131 ve Kaynaklar\u0131"),
        ("6", "Y\u00f6netim"),
        ("7", "Kalite G\u00fcvencesi"),
    ]
    for number, title in standard_areas:
        main_title = f"ES {number}. Standart Alan\u0131: {title}"
        for key, section_title in [
            (f"EBS {number}.1", "Ba\u015flang\u0131\u00e7 Standartlar\u0131"),
            (f"ESS {number}.2", "S\u00fcre\u00e7 Standartlar\u0131"),
            (f"E\u00dcS {number}.3", "\u00dcr\u00fcn Standartlar\u0131"),
            (f"ES {number}", "Standart Alan\u0131 Hakk\u0131nda De\u011ferlendirme"),
        ]:
            rows.append(_section_row(key, main_title, section_title, order))
            order += 10

    appendix_i_title = "Ek I. Programa \u0130li\u015fkin Ek Bilgiler"
    for key, title in [
        ("EK-I.1", "Lisans E\u011fitim Program\u0131"),
        ("EK-I.2", "Akademik Personel Say\u0131lar\u0131"),
        ("EK-I.3", "\u00d6\u011fretim Kadrosunun Analizi"),
        ("EK-I.4", "\u00d6\u011fretim Elemanlar\u0131 Y\u00fck \u00d6zeti"),
        ("EK-I.5", "\u00d6\u011frenci Analizleri"),
        ("EK-I.5.1", "Lisans \u00d6\u011frencilerinin Y\u00fcksek\u00f6\u011fretim Kurumlar\u0131 S\u0131nav\u0131 (YKS) Derecelerine \u0130li\u015fkin Bilgi"),
        ("EK-I.5.2", "Yatay Ge\u00e7i\u015f, Dikey Ge\u00e7i\u015f ve \u00c7ift Ana Dal Bilgileri"),
        ("EK-I.5.3", "\u00d6\u011frenci ve Mezun Say\u0131lar\u0131"),
        ("EK-I.6", "Derslere G\u00f6re \u00d6\u011frenci Say\u0131lar\u0131"),
        ("EK-I.7", "Di\u011fer Bilgiler"),
    ]:
        rows.append(_section_row(key, appendix_i_title, title, order))
        order += 10

    appendix_ii_title = "Ek II. Kurum Profili"
    for key, title in [
        ("II.1", "Kuruma \u0130li\u015fkin Bilgiler"),
        ("II.2", "Fak\u00fclteye \u0130li\u015fkin Bilgiler"),
        ("II.3", "Personel ve Personel Politikalar\u0131"),
        ("II.4", "\u00d6\u011fretim \u00dcyelerinin Y\u00fckleri"),
        ("II.5", "Yar\u0131 Zamanl\u0131 ve Ek G\u00f6revli \u00d6\u011fretim Elemanlar\u0131n\u0131n \u0130zlenmesi"),
        ("II.6", "\u00d6\u011frenci Kay\u0131t ve Mezuniyet Bilgileri"),
        ("II.7", "Kredi Tan\u0131m\u0131"),
        ("II.8", "Kabul, Yatay ve Dikey Ge\u00e7i\u015f, \u00c7ift Ana Dal ve Mezuniyet Ko\u015fullar\u0131"),
    ]:
        rows.append(_section_row(key, appendix_ii_title, title, order))
        order += 10
    return rows


def _build_profile_sections(criteria: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    order = 10
    for index, title in enumerate(BASE_GENERAL_SECTIONS, 1):
        rows.append(
            {
                "section_key": f"A.{index}",
                "main_title": "Programa İlişkin Genel Bilgiler",
                "section_title": title,
                "sort_order": order,
            }
        )
        order += 10
    for index, main_title in enumerate(criteria, 1):
        rows.append(
            {
                "section_key": f"{index}.1",
                "main_title": main_title,
                "section_title": _criterion_short_title(main_title),
                "sort_order": order,
            }
        )
        order += 10
    for index, title in enumerate(BASE_APPENDIX_I, 1):
        rows.append(
            {
                "section_key": f"EK-I.{index}",
                "main_title": "Ek I. Programa İlişkin Ek Bilgiler",
                "section_title": title,
                "sort_order": order,
            }
        )
        order += 10
    for index, title in enumerate(BASE_APPENDIX_II, 1):
        rows.append(
            {
                "section_key": f"EK-II.{index}",
                "main_title": "Ek II. Kurum Profili",
                "section_title": title,
                "sort_order": order,
            }
        )
        order += 10
    return rows


def _template_file_key(profile: str) -> str:
    return _ascii_key(profile).replace(" ", "_")


def _load_json_profile_sections(profile: str) -> list[dict[str, Any]] | None:
    if os.getenv("MEDEK_DISABLE_JSON_TEMPLATES", "").strip().lower() in {"1", "true", "yes"}:
        return None
    template_path = Path(__file__).resolve().parent / "templates" / f"{_template_file_key(profile)}.json"
    if not template_path.exists():
        return None
    try:
        payload = json.loads(template_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    sections = payload.get("sections")
    if not isinstance(sections, list):
        return None
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(sections, 1):
        if not isinstance(item, dict):
            continue
        section_key = str(item.get("section_key", "") or "").strip()
        main_title = str(item.get("main_title", "") or "").strip()
        section_title = str(item.get("section_title", "") or "").strip()
        if not section_key or not main_title or not section_title:
            continue
        rows.append({
            "section_key": section_key,
            "main_title": main_title,
            "section_title": section_title,
            "sort_order": int(item.get("sort_order") or index * 10),
        })
    return rows or None


def profile_section_guide(value: Any, section_key: str) -> dict[str, Any]:
    profile = normalize_accreditation_profile(value)
    template_path = Path(__file__).resolve().parent / "templates" / f"{_template_file_key(profile)}.json"
    if not template_path.exists():
        return {}
    try:
        payload = json.loads(template_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    sections = payload.get("sections")
    if not isinstance(sections, list):
        return {}
    clean_key = str(section_key or "").strip()
    for item in sections:
        if not isinstance(item, dict) or str(item.get("section_key", "")).strip() != clean_key:
            continue
        return {
            "question": str(item.get("guide_question") or item.get("section_title") or ""),
            "evidence": [str(value) for value in item.get("expected_evidence", []) if str(value).strip()]
            if isinstance(item.get("expected_evidence"), list)
            else [],
            "table": bool(item.get("requires_table") or item.get("required_tables")),
            "required_tables": [str(value) for value in item.get("required_tables", []) if str(value).strip()]
            if isinstance(item.get("required_tables"), list)
            else [],
            "source_document": str(item.get("source_document") or payload.get("source_document") or ""),
        }
    return {}




def _norm_text(value: Any) -> str:
    return _ascii_key(str(value or "")).casefold()


def _contains_any(text: str, patterns: list[str]) -> bool:
    normalized = _norm_text(text)
    return any(_norm_text(pattern) in normalized for pattern in patterns)


def _degree_is_associate(degree: Any, school_name: str = "") -> bool:
    value = _norm_text(degree)
    school = _norm_text(school_name)
    return any(token in value for token in ["onlisans", "on lisans", "associate", "myo", "meslek yuksekokulu"]) or "meslek yuksekokulu" in school or school.endswith(" myo") or " myo" in school


def infer_accreditation_profile_by_rule(
    degree: Any = "",
    faculty_name: str = "",
    department_name: str = "",
    program_name: str = "",
) -> str:
    """Infer default accreditation body from degree and program name.

    Rule priority intentionally favors program-specific bodies over broad field bodies.
    Associate degree / MYO programs default to MEDEK.
    """
    if _degree_is_associate(degree, faculty_name):
        return "MEDEK"
    program = str(program_name or "").strip()
    context = " ".join([str(faculty_name or ""), str(department_name or ""), program]).strip()
    source = program or context
    ordered_rules: list[tuple[str, list[str]]] = [
        ("DEPAD", ["Diş Hekimliği", "Dis Hekimligi"]),
        ("TEPDAD", ["Tıp", "Tip"]),
        ("ECZAKDER", ["Eczacılık", "Eczacilik"]),
        ("HEPDAK", ["Hemşirelik", "Hemsirelik"]),
        ("EPDAK", ["Ebelik"]),
        ("FTR-AD", ["Fizyoterapi", "Fizyoterapi ve Rehabilitasyon"]),
        ("SAYAK", ["Sağlık Yönetimi", "Saglik Yonetimi"]),
        ("PEMDER", ["Peyzaj Mimarlığı", "Peyzaj Mimarligi"]),
        ("MİAK", ["Mimarlık", "Mimarligi", "Mimarlik"]),
        ("VEDEK", ["Veteriner"]),
        ("ZİDEK", ["Ziraat", "Tarım", "Tarim"]),
        ("TURAK", ["Turizm", "Gastronomi"]),
        ("İLAD", ["İletişim", "Iletisim", "Gazetecilik", "Radyo", "Yeni Medya"]),
        ("AA", ["İlahiyat", "Ilahiyat", "İslami İlimler", "Islami Ilimler"]),
        ("PDR-DER", ["PDR", "Rehberlik ve Psikolojik Danışmanlık", "Psikolojik Danışmanlık ve Rehberlik"]),
        ("TPD", ["Psikoloji"]),
        ("EPDAD", ["Öğretmenliği", "Ogretmenligi", "Eğitimi Öğretmenliği", "Egitimi Ogretmenligi"]),
        ("FEDEK", ["Matematik", "Fizik", "Kimya", "Biyoloji", "Tarih", "Edebiyat", "Türk Dili ve Edebiyatı", "Sosyoloji"]),
        ("MÜDEK", ["Mühendisliği", "Muhendisligi", "Mühendislik", "Muhendislik"]),
        ("STAR", ["Sosyal Hizmet", "Sosyoloji", "İşletme", "Isletme", "İktisat", "Iktisat", "Kamu Yönetimi", "Kamu Yonetimi", "Maliye", "Uluslararası İlişkiler", "Siyaset Bilimi", "Hukuk", "Felsefe"]),
    ]
    for profile, patterns in ordered_rules:
        if _contains_any(source, patterns):
            return profile
    # Fallbacks from faculty/unit name for incomplete imports.
    faculty_rules: list[tuple[str, list[str]]] = [
        ("MEDEK", ["Meslek Yüksekokulu", "MYO"]),
        ("EPDAD", ["Eğitim Fakültesi"]),
        ("MÜDEK", ["Mühendislik Fakültesi"]),
        ("TEPDAD", ["Tıp Fakültesi"]),
        ("ECZAKDER", ["Eczacılık Fakültesi"]),
        ("SABAK", ["Sağlık Bilimleri Fakültesi"]),
        ("TURAK", ["Turizm Fakültesi"]),
        ("AA", ["İlahiyat Fakültesi", "İslami İlimler Fakültesi"]),
        ("İLAD", ["İletişim Fakültesi"]),
        ("SPORAK", ["Spor Bilimleri Fakültesi"]),
        ("STAR", ["İktisadi ve İdari Bilimler", "Siyasal Bilgiler", "İnsan ve Toplum", "Sosyal ve Beşeri Bilimler"]),
        ("FEDEK", ["Fen Fakültesi", "Edebiyat Fakültesi", "Fen-Edebiyat"]),
    ]
    for profile, patterns in faculty_rules:
        if _contains_any(context, patterns):
            return profile
    return "MEDEK"

def normalize_accreditation_profile(value: Any) -> str:
    raw = str(value or "").strip().upper()
    key = _ascii_key(raw)
    if raw in ACCREDITATION_PROFILES:
        return raw
    if key.startswith("AA"):
        return "AA"
    return PROFILE_ALIASES.get(key, "MEDEK")


def accreditation_profile_meta(value: Any) -> dict[str, str]:
    profile = normalize_accreditation_profile(value)
    return {**ACCREDITATION_PROFILES["MEDEK"], **ACCREDITATION_PROFILES.get(profile, {}), "key": profile}


def profile_section_template(value: Any) -> list[dict[str, Any]]:
    profile = normalize_accreditation_profile(value)
    json_rows = _load_json_profile_sections(profile)
    if json_rows:
        return [dict(row) for row in json_rows]
    if profile == "MÜDEK":
        return _build_mudek_sections()
    if profile == "EPDAD":
        return _build_epdad_sections()
    criteria = PROFILE_CRITERIA.get(profile) or PROFILE_CRITERIA["MEDEK"]
    return [dict(row) for row in _build_profile_sections(criteria)]
