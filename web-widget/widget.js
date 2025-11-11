(function () {
  /**
   * 비전공자 팁: 위젯은 배포 토큰으로 API를 호출하고, postMessage 로 결과를 부모 창에 전달합니다.
   */
  const script = document.currentScript;
  const token = script.getAttribute('data-token');
  const endpoint = script.getAttribute('data-endpoint') || `${window.location.origin}/deploy/${token}/query`;

  async function ask(question) {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ q: question })
    });
    const data = await res.json();
    window.parent.postMessage({ type: 'rag-answer', payload: data }, '*');
    return data;
  }

  window.AIBlockWidget = { ask };
})();
