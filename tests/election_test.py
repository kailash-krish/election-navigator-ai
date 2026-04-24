"""
Tests for Election Navigator AI
Run: python -m pytest tests/ -v
"""
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.get_json()
        assert data["status"] == "ok"


class TestChatEndpoint:
    def test_empty_message_rejected(self, client):
        res = client.post("/chat", json={"message": ""})
        assert res.status_code == 400

    def test_missing_body_rejected(self, client):
        res = client.post("/chat", data="not json", content_type="text/plain")
        assert res.status_code == 400

    def test_too_long_message_rejected(self, client):
        res = client.post("/chat", json={"message": "x" * 501})
        assert res.status_code == 400

    def test_valid_message_returns_structured(self, client):
        res = client.post("/chat", json={"message": "How do I vote?", "context": []})
        assert res.status_code == 200
        data = res.get_json()
        # Must always have these keys (even in fallback mode)
        assert "type" in data
        assert "title" in data
        assert "summary" in data
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_context_optional(self, client):
        res = client.post("/chat", json={"message": "What is EVM?"})
        assert res.status_code == 200


class TestHomePage:
    def test_home_returns_200(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert b"Election Navigator" in res.data

    def test_static_css_exists(self, client):
        res = client.get("/static/style.css")
        assert res.status_code == 200

    def test_static_js_exists(self, client):
        res = client.get("/static/script.js")
        assert res.status_code == 200