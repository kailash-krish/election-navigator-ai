# 🗳️ Election Navigator AI

> An intelligent, guided assistant that helps Indian citizens understand the election process — step by step, card by card.

---

## 🏆 Hackathon Vertical
**Civic Tech / Public Services** — Making democracy more accessible through AI-powered guidance.

---

## ✨ What Makes This Stand Out

Unlike a basic chatbot, Election Navigator AI delivers **structured, interactive responses** — not walls of text. Every answer is visually organized as steps, cards, checklists, or interactive decision trees, making complex electoral information instantly digestible.

---

## 🚀 Features

| Feature | Description |
|---|---|
| 🧭 Guided Flow | Decision-tree navigation — the AI asks clarifying questions to guide users |
| 📋 Voter Registration | Step-by-step registration guide with checklist |
| 🗳️ Voting Day Walkthrough | 8-step visual guide to Election Day |
| ✅ Eligibility Checker | Quick Q&A to verify voter eligibility |
| 📅 Election Timeline | Key dates and important milestones |
| 🌟 First-Time Voter Mode | Specially tailored guidance for new voters |
| 🖥️ EVM & VVPAT Explainer | How electronic voting machines work |
| ⚖️ Voting Rights | Know your rights at the polling booth |
| 💡 Smart Follow-ups | Contextual suggestions after every response |
| 📱 Fully Mobile-Responsive | Works on any screen size |

---

## 🧠 How It Works

1. **User sends a query** via the chat interface or taps a Quick Topic button
2. **Flask backend** receives the message and conversation context
3. **Gemini AI (gemini-2.0-flash-lite)** processes the query with a structured system prompt
4. **AI returns JSON** — typed as `steps`, `cards`, `checklist`, `info`, or `question`
5. **Frontend renders** the JSON into beautiful, interactive UI components
6. **Follow-up buttons** appear, keeping the user engaged in a guided flow

### Response Types
- **`steps`** — numbered step-by-step guide with icons
- **`cards`** — topic cards in a responsive grid
- **`checklist`** — required/optional task lists with visual indicators
- **`info`** — key-value fact tables
- **`question`** — interactive option buttons for decision-tree navigation

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+ · Flask 3.x
- **AI**: Google Gemini API (`gemini-2.0-flash-lite`)
- **Frontend**: Vanilla HTML5 · CSS3 · JavaScript (ES6+)
- **Fonts**: Syne (headings) · DM Sans (body) via Google Fonts
- **Dependencies**: `google-generativeai`, `flask`, `python-dotenv`

---

## 🔧 Setup & Run

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/election-navigator-ai.git
cd election-navigator-ai
```

### 2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API key
```bash
cp .env.example .env
# Edit .env and add your Gemini API key:
# GEMINI_API_KEY=your_key_here
```

Get your free Gemini API key at: https://aistudio.google.com/app/apikey

### 5. Run the app
```bash
python app.py
```
Open http://localhost:5000

---

## 🧪 Running Tests
```bash
pip install pytest
python -m pytest tests/ -v
```

---

## 📁 Project Structure
```
election-navigator-ai/
├── app.py                  # Flask app + Gemini AI logic
├── requirements.txt        # Python dependencies
├── .env.example            # API key template
├── .gitignore
├── README.md
├── templates/
│   └── index.html          # Main UI template
├── static/
│   ├── style.css           # Modern dark UI styles
│   └── script.js           # Chat logic + response renderers
└── tests/
    └── test_app.py         # Pytest test suite
```

---

## 🔐 Security Practices

- API key loaded via environment variable (never hardcoded)
- Input length capped at 500 characters server-side
- HTML output is escaped to prevent XSS
- `.env` excluded from version control via `.gitignore`

---

## ♿ Accessibility

- Semantic HTML with ARIA labels (`role="log"`, `aria-live`, `aria-label`)
- Full keyboard navigation support (Enter to send, Shift+Enter for newline)
- High-contrast dark theme with readable font sizes
- Mobile-responsive layout with hamburger sidebar
- Clear visual hierarchy and descriptive button labels

---

## 🌐 Google Services Used

| Service | Usage |
|---|---|
| **Gemini AI API** | Core AI engine — structured JSON responses |
| **Google Fonts** | Syne + DM Sans typography |

---

## 💡 Assumptions

- Focused on Indian election system (ECI guidelines, EVM, VVPAT, Voter ID)
- Gemini API used as the sole AI backend for simplicity and Gemini integration requirement
- No database needed — conversation context managed in-memory per session
- Repo kept under 1MB as required (no heavy dependencies or assets)

---

*Built for Hack2Skill × Google PromptWars Hackathon*