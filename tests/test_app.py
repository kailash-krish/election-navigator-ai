"""
tests/test_app.py — Comprehensive test suite for Election Navigator AI
Run: python -m pytest tests/ -v --tb=short
"""

import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

# Patch Gemini before importing app
with patch("google.generativeai.configure"), patch("google.generativeai.GenerativeModel"):
    from app import app as flask_app

# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


VALID_RESPONSE = {
    "type": "info",
    "title": "Test Title",
    "summary": "Test summary.",
    "items": [{"label": "A", "value": "B"}],
    "follow_ups": ["Option 1", "Option 2", "Option 3"],
}


# ── Health endpoint ───────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_200(self, client):
        res = client.get("/health")
        assert res.status_code == 200

    def test_health_json_shape(self, client):
        data = client.get("/health").get_json()
        assert "status" in data
        assert "gemini" in data
        assert "maps" in data
        assert "translate" in data
        assert "cache_size" in data

    def test_health_status_ok(self, client):
        data = client.get("/health").get_json()
        assert data["status"] == "ok"


# ── Home page ─────────────────────────────────────────────────────────────

class TestHomePage:
    def test_home_200(self, client):
        assert client.get("/").status_code == 200

    def test_home_contains_brand(self, client):
        assert b"Election Navigator" in client.get("/").data

    def test_static_css(self, client):
        assert client.get("/static/style.css").status_code == 200

    def test_static_js(self, client):
        assert client.get("/static/script.js").status_code == 200


# ── /chat — input validation ──────────────────────────────────────────────

class TestChatValidation:
    def test_empty_message(self, client):
        res = client.post("/chat", json={"message": ""})
        assert res.status_code == 400

    def test_missing_body(self, client):
        res = client.post("/chat", data="not json", content_type="text/plain")
        assert res.status_code == 400

    def test_too_long(self, client):
        res = client.post("/chat", json={"message": "x" * 501})
        assert res.status_code == 400

    def test_no_json_body(self, client):
        res = client.post("/chat")
        assert res.status_code == 400

    def test_invalid_language(self, client):
        res = client.post("/chat", json={"message": "hi", "language": "xx"})
        assert res.status_code == 400

    def test_context_too_long(self, client):
        ctx = [{"role": "user", "content": "hi"}] * 25
        res = client.post("/chat", json={"message": "hi", "context": ctx})
        assert res.status_code == 400

    def test_context_not_list(self, client):
        res = client.post("/chat", json={"message": "hi", "context": "bad"})
        assert res.status_code == 400

    def test_whitespace_only(self, client):
        res = client.post("/chat", json={"message": "   "})
        assert res.status_code == 400

    def test_max_length_ok(self, client):
        # Exactly 500 chars should be OK (scripted flow will handle it)
        msg = "first-time voter " + "x" * 482  # triggers scripted flow
        res = client.post("/chat", json={"message": msg})
        assert res.status_code == 200


# ── /chat — scripted flows ────────────────────────────────────────────────

