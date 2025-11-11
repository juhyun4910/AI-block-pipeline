"""금칙 카테고리 정규식.

비전공자 팁: 욕설/증오/자해 등의 키워드를 탐지합니다.
"""
from __future__ import annotations

import re

CATEGORY_PATTERNS = {
    "욕설": re.compile(r"\b(욕설|damn|hell)\b", re.IGNORECASE),
    "증오": re.compile(r"\b(hate|증오)\b", re.IGNORECASE),
    "성인": re.compile(r"\b(adult|19금)\b", re.IGNORECASE),
    "자해": re.compile(r"\b(self-harm|자해)\b", re.IGNORECASE),
    "불법": re.compile(r"\b(illegal|불법)\b", re.IGNORECASE),
}

__all__ = ["CATEGORY_PATTERNS"]
