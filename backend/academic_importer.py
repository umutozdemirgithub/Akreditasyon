from __future__ import annotations

import html
import json
import ipaddress
import re
import socket
import uuid
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .accreditation import infer_accreditation_profile_by_rule, normalize_accreditation_profile
from .db import get_conn, now_iso, transaction
from .repos.programs_repo import create_program_admin
from .tenancy import DEFAULT_TENANT_ID, ensure_tenant_access, require_tenant_management, save_tenant_admin, user_is_global_admin, user_tenant_id

MAX_FETCH_BYTES = 1_500_000
REQUEST_TIMEOUT_SECONDS = 12
MAX_DISCOVERY_PAGES = 32
MAX_DISCOVERY_LINKS_PER_PAGE = 28
YOKATLAS_BASE_URL = "https://yokatlas.yok.gov.tr"
YOKATLAS_MAX_JSON_BYTES = 8_000_000
YOKATLAS_PAGE_SIZE = 500
YOKATLAS_MAX_PAGES_PER_LEVEL = 12
YOKATLAS_LEVELS = ((46, "Lisans"), (47, "Önlisans"))


# Bazı üniversitelerde DNS, kampüs içinden özel IP döndürebilir.
# Doğrudan IP/localhost yine reddedilir; yalnızca kamuya ait akademik domainler için
# split-DNS özel IP çözümlemesi tolere edilir.
_TRUSTED_ACADEMIC_DOMAIN_SUFFIXES = (".edu.tr",)

_DISCOVERY_PATHS = [
    "/",
    "/tr",
    "/tr/",
    "/akademik",
    "/akademik/",
    "/akademik-birimler",
    "/akademik-birimler/",
    "/akademik-birimleri",
    "/fakultebolumler",
    "/fakultebolumler/bolumler",
    "/tr/a/fakulteler/2014/1",
    "/tr/fakulteler",
    "/tr/myolar",
    "/tr/meslek-yuksekokullari",
    "/tr/yuksekokullar",
    "/tr/bolumler",
    "/tr/programlar",
    "/birimler",
    "/birimler/",
    "/fakulteler",
    "/fakulteler/",
    "/fakultelerimiz",
    "/fakulte",
    "/fakulte/",
    "/meslek-yuksekokullari",
    "/meslek-yuksekokullari/",
    "/yuksekokullar",
    "/yuksekokullar/",
    "/bolumler",
    "/bolumler/",
    "/programlar",
    "/programlar/",
    "/egitim",
    "/egitim/",
    "/tr/akademik",
    "/tr/akademik-birimler",
    "/tr/birimler",
    "/tr/fakulteler",
    "/tr/meslek-yuksekokullari",
    "/tr/bolumler",
    "/tr/programlar",
]

_ACADEMIC_LINK_KEYWORDS = {
    "akademik": 18,
    "academic": 18,
    "birim": 14,
    "fakulte": 14,
    "faculty": 12,
    "myo": 12,
    "meslek yuksekokulu": 12,
    "meslek-yuksekokulu": 12,
    "yuksekokul": 10,
    "bolum": 9,
    "department": 9,
    "program": 9,
    "lisans": 7,
    "on lisans": 7,
    "onlisans": 7,
    "egitim": 5,
}

_BAD_LINK_KEYWORDS = {
    "haber": -14,
    "duyuru": -14,
    "etkinlik": -10,
    "galeri": -10,
    "foto": -10,
    "video": -10,
    "personel": -8,
    "iletisim": -8,
    "kariyer": -8,
    "mezun": -6,
    "kutuphane": -6,
}

_SKIP_URL_EXTENSIONS = (
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".rar",
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".mp4", ".mp3", ".avi",
)

_BAD_TEXT_MARKERS = {
    "anasayfa",
    "haber",
    "haberler",
    "duyuru",
    "duyurular",
    "iletişim",
    "arama",
    "personel",
    "öğrenci bilgi sistemi",
    "kalite",
    "mevzuat",
    "yönetmelik",
    "etkinlik",
    "galeri",
    "kütüphane",
    "rektörlük",
    "uzaktan eğitim",
}

_UNIT_PATTERN = re.compile(
    r"([A-ZÇĞİÖŞÜa-zçğıöşü0-9&.,'’ ()/\-]{3,120}?(?:Fakültesi|Meslek Yüksekokulu|Yüksekokulu|Konservatuvarı|Enstitüsü))",
    flags=re.IGNORECASE,
)
_DEPARTMENT_PATTERN = re.compile(r"([A-ZÇĞİÖŞÜa-zçğıöşü0-9&.,'’ ()/\-]{3,120}?Bölümü)", flags=re.IGNORECASE)
_PROGRAM_PATTERN = re.compile(
    r"([A-ZÇĞİÖŞÜa-zçğıöşü0-9&.,'’ ()/\-]{3,100}?(?:Programı|Mühendisliği|Öğretmenliği|Teknikleri|Hizmetleri|Yönetimi|Hemşirelik|Ebelik|Tıp|Eczacılık|İlahiyat|Gazetecilik|Odyometri|Anestezi|Radyoterapi|Fizyoterapi|Diyetetik|Aşçılık|Adalet|Mimarlık|Sosyoloji|Psikoloji|İşletme|İktisat))",
    flags=re.IGNORECASE,
)
_PREFIX_CLEANERS = [
    "Akademik Birimler",
    "Akademik",
    "Birimler",
    "Fakülteler",
    "Fakülte",
    "Yüksekokullar",
    "Meslek Yüksekokulları",
    "Bölümler",
    "Programlar",
    "Lisans Programları",
    "Ön Lisans Programları",
]


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self._skip_stack: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_stack.append(tag)
            return
        if tag == "title":
            self._in_title = True
        for key, value in attrs:
            if key in {"title", "aria-label", "alt"} and value:
                self._append(value)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._skip_stack and self._skip_stack[-1] == tag:
            self._skip_stack.pop()
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_stack:
            return
        text = _clean_spaces(data)
        if not text:
            return
        if self._in_title:
            self.title = _clean_spaces(f"{self.title} {text}")
        self._append(text)

    def _append(self, value: str) -> None:
        text = _clean_spaces(value)
        if text:
            self.lines.append(text)


