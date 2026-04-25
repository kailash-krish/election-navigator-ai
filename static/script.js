/**
 * Election Navigator AI — Frontend Script
 * Handles: Chat, Structured Rendering, Maps, Tab Navigation, Progress Tracking
 */

"use strict";

// ── State ─────────────────────────────────────────────────────────────────
const state = {
  context:  [],
  progress: { eligible: false, docs: false, register: false, booth: false, timeline: false },
  language: "en",
  map:      null,
  markers:  [],
};

// ── DOM refs ──────────────────────────────────────────────────────────────
const $  = id => document.getElementById(id);
const feed       = $("chat-feed");
const welcome    = $("welcome-card");
const msgInput   = $("msg-input");
const sendBtn    = $("send-btn");
const charCount  = $("char-count");
const langSelect = $("lang-select");

// ── Init ──────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initInput();
  initSidebar();
  initBoothFinder();
  initTimeline();
  $("clear-btn").addEventListener("click", clearChat);
});

// ── Tabs ──────────────────────────────────────────────────────────────────
function initTabs() {
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
}

function switchTab(tabId) {
  document.querySelectorAll(".tab-panel").forEach(p => {
    p.classList.remove("active");
    p.hidden = true;
  });
  document.querySelectorAll(".nav-btn").forEach(b => {
    b.classList.remove("active");
    b.setAttribute("aria-pressed", "false");
  });

  const panel = $(`tab-${tabId}`);
  const btn   = document.querySelector(`[data-tab="${tabId}"]`);
  if (panel) { panel.classList.add("active"); panel.hidden = false; }
  if (btn)   { btn.classList.add("active"); btn.setAttribute("aria-pressed", "true"); }

  if (tabId === "timeline") markProgress("timeline");
}

// ── Input handling ─────────────────────────────────────────────────────────
function initInput() {
  msgInput.addEventListener("input", () => {
    const len = msgInput.value.length;
    charCount.textContent = `${len}/500`;
    sendBtn.disabled = len === 0;
    autoResize(msgInput);
  });

  msgInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });

  sendBtn.addEventListener("click", sendMessage);
  langSelect.addEventListener("change", () => { state.language = langSelect.value; });

  // Welcome chips & sidebar quick btns
  document.querySelectorAll(".chip, .quick-btn, [data-q]").forEach(el => {
    el.addEventListener("click", () => sendQuery(el.dataset.q));
  });
}

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

// ── Sidebar ───────────────────────────────────────────────────────────────
function initSidebar() {
  document.querySelectorAll(".quick-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      switchTab("assistant");
      sendQuery(btn.dataset.q);
    });
  });
}

// ── Send / receive ─────────────────────────────────────────────────────────
function sendQuery(text) {
  if (!text) return;
  switchTab("assistant");
  msgInput.value = text;
  sendMessage();
}

async function sendMessage() {
  const text = msgInput.value.trim();
  if (!text) return;

  hideWelcome();
  appendUserMessage(text);
  msgInput.value = "";
  charCount.textContent = "0/500";
  msgInput.style.height = "auto";
  sendBtn.disabled = true;

  state.context.push({ role: "user", content: text });
  const typing = showTyping();

  try {
    const res  = await fetch("/chat", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, context: state.context, language: state.language }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `Server error ${res.status}`);
    }

    const data = await res.json();
    removeTyping(typing);
    appendAIResponse(data);

    state.context.push({ role: "assistant", content: JSON.stringify(data) });
    if (state.context.length > 20) state.context = state.context.slice(-20);

    detectProgress(text, data);

  } catch (err) {
    removeTyping(typing);
    appendError(err.message);
  }
}

// ── Message rendering ──────────────────────────────────────────────────────
function hideWelcome() {
  if (welcome) { welcome.style.display = "none"; }
}

function appendUserMessage(text) {
  const wrap = el("div", "msg-wrap user");
  const bubble = el("div", "msg-bubble");
  bubble.textContent = text;
  wrap.appendChild(bubble);
  feed.appendChild(wrap);
  scrollFeed();
}

