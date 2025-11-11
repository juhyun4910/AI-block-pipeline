"""환경설정 로더.

비전공자 팁: 환경변수는 서비스 동작에 필요한 주소/비밀값을 담는 설정값입니다.
Docker Compose가 .env 파일을 참고하여 자동으로 주입합니다.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """주요 환경설정. 운영 시에는 별도 비밀관리 시스템으로 교체 가능합니다."""

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    minio_endpoint: str = Field(alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(alias="MINIO_BUCKET")
    # 브라우저 업로드용 공개 엔드포인트 (예: http://localhost:9000). 미설정 시 MINIO_ENDPOINT를 사용.
    minio_public_endpoint: str | None = Field(alias="MINIO_PUBLIC_ENDPOINT", default=None)
    ollama_host: str = Field(alias="OLLAMA_HOST")
    embedding_svc: str = Field(alias="EMBEDDING_SVC")
    jwt_secret: str = Field(alias="JWT_SECRET")
    pgvector_index_lists: int = Field(alias="PGVECTOR_INDEX_LISTS", default=100)
    upload_max_size_mb: int = Field(alias="UPLOAD_MAX_SIZE_MB", default=200)
    token_ttl_minutes: int = Field(alias="TOKEN_TTL_MINUTES", default=60)

    model_config = {"populate_by_name": True}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Settings 인스턴스를 싱글톤처럼 재사용합니다."""

    data = {}
    for name, field in Settings.model_fields.items():
        alias = field.alias or name
        if alias in os.environ:
            data[name] = os.environ[alias]
    return Settings.model_validate(data)


settings = get_settings()

__all__ = ["Settings", "get_settings", "settings"]
