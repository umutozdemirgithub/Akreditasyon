from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from services.ai_report_writer import GeneratedReportDraft, build_specialized_report_draft


def _value(row: Mapping[str, Any] | Any, key: str, default: Any = "") -> Any:
    try:
        return row[key]
    except Exception:
        return default


@dataclass(frozen=True)
class FullReportDraftCandidate:
    section_key: str
    section_title: str
    main_title: str
    current_words: int
    quality_score: int
    draft: GeneratedReportDraft


def should_generate_section(section: Mapping[str, Any] | Any, quality: Mapping[str, Any], include_all: bool = False, min_words: int = 260, min_score: int = 82) -> bool:
    if include_all:
        return True
    current_words = int(quality.get("words", 0) or 0)
    score = int(quality.get("score", 0) or 0)
    risk = list(quality.get("risk", []) or [])
    return current_words < min_words or score < min_score or bool(risk)


def build_full_report_draft_candidates(
    sections: Sequence[Mapping[str, Any] | Any],
    guide_by_key: Mapping[str, Mapping[str, Any]],
    evidence_by_key: Mapping[str, Sequence[Mapping[str, Any] | Any]],
    table_by_key: Mapping[str, Sequence[Mapping[str, Any] | Any]],
    quality_by_key: Mapping[str, Mapping[str, Any]],
    include_all: bool = False,
    target_words: int = 650,
) -> list[FullReportDraftCandidate]:
    """Generate reviewable AI draft candidates in report order without saving them."""
    candidates: list[FullReportDraftCandidate] = []
    for section in sections:
        key = str(_value(section, "section_key", ""))
        if not key:
            continue
        quality = quality_by_key.get(key, {})
        if not should_generate_section(section, quality, include_all=include_all):
            continue
        draft = build_specialized_report_draft(
            section,
            guide_by_key.get(key, {}),
            evidence_by_key.get(key, []),
            table_by_key.get(key, []),
            target_words=target_words,
        )
        candidates.append(
            FullReportDraftCandidate(
                section_key=key,
                section_title=str(_value(section, "section_title", "")),
                main_title=str(_value(section, "main_title", "")),
                current_words=int(quality.get("words", 0) or 0),
                quality_score=int(quality.get("score", 0) or 0),
                draft=draft,
            )
        )
    return candidates

