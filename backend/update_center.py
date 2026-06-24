from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from .academic_importer import discover_academic_catalog_from_yokatlas
from .accreditation import infer_accreditation_profile_by_rule, normalize_accreditation_profile
from .db import get_conn, now_iso, row_to_dict, rows_to_dicts, transaction
from .repositories import actor_has_operation_permission, assert_any_operation_permission, get_user, log_activity
from .repos.programs_repo import create_program_admin
from .tenancy import DEFAULT_TENANT_ID, ensure_tenant_access, user_is_global_admin

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
UPDATE_VIEW_PERMISSION = "update_center.view"
UPDATE_CHECK_PERMISSION = "update_center.check"
UPDATE_APPLY_PERMISSION = "update_center.apply"

ACCREDITATION_TEMPLATE_SOURCES: list[dict[str, str]] = [
    {"profile": "MEDEK", "name": "MEDEK", "url": "https://medek.org.tr/belgeler", "watch_type": "template"},
    {"profile": "MUDEK", "name": "MÜDEK", "url": "https://www.mudek.org.tr/tr/belgeler/belgeler.shtm", "watch_type": "template"},
    {"profile": "TEPDAD", "name": "TEPDAD", "url": "https://tepdad.org.tr/", "watch_type": "template"},
    {"profile": "DEPAD", "name": "DEPAD", "url": "https://depad.org/", "watch_type": "template"},
    {"profile": "ECZAKDER", "name": "ECZAKDER", "url": "https://eczakder.org.tr/", "watch_type": "template"},
    {"profile": "HEPDAK", "name": "HEPDAK", "url": "https://hepdak.org.tr/", "watch_type": "template"},
    {"profile": "EPDAK", "name": "EPDAK", "url": "https://www.epdak.org.tr/", "watch_type": "template"},
    {"profile": "FTR-AD", "name": "FTR-AD", "url": "https://ftrad.org.tr/", "watch_type": "template"},
    {"profile": "SAYAK", "name": "SAYAK", "url": "https://sayak.org.tr/", "watch_type": "template"},
    {"profile": "MIAK", "name": "MİAK", "url": "https://www.miak.org/", "watch_type": "template"},
    {"profile": "PEMDER", "name": "PEMDER", "url": "https://pemder.org.tr/", "watch_type": "template"},
    {"profile": "VEDEK", "name": "VEDEK", "url": "https://vedek.org.tr/", "watch_type": "template"},
    {"profile": "ZIDEK", "name": "ZİDEK", "url": "https://zidek.org.tr/", "watch_type": "template"},
    {"profile": "TURAK", "name": "TURAK", "url": "https://turak.org/", "watch_type": "template"},
    {"profile": "ILAD", "name": "İLAD", "url": "https://iletisimakreditasyon.org/", "watch_type": "template"},
    {"profile": "AA", "name": "İlahiyat Akreditasyon Ajansı", "url": "https://www.iaa.org.tr/", "watch_type": "template"},
    {"profile": "TPD", "name": "Türk Psikologlar Derneği", "url": "https://www.psikolog.org.tr/", "watch_type": "template"},
    {"profile": "PDR-DER", "name": "Türk PDR-Der", "url": "https://pdr.org.tr/", "watch_type": "template"},
    {"profile": "EPDAD", "name": "EPDAD", "url": "https://epdad.org.tr/", "watch_type": "template"},
    {"profile": "FEDEK", "name": "FEDEK", "url": "https://fedek.org.tr/", "watch_type": "template"},
    {"profile": "STAR", "name": "STAR", "url": "https://star.org.tr/", "watch_type": "template"},
]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _json_loads(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except Exception:
        return default


def _tenant_scope_for_user(username: str) -> tuple[str, bool]:
    user = get_user(username, active_only=True) or {}
    return str(user.get("tenant_id") or DEFAULT_TENANT_ID), user_is_global_admin(user)


def _user_has_update_permission(username: str, permission: str) -> bool:
    return actor_has_operation_permission(get_user(username, active_only=True), permission)


def _candidate_mutation_allowed(username: str, row: dict[str, Any]) -> bool:
    tenant_id, is_global = _tenant_scope_for_user(username)
    candidate_tenant = str(row.get("tenant_id") or "global")
    if is_global:
        return True
    # Global template/source candidates affect shared system state, so tenant
    # admins may review them but cannot accept or ignore them for everyone.
    if candidate_tenant == "global":
        return False
    return candidate_tenant == tenant_id


def _assert_candidate_mutation_scope(username: str, row: dict[str, Any]) -> None:
    if not _candidate_mutation_allowed(username, row):
        raise PermissionError("Bu güncelleme adayı kurum kapsamınız dışında.")


def ensure_update_center_seed(conn) -> None:
    now = now_iso()
    for source in ACCREDITATION_TEMPLATE_SOURCES:
        watcher_id = f"template:{source['profile']}"
        exists = conn.execute("SELECT id FROM source_watchers WHERE id=?", (watcher_id,)).fetchone()
        if not exists:
            conn.execute(
                """
                INSERT INTO source_watchers(id, tenant_id, watcher_type, source_name, source_url, profile, cadence, is_active, last_checked_at, last_hash, created_at, updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (watcher_id, "global", "template", source["name"], source["url"], source["profile"], "weekly", 1, "", "", now, now),
            )


def _record_log(conn, *, tenant_id: str, source_type: str, source_name: str, status: str, message: str, details: dict[str, Any] | None = None) -> None:
    conn.execute(
        """
        INSERT INTO source_check_logs(id, tenant_id, source_type, source_name, status, message, details_json, checked_at)
        VALUES(?,?,?,?,?,?,?,?)
        """,
        (str(uuid.uuid4()), tenant_id, source_type, source_name, status, message, _json_dumps(details or {}), now_iso()),
    )


def _candidate_exists(conn, *, tenant_id: str, source_type: str, candidate_kind: str, profile: str, title: str, new_hash: str = "") -> bool:
    row = conn.execute(
        """
        SELECT id FROM update_candidates
        WHERE tenant_id=? AND source_type=? AND candidate_kind=? AND profile=? AND title=?
          AND status='pending' AND COALESCE(new_hash,'')=?
        """,
        (tenant_id, source_type, candidate_kind, profile, title, new_hash),
    ).fetchone()
    return bool(row)


def _add_candidate(
    conn,
    *,
    tenant_id: str,
    source_type: str,
    candidate_kind: str,
    title: str,
    summary: str,
    profile: str = "",
    old_version: str = "",
    new_version: str = "",
    old_hash: str = "",
    new_hash: str = "",
    source_url: str = "",
    payload: dict[str, Any] | None = None,
    diff: list[dict[str, Any]] | None = None,
) -> str | None:
    if _candidate_exists(conn, tenant_id=tenant_id, source_type=source_type, candidate_kind=candidate_kind, profile=profile, title=title, new_hash=new_hash):
        return None
    candidate_id = str(uuid.uuid4())
    now = now_iso()
    conn.execute(
        """
        INSERT INTO update_candidates(
            id, tenant_id, source_type, candidate_kind, profile, title, summary,
            old_version, new_version, old_hash, new_hash, source_url,
            payload_json, diff_json, status, created_at, updated_at, applied_by, applied_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            candidate_id,
            tenant_id,
            source_type,
            candidate_kind,
            profile,
            title,
            summary,
            old_version,
            new_version,
            old_hash,
            new_hash,
            source_url,
            _json_dumps(payload or {}),
            _json_dumps(diff or []),
            "pending",
            now,
            now,
            "",
            "",
        ),
    )
    return candidate_id


def _load_template_file(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _template_key_from_json(path: Path, data: dict[str, Any]) -> str:
    return str(data.get("template_key") or data.get("profile") or path.stem).upper().replace("İ", "I")


def _check_bundled_template_versions(conn, tenant_id: str = "global") -> int:
    created = 0
    for path in sorted(TEMPLATE_DIR.glob("*.json")):
        data = _load_template_file(path)
        if not data:
            continue
        template_key = _template_key_from_json(path, data)
        bundled_hash = _sha256_bytes(_json_dumps(data).encode("utf-8"))
        bundled_version = str(data.get("version") or data.get("updated_at") or "paket")
        existing = conn.execute("SELECT * FROM system_templates WHERE template_key=?", (template_key,)).fetchone()
        if not existing:
            cid = _add_candidate(
                conn,
                tenant_id=tenant_id,
                source_type="template",
                candidate_kind="template_add",
                profile=template_key,
                title=f"{template_key} sistem şablonu eklensin",
                summary="Paket içinde bu akreditasyon profiline ait şablon var ancak sistem şablon bankasında bulunmuyor.",
                new_version=bundled_version,
                new_hash=bundled_hash,
                source_url=str(path.name),
                payload={"template_key": template_key, "template": data},
                diff=[{"field": "system_templates", "old": "Yok", "new": "Eklenecek"}],
            )
            created += 1 if cid else 0
            continue
        current_data = _json_loads(existing["data_json"], {})
        current_hash = _sha256_bytes(_json_dumps(current_data).encode("utf-8"))
        current_version = str(existing["version"] or "")
        if current_hash != bundled_hash:
            cid = _add_candidate(
                conn,
                tenant_id=tenant_id,
                source_type="template",
                candidate_kind="template_bundle_update",
                profile=template_key,
                title=f"{template_key} şablonu paket sürümüyle güncellensin",
                summary="Paket içindeki şablon ile veritabanındaki sistem şablonu farklı. Onaylanırsa sistem şablon bankası yeni paket şablonuna güncellenir; mevcut rapor içerikleri bozulmaz.",
                old_version=current_version,
                new_version=bundled_version,
                old_hash=current_hash,
                new_hash=bundled_hash,
                source_url=str(path.name),
                payload={"template_key": template_key, "template": data},
                diff=[{"field": "template_hash", "old": current_hash[:12], "new": bundled_hash[:12]}],
            )
            created += 1 if cid else 0
    _record_log(conn, tenant_id=tenant_id, source_type="template", source_name="Paket şablonları", status="ok", message=f"Paket şablon kontrolü tamamlandı; {created} aday üretildi.")
    return created


def _fetch_url_fingerprint(url: str) -> dict[str, str]:
    req = Request(url, headers={"User-Agent": "AKYS UpdateCenter/1.0"})
    with urlopen(req, timeout=12) as response:  # noqa: S310 - URLs are curated watcher records, not arbitrary user input.
        body = response.read(500_000)
        return {
            "hash": _sha256_bytes(body),
            "etag": response.headers.get("ETag", ""),
            "last_modified": response.headers.get("Last-Modified", ""),
            "content_type": response.headers.get("Content-Type", ""),
        }


def _check_online_template_sources(conn) -> int:
    created = 0
    rows = conn.execute("SELECT * FROM source_watchers WHERE watcher_type='template' AND is_active=1 ORDER BY source_name").fetchall()
    for row in rows:
        source_name = str(row["source_name"] or row["profile"] or "Şablon Kaynağı")
        source_url = str(row["source_url"] or "")
        try:
            if not source_url.startswith(("https://", "http://")):
                raise ValueError("Kaynak URL tanımlı değil.")
            fp = _fetch_url_fingerprint(source_url)
            new_hash = fp.get("etag") or fp.get("last_modified") or fp.get("hash")
            old_hash = str(row["last_hash"] or "")
            conn.execute("UPDATE source_watchers SET last_checked_at=?, last_status=?, last_message=?, updated_at=? WHERE id=?", (now_iso(), "ok", "Kaynak erişilebilir.", now_iso(), row["id"]))
            if old_hash and new_hash and old_hash != new_hash:
                cid = _add_candidate(
                    conn,
                    tenant_id="global",
                    source_type="template",
                    candidate_kind="external_template_source_changed",
                    profile=str(row["profile"] or ""),
                    title=f"{source_name} web kaynağında değişiklik algılandı",
                    summary="Resmi web kaynağında ETag/Last-Modified/içerik parmak izi değişti. Onaylanırsa kaynak yeni baz sürüm olarak işaretlenir; yapılandırılmış JSON şablonu yoksa mevcut raporlar otomatik değiştirilmez.",
                    old_hash=old_hash,
                    new_hash=new_hash,
                    source_url=source_url,
                    payload={"fingerprint": fp, "source_name": source_name, "source_url": source_url},
                    diff=[{"field": "source_fingerprint", "old": old_hash[:24], "new": new_hash[:24]}],
                )
                created += 1 if cid else 0
            if new_hash:
                conn.execute("UPDATE source_watchers SET last_hash=?, updated_at=? WHERE id=?", (new_hash, now_iso(), row["id"]))
            _record_log(conn, tenant_id="global", source_type="template", source_name=source_name, status="ok", message="Resmi kaynak kontrol edildi.", details=fp)
        except Exception as exc:  # noqa: BLE001
            conn.execute("UPDATE source_watchers SET last_checked_at=?, last_status=?, last_message=?, updated_at=? WHERE id=?", (now_iso(), "error", str(exc), now_iso(), row["id"]))
            _record_log(conn, tenant_id="global", source_type="template", source_name=source_name, status="error", message=str(exc), details={"url": source_url})
    return created


def _iter_tenants_for_user(conn, username: str) -> list[dict[str, Any]]:
    tenant_id, is_global = _tenant_scope_for_user(username)
    if is_global:
        rows = conn.execute("SELECT * FROM tenants WHERE COALESCE(is_active,1)=1 AND COALESCE(deleted_at,'')='' ORDER BY name").fetchall()
    else:
        rows = conn.execute("SELECT * FROM tenants WHERE id=? AND COALESCE(is_active,1)=1 AND COALESCE(deleted_at,'')=''", (tenant_id,)).fetchall()
    return rows_to_dicts(rows)


def _current_program_keys(conn, tenant_id: str) -> set[tuple[str, str, str]]:
    rows = conn.execute(
        """
        SELECT faculty_name, department_name, program_name FROM programs
        WHERE tenant_id=? AND COALESCE(deleted_at,'')='' AND COALESCE(is_active,1)=1
        """,
        (tenant_id,),
    ).fetchall()
    return {(str(r["faculty_name"] or r["school_name"] or "").strip().lower(), str(r["department_name"] or "").strip().lower(), str(r["program_name"] or "").strip().lower()) for r in rows}


def _current_faculty_names(conn, tenant_id: str) -> set[str]:
    rows = conn.execute("SELECT faculty_name FROM tenant_faculties WHERE tenant_id=? AND COALESCE(deleted_at,'')='' AND COALESCE(is_active,1)=1", (tenant_id,)).fetchall()
    program_rows = conn.execute("SELECT DISTINCT faculty_name FROM programs WHERE tenant_id=? AND COALESCE(deleted_at,'')='' AND COALESCE(is_active,1)=1", (tenant_id,)).fetchall()
    return {str(r["faculty_name"] or "").strip().lower() for r in list(rows) + list(program_rows) if str(r["faculty_name"] or "").strip()}


def _catalog_program_rows(catalog: dict[str, Any], tenant: dict[str, Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    university_name = str(catalog.get("yokatlas_university_name") or tenant.get("name") or "")
    for unit in catalog.get("units", []) if isinstance(catalog, dict) else []:
        faculty = str(unit.get("name") or unit.get("faculty_name") or "").strip()
        for department in unit.get("departments", []) or []:
            dept_name = str(department.get("name") or department.get("department_name") or "").strip()
            for program in department.get("programs", []) or []:
                if isinstance(program, str):
                    program_name = program
                    degree = ""
                else:
                    program_name = str(program.get("name") or program.get("program_name") or "").strip()
                    degree = str(program.get("degree") or program.get("level") or program.get("program_degree") or "").strip()
                if not program_name:
                    continue
                profile = infer_accreditation_profile_by_rule(program_name, degree or "Lisans")
                output.append({
                    "university_name": university_name,
                    "faculty_name": faculty,
                    "department_name": dept_name,
                    "program_name": program_name,
                    "program_degree": degree,
                    "accreditation_profile": normalize_accreditation_profile(profile),
                })
    return output


def _check_academic_structure_sources(conn, username: str, *, online: bool) -> int:
    created = 0
    tenants = _iter_tenants_for_user(conn, username)
    for tenant in tenants:
        tenant_id = str(tenant.get("id") or DEFAULT_TENANT_ID)
        tenant_name = str(tenant.get("name") or "")
        domain = str(tenant.get("domain") or "")
        if not online:
            _record_log(conn, tenant_id=tenant_id, source_type="academic", source_name="YÖK Atlas", status="skipped", message="Canlı kontrol kapalı. Çalıştırırken online=true kullanılırsa YÖK Atlas kontrol edilir.")
            continue
        try:
            catalog = discover_academic_catalog_from_yokatlas(domain, tenant_name=tenant_name, code=str(tenant.get("code") or ""))
            faculty_names = _current_faculty_names(conn, tenant_id)
            program_keys = _current_program_keys(conn, tenant_id)
            seen_faculties: set[str] = set()
            for row in _catalog_program_rows(catalog, tenant):
                faculty = row["faculty_name"]
                if faculty and faculty.lower() not in faculty_names and faculty.lower() not in seen_faculties:
                    cid = _add_candidate(
                        conn,
                        tenant_id=tenant_id,
                        source_type="academic",
                        candidate_kind="academic_faculty_add",
                        title=f"Yeni akademik birim: {faculty}",
                        summary="YÖK Atlas verisinde kurum yapısında sistemde olmayan fakülte/MYO/birim tespit edildi.",
                        source_url=str(catalog.get("source_url") or "https://yokatlas.yok.gov.tr"),
                        payload={"tenant_id": tenant_id, "faculty_name": faculty, "accreditation_profile": row.get("accreditation_profile") or "MEDEK"},
                        diff=[{"field": "faculty_name", "old": "Yok", "new": faculty}],
                    )
                    created += 1 if cid else 0
                    seen_faculties.add(faculty.lower())
                key = (faculty.lower(), row["department_name"].lower(), row["program_name"].lower())
                if key not in program_keys:
                    cid = _add_candidate(
                        conn,
                        tenant_id=tenant_id,
                        source_type="academic",
                        candidate_kind="academic_program_add",
                        profile=row.get("accreditation_profile") or "",
                        title=f"Yeni program: {row['program_name']}",
                        summary="YÖK Atlas verisinde sistemde olmayan program tespit edildi. Onaylanırsa yeni program taslak olarak eklenir; mevcut programlar silinmez.",
                        source_url=str(catalog.get("source_url") or "https://yokatlas.yok.gov.tr"),
                        payload={"tenant_id": tenant_id, **row},
                        diff=[
                            {"field": "faculty_name", "old": "Yok", "new": faculty},
                            {"field": "department_name", "old": "Yok", "new": row["department_name"]},
                            {"field": "program_name", "old": "Yok", "new": row["program_name"]},
                        ],
                    )
                    created += 1 if cid else 0
            _record_log(conn, tenant_id=tenant_id, source_type="academic", source_name="YÖK Atlas", status="ok", message=f"YÖK Atlas kontrol edildi; toplam {created} yeni aday üretildi.", details={"tenant": tenant_name, "domain": domain})
        except Exception as exc:  # noqa: BLE001
            _record_log(conn, tenant_id=tenant_id, source_type="academic", source_name="YÖK Atlas", status="error", message=str(exc), details={"tenant": tenant_name, "domain": domain})
    return created


def list_update_center_payload(username: str) -> dict[str, Any]:
    assert_any_operation_permission(username, {UPDATE_VIEW_PERMISSION, UPDATE_CHECK_PERMISSION, UPDATE_APPLY_PERMISSION})
    with transaction() as conn:
        ensure_update_center_seed(conn)
        tenant_id, is_global = _tenant_scope_for_user(username)
        if is_global:
            candidate_rows = conn.execute("SELECT * FROM update_candidates ORDER BY CASE status WHEN 'pending' THEN 0 WHEN 'applied' THEN 1 ELSE 2 END, created_at DESC LIMIT 300").fetchall()
            watcher_rows = conn.execute("SELECT * FROM source_watchers ORDER BY watcher_type, source_name").fetchall()
            log_rows = conn.execute("SELECT * FROM source_check_logs ORDER BY checked_at DESC LIMIT 120").fetchall()
        else:
            candidate_rows = conn.execute("SELECT * FROM update_candidates WHERE tenant_id IN (?, 'global') ORDER BY CASE status WHEN 'pending' THEN 0 WHEN 'applied' THEN 1 ELSE 2 END, created_at DESC LIMIT 300", (tenant_id,)).fetchall()
            watcher_rows = conn.execute("SELECT * FROM source_watchers WHERE tenant_id IN (?, 'global') ORDER BY watcher_type, source_name", (tenant_id,)).fetchall()
            log_rows = conn.execute("SELECT * FROM source_check_logs WHERE tenant_id IN (?, 'global') ORDER BY checked_at DESC LIMIT 120", (tenant_id,)).fetchall()
        candidates = rows_to_dicts(candidate_rows)
        can_apply = _user_has_update_permission(username, UPDATE_APPLY_PERMISSION)
        for row in candidates:
            row["payload"] = _json_loads(row.pop("payload_json", "{}"), {})
            row["diff"] = _json_loads(row.pop("diff_json", "[]"), [])
            can_mutate = bool(row.get("status") == "pending" and can_apply and _candidate_mutation_allowed(username, row))
            row["can_apply"] = can_mutate
            row["can_ignore"] = can_mutate
        watchers = rows_to_dicts(watcher_rows)
        logs = rows_to_dicts(log_rows)
        for row in logs:
            row["details"] = _json_loads(row.pop("details_json", "{}"), {})
        pending = [c for c in candidates if c.get("status") == "pending"]
        return {
            "summary": {
                "pending_total": len(pending),
                "pending_template": len([c for c in pending if c.get("source_type") == "template"]),
                "pending_academic": len([c for c in pending if c.get("source_type") == "academic"]),
                "watchers": len(watchers),
                "last_checked_at": logs[0]["checked_at"] if logs else "",
                "can_check": _user_has_update_permission(username, UPDATE_CHECK_PERMISSION),
                "can_apply": can_apply,
            },
            "candidates": candidates,
            "watchers": watchers,
            "logs": logs,
        }


def run_update_center_check(username: str, scope: str = "all", online: bool = False) -> dict[str, Any]:
    assert_any_operation_permission(username, {UPDATE_CHECK_PERMISSION})
    scope_value = str(scope or "all").lower()
    created_template = 0
    created_academic = 0
    with transaction() as conn:
        ensure_update_center_seed(conn)
        if scope_value in {"all", "template", "templates"}:
            created_template += _check_bundled_template_versions(conn)
            if online:
                created_template += _check_online_template_sources(conn)
            else:
                _record_log(conn, tenant_id="global", source_type="template", source_name="Resmi web kaynakları", status="skipped", message="Canlı web kontrolü kapalı. Online kontrol için online=true ile çalıştırın.")
        if scope_value in {"all", "academic", "yokatlas"}:
            created_academic += _check_academic_structure_sources(conn, username, online=online)
        log_activity("update_center.check", f"Güncelleme Merkezi kontrolü çalıştırıldı. scope={scope_value}, online={online}, template={created_template}, academic={created_academic}", username)
    return {"ok": True, "created_template": created_template, "created_academic": created_academic, "online": online, "scope": scope_value}


def _apply_template_candidate(conn, username: str, row: dict[str, Any]) -> dict[str, Any]:
    payload = _json_loads(row.get("payload_json"), {})
    kind = str(row.get("candidate_kind") or "")
    if kind in {"template_add", "template_bundle_update"}:
        template = payload.get("template") or {}
        template_key = str(payload.get("template_key") or row.get("profile") or "").upper()
        if not template_key or not template:
            raise ValueError("Şablon adayı eksik payload içeriyor.")
        conn.execute(
            """
            INSERT OR REPLACE INTO system_templates(template_key, template_name, version, association_name, system_name, report_type, data_json, updated_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                template_key,
                str(template.get("template_name") or template.get("name") or template_key),
                str(template.get("version") or row.get("new_version") or ""),
                str(template.get("association_name") or template.get("association") or ""),
                str(template.get("system_name") or ""),
                str(template.get("report_type") or ""),
                _json_dumps(template),
                now_iso(),
            ),
        )
        return {"applied": "system_template", "template_key": template_key}
    if kind == "external_template_source_changed":
        fingerprint = payload.get("fingerprint", {}) if isinstance(payload, dict) else {}
        watcher_id = f"template:{row.get('profile')}"
        conn.execute("UPDATE source_watchers SET last_hash=?, last_checked_at=?, last_status='reviewed', last_message=?, updated_at=? WHERE id=?", (str(row.get("new_hash") or fingerprint.get("hash") or ""), now_iso(), "Kullanıcı tarafından yeni kaynak baz sürümü kabul edildi.", now_iso(), watcher_id))
        return {"applied": "source_baseline", "profile": row.get("profile"), "manual_template_review_required": True}
    raise ValueError("Bu şablon adayı otomatik uygulanamıyor.")


def _apply_academic_candidate(conn, username: str, row: dict[str, Any]) -> dict[str, Any]:
    payload = _json_loads(row.get("payload_json"), {})
    kind = str(row.get("candidate_kind") or "")
    tenant_id = str(payload.get("tenant_id") or row.get("tenant_id") or DEFAULT_TENANT_ID)
    row_tenant_id = str(row.get("tenant_id") or DEFAULT_TENANT_ID)
    if tenant_id != row_tenant_id:
        raise ValueError("Güncelleme adayı kurum bilgisi tutarsız.")
    ensure_tenant_access(username, tenant_id)
    if kind == "academic_faculty_add":
        faculty = str(payload.get("faculty_name") or "").strip()
        if not faculty:
            raise ValueError("Akademik birim adı boş.")
        existing = conn.execute("SELECT id FROM tenant_faculties WHERE tenant_id=? AND lower(faculty_name)=lower(?) AND COALESCE(deleted_at,'')=''", (tenant_id, faculty)).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO tenant_faculties(id, tenant_id, faculty_name, accreditation_profile, is_active, created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), tenant_id, faculty, str(payload.get("accreditation_profile") or "MEDEK"), 1, now_iso(), now_iso()),
            )
        return {"applied": "tenant_faculty", "faculty_name": faculty}
    if kind == "academic_program_add":
        program_name = str(payload.get("program_name") or "").strip()
        if not program_name:
            raise ValueError("Program adı boş.")
        existing = conn.execute(
            """
            SELECT id FROM programs WHERE tenant_id=? AND lower(COALESCE(faculty_name,''))=lower(?)
              AND lower(COALESCE(department_name,''))=lower(?) AND lower(program_name)=lower(?) AND COALESCE(deleted_at,'')=''
            """,
            (tenant_id, str(payload.get("faculty_name") or ""), str(payload.get("department_name") or ""), program_name),
        ).fetchone()
        if existing:
            return {"applied": "program_exists", "program_id": existing["id"]}
        # create_program_admin opens program with the appropriate accreditation template and permission/audit checks.
        result = create_program_admin(username, {
            "tenant_id": tenant_id,
            "university_name": str(payload.get("university_name") or ""),
            "school_name": str(payload.get("faculty_name") or ""),
            "faculty_name": str(payload.get("faculty_name") or ""),
            "department_name": str(payload.get("department_name") or ""),
            "program_name": program_name,
            "program_degree": str(payload.get("program_degree") or ""),
            "accreditation_profile": str(payload.get("accreditation_profile") or "MEDEK"),
            "report_year": str(datetime.now().year),
        })
        return {"applied": "program_created", "program_id": result.get("id"), "program_name": program_name}
    raise ValueError("Bu akademik yapı adayı otomatik uygulanamıyor.")


def apply_update_candidate(username: str, candidate_id: str) -> dict[str, Any]:
    assert_any_operation_permission(username, {UPDATE_APPLY_PERMISSION})
    with transaction() as conn:
        row_obj = conn.execute("SELECT * FROM update_candidates WHERE id=?", (candidate_id,)).fetchone()
        if not row_obj:
            raise KeyError("Güncelleme adayı bulunamadı.")
        row = row_to_dict(row_obj) or {}
        if row.get("status") != "pending":
            raise ValueError("Bu aday bekleyen durumda değil.")
        _assert_candidate_mutation_scope(username, row)
        source_type = str(row.get("source_type") or "")
        if source_type == "template":
            result = _apply_template_candidate(conn, username, row)
        elif source_type == "academic":
            result = _apply_academic_candidate(conn, username, row)
        else:
            raise ValueError("Bilinmeyen güncelleme adayı türü.")
        conn.execute("UPDATE update_candidates SET status='applied', applied_by=?, applied_at=?, updated_at=? WHERE id=?", (username, now_iso(), now_iso(), candidate_id))
        log_activity("update_center.apply", f"Güncelleme adayı uygulandı: {row.get('title')}", username, str(result.get("program_id", "")))
        return {"ok": True, "candidate_id": candidate_id, "result": result}


def ignore_update_candidate(username: str, candidate_id: str, note: str = "") -> dict[str, Any]:
    assert_any_operation_permission(username, {UPDATE_APPLY_PERMISSION})
    with transaction() as conn:
        row_obj = conn.execute("SELECT * FROM update_candidates WHERE id=?", (candidate_id,)).fetchone()
        if not row_obj:
            raise KeyError("Güncelleme adayı bulunamadı.")
        row = row_to_dict(row_obj) or {}
        if row.get("status") != "pending":
            raise ValueError("Bu aday bekleyen durumda değil.")
        _assert_candidate_mutation_scope(username, row)
        conn.execute("UPDATE update_candidates SET status='ignored', applied_by=?, applied_at=?, updated_at=?, summary=summary || ? WHERE id=?", (username, now_iso(), now_iso(), f"\nYok sayma notu: {note}" if note else "", candidate_id))
        log_activity("update_center.ignore", f"Güncelleme adayı yok sayıldı: {row.get('title')}", username)
        return {"ok": True, "candidate_id": candidate_id}
