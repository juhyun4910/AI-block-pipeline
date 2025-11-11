// 간단한 프론트엔드 헬퍼: 회사원도 쉽게 쓰도록 최소 폼과 버튼만 제공합니다.
const API_BASE = 'http://localhost:8000';

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = typeof text === 'string' ? text : JSON.stringify(text, null, 2);
}

function getToken() {
  return localStorage.getItem('access_token') || '';
}

function setToken(token) {
  localStorage.setItem('access_token', token);
  const short = token ? token.slice(0, 12) + '…' : '미로그인';
  setText('login-status', token ? `로그인됨 (${short})` : '미로그인');
}

async function uiLogin() {
  const email = document.getElementById('email').value || 'demo@example.com';
  const password = document.getElementById('password').value || 'demo1234';
  const resp = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!resp.ok) {
    setText('login-status', '로그인 실패');
    return;
  }
  const data = await resp.json();
  setToken(data.access_token);
}

async function uiCheckStatus() {
  try {
    const r1 = await fetch(`${API_BASE}/healthz`);
    setText('status-api', `API: ${r1.ok ? 'OK' : 'X'}`);
  } catch (e) { setText('status-api', 'API: X'); }
  try {
    const r2 = await fetch('http://localhost:8001/healthz');
    setText('status-embed', `Embedding: ${r2.ok ? 'OK' : 'X'}`);
  } catch (e) { setText('status-embed', 'Embedding: X'); }
}

// 브라우저에서 SHA-256 계산
async function sha256Hex(file) {
  const buf = await file.arrayBuffer();
  const digest = await crypto.subtle.digest('SHA-256', buf);
  const arr = Array.from(new Uint8Array(digest));
  return arr.map(b => b.toString(16).padStart(2, '0')).join('');
}

async function uiUpload() {
  const fileEl = document.getElementById('file');
  const file = fileEl.files && fileEl.files[0];
  if (!file) { setText('upload-result', '파일을 선택하세요.'); return; }
  const mime = (document.getElementById('mime').value || file.type || 'application/octet-stream');
  const sha = await sha256Hex(file);
  const size = file.size;
  const name = file.name;
  const token = getToken();
  if (!token) { setText('upload-result', '먼저 로그인하세요.'); return; }

  // 1) check
  let resp = await fetch(`${API_BASE}/uploads/check`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ sha256: sha, size, name })
  });
  const ck = await resp.json();
  if (!ck.allowed) { setText('upload-result', '파일 용량이 허용 한도를 초과합니다.'); return; }

  // 2) presign
  resp = await fetch(`${API_BASE}/uploads/presign`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ name, mime, size })
  });
  if (!resp.ok) { setText('upload-result', 'presign 실패'); return; }
  const ps = await resp.json();

  // 3) 브라우저 → MinIO 직업로드 (HTML form POST)
  const form = new FormData();
  Object.entries(ps.fields).forEach(([k, v]) => form.append(k, v));
  form.append('file', file);
  const up = await fetch(ps.url, { method: 'POST', body: form });
  if (!up.ok) { setText('upload-result', `MinIO 업로드 실패: ${up.status}`); return; }

  // 4) commit → 인덱싱 큐잉
  const pipelineId = parseInt(document.getElementById('optPipelineId').value || '0') || null;
  resp = await fetch(`${API_BASE}/uploads/commit`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ name, sha256: sha, size, mime, bucket: ps.fields.bucket || 'docs', key: ps.fields.key, pipeline_id: pipelineId })
  });
  const cm = await resp.json();
  setText('upload-result', cm);
}

async function uiCreatePipeline() {
  const name = document.getElementById('plName').value || '내 파이프라인';
  const description = document.getElementById('plDesc').value || '';
  const token = getToken();
  const resp = await fetch(`${API_BASE}/pipelines`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ name, description })
  });
  const data = await resp.json();
  setText('pipeline-result', data);
}

async function uiQuery() {
  const id = parseInt(document.getElementById('qPipelineId').value || '0');
  const q = document.getElementById('qText').value || '';
  const top_k = parseInt(document.getElementById('qTopK').value || '8');
  const threshold = parseFloat(document.getElementById('qTh').value || '0.4');
  const dedup = document.getElementById('qDedup').checked;
  const with_sources = document.getElementById('qWithSrc').checked;
  const token = getToken();
  const resp = await fetch(`${API_BASE}/pipelines/${id}/query`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ q, top_k, threshold, dedup, with_sources })
  });
  const data = await resp.json();
  setText('query-result', data);
}

async function uiDeploy() {
  const id = parseInt(document.getElementById('dPipelineId').value || '0');
  const type = document.getElementById('dType').value || 'link';
  const token = getToken();
  const resp = await fetch(`${API_BASE}/pipelines/${id}/deploy`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ type })
  });
  const data = await resp.json();
  setText('deploy-result', data);
}

// 초기 상태 표시
(() => { setToken(getToken()); uiCheckStatus(); })();

