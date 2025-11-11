# 문서 기반 RAG 파이프라인 빌더 (MVP)

본 저장소는 문서를 업로드하고, 전처리→임베딩→검색→LLM→가드레일을 거쳐 답변을 생성하는 RAG 파이프라인을 REST API로 구성/테스트/배포할 수 있는 최소기능제품(MVP)입니다. 모든 구성요소는 Docker Compose 한 번으로 기동됩니다.

## 구성요소
- Backend API: FastAPI + Pydantic v2
- Worker/Queue: Celery + Redis
- DB: Postgres + pgvector
- Object Storage: MinIO (S3 호환)
- Embedding Service: Python(sentence-transformers)
- LLM Service: Ollama (Llama3 등)
- Auth: JWT(액세스/리프레시), RBAC(Owner/Editor/Reviewer/Consumer)
- Observability: `/metrics` (Prometheus), 기본 JSON 로깅

## 빠른 시작
1) Docker Desktop 실행, Linux 컨테이너 모드 확인
2) 환경파일 준비: `cp .env.example .env`
3) 기동: `docker compose up --build`
4) 확인:
   - API: `http://localhost:8000/healthz`, 문서: `http://localhost:8000/docs`
   - 임베딩: `http://localhost:8001/healthz`
   - MinIO 콘솔: `http://localhost:9001` (ID/PW: `minioadmin`/`minioadmin`)
   - UI 목업(선택): `http://localhost:3000`

처음 실행 시 모델/이미지 다운로드로 시간이 걸릴 수 있습니다. Ollama 모델은 한 번 받아야 합니다:

```bash
docker exec -it <ollama_container_name> ollama pull llama3
```

## 3단계 마법사(API 조합 예시)
1) 문서 업로드/커밋: Presigned URL을 발급받아 브라우저에서 MinIO로 직접 업로드 → 서버는 파일 바이트를 받지 않습니다.
   - `POST /uploads/check {sha256,size,name}`
   - `POST /uploads/presign {name,mime,size}` → `{url, fields}` 수신 후 브라우저에서 업로드
   - `POST /uploads/commit {name,sha256,size,mime,bucket,key}` → 인덱싱 잡 enqueue
2) 검색 정확도 슬라이더 → top-k/threshold 매핑
   - 빠르게: top_k=4, threshold=0.25
   - 표준: top_k=8, threshold=0.40
   - 정확하게: top_k=12, threshold=0.55
3) 배포 방식 선택 및 권한
   - `POST /pipelines/{id}/publish`
   - `POST /pipelines/{id}/deploy {"type": "link|widget|api"}`
   - 발급된 토큰으로 `/deploy/{token}/query` 호출

## 보안 체크리스트(권장 기본값)
- PII 마스킹 On (전화/이메일/주민번호/주소 등 정규식)
- 금칙 룰 On (욕설/증오/성인/자해/불법)
- 조직 외 공개 전 Reviewer 승인 프로세스 유지
- 발행 토큰 만료시간 설정 (`TOKEN_TTL_MINUTES`)

## 테스트
간단 E2E 테스트는 pytest로 제공합니다.

```bash
pytest -q
```

## 문제 해결(Troubleshooting)
- MinIO/mc 태그 오류 → 최신 태그 사용 중입니다. 네트워크 이슈 시 `docker pull minio/minio:latest`/`minio/mc:latest` 사전 다운로드 후 재시도하세요.
- pgvector 이미지 → `pgvector/pgvector:pg16` 사용. 풀 실패 시 `docker pull pgvector/pgvector:pg16`.
- Ollama 모델 미설치 → 컨테이너에 접속하여 `ollama pull llama3` 수행.
- Windows에서 Docker 연결 오류 → Docker Desktop 실행, Linux 컨테이너 모드/WSL2 상태 확인 (`wsl -l -v`).

## 비전공자 용어설명
- 임베딩: 문장의 의미를 수치화한 벡터
- 임계 점수(threshold): 검색 결과에서 “충분히 관련”하다고 보는 기준값
- 검색 개수(top-k): 상위 몇 개 결과를 사용할지
- 가드레일: 개인정보(PII) 마스킹, 금칙어 탐지 등 안전장치

