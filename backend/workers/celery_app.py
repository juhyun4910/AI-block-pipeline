"""Celery 앱 초기화.

비전공자 팁: Celery는 백그라운드 작업(예: 문서 인덱싱)을 처리하는 작업자입니다.
"""
from __future__ import annotations

from celery import Celery

from backend.deps.settings import settings

celery_app = Celery(
    "ai_block_pipeline",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    task_always_eager=False,
)


@celery_app.task(bind=True)
def ping(self):  # pragma: no cover - 단순 헬스체크
    return "pong"


__all__ = ["celery_app", "ping"]
