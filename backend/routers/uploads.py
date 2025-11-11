"""업로드 관련 REST API.

비전공자 팁: 서버는 파일 바이트를 받지 않고, 브라우저가 직접 MinIO에 업로드합니다.
"""
from __future__ import annotations

import datetime as dt
import logging
import uuid

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from minio import PostPolicy

from backend.deps.auth import UserContext, get_current_user
from backend.deps.db import get_session
from backend.deps.minio import get_minio
from backend.deps.rate_limit import enforce_rate_limit
from backend.deps.settings import settings
from backend.models.schema import (
    UploadCheckRequest,
    UploadCheckResponse,
    UploadCommitRequest,
    UploadCommitResponse,
    UploadPresignRequest,
    UploadPresignResponse,
)
from backend.workers.tasks_index import enqueue_index_file

router = APIRouter(tags=["uploads"])
LOGGER = logging.getLogger(__name__)


@router.post("/check", response_model=UploadCheckResponse)
async def check_upload(
    payload: UploadCheckRequest,
    user: UserContext = Depends(get_current_user),
    session=Depends(get_session),
):
    """파일이 이미 업로드 되었는지 확인."""

    await enforce_rate_limit(f"upload-check:{user.user_id}")
    row = await session.execute(
        sa.text("SELECT id FROM files WHERE owner_id = :owner AND sha256 = :sha"),
        {"owner": user.user_id, "sha": payload.sha256},
    )
    exists = row.fetchone() is not None
    allowed = payload.size <= settings.upload_max_size_mb * 1024 * 1024
    return UploadCheckResponse(exists=exists, allowed=allowed)


@router.post("/presign", response_model=UploadPresignResponse)
async def presign_upload(
    payload: UploadPresignRequest,
    user: UserContext = Depends(get_current_user),
):
    """MinIO에 직접 업로드할 수 있는 사전 서명 정보를 발급."""

    client = get_minio()
    policy = PostPolicy()
    object_key = f"{user.user_id}/{uuid.uuid4()}-{payload.name}"
    expires = dt.timedelta(minutes=10)
    policy.set_bucket_name(settings.minio_bucket)
    policy.set_key(object_key)
    policy.set_content_type(payload.mime)
    policy.set_content_length_range(1, settings.upload_max_size_mb * 1024 * 1024)
    policy.set_expiration(dt.datetime.utcnow() + expires)
    url, fields = client.presigned_post_policy(policy)
    return UploadPresignResponse(url=url, fields={**fields, "key": object_key})


@router.post("/commit", response_model=UploadCommitResponse)
async def commit_upload(
    payload: UploadCommitRequest,
    user: UserContext = Depends(get_current_user),
    session=Depends(get_session),
):
    """업로드가 완료되었음을 선언하고 인덱싱을 큐잉."""

    await enforce_rate_limit(f"upload-commit:{user.user_id}")
    now = dt.datetime.utcnow()
    insert_result = await session.execute(
        sa.text(
            """
            INSERT INTO files (owner_id, name, sha256, size_bytes, mime, bucket, object_key, status, created_at)
            VALUES (:owner, :name, :sha, :size, :mime, :bucket, :key, 'pending', :created_at)
            ON CONFLICT (owner_id, sha256) DO UPDATE SET status = 'pending'
            RETURNING id
            """
        ),
        {
            "owner": user.user_id,
            "name": payload.name,
            "sha": payload.sha256,
            "size": payload.size,
            "mime": payload.mime,
            "bucket": payload.bucket,
            "key": payload.key,
            "created_at": now,
        },
    )
    file_id = insert_result.scalar_one()
    await session.commit()

    enqueue_index_file(file_id=file_id, pipeline_id=payload.pipeline_id)
    LOGGER.info("인덱싱 큐잉", extra={"file_id": file_id, "pipeline_id": payload.pipeline_id})
    return UploadCommitResponse(file_id=file_id, status="pending")
