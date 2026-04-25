# 🗳️ Election Navigator AI

> **An intelligent, fully guided AI assistant that helps Indian citizens understand the election process — powered by Google Gemini, Maps & Translate.**

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1-green)](https://flask.palletsprojects.com)
[![Gemini](https://img.shields.io/badge/Google-Gemini%202.5%20Flash-orange)](https://ai.google.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🚀 Problem Statement

Millions of first-time voters in India face confusion about **how to register**, **when to vote**, **what to carry**, and **where their booth is**. Generic chatbots fail them — they need a guided, visual, step-by-step experience.

---

## 💡 Solution

Election Navigator AI is a **decision-tree + AI hybrid** that:
- Guides users through a personalized wizard (no free-text confusion)
- Returns structured, card-based responses (not walls of text)
- Integrates Google Gemini for intelligent Q&A
- Uses Google Maps to find nearby polling booths
- Supports 9 Indian languages via Google Translate API
- Tracks your voter-readiness progress in real time

---

## 🎯 Key Features

| Feature | Description |
|---------|-------------|
| 🌟 First-Time Voter Wizard | Step-by-step guided flow from eligibility → registration → voting day |
| ✅ Eligibility Checker | Interactive checklist of all voter eligibility criteria |
| 📄 Document Checklist | What to gather for Voter ID registration |
| 🪪 Registration Steps | How to register on NVSP/ECI portal (Form 6) |
| 🗳️ Voting Day Guide | Exactly what happens on election day, step by step |
| 🖥️ EVM Explainer | How Electronic Voting Machines work |
| 🧾 VVPAT Explainer | What the paper trail is and why it matters |
| 🗓️ Election Timeline | Visual interactive timeline of all election phases |
| 📍 Polling Booth Finder | Google Maps integration — search by pincode or live location |
| 🌐 Multilingual | 9 Indian languages via Google Translate API |
| 🎯 Progress Tracker | Real-time voter-readiness checklist in the sidebar |
| 🤖 Gemini AI | Falls back to Gemini for any question not in scripted flows |

---

## 🧱 Architecture

```
election-navigator-ai/
├── app.py                  # Flask app, routes
├── services/
│   ├── gemini_service.py   # Google Gemini API + caching + retry
│   ├── maps_service.py     # Google Maps Places + Geocoding API
│   ├── translate_service.py# Google Cloud Translation API
│   ├── flow_service.py     # Scripted decision-tree flows
│   └── validator.py        # Input validation + sanitization
├── templates/
│   └── index.html          # Full UI with Maps embed
├── static/
│   ├── style.css           # Design system (WCAG 2.1 AA)
│   └── script.js           # Chat, rendering, Maps JS
├── tests/
│   └── test_app.py         # 50+ pytest tests
├── .env.example
├── requirements.txt
└── Dockerfile
```

---

## ⚡ Google Services Used

| Service | How It's Used |
|---------|--------------|
| **Gemini 2.5 Flash** | Structured JSON AI responses with retry, caching, temperature control |
| **Maps JavaScript API** | Interactive map in Booth Finder tab |
| **Places API (Nearby Search)** | Finds election offices near user's location |
| **Geocoding API** | Converts 6-digit pincodes to lat/lng coordinates |
| **Cloud Translation API** | Translates all AI responses into 9 Indian languages |

---

## 🔐 Security

- All API keys via environment variables (never hardcoded)
- Input validation: length, type, allowed values, sanitization (XSS prevention)
- HTML escape on all user-facing dynamic content
- Request timeouts on all external API calls
- Error handling for every external service call
- No sensitive data logged

---

## 🛠️ Setup

### 1. Clone

```bash
git clone https://github.com/kailash-krish/election-navigator-ai
cd election-navigator-ai
```

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure API keys

```bash
cp .env.example .env
# Edit .env and add your keys:
#   GEMINI_API_KEY         (required)
#   GOOGLE_MAPS_API_KEY    (optional — enables booth finder map)
#   GOOGLE_TRANSLATE_API_KEY (optional — enables multilingual)
```

**Get your keys:**
- Gemini: https://aistudio.google.com/
- Maps + Translate: https://console.cloud.google.com/ → Enable: Maps JS API, Places API, Geocoding API, Cloud Translation API

### 4. Run

```bash
python app.py
# Visit http://localhost:5000
```

### 5. Run tests

```bash
python -m pytest tests/ -v
```

---

## 🐳 Docker

```bash
docker build -t election-navigator .
docker run -p 5000:5000 --env-file .env election-navigator
```

---

## ♿ Accessibility

- WCAG 2.1 AA compliant
- Skip navigation link
- All interactive elements keyboard-accessible
- `aria-label`, `aria-live`, `aria-pressed`, `role` attributes throughout
- `prefers-reduced-motion` respected
- High contrast mode support

---

## 🤝 Data Sources

- [Election Commission of India](https://eci.gov.in)
- [NVSP Portal](https://voters.eci.gov.in)
- Voter Helpline: **1950**

---

## 📄 License

MIT — built for PromptWars by Hack2Skill × Google
