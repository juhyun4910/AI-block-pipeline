(() => {
  const canvas = document.getElementById("pipeline-canvas");
  if (!canvas) {
    console.warn("파이프라인 캔버스를 찾을 수 없습니다.");
    return;
  }

  const emptyState = document.getElementById("canvas-empty-state");
  const inspectorSelection = document.getElementById("inspector-selection");
  const inspectorDescription = document.getElementById("inspector-description");
  const inspectorConfig = document.getElementById("config-text");
  const inspectorMetrics = document.getElementById("inspector-metrics");
  const duplicateButton = document.getElementById("duplicate-node");
  const deleteButton = document.getElementById("delete-node");
  const templateButton = document.getElementById("add-template");
  const clearButton = document.getElementById("clear-canvas");
  const autoArrangeButton = document.getElementById("auto-arrange");

  let selectedNode = null;
  let nodeIdCounter = 1;
  let activeDrag = null;

  const TYPE_METADATA = {
    data: {
      label: "데이터",
      color: "#2563eb",
      metrics: { latency: "0.6s", tokens: "—", success: "99%" },
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
  };

  const TEMPLATE_PIPELINE = [
    {
      type: "data",
      title: "파일 업로드",
      description: "MinIO · PDF, PPT, DOC 지원",
      config: "s3_bucket=documents",
    },
    {
      type: "index",
      title: "청크 생성",
      description: "Chunk 800 / overlap 120",
      config: "strategy=recursive",
    },
    {
      type: "search",
      title: "하이브리드 검색",
      description: "pgvector + BM25, top_k=5",
      config: "hybrid=true",
    },
    {
      type: "llm",
      title: "LLM 응답",
      description: "Ollama llama3.1:8b · 근거 기반",
      config: "temperature=0.2",
    },
    {
      type: "guard",
      title: "PII 마스킹",
      description: "이메일/전화번호 마스킹",
      config: "masking_level=high",
    },
    {
      type: "output",
      title: "웹앱 배포",
      description: "1클릭 배포 · A/B 지원",
      config: "auth=rbac",
    },
  ];

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
    if (duplicateButton) {
      duplicateButton.disabled = true;
    }
    if (deleteButton) {
      deleteButton.disabled = true;
    }
  }

  function selectNode(node) {
    if (selectedNode === node) {
      return;
    }
    selectedNode?.classList.remove("selected");
    selectedNode = node;
    node.classList.add("selected");
    const type = node.dataset.type;
    const title = node.dataset.title;
    const description = node.dataset.description;
    const config = node.dataset.config;
    if (inspectorSelection) {
      inspectorSelection.textContent = `${title} (${TYPE_METADATA[type]?.label ?? type})`;
    }
    if (inspectorDescription) {
      inspectorDescription.textContent = description;
    }
    if (inspectorConfig) {
      inspectorConfig.value = config ?? "";
    }
    if (inspectorMetrics) {
      const metrics = TYPE_METADATA[type]?.metrics;
      inspectorMetrics.innerHTML = metrics
        ? `
            <li>평균 지연: <strong>${metrics.latency}</strong></li>
            <li>토큰 사용량: <strong>${metrics.tokens}</strong></li>
            <li>성공률: <strong>${metrics.success}</strong></li>
          `
        : `
            <li>평균 지연: <strong>—</strong></li>
            <li>토큰 사용량: <strong>—</strong></li>
            <li>성공률: <strong>—</strong></li>
          `;
    }
    if (duplicateButton) {
      duplicateButton.disabled = false;
    }
    if (deleteButton) {
      deleteButton.disabled = false;
    }
  }

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function makeNodeDraggable(node) {
    node.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      const target = event.target;
      if (target.closest && target.closest(".node-action")) return;
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
    });

    const endDrag = (event) => {
      if (!activeDrag || activeDrag.pointerId !== event.pointerId) return;
      node.releasePointerCapture(event.pointerId);
      activeDrag = null;
    };

    node.addEventListener("pointerup", endDrag);
    node.addEventListener("pointercancel", endDrag);
  }

  function createNode({ type, title, description, config, position }) {
    const meta = TYPE_METADATA[type] ?? { label: type, color: "#64748b" };
    const node = document.createElement("div");
    node.className = "canvas-node";
    node.dataset.type = type;
    node.dataset.title = title;
    node.dataset.description = description;
    node.dataset.config = config;
    node.dataset.id = `node-${nodeIdCounter++}`;

    node.innerHTML = `
      <div class="node-header" style="background:${meta.color}">
        <span class="node-type">${meta.label}</span>
      </div>
      <div class="node-body">
        <h4>${title}</h4>
        <p>${description}</p>
      </div>
    `;

    makeNodeDraggable(node);
    node.addEventListener("click", () => selectNode(node));

    canvas.appendChild(node);
    const canvasRect = canvas.getBoundingClientRect();
    const width = node.offsetWidth || 220;
    const height = node.offsetHeight || 120;
    const defaultX = canvasRect.width / 2 - width / 2;
    const defaultY = canvasRect.height / 2 - height / 2;
    const { x, y } = position ?? { x: defaultX, y: defaultY };
    node.style.left = `${clamp(x, 0, Math.max(canvasRect.width - width, 0))}px`;
    node.style.top = `${clamp(y, 0, Math.max(canvasRect.height - height, 0))}px`;

    updateEmptyState();
    selectNode(node);
    return node;
  }

  function handleBlockDragStart(event) {
    const button = event.currentTarget;
    const payload = {
      type: button.dataset.type,
      title: button.dataset.title,
      description: button.dataset.description,
      config: button.dataset.config,
    };
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
      const y = event.clientY - canvasRect.top - 50;
      createNode({
        type: data.type,
        title: data.title,
        description: data.description,
        config: data.config,
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

  function duplicateSelectedNode() {
    if (!selectedNode) return;
    const rect = selectedNode.getBoundingClientRect();
    const canvasRect = canvas.getBoundingClientRect();
    const newPosition = {
      x: rect.left - canvasRect.left + 24,
      y: rect.top - canvasRect.top + 24,
    };
    createNode({
      type: selectedNode.dataset.type,
      title: `${selectedNode.dataset.title} (복제)` ,
      description: selectedNode.dataset.description,
      config: selectedNode.dataset.config,
      position: newPosition,
    });
  }

  function deleteSelectedNode() {
    if (!selectedNode) return;
    const nodeToRemove = selectedNode;
    resetInspector();
    nodeToRemove.remove();
    updateEmptyState();
  }

  function clearCanvas() {
    canvas.querySelectorAll(".canvas-node").forEach((node) => node.remove());
    resetInspector();
    updateEmptyState();
  }

  function loadTemplate() {
    clearCanvas();
    const canvasRect = canvas.getBoundingClientRect();
    const spacing = canvasRect.width / (TEMPLATE_PIPELINE.length + 1);
    TEMPLATE_PIPELINE.forEach((block, index) => {
      const x = spacing * (index + 1) - 110;
      const y = canvasRect.height / 2 - 70;
      createNode({ ...block, position: { x, y } });
    });
  }

  function autoArrange() {
    const nodes = Array.from(canvas.querySelectorAll(".canvas-node"));
    if (!nodes.length) return;
    const typeOrder = ["data", "index", "search", "llm", "guard", "output"];
    nodes.sort((a, b) => {
      const aOrder = typeOrder.indexOf(a.dataset.type);
      const bOrder = typeOrder.indexOf(b.dataset.type);
      return (aOrder === -1 ? Number.MAX_SAFE_INTEGER : aOrder) -
        (bOrder === -1 ? Number.MAX_SAFE_INTEGER : bOrder);
    });
    const canvasRect = canvas.getBoundingClientRect();
    const spacing = canvasRect.width / (nodes.length + 1);
    nodes.forEach((node, index) => {
      const width = node.offsetWidth || 220;
      const height = node.offsetHeight || 120;
      const x = spacing * (index + 1) - width / 2;
      const y = canvasRect.height / 2 - height / 2;
      node.style.left = `${clamp(x, 0, Math.max(canvasRect.width - width, 0))}px`;
      node.style.top = `${clamp(y, 0, Math.max(canvasRect.height - height, 0))}px`;
    });
  }

  Array.from(document.querySelectorAll(".block-item")).forEach((item) => {
    item.addEventListener("dragstart", handleBlockDragStart);
  });

  canvas.addEventListener("dragover", handleCanvasDragOver);
  canvas.addEventListener("drop", handleCanvasDrop);

  duplicateButton?.addEventListener("click", duplicateSelectedNode);
  deleteButton?.addEventListener("click", deleteSelectedNode);
  clearButton?.addEventListener("click", clearCanvas);
  templateButton?.addEventListener("click", loadTemplate);
  autoArrangeButton?.addEventListener("click", autoArrange);

  document.addEventListener("keydown", (event) => {
    if ((event.key === "Delete" || event.key === "Backspace") && selectedNode) {
      deleteSelectedNode();
    }
  });

  window.addEventListener("load", () => {
    loadTemplate();
  });
})();
