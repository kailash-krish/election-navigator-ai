/**
 * Election Navigator AI — Frontend Script v2
 * Maps: proper dark-mode JSON style (no CSS filter hack)
 * Firebase: real-time live-count + query category logging
 * Translation: language change re-triggers last query
 * Accessibility: aria-disabled sync, focus management
 */

"use strict";

const ElectionNavigator = (function() {

/* ── Google Maps dark style ──────────────────────────────────────────── */
const DARK_MAP_STYLE = [
  { elementType: "geometry",        stylers: [{ color: "#0f1623" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#0f1623" }] },
  { elementType: "labels.text.fill",   stylers: [{ color: "#8d9db5" }] },
  { featureType: "road",  elementType: "geometry",       stylers: [{ color: "#1e293b" }] },
  { featureType: "road",  elementType: "geometry.stroke", stylers: [{ color: "#0f1623" }] },
  { featureType: "road",  elementType: "labels.text.fill", stylers: [{ color: "#9ca3af" }] },
  { featureType: "road.highway", elementType: "geometry",       stylers: [{ color: "#2563eb" }] },
  { featureType: "road.highway", elementType: "geometry.stroke", stylers: [{ color: "#1d4ed8" }] },
  { featureType: "water",         elementType: "geometry",       stylers: [{ color: "#0e1929" }] },
  { featureType: "water",         elementType: "labels.text.fill", stylers: [{ color: "#3d5a80" }] },
  { featureType: "poi",           stylers: [{ visibility: "off" }] },
  { featureType: "poi.park",      elementType: "geometry",       stylers: [{ color: "#0d2137" }, { visibility: "on" }] },
  { featureType: "transit",       stylers: [{ visibility: "off" }] },
  { featureType: "administrative.locality", elementType: "labels.text.fill", stylers: [{ color: "#7c8db5" }] },
  { featureType: "administrative.neighborhood", elementType: "labels.text.fill", stylers: [{ color: "#5a6a8a" }] },
];

/* ── State ─────────────────────────────────────────────────────────── */
const state = {
  context:   [],
  progress:  { eligible: false, docs: false, register: false, booth: false, timeline: false },
  language:  "en",
  map:       null,
  markers:   [],
  infoWindows: [],
  lastQuery: "",
};

/* ── DOM refs ────────────────────────────────────────────────────────── */
const $ = id => document.getElementById(id);
const feed      = $("chat-feed");
const welcome   = $("welcome-card");
const msgInput  = $("msg-input");
const sendBtn   = $("send-btn");
const charCount = $("char-count");
const langSelect = $("lang-select");

/* ── Init ────────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initInput();
  initSidebar();
  initBoothFinder();
  initTimeline();
  $("clear-btn").addEventListener("click", clearChat);
});

/* ── Tabs ────────────────────────────────────────────────────────────── */
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
  if (btn)   { btn.classList.add("active");   btn.setAttribute("aria-pressed", "true"); }
  if (tabId === "timeline") markProgress("timeline");
  // Announce tab change to screen readers
  panel?.setAttribute("tabindex", "-1");
  panel?.focus();
}

/* ── Input ────────────────────────────────────────────────────────────── */
function initInput() {
  msgInput.addEventListener("input", () => {
    const len = msgInput.value.length;
    charCount.textContent = `${len}/500`;
    const disabled = len === 0;
    sendBtn.disabled = disabled;
    sendBtn.setAttribute("aria-disabled", String(disabled));
    autoResize(msgInput);
  });

  msgInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });

  sendBtn.addEventListener("click", sendMessage);

  langSelect.addEventListener("change", () => {
    state.language = langSelect.value;
    // If there was a previous query, re-translate by re-sending it silently
    if (state.lastQuery) {
      showToast(`Language changed to ${langSelect.options[langSelect.selectedIndex].text}. Re-fetching last answer…`);
      // Short delay so toast shows first
      setTimeout(() => sendQuery(state.lastQuery), 600);
    } else {
      showToast(`Language: ${langSelect.options[langSelect.selectedIndex].text}`);
    }
  });

  document.querySelectorAll(".chip").forEach(el => {
    el.addEventListener("click", e => { e.stopPropagation(); sendQuery(el.dataset.q); });
  });
}

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

/* ── Sidebar ─────────────────────────────────────────────────────────── */
function initSidebar() {
  document.querySelectorAll(".quick-btn").forEach(btn => {
    btn.addEventListener("click", e => {
      e.stopPropagation();
      switchTab("assistant");
      sendQuery(btn.dataset.q);
    });
  });
}

/* ── Send / receive ───────────────────────────────────────────────────── */
function sendQuery(text, displayText) {
  if (!text) return;
  switchTab("assistant");
  if (displayText) sendMessage(text, displayText);
  else {
    msgInput.value = text;
    sendMessage();
  }
}

async function sendMessage(overrideText, overrideDisplayText) {
  const text = overrideText || msgInput.value.trim();
  if (!text) return;
  const displayText = overrideDisplayText || text;

  hideWelcome();
  appendUserMessage(displayText);
  state.lastQuery = text;

  if (!overrideText) {
    msgInput.value = "";
    charCount.textContent = "0/500";
    msgInput.style.height = "auto";
    sendBtn.disabled = true;
    sendBtn.setAttribute("aria-disabled", "true");
  }

  state.context.push({ role: "user", content: text });
  const typing = showTyping();

  try {
    const res = await fetch("/chat", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ message: text, context: state.context, language: state.language }),
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
    // Log to Firebase if available
    if (typeof window._fbLogQuery === "function") {
      window._fbLogQuery(_categorizeQuery(text));
    }

  } catch (err) {
    removeTyping(typing);
    appendError(err.message);
  }
}

function _categorizeQuery(text) {
  const t = text.toLowerCase();
  if (/eligib|qualify|am i/.test(t))             return "eligibility";
  if (/register|form.?6|voter.?id|nvsp/.test(t)) return "registration";
  if (/document|id.?proof|papers/.test(t))        return "documents";
  if (/timeline|phase|schedule/.test(t))          return "timeline";
  if (/evm|electronic.?voting/.test(t))           return "evm";
  if (/vvpat|paper.?trail/.test(t))               return "vvpat";
  if (/booth|polling.?center/.test(t))            return "booth_finder";
  if (/voting.?day|election.?day/.test(t))        return "voting_process";
  if (/first|new.?voter|beginner/.test(t))        return "first_time_voter";
  return "general";
}

/* ── Message rendering ────────────────────────────────────────────────── */
function hideWelcome() {
  if (welcome) welcome.style.display = "none";
}

function appendUserMessage(text) {
  const wrap   = el("div", "msg-wrap user");
  const bubble = el("div", "msg-bubble");
  bubble.setAttribute("role", "log");
  bubble.textContent = text;
  wrap.appendChild(bubble);
  feed.appendChild(wrap);
  scrollFeed();
}

function appendError(msg) {
  const wrap   = el("div", "msg-wrap ai");
  const bubble = el("div", "msg-bubble");
  bubble.setAttribute("role", "alert");
  bubble.innerHTML = `⚠️ <strong>Error:</strong> ${sanitize(msg)} <br><small>Please try again.</small>`;
  wrap.appendChild(bubble);
  feed.appendChild(wrap);
  scrollFeed();
}

function appendAIResponse(data) {
  const wrap = el("div", "msg-wrap ai");
  wrap.setAttribute("role", "log");
  const card = buildResponseCard(data);
  wrap.appendChild(card);

  if (data.follow_ups?.length) {
    const fu = el("div", "follow-ups");
    fu.setAttribute("aria-label", "Follow-up questions");
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

  // Move focus to new message for keyboard users
  card.setAttribute("tabindex", "-1");
  card.focus({ preventScroll: true });
}

function buildResponseCard(data) {
  const card   = el("div", "response-card");
  const header = el("div", "card-header");
  const h2 = el("h2"); h2.textContent = data.title || "Response";
  const p  = el("p");  p.textContent  = data.summary || "";
  header.appendChild(h2);
  if (data.summary) header.appendChild(p);
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
      const row  = el("div", "step-item");
      const num  = el("div", "step-num");  num.textContent = it.step;
      const ico  = el("div", "step-icon"); ico.textContent = it.icon || "•";
      ico.setAttribute("aria-hidden", "true");
      const txt  = el("div", "step-text");
      const h3   = el("h3"); h3.textContent = it.title;
      const desc = el("p");  desc.textContent = it.description;
      txt.append(h3, desc);
      row.append(num, ico, txt);
      wrap.appendChild(row);
    });
    return wrap;
  }

  if (type === "cards") {
    const grid = el("div", "cards-grid");
    items.forEach(it => {
      const c   = el("div", "info-card");
      if (it.tag) { const t = el("div", "tag"); t.textContent = it.tag; c.appendChild(t); }
      const ico = el("div", "info-card-icon"); ico.textContent = it.icon || "ℹ️";
      ico.setAttribute("aria-hidden", "true");
      const h3  = el("h3"); h3.textContent = it.title;
      const p   = el("p");  p.textContent  = it.description;
      c.append(ico, h3, p);
      grid.appendChild(c);
    });
    return grid;
  }

  if (type === "checklist") {
    const list = el("div", "checklist");
    list.setAttribute("role", "list");
    items.forEach(it => {
      const row = el("div", "check-item");
      row.setAttribute("role",        "checkbox");
      row.setAttribute("aria-checked","false");
      row.setAttribute("tabindex",    "0");

      const box = el("div", "check-box");
      box.setAttribute("aria-hidden", "true");
      const txt = el("div", "check-text");
      const h3  = el("h3"); h3.textContent = it.task;
      const p   = el("p");  p.textContent  = it.detail || "";
      txt.append(h3, p);
      if (it.required) {
        const req = el("span", "check-required"); req.textContent = "Required";
        txt.appendChild(req);
      }
      row.append(box, txt);

      const toggle = () => {
        row.classList.toggle("checked");
        row.setAttribute("aria-checked", row.classList.contains("checked"));
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
    grid.setAttribute("role", "list");
    items.forEach(it => {
      const btn = el("button", "option-btn");
      btn.setAttribute("role", "listitem");
      btn.setAttribute("aria-label", it.option);
      const ico = el("div", "opt-icon"); ico.textContent = "👉";
      ico.setAttribute("aria-hidden", "true");
      const txt = el("div");
      const h3  = el("h3"); h3.textContent = it.option;
      const p   = el("p");  p.textContent  = it.description || "";
      txt.append(h3, p);
      btn.append(ico, txt);
      btn.addEventListener("click", () => sendQuery(it.action || it.option, it.option));
      grid.appendChild(btn);
    });
    return grid;
  }

  if (type === "timeline") {
    const tl = el("div", "tl-chat");
    tl.setAttribute("role", "list");
    items.forEach(it => {
      const row  = el("div", `tl-chat-item ${it.status || "upcoming"}`);
      row.setAttribute("role", "listitem");
      const dot  = el("div", "tl-chat-dot"); dot.setAttribute("aria-hidden", "true");
      const body = el("div");
      const badge = el("span", `tl-status-badge ${it.status || "upcoming"}`);
      badge.textContent = it.status || "upcoming";
      const date = el("p", "tl-chat-date"); date.textContent = it.date;
      const ev   = el("p", "tl-chat-event"); ev.textContent = it.event;
      const desc = el("p", "tl-chat-desc"); desc.textContent = it.description;
      body.append(badge, date, ev, desc);
      row.append(dot, body);
      tl.appendChild(row);
    });
    return tl;
  }

  // Fallback plain text
  const div = el("div"); div.textContent = items.map(i => JSON.stringify(i)).join("\n");
  return div;
}

/* ── Typing indicator ─────────────────────────────────────────────────── */
function showTyping() {
  const wrap = el("div", "msg-wrap ai");
  wrap.id    = "typing-wrap";
  const t    = el("div", "typing");
  t.setAttribute("aria-label", "AI is thinking");
  t.setAttribute("role", "status");
  t.innerHTML = "<span></span><span></span><span></span>";
  wrap.appendChild(t);
  feed.appendChild(wrap);
  scrollFeed();
  return wrap;
}
function removeTyping(wrap) { if (wrap?.parentNode) wrap.remove(); }

/* ── Progress tracker ─────────────────────────────────────────────────── */
function detectProgress(text) {
  const t = text.toLowerCase();
  if (/eligib/.test(t))                           markProgress("eligible");
  if (/document|id.?proof|papers/.test(t))        markProgress("docs");
  if (/register|form.?6|voter.?id/.test(t))       markProgress("register");
  if (/booth|find.*booth|polling/.test(t))        markProgress("booth");
  if (/timeline|phases|schedule/.test(t))         markProgress("timeline");
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
  const wrap  = $("progress-bar-wrap");
  if (bar)  bar.style.width = pct + "%";
  if (wrap) { wrap.setAttribute("aria-valuenow", pct); }

  if (done === total) showToast("🎉 You're fully vote-ready!");
}

/* ── Booth Finder ─────────────────────────────────────────────────────── */
function initBoothFinder() {
  $("pincode-btn").addEventListener("click", () => {
    const pin = $("pincode-input").value.trim();
    const errEl = $("pincode-error");
    if (!pin || !/^\d{6}$/.test(pin)) {
      errEl.textContent = "Please enter a valid 6-digit pincode.";
      errEl.hidden = false;
      $("pincode-input").setAttribute("aria-invalid", "true");
      return;
    }
    errEl.hidden = true;
    $("pincode-input").setAttribute("aria-invalid", "false");
    fetchBooths({ pincode: pin });
  });

  $("pincode-input").addEventListener("keydown", e => { if (e.key === "Enter") $("pincode-btn").click(); });

  $("location-btn").addEventListener("click", () => {
    if (!navigator.geolocation) { showToast("Geolocation not supported by your browser."); return; }
    showToast("📡 Getting your location…");
    navigator.geolocation.getCurrentPosition(
      pos => fetchBooths({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      err => {
        const msgs = { 1: "Location access denied. Try pincode.", 2: "Location unavailable.", 3: "Timed out." };
        showToast(msgs[err.code] || "Location error.");
      },
      { timeout: 10000, maximumAge: 60000 }
    );
  });
}

async function fetchBooths(params) {
  const results = $("booth-results");
  results.innerHTML = `<div class="typing" role="status" aria-label="Searching nearby voter registration offices"><span></span><span></span><span></span></div>`;
  markProgress("booth");

  try {
    const res  = await fetch("/polling-booth", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(params),
    });
    const data = await res.json();

    if (data.error) {
      results.innerHTML = `<p role="alert" style="color:var(--red)">${sanitize(data.error)}</p>`;
      return;
    }
    if (!data.results?.length) {
      results.innerHTML = `<p role="status">No voter registration offices found nearby. Try a different pincode or expand your area.</p>`;
      return;
    }

    results.innerHTML = "";
    data.results.forEach(place => {
      const card = el("div", "booth-card");
      card.setAttribute("role",     "article");
      card.setAttribute("tabindex", "0");
      card.setAttribute("aria-label", `${place.name}, ${place.distance_km}km away — voter registration office`);

      const h3 = el("h3"); h3.textContent = place.name;
      const p  = el("p");  p.textContent  = place.address || "Address not available";
      const meta = el("div", "booth-meta");

      if (place.rating) {
        const r = el("span", "booth-badge");
        r.textContent = `⭐ ${place.rating}${place.total_ratings ? ` (${place.total_ratings})` : ""}`;
        meta.appendChild(r);
      }
      if (place.open_now !== undefined) {
        const o = el("span", place.open_now ? "booth-badge" : "booth-badge closed");
        o.textContent = place.open_now ? "Open Now" : "Closed";
        meta.appendChild(o);
      }
      if (place.distance_km) {
        const d = el("span", "booth-distance");
        d.textContent = `${place.distance_km} km away`;
        meta.appendChild(d);
      }

      const actions = el("div", "booth-actions");
      if (place.directions_url) {
        const dir = el("a", "booth-action-btn primary");
        dir.href = place.directions_url;
        dir.target = "_blank";
        dir.rel = "noopener noreferrer";
        dir.setAttribute("aria-label", `Get directions to ${place.name} (opens in Google Maps)`);
        dir.innerHTML = "🗺️ Directions";
        actions.appendChild(dir);
      }
      const viewBtn = el("button", "booth-action-btn");
      viewBtn.textContent = "📍 Show on map";
      viewBtn.setAttribute("aria-label", `Show ${place.name} on map`);
      viewBtn.addEventListener("click", () => panMapTo(place.lat, place.lng, place.name));
      actions.appendChild(viewBtn);

      card.append(h3, p, meta, actions);
      card.addEventListener("click", () => panMapTo(place.lat, place.lng, place.name));
      card.addEventListener("keydown", e => { if (e.key === "Enter") panMapTo(place.lat, place.lng, place.name); });
      results.appendChild(card);
    });

    if (data.lat && data.lng) renderMap(data.lat, data.lng, data.results);
  } catch (err) {
    results.innerHTML = `<p role="alert" style="color:var(--red)">Error: ${sanitize(err.message)}</p>`;
  }
}

/* ── Google Maps ───────────────────────────────────────────────────────── */
window.initMap = function () { /* SDK loaded — nothing to init until search */ };

function renderMap(lat, lng, places) {
  if (typeof google === "undefined" || !google.maps) {
    $("map-placeholder").style.display = "flex";
    return;
  }
  $("map-placeholder").style.display = "none";
  const center = { lat, lng };

  // Close existing info windows
  state.infoWindows.forEach(w => w.close());
  state.infoWindows = [];

  if (!state.map) {
    state.map = new google.maps.Map($("map"), {
      zoom:           13,
      center,
      mapTypeControl: false,
      fullscreenControl: true,
      streetViewControl: false,
      styles:         DARK_MAP_STYLE,
    });
  } else {
    state.map.setCenter(center);
    state.map.setZoom(13);
    state.markers.forEach(m => m.setMap(null));
    state.markers = [];
  }

  // User location marker (pulsing blue dot)
  const userMarker = new google.maps.Marker({
    position: center,
    map:      state.map,
    title:    "Your location",
    icon: {
      path:         google.maps.SymbolPath.CIRCLE,
      scale:        10,
      fillColor:    "#4f7aff",
      fillOpacity:  1,
      strokeColor:  "#fff",
      strokeWeight: 3,
    },
    zIndex: 999,
  });
  state.markers.push(userMarker);

  // Place markers
  places.forEach((p, i) => {
    const marker = new google.maps.Marker({
      position: { lat: p.lat, lng: p.lng },
      map:      state.map,
      title:    p.name,
      label: {
        text:      String(i + 1),
        color:     "#fff",
        fontSize:  "12px",
        fontWeight: "bold",
      },
      icon: {
        path:         google.maps.SymbolPath.BACKWARD_CLOSED_ARROW,
        scale:        7,
        fillColor:    "#7c3aed",
        fillOpacity:  1,
        strokeColor:  "#fff",
        strokeWeight: 2,
      },
    });

    const contentStr = `
      <div style="font-family:sans-serif;max-width:220px;padding:4px">
        <strong style="font-size:14px">${sanitize(p.name)}</strong><br>
        <span style="color:#555;font-size:12px">${sanitize(p.address || "")}</span><br>
        ${p.distance_km ? `<span style="color:#7c3aed;font-size:12px">📍 ${p.distance_km} km away</span><br>` : ""}
        ${p.directions_url ? `<a href="${p.directions_url}" target="_blank" rel="noopener" style="color:#2563eb;font-size:12px">Get Directions ↗</a>` : ""}
      </div>`;
    const infoWin = new google.maps.InfoWindow({ content: contentStr });
    state.infoWindows.push(infoWin);

    marker.addListener("click", () => {
      state.infoWindows.forEach(w => w.close());
      infoWin.open(state.map, marker);
    });
    state.markers.push(marker);
  });
}

function panMapTo(lat, lng, name) {
  if (!state.map) return;
  state.map.panTo({ lat: parseFloat(lat), lng: parseFloat(lng) });
  state.map.setZoom(16);
}

/* ── Timeline tab ──────────────────────────────────────────────────────── */
function initTimeline() {
  document.querySelector('[data-tab="timeline"]')
    .addEventListener("click", () => markProgress("timeline"));
}

/* ── Toast ─────────────────────────────────────────────────────────────── */
let toastTimer;
function showToast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 3200);
}

/* ── Utilities ─────────────────────────────────────────────────────────── */
function clearChat() {
  feed.innerHTML    = "";
  state.context     = [];
  state.lastQuery   = "";
  if (welcome) welcome.style.display = "";
  showToast("Chat cleared");
  msgInput.focus();
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
    .replace(/&/g,  "&amp;")
    .replace(/</g,  "&lt;")
    .replace(/>/g,  "&gt;")
    .replace(/"/g,  "&quot;")
    .replace(/'/g,  "&#x27;");
}

  return {
    _categorizeQuery,
    getState: () => state,
    initMap: window.initMap
  };
})();

if (typeof module !== "undefined" && module.exports) {
  module.exports = ElectionNavigator;
}
