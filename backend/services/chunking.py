"""청킹 서비스.

비전공자 팁: 긴 문서를 잘게 나눠서 검색 정확도를 높이는 과정입니다.
"""
from __future__ import annotations

from typing import Iterable, List


def sliding_window_chunks(text: str, chunk_size: int = 800, overlap: int = 120) -> List[str]:
    """토큰 대신 문자 기준으로 단순 청크를 만듭니다.

    실제 운영에서는 토크나이저 사용이 권장됩니다.
    """

    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += max(chunk_size - overlap, 1)
    return chunks


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> Iterable[tuple[int, str]]:
    """청킹 후 위치(index)와 함께 반환."""

    for idx, chunk in enumerate(sliding_window_chunks(text, chunk_size=chunk_size, overlap=overlap)):
        yield idx, chunk


__all__ = ["chunk_text"]
