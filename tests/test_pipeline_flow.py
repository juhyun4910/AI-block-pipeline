"""업로드부터 질의까지의 간단한 E2E 시뮬레이션 테스트."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from types import SimpleNamespace

import json
import os
import sys
import types

sys.path.append(str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("MINIO_ENDPOINT", "http://minio:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin")
os.environ.setdefault("MINIO_BUCKET", "docs")
os.environ.setdefault("OLLAMA_HOST", "http://ollama:11434")
os.environ.setdefault("EMBEDDING_SVC", "http://embedding:8000")
os.environ.setdefault("JWT_SECRET", "testsecret")

if "prometheus_client" not in sys.modules:  # 테스트 의존성 경량화
    class _DummyMetric:
        def labels(self, *args, **kwargs):
            return self

        def observe(self, *args, **kwargs):
            return None

        def inc(self, *args, **kwargs):
            return None

    sys.modules["prometheus_client"] = types.SimpleNamespace(
        Counter=lambda *args, **kwargs: _DummyMetric(),
        Histogram=lambda *args, **kwargs: _DummyMetric(),
        generate_latest=lambda: b"",
    )


if "sqlalchemy" not in sys.modules:  # 최소 기능 스텁
    sa_module = types.SimpleNamespace()

    def _text(query: str):
        return types.SimpleNamespace(text=query)

    sa_module.text = _text
    sys.modules["sqlalchemy"] = sa_module

    ext_module = types.ModuleType("sqlalchemy.ext")
    sys.modules["sqlalchemy.ext"] = ext_module

    async_module = types.ModuleType("sqlalchemy.ext.asyncio")

    class _AsyncSession:  # pragma: no cover - 타입 호환 목적
        ...

    def _create_async_engine(*args, **kwargs):
        return None

    def _async_sessionmaker(*args, **kwargs):
        return None

    async_module.AsyncSession = _AsyncSession
    async_module.AsyncEngine = object
    async_module.async_sessionmaker = _async_sessionmaker
    async_module.create_async_engine = _create_async_engine
    sys.modules["sqlalchemy.ext.asyncio"] = async_module


if "jose" not in sys.modules:  # JWT 최소 스텁
    jose_module = types.ModuleType("jose")

    class _JWTError(Exception):
        ...

    def _encode(payload, secret, algorithm="HS256"):
        return json.dumps(payload)

    def _decode(token, secret, algorithms=None):
        return json.loads(token)

    jose_module.JWTError = _JWTError
    jose_module.jwt = types.SimpleNamespace(encode=_encode, decode=_decode)
    sys.modules["jose"] = jose_module
    sys.modules["jose.jwt"] = jose_module.jwt


if "redis" not in sys.modules:
    redis_module = types.ModuleType("redis")
    asyncio_module = types.ModuleType("redis.asyncio")

    class _Redis:
        def __init__(self):
            self.store = {}

        async def incr(self, key):
            self.store[key] = self.store.get(key, 0) + 1
            return self.store[key]

        async def expire(self, key, window):  # pragma: no cover - 단순 시뮬레이션
            return True

    def _from_url(url, decode_responses=True):
        return _Redis()

    asyncio_module.Redis = _Redis
    asyncio_module.from_url = _from_url
    redis_module.asyncio = asyncio_module
    sys.modules["redis"] = redis_module
    sys.modules["redis.asyncio"] = asyncio_module


if "minio" not in sys.modules:
    minio_module = types.ModuleType("minio")

    class _Minio:
        def __init__(self, *args, **kwargs):
            pass

        def presigned_post_policy(self, policy):
            return ("http://minio/upload", {"policy": "stub", "x-amz-signature": "stub"})

    class _PostPolicy:
        def set_bucket_name(self, *args, **kwargs):
            return None

        def set_key(self, *args, **kwargs):
            return None

        def set_content_type(self, *args, **kwargs):
            return None

        def set_content_length_range(self, *args, **kwargs):
            return None

        def set_expiration(self, *args, **kwargs):
            return None

    minio_module.Minio = _Minio
    minio_module.PostPolicy = _PostPolicy
    sys.modules["minio"] = minio_module


if "celery" not in sys.modules:
    celery_module = types.ModuleType("celery")

    class _TaskWrapper:
        def __init__(self, func):
            self.func = func

        def __call__(self, *args, **kwargs):
            return self.func(*args, **kwargs)

        def delay(self, *args, **kwargs):
            return self.func(*args, **kwargs)

    class _Celery:
        def __init__(self, *args, **kwargs):
            self.conf = types.SimpleNamespace(update=lambda *a, **k: None)

        def task(self, *args, **kwargs):
            def decorator(func):
                return _TaskWrapper(func)

            return decorator

    def _CeleryFactory(*args, **kwargs):
        return _Celery()

    celery_module.Celery = _CeleryFactory
    sys.modules["celery"] = celery_module

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.deps.auth import Role, UserContext, get_current_user
from backend.deps.db import get_session
from backend.models.schema import QuerySource


class Row(SimpleNamespace):
    """SQLAlchemy Row 대체."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mapping = kwargs


