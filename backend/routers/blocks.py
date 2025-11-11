"""블록 및 엣지 정의 API."""
from __future__ import annotations

import datetime as dt

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status

from backend.deps.auth import Role, UserContext, require_role
from backend.deps.db import get_session
from backend.models.schema import BlockCreateRequest, EdgeCreateRequest

router = APIRouter(tags=["blocks"])


@router.post("/{pipeline_id}/blocks")
async def add_block(
    pipeline_id: int,
    payload: BlockCreateRequest,
    user: UserContext = Depends(require_role(Role.OWNER, Role.EDITOR)),
    session=Depends(get_session),
):
    """블록을 순서대로 추가."""

    order_row = await session.execute(
        sa.text("SELECT COALESCE(MAX(order_no),0)+1 as next FROM blocks WHERE pipeline_id = :pid"),
        {"pid": pipeline_id},
    )
    next_order = order_row.scalar_one()
    result = await session.execute(
        sa.text(
            """
            INSERT INTO blocks (pipeline_id, type_code, name, order_no, config, created_at)
            VALUES (:pid, :type_code, :name, :order_no, :config::jsonb, :created_at)
            RETURNING id
            """
        ),
        {
            "pid": pipeline_id,
            "type_code": payload.type_code,
            "name": payload.name,
            "order_no": next_order,
            "config": payload.config,
            "created_at": dt.datetime.utcnow(),
        },
    )
    block_id = result.scalar_one()
    await session.commit()
    return {"id": block_id, "order_no": next_order}


@router.post("/{pipeline_id}/edges")
async def add_edge(
    pipeline_id: int,
    payload: EdgeCreateRequest,
    user: UserContext = Depends(require_role(Role.OWNER, Role.EDITOR)),
    session=Depends(get_session),
):
    """블록 간 연결 정의."""

    await session.execute(
        sa.text(
            """
            INSERT INTO edges (pipeline_id, src_block, dst_block)
            VALUES (:pid, :src, :dst)
            """
        ),
        {"pid": pipeline_id, "src": payload.src_block_id, "dst": payload.dst_block_id},
    )
    await session.commit()
    return {"status": "ok"}
