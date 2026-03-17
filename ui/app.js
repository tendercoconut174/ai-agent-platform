const API_URL_KEY = "ai-agent-platform-api-url";
const SESSION_KEY = "ai-agent-platform-session-id";

let abortController = null;

function getApiUrl() {
  try {
    const el = document.getElementById("api-url");
    return (el && el.value) ? el.value : "http://localhost:8000";
  } catch (_) {
    return "http://localhost:8000";
  }
}

function getSessionId() {
  return localStorage.getItem(SESSION_KEY);
}

function setSessionId(id) {
  if (id) localStorage.setItem(SESSION_KEY, id);
  document.getElementById("session-id").textContent = id || "—";
}

function setWorkflowId(id) {
  document.getElementById("workflow-id").textContent = id || "—";
}

function setIntent(intent) {
  const badge = document.getElementById("intent-badge");
  if (!intent) {
    badge.classList.add("hidden");
    return;
  }
  badge.textContent = intent;
  badge.className = "intent-badge " + intent;
  badge.classList.remove("hidden");
}

function addMessage(role, content, isError = false) {
  const container = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.className = `message ${role}` + (isError ? " error" : "");
  div.textContent = content;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return div;
}

function addLoadingMessage() {
  const container = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.className = "message assistant loading";
  div.id = "loading-msg";
  div.textContent = "Thinking...";
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function removeLoadingMessage() {
  document.getElementById("loading-msg")?.remove();
}

function renderSteps(stepResults) {
  const list = document.getElementById("steps-list");
  list.innerHTML = "";

  if (!stepResults || stepResults.length === 0) {
    list.innerHTML = '<p class="steps-placeholder">Steps will appear here.</p>';
    return;
  }

  stepResults.forEach((step) => {
    const div = document.createElement("div");
    const running = step.running === true;
    const statusClass = running ? "running" : (step.success ? "success" : "error");
    div.className = `step-item ${statusClass}`;
    const resultText = (step.result || step.error || "").slice(0, 500);
    const isCodeAgent = ["code", "analysis", "generator"].includes(step.agent_type);
    const resultHtml = running && !resultText
      ? '<span class="step-running">Running…</span>'
      : escapeHtml(resultText) + ((step.result || "").length > 500 ? "…" : "");
    div.innerHTML = `
      <div class="step-header">
        <span class="step-id">${step.node_id}</span>
        <span class="step-agent">${step.agent_type}</span>
        ${isCodeAgent ? '<span class="step-badge" title="Code ran automatically">✓ ran</span>' : ""}
      </div>
      <div class="step-result">${resultHtml}</div>
    `;
    list.appendChild(div);
  });
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function showClarificationBanner(question) {
  const banner = document.getElementById("clarification-banner");
  document.getElementById("clarification-question").textContent = question;
  document.getElementById("clarification-input").value = "";
  banner.classList.remove("hidden");
  document.querySelector(".input-area").classList.add("clarification-active");
}

function hideClarificationBanner() {
  document.getElementById("clarification-banner").classList.add("hidden");
  document.querySelector(".input-area").classList.remove("clarification-active");
}

function setStatus(text) {
  document.getElementById("status-text").textContent = text || "";
}

function showStopButton() {
  document.getElementById("send-btn").classList.add("hidden");
  document.getElementById("stop-btn").classList.remove("hidden");
}

function hideStopButton() {
  document.getElementById("send-btn").classList.remove("hidden");
  document.getElementById("stop-btn").classList.add("hidden");
}

let pendingCodeApprovalId = null;

function showCodeApprovalBanner(code, approvalId) {
  pendingCodeApprovalId = approvalId;
  document.getElementById("code-approval-code").textContent = code;
  document.getElementById("code-approval-banner").classList.remove("hidden");
  document.querySelector(".input-area").classList.add("clarification-active");
}

function hideCodeApprovalBanner() {
  pendingCodeApprovalId = null;
  document.getElementById("code-approval-banner").classList.add("hidden");
  document.querySelector(".input-area").classList.remove("clarification-active");
}

function clearChat() {
  document.getElementById("chat-messages").innerHTML = "";
  renderSteps([]);
  hideClarificationBanner();
  hideCodeApprovalBanner();
  setStatus("");
}

async function sendMessage(sourceInput = "main") {
  const mainInput = document.getElementById("message-input");
  const clarificationInput = document.getElementById("clarification-input");
  const input = sourceInput === "clarification" ? clarificationInput : mainInput;
  const sendBtn = document.getElementById("send-btn");
  if (!input || !sendBtn) return;
  let message = input.value.trim();
  if (sourceInput === "code_approval") {
    message = "approved";
  } else if (!message) return;

  const apiUrl = getApiUrl();
  const sessionId = getSessionId();
  const workflowEl = document.getElementById("workflow-id");
  const workflowId = workflowEl?.textContent ?? "—";
  const wfId = workflowId === "—" ? null : workflowId;
  const streamEl = document.getElementById("stream-mode");
  const streamMode = streamEl ? streamEl.checked : true;

  sendBtn.disabled = true;
  const clarificationSendBtn = document.getElementById("clarification-send-btn");
  if (clarificationSendBtn) clarificationSendBtn.disabled = true;
  input.value = "";
  const approvalIdToSend = sourceInput === "code_approval" ? pendingCodeApprovalId : null;
  if (sourceInput === "clarification") hideClarificationBanner();
  if (sourceInput === "code_approval") hideCodeApprovalBanner();
  addMessage("user", message);
  setStatus("Sending...");
  renderSteps([]);

  abortController = new AbortController();
  const payload = {
    message,
    session_id: sessionId || null,
    workflow_id: wfId || null,
  };
  if (approvalIdToSend) {
    payload.code_approval_id = approvalIdToSend;
  }

  try {
    showStopButton();
    if (streamMode) {
      await sendMessageStream(apiUrl, payload, sessionId, sendBtn);
    } else {
      await sendMessageSync(apiUrl, payload, sessionId, sendBtn);
    }
  } catch (err) {
    if (err.name === "AbortError") {
      removeLoadingMessage();
      addMessage("assistant", "Request cancelled.", true);
      setStatus("Cancelled");
    } else {
      removeLoadingMessage();
      addMessage("assistant", `Error: ${err.message}`, true);
      setStatus("Error");
    }
  } finally {
    sendBtn.disabled = false;
    const clarificationSendBtn = document.getElementById("clarification-send-btn");
    if (clarificationSendBtn) clarificationSendBtn.disabled = false;
    hideStopButton();
    abortController = null;
  }
}

async function sendMessageStream(apiUrl, payload, sessionId, sendBtn) {
  addLoadingMessage();
  let resultEl = null;
  const steps = [];

  const res = await fetch(`${apiUrl}/message/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: abortController?.signal,
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    removeLoadingMessage();
    addMessage("assistant", `Error: ${data.detail || res.statusText}`, true);
    setStatus("Error");
    return;
  }

  removeLoadingMessage();
  resultEl = addMessage("assistant", "", false);
  resultEl.textContent = "";

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (!data.trim()) continue;
        try {
          const event = JSON.parse(data);
          if (event.session_id) setSessionId(event.session_id);

          if (event.type === "step_start") {
            steps.push({ node_id: event.node_id, agent_type: event.agent_type, result: "", success: true, running: true });
            renderSteps(steps);
            setStatus(`Running ${event.node_id} (${event.agent_type})…`);
          } else if (event.type === "step_done") {
            const s = steps.find((x) => x.node_id === event.node_id);
            if (s) {
              s.result = event.result || event.error || "";
              s.success = event.success;
              s.running = false;
            } else {
              steps.push({ node_id: event.node_id, agent_type: event.agent_type, result: event.result || event.error || "", success: event.success, running: false });
            }
            renderSteps(steps);
          } else if (event.type === "node_done") {
            setIntent(event.intent);
            if (event.step_results && event.step_results.length > 0) {
              renderSteps(event.step_results);
            }
            setStatus(`Completed ${event.node}`);
          } else if (event.type === "done") {
            setWorkflowId(event.workflow_id);
            setIntent(event.intent);
            if (event.step_results) renderSteps(event.step_results);

            const delivery = event.delivery || {};
            if (delivery.needs_code_approval) {
              showCodeApprovalBanner(delivery.code || "", delivery.code_approval_id);
              resultEl.textContent = delivery.result || "Code execution requires your approval.";
              setStatus("Code approval needed");
            } else if (delivery.needs_clarification) {
              showClarificationBanner(delivery.question || delivery.result);
              resultEl.textContent = delivery.question || delivery.result;
              setStatus("Clarification needed");
            } else if (delivery.content_base64 && delivery.content_type) {
              const blob = base64ToBlob(delivery.content_base64, delivery.content_type);
              const fmt = delivery.output_format || "json";
              const ext = fmt === "xl" ? "xlsx" : fmt === "pdf" ? "pdf" : fmt === "audio" ? "mp3" : "bin";
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = delivery.filename || `result.${ext}`;
              a.click();
              URL.revokeObjectURL(url);
              resultEl.textContent = `Downloaded: ${delivery.filename || "result"}`;
              setStatus("File downloaded");
            } else {
              resultEl.textContent = delivery.result || event.final_result || "";
              setStatus("Done");
            }
          } else if (event.type === "error") {
            resultEl.textContent = `Error: ${event.error}`;
            resultEl.classList.add("error");
            setStatus("Error");
          }
        } catch (e) {
          console.warn("Parse SSE:", e);
        }
      }
    }
  }
}

async function sendMessageSync(apiUrl, payload, sessionId, sendBtn) {
  addLoadingMessage();

  const res = await fetch(`${apiUrl}/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: abortController?.signal,
  });

  removeLoadingMessage();

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    addMessage("assistant", `Error: ${data.detail || res.statusText}`, true);
    setStatus("Error");
    return;
  }

  setSessionId(data.session_id || sessionId);
  setWorkflowId(data.workflow_id || null);
  setIntent(data.intent || null);

  if (data.needs_code_approval) {
    showCodeApprovalBanner(data.code || "", data.code_approval_id);
    addMessage("assistant", data.result || "Code execution requires your approval.");
    setStatus("Code approval needed");
  } else if (data.needs_clarification) {
    showClarificationBanner(data.question || data.result);
    addMessage("assistant", data.question || data.result);
    setStatus("Clarification needed");
  } else if (data.content_base64 && data.content_type) {
    const blob = base64ToBlob(data.content_base64, data.content_type);
    const fmt = data.output_format || "json";
    const ext = fmt === "xl" ? "xlsx" : fmt === "pdf" ? "pdf" : fmt === "audio" ? "mp3" : "bin";
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = data.filename || `result.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
    addMessage("assistant", `Downloaded: ${data.filename || "result"}`);
    setStatus("File downloaded");
  } else {
    addMessage("assistant", data.result || "");
    setStatus("Done");
  }

  if (data.step_results && data.step_results.length > 0) {
    renderSteps(data.step_results);
  }
}

function base64ToBlob(base64, mimeType) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new Blob([bytes], { type: mimeType });
}

function init() {
  const apiUrl = localStorage.getItem(API_URL_KEY) || "http://localhost:8000";
  const apiUrlEl = document.getElementById("api-url");
  if (apiUrlEl) apiUrlEl.value = apiUrl;
  document.getElementById("api-url").addEventListener("change", (e) => {
    localStorage.setItem(API_URL_KEY, e.target.value);
  });

  setSessionId(getSessionId());
  setWorkflowId(null);

  document.getElementById("send-btn").addEventListener("click", sendMessage);
  document.getElementById("message-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  document.getElementById("copy-session").addEventListener("click", () => {
    const id = document.getElementById("session-id").textContent;
    if (id !== "—") navigator.clipboard.writeText(id);
  });
  document.getElementById("new-session").addEventListener("click", () => {
    localStorage.removeItem(SESSION_KEY);
    setSessionId(null);
    setWorkflowId(null);
    hideClarificationBanner();
    setStatus("New session");
  });
  document.getElementById("copy-workflow").addEventListener("click", () => {
    const id = document.getElementById("workflow-id").textContent;
    if (id !== "—") navigator.clipboard.writeText(id);
  });

  document.getElementById("clear-chat").addEventListener("click", clearChat);

  document.getElementById("stop-btn").addEventListener("click", () => {
    if (abortController) abortController.abort();
  });

  document.getElementById("clarification-send-btn").addEventListener("click", () => sendMessage("clarification"));
  document.getElementById("code-approval-btn").addEventListener("click", () => sendMessage("code_approval"));
  document.getElementById("clarification-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage("clarification");
    }
  });
}

init();
