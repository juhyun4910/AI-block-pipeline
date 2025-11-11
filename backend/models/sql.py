"""DDL 실행 스텁.

비전공자 팁: 초기 테이블을 만들기 위해 SQL 스크립트를 실행하는 도구입니다.
"""
from __future__ import annotations

from pathlib import Path

from backend.deps.db import execute_sql

INIT_SQL_PATH = Path(__file__).resolve().parent.parent / ".." / "infra" / "initdb" / "01-init.sql"


async def init_db() -> None:
    """초기화 SQL을 실행합니다. Compose 기동 시 worker에서 호출하도록 설계되었습니다."""

    sql = INIT_SQL_PATH.read_text(encoding="utf-8")
    await execute_sql(sql)


__all__ = ["init_db"]
