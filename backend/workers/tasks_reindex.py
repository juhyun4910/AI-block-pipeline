"""재인덱싱 태스크 스텁."""
from __future__ import annotations

from backend.workers.celery_app import celery_app
from backend.workers.tasks_index import index_file_task


@celery_app.task(name="reindex_pipeline")
def reindex_pipeline(pipeline_id: int) -> str:
    """단순히 연결된 파일을 순회하는 TODO."""

    # TODO: 파이프라인-파일 매핑 테이블 생성 후 구현
    return f"queued reindex for {pipeline_id}"


__all__ = ["reindex_pipeline"]
