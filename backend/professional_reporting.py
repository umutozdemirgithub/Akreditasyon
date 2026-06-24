from __future__ import annotations

import csv
import io
import json
import re
import uuid
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from difflib import SequenceMatcher, unified_diff
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from .db import get_conn, now_iso, row_to_dict, rows_to_dicts, transaction
from .file_security import safe_download_name, safe_stored_path
from .reporting import build_final_docx, convert_docx_to_pdf
from .repositories import (
    APPROVED,
    COMPLETED,
    READY,
    REVISION,
    SUBMITTED,
    assert_program_access,
    get_program,
    get_section,
    get_settings,
    list_evidence,
    list_sections,
    list_tables,
    log_activity,
    update_section,
)
from .section_permissions import section_permission_allows

CLAUSE_TYPES = ["standart", "kanıt_yönlendirmesi", "tablo_açıklaması", "riskli_ifade", "iyileştirme"]
PACKAGE_FILENAME = "AKYS_profesyonel_rapor_paketi.zip"
AUDITOR_PACKAGE_FILENAME = "AKYS_denetci_okuma_paketi.zip"
PRO_QUALITY_TARGET = 98
PRO_TARGET_LABEL = "9.8+"

DEFAULT_CLAUSES: list[dict[str, str]] = [
    {
        "criterion_code": "1",
        "title": "Program tanımı ve amaç hizalaması",
        "clause_type": "standart",
        "content": "Programın eğitim amaçları, kurumun stratejik hedefleri ve ilgili akreditasyon ölçütleriyle uyumlu biçimde tanımlanmış; paydaş görüşleri doğrultusunda düzenli olarak gözden geçirilmiştir.",
        "tags": "program amacı,paydaş,ölçüt 1",
    },
    {
        "criterion_code": "2",
        "title": "Program çıktıları kanıt yönlendirmesi",
        "clause_type": "kanıt_yönlendirmesi",
        "content": "Bu bölümde program çıktılarının ders öğrenme çıktılarıyla ilişkisini gösteren matris, ilgili kurul kararı ve ölçme-değerlendirme sonuçları kanıt olarak referanslanmalıdır.",
        "tags": "program çıktısı,matris,kanıt",
    },
    {
        "criterion_code": "3",
        "title": "Sürekli iyileştirme cümlesi",
        "clause_type": "iyileştirme",
        "content": "Elde edilen bulgular PUKÖ döngüsü kapsamında değerlendirilmiş, iyileştirme kararları sorumlu kişiler ve hedef tarihlerle birlikte izlenebilir hale getirilmiştir.",
        "tags": "PUKÖ,iyileştirme,izleme",
    },
    {
        "criterion_code": "5",
        "title": "Öğretim planı tablo açıklaması",
        "clause_type": "tablo_açıklaması",
        "content": "Tabloda verilen öğretim planı; ders türü, kredi/AKTS yükü, zorunlu-seçmeli dağılımı ve program çıktılarına katkı düzeyi açısından bütüncül olarak değerlendirilmiştir.",
        "tags": "öğretim planı,tablo,AKTS",
    },
    {
        "criterion_code": "6",
        "title": "Öğretim kadrosu kanıt uyarısı",
        "clause_type": "riskli_ifade",
        "content": "Öğretim kadrosu yeterliliğine ilişkin kesin ifadeler; kadro listesi, ders yükü tablosu, uzmanlık alanı bilgileri ve güncel özgeçmiş kanıtlarıyla desteklenmelidir.",
        "tags": "öğretim kadrosu,risk,kanıt",
    },
]


def _loads(value: str, fallback: Any) -> Any:
    try:
        parsed = json.loads(value or "")
        return parsed if parsed is not None else fallback
    except Exception:
        return fallback


def _text(value: Any) -> str:
    return str(value or "").strip()


def _word_count(value: str) -> int:
    return len(re.findall(r"\b[\wğüşöçıİĞÜŞÖÇ-]+\b", value or "", re.UNICODE))


def _sentences(value: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?])\s+|\n+", value or "")
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _section_prefix(section_key: str) -> str:
    key = _text(section_key).upper().replace("ÖLÇÜT", "").replace("EK", "EK-")
    match = re.search(r"(EK-[IVX]+|\d+)", key)
    return match.group(1) if match else _text(section_key).split(".")[0]


