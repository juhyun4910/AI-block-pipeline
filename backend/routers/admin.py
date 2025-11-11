"""관리자용 시드 API."""
from __future__ import annotations

import json

import sqlalchemy as sa
from fastapi import APIRouter, Depends

from backend.deps.auth import Role, require_role
from backend.deps.db import get_session
from backend.models.schema import AdminSeedResponse

router = APIRouter(tags=["admin"])

BLOCK_TYPE_SEED = [
    ("preprocess", "전처리", "preprocess", {"steps": ["pre_normalize", "pre_lang_detect", "pre_table_code_preserve", "pre_pii_mask", "pre_regex_filter"]}),
    ("embedding", "임베딩", "embedding", {"model": "gte-small"}),
    ("search", "검색", "search", {"method": "search_knn"}),
    ("llm", "LLM", "generation", {"model": "llama3"}),
    ("guardrail", "가드레일", "safety", {"rules": ["gr_pii_guard", "gr_moderation", "gr_citation_check"]}),
    ("deploy", "배포", "delivery", {"types": ["deploy_link", "deploy_widget", "deploy_api"]}),
]


@router.post("/seed", response_model=AdminSeedResponse)
async def seed_block_types(
    user=Depends(require_role(Role.OWNER)),
    session=Depends(get_session),
):
    """block_types 테이블 초기 데이터 입력."""

    for code, display_name, category, schema in BLOCK_TYPE_SEED:
        await session.execute(
            sa.text(
                """
                INSERT INTO block_types (code, display_name, category, schema_json)
                VALUES (:code, :display_name, :category, :schema::jsonb)
                ON CONFLICT (code) DO UPDATE SET display_name = EXCLUDED.display_name
                """
            ),
            {
                "code": code,
                "display_name": display_name,
                "category": category,
                "schema": json.dumps(schema, ensure_ascii=False),
            },
        )
    await session.commit()
    return AdminSeedResponse(message="seeded")
