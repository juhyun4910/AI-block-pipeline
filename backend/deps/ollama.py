"""Ollama LLM 호출 헬퍼.

비전공자 팁: LLM은 질문에 자연어로 답하는 AI 모델입니다.
"""
from __future__ import annotations

import httpx

from backend.deps.settings import settings


async def call_ollama(prompt: str, system: str = "", model: str = "llama3") -> str:
    """Ollama HTTP API를 호출하여 답변을 생성합니다.

    운영 환경에서는 스트리밍, 타임아웃, 에러 처리 고도화가 필요합니다.
    """

    url = f"{settings.ollama_host}/api/generate"
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json={"model": model, "prompt": prompt, "system": system})
        resp.raise_for_status()
        data = resp.json()
    return data.get("response", "")


__all__ = ["call_ollama"]