def _section_quality(section: dict[str, Any], evidence_count: int, table_count: int, issues: int = 0) -> dict[str, Any]:
    text = "\n".join(_text(section.get(key)) for key in ["report_text", "planla", "uygula", "kontrol", "onlem", "notes"])
    words = _word_count(text)
    puko_count = sum(1 for key in ["planla", "uygula", "kontrol", "onlem"] if _text(section.get(key)))
    deadline = _text(section.get("deadline"))
    approval = _text(section.get("approval_status"))
    status = _text(section.get("status"))
    score = 0
    score += min(25, round(words / 12))
    score += min(20, evidence_count * 10)
    score += min(10, table_count * 5)
    score += round((puko_count / 4) * 20)
    score += 10 if status in {READY, COMPLETED} else 4 if status else 0
    score += 15 if approval == APPROVED else 9 if approval == SUBMITTED else 0
    score -= min(20, issues * 5)
    score = max(0, min(100, score))
    if approval == REVISION or score < 40:
        risk = "critical"
    elif score < 70 or evidence_count == 0 or not deadline:
        risk = "warning"
    else:
        risk = "good"
    return {
        "section_key": section.get("section_key", ""),
        "section_title": section.get("section_title", ""),
        "main_title": section.get("main_title", ""),
        "score": score,
        "risk": risk,
        "word_count": words,
        "evidence_count": evidence_count,
        "table_count": table_count,
        "puko_completion": puko_count,
        "approval_status": approval,
        "deadline": deadline,
        "issue_count": issues,
    }


