"""배포 토큰 API."""
from __future__ import annotations

import datetime as dt
import secrets

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status

from backend.deps.auth import Role, UserContext, get_current_user, require_role
from backend.deps.db import get_session
from backend.deps.rate_limit import enforce_rate_limit
from backend.deps.settings import settings
from backend.models.schema import DeployRequest, DeployResponse, QueryRequest, QueryResponse
from backend.services.guardrails import run_guardrails
from backend.services.search import search_similar_chunks
from backend.deps.ollama import call_ollama

router = APIRouter(tags=["deploy"])


async def _embed(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{settings.embedding_svc}/embed", json={"texts": [text]})
        resp.raise_for_status()
        data = resp.json()
    vectors = data.get("vectors", [])
    if not vectors:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="embedding failed")
    return vectors[0]


@router.post("/pipelines/{pipeline_id}/deploy", response_model=DeployResponse)
async def create_deploy_token(
    pipeline_id: int,
    payload: DeployRequest,
    user: UserContext = Depends(require_role(Role.OWNER, Role.REVIEWER)),
    session=Depends(get_session),
):
    """공유 토큰 발급."""

    pipeline = await session.execute(
        sa.text("SELECT is_published FROM pipelines WHERE id = :pid AND owner_id = :owner"),
        {"pid": pipeline_id, "owner": user.user_id},
    )
    row = pipeline.fetchone()
    if not row or not row.is_published:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="pipeline not published")
    token = secrets.token_urlsafe(24)
    expires = dt.datetime.utcnow() + dt.timedelta(minutes=settings.token_ttl_minutes)
    await session.execute(
        sa.text(
            """
            INSERT INTO deployments (pipeline_id, version, type, token, config, created_at)
            VALUES (:pipeline_id, 1, :type, :token, :config::jsonb, :created_at)
            RETURNING id
            """
        ),
        {
            "pipeline_id": pipeline_id,
            "type": payload.type,
            "token": token,
            "config": {"expires_at": expires.isoformat()},
            "created_at": dt.datetime.utcnow(),
        },
    )
    await session.commit()
    url = f"/deploy/{token}/query"
    return DeployResponse(token=token, url=url)


@router.post("/deploy/{token}/query", response_model=QueryResponse)
async def query_with_token(
    token: str,
    payload: QueryRequest,
    session=Depends(get_session),
):
    """배포 토큰을 이용한 공개 질의."""

    await enforce_rate_limit(f"deploy:{token}", limit=30, window=60)
    deployment_row = await session.execute(
        sa.text(
            """
            SELECT pipeline_id, config->>'expires_at' AS expires_at
            FROM deployments
            WHERE token = :token
            """
        ),
        {"token": token},
    )
    deployment = deployment_row.fetchone()
    if not deployment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invalid token")
    if deployment.expires_at:
        expires = dt.datetime.fromisoformat(deployment.expires_at)
        if expires < dt.datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token expired")

    vector = await _embed(payload.q)
    sources = await search_similar_chunks(session, deployment.pipeline_id, vector, payload.top_k, payload.threshold)
    context = "\n\n".join(f"[{s.chunk_id}] {s.text}" for s in sources)
    system_prompt = "배포 모드: 근거에 없는 내용은 답하지 말 것"
    user_prompt = f"질문: {payload.q}\n\n근거:\n{context}"
    answer = await call_ollama(user_prompt, system=system_prompt)
    masked, warnings = run_guardrails(answer, [s.text for s in sources])
    await session.execute(
        sa.text(
            """
            INSERT INTO runs (pipeline_id, user_id, kind, status, input, output, started_at, finished_at)
            VALUES (:pipeline_id, NULL, 'deploy', 'success', :input::jsonb, :output::jsonb, NOW(), NOW())
            """
        ),
        {
            "pipeline_id": deployment.pipeline_id,
            "input": payload.model_dump_json(),
            "output": QueryResponse(answer=masked, sources=list(sources), warnings=warnings).model_dump_json(),
        },
    )
    await session.commit()
    return QueryResponse(answer=masked, sources=list(sources), warnings=warnings)
