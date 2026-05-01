"""
Election Navigator AI — Production Flask Application v2.0
Google Gemini + Maps + Translate + BigQuery + Firebase + Cloud Logging
"""

import os
import logging
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

from services.gemini_service import GeminiService
from services.maps_service import MapsService
from services.translate_service import TranslateService
from services.flow_service import FlowService
from services.analytics_service import AnalyticsService
from services.validator import validate_chat_request, validate_translate_request, init_safety_model

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger(__name__)

# ── App factory ───────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# ── Security Headers (Talisman-equivalent manual) ────────────────────────────
@app.after_request
def set_security_headers(response):
    """OWASP-recommended security headers on every response."""
    maps_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    firebase_key = os.environ.get("FIREBASE_API_KEY", "")
    # CSP: allow Maps JS, Firebase, Fonts — block everything else
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://maps.googleapis.com https://maps.gstatic.com "
        "https://www.gstatic.com https://www.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; "
        "img-src 'self' data: https://*.googleapis.com https://*.gstatic.com https://*.google.com; "
        "connect-src 'self' https://*.googleapis.com https://*.firebaseio.com; "
        "frame-src 'none'; object-src 'none';"
    )
    response.headers["Content-Security-Policy"] = csp
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # Remove server fingerprint
    response.headers.pop("Server", None)
    return response


# ── Rate Limiting (lightweight, no external dep) ──────────────────────────────
import redis
from collections import defaultdict
import time

_rate_store: dict = defaultdict(list)
_RATE_WINDOW = int(os.environ.get("RATE_WINDOW", 60))
_RATE_LIMIT   = int(os.environ.get("RATE_LIMIT", 30))

_redis_client = None
if os.environ.get("REDIS_URL"):
    try:
        _redis_client = redis.from_url(os.environ.get("REDIS_URL"), decode_responses=True)
    except Exception as e:
        logger.warning("Redis connection failed: %s", e)

def _is_rate_limited(ip: str) -> bool:
    if _redis_client:
        try:
            key = f"rate_limit:{ip}"
            calls = _redis_client.incr(key)
            if calls == 1:
                _redis_client.expire(key, _RATE_WINDOW)
            if calls > _RATE_LIMIT:
                logger.warning("Rate limit hit for IP %s", ip)
                return True
            return False
        except Exception as e:
            logger.error("Redis rate limit failed, falling back to memory: %s", e)
    
    # Fallback in-memory
    now = time.time()
    calls = _rate_store[ip]
    _rate_store[ip] = [t for t in calls if now - t < _RATE_WINDOW]
    if len(_rate_store[ip]) >= _RATE_LIMIT:
        logger.warning("Rate limit hit for IP %s", ip)
        return True
    _rate_store[ip].append(now)
    return False

def _client_ip() -> str:
    return request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()