class FakeResult:
    def __init__(self, rows: list[Row]):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def scalar_one(self):
        return self._rows[0].id if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class FakeSession:
    def __init__(self):
        self.files: dict[int, Row] = {}
        self.pipelines: dict[int, Row] = {}
        self.deployments: dict[str, Row] = {}
        self.audit_logs: list[dict] = []
        self.runs: list[dict] = []
        self.index_calls: list[tuple[int, int | None]] = []
        self._ids = {"files": 1, "pipelines": 1}

    async def execute(self, query, params=None):  # noqa: D401 - SQL 핸들링
        text = str(query)
        params = params or {}
        now = dt.datetime.utcnow()
        if "INSERT INTO pipelines" in text:
            pid = self._ids["pipelines"]
            self._ids["pipelines"] += 1
            row = Row(
                id=pid,
                owner_id=params["owner"],
                name=params["name"],
                description=params.get("desc"),
                is_published=False,
                version=1,
                created_at=now,
            )
            self.pipelines[pid] = row
            return FakeResult([row])
        if "SELECT id, name, description" in text and "WHERE owner_id" in text:
            rows = [row for row in self.pipelines.values() if row.owner_id == params["owner"]]
            return FakeResult(rows)
        if "SELECT id, name, description" in text and "WHERE id" in text:
            row = self.pipelines.get(params["pid"])
            if row and row.owner_id == params["owner"]:
                return FakeResult([row])
            return FakeResult([])
        if "UPDATE pipelines" in text:
            row = self.pipelines.get(params["pid"])
            if row and row.owner_id == params["owner"]:
                row.is_published = True
                row.version += 1
                row._mapping = {
                    **row._mapping,
                    "is_published": row.is_published,
                    "version": row.version,
                }
                return FakeResult([row])
            return FakeResult([])
        if "INSERT INTO audit_logs" in text:
            self.audit_logs.append({"pipeline_id": params["pipeline_id"], "action": params["action"]})
            return FakeResult([])
        if "INSERT INTO files" in text:
            fid = self._ids["files"]
            self._ids["files"] += 1
            row = Row(id=fid, owner_id=params["owner"], sha256=params["sha"], status="pending")
            self.files[fid] = row
            return FakeResult([row])
        if "SELECT id FROM files" in text:
            for row in self.files.values():
                if row.owner_id == params["owner"] and row.sha256 == params["sha"]:
                    return FakeResult([row])
            return FakeResult([])
        if "SELECT is_published" in text:
            row = self.pipelines.get(params["pid"])
            if row and row.owner_id == params["owner"]:
                return FakeResult([Row(is_published=row.is_published)])
            return FakeResult([])
        if "INSERT INTO deployments" in text:
            token = params["token"]
            self.deployments[token] = Row(
                pipeline_id=params["pipeline_id"],
                token=token,
                config={"expires_at": params["config"]["expires_at"]},
            )
            return FakeResult([Row(id=1)])
        if "SELECT pipeline_id, config->>'expires_at'" in text:
            dep = self.deployments.get(params["token"])
            if not dep:
                return FakeResult([])
            return FakeResult([Row(pipeline_id=dep.pipeline_id, expires_at=dep.config["expires_at"])] )
        if "INSERT INTO runs" in text:
            self.runs.append({"pipeline_id": params["pipeline_id"], "input": params["input"]})
            return FakeResult([])
        return FakeResult([])

    async def commit(self):
        return None