class TestScriptedFlows:
    def _chat(self, client, msg, **kwargs):
        body = {"message": msg, **kwargs}
        return client.post("/chat", json=body)

    def test_first_time_voter(self, client):
        res = self._chat(client, "I am a first-time voter")
        data = res.get_json()
        assert res.status_code == 200
        assert data["type"] == "question"
        assert "first" in data["title"].lower() or "voter" in data["title"].lower()

    def test_eligibility(self, client):
        res = self._chat(client, "Am I eligible to vote?")
        assert res.status_code == 200
        data = res.get_json()
        assert data["type"] == "checklist"

    def test_documents(self, client):
        res = self._chat(client, "What documents do I need?")
        assert res.status_code == 200
        data = res.get_json()
        assert data["type"] == "checklist"

    def test_registration(self, client):
        res = self._chat(client, "How do I register for voter id?")
        assert res.status_code == 200
        data = res.get_json()
        assert data["type"] == "steps"

    def test_evm(self, client):
        res = self._chat(client, "What is EVM and how does it work?")
        assert res.status_code == 200
        data = res.get_json()
        assert data["type"] in ("cards", "steps", "info")

    def test_vvpat(self, client):
        res = self._chat(client, "What is VVPAT?")
        assert res.status_code == 200
        data = res.get_json()
        assert data["type"] in ("cards", "info", "steps")

    def test_timeline(self, client):
        res = self._chat(client, "Show election timeline")
        assert res.status_code == 200
        data = res.get_json()
        assert data["type"] == "timeline"

    def test_flow_age_yes(self, client):
        res = self._chat(client, "age_yes")
        assert res.status_code == 200
        data = res.get_json()
        assert data["type"] == "question"

    def test_flow_age_no(self, client):
        res = self._chat(client, "age_no")
        assert res.status_code == 200
        data = res.get_json()
        assert data["type"] == "info"

    def test_flow_have_id(self, client):
        res = self._chat(client, "have_id")
        assert res.status_code == 200
        data = res.get_json()
        assert data["type"] == "steps"

    def test_flow_no_id(self, client):
        res = self._chat(client, "no_id")
        assert res.status_code == 200
        data = res.get_json()
        assert data["type"] == "steps"

    def test_response_has_required_keys(self, client):
        res = self._chat(client, "eligibility check")
        data = res.get_json()
        for key in ("type", "title", "summary", "items", "follow_ups"):
            assert key in data, f"Missing key: {key}"

    def test_follow_ups_is_list(self, client):
        res = self._chat(client, "I am a first-time voter")
        data = res.get_json()
        assert isinstance(data["follow_ups"], list)

    def test_items_is_list(self, client):
        res = self._chat(client, "eligibility")
        data = res.get_json()
        assert isinstance(data["items"], list)


# ── /polling-booth ────────────────────────────────────────────────────────

class TestPollingBooth:
    def test_no_params_rejected(self, client):
        res = client.post("/polling-booth", json={})
        assert res.status_code == 400

    def test_invalid_pincode(self, client):
        res = client.post("/polling-booth", json={"pincode": "123"})
        assert res.status_code == 400

    def test_alpha_pincode(self, client):
        res = client.post("/polling-booth", json={"pincode": "abcdef"})
        assert res.status_code == 400

    def test_valid_pincode_no_key(self, client):
        # Without Maps key, should return no-key response (not 500)
        res = client.post("/polling-booth", json={"pincode": "600001"})
        data = res.get_json()
        assert res.status_code == 200
        assert "results" in data or "error" in data

    def test_lat_lng(self, client):
        res = client.post("/polling-booth", json={"lat": 13.0, "lng": 80.2})
        assert res.status_code == 200


# ── /translate ────────────────────────────────────────────────────────────

class TestTranslate:
    def test_missing_text(self, client):
        res = client.post("/translate", json={"target": "hi"})
        assert res.status_code == 400

    def test_valid_request_no_key(self, client):
        res = client.post("/translate", json={"text": "Hello", "target": "hi"})
        assert res.status_code == 200
        data = res.get_json()
        assert "translatedText" in data


# ── 404 / 405 handlers ────────────────────────────────────────────────────

class TestErrorHandlers:
    def test_404(self, client):
        res = client.get("/does-not-exist")
        assert res.status_code == 404

    def test_405_on_chat_get(self, client):
        res = client.get("/chat")
        assert res.status_code == 405


# ── Services unit tests ───────────────────────────────────────────────────

class TestValidator:
    def test_valid(self):
        from services.validator import validate_chat_request
        assert validate_chat_request({"message": "hello"}) is None

    def test_none(self):
        from services.validator import validate_chat_request
        assert validate_chat_request(None) is not None

    def test_empty_msg(self):
        from services.validator import validate_chat_request
        assert validate_chat_request({"message": ""}) is not None

    def test_too_long(self):
        from services.validator import validate_chat_request
        assert validate_chat_request({"message": "x" * 501}) is not None

    def test_bad_language(self):
        from services.validator import validate_chat_request
        assert validate_chat_request({"message": "hi", "language": "zz"}) is not None

    def test_context_not_list(self):
        from services.validator import validate_chat_request
        assert validate_chat_request({"message": "hi", "context": {}}) is not None

    def test_sanitize(self):
        from services.validator import sanitize
        result = sanitize("<script>alert('xss')</script>")
        assert "<script>" not in result


