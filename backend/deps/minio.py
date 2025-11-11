"""MinIO S3 클라이언트.

비전공자 팁: 오브젝트 스토리지는 큰 파일을 저장하는 전용 저장소로, 서버가 파일을 직접 들고 있지 않아도 됩니다.
"""
from __future__ import annotations

from minio import Minio

from backend.deps.settings import settings


def get_minio() -> Minio:
    """MinIO 클라이언트를 초기화합니다."""

    return Minio(
        settings.minio_endpoint.replace("http://", "").replace("https://", ""),
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_endpoint.startswith("https"),
    )


__all__ = ["get_minio"]
