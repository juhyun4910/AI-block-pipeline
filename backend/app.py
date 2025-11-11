"""백엔드 FastAPI 진입점.

비전공자 용어설명:
- 임베딩: 문장을 숫자 벡터로 바꿔서 의미를 비교하는 기술입니다.
- 임계점수(threshold): 검색 결과가 충분히 비슷한지 판단하는 최소 점수입니다.
- 검색개수(top-k): 가장 비슷한 문서를 몇 개 가져올지 결정하는 값입니다.
- 가드레일: 민감정보나 금칙어가 포함되면 차단/마스킹하는 안전장치입니다.
"""
from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import (
    admin,
    auth,
    blocks,
    deploy,
    pipelines,
    query,
    uploads,
)

# 한국어 주석: 서비스 관측을 위한 기본 메트릭 정의
REQUEST_COUNTER = Counter("api_requests_total", "총 요청 수", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("api_request_seconds", "요청 처리 시간", ["method", "path"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 기동/종료 시 필요한 훅.

    실제 운영에서는 DB 연결 확인, 마이그레이션 등을 수행합니다.
    여기서는 TODO 로 남겨두고 로깅만 수행합니다.
    """

    logging.info("FastAPI 앱 시작")
    yield
    logging.info("FastAPI 앱 종료")


app = FastAPI(title="AI Block Pipeline", lifespan=lifespan)

# CORS: 브라우저에서 UI(3000) → API(8000) 호출 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 한국어 주석: 공통 요청 ID를 생성하여 로그 상관관계를 단순화합니다.
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id

    start = time.perf_counter()
    try:
        response: Response = await call_next(request)
    except Exception as exc:  # pylint: disable=broad-except
        logging.exception("Unhandled error", extra={"request_id": request_id})
        response = JSONResponse({"detail": "internal server error"}, status_code=500)
    finally:
        elapsed = time.perf_counter() - start
        REQUEST_COUNTER.labels(request.method, request.url.path, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
        logging.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "elapsed": elapsed,
            },
        )
        response.headers["x-request-id"] = request_id
    return response


@app.get("/healthz")
async def healthz():
    """간단한 헬스체크."""

    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    """Prometheus가 스크랩할 수 있는 메트릭 엔드포인트."""

    return Response(generate_latest(), media_type="text/plain; version=0.0.4")


# 한국어 주석: API 라우터를 모듈별로 등록
routers: list[tuple[APIRouter, str]] = [
    (auth.router, "/auth"),
    (uploads.router, "/uploads"),
    (pipelines.router, "/pipelines"),
    (blocks.router, "/pipelines"),  # 블록 관련 라우터는 파이프라인 하위 경로에 포함
    (query.router, "/pipelines"),
    (deploy.router, ""),
    (admin.router, "/admin"),
]

for router, prefix in routers:
    app.include_router(router, prefix=prefix)


__all__ = ["app"]
