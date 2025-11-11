"""문장 임베딩 모델 래퍼.

간단 설명(비전공자용):
- 임베딩(embedding): 문장을 숫자 벡터로 바꾼 값입니다. 서로 비슷한 문장을 쉽게 찾게 해줍니다.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import numpy as np

try:  # sentence-transformers가 없으면 더미 모델 사용
    from sentence_transformers import SentenceTransformer
except Exception:  # pylint: disable=broad-except
    SentenceTransformer = None  # type: ignore

LOGGER = logging.getLogger(__name__)
DEFAULT_MODEL = "gte-small"
DEFAULT_DIM = 384


class DummyModel:
    """설치가 어려운 환경을 위한 더미 모델.

    입력 텍스트의 해시를 기반으로 결정론적 난수를 생성하여
    일관된(재현 가능한) 임베딩 벡터를 반환합니다.
    """

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
    LOGGER.warning("SentenceTransformer 미탑재: DummyModel 사용", extra={"model": name})
    return DummyModel()


def embed_texts(texts: list[str], model_name: str = DEFAULT_MODEL) -> dict[str, Any]:
    model = get_model(model_name)
    vectors = model.encode(texts)
    return {
        "vectors": vectors,
        "dim": len(vectors[0]) if vectors else DEFAULT_DIM,
        "model": model_name,
    }


__all__ = ["embed_texts", "DEFAULT_MODEL", "DEFAULT_DIM"]

