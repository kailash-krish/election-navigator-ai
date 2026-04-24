/**
 * Election Navigator AI — Frontend Logic
 * Handles chat, structured responses, and interactive UI.
 */

const chatArea = document.getElementById("chatArea");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const sidebarToggle = document.getElementById("sidebarToggle");
const sidebar = document.querySelector(".sidebar");

let conversationContext = [];

// ── Init ──────────────────────────────────────────────────────────────
function init() {
    renderWelcome();

    sendBtn.addEventListener("click", handleSend);
    userInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
    });
    userInput.addEventListener("input", autoResize);

    sidebarToggle.addEventListener("click", () => sidebar.classList.toggle("open"));
    document.addEventListener("click", (e) => {
        if (sidebar.classList.contains("open") && !sidebar.contains(e.target) && e.target !== sidebarToggle) {
            sidebar.classList.remove("open");
        }
    });

    document.querySelectorAll(".nav-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            sidebar.classList.remove("open");
            sendQuery(btn.dataset.query);
        });
    });
}

// ── Welcome Card ──────────────────────────────────────────────────────
function renderWelcome() {
    const starters = [
        "I'm a first-time voter 🌟",
        "How do I register? 📋",
        "What happens on voting day? 🗳️",
        "What IDs do I need? 🪪",
    ];
    const el = document.createElement("div");
    el.className = "welcome-card";
    el.innerHTML = `
    <div class="welcome-emoji">🗳️</div>
    <h1>Election Navigator AI</h1>
    <p>Your personal guide to India's democratic process.<br>Ask me anything about voting, registration, or elections.</p>
    <div class="welcome-chips">
      ${starters.map((s) => `<button class="chip">${s}</button>`).join("")}
    </div>
  `;
    el.querySelectorAll(".chip").forEach((chip) => {
        chip.addEventListener("click", () => sendQuery(chip.textContent.trim()));
    });
    chatArea.appendChild(el);
}

// ── Send Handler ──────────────────────────────────────────────────────
async function handleSend() {
    const text = userInput.value.trim();
    if (!text) return;
    userInput.value = "";
    autoResize();
    await sendQuery(text);
}

async function sendQuery(text, displayText = null) {
    appendUserMessage(displayText || text);
    conversationContext.push({ role: "user", content: text });

    const typingId = showTyping();
    sendBtn.disabled = true;

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text, context: conversationContext }),
        });

        removeTyping(typingId);

        if (!res.ok) {
            const err = await res.json();
            appendError(err.error || "Something went wrong.");
            return;
        }

        const data = await res.json();
        renderStructuredResponse(data);
        conversationContext.push({ role: "assistant", content: JSON.stringify(data) });
        // Trim context to avoid bloat
        if (conversationContext.length > 12) conversationContext = conversationContext.slice(-12);
    } catch (e) {
        removeTyping(typingId);
        appendError("Network error. Please check your connection.");
    } finally {
        sendBtn.disabled = false;
        userInput.focus();
        scrollBottom();
    }
}

// ── Message Renderers ─────────────────────────────────────────────────
function appendUserMessage(text) {
    const row = document.createElement("div");
    row.className = "msg-row user";
    row.innerHTML = `
    <div class="avatar user">👤</div>
    <div class="bubble user">${escapeHtml(text)}</div>
  `;
    chatArea.appendChild(row);
    scrollBottom();
}

function appendError(msg) {
    const row = document.createElement("div");
    row.className = "msg-row";
    row.innerHTML = `
    <div class="avatar ai">🗳️</div>
    <div class="bubble ai" style="border-color: rgba(239,68,68,0.3); color: #fca5a5;">${escapeHtml(msg)}</div>
  `;
    chatArea.appendChild(row);
}

function renderStructuredResponse(data) {
    const wrap = document.createElement("div");
    wrap.className = "response-wrap";

    const aiRow = document.createElement("div");
    aiRow.className = "msg-row";
    aiRow.innerHTML = `<div class="avatar ai">🗳️</div>`;

    const bubble = document.createElement("div");
    bubble.className = "bubble ai";
    bubble.style.maxWidth = "100%";
    bubble.style.flex = "1";

    bubble.innerHTML = buildResponseHeader(data);

    switch (data.type) {
        case "steps": bubble.innerHTML += buildSteps(data.items); break;
        case "cards": bubble.innerHTML += buildCards(data.items); break;
        case "checklist": bubble.innerHTML += buildChecklist(data.items); break;
        case "info": bubble.innerHTML += buildInfo(data.items); break;
        case "question": bubble.innerHTML += buildQuestion(data.items); break;
        default: bubble.innerHTML += `<p>${escapeHtml(data.summary || "")}</p>`;
    }

    if (data.follow_ups?.length) {
        bubble.innerHTML += buildFollowUps(data.follow_ups);
    }

    aiRow.appendChild(bubble);
    aiRow.querySelectorAll(".option-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            const titleEl = btn.querySelector(".option-title");
            sendQuery(btn.dataset.action, titleEl ? titleEl.textContent : btn.dataset.action);
        });
    });
    aiRow.querySelectorAll(".followup-btn").forEach((btn) => {
        btn.addEventListener("click", () => sendQuery(btn.dataset.query));
    });

    chatArea.appendChild(aiRow);
    scrollBottom();
}

