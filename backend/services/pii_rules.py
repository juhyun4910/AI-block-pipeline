"""PII 마스킹 정규식 모음.

비전공자 팁: 정규식은 글자 패턴을 찾기 위한 규칙입니다.
"""
from __future__ import annotations

import re

PII_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{4}-\d{4}\b"), "[전화번호]"),
    (re.compile(r"\b\d{6}-\d{7}\b"), "[주민등록번호]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[이메일]")
]

__all__ = ["PII_PATTERNS"]