class _LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._stack: list[dict[str, str]] = []
        self._skip_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_stack.append(tag)
            return
        if self._skip_stack:
            return
        if tag != "a":
            return
        data = {"href": "", "text": ""}
        for key, value in attrs:
            key = key.lower()
            if key == "href" and value:
                data["href"] = value.strip()
            elif key in {"title", "aria-label"} and value:
                data["text"] = _clean_spaces(f"{data['text']} {value}")
        if data["href"]:
            self._stack.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._skip_stack and self._skip_stack[-1] == tag:
            self._skip_stack.pop()
            return
        if tag == "a" and self._stack:
            data = self._stack.pop()
            self.links.append((data["href"], _clean_spaces(data.get("text", ""))))

    def handle_data(self, data: str) -> None:
        if self._skip_stack or not self._stack:
            return
        self._stack[-1]["text"] = _clean_spaces(f"{self._stack[-1].get('text', '')} {data}")


class _SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        _validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _clean_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip(" \t\r\n-–—|•·›»")


def _strip_noise(value: str) -> str:
    text = _clean_spaces(value)
    for prefix in _PREFIX_CLEANERS:
        text = re.sub(rf"^(?:{re.escape(prefix)}\s*)+", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^(?:[>:/|•·›»\-–—]+\s*)+", "", text).strip()
    return _clean_spaces(text)


def _valid_label(value: str, min_len: int = 4, max_len: int = 130) -> bool:
    text = _strip_noise(value)
    if len(text) < min_len or len(text) > max_len:
        return False
    lowered = text.lower()
    if any(marker == lowered or lowered.startswith(f"{marker} ") for marker in _BAD_TEXT_MARKERS):
        return False
    if text.count("/") > 4 or text.count("|") > 1:
        return False
    return True


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        clean = _strip_noise(value)
        key = clean.casefold()
        if not clean or key in seen:
            continue
        seen.add(key)
        out.append(clean)
    return out


def _is_literal_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return False


def _is_trusted_academic_hostname(host: str) -> bool:
    clean = host.strip().lower().removeprefix("www.")
    return any(clean.endswith(suffix) for suffix in _TRUSTED_ACADEMIC_DOMAIN_SUFFIXES)


def _validate_public_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Akademik yapı adresi http veya https ile başlamalıdır.")
    if not parsed.hostname:
        raise ValueError("Akademik yapı adresinde geçerli bir alan adı bulunamadı.")
    host = parsed.hostname.strip().lower()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        raise ValueError("Yerel ağ/localhost linkleri akademik yapı içe aktarma için kullanılamaz.")

    # Kullanıcı doğrudan IP yazarsa özel/ağ içi adresleri kesin reddet.
    if _is_literal_ip(host):
        ip = ipaddress.ip_address(host.strip("[]"))
        if not ip.is_global:
            raise ValueError("Güvenlik nedeniyle özel/ağ içi IP adreslerine yönlenen linkler kullanılamaz.")
        return parsed.geturl()

    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("Link alan adı çözümlenemedi.") from exc

    resolved_ips = [ipaddress.ip_address(info[4][0]) for info in infos]
    if any(ip.is_global for ip in resolved_ips):
        return parsed.geturl()

    # erciyes.edu.tr gibi kamu üniversitesi domainleri bazı ağlarda split-DNS ile
    # özel IP'ye çözülebiliyor. Bu durumda alan adı kurumsal akademik domain olduğu
    # için keşfi tamamen durdurmuyoruz; doğrudan localhost/IP hâlâ yukarıda engelli.
    if _is_trusted_academic_hostname(host):
        return parsed.geturl()

    raise ValueError("Güvenlik nedeniyle özel/ağ içi IP adreslerine yönlenen linkler kullanılamaz.")

def _ascii_fold(value: str) -> str:
    table = str.maketrans({
        "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "I": "i", "İ": "i",
        "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
    })
    return str(value or "").translate(table).casefold()


def _host_root(host: str) -> str:
    return str(host or "").strip().lower().removeprefix("www.")


def _normalize_domain_input(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    host = (parsed.hostname or "").strip().lower()
    if not host:
        raise ValueError("Kurum alan adı/domain geçerli değil.")
    return host


def _same_institution_domain(url: str, institution_domain: str) -> bool:
    host = (urlparse(url).hostname or "").strip().lower()
    if not host:
        return False
    root = _host_root(institution_domain)
    other = _host_root(host)
    return other == root or other.endswith(f".{root}")


def _candidate_academic_urls_for_domain(domain: str) -> list[str]:
    host = _normalize_domain_input(domain)
    if not host:
        return []
    root = _host_root(host)
    hosts = [host]
    if host.startswith("www."):
        hosts.append(root)
    else:
        hosts.append(f"www.{host}")
    for subdomain in ("ogrisl", "oidb", "obs", "ogrenci", "aday", "katalog"):
        candidate = f"{subdomain}.{root}"
        if candidate not in hosts:
            hosts.append(candidate)
    urls: list[str] = []
    seen: set[str] = set()
    for scheme in ("https", "http"):
        for candidate_host in hosts:
            for path in _DISCOVERY_PATHS:
                url = f"{scheme}://{candidate_host}{path}"
                if url not in seen:
                    seen.add(url)
                    urls.append(url)
    return urls


def _score_academic_link(url: str, text: str = "") -> int:
    parsed = urlparse(url)
    path = parsed.path.lower()
    if parsed.scheme not in {"http", "https"}:
        return -100
    if path.endswith(_SKIP_URL_EXTENSIONS):
        return -100
    folded = _ascii_fold(f"{url} {text}").replace("_", " ").replace("/", " ").replace("-", " ")
    score = 0
    for keyword, weight in _ACADEMIC_LINK_KEYWORDS.items():
        if keyword in folded:
            score += weight
    for keyword, weight in _BAD_LINK_KEYWORDS.items():
        if keyword in folded:
            score += weight
    return score


def _extract_academic_links(html_text: str, base_url: str, institution_domain: str) -> list[tuple[int, str]]:
    parser = _LinkExtractor()
    parser.feed(html_text or "")
    candidates: dict[str, int] = {}
    for href, text in parser.links:
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        clean_url = parsed._replace(fragment="").geturl()
        if not _same_institution_domain(clean_url, institution_domain):
            continue
        score = _score_academic_link(clean_url, text)
        if score < 6:
            continue
        candidates[clean_url] = max(candidates.get(clean_url, -100), score)
    ranked = sorted(((score, url) for url, score in candidates.items()), reverse=True)
    return ranked[:MAX_DISCOVERY_LINKS_PER_PAGE]


def _catalog_relevance_score(catalog: dict[str, Any], source_url: str = "") -> int:
    summary = catalog.get("summary", {}) if isinstance(catalog, dict) else {}
    unit_count = int(summary.get("unit_count") or 0)
    department_count = int(summary.get("department_count") or 0)
    program_count = int(summary.get("program_count") or 0)
    score = unit_count * 8 + department_count * 6 + program_count * 2
    score += max(_score_academic_link(source_url, str(catalog.get("title", "") if isinstance(catalog, dict) else "")), 0)
    return score


def merge_academic_catalogs(catalogs: list[dict[str, Any]]) -> dict[str, Any]:
    merged_units: dict[str, dict[str, Any]] = {}
    for catalog in catalogs:
        for unit in catalog.get("units", []) if isinstance(catalog, dict) else []:
            faculty_name = _strip_noise(unit.get("faculty_name", ""))
            if not faculty_name:
                continue
            faculty_key = faculty_name.casefold()
            target_unit = merged_units.setdefault(
                faculty_key,
                {
                    "faculty_name": faculty_name,
                    "accreditation_profile": normalize_accreditation_profile(unit.get("accreditation_profile") or infer_accreditation_profile(faculty_name)),
                    "departments": {},
                },
            )
            for department in unit.get("departments", []):
                department_name = _strip_noise(department.get("department_name", ""))
                if not department_name:
                    continue
                department_key = department_name.casefold()
                target_department = target_unit["departments"].setdefault(department_key, {"department_name": department_name, "programs": []})
                for program in department.get("programs", []):
                    clean_program = _strip_noise(str(program))
                    if not clean_program:
                        continue
                    if clean_program.casefold() not in {item.casefold() for item in target_department["programs"]}:
                        target_department["programs"].append(clean_program)
    units: list[dict[str, Any]] = []
    for unit in merged_units.values():
        departments = []
        for department in unit.get("departments", {}).values():
            programs = _dedupe_keep_order([str(item) for item in department.get("programs", [])])
            if programs:
                departments.append({"department_name": department["department_name"], "programs": programs})
        if departments:
            units.append({
                "faculty_name": unit["faculty_name"],
                "accreditation_profile": normalize_accreditation_profile(unit.get("accreditation_profile") or infer_accreditation_profile(unit["faculty_name"])),
                "departments": departments,
            })
    department_count = sum(len(unit["departments"]) for unit in units)
    program_count = sum(len(department["programs"]) for unit in units for department in unit["departments"])
    return {
        "title": "Alan Adından Keşfedilen Akademik Yapı",
        "units": units,
        "summary": {"unit_count": len(units), "department_count": department_count, "program_count": program_count},
    }


def _yokatlas_json_request(path: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> Any:
    """YÖK Atlas tercih kılavuzu JSON API çağrısı.

    Dış paket bağımlılığı eklememek için stdlib urllib kullanılır. Path sabit
    YÖK Atlas köküne bağlanır; kullanıcı girdisi URL olarak kullanılmaz.
    """
    clean_path = "/" + str(path or "").lstrip("/")
    url = f"{YOKATLAS_BASE_URL}{clean_path}"
    payload: bytes | None = None
    headers = {
        "User-Agent": "AKYS YOKAtlasImporter/1.0 (+https://yokatlas.yok.gov.tr)",
        "Accept": "application/json,text/plain,*/*",
    }
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json;charset=UTF-8"
    request = Request(url, data=payload, headers=headers, method=method.upper())
    opener = build_opener(_SafeRedirectHandler())
    with opener.open(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:  # noqa: S310 - fixed official API host.
        raw = response.read(YOKATLAS_MAX_JSON_BYTES + 1)
    if len(raw) > YOKATLAS_MAX_JSON_BYTES:
        raise ValueError("YÖK Atlas yanıtı çok büyük; içe aktarma güvenli sınırı aşıldı.")
    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise ValueError("YÖK Atlas JSON yanıtı okunamadı.") from exc


def _items_from_yokatlas_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("content", "data", "items", "universities", "programs", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _json_get(row: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return default


def _match_key(value: str) -> str:
    text = _ascii_fold(value)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return _clean_spaces(text)


def _important_name_tokens(value: str) -> list[str]:
    ignored = {
        "universite", "universitesi", "university", "devlet", "vakif", "turkiye", "turk", "tc",
        "kayseri", "istanbul", "ankara", "izmir", "konya", "bursa", "adana", "trabzon",
    }
    return [token for token in _match_key(value).split() if len(token) > 2 and token not in ignored]


def _domain_identity_tokens(domain: str) -> list[str]:
    host = _normalize_domain_input(domain) if domain else ""
    host = host.removeprefix("www.")
    parts = [part for part in host.split(".") if part and part not in {"edu", "tr", "edu.tr", "k12", "gov", "com", "net", "org"}]
    aliases = {
        "eru": ["erciyes"],
        "erciyes": ["erciyes"],
        "beun": ["bulent", "ecevit", "zonguldak"],
        "deu": ["dokuz", "eylul"],
        "itu": ["istanbul", "teknik"],
        "odtu": ["orta", "dogu", "teknik"],
        "metu": ["orta", "dogu", "teknik"],
        "ktu": ["karadeniz", "teknik"],
        "iyte": ["izmir", "yuksek", "teknoloji"],
        "yildiz": ["yildiz", "teknik"],
        "gtu": ["gebze", "teknik"],
        "agu": ["abdullah", "gul"],
        "hacettepe": ["hacettepe"],
        "gazi": ["gazi"],
        "ege": ["ege"],
        "ankara": ["ankara"],
        "istanbul": ["istanbul"],
        "marmara": ["marmara"],
        "selcuk": ["selcuk"],
        "atauni": ["ataturk"],
        "anadolu": ["anadolu"],
        "sakarya": ["sakarya"],
        "karabuk": ["karabuk"],
        "bartin": ["bartin"],
    }
    tokens: list[str] = []
    for part in parts:
        folded = _match_key(part)
        if not folded:
            continue
        tokens.extend(aliases.get(folded, [folded]))
    return _dedupe_keep_order(tokens)


def _score_university_match(row: dict[str, Any], *, tenant_name: str = "", domain: str = "", code: str = "") -> int:
    uni_name = str(_json_get(row, "universiteAdi", "universite_adi", "name", "ad", default=""))
    key = _match_key(uni_name)
    score = 0
    name_key = _match_key(tenant_name)
    if name_key:
        if name_key == key:
            score += 150
        elif name_key in key or key in name_key:
            score += 115
        name_tokens = _important_name_tokens(tenant_name)
        if name_tokens:
            hits = sum(1 for token in name_tokens if token in key)
            score += int(80 * hits / len(name_tokens))
            if hits == len(name_tokens):
                score += 35
    domain_tokens = _domain_identity_tokens(domain)
    if domain_tokens:
        hits = sum(1 for token in domain_tokens if token in key)
        score += int(95 * hits / len(domain_tokens))
        if hits == len(domain_tokens):
            score += 30
    code_key = _match_key(code)
    if code_key and len(code_key) >= 3:
        initials = "".join(token[0] for token in key.split() if token and token not in {"universitesi", "universite"})
        if code_key == initials or code_key in key:
            score += 35
    return score


def _select_yokatlas_university(universities: list[dict[str, Any]], *, tenant_name: str = "", domain: str = "", code: str = "") -> dict[str, Any] | None:
    ranked = sorted(
        ((_score_university_match(row, tenant_name=tenant_name, domain=domain, code=code), row) for row in universities),
        key=lambda item: item[0],
        reverse=True,
    )
    if not ranked or ranked[0][0] < 55:
        return None
    return ranked[0][1]


def _yokatlas_program_department(program_name: str, level_label: str) -> str:
    clean = _strip_noise(program_name)
    clean = re.sub(r"\s*\((?:İngilizce|Arapça|Fransızca|Almanca|Rusça|Örgün Öğretim|İkinci Öğretim|Uzaktan Öğretim|Burslu|Ücretli|%\s*\d+\s*İndirimli|KKTC Uyruklu)\)\s*", " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean:
        clean = _strip_noise(program_name)
    if _ascii_fold(level_label) == "onlisans":
        return f"{clean} Programı" if not clean.casefold().endswith(" programı") else clean
    return _candidate_department_from_program(clean)


def _catalog_from_yokatlas_program_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    units: dict[str, dict[str, Any]] = {}
    for row in rows:
        faculty_name = _strip_noise(str(_json_get(row, "fymkAdi", "fymk_adi", "fakulteAdi", "fakulte_adi", default="")))
        program_name = _strip_noise(str(_json_get(row, "birimAdi", "birim_adi", "programAdi", "program_adi", default="")))
        level_label = str(_json_get(row, "birimTuruAdi", "birim_turu_adi", default=""))
        if not faculty_name or not program_name:
            continue
        if faculty_name.upper() == faculty_name and any(char.isalpha() for char in faculty_name):
            faculty_name = _title_case_tr(faculty_name)
        if program_name.upper() == program_name and any(char.isalpha() for char in program_name):
            program_name = _title_case_tr(program_name)
        profile = normalize_accreditation_profile(infer_accreditation_profile(faculty_name, program_name=program_name, degree=level_label))
        unit = units.setdefault(
            faculty_name.casefold(),
            {"faculty_name": faculty_name, "accreditation_profile": profile, "departments": {}},
        )
        department_name = _yokatlas_program_department(program_name, level_label)
        department = _ensure_department(unit, department_name)
        _add_program(department, program_name)
    normalized_units: list[dict[str, Any]] = []
    for unit in units.values():
        departments = []
        for department in unit.get("departments", {}).values():
            programs = _dedupe_keep_order([str(item) for item in department.get("programs", [])])
            if programs:
                departments.append({"department_name": department["department_name"], "programs": programs})
        if departments:
            normalized_units.append({
                "faculty_name": unit["faculty_name"],
                "accreditation_profile": normalize_accreditation_profile(unit.get("accreditation_profile") or infer_accreditation_profile(unit["faculty_name"])),
                "departments": departments,
            })
    department_count = sum(len(unit["departments"]) for unit in normalized_units)
    program_count = sum(len(department["programs"]) for unit in normalized_units for department in unit["departments"])
    return {
        "title": "YÖK Atlas Akademik Program Kataloğu",
        "units": normalized_units,
        "summary": {"unit_count": len(normalized_units), "department_count": department_count, "program_count": program_count},
    }


def _fetch_yokatlas_program_rows(university_id: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for level_id, _label in YOKATLAS_LEVELS:
        for page in range(YOKATLAS_MAX_PAGES_PER_LEVEL):
            body = {
                "filters": {
                    "puanTuru": None,
                    "universiteId": [int(university_id)],
                    "birimGrupId": [],
                    "ilKodu": [],
                    "birimTuruId": level_id,
                    "universiteTuru": None,
                    "bursOraniId": None,
                    "ogrenimTuruId": None,
                    "kilavuzKodu": None,
                    "minBasariSirasi": None,
                    "maxBasariSirasi": None,
                },
                "page": page,
                "size": YOKATLAS_PAGE_SIZE,
                "sortBy": "basariSirasi",
                "direction": "ASC",
            }
            payload = _yokatlas_json_request("/api/tercih-kilavuz/search", method="POST", body=body)
            content = _items_from_yokatlas_payload(payload)
            if not content:
                break
            rows.extend(content)
            total_pages = int(_json_get(payload, "totalPages", "total_pages", default=page + 1) or page + 1) if isinstance(payload, dict) else page + 1
            if page + 1 >= total_pages:
                break
    return rows


def discover_academic_catalog_from_yokatlas(domain: str, *, tenant_name: str = "", code: str = "") -> dict[str, Any]:
    """Kurum program kataloğunu YÖK Atlas resmi tercih kılavuzu JSON API'sinden üretir."""
    universities_payload = _yokatlas_json_request("/api/tercih-kilavuz/universiteler")
    universities = _items_from_yokatlas_payload(universities_payload)
    if not universities:
        raise ValueError("YÖK Atlas üniversite listesi alınamadı.")
    selected = _select_yokatlas_university(universities, tenant_name=tenant_name, domain=domain, code=code)
    if not selected:
        raise ValueError("YÖK Atlas üniversite listesinde bu kurum alan adı/adı ile güvenilir eşleşme bulunamadı.")
    university_id = int(_json_get(selected, "universiteId", "universite_id", "id", default=0) or 0)
    university_name = str(_json_get(selected, "universiteAdi", "universite_adi", "name", "ad", default=""))
    if not university_id:
        raise ValueError("YÖK Atlas üniversite eşleşmesinde üniversite ID değeri bulunamadı.")
    rows = _fetch_yokatlas_program_rows(university_id)
    catalog = _catalog_from_yokatlas_program_rows(rows)
    if not catalog.get("units"):
        raise ValueError("YÖK Atlas program kayıtları alındı ancak fakülte/MYO ve program yapısı çıkarılamadı.")
    source_urls = [
        f"{YOKATLAS_BASE_URL}/lisans-univ.php?u={university_id}",
        f"{YOKATLAS_BASE_URL}/onlisans-univ.php?u={university_id}",
    ]
    catalog["title"] = f"{university_name or tenant_name or domain} - YÖK Atlas Akademik Program Kataloğu"
    catalog["source"] = "YÖK Atlas"
    catalog["source_url"] = source_urls[0]
    catalog["source_urls"] = source_urls
    catalog["domain"] = _normalize_domain_input(domain) if domain else ""
    catalog["yokatlas_university_id"] = university_id
    catalog["yokatlas_university_name"] = university_name
    return catalog


def discover_academic_catalog_from_domain(domain: str) -> dict[str, Any]:
    institution_domain = _normalize_domain_input(domain)
    if not institution_domain:
        raise ValueError("Kurum alan adı/domain girilmelidir.")
    pending: dict[str, int] = {url: _score_academic_link(url) + 2 for url in _candidate_academic_urls_for_domain(institution_domain)}
    seen: set[str] = set()
    page_results: list[dict[str, Any]] = []
    last_error = ""
    attempts = 0
    fetched_pages = 0

    while pending and fetched_pages < MAX_DISCOVERY_PAGES and attempts < MAX_DISCOVERY_PAGES * 4:
        url, _hint = max(pending.items(), key=lambda item: item[1])
        attempts += 1
        pending.pop(url, None)
        parsed = urlparse(url)
        normalized_url = parsed._replace(fragment="").geturl()
        if normalized_url in seen:
            continue
        seen.add(normalized_url)
        try:
            html_text, final_url = fetch_academic_page(normalized_url)
            fetched_pages += 1
        except Exception as exc:  # noqa: BLE001 - discovery should try alternate public pages.
            last_error = str(exc)
            continue
        final_key = urlparse(final_url)._replace(fragment="").geturl()
        seen.add(final_key)
        extracted = extract_academic_catalog_from_html(html_text)
        relevance = _catalog_relevance_score(extracted, final_url)
        summary = extracted.get("summary", {})
        if relevance >= 12 and (summary.get("department_count") or summary.get("program_count")):
            page_results.append({"url": final_url, "catalog": extracted, "score": relevance})
        for link_score, link_url in _extract_academic_links(html_text, final_url, institution_domain):
            if link_url not in seen:
                # Ana sayfadan bulunan akademik linkler, statik tahmin listesine göre daha güvenilir.
                pending[link_url] = max(pending.get(link_url, -100), link_score + 40)

    if not page_results:
        detail = f" Son hata: {last_error}" if last_error else ""
        raise ValueError(f"Kurum alan adına göre fakülte/MYO, bölüm ve program sayfaları otomatik bulunamadı.{detail}")

    page_results.sort(key=lambda item: item["score"], reverse=True)
    merged = merge_academic_catalogs([item["catalog"] for item in page_results])
    if not merged.get("units"):
        raise ValueError("Kurum alanından sayfalar bulundu ancak fakülte/MYO, bölüm ve program yapısı çıkarılamadı.")
    source_urls = _dedupe_keep_order([str(item["url"]) for item in page_results])
    merged["source_url"] = source_urls[0] if source_urls else f"https://{institution_domain}"
    merged["source_urls"] = source_urls
    merged["domain"] = institution_domain
    return merged


def fetch_academic_page(url: str) -> tuple[str, str]:
    safe_url = _validate_public_url(url)
    opener = build_opener(_SafeRedirectHandler())
    request = Request(
        safe_url,
        headers={
            "User-Agent": "AKYS AcademicCatalogImporter/1.0 (+https://local.medek)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5",
        },
    )
    with opener.open(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:  # noqa: S310 - URL validated above.
        final_url = _validate_public_url(response.geturl())
        content_type = str(response.headers.get("Content-Type", "") or "")
        if content_type and "html" not in content_type and "text" not in content_type and "xml" not in content_type:
            raise ValueError("Adres HTML/metin içerik döndürmüyor. Akademik birimler veya programlar sayfası bulunamadı.")
        raw = response.read(MAX_FETCH_BYTES + 1)
    if len(raw) > MAX_FETCH_BYTES:
        raise ValueError("Adres içeriği çok büyük. Akademik birimler/programlar sayfası otomatik keşfi daraltılamadı.")
    charset_match = re.search(r"charset=([^;]+)", content_type, flags=re.IGNORECASE)
    charset = charset_match.group(1).strip() if charset_match else "utf-8"
    try:
        return raw.decode(charset, errors="replace"), final_url
    except LookupError:
        return raw.decode("utf-8", errors="replace"), final_url


def infer_accreditation_profile(faculty_name: str, department_name: str = "", program_name: str = "", degree: str = "") -> str:
    return infer_accreditation_profile_by_rule(
        degree=degree,
        faculty_name=faculty_name,
        department_name=department_name,
        program_name=program_name,
    )


def _ensure_unit(units: dict[str, dict[str, Any]], name: str) -> dict[str, Any]:
    clean = _strip_noise(name)
    if not _valid_label(clean):
        clean = "Akademik Birimler"
    profile = normalize_accreditation_profile(infer_accreditation_profile(clean))
    return units.setdefault(clean, {"faculty_name": clean, "accreditation_profile": profile, "departments": {}})


def _ensure_department(unit: dict[str, Any], name: str) -> dict[str, Any]:
    clean = _strip_noise(name)
    if not _valid_label(clean):
        clean = "Programlar"
    departments = unit.setdefault("departments", {})
    return departments.setdefault(clean, {"department_name": clean, "programs": []})


def _candidate_program_from_department(department: str) -> str:
    clean = _strip_noise(department)
    clean = re.sub(r"\s+Bölümü$", "", clean, flags=re.IGNORECASE).strip()
    return clean


def _tr_lower(value: str) -> str:
    return "".join({"I": "ı", "İ": "i"}.get(char, char) for char in str(value)).lower()


def _tr_capitalize(value: str) -> str:
    lowered = _tr_lower(value)
    if not lowered:
        return ""
    first = {"i": "İ", "ı": "I"}.get(lowered[0], lowered[0].upper())
    return first + lowered[1:]


def _title_case_tr(value: str) -> str:
    # Türkçe karakterleri bozmadan, tamamen büyük gelen YÖK/üniversite listelerini
    # okunabilir program/bölüm adına yaklaştırır.
    abbreviations = {"MYO", "İÖ", "IÖ", "DGS", "TYT", "AYT", "ALES", "YDS", "KKTC", "M.T.O.K.", "MTOK"}
    conjunctions = {"ve", "ile", "veya"}
    words = []
    for word in _clean_spaces(value).split(" "):
        if not word:
            continue
        stripped = word.strip("()")
        if stripped.upper() in abbreviations:
            rebuilt = stripped.upper().replace("IÖ", "İÖ")
            words.append(f"({rebuilt})" if word.startswith("(") and word.endswith(")") else rebuilt)
            continue
        lowered = _tr_lower(word)
        if lowered in conjunctions:
            words.append(lowered)
            continue
        if "-" in word:
            words.append("-".join(_tr_capitalize(part) for part in word.split("-")))
            continue
        words.append(_tr_capitalize(word))
    return _clean_spaces(" ".join(words))

def _candidate_department_from_program(program_name: str) -> str:
    clean = _strip_noise(program_name)
    clean = re.sub(r"\s+Programı$", "", clean, flags=re.IGNORECASE).strip() or clean
    clean = _title_case_tr(clean)
    if clean.casefold().endswith(" bölümü"):
        return clean
    if clean.casefold().endswith(" programı"):
        clean = re.sub(r"\s+Programı$", "", clean, flags=re.IGNORECASE).strip()
    return f"{clean} Bölümü"


def _looks_like_standalone_program(line: str) -> bool:
    clean = _strip_noise(line)
    if not _valid_label(clean, 3, 110):
        return False
    folded = _ascii_fold(clean)
    if any(token in folded for token in ("http", "www.", "@", "telefon", "fax", "adres", "eposta", "e posta")):
        return False
    if any(token in folded for token in ("fakultesi", "yuksekokulu", "enstitusu", "konservatuvari", "bolumu", "programi")):
        return False
    word_count = len(clean.split())
    if word_count > 9:
        return False
    education_terms = (
        "muhendisligi", "ogretmenligi", "hemsirelik", "ebelik", "iktisat", "isletme", "maliye",
        "hukuk", "tip", "eczacilik", "ilahiyat", "matematik", "fizik", "kimya", "biyoloji",
        "odyometri", "anestezi", "radyoterapi", "fizyoterapi", "diyetetik", "ascilik", "adalet",
        "mimarlik", "sosyoloji", "psikoloji", "gazetecilik", "turizm", "veteriner", "dis hekimligi",
        "cocuk gelisimi", "yasli bakimi", "ilk ve acil yardim", "ameliyathane hizmetleri",
    )
    if any(term in folded for term in education_terms):
        return True
    letters = [char for char in clean if char.isalpha()]
    uppercase_letters = [char for char in letters if char.upper() == char and char.lower() != char]
    return bool(letters) and len(uppercase_letters) / max(len(letters), 1) > 0.75


def _add_program(department: dict[str, Any], program_name: str) -> None:
    clean = _strip_noise(program_name)
    clean = re.sub(r"\s+Programı$", "", clean, flags=re.IGNORECASE).strip() or clean
    if clean.upper() == clean and any(char.isalpha() for char in clean):
        clean = _title_case_tr(clean)
    if not _valid_label(clean, 2, 110):
        return
    if clean.casefold().endswith(" bölümü"):
        clean = _candidate_program_from_department(clean)
    programs = department.setdefault("programs", [])
    if clean and clean.casefold() not in {item.casefold() for item in programs}:
        programs.append(clean)


def extract_academic_catalog_from_html(html_text: str) -> dict[str, Any]:
    parser = _TextExtractor()
    parser.feed(html_text or "")
    raw_lines = _dedupe_keep_order(parser.lines)
    lines: list[str] = []
    for line in raw_lines:
        clean = _strip_noise(line)
        if _valid_label(clean, 2, 180):
            lines.append(clean)
    units: dict[str, dict[str, Any]] = {}
    current_unit: dict[str, Any] | None = None
    current_department: dict[str, Any] | None = None

    for line in lines:
        unit_matches = [match.group(1) for match in _UNIT_PATTERN.finditer(line)]
        department_matches = [match.group(1) for match in _DEPARTMENT_PATTERN.finditer(line)]
        program_matches = [match.group(1) for match in _PROGRAM_PATTERN.finditer(line)]

        for unit_name in unit_matches:
            clean_unit = _strip_noise(unit_name)
            if clean_unit.upper() == clean_unit and any(char.isalpha() for char in clean_unit):
                clean_unit = _title_case_tr(clean_unit)
            if not _valid_label(clean_unit):
                continue
            current_unit = _ensure_unit(units, clean_unit)
            current_department = None

        if current_unit is None and (department_matches or program_matches):
            current_unit = _ensure_unit(units, "Akademik Birimler")

        for department_name in department_matches:
            if current_unit is None:
                current_unit = _ensure_unit(units, "Akademik Birimler")
            clean_department = _strip_noise(department_name)
            if clean_department.upper() == clean_department and any(char.isalpha() for char in clean_department):
                clean_department = _title_case_tr(clean_department)
            if not _valid_label(clean_department):
                continue
            current_department = _ensure_department(current_unit, clean_department)
            inferred_program = _candidate_program_from_department(clean_department)
            if inferred_program and inferred_program != clean_department:
                _add_program(current_department, inferred_program)

        for program_name in program_matches:
            if current_unit is None:
                continue
            target_department = current_department or _ensure_department(current_unit, "Programlar")
            _add_program(target_department, program_name)

        if current_unit is not None and not department_matches and not program_matches and _looks_like_standalone_program(line):
            program_name = _title_case_tr(line) if line.upper() == line else line
            target_department = current_department or _ensure_department(current_unit, _candidate_department_from_program(program_name))
            _add_program(target_department, program_name)

    normalized_units: list[dict[str, Any]] = []
    for unit in units.values():
        departments: list[dict[str, Any]] = []
        for department in unit.get("departments", {}).values():
            programs = _dedupe_keep_order(department.get("programs", []))
            if not programs:
                fallback = _candidate_program_from_department(department.get("department_name", ""))
                if fallback:
                    programs = [fallback]
            if programs:
                departments.append({"department_name": department["department_name"], "programs": programs})
        if departments:
            normalized_units.append({
                "faculty_name": unit["faculty_name"],
                "accreditation_profile": normalize_accreditation_profile(unit.get("accreditation_profile", "MEDEK")),
                "departments": departments,
            })
    department_count = sum(len(unit["departments"]) for unit in normalized_units)
    program_count = sum(len(department["programs"]) for unit in normalized_units for department in unit["departments"])
    return {
        "title": parser.title,
        "units": normalized_units,
        "summary": {"unit_count": len(normalized_units), "department_count": department_count, "program_count": program_count},
    }


def _program_exists(conn, tenant_id: str, faculty_name: str, department_name: str, program_name: str, report_year: str) -> bool:
    row = conn.execute(
        """SELECT id FROM programs
           WHERE COALESCE(tenant_id, ?) = ? AND COALESCE(deleted_at,'')=''
             AND COALESCE(faculty_name, school_name, '')=?
             AND COALESCE(department_name,'')=?
             AND program_name=? AND report_year=?""",
        (DEFAULT_TENANT_ID, tenant_id, faculty_name, department_name, program_name, report_year),
    ).fetchone()
    return bool(row)


def _upsert_faculty(conn, tenant_id: str, faculty_name: str, profile: str) -> None:
    conn.execute(
        """INSERT INTO tenant_faculties(id,tenant_id,faculty_name,accreditation_profile,is_active,created_at,updated_at,deleted_at,deleted_by)
           VALUES(?,?,?,?,?,?,?,?,?)
           ON CONFLICT(tenant_id, faculty_name) DO UPDATE SET accreditation_profile=excluded.accreditation_profile,
               is_active=1, updated_at=excluded.updated_at, deleted_at='', deleted_by=''""",
        (str(uuid.uuid4()), tenant_id, faculty_name, profile, 1, now_iso(), now_iso(), "", ""),
    )


def import_academic_catalog_admin(username: str, payload: dict[str, Any]) -> dict[str, Any]:
    actor = require_tenant_management(username)
    source_url = str(payload.get("source_url", "") or payload.get("url", "") or "").strip()
    domain_input = str(payload.get("domain", "") or "").strip()
    discovered_source_urls: list[str] = []
    if source_url:
        html_text, final_url = fetch_academic_page(source_url)
        extracted = extract_academic_catalog_from_html(html_text)
        discovered_source_urls = [final_url]
        if not domain_input:
            domain_input = str(urlparse(final_url).hostname or "")
    else:
        tenant_name_hint = str(payload.get("tenant_name", "") or payload.get("name", "") or "").strip()
        code_hint = str(payload.get("code", "") or "").strip()
        try:
            extracted = discover_academic_catalog_from_yokatlas(domain_input, tenant_name=tenant_name_hint, code=code_hint)
        except Exception as yokatlas_exc:  # noqa: BLE001 - fallback keeps legacy domain discovery available.
            try:
                extracted = discover_academic_catalog_from_domain(domain_input)
            except Exception as legacy_exc:  # noqa: BLE001
                raise ValueError(
                    "YÖK Atlas üzerinden kurumun fakülte/MYO, bölüm ve program listesi alınamadı. "
                    f"Son YÖK Atlas hatası: {yokatlas_exc}. Kurum sitesi yedek tarama hatası: {legacy_exc}"
                ) from legacy_exc
        final_url = str(extracted.get("source_url") or f"https://{extracted.get('domain')}")
        discovered_source_urls = [str(item) for item in extracted.get("source_urls", [])]
        domain_input = str(extracted.get("domain") or domain_input)
    units = extracted.get("units", [])
    if not units:
        raise ValueError("Kurum alan adına göre fakülte/MYO, bölüm ve program yapısı çıkarılamadı. Kurum sitesinin erişilebilir ve akademik katalog sayfalarının kamuya açık olduğundan emin olun.")

    tenant_id = str(payload.get("tenant_id", "") or "").strip()
    tenant_name = str(payload.get("tenant_name", "") or payload.get("name", "") or "").strip()
    code = str(payload.get("code", "") or "").strip()
    domain = str(domain_input or urlparse(final_url).hostname or "").strip()
    report_year = str(payload.get("report_year", "") or "2025").strip()
    create_programs = bool(payload.get("create_programs", True))

    if not tenant_id:
        if user_is_global_admin(actor):
            if not tenant_name:
                title = str(extracted.get("title", "") or "").split("|")[0].strip()
                tenant_name = title or domain or "İçe Aktarılan Kurum"
            tenant = save_tenant_admin(username, {"name": tenant_name, "code": code, "domain": domain, "is_active": True, "source_url": final_url})
            tenant_id = str(tenant.get("id") or "")
            tenant_name = str(tenant.get("name") or tenant_name)
        else:
            tenant_id = user_tenant_id(actor)
    else:
        ensure_tenant_access(username, tenant_id)
        if tenant_name:
            save_tenant_admin(username, {"id": tenant_id, "name": tenant_name, "code": code, "domain": domain, "is_active": True, "source_url": final_url})

    if not tenant_id:
        raise ValueError("Kurum seçilemedi veya oluşturulamadı.")

    created_programs = 0
    skipped_programs = 0
    faculty_count = 0
    normalized_units: list[dict[str, Any]] = []
    with transaction() as conn:
        try:
            conn.execute("UPDATE tenants SET source_url=?, updated_at=? WHERE id=?", (final_url, now_iso(), tenant_id))
        except Exception:
            pass
        for unit in units:
            faculty_name = _strip_noise(unit.get("faculty_name", ""))
            if not faculty_name:
                continue
            profile = normalize_accreditation_profile(unit.get("accreditation_profile") or infer_accreditation_profile(faculty_name))
            _upsert_faculty(conn, tenant_id, faculty_name, profile)
            faculty_count += 1
            normalized_departments: list[dict[str, Any]] = []
            for department in unit.get("departments", []):
                department_name = _strip_noise(department.get("department_name", ""))
                if not department_name:
                    continue
                programs = _dedupe_keep_order([str(item) for item in department.get("programs", [])])
                normalized_programs: list[str] = []
                for program_name in programs:
                    if not program_name:
                        continue
                    normalized_programs.append(program_name)
                normalized_departments.append({"department_name": department_name, "programs": normalized_programs})
            normalized_units.append({"faculty_name": faculty_name, "accreditation_profile": profile, "departments": normalized_departments})

    # Create program rows through the canonical repository path so section skeletons,
    # program-user admin assignment and activity logging stay consistent.
    if create_programs:
        for unit in normalized_units:
            faculty_name = unit["faculty_name"]
            for department in unit.get("departments", []):
                department_name = department["department_name"]
                for program_name in department.get("programs", []):
                    with get_conn() as conn:
                        exists = _program_exists(conn, tenant_id, faculty_name, department_name, program_name, report_year)
                    if exists:
                        skipped_programs += 1
                        continue
                    program_profile = normalize_accreditation_profile(infer_accreditation_profile(faculty_name, department_name, program_name))
                    create_program_admin(username, {
                        "tenant_id": tenant_id,
                        "university_name": tenant_name or domain,
                        "school_name": faculty_name,
                        "faculty_name": faculty_name,
                        "department_name": department_name,
                        "program_name": program_name,
                        "report_year": report_year,
                        "report_type": "ÖZ DEĞERLENDİRME RAPORU",
                        "accreditation_profile": program_profile,
                        "is_active": True,
                    })
                    created_programs += 1

    department_count = sum(len(unit.get("departments", [])) for unit in normalized_units)
    program_count = sum(len(department.get("programs", [])) for unit in normalized_units for department in unit.get("departments", []))
    return {
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "source": extracted.get("source", "Kurum Sitesi"),
        "source_url": final_url,
        "source_urls": discovered_source_urls,
        "faculty_count": faculty_count,
        "department_count": department_count,
        "program_count": program_count,
        "created_program_count": created_programs,
        "skipped_program_count": skipped_programs,
        "units": normalized_units,
        "summary": extracted.get("summary", {}),
    }