function appendError(msg) {
  const wrap = el("div", "msg-wrap ai");
  const bubble = el("div", "msg-bubble");
  bubble.innerHTML = `⚠️ <strong>Error:</strong> ${sanitize(msg)}`;
  wrap.appendChild(bubble);
  feed.appendChild(wrap);
  scrollFeed();
}

function appendAIResponse(data) {
  const wrap = el("div", "msg-wrap ai");
  const card = buildResponseCard(data);
  wrap.appendChild(card);

  if (data.follow_ups?.length) {
    const fu = el("div", "follow-ups");
    data.follow_ups.forEach(text => {
      const btn = el("button", "follow-up-btn");
      btn.textContent = text;
      btn.setAttribute("aria-label", `Ask: ${text}`);
      btn.addEventListener("click", () => sendQuery(text));
      fu.appendChild(btn);
    });
    wrap.appendChild(fu);
  }

  feed.appendChild(wrap);
  scrollFeed();
}

function buildResponseCard(data) {
  const card   = el("div", "response-card");
  const header = el("div", "card-header");
  const h2     = el("h2");  h2.textContent = data.title || "Response";
  const p      = el("p");   p.textContent  = data.summary || "";
  header.appendChild(h2);
  header.appendChild(p);

  if (data.tip) {
    const tip = el("p", "card-tip");
    tip.textContent = "💡 " + data.tip;
    header.appendChild(tip);
  }

  card.appendChild(header);

  const body = el("div", "card-body");
  body.appendChild(renderItems(data));
  card.appendChild(body);
  return card;
}

function renderItems(data) {
  const { type, items = [] } = data;

  if (type === "steps") {
    const wrap = el("div");
    items.forEach(it => {
      const row = el("div", "step-item");
      const num = el("div", "step-num"); num.textContent = it.step;
      const ico = el("div", "step-icon"); ico.textContent = it.icon || "•";
      const txt = el("div", "step-text");
      const h3  = el("h3"); h3.textContent = it.title;
      const p   = el("p");  p.textContent  = it.description;
      txt.append(h3, p);
      row.append(num, ico, txt);
      wrap.appendChild(row);
    });
    return wrap;
  }

  if (type === "cards") {
    const grid = el("div", "cards-grid");
    items.forEach(it => {
      const c = el("div", "info-card");
      if (it.tag) { const t = el("div", "tag"); t.textContent = it.tag; c.appendChild(t); }
      const ico = el("div", "info-card-icon"); ico.textContent = it.icon || "ℹ️";
      const h3  = el("h3"); h3.textContent = it.title;
      const p   = el("p");  p.textContent  = it.description;
      c.append(ico, h3, p);
      grid.appendChild(c);
    });
    return grid;
  }

  if (type === "checklist") {
    const list = el("div", "checklist");
    items.forEach(it => {
      const row = el("div", "check-item");
      row.setAttribute("role", "checkbox");
      row.setAttribute("aria-checked", "false");
      row.setAttribute("tabindex", "0");

      const box  = el("div", "check-box");
      const txt  = el("div", "check-text");
      const h3   = el("h3"); h3.textContent = it.task;
      const p    = el("p");  p.textContent  = it.detail || "";
      txt.append(h3, p);

      if (it.required) {
        const req = el("span", "check-required"); req.textContent = "Required";
        txt.appendChild(req);
      }

      row.append(box, txt);

      const toggle = () => {
        row.classList.toggle("checked");
        const checked = row.classList.contains("checked");
        row.setAttribute("aria-checked", checked);
      };
      row.addEventListener("click", toggle);
      row.addEventListener("keydown", e => { if (e.key === " " || e.key === "Enter") { e.preventDefault(); toggle(); } });

      list.appendChild(row);
    });
    return list;
  }

  if (type === "info") {
    const pairs = el("div", "info-pairs");
    items.forEach(it => {
      const row = el("div", "info-pair");
      const lbl = el("span", "label"); lbl.textContent = it.label;
      const val = el("span", "value"); val.textContent = it.value;
      row.append(lbl, val);
      pairs.appendChild(row);
    });
    return pairs;
  }

  if (type === "question") {
    const grid = el("div", "options-grid");
    items.forEach(it => {
      const btn = el("button", "option-btn");
      const ico = el("div", "opt-icon"); ico.textContent = "👉";
      const txt = el("div");
      const h3  = el("h3"); h3.textContent = it.option;
      const p   = el("p");  p.textContent  = it.description || "";
      txt.append(h3, p);
      btn.append(ico, txt);
      btn.addEventListener("click", () => sendQuery(it.action || it.option));
      grid.appendChild(btn);
    });
    return grid;
  }

  if (type === "timeline") {
    const tl = el("div", "tl-chat");
    items.forEach(it => {
      const row  = el("div", `tl-chat-item ${it.status || "upcoming"}`);
      const dot  = el("div", "tl-chat-dot"); dot.setAttribute("aria-hidden", "true");
      const body = el("div");
      const badge = el("span", `tl-status-badge ${it.status || "upcoming"}`);
      badge.textContent = it.status || "upcoming";
      const date = el("p", "tl-chat-date"); date.textContent = it.date;
      const ev   = el("p", "tl-chat-event"); ev.textContent = it.event;
      const desc = el("p", "tl-chat-desc");  desc.textContent = it.description;
      body.append(badge, date, ev, desc);
      row.append(dot, body);
      tl.appendChild(row);
    });
    return tl;
  }

  // Fallback
  const div = el("div"); div.textContent = JSON.stringify(items);
  return div;
}

