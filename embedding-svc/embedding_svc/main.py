"""임베딩 서비스 HTTP 엔드포인트.

간단 설명(비전공자용):
- 임베딩(embedding): 문장을 숫자 벡터로 바꾼 값입니다. 문장의 의미 유사도를 비교할 때 사용합니다.
"""
from __future__ import annotations

from fastapi import FastAPI

from .models import DEFAULT_MODEL, embed_texts

app = FastAPI(title="Embedding Service")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/embed")
async def embed(payload: dict):
    texts = payload.get("texts", [])
    model = payload.get("model", DEFAULT_MODEL)
    result = embed_texts(texts, model)
    return result

