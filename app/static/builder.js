(() => {
  const canvas = document.getElementById("pipeline-canvas");
  if (!canvas) {
    console.warn("파이프라인 캔버스를 찾을 수 없습니다.");
    return;
  }

  const emptyState = document.getElementById("canvas-empty-state");
  const edgesSvg = document.getElementById("edges-layer");
  const inspectorSelection = document.getElementById("inspector-selection");
  const inspectorDescription = document.getElementById("inspector-description");
  const inspectorConfig = document.getElementById("config-text");
  const inspectorMetrics = document.getElementById("inspector-metrics");
  const inspectorCommon = document.getElementById("inspector-common");
  const inspectorSpecific = document.getElementById("inspector-specific");
  const inspectorValidation = document.getElementById("inspector-validation");
  const duplicateButton = document.getElementById("duplicate-node");
  const deleteButton = document.getElementById("delete-node");
  const clearButton = document.getElementById("clear-canvas");
  const autoArrangeButton = document.getElementById("auto-arrange");
  const templateSelector = document.getElementById("template-selector");
  const applyTemplateButton = document.getElementById("apply-template");
  const templatePills = Array.from(document.querySelectorAll(".template-pill"));

  let selectedNode = null;
  let activeDrag = null;
  const typeCounts = {};
  let nodeIdSeq = 1;
  const edges = []; // { id, fromId, toId, fromSide, toSide }
  const linking = { active: false, fromId: null, fromSide: null, temp: null };

  const TYPE_METADATA = {
    data: {
      label: "데이터",
      color: "#2563eb",
      metrics: { latency: "0.6s", tokens: "—", success: "99%" },
    },
    preprocess: {
      label: "전처리",
      color: "#6366f1",
      metrics: { latency: "0.4s", tokens: "—", success: "98%" },
    },
    index: {
      label: "인덱싱",
      color: "#7c3aed",
      metrics: { latency: "2.4s", tokens: "1.2k", success: "97%" },
    },
    search: {
      label: "검색",
      color: "#0f766e",
      metrics: { latency: "0.9s", tokens: "0.2k", success: "98%" },
    },
    llm: {
      label: "LLM",
      color: "#f97316",
      metrics: { latency: "3.1s", tokens: "1.8k", success: "94%" },
    },
    guard: {
      label: "가드",
      color: "#dc2626",
      metrics: { latency: "0.5s", tokens: "—", success: "99%" },
    },
    output: {
      label: "출력",
      color: "#16a34a",
      metrics: { latency: "—", tokens: "—", success: "100%" },
    },
    orchestration: {
      label: "오케스트레이션",
      color: "#f59e0b",
      metrics: { latency: "0.8s", tokens: "—", success: "96%" },
    },
    observability: {
      label: "관측/비용",
      color: "#14b8a6",
      metrics: { latency: "—", tokens: "—", success: "—" },
    },
    access: {
      label: "접근 제어",
      color: "#8b5cf6",
      metrics: { latency: "—", tokens: "—", success: "—" },
    },
  };

  TYPE_METADATA.upload = { ...TYPE_METADATA.data, label: "업로드" };
  TYPE_METADATA.embedding = { ...TYPE_METADATA.index, label: "임베딩" };
  TYPE_METADATA.deploy = { ...TYPE_METADATA.output, label: "테스트·배포" };

  const EMBEDDING_DIMENSIONS = {
    "nomic-embed-text": 768,
    "all-minilm-l6-v2": 384,
    "text-embedding-3-large": 3072,
  };

  const COMMON_FIELDS = [
    {
      key: "label",
      label: "표시명",
      type: "text",
      default: ({ meta, count }) => `${meta.label} ${count}`,
      helper: "캔버스에 표시될 블록 이름입니다.",
    },
    {
      key: "note",
      label: "설명",
      type: "textarea",
      default: "",
      placeholder: "툴팁/주석을 입력하세요.",
    },
    {
      key: "timeoutMs",
      label: "실행 타임아웃 (ms)",
      type: "number",
      default: 30000,
      min: 1000,
      max: 120000,
      step: 500,
    },
    {
      key: "retries",
      label: "재시도 횟수",
      type: "number",
      default: 1,
      min: 0,
      max: 3,
      step: 1,
    },
    {
      key: "useCache",
      label: "캐시 사용",
      type: "toggle",
      default: true,
    },
    {
      key: "previewRetention",
      label: "출력 미리보기 보관 (회)",
      type: "number",
      default: 5,
      min: 0,
      max: 50,
      step: 1,
    },
  ];

  const BLOCK_FIELDS = {
    data: [
      {
        key: "role",
        label: "역할",
        type: "text",
        default: "문서/데이터 소스 연결",
        readonly: true,
      },
      {
        key: "sourceType",
        label: "소스 유형",
        type: "select",
        default: "upload",
        options: [
          { value: "upload", label: "upload" },
          { value: "url", label: "url" },
          { value: "google-drive", label: "google-drive" },
          { value: "notion", label: "notion" },
          { value: "s3", label: "s3" },
          { value: "local-folder", label: "local-folder" },
        ],
      },
      {
        key: "allowedExtensions",
        label: "파일 확장자",
        type: "text",
        default: "pdf, docx, txt",
      },
      {
        key: "maxFileSizeMb",
        label: "최대 파일 크기 (MB)",
        type: "number",
        default: 50,
        min: 1,
        max: 500,
        step: 1,
      },
      {
        key: "duplicateCheck",
        label: "중복 검사 (SHA256)",
        type: "toggle",
        default: true,
      },
      {
        key: "accessLabel",
        label: "권한 라벨",
        type: "select",
        default: "private",
        options: [
          { value: "private", label: "private" },
          { value: "team", label: "team" },
          { value: "public", label: "public" },
        ],
      },
      {
        key: "autoIndexing",
        label: "자동 인덱싱",
        type: "toggle",
        default: true,
      },
      {
        key: "autoOcr",
        label: "OCR 필요 시 자동 전환",
        type: "toggle",
        default: true,
      },
      {
        key: "presignedExpiry",
        label: "Presigned 만료 (분)",
        type: "number",
        default: 10,
        min: 1,
        max: 60,
        step: 1,
      },
      {
        key: "allowedUrlScheme",
        label: "허용 URL 스킴",
        type: "text",
        default: "https://",
        readonly: true,
      },
    ],
    preprocess: [
      {
        key: "role",
        label: "역할",
        type: "text",
        default: "텍스트 정리",
        readonly: true,
      },
      {
        key: "normalization",
        label: "정규화",
        type: "toggle",
        default: true,
      },
      {
        key: "language",
        label: "언어 감지/변환",
        type: "select",
        default: "auto",
        options: [
          { value: "auto", label: "auto" },
          { value: "ko", label: "ko" },
          { value: "en", label: "en" },
          { value: "ja", label: "ja" },
          { value: "zh", label: "zh" },
        ],
      },
      {
        key: "preserveTables",
        label: "표/코드 보존",
        type: "toggle",
        default: true,
      },
      {
        key: "piiMasking",
        label: "PII 마스킹 (전처리)",
        type: "toggle",
        default: false,
      },
      {
        key: "customRegex",
        label: "사용자 필터 (정규식)",
        type: "textarea",
        default: "",
        placeholder: "한 줄에 하나의 정규식을 입력하세요.",
      },
    ],
    index: [
      {
        key: "role",
        label: "역할",
        type: "text",
        default: "청크 생성+임베딩 저장",
        readonly: true,
      },
      {
        key: "chunkSize",
        label: "청크 크기",
        type: "number",
        default: 800,
        min: 300,
        max: 1200,
        step: 50,
      },
      {
        key: "overlap",
        label: "오버랩",
        type: "number",
        default: 120,
        min: 0,
        max: 400,
        step: 10,
      },
      {
        key: "splitMode",
        label: "분할 규칙",
        type: "select",
        default: "paragraph",
        options: [
          { value: "paragraph", label: "문단 기준" },
          { value: "sentence", label: "문장 기준" },
          { value: "token", label: "토큰 기준" },
        ],
      },
      {
        key: "embeddingModel",
        label: "임베딩 모델",
        type: "select",
        default: "nomic-embed-text",
        options: [
          { value: "nomic-embed-text", label: "nomic-embed-text" },
          { value: "all-minilm-l6-v2", label: "all-minilm-l6-v2" },
          { value: "text-embedding-3-large", label: "text-embedding-3-large" },
        ],
      },
      {
        key: "embeddingDim",
        label: "차원",
        type: "number",
        default: 768,
        readonly: true,
      },
      {
        key: "distanceMetric",
        label: "벡터 거리",
        type: "select",
        default: "cosine",
        options: [
          { value: "cosine", label: "cosine" },
          { value: "dot", label: "dot" },
          { value: "l2", label: "l2" },
        ],
      },
      {
        key: "storeMetadata",
        label: "메타 저장",
        type: "toggle",
        default: true,
      },
      {
        key: "incremental",
        label: "증분 인덱싱",
        type: "toggle",
        default: true,
      },
      {
        key: "ivfProbes",
        label: "IVFFlat 프로브 수",
        type: "text",
        default: "auto",
      },
    ],
    search: [
      {
        key: "role",
        label: "역할",
        type: "text",
        default: "질문 → 관련 청크 검색",
        readonly: true,
      },
      {
        key: "topK",
        label: "top_k",
        type: "number",
        default: 5,
        min: 1,
        max: 20,
        step: 1,
      },
      {
        key: "threshold",
        label: "임계점수",
        type: "number",
        default: 0.3,
        min: 0,
        max: 1,
        step: 0.05,
      },
      {
        key: "hybrid",
        label: "하이브리드 검색",
        type: "toggle",
        default: true,
      },
      {
        key: "keywordBoost",
        label: "키워드 부스트",
        type: "number",
        default: 0.5,
        min: 0,
        max: 2,
        step: 0.1,
      },
      {
        key: "dedupe",
        label: "중복 제거",
        type: "toggle",
        default: true,
      },
      {
        key: "metaFilters",
        label: "메타 필터",
        type: "textarea",
        default: "",
        placeholder: "파일/태그/날짜 조건을 JSON 형태로 입력",
      },
      {
        key: "rerank",
        label: "리랭킹",
        type: "select",
        default: "off",
        options: [
          { value: "off", label: "off" },
          { value: "llm", label: "LLM" },
          { value: "score", label: "간단 점수식" },
        ],
      },
    ],
    llm: [
      {
        key: "role",
        label: "역할",
        type: "text",
        default: "근거 컨텍스트로 최종 답 생성",
        readonly: true,
      },
      {
        key: "model",
        label: "모델",
        type: "select",
        default: "llama3.1:8b",
        options: [
          { value: "llama3.1:8b", label: "llama3.1:8b" },
          { value: "llama3.1:70b", label: "llama3.1:70b" },
          { value: "gpt-4o-mini", label: "gpt-4o-mini" },
        ],
      },
      {
        key: "systemPrompt",
        label: "시스템 프롬프트",
        type: "textarea",
        default: "제공된 근거 텍스트만 사용하여 답변하고, 불확실하면 모른다고 응답합니다.",
      },
      {
        key: "userPrompt",
        label: "사용자 템플릿",
        type: "textarea",
        default: "질문: {{question}}\n근거: {{context}}",
      },
      {
        key: "guardRules",
        label: "기본 규칙",
        type: "checkbox-group",
        options: [
          { value: "context-only", label: "컨텍스트만 사용" },
          { value: "admit-unknown", label: "모르면 모른다" },
          { value: "cite-evidence", label: "근거 나열" },
        ],
        default: ["context-only", "admit-unknown", "cite-evidence"],
      },
      {
        key: "maxTokens",
        label: "맥스 토큰",
        type: "number",
        default: 512,
        min: 128,
        max: 2048,
        step: 16,
      },
      {
        key: "temperature",
        label: "temperature",
        type: "number",
        default: 0.2,
        min: 0,
        max: 1,
        step: 0.05,
      },
      {
        key: "topP",
        label: "top_p",
        type: "number",
        default: 1,
        min: 0.1,
        max: 1,
        step: 0.05,
      },
      {
        key: "outputFormat",
        label: "출력 형식",
        type: "select",
        default: "free-text",
        options: [
          { value: "free-text", label: "free-text" },
          { value: "json", label: "JSON" },
        ],
      },
      {
        key: "jsonSchema",
        label: "JSON 스키마",
        type: "textarea",
        default: "{\n  \"answer\": \"string\",\n  \"evidence\": [\"string\"]\n}",
      },
      {
        key: "streaming",
        label: "스트리밍",
        type: "toggle",
        default: true,
      },
      {
        key: "retryCount",
        label: "에러 시 재시도",
        type: "number",
        default: 1,
        min: 0,
        max: 3,
        step: 1,
      },
      {
        key: "retryDelay",
        label: "재시도 지연 (초)",
        type: "number",
        default: 1,
        min: 0,
        max: 10,
        step: 0.5,
      },
    ],
    guard: [
      {
        key: "role",
        label: "역할",
        type: "text",
        default: "출력 후 필터링/수정",
        readonly: true,
      },
      {
        key: "maskEmail",
        label: "이메일 마스킹",
        type: "toggle",
        default: true,
      },
      {
        key: "maskPhone",
        label: "전화번호 마스킹",
        type: "toggle",
        default: true,
      },
      {
        key: "maskSsn",
        label: "주민번호 마스킹",
        type: "toggle",
        default: false,
      },
      {
        key: "maskAddress",
        label: "주소 마스킹",
        type: "toggle",
        default: false,
      },
      {
        key: "blockCategories",
        label: "금칙 카테고리",
        type: "checkbox-group",
        options: [
          { value: "abuse", label: "욕설" },
          { value: "hate", label: "증오" },
          { value: "adult", label: "성인" },
          { value: "self-harm", label: "자해" },
          { value: "illegal", label: "불법 유도" },
        ],
        default: ["abuse", "hate", "illegal"],
      },
      {
        key: "categoryActions",
        label: "동작",
        type: "action-map",
        options: [
          { value: "allow", label: "허용" },
          { value: "mask", label: "마스킹" },
          { value: "block", label: "차단" },
        ],
        categories: ["abuse", "hate", "adult", "self-harm", "illegal"],
        default: {
          abuse: "mask",
          hate: "block",
          adult: "mask",
          "self-harm": "block",
          illegal: "block",
        },
      },
      {
        key: "crossCheck",
        label: "근거 교차검증",
        type: "select",
        default: "warn",
        options: [
          { value: "off", label: "off" },
          { value: "warn", label: "경고" },
          { value: "regenerate", label: "재생성" },
        ],
      },
      {
        key: "policyMessage",
        label: "정책 메시지",
        type: "textarea",
        default: "정책에 따라 답변을 제공할 수 없습니다.",
      },
      {
        key: "auditLog",
        label: "감사 로그 남기기",
        type: "toggle",
        default: true,
      },
    ],
    output: [
      {
        key: "role",
        label: "역할",
        type: "text",
        default: "사용자 전달/임베드/API",
        readonly: true,
      },
      {
        key: "displayMode",
        label: "표시 형태",
        type: "select",
        default: "webapp",
        options: [
          { value: "webapp", label: "웹앱" },
          { value: "widget", label: "위젯" },
          { value: "api", label: "API" },
        ],
      },
      {
        key: "showEvidence",
        label: "근거 표시",
        type: "toggle",
        default: true,
      },
      {
        key: "allowFollowUp",
        label: "후속 질문 허용",
        type: "toggle",
        default: true,
      },
      {
        key: "exportOptions",
        label: "복사/내보내기",
        type: "checkbox-group",
        options: [
          { value: "text", label: "텍스트" },
          { value: "markdown", label: "Markdown" },
          { value: "pdf", label: "PDF" },
        ],
        default: ["text", "markdown"],
      },
      {
        key: "theme",
        label: "테마",
        type: "select",
        default: "auto",
        options: [
          { value: "light", label: "라이트" },
          { value: "dark", label: "다크" },
          { value: "auto", label: "자동" },
        ],
      },
      {
        key: "visibility",
        label: "공개 범위",
        type: "select",
        default: "private",
        options: [
          { value: "private", label: "private" },
          { value: "link-only", label: "link-only" },
          { value: "public", label: "public" },
        ],
      },
      {
        key: "requireApiKey",
        label: "API 키 필요",
        type: "toggle",
        default: true,
      },
    ],
    orchestration: [
      {
        key: "role",
        label: "역할",
        type: "text",
        default: "분기/조건/루프",
        readonly: true,
      },
      {
        key: "condition",
        label: "조건 분기",
        type: "textarea",
        default: "score > 0.7 ? guard : fallback",
        placeholder: "스코어/메타 기반 분기 로직을 기술하세요.",
      },
      {
        key: "parallel",
        label: "병렬 실행",
        type: "toggle",
        default: false,
      },
      {
        key: "joinStrategy",
        label: "합류",
        type: "select",
        default: "first-win",
        options: [
          { value: "first-win", label: "first-win" },
          { value: "all-success", label: "all-success" },
          { value: "reduce", label: "reduce" },
        ],
      },
      {
        key: "failureHandling",
        label: "실패 처리",
        type: "select",
        default: "retry",
        options: [
          { value: "retry", label: "재시도" },
          { value: "fallback", label: "대체 경로" },
          { value: "abort", label: "중단" },
        ],
      },
    ],
    observability: [
      {
        key: "role",
        label: "역할",
        type: "text",
        default: "실행 로그/메트릭/코스트",
        readonly: true,
      },
      {
        key: "costMeter",
        label: "코스트 미터",
        type: "toggle",
        default: true,
      },
      {
        key: "latencyTarget",
        label: "지연 목표 (p95 ms)",
        type: "number",
        default: 3000,
        min: 500,
        max: 10000,
        step: 100,
      },
      {
        key: "alertHook",
        label: "알림 훅",
        type: "text",
        default: "",
        placeholder: "https://hooks.slack.com/...",
      },
      {
        key: "samplingRate",
        label: "샘플링 비율",
        type: "number",
        default: 0.2,
        min: 0,
        max: 1,
        step: 0.05,
      },
    ],
    access: [
      {
        key: "role",
        label: "역할",
        type: "text",
        default: "권한/팀 관리",
        readonly: true,
      },
      {
        key: "visibility",
        label: "가시성",
        type: "select",
        default: "team",
        options: [
          { value: "team", label: "팀" },
          { value: "organization", label: "조직" },
          { value: "personal", label: "개인" },
        ],
      },
      {
        key: "roles",
        label: "역할",
        type: "checkbox-group",
        options: [
          { value: "owner", label: "소유자" },
          { value: "editor", label: "편집자" },
          { value: "viewer", label: "뷰어" },
        ],
        default: ["owner", "editor", "viewer"],
      },
      {
        key: "dailyQuota",
        label: "일 요청 한도",
        type: "number",
        default: 5000,
        min: 0,
        max: 100000,
        step: 100,
      },
      {
        key: "monthlyQuota",
        label: "월 요청 한도",
        type: "number",
        default: 20000,
        min: 0,
        max: 500000,
        step: 500,
      },
      {
        key: "allowlist",
        label: "IP/도메인 허용목록",
        type: "textarea",
        default: "",
        placeholder: "한 줄에 하나씩 입력하세요.",
      },
    ],
  };

  BLOCK_FIELDS.upload = BLOCK_FIELDS.data;
  BLOCK_FIELDS.embedding = BLOCK_FIELDS.index;
  BLOCK_FIELDS.deploy = BLOCK_FIELDS.output;

  const TEMPLATES = {
    "document-qa": {
      name: "문서 Q&A",
      description: "표준 문서 기반 질의응답 파이프라인",
      nodes: [
        { type: "data", title: "문서 업로드", description: "PDF/문서 업로드", config: { sourceType: "upload", autoIndexing: true } },
        { type: "preprocess", title: "텍스트 정리", description: "공백 정리 + 언어 감지", config: { normalization: true } },
        {
          type: "index",
          title: "청크 + 임베딩",
          description: "chunk 800, overlap 120",
          config: { chunkSize: 800, overlap: 120, embeddingModel: "nomic-embed-text" },
        },
        {
          type: "search",
          title: "하이브리드 검색",
          description: "top_k 5, hybrid on",
          config: { topK: 5, hybrid: true, dedupe: true },
        },
        {
          type: "llm",
          title: "LLM 응답",
          description: "temp 0.2, max_tokens 512",
          config: { temperature: 0.2, maxTokens: 512, streaming: true },
        },
        {
          type: "guard",
          title: "PII 가드",
          description: "이메일/전화 마스킹",
          config: { maskEmail: true, maskPhone: true, blockCategories: ["abuse", "hate", "illegal"] },
        },
        {
          type: "output",
          title: "웹앱",
          description: "근거 하이라이트 on",
          config: { displayMode: "webapp", showEvidence: true },
        },
        {
          type: "observability",
          title: "모니터링",
          description: "코스트 미터",
          config: { costMeter: true, samplingRate: 0.2 },
        },
      ],
    },
    regulation: {
      name: "규정/법령",
      description: "정확도 우선 규정 질의 파이프라인",
      nodes: [
        { type: "data", title: "문서 업로드", description: "규정 PDF", config: { sourceType: "upload" } },
        {
          type: "index",
          title: "정밀 청크",
          description: "chunk 800",
          config: { chunkSize: 800, overlap: 120 },
        },
        {
          type: "search",
          title: "보수적 검색",
          description: "top_k 3",
          config: { topK: 3, hybrid: true, keywordBoost: 0.8 },
        },
        {
          type: "llm",
          title: "JSON 응답",
          description: "temp 0.1, JSON",
          config: { temperature: 0.1, outputFormat: "json", guardRules: ["context-only", "cite-evidence"], jsonSchema: "{\n  \"answer\": \"string\",\n  \"citations\": [\"string\"]\n}" },
        },
        {
          type: "guard",
          title: "근거 검증",
          description: "인용 미포함 시 재생성",
          config: { crossCheck: "regenerate", blockCategories: ["illegal", "hate"], maskEmail: true, maskPhone: true },
        },
        {
          type: "output",
          title: "JSON API",
          description: "API + 근거",
          config: { displayMode: "api", showEvidence: true, requireApiKey: true },
        },
        {
          type: "access",
          title: "팀 권한",
          description: "역할 기반 접근",
          config: { visibility: "organization", roles: ["owner", "viewer"], dailyQuota: 2000 },
        },
      ],
    },
    "product-faq": {
      name: "제품 FAQ",
      description: "친절한 안내 중심",
      nodes: [
        { type: "data", title: "문서 업로드", description: "매뉴얼/FAQ", config: { sourceType: "upload", autoIndexing: true } },
        { type: "preprocess", title: "표/코드 유지", description: "표/코드 보존", config: { preserveTables: true } },
        {
          type: "index",
          title: "임베딩",
          description: "chunk 800",
          config: { chunkSize: 800, overlap: 120 },
        },
        {
          type: "search",
          title: "확장 검색",
          description: "top_k 6",
          config: { topK: 6, hybrid: true },
        },
        {
          type: "llm",
          title: "친절 응답",
          description: "temp 0.5, 예시 포함",
          config: {
            temperature: 0.5,
            streaming: true,
            userPrompt: "질문: {{question}}\n근거: {{context}}\n요청: 예시와 함께 친절하게 답하세요.",
          },
        },
        {
          type: "guard",
          title: "완화 정책",
          description: "욕설 마스킹",
          config: { blockCategories: ["abuse"], categoryActions: { abuse: "mask" }, maskEmail: true, maskPhone: true },
        },
        {
          type: "output",
          title: "위젯",
          description: "후속 질문 on",
          config: { displayMode: "widget", allowFollowUp: true, exportOptions: ["text", "markdown", "pdf"] },
        },
      ],
    },
  };

  function structuredClonePolyfill(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function buildFieldDefault(field, context) {
    if (typeof field.default === "function") {
      return field.default(context);
    }
    if (Array.isArray(field.default)) {
      return [...field.default];
    }
    if (field.type === "action-map") {
      return field.default ? { ...field.default } : {};
    }
    if (field.default && typeof field.default === "object") {
      return structuredClonePolyfill(field.default);
    }
    return field.default ?? null;
  }

  function buildDefaultConfig(type, overrides = {}) {
    const meta = TYPE_METADATA[type] ?? { label: type };
    typeCounts[type] = (typeCounts[type] ?? 0) + 1;
    const count = typeCounts[type];
    const context = { meta, count };
    const config = {};
    [...COMMON_FIELDS, ...(BLOCK_FIELDS[type] ?? [])].forEach((field) => {
      const key = field.key;
      if (Object.prototype.hasOwnProperty.call(overrides, key)) {
        config[key] = structuredClonePolyfill(overrides[key]);
      } else {
        config[key] = buildFieldDefault(field, context);
      }
    });
    return config;
  }

  function updateEmptyState() {
    const hasNodes = canvas.querySelectorAll(".canvas-node").length > 0;
    if (hasNodes) {
      emptyState?.classList.add("hidden");
    } else {
      emptyState?.classList.remove("hidden");
      resetInspector();
    }
  }

  function resetInspector() {
    selectedNode = null;
    if (inspectorSelection) {
      inspectorSelection.textContent = "블록을 선택하세요";
    }
    if (inspectorDescription) {
      inspectorDescription.textContent = "캔버스에서 블록을 선택하면 상세 설명이 표시됩니다.";
    }
    if (inspectorConfig) {
      inspectorConfig.value = "";
    }
    if (inspectorMetrics) {
      inspectorMetrics.innerHTML = `
        <li>평균 지연: <strong>—</strong></li>
        <li>토큰 사용량: <strong>—</strong></li>
        <li>성공률: <strong>—</strong></li>
      `;
    }
    if (inspectorCommon) {
      inspectorCommon.innerHTML = "";
    }
    if (inspectorSpecific) {
      inspectorSpecific.innerHTML = "";
    }
    if (inspectorValidation) {
      inspectorValidation.textContent = "필수 항목을 입력하면 검증 결과가 표시됩니다.";
      inspectorValidation.classList.remove("warn", "ok");
    }
    duplicateButton?.setAttribute("disabled", "true");
    deleteButton?.setAttribute("disabled", "true");
  }

  function clearSvg() {
    if (!edgesSvg) return;
    while (edgesSvg.firstChild) edgesSvg.removeChild(edgesSvg.firstChild);
  }

  function pathForPoints(x1, y1, x2, y2) {
    const dx = Math.abs(x2 - x1);
    const dy = Math.abs(y2 - y1);
    const cx = Math.max(40, dx * 0.5);
    const cy = Math.max(0, dy * 0.2);
    const c1x = x1 + (x2 >= x1 ? cx : -cx);
    const c1y = y1 + (y2 >= y1 ? cy : -cy);
    const c2x = x2 + (x2 >= x1 ? -cx : cx);
    const c2y = y2 + (y2 >= y1 ? -cy : cy);
    return `M ${x1} ${y1} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${x2} ${y2}`;
  }

  function getPortCenter(node, side) {
    const rect = node.getBoundingClientRect();
    const crect = canvas.getBoundingClientRect();
    const xLeft = rect.left - crect.left;
    const yTop = rect.top - crect.top;
    const w = rect.width;
    const h = rect.height;
    switch (side) {
      case "left": return { x: xLeft, y: yTop + h / 2 };
      case "right": return { x: xLeft + w, y: yTop + h / 2 };
      case "top": return { x: xLeft + w / 2, y: yTop };
      case "bottom": return { x: xLeft + w / 2, y: yTop + h };
      default: return { x: xLeft + w / 2, y: yTop + h / 2 };
    }
  }

  function findNodeById(id) {
    return canvas.querySelector(`.canvas-node[data-id="${id}"]`);
  }

  function renderEdges() {
    if (!edgesSvg) return;
    clearSvg();
    const draw = (fromId, fromSide, toId, toSide, className = "edge-path") => {
      const fromNode = findNodeById(fromId);
      const toNode = findNodeById(toId);
      if (!fromNode || !toNode) return;
      const a = getPortCenter(fromNode, fromSide);
      const b = getPortCenter(toNode, toSide);
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("class", className);
      path.setAttribute("d", pathForPoints(a.x, a.y, b.x, b.y));
      edgesSvg.appendChild(path);
    };
    edges.forEach((e) => draw(e.fromId, e.fromSide, e.toId, e.toSide));
    if (linking.active && linking.temp) {
      const { x, y } = linking.temp;
      const fromNode = findNodeById(linking.fromId);
      if (fromNode) {
        const a = getPortCenter(fromNode, linking.fromSide);
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("class", "edge-path temp");
        path.setAttribute("d", pathForPoints(a.x, a.y, x, y));
        edgesSvg.appendChild(path);
      }
    }
  }

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function parseNodeConfig(node) {
    try {
      return JSON.parse(node.dataset.config ?? "{}");
    } catch (error) {
      console.warn("노드 구성을 해석할 수 없습니다.", error);
      return {};
    }
  }

  function updateNodeDataset(node, config) {
    node.dataset.config = JSON.stringify(config, null, 0);
  }

  function updateNodeLabel(node, config) {
    const titleEl = node.querySelector(".node-title");
    if (titleEl) {
      titleEl.textContent = config.label ?? node.dataset.title ?? "블록";
    }
  }

  function renderMetrics(type) {
    const metrics = TYPE_METADATA[type]?.metrics;
    if (!metrics || !inspectorMetrics) return;
    inspectorMetrics.innerHTML = `
      <li>평균 지연: <strong>${metrics.latency ?? "—"}</strong></li>
      <li>토큰 사용량: <strong>${metrics.tokens ?? "—"}</strong></li>
      <li>성공률: <strong>${metrics.success ?? "—"}</strong></li>
    `;
  }

  function createFieldControl(field, value, onChange) {
    const wrapper = document.createElement("label");
    wrapper.className = "form-field";
    const title = document.createElement("span");
    title.textContent = field.label;
    wrapper.appendChild(title);

    let input;
    switch (field.type) {
      case "text":
        input = document.createElement("input");
        input.type = "text";
        input.value = value ?? "";
        if (field.placeholder) input.placeholder = field.placeholder;
        if (field.readonly) input.readOnly = true;
        break;
      case "textarea":
        input = document.createElement("textarea");
        input.value = value ?? "";
        if (field.placeholder) input.placeholder = field.placeholder;
        if (field.readonly) input.readOnly = true;
        break;
      case "number":
        input = document.createElement("input");
        input.type = "number";
        if (value !== null && value !== undefined) input.value = value;
        if (field.min !== undefined) input.min = field.min;
        if (field.max !== undefined) input.max = field.max;
        if (field.step !== undefined) input.step = field.step;
        if (field.readonly) input.readOnly = true;
        break;
      case "select":
        input = document.createElement("select");
        (field.options ?? []).forEach((option) => {
          const opt = document.createElement("option");
          opt.value = option.value;
          opt.textContent = option.label;
          input.appendChild(opt);
        });
        if (value !== undefined && value !== null) {
          input.value = value;
        }
        if (field.readonly) input.disabled = true;
        break;
      case "toggle": {
        wrapper.classList.add("toggle-field");
        input = document.createElement("input");
        input.type = "checkbox";
        input.checked = Boolean(value);
        if (field.readonly) input.disabled = true;
        break;
      }
      case "checkbox-group": {
        wrapper.classList.add("checkbox-group");
        input = document.createElement("div");
        let current = Array.isArray(value) ? [...value] : [];
        (field.options ?? []).forEach((option) => {
          const item = document.createElement("label");
          item.className = "checkbox-item";
          const checkbox = document.createElement("input");
          checkbox.type = "checkbox";
          checkbox.value = option.value;
          checkbox.checked = current.includes(option.value);
          checkbox.addEventListener("change", () => {
            const next = new Set(current);
            if (checkbox.checked) {
              next.add(option.value);
            } else {
              next.delete(option.value);
            }
            current = Array.from(next);
            onChange(current);
          });
          item.appendChild(checkbox);
          const span = document.createElement("span");
          span.textContent = option.label;
          item.appendChild(span);
          input.appendChild(item);
        });
        wrapper.appendChild(input);
        return wrapper;
      }
      case "action-map": {
        wrapper.classList.add("action-map");
        const table = document.createElement("table");
        const headerRow = document.createElement("tr");
        const headCategory = document.createElement("th");
        headCategory.textContent = "카테고리";
        headerRow.appendChild(headCategory);
        const headAction = document.createElement("th");
        headAction.textContent = "동작";
        headerRow.appendChild(headAction);
        table.appendChild(headerRow);
        const current = value && typeof value === "object" ? { ...value } : {};
        (field.categories ?? []).forEach((category) => {
          const row = document.createElement("tr");
          const catCell = document.createElement("td");
          catCell.textContent = category;
          row.appendChild(catCell);
          const selectCell = document.createElement("td");
          const select = document.createElement("select");
          (field.options ?? []).forEach((option) => {
            const opt = document.createElement("option");
            opt.value = option.value;
            opt.textContent = option.label;
            select.appendChild(opt);
          });
          select.value = current[category] ?? field.default?.[category] ?? "mask";
          select.addEventListener("change", () => {
            current[category] = select.value;
            onChange({ ...current });
          });
          selectCell.appendChild(select);
          row.appendChild(selectCell);
          table.appendChild(row);
        });
        wrapper.appendChild(table);
        return wrapper;
      }
      default:
        input = document.createElement("input");
        input.type = "text";
        input.value = value ?? "";
    }

    if (input) {
      input.addEventListener("change", (event) => {
        let nextValue;
        if (field.type === "number") {
          nextValue = event.target.value === "" ? null : Number(event.target.value);
        } else if (field.type === "toggle") {
          nextValue = event.target.checked;
        } else if (field.type === "select") {
          nextValue = event.target.value;
        } else {
          nextValue = event.target.value;
        }
        onChange(nextValue);
      });
      if (field.type === "toggle") {
        const toggleWrapper = document.createElement("div");
        toggleWrapper.className = "toggle-wrapper";
        toggleWrapper.appendChild(input);
        wrapper.appendChild(toggleWrapper);
      } else {
        wrapper.appendChild(input);
      }
    }

    if (field.helper) {
      const helper = document.createElement("small");
      helper.className = "helper";
      helper.textContent = field.helper;
      wrapper.appendChild(helper);
    }

    return wrapper;
  }

  function applyField(container, node, config, field) {
    const value = config[field.key];
    const control = createFieldControl(field, value, (nextValue) => {
      const nextConfig = { ...config, [field.key]: nextValue };
      updateNodeDataset(node, nextConfig);
      if (field.key === "label") {
        updateNodeLabel(node, nextConfig);
      }
      if (field.key === "embeddingModel") {
        const dim = EMBEDDING_DIMENSIONS[nextValue] ?? nextConfig.embeddingDim;
        if (dim) {
          nextConfig.embeddingDim = dim;
          updateNodeDataset(node, nextConfig);
        }
        selectNode(node, { forceRefresh: true });
        return;
      }
      selectNode(node, { skipScroll: true, forceRefresh: true });
    });
    container.appendChild(control);
  }

  function validateConfig(type, config) {
    const messages = [];
    const isUpload = type === "data" || type === "upload";
    if (isUpload && (config.sourceType === "url" || config.source === "url")) {
      if (!config.allowedUrlScheme || !config.allowedUrlScheme.startsWith("https://")) {
        messages.push("URL 소스는 https:// 스킴만 허용됩니다.");
      }
    }
    if (isUpload && config.maxFileSizeMb > 50) {
      messages.push("파일 최대 크기가 50MB를 초과하면 업로드 지연이 발생할 수 있습니다.");
    }
    if (type === "index" || type === "embedding") {
      const expectedDim = EMBEDDING_DIMENSIONS[config.embeddingModel];
      if (expectedDim && expectedDim !== config.embeddingDim) {
        messages.push(`임베딩 차원(${config.embeddingDim})이 모델(${expectedDim})과 다릅니다. 재설정이 필요합니다.`);
      }
    }
    if (type === "search" && config.topK > 10) {
      messages.push("top_k 값이 커서 컨텍스트가 오염되거나 지연이 증가할 수 있습니다.");
    }
    if (type === "llm" && config.outputFormat === "json") {
      if (!config.jsonSchema || !config.jsonSchema.trim()) {
        messages.push("JSON 스키마를 지정해야 합니다. 불일치 시 재생성 옵션을 활용하세요.");
      }
    }
    if (type === "observability" && config.alertHook && !config.alertHook.startsWith("https://")) {
      messages.push("알림 훅은 https:// URL 이어야 합니다.");
    }
    if (type === "access" && (!Array.isArray(config.roles) || config.roles.length === 0)) {
      messages.push("최소 한 개 이상의 역할을 선택하세요.");
    }
    return messages;
  }

  function selectNode(node, options = {}) {
    if (selectedNode === node && !options.forceRefresh) {
      return;
    }
    selectedNode?.classList.remove("selected");
    selectedNode = node;
    node.classList.add("selected");

    const type = node.dataset.type;
    const description = node.dataset.description ?? "";
    const config = parseNodeConfig(node);

    if (inspectorSelection) {
      inspectorSelection.textContent = `${config.label ?? node.dataset.title} (${TYPE_METADATA[type]?.label ?? type})`;
    }
    if (inspectorDescription) {
      inspectorDescription.textContent = description;
    }
    if (inspectorConfig) {
      inspectorConfig.value = JSON.stringify(config, null, 2);
    }
    renderMetrics(type);

    if (inspectorCommon) {
      inspectorCommon.innerHTML = "";
      COMMON_FIELDS.forEach((field) => applyField(inspectorCommon, node, config, field));
    }
    if (inspectorSpecific) {
      inspectorSpecific.innerHTML = "";
      (BLOCK_FIELDS[type] ?? []).forEach((field) => {
        if (field.key === "label") return;
        applyField(inspectorSpecific, node, config, field);
      });
    }

    const validations = validateConfig(type, config);
    if (inspectorValidation) {
      if (validations.length) {
        inspectorValidation.textContent = validations.map((msg) => `• ${msg}`).join("\n");
        inspectorValidation.classList.add("warn");
        inspectorValidation.classList.remove("ok");
      } else {
        inspectorValidation.textContent = "구성이 유효합니다.";
        inspectorValidation.classList.add("ok");
        inspectorValidation.classList.remove("warn");
      }
    }

    duplicateButton?.removeAttribute("disabled");
    deleteButton?.removeAttribute("disabled");

    if (!options.skipScroll) {
      node.scrollIntoView({ block: "nearest" });
    }
  }

  function makeNodeDraggable(node) {
    node.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      const target = event.target;
      if (target.closest && (target.closest(".node-action") || target.closest(".node-port"))) return;
      selectNode(node);
      node.setPointerCapture(event.pointerId);
      const rect = node.getBoundingClientRect();
      const canvasRect = canvas.getBoundingClientRect();
      activeDrag = {
        node,
        pointerId: event.pointerId,
        offsetX: event.clientX - rect.left,
        offsetY: event.clientY - rect.top,
        canvasRect,
      };
      event.preventDefault();
    });

    node.addEventListener("pointermove", (event) => {
      if (!activeDrag || activeDrag.pointerId !== event.pointerId) return;
      const { node: draggedNode, canvasRect, offsetX, offsetY } = activeDrag;
      const x = clamp(event.clientX - canvasRect.left - offsetX, 0, canvasRect.width - draggedNode.offsetWidth);
      const y = clamp(event.clientY - canvasRect.top - offsetY, 0, canvasRect.height - draggedNode.offsetHeight);
      draggedNode.style.left = `${x}px`;
      draggedNode.style.top = `${y}px`;
      renderEdges();
    });

    const endDrag = (event) => {
      if (!activeDrag || activeDrag.pointerId !== event.pointerId) return;
      node.releasePointerCapture(event.pointerId);
      activeDrag = null;
    };

    node.addEventListener("pointerup", endDrag);
    node.addEventListener("pointercancel", endDrag);
  }

  function attachPorts(node) {
    const ports = document.createElement("div");
    ports.className = "node-ports";
    const sides = ["left", "right"]; // 좌/우 포트 제공
    sides.forEach((side) => {
      const port = document.createElement("div");
      port.className = `node-port ${side}`;
      port.dataset.side = side;
      port.title = side;
      port.addEventListener("pointerdown", (event) => {
        event.stopPropagation();
        const nodeId = node.dataset.id;
        linking.active = true;
        linking.fromId = nodeId;
        linking.fromSide = side;
        const crect = canvas.getBoundingClientRect();
        linking.temp = { x: event.clientX - crect.left, y: event.clientY - crect.top };
        renderEdges();
      });
      ports.appendChild(port);
    });
    node.appendChild(ports);
  }

  function createNode({ type, title, description, overrides = {}, position }) {
    const meta = TYPE_METADATA[type] ?? { label: type, color: "#64748b" };
    const config = buildDefaultConfig(type, overrides);

    const node = document.createElement("div");
    node.className = "canvas-node";
    node.dataset.type = type;
    node.dataset.description = description ?? "";
    node.dataset.title = title ?? config.label;
    node.dataset.id = String(nodeIdSeq++);
    updateNodeDataset(node, config);

    node.innerHTML = `
      <div class="node-header" style="background:${meta.color}">
        <span class="node-type">${meta.label}</span>
      </div>
      <div class="node-body">
        <h4 class="node-title">${config.label}</h4>
        <p class="node-description">${description ?? ""}</p>
      </div>
    `;

    attachPorts(node);
    makeNodeDraggable(node);
    node.addEventListener("click", () => selectNode(node, { forceRefresh: true }));

    canvas.appendChild(node);
    const canvasRect = canvas.getBoundingClientRect();
    const width = node.offsetWidth || 180;
    const height = node.offsetHeight || 120;
    const defaultX = canvasRect.width / 2 - width / 2;
    const defaultY = canvasRect.height / 2 - height / 2;
    const { x, y } = position ?? { x: defaultX, y: defaultY };
    node.style.left = `${clamp(x, 0, Math.max(canvasRect.width - width, 0))}px`;
    node.style.top = `${clamp(y, 0, Math.max(canvasRect.height - height, 0))}px`;

    updateEmptyState();
    selectNode(node, { skipScroll: true, forceRefresh: true });
    renderEdges();
    return node;
  }

  function handleBlockDragStart(event) {
    const button = event.currentTarget;
    const payload = {
      type: button.dataset.type,
      title: button.dataset.title,
      description: button.dataset.description,
      overrides: {},
    };
    if (button.dataset.config) {
      try {
        payload.overrides = JSON.parse(button.dataset.config);
      } catch (error) {
        console.warn("블록 기본값을 해석할 수 없습니다.", error);
      }
    }
    event.dataTransfer.setData("application/x-pipeline-block", JSON.stringify(payload));
    event.dataTransfer.effectAllowed = "copy";
  }

  function handleCanvasDrop(event) {
    event.preventDefault();
    const raw =
      event.dataTransfer.getData("application/x-pipeline-block") || event.dataTransfer.getData("text/plain");
    if (!raw) return;
    try {
      const data = JSON.parse(raw);
      const canvasRect = canvas.getBoundingClientRect();
      const x = event.clientX - canvasRect.left - 110;
      const y = event.clientY - canvasRect.top - 60;
      createNode({
        type: data.type,
        title: data.title,
        description: data.description,
        overrides: data.overrides,
        position: { x, y },
      });
    } catch (error) {
      console.warn("드롭 데이터를 해석할 수 없습니다.", error);
    }
  }

  function handleCanvasDragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  }

  // 연결 드래그 중 포인터 이동 → 임시 선 업데이트
  canvas.addEventListener("pointermove", (event) => {
    if (!linking.active) return;
    const crect = canvas.getBoundingClientRect();
    linking.temp = { x: clamp(event.clientX - crect.left, 0, crect.width), y: clamp(event.clientY - crect.top, 0, crect.height) };
    renderEdges();
  });

  // 포트 위에서 포인터 업 → 연결 완료
  canvas.addEventListener("pointerup", (event) => {
    if (!linking.active) return;
    const target = event.target;
    if (target && target.classList && target.classList.contains("node-port")) {
      const toNode = target.closest(".canvas-node");
      const toId = toNode?.dataset.id;
      const toSide = target.dataset.side;
      if (toId && toSide && toId !== linking.fromId) {
        edges.push({ id: `${linking.fromId}-${toId}-${Date.now()}`, fromId: linking.fromId, toId, fromSide: linking.fromSide, toSide });
      }
    }
    linking.active = false;
    linking.fromId = null;
    linking.fromSide = null;
    linking.temp = null;
    renderEdges();
  });

  function duplicateSelectedNode() {
    if (!selectedNode) return;
    const rect = selectedNode.getBoundingClientRect();
    const canvasRect = canvas.getBoundingClientRect();
    const overrides = parseNodeConfig(selectedNode);
    const overridesCopy = { ...overrides, label: `${overrides.label ?? selectedNode.dataset.title} (복제)` };
    const newPosition = {
      x: rect.left - canvasRect.left + 24,
      y: rect.top - canvasRect.top + 24,
    };
    createNode({
      type: selectedNode.dataset.type,
      title: `${overrides.label ?? selectedNode.dataset.title} (복제)`,
      description: selectedNode.dataset.description,
      overrides: overridesCopy,
      position: newPosition,
    });
  }

  function deleteSelectedNode() {
    if (!selectedNode) return;
    const nodeToRemove = selectedNode;
    const id = nodeToRemove.dataset.id;
    for (let i = edges.length - 1; i >= 0; i--) {
      if (edges[i].fromId === id || edges[i].toId === id) {
        edges.splice(i, 1);
      }
    }
    resetInspector();
    nodeToRemove.remove();
    updateEmptyState();
    renderEdges();
  }

  function clearCanvas() {
    canvas.querySelectorAll(".canvas-node").forEach((node) => node.remove());
    Object.keys(typeCounts).forEach((key) => (typeCounts[key] = 0));
    edges.splice(0, edges.length);
    clearSvg();
    resetInspector();
    updateEmptyState();
  }

  function loadTemplate(templateId) {
    const template = TEMPLATES[templateId];
    if (!template) return;
    clearCanvas();
    const canvasRect = canvas.getBoundingClientRect();
    const spacing = canvasRect.width / (template.nodes.length + 1);
    template.nodes.forEach((block, index) => {
      const x = spacing * (index + 1) - 110;
      const y = canvasRect.height / 2 - 70;
      createNode({
        type: block.type,
        title: block.title,
        description: block.description,
        overrides: block.config ?? {},
        position: { x, y },
      });
    });
    if (inspectorValidation) {
      inspectorValidation.textContent = `${template.name} 템플릿이 적용되었습니다.`;
      inspectorValidation.classList.add("ok");
      inspectorValidation.classList.remove("warn");
    }
  }

  function autoArrange() {
    const nodes = Array.from(canvas.querySelectorAll(".canvas-node"));
    if (!nodes.length) return;
    const typeOrder = [
      "data",
      "preprocess",
      "index",
      "search",
      "llm",
      "guard",
      "output",
      "orchestration",
      "observability",
      "access",
    ];
    nodes.sort((a, b) => {
      const aOrder = typeOrder.indexOf(a.dataset.type);
      const bOrder = typeOrder.indexOf(b.dataset.type);
      return (aOrder === -1 ? Number.MAX_SAFE_INTEGER : aOrder) -
        (bOrder === -1 ? Number.MAX_SAFE_INTEGER : bOrder);
    });
    const canvasRect = canvas.getBoundingClientRect();
    const spacing = canvasRect.width / (nodes.length + 1);
    nodes.forEach((node, index) => {
      const width = node.offsetWidth || 180;
      const height = node.offsetHeight || 120;
      const x = spacing * (index + 1) - width / 2;
      const y = canvasRect.height / 2 - height / 2;
      node.style.left = `${clamp(x, 0, Math.max(canvasRect.width - width, 0))}px`;
      node.style.top = `${clamp(y, 0, Math.max(canvasRect.height - height, 0))}px`;
    });
    renderEdges();
  }

  function handleTemplatePillClick(event) {
    const id = event.currentTarget.dataset.template;
    if (id) {
      templateSelector.value = id;
      loadTemplate(id);
    }
  }

  Array.from(document.querySelectorAll(".block-item")).forEach((item) => {
    item.addEventListener("dragstart", handleBlockDragStart);
  });

  canvas.addEventListener("dragover", handleCanvasDragOver);
  canvas.addEventListener("drop", handleCanvasDrop);

  duplicateButton?.addEventListener("click", duplicateSelectedNode);
  deleteButton?.addEventListener("click", deleteSelectedNode);
  clearButton?.addEventListener("click", clearCanvas);
  autoArrangeButton?.addEventListener("click", autoArrange);
  // 템플릿 UI 제거됨

  document.addEventListener("keydown", (event) => {
    if ((event.key === "Delete" || event.key === "Backspace") && selectedNode) {
      deleteSelectedNode();
    }
  });

  window.addEventListener("load", () => {
    // 초기 템플릿 자동 로드 제거 (빈 캔버스 시작)
    renderEdges();
  });
})();
