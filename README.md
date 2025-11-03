# AI Block Pipeline Mockup

FastAPI 기반으로 작성된 드래그 앤 드랍 AI 파이프라인 빌더의 목업 UI와 프로젝트 설명 페이지입니다. 문서 기반 RAG 파이프라인 서비스의 초기 컨셉을 시각적으로 확인하고 설계를 정리한 페이지를 함께 제공합니다.

## 실행 방법

1. 의존성 설치

   ```bash
   pip install -r requirements.txt
   ```

2. 개발 서버 실행

   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

3. 브라우저에서 확인

   - 목업 파이프라인 빌더: <http://localhost:8000/>
   - 프로젝트 상세 설명: <http://localhost:8000/project-overview>

## 폴더 구조

```
app/
├── main.py              # FastAPI 엔트리 포인트
├── templates/           # Jinja2 템플릿
│   ├── base.html
│   ├── index.html
│   └── project_overview.html
└── static/
    └── styles.css       # 공통 스타일 시트
```

## 참고

- 현재는 기능을 시각화한 목업 단계이며 실제 드래그 앤 드랍 로직과 데이터 처리는 포함되어 있지 않습니다.
- 추후 React Flow 기반 프런트엔드와 백엔드 API를 연동하여 완전한 파이프라인 빌더로 확장할 수 있습니다.