@pytest.fixture
def client(monkeypatch):
    session = FakeSession()

    async def fake_get_session():
        yield session

    async def fake_current_user():
        return UserContext(user_id="1", role=Role.OWNER)

    async def fake_embed_query(text: str):
        return [0.1, 0.2, 0.3]

    async def fake_search(session_obj, pipeline_id, embedding, top_k, threshold):
        return [QuerySource(chunk_id=1, text="고객 이메일 test@example.com", score=0.9)]

    async def fake_call_ollama(prompt: str, system: str = "", model: str = "llama3"):
        return "결과: test@example.com hate"

    async def fake_embed_deploy(text: str):
        return [0.1, 0.2, 0.3]

    app.dependency_overrides[get_session] = fake_get_session
    app.dependency_overrides[get_current_user] = fake_current_user

    monkeypatch.setattr("backend.routers.uploads.enqueue_index_file", lambda file_id, pipeline_id=None: session.index_calls.append((file_id, pipeline_id)))
    monkeypatch.setattr("backend.routers.query._embed_query", fake_embed_query)
    monkeypatch.setattr("backend.routers.query.search_similar_chunks", fake_search)
    monkeypatch.setattr("backend.deps.ollama.call_ollama", fake_call_ollama)
    monkeypatch.setattr("backend.routers.deploy._embed", fake_embed_deploy)
    monkeypatch.setattr("backend.routers.deploy.search_similar_chunks", fake_search)
    monkeypatch.setattr("backend.routers.deploy.call_ollama", fake_call_ollama)

    with TestClient(app) as test_client:
        yield test_client, session

    app.dependency_overrides.clear()


def test_full_flow(client):
    test_client, session = client

    # 파이프라인 생성
    resp = test_client.post("/pipelines", json={"name": "샘플 파이프라인", "description": "테스트"})
    assert resp.status_code == 200
    pipeline_id = resp.json()["id"]

    # 업로드 체크 및 커밋
    check = test_client.post("/uploads/check", json={"sha256": "abc", "size": 10, "name": "doc.txt"})
    assert check.json()["allowed"] is True
    commit = test_client.post(
        "/uploads/commit",
        json={
            "name": "doc.txt",
            "sha256": "abc",
            "size": 10,
            "mime": "text/plain",
            "bucket": "docs",
            "key": "1/doc.txt",
            "pipeline_id": pipeline_id,
        },
    )
    assert commit.status_code == 200
    assert session.index_calls[0][1] == pipeline_id

    # 파이프라인 발행
    publish = test_client.post(f"/pipelines/{pipeline_id}/publish")
    assert publish.json()["is_published"] is True

    # 배포 토큰 발급
    deploy = test_client.post(f"/pipelines/{pipeline_id}/deploy", json={"type": "api"})
    token = deploy.json()["token"]

    # 배포 토큰으로 질의
    query_resp = test_client.post(f"/deploy/{token}/query", json={"q": "고객 이메일?"})
    body = query_resp.json()
    assert "[이메일]" in body["answer"]
    assert any("증오" in warn for warn in body["warnings"])
    assert body["sources"][0]["chunk_id"] == 1
