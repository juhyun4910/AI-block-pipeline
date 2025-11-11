"""문서 인덱싱 Celery 태스크.

비전공자 팁: 업로드된 문서를 자동으로 읽어 전처리→청킹→임베딩→DB 저장을 수행합니다.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import json
import logging
from typing import Any

import httpx
import sqlalchemy as sa

from backend.deps.db import get_session
from backend.deps.minio import get_minio
from backend.deps.settings import settings
from backend.services.chunking import chunk_text
from backend.services.preprocess import preprocess
from backend.workers.celery_app import celery_app

LOGGER = logging.getLogger(__name__)


async def _call_embedding_service(texts: list[str], model: str = "gte-small") -> list[list[float]]:
    """embedding-svc에 배치 요청."""

    if not texts:
        return []
    url = f"{settings.embedding_svc}/embed"
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json={"texts": texts, "model": model})
        resp.raise_for_status()
        data = resp.json()
    return data.get("vectors", [])


async def _index_file(file_id: int, pipeline_id: int | None = None) -> None:
    async with get_session() as session:
        file_row = await session.execute(
            sa.text("SELECT id, bucket, object_key, owner_id FROM files WHERE id = :fid"),
            {"fid": file_id},
        )
        file_info = file_row.fetchone()
        if not file_info:
            LOGGER.error("파일 정보를 찾을 수 없음", extra={"file_id": file_id})
            return

    minio_client = get_minio()
    response = minio_client.get_object(file_info.bucket, file_info.object_key)
    try:
        payload = response.read().decode("utf-8")
    finally:
        response.close()
        response.release_conn()

    preprocessed = preprocess(payload)
    chunks = list(chunk_text(preprocessed.text))
    chunk_texts = [text for _, text in chunks]
    vectors = await _call_embedding_service(chunk_texts)

    async with get_session() as session:
        now = dt.datetime.utcnow()
        doc_meta: dict[str, Any] = {"language": preprocessed.language}
        if pipeline_id is not None:
            doc_meta["pipeline_id"] = pipeline_id
        document_row = await session.execute(
            sa.text(
                """
                INSERT INTO documents (file_id, lang, meta, created_at)
                VALUES (:file_id, :lang, :meta::jsonb, :created_at)
                RETURNING id
                """
            ),
            {
                "file_id": file_id,
                "lang": preprocessed.language,
                "meta": json.dumps(doc_meta),
                "created_at": now,
            },
        )
        document_id = document_row.scalar_one()

        if not chunks:
            await session.execute(
                sa.text("UPDATE files SET status = 'ready' WHERE id = :fid"),
                {"fid": file_id},
            )
            await session.commit()
            return

        if len(vectors) != len(chunks):
            LOGGER.warning(
                "임베딩 수량 불일치", extra={"chunks": len(chunks), "vectors": len(vectors), "file_id": file_id}
            )

        for (pos, text), vector in zip(chunks, vectors):
            chunk_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()
            chunk_row = await session.execute(
                sa.text(
                    """
                    INSERT INTO chunks (document_id, pos, text, hash, created_at)
                    VALUES (:doc_id, :pos, :text, :hash, :created_at)
                    RETURNING id
                    """
                ),
                {
                    "doc_id": document_id,
                    "pos": pos,
                    "text": text,
                    "hash": chunk_hash,
                    "created_at": now,
                },
            )
            chunk_id = chunk_row.scalar_one()
            await session.execute(
                sa.text(
                    """
                    INSERT INTO embeddings (chunk_id, model, dim, vec, created_at)
                    VALUES (:chunk_id, :model, :dim, :vec, :created_at)
                    """
                ),
                {
                    "chunk_id": chunk_id,
                    "model": "gte-small",
                    "dim": len(vector),
                    "vec": vector,
                    "created_at": now,
                },
            )

        await session.execute(
            sa.text("UPDATE files SET status = 'ready' WHERE id = :fid"),
            {"fid": file_id},
        )
        await session.commit()


@celery_app.task(name="index_file")
def index_file_task(file_id: int, pipeline_id: int | None = None) -> str:
    """Celery 작업 엔트리 포인트."""

    LOGGER.info("인덱싱 시작", extra={"file_id": file_id, "pipeline_id": pipeline_id})
    try:
        asyncio.run(_index_file(file_id, pipeline_id))
        return "ok"
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.exception("인덱싱 실패", extra={"file_id": file_id, "pipeline_id": pipeline_id})
        asyncio.run(
            _mark_file_error(file_id)
        )
        raise exc


async def _mark_file_error(file_id: int) -> None:
    async with get_session() as session:
        await session.execute(
            sa.text("UPDATE files SET status = 'error' WHERE id = :fid"),
            {"fid": file_id},
        )
        await session.commit()


def enqueue_index_file(file_id: int, pipeline_id: int | None = None) -> None:
    """라우터에서 사용하기 위한 헬퍼."""

    index_file_task.delay(file_id, pipeline_id)


__all__ = ["enqueue_index_file", "index_file_task"]
