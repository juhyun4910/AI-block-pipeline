"""임베딩 모델 로더."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import numpy as np

try:  # pragma: no cover - sentence-transformers 미설치 시 대체
    from sentence_transformers import SentenceTransformer
except Exception:  # pylint: disable=broad-except
    SentenceTransformer = None

LOGGER = logging.getLogger(__name__)
DEFAULT_MODEL = "gte-small"
DEFAULT_DIM = 384


class DummyModel:
    """모델이 없을 때 해시 기반 벡터를 생성하는 간단한 대체."""

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            rng = np.random.default_rng(abs(hash(text)) % (2**32))
            vec = rng.standard_normal(DEFAULT_DIM)
            vec = vec / np.linalg.norm(vec)
            vectors.append(vec.astype(float).tolist())
        return vectors


@lru_cache(maxsize=2)
def get_model(name: str = DEFAULT_MODEL):
    if SentenceTransformer:
        LOGGER.info("loading sentence transformer", extra={"model": name})
        return SentenceTransformer(name)
    LOGGER.warning("SentenceTransformer 미설치: DummyModel 사용", extra={"model": name})
    return DummyModel()


def embed_texts(texts: list[str], model_name: str = DEFAULT_MODEL) -> dict[str, Any]:
    model = get_model(model_name)
    vectors = model.encode(texts)
    return {"vectors": vectors, "dim": len(vectors[0]) if vectors else DEFAULT_DIM, "model": model_name}


__all__ = ["embed_texts", "DEFAULT_MODEL", "DEFAULT_DIM"]