// ── Typing indicator ──────────────────────────────────────────────────────
function showTyping() {
  const wrap = el("div", "msg-wrap ai");
  wrap.id    = "typing-wrap";
  const t    = el("div", "typing");
  t.setAttribute("aria-label", "AI is thinking");
  t.innerHTML = "<span></span><span></span><span></span>";
  wrap.appendChild(t);
  feed.appendChild(wrap);
  scrollFeed();
  return wrap;
}
function removeTyping(wrap) { if (wrap?.parentNode) wrap.remove(); }

// ── Progress tracker ──────────────────────────────────────────────────────
function detectProgress(text, data) {
  const t = text.toLowerCase();
  if (/eligib/.test(t))                     markProgress("eligible");
  if (/document|id proof|papers/.test(t))   markProgress("docs");
  if (/register|form 6|voter id/.test(t))   markProgress("register");
  if (/booth|find.*booth|polling/.test(t))  markProgress("booth");
  if (/timeline|phases|schedule/.test(t))   markProgress("timeline");
}

function markProgress(key) {
  if (state.progress[key]) return;
  state.progress[key] = true;

  const item = document.querySelector(`.p-item[data-key="${key}"]`);
  if (item) item.classList.add("done");

  const done  = Object.values(state.progress).filter(Boolean).length;
  const total = Object.keys(state.progress).length;
  const pct   = Math.round((done / total) * 100);
  const bar   = $("progress-bar");
  if (bar) {
    bar.style.width = pct + "%";
    bar.setAttribute("aria-valuenow", pct);
  }

  if (done === total) showToast("🎉 You're fully vote-ready!");
}

