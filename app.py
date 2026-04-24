"""
Election Navigator AI - Main Application
Flask backend with Gemini API integration for election guidance.
"""

import os
import logging
import time  # ✅ ADDED
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import google.generativeai as genai
import json  # ✅ ADDED

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ✅ SIMPLE IN-MEMORY CACHE (ADDED)
CACHE = {}
CACHE_TTL = 300  # 5 minutes


# Initialize Gemini client
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    logger.warning("GEMINI_API_KEY not set. AI responses will be disabled.")
    model = None
else:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
    logger.info("Gemini model initialized successfully.")


SYSTEM_PROMPT = """You are Election Navigator AI — a friendly, expert guide helping Indian citizens understand the election process.

STRICT OUTPUT FORMAT: Always respond in valid JSON with this exact structure:
{
  "type": "steps" | "cards" | "checklist" | "info" | "question",
  "title": "Brief heading",
  "summary": "1-2 sentence overview",
  "items": [...],
  "follow_ups": ["suggestion 1", "suggestion 2", "suggestion 3"]
}

For type "steps": items = [{"step": 1, "title": "...", "description": "...", "icon": "emoji"}]
For type "cards": items = [{"title": "...", "description": "...", "icon": "emoji", "tag": "optional badge"}]
For type "checklist": items = [{"task": "...", "detail": "...", "required": true/false}]
For type "info": items = [{"label": "...", "value": "..."}]
For type "question": items = [{"option": "...", "description": "...", "action": "query to send"}]

Rules:
- ALWAYS return valid JSON, nothing else. No markdown fences.
- Max 6-8 items per list.
- Keep descriptions concise (under 20 words each).
- Use relevant emojis for icons.
- follow_ups must always have exactly 3 items — short, actionable button labels.
- Focus on India's election system (ECI, EVM, VVPAT, Voter ID, etc.)
- Be accurate, factual, and helpful.
- For greetings/unclear input, use type "question" to guide the user."""

def handle_personalized_flow(user_input, context):
    text = user_input.lower()

    # Entry point
    if "first-time voter" in text:
        return {
            "type": "question",
            "title": "Let’s get you ready to vote 🌟",
            "summary": "Answer 2 quick questions so I can guide you.",
            "items": [
                {"option": "I’m 18 or above", "description": "Eligible by age", "action": "age_yes"},
                {"option": "I’m below 18", "description": "Not eligible yet", "action": "age_no"}
            ],
            "follow_ups": ["Check eligibility", "Documents needed", "Registration steps"]
        }

    # Age branch
    if "age_yes" in text:
        return {
            "type": "question",
            "title": "Great! Do you have a Voter ID?",
            "summary": "This helps decide your next steps.",
            "items": [
                {"option": "Yes, I have it", "description": "Ready to vote", "action": "have_id"},
                {"option": "No, I don’t", "description": "Need to register", "action": "no_id"}
            ],
            "follow_ups": ["How to register", "Required documents", "Voting day steps"]
        }

    if "age_no" in text:
        return {
            "type": "info",
            "title": "You’ll be eligible soon 🎓",
            "summary": "Voting starts at 18 years in India.",
            "items": [{"label": "Tip", "value": "Prepare documents in advance."}],
            "follow_ups": ["Documents needed", "How to register", "Election basics"]
        }

    # ID branch
    if "no_id" in text:
        return {
            "type": "checklist",
            "title": "Register for Voter ID 🪪",
            "summary": "Follow this to get your EPIC.",
            "items": [
                {"task": "Go to NVSP/ECI portal", "detail": "Fill Form 6", "required": True},
                {"task": "Upload documents", "detail": "Age + address proof", "required": True},
                {"task": "Track application", "detail": "Get EPIC number", "required": True}
            ],
            "follow_ups": ["Documents list", "Check eligibility", "What next after ID"]
        }

    if "have_id" in text:
        return {
            "type": "steps",
            "title": "You’re ready to vote 🗳️",
            "summary": "Here’s your voting day flow.",
            "items": [
                {"step": 1, "title": "Check your name", "description": "In electoral roll", "icon": "🔍"},
                {"step": 2, "title": "Find booth", "description": "Use EPIC details", "icon": "📍"},
                {"step": 3, "title": "Vote on EVM", "description": "Verify via VVPAT", "icon": "🖥️"}
            ],
            "follow_ups": ["What to carry", "Booth finder", "EVM explained"]
        }

    return None

# ✅ FALLBACK RESPONSE (ADDED)
def fallback_response(message="Try again"):
    return {
        "type": "info",
        "title": "⚠️ Temporary Issue",
        "summary": "I'm having trouble right now. Please try again.",
        "items": [{"label": "Suggestion", "value": message}],
        "follow_ups": ["How do I vote?", "Check eligibility", "Register to vote"]
    }


def get_ai_response(user_input: str, context: list) -> dict:
    """Get structured response from Gemini API."""

    # ✅ NORMALIZE INPUT FOR CACHE (ADDED)
    context_str = json.dumps(context, sort_keys=True) if context else "[]"
    cache_key = f"{user_input.strip().lower()}_{context_str}"

    # ✅ CACHE CHECK (ADDED)
    if cache_key in CACHE:
        cached_data, timestamp = CACHE[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            logger.info("Cache hit")
            return cached_data

    if not model:
        return {
            "type": "info",
            "title": "API Key Required",
            "summary": "Please configure your GEMINI_API_KEY in the .env file.",
            "items": [{"label": "Setup", "value": "Add GEMINI_API_KEY=your_key to .env file"}],
            "follow_ups": ["How to get API key?", "Check eligibility", "Voting steps"]
        }

    # Build conversation history
    history = []
    for msg in context[-6:]:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})

    try:
        chat = model.start_chat(history=history)

        response = chat.send_message(
            f"{SYSTEM_PROMPT}\n\nUser query: {user_input}",
            generation_config={"response_mime_type": "application/json"},
            request_options={"timeout": 10}  # ✅ TIMEOUT ADDED
        )

        text = response.text.strip()

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        parsed = json.loads(text)

        # ✅ STORE IN CACHE (ADDED)
        CACHE[cache_key] = (parsed, time.time())

        return parsed

    except json.JSONDecodeError as e:
        logger.error(f"JSON Decode Error: {e}")
        return fallback_response("Invalid AI response format")

    except Exception as e:
        logger.error(f"Gemini API error: {e}")

        # ✅ HANDLE QUOTA ERROR (ADDED)
        if "429" in str(e):
            return {
                "type": "info",
                "title": "⚠️ High Traffic",
                "summary": "Too many requests right now. Please wait a moment.",
                "items": [{"label": "Error", "value": "Quota exceeded"}],
                "follow_ups": ["Try again", "Check eligibility", "Voting steps"]
            }

        return fallback_response(str(e)[:80])


@app.route("/")
def index():
    """Serve the main application page."""
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)  # ✅ FIXED

    if not data:
        return jsonify({"error": "Invalid request body"}), 400
    user_input = data.get("message", "").strip()
    context = data.get("context", [])

    if not user_input:
        return jsonify({"error": "Message cannot be empty"}), 400

    if len(user_input) > 500:
        return jsonify({"error": "Message too long (max 500 characters)"}), 400

    logger.info(f"User query: {user_input[:80]}")

    # 🔥 ADD THIS BLOCK
    personalized = handle_personalized_flow(user_input, context)
    if personalized:
        return jsonify(personalized)
    response = get_ai_response(user_input, context)
    return jsonify(response)


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "model": "gemini-1.5-flash",
        "api_key_set": bool(API_KEY),
        "cache_size": len(CACHE)  # ✅ ADDED
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)