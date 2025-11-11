"""Pydantic 데이터 스키마 모음.

비전공자 팁: 스키마는 API 입출력 형태를 정의해 자동 검증을 도와줍니다.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class UploadCheckRequest(BaseModel):
    sha256: str
    size: int
    name: str


class UploadCheckResponse(BaseModel):
    exists: bool
    allowed: bool


class UploadPresignRequest(BaseModel):
    name: str
    mime: str
    size: int


class UploadPresignResponse(BaseModel):
    url: str
    fields: dict[str, Any]


class UploadCommitRequest(BaseModel):
    name: str
    sha256: str
    size: int
    mime: str
    bucket: str
    key: str
    pipeline_id: Optional[int] = None


class UploadCommitResponse(BaseModel):
    file_id: int
    status: Literal["pending", "ready", "error"]


class PipelineCreateRequest(BaseModel):
    name: str
    description: str | None = None


class PipelineResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_published: bool
    version: int
    created_at: dt.datetime


class BlockCreateRequest(BaseModel):
    type_code: str
    name: str
    config: dict[str, Any] = Field(default_factory=dict)


class EdgeCreateRequest(BaseModel):
    src_block_id: int
    dst_block_id: int


class QueryRequest(BaseModel):
    q: str
    top_k: int = 8
    threshold: float = 0.4
    dedup: bool = True
    with_sources: bool = True


class QuerySource(BaseModel):
    chunk_id: int
    text: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[QuerySource]
    warnings: list[str] = Field(default_factory=list)


class DeployRequest(BaseModel):
    type: Literal["link", "widget", "api"]


class DeployResponse(BaseModel):
    token: str
    url: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminSeedResponse(BaseModel):
    message: str


__all__ = [name for name in globals().keys() if name.endswith("Request") or name.endswith("Response")]
