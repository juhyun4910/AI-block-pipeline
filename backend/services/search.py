"""벡터 검색 서비스.

비전공자 팁: pgvector는 벡터 거리 계산을 데이터베이스에서 빠르게 수행합니다.
"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.schema import QuerySource


async def search_similar_chunks(
    session: AsyncSession,
    pipeline_id: int,
    embedding: list[float],
    top_k: int,
    threshold: float,
) -> Sequence[QuerySource]:
    """pgvector 코사인 유사도 기반 검색."""

    query = sa.text(
        """
        SELECT c.id as chunk_id, c.text, 1 - (e.vec <#> :embedding) AS score
        FROM embeddings e
        JOIN chunks c ON c.id = e.chunk_id
        JOIN documents d ON d.id = c.document_id
        WHERE (:pipeline_id::text IS NULL) OR (d.meta ->> 'pipeline_id') = :pipeline_id::text
        ORDER BY e.vec <#> :embedding
        LIMIT :top_k
        """
    )
    rows = await session.execute(
        query,
        {
            "embedding": embedding,
            "pipeline_id": str(pipeline_id),
            "top_k": top_k,
        },
    )
    sources = []
    for row in rows:
        score = row.score
        if score is None or score < threshold:
            continue
        sources.append(QuerySource(chunk_id=row.chunk_id, text=row.text, score=float(score)))
    return sources


__all__ = ["search_similar_chunks"]
