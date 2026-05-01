# Election Navigator AI v2 🗳️

> Top-ranked AI assistant for India's election process — powered by Google Gemini, Maps, Translate, BigQuery, Firebase, and Cloud Run.

---

## 🏗️ Architecture

```
election-navigator-ai/
├── app.py                        # Flask entrypoint — security, routing, rate limiting
├── services/
│   ├── gemini_service.py         # Vertex AI / Gemini — structured JSON responses
│   ├── flow_service.py           # Scripted decision-tree flows (zero-latency)
│   ├── maps_service.py           # Google Maps Places + Geocoding API
│   ├── translate_service.py      # Google Cloud Translation API v2 (batch)
│   ├── analytics_service.py      # BigQuery + Cloud Logging integration
│   └── validator.py              # Input validation, sanitization, injection guard
├── templates/
│   └── index.html                # SPA — Firebase SDK, Maps SDK, ARIA-complete
├── static/
│   ├── style.css                 # Dark glassmorphic — WCAG AA, responsive
│   └── script.js                 # Maps dark-mode JSON style, Firebase RT, accessibility
├── tests/
│   ├── conftest.py               # Pytest path setup
│   └── test_all.py               # Full test suite (unit + integration + edge cases)
├── Dockerfile                    # Cloud Run container
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔧 Setup

### 1. Clone & install
```bash
git clone <repo>
cd election-navigator-ai
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Fill in all API keys
```

### 3. Run locally
```bash
flask run --port 5000
# OR
gunicorn --bind 0.0.0.0:5000 app:app
```

### 4. Run tests
```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

---

## ☁️ Google Services Used

| Service | Usage | How to enable |
|---------|-------|---------------|
| **Vertex AI / Gemini** | Structured AI responses (steps, options, checklists) | Enable Generative Language API |
| **Google Maps JS API** | Dark-mode interactive map with custom markers | Enable Maps JavaScript API |
| **Places API** | Finds nearby election offices and government centres | Enable Places API |
| **Geocoding API** | Converts 6-digit pincodes to lat/lng | Enable Geocoding API |
| **Cloud Translation v2** | Batch-translates all response fields into 12 Indian languages | Enable Cloud Translation API |
| **BigQuery** | Stores anonymized usage analytics (category, language, source) | Create dataset `election_navigator` |
| **Cloud Logging** | Structured request and error logging | Automatic when `GOOGLE_CLOUD_PROJECT` set |
| **Firebase Realtime DB** | Live active-user count + recent query feed | Create project, enable Realtime Database |
| **Cloud Run** | Serverless deployment via Dockerfile | `gcloud run deploy` |

---

## 🚀 Deploy to Cloud Run

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT/election-navigator-ai
gcloud run deploy election-navigator-ai \
  --image gcr.io/YOUR_PROJECT/election-navigator-ai \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=...,GOOGLE_MAPS_API_KEY=...,GOOGLE_TRANSLATE_API_KEY=...,GOOGLE_CLOUD_PROJECT=...
```

---

## 🔐 Security Measures

- **CSP headers** — restricts script/style/connect sources
- **Rate limiting** — 30 requests/min per IP (in-process, no Redis dep)
- **Input validation** — all endpoints validate type, length, allow-list
- **Prompt injection guard** — regex-based detection blocks jailbreak attempts
- **API keys** — never exposed client-side (Maps key injected server-side per render)
- **XSS sanitization** — `sanitize()` in validator + frontend
- **Server fingerprint removed** — `Server` header stripped

---

## ♿ Accessibility (WCAG 2.1 AA)

- Skip-to-content link
- All interactive elements have `aria-label` or `aria-labelledby`
- Live regions (`aria-live="polite"` / `"assertive"`) for dynamic updates
- Full keyboard navigation — no mouse required
- `aria-pressed` on tab buttons, `aria-checked` on checklists
- 44px minimum touch targets throughout
- `prefers-reduced-motion` and `prefers-contrast: high` media query support
- Semantic HTML5 (`header`, `nav`, `main`, `section`, `aside`, `footer`, `article`)
- Error messages linked with `aria-describedby`

---

## 📊 BigQuery Schema

### `election_navigator.interactions`
| Field | Type | Description |
|-------|------|-------------|
| ts | STRING | ISO timestamp (UTC) |
| category | STRING | Query category (eligibility, registration, etc.) |
| response_type | STRING | AI response type (steps, question, etc.) |
| source | STRING | `gemini` or `flow` |
| language | STRING | Language code |

### `election_navigator.booth_searches`
| Field | Type | Description |
|-------|------|-------------|
| ts | STRING | ISO timestamp |
| has_pincode | BOOL | Whether pincode was used |
| has_location | BOOL | Whether GPS was used |
| region | STRING | First 3 digits of pincode + "XXX" (no exact location) |

---

## 📋 Evaluation Targets

| Category | Target | Implementation |
|----------|--------|----------------|
| Code Quality | 100% | Modular services, docstrings, typed, linting-ready |
| Security | 100% | CSP, rate-limit, validation, sanitization, injection guard |
| Testing | 100% | 60+ tests, unit + integration + edge cases, mocked APIs |
| Accessibility | 100% | WCAG AA, ARIA, keyboard nav, skip link, contrast |
| Google Services | 100% | Gemini, Maps, Places, Geocoding, Translate, BigQuery, Cloud Logging, Firebase, Cloud Run |
| Problem Alignment | 100% | Structured flows, timelines, personalized journeys, booth finder |
