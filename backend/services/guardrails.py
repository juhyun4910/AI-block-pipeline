"""가드레일 서비스.

비전공자 팁: 가드레일은 민감한 정보나 위험한 요청을 자동으로 감시합니다.
"""
from __future__ import annotations

from typing import Iterable

from backend.services import pii_rules, moderation_rules


def apply_pii_mask(text: str) -> str:
    """응답 내 PII를 재차 마스킹."""

    masked = text
    for pattern, replacement in pii_rules.PII_PATTERNS:
        masked = pattern.sub(replacement, masked)
    return masked


def detect_moderation_flags(text: str) -> list[str]:
    """금칙 카테고리 감지."""

    flags: list[str] = []
    for category, regex in moderation_rules.CATEGORY_PATTERNS.items():
        if regex.search(text):
            flags.append(category)
    return flags


def citation_check(answer: str, sources: Iterable[str]) -> list[str]:
    """근거 비율을 간단히 체크."""

    warnings: list[str] = []
    total_len = sum(len(src) for src in sources)
    if total_len == 0:
        warnings.append("근거 텍스트 없음: citations unavailable")
    elif len(answer) / max(total_len, 1) > 4:
        warnings.append("답변 길이가 근거 대비 길어 검증 필요")
    return warnings


def run_guardrails(answer: str, sources: Iterable[str]) -> tuple[str, list[str]]:
    """PII 마스킹과 금칙 경고를 순차 적용."""

    masked = apply_pii_mask(answer)
    warnings = citation_check(masked, sources)
    moderation_flags = detect_moderation_flags(masked)
    if moderation_flags:
        warnings.append(f"금칙 카테고리 감지: {', '.join(moderation_flags)}")
    return masked, warnings


__all__ = ["run_guardrails"]
