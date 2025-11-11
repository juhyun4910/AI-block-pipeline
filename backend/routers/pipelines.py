"""파이프라인 CRUD API.

비전공자 팁: 파이프라인은 전처리→임베딩→검색→LLM→가드레일 블록을 순서대로 연결한 설계도입니다.
"""
from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status

from backend.deps.auth import Role, UserContext, get_current_user, require_role
from backend.deps.db import get_session
from backend.models.schema import PipelineCreateRequest, PipelineResponse

router = APIRouter(tags=["pipelines"])


async def _log_audit(session, pipeline_id: int, user_id: str, action: str, detail: dict | None = None) -> None:
    await session.execute(
        sa.text(
            """
            INSERT INTO audit_logs (pipeline_id, user_id, action, detail, created_at)
            VALUES (:pipeline_id, :user_id, :action, :detail::jsonb, :created_at)
            """
        ),
        {
            "pipeline_id": pipeline_id,
            "user_id": user_id,
            "action": action,
            "detail": (detail or {}),
            "created_at": dt.datetime.utcnow(),
        },
    )


@router.post("", response_model=PipelineResponse)
async def create_pipeline(
    payload: PipelineCreateRequest,
    user: UserContext = Depends(require_role(Role.OWNER, Role.EDITOR)),
    session=Depends(get_session),
):
    """새 파이프라인 생성."""

    result = await session.execute(
        sa.text(
            """
            INSERT INTO pipelines (owner_id, name, description, is_published, version, created_at)
            VALUES (:owner, :name, :desc, false, 1, :created_at)
            RETURNING id, owner_id, name, description, is_published, version, created_at
            """
        ),
        {
            "owner": user.user_id,
            "name": payload.name,
            "desc": payload.description,
            "created_at": dt.datetime.utcnow(),
        },
    )
    row = result.fetchone()
    row_data = row._mapping
    await _log_audit(session, row_data["id"], user.user_id, "pipeline_created", {"name": payload.name})
    await session.commit()
    return PipelineResponse(
        id=row_data["id"],
        name=row_data["name"],
        description=row_data["description"],
        is_published=row_data["is_published"],
        version=row_data["version"],
        created_at=row_data["created_at"],
    )


@router.get("", response_model=list[PipelineResponse])
async def list_pipelines(
    user: UserContext = Depends(get_current_user),
    session=Depends(get_session),
):
    """내 파이프라인 목록 조회."""

    rows = await session.execute(
        sa.text("SELECT id, name, description, is_published, version, created_at FROM pipelines WHERE owner_id = :owner"),
        {"owner": user.user_id},
    )
    return [PipelineResponse(**dict(row._mapping)) for row in rows]


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(
    pipeline_id: int,
    user: UserContext = Depends(get_current_user),
    session=Depends(get_session),
):
    """특정 파이프라인 조회."""

    result = await session.execute(
        sa.text(
            "SELECT id, name, description, is_published, version, created_at FROM pipelines WHERE id = :pid AND owner_id = :owner"
        ),
        {"pid": pipeline_id, "owner": user.user_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pipeline not found")
    row_data = row._mapping
    return PipelineResponse(**dict(row_data))


@router.post("/{pipeline_id}/publish", response_model=PipelineResponse)
async def publish_pipeline(
    pipeline_id: int,
    user: UserContext = Depends(require_role(Role.OWNER, Role.REVIEWER)),
    session=Depends(get_session),
):
    """파이프라인을 배포 가능 상태로 전환."""

    result = await session.execute(
        sa.text(
            """
            UPDATE pipelines
            SET is_published = true, version = version + 1
            WHERE id = :pid AND owner_id = :owner
            RETURNING id, name, description, is_published, version, created_at
            """
        ),
        {"pid": pipeline_id, "owner": user.user_id},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pipeline not found")
    row_data = row._mapping
    await _log_audit(session, pipeline_id, user.user_id, "pipeline_published", {"version": row_data["version"]})
    await session.commit()
    return PipelineResponse(**dict(row_data))
