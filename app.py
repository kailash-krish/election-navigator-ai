"""
Election Navigator AI — Production Flask Application
Google Gemini + Maps + Translate powered election guidance for Indian citizens.
"""

import os
import logging
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

from services.gemini_service import GeminiService
from services.maps_service import MapsService
from services.translate_service import TranslateService
from services.flow_service import FlowService
from services.validator import validate_chat_request

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# ── Service Initialization ──────────────────────────────────────────────────
gemini_svc = GeminiService(api_key=os.environ.get("GEMINI_API_KEY"))
maps_svc   = MapsService(api_key=os.environ.get("GOOGLE_MAPS_API_KEY"))
trans_svc  = TranslateService(api_key=os.environ.get("GOOGLE_TRANSLATE_API_KEY"))
flow_svc   = FlowService()


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    maps_key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    return render_template("index.html", maps_api_key=maps_key)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True)
    error = validate_chat_request(data)
    if error:
        return jsonify({"error": error}), 400

    user_input = data["message"].strip()
    context    = data.get("context", [])
    language   = data.get("language", "en")

    logger.info("Query [%s]: %s", language, user_input[:80])

    # 1. Scripted decision-flow first
    flow_resp = flow_svc.handle(user_input, context)
    if flow_resp:
        return jsonify(flow_resp)

    # 2. AI response
    response = gemini_svc.get_response(user_input, context)

    # 3. Translate if needed
    if language != "en":
        response = trans_svc.translate_response(response, language)

    return jsonify(response)


@app.route("/polling-booth", methods=["POST"])
def polling_booth():
    data    = request.get_json(silent=True) or {}
    pincode = str(data.get("pincode", "")).strip()
    lat     = data.get("lat")
    lng     = data.get("lng")

    if not pincode and not (lat and lng):
        return jsonify({"error": "Provide pincode or lat/lng"}), 400

    if pincode and (not pincode.isdigit() or len(pincode) != 6):
        return jsonify({"error": "Invalid pincode (must be 6 digits)"}), 400

    results = maps_svc.find_polling_booths(pincode=pincode, lat=lat, lng=lng)
    return jsonify(results)


@app.route("/translate", methods=["POST"])
def translate():
    data = request.get_json(silent=True) or {}
    text     = str(data.get("text", "")).strip()[:2000]
    target   = str(data.get("target", "en")).strip()[:5]

    if not text:
        return jsonify({"error": "text is required"}), 400

    result = trans_svc.translate_text(text, target)
    return jsonify(result)


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "gemini": gemini_svc.is_ready(),
        "maps":   maps_svc.is_ready(),
        "translate": trans_svc.is_ready(),
        "cache_size": gemini_svc.cache_size()
    })


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(405)
def method_not_allowed(_):
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_error(e):
    logger.error("Internal error: %s", e)
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=False, port=5000, host="0.0.0.0")
