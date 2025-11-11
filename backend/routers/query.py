"""검색 및 생성 API."""
from __future__ import annotations

import hashlib

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status

from backend.deps.auth import UserContext, get_current_user
from backend.deps.db import get_session
from backend.deps.rate_limit import enforce_rate_limit
from backend.deps.settings import settings
from backend.models.schema import QueryRequest, QueryResponse
from backend.services.guardrails import run_guardrails
from backend.services.search import search_similar_chunks
from backend.deps.ollama import call_ollama

router = APIRouter(tags=["query"])


async def _embed_query(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{settings.embedding_svc}/embed", json={"texts": [text]})
        resp.raise_for_status()
        data = resp.json()
    vectors = data.get("vectors", [])
    if not vectors:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="embedding failed")
    return vectors[0]


@router.post("/{pipeline_id}/query", response_model=QueryResponse)
async def query_pipeline(
    pipeline_id: int,
    payload: QueryRequest,
    user: UserContext = Depends(get_current_user),
    session=Depends(get_session),
):
    """파이프라인 질의.

    top-k, threshold, dedup 옵션이 그대로 반영됩니다.
    """

    await enforce_rate_limit(f"pipeline-query:{pipeline_id}:{user.user_id}")
    pipeline_exists = await session.execute(
        sa.text("SELECT 1 FROM pipelines WHERE id = :pid AND owner_id = :owner"),
        {"pid": pipeline_id, "owner": user.user_id},
    )
    if pipeline_exists.fetchone() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pipeline not found")

    embedding = await _embed_query(payload.q)
    sources = await search_similar_chunks(session, pipeline_id, embedding, payload.top_k, payload.threshold)

    if payload.dedup:
        deduped = []
        seen = set()
        for src in sources:
            digest = hashlib.sha1(src.text.encode("utf-8")).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            deduped.append(src)
        sources = deduped

    context = "\n\n".join(f"[{s.chunk_id}] {s.text}" for s in sources)
    system_prompt = "당신은 기업용 문서비서입니다. 주어진 근거만으로 답변하세요."
    user_prompt = f"질문: {payload.q}\n\n근거:\n{context}"
    answer = await call_ollama(user_prompt, system=system_prompt)

    masked_answer, warnings = run_guardrails(answer, [s.text for s in sources])

    await session.execute(
        sa.text(
            """
            INSERT INTO runs (pipeline_id, user_id, kind, status, input, output, started_at, finished_at)
            VALUES (:pipeline_id, :user_id, 'query', 'success', :input::jsonb, :output::jsonb, NOW(), NOW())
            """
        ),
        {
            "pipeline_id": pipeline_id,
            "user_id": user.user_id,
            "input": payload.model_dump_json(),
            "output": QueryResponse(answer=masked_answer, sources=list(sources), warnings=warnings).model_dump_json(),
        },
    )
    await session.commit()

    return QueryResponse(answer=masked_answer, sources=list(sources), warnings=warnings)
