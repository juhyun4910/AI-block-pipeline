"""데이터베이스 의존성.

비전공자 팁: Postgres는 관계형 데이터베이스입니다.
pgvector 확장을 이용해 벡터(임베딩)를 저장하고 검색합니다.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from backend.deps.settings import settings

# 한국어 주석: asyncpg 드라이버를 사용하기 위해 URL을 치환합니다.
ASYNC_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

engine: AsyncEngine = create_async_engine(ASYNC_URL, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends에서 사용할 세션 생성기."""

    async with SessionLocal() as session:
        yield session


async def execute_sql(text: str) -> None:
    """간단한 raw SQL 실행 도우미.

    마이그레이션 스크립트 없이도 초기 DDL을 실행할 수 있도록 합니다.
    """

    async with engine.begin() as conn:
        await conn.execute(sa.text(text))


__all__ = ["engine", "SessionLocal", "get_session", "execute_sql"]