def _evidence_code_map(evidence_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    for row in evidence_rows:
        code = _text(row.get("code")).lower()
        if code:
            mapping[code] = row
    return mapping


def _tables_by_section(tables: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in tables:
        grouped[_text(row.get("section_key"))].append(row)
    return grouped


def _evidence_by_section(evidence_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in evidence_rows:
        grouped[_text(row.get("section_key"))].append(row)
    with get_conn() as conn:
        links = rows_to_dicts(conn.execute("SELECT evidence_id, section_key, program_id FROM evidence_links").fetchall())
        evidence_by_id = {row.get("id"): row for row in evidence_rows}
    for link in links:
        row = evidence_by_id.get(link.get("evidence_id"))
        if row:
            grouped[_text(link.get("section_key"))].append(row)
    return grouped


def _table_rows(table: dict[str, Any]) -> list[dict[str, Any]]:
    prepared = table.get("rows")
    if isinstance(prepared, list):
        return prepared
    payload = _loads(_text(table.get("data_json")), [])
    if isinstance(payload, dict):
        columns = payload.get("columns") or []
        data = payload.get("data") or []
        if isinstance(columns, list) and isinstance(data, list):
            return [dict(zip(columns, row)) for row in data if isinstance(row, list)]
        payload = payload.get("rows", [])
    return payload if isinstance(payload, list) else []


def _number_tokens(text: str) -> list[int]:
    tokens: list[int] = []
    for raw in re.findall(r"(?<![\w])\d{1,6}(?![\w])", text or ""):
        try:
            value = int(raw)
        except Exception:
            continue
        if 2 <= value <= 100000:
            tokens.append(value)
    return tokens


def _table_number_fingerprint(tables: list[dict[str, Any]]) -> Counter[int]:
    counter: Counter[int] = Counter()
    for table in tables:
        for row in _table_rows(table):
            if isinstance(row, dict):
                raw = " ".join(_text(value) for value in row.values())
            else:
                raw = _text(row)
            counter.update(_number_tokens(raw))
    return counter


def consistency_check_payload(username: str, program_id: str) -> dict[str, Any]:
    assert_program_access(username, program_id)
    sections = list_sections(username, program_id)
    evidence_rows = list_evidence(username, program_id)
    tables = list_tables(username, program_id)
    ev_codes = _evidence_code_map(evidence_rows)
    ev_by_section = _evidence_by_section(evidence_rows)
    tb_by_section = _tables_by_section(tables)
    table_numbers = _table_number_fingerprint(tables)
    issues: list[dict[str, Any]] = []
    today = datetime.now().date()

    ref_pattern = re.compile(r"(?<![\w.-])((?:EK-[IVX]+(?:\.\d+)*|[A-Z](?:\.\d+)*|\d+(?:\.\d+)*)\.K\d+(?:\.\d+)?)(?![\w.-])", re.IGNORECASE)
    section_keys = {_text(row.get("section_key")) for row in sections}
    key_prefixes = {_section_prefix(key) for key in section_keys if key}

    for section in sections:
        skey = _text(section.get("section_key"))
        text_blob = "\n".join(_text(section.get(key)) for key in ["report_text", "planla", "uygula", "kontrol", "onlem", "notes"])
        refs = [ref.group(1) for ref in ref_pattern.finditer(text_blob)]
        for code in refs:
            if code.lower() not in ev_codes:
                issues.append({"severity": "high", "type": "missing_evidence", "section_key": skey, "message": f"Metinde {code} kanıtı geçiyor ancak kanıt arşivinde bulunamadı.", "suggestion": "Kanıtı yükleyin veya referans kodunu düzeltin."})
        for target in re.findall(r"(?:Ölçüt|Madde|Bölüm)\s+(\d+(?:\.\d+)*)", text_blob, re.IGNORECASE):
            if _section_prefix(target) not in key_prefixes and target not in section_keys:
                issues.append({"severity": "medium", "type": "cross_reference", "section_key": skey, "message": f"'{target}' çapraz referansı mevcut rapor başlıklarıyla eşleşmedi.", "suggestion": "Ölçüt/bölüm numarasını kontrol edin."})
        if len(text_blob.strip()) > 120 and not ev_by_section.get(skey):
            issues.append({"severity": "high", "type": "evidence_gap", "section_key": skey, "message": "Bu başlıkta metin var ancak bağlı kanıt bulunmuyor.", "suggestion": "Beklenen kanıtları Kanıt Arşivi üzerinden bağlayın."})
        deadline = _text(section.get("deadline"))
        if deadline:
            try:
                delta = (datetime.fromisoformat(deadline).date() - today).days
                if delta < 0 and _text(section.get("approval_status")) != APPROVED:
                    issues.append({"severity": "critical", "type": "deadline", "section_key": skey, "message": f"Son teslim tarihi {abs(delta)} gün geçmiş.", "suggestion": "Sorumlu kişiye bildirim gönderin veya takvimi güncelleyin."})
                elif 0 <= delta <= 7 and _text(section.get("approval_status")) != APPROVED:
                    issues.append({"severity": "medium", "type": "deadline", "section_key": skey, "message": f"Son teslim tarihine {delta} gün kaldı.", "suggestion": "Onay hazırlığını hızlandırın."})
            except Exception:
                issues.append({"severity": "low", "type": "deadline_format", "section_key": skey, "message": "Son teslim tarihi okunamadı.", "suggestion": "Tarihi YYYY-AA-GG formatında girin."})
        section_numbers = set(_number_tokens(text_blob))
        suspicious = [value for value in section_numbers if value >= 10 and table_numbers and value not in table_numbers and any(word in text_blob.lower() for word in ["öğrenci", "mezun", "personel", "öğretim elemanı"])]
        for value in suspicious[:4]:
            issues.append({"severity": "medium", "type": "number_consistency", "section_key": skey, "message": f"Metindeki {value} sayısı rapor tablolarında eşleşmedi.", "suggestion": "Öğrenci/mezun/personel sayılarının tüm raporda aynı olduğundan emin olun."})
        if not tb_by_section.get(skey) and any(word in text_blob.lower() for word in ["tablo", "çizelge"]):
            issues.append({"severity": "medium", "type": "table_gap", "section_key": skey, "message": "Metinde tablo/çizelge ifadesi var ancak bu başlığa bağlı tablo yok.", "suggestion": "Tablo Yönetimi ekranından ilgili tabloyu ekleyin veya referansı düzeltin."})

    by_type = Counter(item["type"] for item in issues)
    by_severity = Counter(item["severity"] for item in issues)
    return {
        "generated_at": now_iso(),
        "total_issues": len(issues),
        "by_type": dict(by_type),
        "by_severity": dict(by_severity),
        "issues": issues,
    }


def _section_issue_counts(issues: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for item in issues:
        counter[_text(item.get("section_key"))] += 1
    return counter


def _clause_scope_sql(program_id: str, section_key: str = "") -> tuple[str, list[Any]]:
    program = get_program(program_id) or {}
    tenant_id = _text(program.get("tenant_id")) or "tenant_default"
    profile = _text(program.get("accreditation_profile")) or "MEDEK"
    params: list[Any] = [tenant_id, profile, program_id]
    section_filter = ""
    if section_key:
        section_filter = " AND (COALESCE(section_key,'')='' OR section_key=?)"
        params.append(section_key)
    where = """COALESCE(deleted_at,'')='' AND status='active'
      AND (COALESCE(tenant_id,'tenant_default') IN ('global', ?) OR COALESCE(profile,'') IN ('', ?) OR COALESCE(program_id,'') IN ('', ?))"""
    return where + section_filter, params


def seed_clause_library(username: str, program_id: str) -> dict[str, Any]:
    role = assert_program_access(username, program_id)
    program = get_program(program_id) or {}
    tenant_id = _text(program.get("tenant_id")) or "tenant_default"
    profile = _text(program.get("accreditation_profile")) or "MEDEK"
    inserted = 0
    with transaction() as conn:
        for item in DEFAULT_CLAUSES:
            exists = conn.execute(
                """SELECT id FROM clause_library
                   WHERE COALESCE(deleted_at,'')='' AND tenant_id=? AND profile=? AND title=?""",
                (tenant_id, profile, item["title"]),
            ).fetchone()
            if exists:
                continue
            conn.execute(
                """INSERT INTO clause_library(
                    id, tenant_id, program_id, profile, criterion_code, title, clause_type,
                    content, tags, status, version, created_by, created_at, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()), tenant_id, "", profile, item["criterion_code"], item["title"], item["clause_type"],
                    item["content"], item["tags"], "active", 1, username, now_iso(), now_iso(),
                ),
            )
            inserted += 1
    log_activity("Clause Library seed", f"{inserted} blok", username, program_id)
    return {"inserted": inserted, "role": role}


def list_clause_library(username: str, program_id: str, section_key: str = "") -> list[dict[str, Any]]:
    assert_program_access(username, program_id)
    where, params = _clause_scope_sql(program_id, section_key)
    prefix = _section_prefix(section_key) if section_key else ""
    with get_conn() as conn:
        rows = rows_to_dicts(conn.execute(
            f"""SELECT * FROM clause_library
                WHERE {where}
                ORDER BY CASE WHEN program_id=? THEN 0 WHEN section_key=? THEN 1 ELSE 2 END,
                         criterion_code, title""",
            [*params, program_id, section_key],
        ).fetchall())
    if prefix:
        filtered = [row for row in rows if not _text(row.get("criterion_code")) or _text(row.get("criterion_code")).upper().startswith(prefix.upper()) or not _text(row.get("section_key"))]
        return filtered or rows
    return rows


def create_clause(username: str, program_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    role = assert_program_access(username, program_id)
    if role not in {"Süper Admin", "Kurum Admin", "Birim Admin", "Birim Koordinatörü", "Editör / Hazırlayıcı"}:
        raise PermissionError("Clause Library oluşturma yetkiniz yok.")
    program = get_program(program_id) or {}
    tenant_id = _text(program.get("tenant_id")) or "tenant_default"
    profile = _text(payload.get("profile")) or _text(program.get("accreditation_profile")) or "MEDEK"
    title = _text(payload.get("title"))
    content = _text(payload.get("content"))
    if not title or not content:
        raise ValueError("Başlık ve içerik zorunludur.")
    clause_type = _text(payload.get("clause_type")) or "standart"
    if clause_type not in CLAUSE_TYPES:
        clause_type = "standart"
    clause_id = str(uuid.uuid4())
    with transaction() as conn:
        conn.execute(
            """INSERT INTO clause_library(
                id, tenant_id, program_id, section_key, profile, criterion_code, title, clause_type,
                content, tags, status, version, created_by, created_at, updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                clause_id, tenant_id, _text(payload.get("program_id")) or program_id,
                _text(payload.get("section_key")), profile, _text(payload.get("criterion_code")),
                title, clause_type, content, _text(payload.get("tags")), "active", 1, username, now_iso(), now_iso(),
            ),
        )
    log_activity("Clause eklendi", title, username, program_id)
    return {"id": clause_id, "title": title, "content": content, "clause_type": clause_type}


def insert_clause_into_section(username: str, program_id: str, section_key: str, clause_id: str, position: str = "append") -> dict[str, Any]:
    role = assert_program_access(username, program_id)
    if not section_permission_allows(program_id, section_key, role, "edit_text"):
        raise PermissionError("Bu başlığa standart blok ekleme yetkiniz yok.")
    section = get_section(username, program_id, section_key)
    if not section:
        raise KeyError(section_key)
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM clause_library WHERE id=? AND COALESCE(deleted_at,'')=''", (clause_id,)).fetchone()
    clause = row_to_dict(row)
    if not clause:
        raise KeyError(clause_id)
    current = _text(section.get("report_text"))
    clause_text = _text(clause.get("content"))
    marker = f"\n\n[Şablon: {_text(clause.get('title'))}]\n{clause_text}"
    if position == "prepend":
        next_text = f"{marker.strip()}\n\n{current}".strip()
    else:
        next_text = f"{current}{marker}".strip() if current else marker.strip()
    updated = update_section(username, program_id, section_key, {**section, "report_text": next_text})
    with transaction() as conn:
        conn.execute(
            """INSERT INTO content_blocks(id, program_id, section_key, block_type, source_clause_id, sort_order, content, created_by, created_at, updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (str(uuid.uuid4()), program_id, section_key, "smart_clause", clause_id, 9999, clause_text, username, now_iso(), now_iso()),
        )
    log_activity("Clause başlığa eklendi", f"{section_key}: {clause.get('title')}", username, program_id)
    return updated


def sentence_diff_payload(username: str, program_id: str, section_key: str, base_id: str = "") -> dict[str, Any]:
    assert_program_access(username, program_id)
    current = get_section(username, program_id, section_key)
    if not current:
        raise KeyError(section_key)
    with get_conn() as conn:
        if base_id:
            row = conn.execute("SELECT * FROM section_versions WHERE id=? AND program_id=? AND section_key=?", (base_id, program_id, section_key)).fetchone()
        else:
            row = conn.execute("SELECT * FROM section_versions WHERE program_id=? AND section_key=? ORDER BY saved_at DESC LIMIT 1", (program_id, section_key)).fetchone()
    base = row_to_dict(row) or {}
    old_sentences = _sentences(_text(base.get("report_text")))
    new_sentences = _sentences(_text(current.get("report_text")))
    matcher = SequenceMatcher(a=old_sentences, b=new_sentences)
    rows: list[dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag in {"replace", "delete"}:
            for sentence in old_sentences[i1:i2]:
                rows.append({"type": "removed" if tag == "delete" else "changed_from", "sentence": sentence})
        if tag in {"replace", "insert"}:
            for sentence in new_sentences[j1:j2]:
                rows.append({"type": "added" if tag == "insert" else "changed_to", "sentence": sentence})
    unified = "\n".join(unified_diff(old_sentences, new_sentences, fromfile="önceki", tofile="güncel", lineterm=""))
    return {"section_key": section_key, "base_version": base, "diff_rows": rows, "unified_diff": unified, "changed_sentence_count": len(rows)}


def _quality_payload_from_parts(username: str, program_id: str, consistency: dict[str, Any] | None = None) -> dict[str, Any]:
    consistency = consistency or consistency_check_payload(username, program_id)
    sections = list_sections(username, program_id)
    evidence_rows = list_evidence(username, program_id)
    tables = list_tables(username, program_id)
    ev_by_section = _evidence_by_section(evidence_rows)
    tb_by_section = _tables_by_section(tables)
    issue_counts = _section_issue_counts(consistency.get("issues", []))
    heatmap = [_section_quality(row, len(ev_by_section.get(_text(row.get("section_key")), [])), len(tb_by_section.get(_text(row.get("section_key")), [])), issue_counts.get(_text(row.get("section_key")), 0)) for row in sections]
    average = round(sum(item["score"] for item in heatmap) / max(1, len(heatmap)))
    approved = sum(1 for row in sections if _text(row.get("approval_status")) == APPROVED)
    complete = sum(1 for row in sections if _text(row.get("status")) in {READY, COMPLETED} or _text(row.get("approval_status")) == APPROVED)
    evidence_coverage = round(sum(1 for item in heatmap if item["evidence_count"] > 0) / max(1, len(heatmap)) * 100)
    consistency_score = max(0, 100 - int(consistency.get("total_issues", 0)) * 4)
    score = round(average * 0.35 + (complete / max(1, len(sections)) * 100) * 0.20 + evidence_coverage * 0.20 + consistency_score * 0.20 + (approved / max(1, len(sections)) * 100) * 0.05)
    payload = {
        "generated_at": now_iso(),
        "score": max(0, min(100, score)),
        "average_section_score": average,
        "completion_percent": round(complete / max(1, len(sections)) * 100),
        "approval_percent": round(approved / max(1, len(sections)) * 100),
        "evidence_coverage_percent": evidence_coverage,
        "consistency_score": consistency_score,
        "heatmap": heatmap,
        "weak_sections": sorted([item for item in heatmap if item["risk"] != "good"], key=lambda item: item["score"])[:12],
        "strengths": [item for item in heatmap if item["score"] >= 80][:8],
        "formula": [
            {"label": "Başlık kalite ortalaması", "weight": 35},
            {"label": "Tamamlanma", "weight": 20},
            {"label": "Kanıt kapsamı", "weight": 20},
            {"label": "Tutarlılık", "weight": 20},
            {"label": "Onay oranı", "weight": 5},
        ],
    }
    payload["premium_readiness"] = _premium_readiness_payload(payload, consistency)
    return payload


def _premium_readiness_payload(quality: dict[str, Any], consistency: dict[str, Any]) -> dict[str, Any]:
    score = int(quality.get("score", 0) or 0)
    completion = int(quality.get("completion_percent", 0) or 0)
    approval = int(quality.get("approval_percent", 0) or 0)
    evidence = int(quality.get("evidence_coverage_percent", 0) or 0)
    consistency_score = int(quality.get("consistency_score", 0) or 0)
    issue_count = int(consistency.get("total_issues", 0) or 0)
    critical_count = int((consistency.get("by_severity") or {}).get("critical", 0) or 0)
    weak_sections = quality.get("weak_sections", []) or []
    requirements = [
        {"key": "score", "label": "Genel kalite 98+", "done": score >= PRO_QUALITY_TARGET, "value": score, "target": PRO_QUALITY_TARGET},
        {"key": "completion", "label": "Tamamlanma 98%+", "done": completion >= PRO_QUALITY_TARGET, "value": completion, "target": PRO_QUALITY_TARGET},
        {"key": "evidence", "label": "Kanıt kapsamı 98%+", "done": evidence >= PRO_QUALITY_TARGET, "value": evidence, "target": PRO_QUALITY_TARGET},
        {"key": "consistency", "label": "Tutarlılık 98+", "done": consistency_score >= PRO_QUALITY_TARGET and critical_count == 0, "value": consistency_score, "target": PRO_QUALITY_TARGET},
        {"key": "approval", "label": "Onay oranı 98%+", "done": approval >= PRO_QUALITY_TARGET, "value": approval, "target": PRO_QUALITY_TARGET},
        {"key": "weak_sections", "label": "Zayıf başlık kalmadı", "done": not weak_sections, "value": len(weak_sections), "target": 0},
    ]
    missing = [row for row in requirements if not row["done"]]
    return {
        "target_score": PRO_QUALITY_TARGET,
        "target_label": PRO_TARGET_LABEL,
        "ready": not missing,
        "status": "ready" if not missing else "near" if score >= 85 and critical_count == 0 else "work",
        "score_gap": max(0, PRO_QUALITY_TARGET - score),
        "issue_count": issue_count,
        "critical_count": critical_count,
        "requirements": requirements,
        "next_actions": [
            "Kritik tutarlılık uyarılarını kapatın." if row["key"] == "consistency" else
            "Zayıf başlıkları 98+ kaliteye taşıyın." if row["key"] == "weak_sections" else
            f"{row['label']} hedefini tamamlayın."
            for row in missing[:6]
        ],
    }


def report_quality_payload(username: str, program_id: str) -> dict[str, Any]:
    assert_program_access(username, program_id)
    consistency = consistency_check_payload(username, program_id)
    payload = _quality_payload_from_parts(username, program_id, consistency)
    with transaction() as conn:
        conn.execute(
            "INSERT INTO report_quality_snapshots(id, program_id, score, payload_json, created_by, created_at) VALUES(?,?,?,?,?,?)",
            (str(uuid.uuid4()), program_id, int(payload.get("score", 0)), json.dumps(payload, ensure_ascii=False), username, now_iso()),
        )
    return payload


def mock_audit_payload(username: str, program_id: str, sample_size: int = 5) -> dict[str, Any]:
    assert_program_access(username, program_id)
    consistency = consistency_check_payload(username, program_id)
    quality = _quality_payload_from_parts(username, program_id, consistency)
    weak = quality.get("weak_sections", [])
    fallback = sorted(quality.get("heatmap", []), key=lambda row: (row.get("score", 0), row.get("section_key", "")))
    selected = (weak or fallback)[: max(1, min(12, int(sample_size or 5)))]
    questions: list[dict[str, Any]] = []
    issues_by_section: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for issue in consistency.get("issues", []):
        issues_by_section[_text(issue.get("section_key"))].append(issue)
    for item in selected:
        skey = _text(item.get("section_key"))
        local_issues = issues_by_section.get(skey, [])[:3]
        questions.append({
            "section_key": skey,
            "section_title": item.get("section_title", ""),
            "risk": item.get("risk", "warning"),
            "score": item.get("score", 0),
            "auditor_question": "Bu bölümde verilen iddiaları hangi güncel kanıtlarla doğrulayabilirsiniz?" if not local_issues else local_issues[0].get("message", "Bu başlığın kanıt ve tutarlılık durumunu açıklayın."),
            "expected_preparation": [
                "İlgili kanıt dosyalarını açıp kodları kontrol edin.",
                "Tablolardaki sayılar ile metindeki ifadeleri karşılaştırın.",
                "PUKÖ açıklamalarında sorumlu kişi ve hedef tarih bulunduğunu doğrulayın.",
            ],
            "related_issues": local_issues,
        })
    return {"generated_at": now_iso(), "mode": "mock_audit", "sample_size": len(questions), "questions": questions, "quality_score": quality.get("score", 0)}


def professional_reporting_payload(username: str, program_id: str) -> dict[str, Any]:
    assert_program_access(username, program_id)
    seed_clause_library(username, program_id)
    consistency = consistency_check_payload(username, program_id)
    quality = _quality_payload_from_parts(username, program_id, consistency)
    sections = list_sections(username, program_id)
    clauses = list_clause_library(username, program_id)
    return {
        "generated_at": now_iso(),
        "quality": quality,
        "consistency": consistency,
        "premium_pack": {
            "target_score": PRO_QUALITY_TARGET,
            "target_label": PRO_TARGET_LABEL,
            "gate": quality.get("premium_readiness", {}),
            "summary": f"Profesyonel raporlama hedefi {PRO_TARGET_LABEL} kalite kapısıdır.",
        },
        "clauses": clauses,
        "heatmap": quality.get("heatmap", []),
        "mock_audit": mock_audit_payload(username, program_id, sample_size=5),
        "split_view": {
            "left_panel": ["Ölçüt rehberi", "Beklenen kanıtlar", "Clause Library", "Tutarlılık uyarıları", "Önceki sürüm"],
            "right_panel": ["Editör / Hazırlayıcı", "Canlı önizleme", "Kanıt bağlama", "Cümle diff"],
        },
        "table_editor_capabilities": ["Excel yapıştırma", "Toplam satırı", "Koşullu uyarı", "Rapor içine gömülü aktarım", "Excel içe/dışa aktarım hazırlığı"],
        "package_manifest": ["Ana_Rapor.docx", "Ana_Rapor.pdf", "Ekler/Kanit_Dizini.csv", "Kalite_Skoru.json", "Premium_98_Readiness.json", "Tutarlilik_Kontrolu.json", "Mock_Denetim.json"],
        "sections_count": len(sections),
    }


def _write_json(archive: zipfile.ZipFile, name: str, payload: Any) -> None:
    archive.writestr(name, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))


def _evidence_index_csv(evidence_rows: list[dict[str, Any]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Kod", "Başlık", "Bölüm", "Not", "Yükleme Tarihi", "Dosya"])
    for row in evidence_rows:
        writer.writerow([row.get("code", ""), row.get("original_name", ""), row.get("section_key", ""), row.get("note", ""), row.get("uploaded_at", ""), row.get("stored_path", "")])
    return buffer.getvalue().encode("utf-8-sig")


def _add_watermark_note(docx_data: bytes, settings: dict[str, str], note: str) -> bytes:
    doc = Document(io.BytesIO(docx_data))
    section = doc.sections[0]
    paragraph = section.header.paragraphs[0]
    paragraph.text = note
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in paragraph.runs:
        run.bold = True
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(160, 30, 30)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def build_report_package_zip(username: str, program_id: str, base_url: str = "", auditor: bool = False) -> bytes:
    assert_program_access(username, program_id)
    settings = get_settings(program_id)
    evidence_rows = list_evidence(username, program_id)
    quality = report_quality_payload(username, program_id)
    consistency = consistency_check_payload(username, program_id)
    mock = mock_audit_payload(username, program_id)
    docx_data = build_final_docx(username, program_id, base_url=base_url)
    if auditor:
        docx_data = _add_watermark_note(docx_data, settings, "DENETÇİ OKUMA KOPYASI - SALT OKUNUR")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Ana_Rapor.docx" if not auditor else "Denetci_Ana_Rapor.docx", docx_data)
        try:
            pdf_data = convert_docx_to_pdf(docx_data, "Ana_Rapor")
            archive.writestr("Ana_Rapor.pdf" if not auditor else "Denetci_Ana_Rapor.pdf", pdf_data)
        except Exception as exc:
            archive.writestr("PDF_DONUSUM_NOTU.txt", f"PDF üretimi bu ortamda tamamlanamadı: {exc}\nDOCX dosyası pakete eklendi.")
        archive.writestr("Ekler/Kanit_Dizini.csv", _evidence_index_csv(evidence_rows))
        _write_json(archive, "Kalite_Skoru.json", quality)
        _write_json(archive, "Premium_98_Readiness.json", quality.get("premium_readiness", {}))
        _write_json(archive, "Tutarlilik_Kontrolu.json", consistency)
        _write_json(archive, "Mock_Denetim.json", mock)
        _write_json(archive, "Paket_Manifest.json", {
            "program_id": program_id,
            "created_by": username,
            "created_at": now_iso(),
            "auditor_copy": auditor,
            "watermark": "DENETÇİ OKUMA KOPYASI" if auditor else "",
        })
        for row in evidence_rows:
            stored = safe_stored_path(_text(row.get("stored_path")))
            if stored and stored.exists() and stored.is_file():
                name = safe_download_name(_text(row.get("original_name")) or stored.name)
                code = safe_download_name(_text(row.get("code")) or "kanit")
                archive.write(stored, f"Kanitlar/{code}_{name}")
    log_activity("Profesyonel rapor paketi oluşturuldu", "denetçi" if auditor else "tam paket", username, program_id)
    return buffer.getvalue()


def create_auditor_share_link(username: str, program_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    role = assert_program_access(username, program_id)
    if role not in {"Süper Admin", "Kurum Admin", "Birim Admin", "Birim Koordinatörü", "Onaylayıcı"}:
        raise PermissionError("Harici denetçi bağlantısı oluşturma yetkiniz yok.")
    token = uuid.uuid4().hex + uuid.uuid4().hex
    expires_at = _text(payload.get("expires_at"))
    if not expires_at:
        expires_at = datetime.now().replace(hour=23, minute=59, second=59).isoformat(timespec="seconds")
    link_id = str(uuid.uuid4())
    with transaction() as conn:
        conn.execute(
            """INSERT INTO auditor_share_links(id, program_id, token, label, expires_at, watermark, is_active, created_by, created_at, last_access_at, access_count)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (link_id, program_id, token, _text(payload.get("label")) or "Denetçi paylaşımı", expires_at, _text(payload.get("watermark")) or "DENETÇİ KOPYASI", 1, username, now_iso(), "", 0),
        )
    log_activity("Denetçi paylaşım linki oluşturuldu", link_id, username, program_id)
    return {"id": link_id, "token": token, "expires_at": expires_at, "watermark": _text(payload.get("watermark")) or "DENETÇİ KOPYASI", "read_only": True}


def list_auditor_share_links(username: str, program_id: str) -> list[dict[str, Any]]:
    assert_program_access(username, program_id)
    with get_conn() as conn:
        return rows_to_dicts(conn.execute(
            "SELECT id, program_id, label, expires_at, watermark, is_active, created_by, created_at, last_access_at, access_count FROM auditor_share_links WHERE program_id=? ORDER BY created_at DESC",
            (program_id,),
        ).fetchall())
