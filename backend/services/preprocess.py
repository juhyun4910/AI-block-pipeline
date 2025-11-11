"""문서 전처리 서비스.

비전공자 팁: 전처리는 문서를 깨끗하게 다듬어 AI가 이해하기 쉽게 만드는 과정입니다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from backend.services import pii_rules

WHITESPACE_RE = re.compile(r"[\u00A0\s]+")


@dataclass
class PreprocessResult:
    text: str
    language: str


def normalize_text(text: str) -> str:
    """공백/개행을 정리하고 깨진 문자를 치환합니다."""

    cleaned = WHITESPACE_RE.sub(" ", text)
    return cleaned.strip()


def detect_language(text: str) -> str:
    """간단한 언어 감지.

    TODO: langdetect 라이브러리 연동.
    """

    if re.search(r"[\uac00-\ud7a3]", text):
        return "ko"
    return "en"


def preserve_tables_and_code(text: str) -> str:
    """테이블/코드 블록을 간단한 토큰으로 감싸 재구성에 도움을 줍니다."""

    return text.replace("```", "<code block>")


def mask_pii(text: str) -> str:
    """PII(개인식별정보)를 정규식으로 치환합니다."""

    masked = text
    for pattern, replacement in pii_rules.PII_PATTERNS:
        masked = re.sub(pattern, replacement, masked)
    return masked


def regex_filter(text: str, patterns: Iterable[str]) -> str:
    """사용자 정의 패턴을 제거합니다."""

    filtered = text
    for pattern in patterns:
        filtered = re.sub(pattern, "", filtered)
    return filtered


def preprocess(text: str, custom_patterns: Iterable[str] | None = None) -> PreprocessResult:
    """전처리 전체 파이프라인."""

    normalized = normalize_text(text)
    preserved = preserve_tables_and_code(normalized)
    masked = mask_pii(preserved)
    filtered = regex_filter(masked, custom_patterns or [])
    language = detect_language(filtered)
    return PreprocessResult(text=filtered, language=language)


__all__ = ["preprocess", "PreprocessResult"]
