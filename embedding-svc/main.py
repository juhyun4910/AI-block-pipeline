"""임베딩 HTTP 서비스."""
from __future__ import annotations

from fastapi import FastAPI

from embedding_svc.models import DEFAULT_MODEL, embed_texts

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