// ── HTML Builders ─────────────────────────────────────────────────────
function buildResponseHeader(data) {
    if (!data.title && !data.summary) return "";
    return `
    <div class="response-header">
      ${data.title ? `<div class="response-title">${escapeHtml(data.title)}</div>` : ""}
      ${data.summary ? `<div class="response-summary">${escapeHtml(data.summary)}</div>` : ""}
    </div>
  `;
}

function buildSteps(items = []) {
    return `<div class="steps-list">${items.map((s) => `
    <div class="step-card">
      <div class="step-num">${s.step || "•"}</div>
      <div>
        <div class="step-title">${s.icon ? s.icon + " " : ""}${escapeHtml(s.title || "")}</div>
        <div class="step-desc">${escapeHtml(s.description || "")}</div>
      </div>
    </div>
  `).join("")}</div>`;
}

function buildCards(items = []) {
    return `<div class="cards-grid">${items.map((c) => `
    <div class="info-card">
      <div class="card-icon">${c.icon || "📌"}</div>
      ${c.tag ? `<div class="card-tag">${escapeHtml(c.tag)}</div>` : ""}
      <div class="card-title">${escapeHtml(c.title || "")}</div>
      <div class="card-desc">${escapeHtml(c.description || "")}</div>
    </div>
  `).join("")}</div>`;
}

function buildChecklist(items = []) {
    return `<div class="check-list">${items.map((c) => `
    <div class="check-item">
      <div class="check-box ${c.required ? "required" : "optional"}">${c.required ? "✓" : "○"}</div>
      <div>
        <div class="check-task">${escapeHtml(c.task || "")}</div>
        <div class="check-detail">${escapeHtml(c.detail || "")}</div>
        ${c.required ? `<span class="req-label">REQUIRED</span>` : ""}
      </div>
    </div>
  `).join("")}</div>`;
}

function buildInfo(items = []) {
    return `<div class="info-table">${items.map((r) => `
    <div class="info-row">
      <span class="info-label">${escapeHtml(r.label || "")}</span>
      <span class="info-value">${escapeHtml(r.value || "")}</span>
    </div>
  `).join("")}</div>`;
}

function buildQuestion(items = []) {
    return `<div class="option-list">${items.map((o) => `
    <button class="option-btn" data-action="${escapeAttr(o.action || o.option)}">
      <div>
        <span class="option-title">${escapeHtml(o.option || "")}</span>
        ${o.description ? `<span class="option-desc">${escapeHtml(o.description)}</span>` : ""}
      </div>
      <span class="option-arrow">→</span>
    </button>
  `).join("")}</div>`;
}

function buildFollowUps(items = []) {
    return `<div class="followups">${items.map((f) => `
    <button class="followup-btn" data-query="${escapeAttr(f)}">${escapeHtml(f)}</button>
  `).join("")}</div>`;
}

// ── Typing Indicator ──────────────────────────────────────────────────
let typingCounter = 0;
function showTyping() {
    const id = "typing-" + (++typingCounter);
    const row = document.createElement("div");
    row.className = "typing-row"; row.id = id;
    row.innerHTML = `<div class="avatar ai">🗳️</div><div class="typing-bubble"><span></span><span></span><span></span></div>`;
    chatArea.appendChild(row);
    scrollBottom();
    return id;
}
function removeTyping(id) {
    document.getElementById(id)?.remove();
}

// ── Utilities ─────────────────────────────────────────────────────────
function scrollBottom() {
    requestAnimationFrame(() => { chatArea.scrollTop = chatArea.scrollHeight; });
}

function autoResize() {
    userInput.style.height = "auto";
    userInput.style.height = Math.min(userInput.scrollHeight, 120) + "px";
}

function escapeHtml(str) {
    if (typeof str !== "string") return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function escapeAttr(str) {
    if (typeof str !== "string") return "";
    return str.replace(/"/g, "&quot;");
}

// ── Start ─────────────────────────────────────────────────────────────
init();