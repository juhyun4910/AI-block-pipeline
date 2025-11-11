# 문서 기반 RAG 파이프라인 빌더 (MVP)

> "문서를 넣으면 AI가 안전하게 답하도록 설계도를 만들어 드려요" — 비전공자용 툴팁 문구 예시

이 저장소는 문서 업로드부터 전처리 → 임베딩 → 검색 → LLM → 가드레일까지 한 번에 구성하고 배포할 수 있는 백엔드 MVP입니다. 모든 구성요소는 Docker Compose 한 번으로 기동되며, 브라우저는 MinIO 사전 서명 URL을 이용해 파일을 직접 업로드합니다.

## 구성 요소

- **FastAPI 백엔드**: 파이프라인/배포/쿼리 REST API
- **Celery 워커 + Redis**: 비동기 인덱싱 파이프라인
- **Postgres + pgvector**: 문서/청크/임베딩 저장소
- **MinIO**: 문서 객체 스토리지
- **Ollama**: LLM 추론 서버 (기본: Llama3)
- **Embedding Service**: Sentence-Transformers 기반 gte-small 임베딩 HTTP 서비스
- **Prometheus Exporter**: `/metrics`에서 기본 지표 제공

## 빠른 시작

```bash
make dev
# 또는
cp .env.example .env
docker compose up --build
```

기동 후 핵심 엔드포인트는 다음과 같습니다.

- `POST /auth/login` : 샘플 계정 `demo@example.com` / `demo1234`
- `POST /uploads/*` : 파일 체크 → 사전 서명 → 커밋
- `POST /pipelines` : 파이프라인 생성 및 블록 연결
- `POST /pipelines/{id}/query` : 검색 + 생성 테스트
- `POST /pipelines/{id}/deploy` : 공유 링크/위젯/API 토큰 발급
- `POST /deploy/{token}/query` : 배포 토큰으로 질의

## 3단계 마법사에 해당하는 API 조합 예시

1. **문서 업로드/커밋**
   - `POST /uploads/check` → `POST /uploads/presign` → 브라우저에서 MinIO 업로드 → `POST /uploads/commit`
2. **검색 정확도 슬라이더**
   - 아래 표를 참고하여 `top_k`, `threshold` 값을 조정하고 `POST /pipelines/{id}/query` 호출

| 슬라이더 값 | 설명 | top_k | threshold |
|-------------|------|-------|-----------|
| 빠르게      | 빠른 응답, 낮은 정확도 | 4 | 0.25 |
| 표준        | 균형형 추천 | 8 | 0.40 |
| 정확하게    | 높은 정확도, 더 많은 근거 | 12 | 0.55 |

3. **배포 방식 선택 및 권한 설정**
   - `POST /pipelines/{id}/publish`
   - `POST /pipelines/{id}/deploy {"type": "link|widget|api"}`
   - 발급된 토큰을 API/위젯/링크에서 사용하고, 필요 시 Redis 토큰버킷으로 호출 제어

## 보안 체크리스트

- [x] **PII 마스킹 룰 활성화**: 업로드와 응답 단계 모두에서 전화/이메일/주민번호 마스킹
- [x] **금칙 카테고리 필터링**: 욕설, 증오, 성인, 자해, 불법 키워드 탐지
- [x] **Reviewer 승인 후 공개**: `POST /pipelines/{id}/publish` 로 Reviewer/Owner가 검수 완료 후 배포
- [x] **배포 토큰 만료 관리**: `.env`의 `TOKEN_TTL_MINUTES` 로 만료시간 설정

## 테스트

로컬에서 API 의사흐름을 검증하는 pytest 시나리오가 포함되어 있습니다.

```bash
pytest -q
```

## 문제 해결 가이드

- **모델 다운로드 실패**: 오프라인 환경에서는 embedding 서비스가 Dummy 벡터를 사용하며, README 상단 툴팁에 안내된 대로 모델을 선불로드하세요.
- **MinIO Healthcheck 실패**: `curl` 이 이미지에 없는 경우 `docker compose up` 로그에서 실패 원인을 확인 후 `docker compose restart minio` 로 재시도합니다.
- **Ollama 모델 미설치**: `docker exec -it <ollama_container> ollama pull llama3` 명령으로 모델을 다운로드합니다.
- **Celery 인덱싱 실패**: `worker` 로그를 확인하고, 필요 시 `backend/workers/tasks_index.py` 의 TODO 주석을 참고하여 오류처리를 확장합니다.

## 운영 전환 가이드 (요약)

`infra/k8s/` 폴더에 Kubernetes 배포 스켈레톤을 제공합니다. 실제 운영에서는 다음을 권장합니다.

- Postgres/MinIO 는 관리형 서비스를 사용하거나 고가용성 구성을 적용
- Secrets은 Kubernetes Secret 또는 외부 Vault로 이전
- Prometheus/Grafana 스택과 로깅 파이프라인(ELK, Loki 등) 연동

## 추가 참고

- 비전공자 설명 주석은 각 Python 모듈 상단에 기재되어 있습니다.
- README에 적힌 플로우대로 진행하면 GUI 없이도 파이프라인을 구성/배포할 수 있습니다.
- 실패 시 원인과 수정법은 위 문제 해결 가이드를 참고하세요.