class TestFlowService:
    def setup_method(self):
        from services.flow_service import FlowService
        self.svc = FlowService()

    def test_first_time_voter(self):
        r = self.svc.handle("I am a first-time voter", [])
        assert r is not None
        assert r["type"] == "question"

    def test_eligibility(self):
        r = self.svc.handle("Am I eligible to vote?", [])
        assert r["type"] == "checklist"

    def test_documents(self):
        r = self.svc.handle("What documents do I need?", [])
        assert r["type"] == "checklist"

    def test_registration(self):
        r = self.svc.handle("How do I register?", [])
        assert r["type"] == "steps"

    def test_evm(self):
        r = self.svc.handle("How does EVM work?", [])
        assert r is not None

    def test_vvpat(self):
        r = self.svc.handle("What is VVPAT?", [])
        assert r is not None

    def test_timeline(self):
        r = self.svc.handle("Show election timeline", [])
        assert r["type"] == "timeline"

    def test_age_yes(self):
        r = self.svc.handle("age_yes", [])
        assert r["type"] == "question"

    def test_age_no(self):
        r = self.svc.handle("age_no", [])
        assert r["type"] == "info"

    def test_have_id(self):
        r = self.svc.handle("have_id", [])
        assert r["type"] == "steps"

    def test_no_id(self):
        r = self.svc.handle("no_id", [])
        assert r["type"] == "steps"

    def test_unknown_returns_none(self):
        r = self.svc.handle("some random query xyz", [])
        assert r is None

    def test_all_responses_have_keys(self):
        inputs = [
            "first-time voter", "am I eligible", "documents needed",
            "how to register", "how does evm work", "what is vvpat",
            "election timeline",
        ]
        for inp in inputs:
            r = self.svc.handle(inp, [])
            if r:
                for k in ("type", "title", "summary", "items", "follow_ups"):
                    assert k in r, f"Missing '{k}' for input '{inp}'"


class TestMapsService:
    def test_no_key(self):
        from services.maps_service import MapsService
        svc = MapsService(api_key=None)
        assert not svc.is_ready()
        result = svc.find_polling_booths(pincode="600001")
        assert "error" in result

    def test_is_ready(self):
        from services.maps_service import MapsService
        svc = MapsService(api_key="fake-key")
        assert svc.is_ready()


class TestTranslateService:
    def test_no_key_passthrough(self):
        from services.translate_service import TranslateService
        svc = TranslateService(api_key=None)
        r = svc.translate_text("Hello", "hi")
        assert r["translatedText"] == "Hello"

    def test_english_passthrough(self):
        from services.translate_service import TranslateService
        svc = TranslateService(api_key="fake")
        data = {"type": "info", "title": "Test", "summary": "s", "items": [], "follow_ups": []}
        result = svc.translate_response(data, "en")
        assert result["title"] == "Test"


class TestGeminiService:
    def test_no_key(self):
        from services.gemini_service import GeminiService
        with patch("google.generativeai.configure"), patch("google.generativeai.GenerativeModel"):
            svc = GeminiService(api_key=None)
        assert not svc.is_ready()

    def test_cache_size_starts_zero(self):
        from services.gemini_service import GeminiService
        with patch("google.generativeai.configure"), patch("google.generativeai.GenerativeModel"):
            svc = GeminiService(api_key=None)
        assert svc.cache_size() == 0

    def test_no_key_response_shape(self):
        from services.gemini_service import GeminiService
        with patch("google.generativeai.configure"), patch("google.generativeai.GenerativeModel"):
            svc = GeminiService(api_key=None)
        r = svc.get_response("How do I vote?", [])
        for k in ("type", "title", "summary", "items", "follow_ups"):
            assert k in r


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