// ── Booth Finder ──────────────────────────────────────────────────────────
function initBoothFinder() {
  $("pincode-btn").addEventListener("click", () => {
    const pin = $("pincode-input").value.trim();
    if (!pin || !/^\d{6}$/.test(pin)) {
      showToast("Please enter a valid 6-digit pincode");
      return;
    }
    fetchBooths({ pincode: pin });
  });

  $("pincode-input").addEventListener("keydown", e => {
    if (e.key === "Enter") $("pincode-btn").click();
  });

  $("location-btn").addEventListener("click", () => {
    if (!navigator.geolocation) { showToast("Geolocation not supported"); return; }
    showToast("📡 Getting your location…");
    navigator.geolocation.getCurrentPosition(
      pos => fetchBooths({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      ()  => showToast("Location access denied. Try pincode instead.")
    );
  });
}

async function fetchBooths(params) {
  const results = $("booth-results");
  results.innerHTML = `<div class="typing"><span></span><span></span><span></span></div>`;
  markProgress("booth");

  try {
    const res  = await fetch("/polling-booth", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(params),
    });
    const data = await res.json();

    if (data.error) { results.innerHTML = `<p style="color:var(--red-500)">${sanitize(data.error)}</p>`; return; }

    if (!data.results?.length) {
      results.innerHTML = "<p>No results found for this location.</p>";
      return;
    }

    results.innerHTML = "";
    data.results.forEach(place => {
      const card = el("div", "booth-card");
      card.setAttribute("role", "article");
      card.setAttribute("tabindex", "0");
      card.setAttribute("aria-label", place.name);

      const h3 = el("h3"); h3.textContent = place.name;
      const p  = el("p");  p.textContent  = place.address || "Address not available";
      const meta = el("div", "booth-meta");

      if (place.rating) {
        const r = el("span", "booth-badge"); r.textContent = `⭐ ${place.rating}`;
        meta.appendChild(r);
      }
      if (place.open_now !== undefined) {
        const o = el("span", place.open_now ? "booth-badge" : "booth-badge closed");
        o.textContent = place.open_now ? "Open Now" : "Closed";
        meta.appendChild(o);
      }

      card.append(h3, p, meta);
      card.addEventListener("click", () => panMapTo(place.lat, place.lng, place.name));
      card.addEventListener("keydown", e => { if (e.key === "Enter") panMapTo(place.lat, place.lng, place.name); });
      results.appendChild(card);
    });

    if (data.lat && data.lng) renderMap(data.lat, data.lng, data.results);

  } catch (err) {
    results.innerHTML = `<p style="color:var(--red-500)">Error: ${sanitize(err.message)}</p>`;
  }
}

// ── Google Maps ─────────────────────────────────────────────────────────
window.initMap = function () {
  // Called by Maps SDK after load
};

function renderMap(lat, lng, places) {
  if (typeof google === "undefined" || !google.maps) {
    $("map-placeholder").style.display = "flex";
    return;
  }

  $("map-placeholder").style.display = "none";
  const center = { lat, lng };

  if (!state.map) {
    state.map = new google.maps.Map($("map"), { zoom: 13, center, mapTypeControl: false });
  } else {
    state.map.setCenter(center);
    state.map.setZoom(13);
    state.markers.forEach(m => m.setMap(null));
    state.markers = [];
  }

  // Center marker
  new google.maps.Marker({ position: center, map: state.map, title: "Your location",
    icon: { path: google.maps.SymbolPath.CIRCLE, scale: 8, fillColor: "#1a56db", fillOpacity: 1, strokeColor: "#fff", strokeWeight: 2 }
  });

  // Place markers
  places.forEach(p => {
    const m = new google.maps.Marker({
      position: { lat: p.lat, lng: p.lng },
      map: state.map, title: p.name,
    });
    const info = new google.maps.InfoWindow({
      content: `<strong>${p.name}</strong><br>${p.address || ""}`,
    });
    m.addListener("click", () => info.open(state.map, m));
    state.markers.push(m);
  });
}

function panMapTo(lat, lng, name) {
  if (!state.map) return;
  state.map.panTo({ lat, lng });
  state.map.setZoom(16);
}

// ── Timeline tab ──────────────────────────────────────────────────────────
function initTimeline() {
  // Progress tracking when tab opened
  document.querySelector('[data-tab="timeline"]').addEventListener("click", () => markProgress("timeline"));
}

// ── Toast ─────────────────────────────────────────────────────────────────
let toastTimer;
function showToast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 3200);
}

// ── Utilities ─────────────────────────────────────────────────────────────
function clearChat() {
  feed.innerHTML = "";
  state.context  = [];
  if (welcome) welcome.style.display = "";
  showToast("Chat cleared");
}

function scrollFeed() {
  requestAnimationFrame(() => { feed.scrollTop = feed.scrollHeight; });
}

function el(tag, cls) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  return e;
}

function sanitize(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
