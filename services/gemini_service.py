"""
services/gemini_service.py — Google Gemini API integration.
Advanced prompting with structured JSON output, caching, and retry logic.
"""

import json
import logging
import time
import hashlib
import os

import google.generativeai as genai

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Election Navigator AI — an expert, friendly guide helping Indian citizens understand elections.

STRICT OUTPUT FORMAT: Respond ONLY in valid JSON (no markdown fences, no preamble):
{
  "type": "steps" | "cards" | "checklist" | "info" | "question" | "timeline",
  "title": "Brief, engaging heading",
  "summary": "1-2 sentence overview (max 30 words)",
  "items": [...],
  "follow_ups": ["short action 1", "short action 2", "short action 3"],
  "tip": "Optional pro-tip (max 20 words)"
}

TYPE SCHEMAS:
- steps:    items = [{"step":N, "title":"...", "description":"...(max 15 words)", "icon":"emoji"}]
- cards:    items = [{"title":"...", "description":"...(max 20 words)", "icon":"emoji", "tag":"optional"}]
- checklist:items = [{"task":"...", "detail":"...(max 15 words)", "required":bool}]
- info:     items = [{"label":"...", "value":"...(max 30 words)"}]
- question: items = [{"option":"...", "description":"...(max 10 words)", "action":"short_slug"}]
- timeline: items = [{"date":"...", "event":"...", "description":"...(max 15 words)", "status":"past|current|upcoming"}]

RULES:
- Max 7 items per list.
- Always exactly 3 follow_ups (short button labels, max 5 words each).
- Focus on India: ECI, EVM, VVPAT, Voter ID, NVSP, Form 6, electoral rolls.
- Be accurate, factual, concise.
- For greetings or unclear input: use type "question" to guide the user.
- Never mention you are an AI or mention Gemini."""

- Never mention you are an AI or mention Gemini."""


class GeminiService:
    def __init__(self, api_key: str | None, redis_client=None):
        self._ready = False
        self._cache: dict = {}
        self._redis = redis_client
        self._cache_ttl = int(os.environ.get("CACHE_TTL", 600))

        if not api_key:
            logger.warning("GEMINI_API_KEY not configured.")
            self._model = None
            return

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel("gemini-2.5-flash")
        self._ready = True
        logger.info("Gemini service initialized.")

    def is_ready(self) -> bool:
        return self._ready

    def cache_size(self) -> int:
        return len(self._cache)

    def get_response(self, user_input: str, context: list) -> dict:
        cache_key = f"gemini_cache:{self._make_cache_key(user_input, context)}"

        if self._redis:
            try:
                val = self._redis.get(cache_key)
                if val:
                    logger.info("Cache hit from Redis.")
                    return json.loads(val)
            except Exception as e:
                logger.error("Redis cache error: %s", e)
        else:
            if cache_key in self._cache:
                entry, ts = self._cache[cache_key]
                if time.time() - ts < self._cache_ttl:
                    logger.info("Cache hit from in-memory.")
                    return entry

        if not self._model:
            return self._no_api_key_response()

        history = self._build_history(context)
        prompt  = f"{SYSTEM_PROMPT}\n\nUser: {user_input}"

        for attempt in range(3):
            try:
                chat  = self._model.start_chat(history=history)
                resp  = chat.send_message(
                    prompt,
                    generation_config={
                        "response_mime_type": "application/json",
                        "temperature": 0.3,
                        "max_output_tokens": 700,
                    },
                    request_options={"timeout": 15},
                )
                parsed = self._parse(resp.text)
                
                if self._redis:
                    try:
                        self._redis.setex(cache_key, self._cache_ttl, json.dumps(parsed))
                    except Exception as e:
                        logger.error("Redis set error: %s", e)
                else:
                    self._cache[cache_key] = (parsed, time.time())
                    
                return parsed

            except Exception as e:
                logger.error("Gemini attempt %d failed: %s", attempt + 1, str(e)[:100])
                if "429" in str(e):
                    return self._rate_limit_response()
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))

        return self._fallback_response()

    # ── Private helpers ──────────────────────────────────────────────────────

    def _make_cache_key(self, user_input: str, context: list) -> str:
        parts = [user_input.strip().lower()]
        for msg in context[-4:]:
            parts.append(f"{msg.get('role', '')}:{msg.get('content', '')}")
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    def _build_history(self, context: list) -> list:
        history = []
        for msg in context[-8:]:
            role = "user" if msg.get("role") == "user" else "model"
            history.append({"role": role, "parts": [str(msg.get("content", ""))]})
        return history

    def _parse(self, text: str) -> dict:
        text = text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip().rstrip("```").strip()
        parsed = json.loads(text)

        # Ensure required keys
        for key in ("type", "title", "summary", "items", "follow_ups"):
            if key not in parsed:
                raise ValueError(f"Missing key: {key}")
        return parsed

    def _no_api_key_response(self) -> dict:
        return {
            "type": "info",
            "title": "API Key Required",
            "summary": "Add GEMINI_API_KEY to your .env file to enable AI responses.",
            "items": [{"label": "Setup", "value": "Create .env and add GEMINI_API_KEY=your_key"}],
            "follow_ups": ["How to register?", "Check eligibility", "Voting steps"],
        }

    def _rate_limit_response(self) -> dict:
        return {
            "type": "info",
            "title": "⚠️ High Traffic",
            "summary": "Too many requests right now. Please wait a moment and try again.",
            "items": [{"label": "Status", "value": "Quota exceeded — retry in 60 seconds"}],
            "follow_ups": ["Try again", "Check eligibility", "Voting steps"],
        }

    def _fallback_response(self) -> dict:
        return {
            "type": "question",
            "title": "How can I help you?",
            "summary": "I'm your election guide. Choose a topic to get started.",
            "items": [
                {"option": "How do I register?",      "description": "Get Voter ID",            "action": "How do I register to vote?"},
                {"option": "How do I vote?",           "description": "Voting day guide",        "action": "Explain the voting process step by step"},
                {"option": "Check my eligibility",    "description": "Am I eligible?",          "action": "Check voter eligibility"},
                {"option": "Election timeline",        "description": "Key dates & phases",     "action": "Show election timeline for India"},
            ],
            "follow_ups": ["Register to vote", "Find polling booth", "Election FAQ"],
        }