# ── Service init ──────────────────────────────────────────────────────────────
init_safety_model(os.environ.get("GEMINI_API_KEY"))
gemini_svc   = GeminiService(api_key=os.environ.get("GEMINI_API_KEY"), redis_client=_redis_client)
maps_svc     = MapsService(api_key=os.environ.get("GOOGLE_MAPS_API_KEY"))
trans_svc    = TranslateService(api_key=os.environ.get("GOOGLE_TRANSLATE_API_KEY"))
flow_svc     = FlowService()
analytics_svc = AnalyticsService(
    project_id=os.environ.get("GOOGLE_CLOUD_PROJECT"),
    dataset_id=os.environ.get("BIGQUERY_DATASET", "election_navigator"),
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve main SPA. Inject Maps key securely — never expose other keys."""
    maps_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    firebase_cfg = {
        "apiKey":            os.environ.get("FIREBASE_API_KEY", ""),
        "authDomain":        os.environ.get("FIREBASE_AUTH_DOMAIN", ""),
        "databaseURL":       os.environ.get("FIREBASE_DATABASE_URL", ""),
        "projectId":         os.environ.get("FIREBASE_PROJECT_ID", ""),
        "storageBucket":     os.environ.get("FIREBASE_STORAGE_BUCKET", ""),
        "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", ""),
        "appId":             os.environ.get("FIREBASE_APP_ID", ""),
    }
    return render_template("index.html", maps_api_key=maps_key, firebase_cfg=firebase_cfg)


@app.route("/chat", methods=["POST"])
def chat():
    """Main AI conversation endpoint with flow routing and translation."""
    if _is_rate_limited(_client_ip()):
        return jsonify({"error": "Too many requests. Please wait a minute."}), 429

    data = request.get_json(silent=True)
    error = validate_chat_request(data)
    if error:
        return jsonify({"error": error}), 400

    user_input = data["message"].strip()
    context    = data.get("context", [])
    language   = data.get("language", "en")

    logger.info("Chat [%s] from %s: %s", language, _client_ip(), user_input[:80])

    # 1. Scripted decision flow (instant, no API)
    flow_resp = flow_svc.handle(user_input, context)
    if flow_resp:
        if language != "en":
            flow_resp = trans_svc.translate_response(flow_resp, language)
        analytics_svc.log_interaction(
            query=user_input, response_type=flow_resp.get("type", "flow"),
            source="flow", language=language
        )
        return jsonify(flow_resp)

    # 2. AI response
    response = gemini_svc.get_response(user_input, context)

    # 3. Translate if requested
    if language != "en":
        response = trans_svc.translate_response(response, language)

    analytics_svc.log_interaction(
        query=user_input, response_type=response.get("type", "ai"),
        source="gemini", language=language
    )
    return jsonify(response)


@app.route("/polling-booth", methods=["POST"])
def polling_booth():
    """Finds nearby election offices using Google Maps Places API."""
    if _is_rate_limited(_client_ip()):
        return jsonify({"error": "Too many requests."}), 429

    data    = request.get_json(silent=True) or {}
    pincode = str(data.get("pincode", "")).strip()
    lat     = data.get("lat")
    lng     = data.get("lng")

    if not pincode and not (lat and lng):
        return jsonify({"error": "Provide pincode or lat/lng"}), 400
    if pincode and (not pincode.isdigit() or len(pincode) != 6):
        return jsonify({"error": "Invalid pincode (must be 6 digits)"}), 400

    results = maps_svc.find_voter_offices(pincode=pincode, lat=lat, lng=lng)
    analytics_svc.log_booth_search(pincode=pincode, has_location=bool(lat and lng))
    return jsonify(results)


@app.route("/translate", methods=["POST"])
def translate():
    """Standalone translation endpoint."""
    if _is_rate_limited(_client_ip()):
        return jsonify({"error": "Too many requests."}), 429

    data = request.get_json(silent=True) or {}
    err = validate_translate_request(data)
    if err:
        return jsonify({"error": err}), 400

    text   = str(data["text"]).strip()[:2000]
    target = str(data.get("target", "en")).strip()[:5]
    result = trans_svc.translate_text(text, target)
    return jsonify(result)


@app.route("/analytics/summary", methods=["GET"])
def analytics_summary():
    """Returns anonymized usage summary from BigQuery (read-only, no PII)."""
    summary = analytics_svc.get_summary()
    return jsonify(summary)


@app.route("/health")
def health():
    """Health check for Cloud Run / uptime monitoring."""
    return jsonify({
        "status":     "ok",
        "version":    "2.0.0",
        "gemini":     gemini_svc.is_ready(),
        "maps":       maps_svc.is_ready(),
        "translate":  trans_svc.is_ready(),
        "analytics":  analytics_svc.is_ready(),
        "cache_size": gemini_svc.cache_size(),
    })


# ── Error handlers ────────────────────────────────────────────────────────────

@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "Bad request"}), 400

@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(405)
def method_not_allowed(_):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(429)
def too_many_requests(_):
    return jsonify({"error": "Rate limit exceeded"}), 429

@app.errorhandler(500)
def internal_error(e):
    logger.error("Internal error: %s", e)
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=False, port=int(os.environ.get("PORT", 5000)), host="0.0.0.0")
