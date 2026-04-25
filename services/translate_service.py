"""
services/translate_service.py — Google Cloud Translation API (Basic/v2).
Translates AI response titles, summaries, and item text into regional languages.
"""

import logging
import urllib.parse
import urllib.request
import json

logger = logging.getLogger(__name__)

TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"


class TranslateService:
    def __init__(self, api_key: str | None):
        self._key   = api_key
        self._ready = bool(api_key)
        if not api_key:
            logger.warning("GOOGLE_TRANSLATE_API_KEY not configured.")

    def is_ready(self) -> bool:
        return self._ready

    def translate_text(self, text: str, target: str) -> dict:
        if not self._ready:
            return {"translatedText": text, "warning": "Translate API not configured"}
        result = self._call_api(text, target)
        return {"translatedText": result}

    def translate_response(self, response: dict, target: str) -> dict:
        """Translate key text fields in a structured AI response dict."""
        if not self._ready or target == "en":
            return response

        try:
            response["title"]   = self._call_api(response.get("title", ""), target)
            response["summary"] = self._call_api(response.get("summary", ""), target)

            for item in response.get("items", []):
                for field in ("title", "description", "task", "detail",
                              "label", "value", "option", "event"):
                    if field in item and item[field]:
                        item[field] = self._call_api(str(item[field]), target)

            response["follow_ups"] = [
                self._call_api(f, target) for f in response.get("follow_ups", [])
            ]
            if response.get("tip"):
                response["tip"] = self._call_api(response["tip"], target)

        except Exception as e:
            logger.error("Translation error: %s", e)

        return response

    def _call_api(self, text: str, target: str) -> str:
        if not text:
            return text
        params = urllib.parse.urlencode({
            "q":      text,
            "target": target,
            "key":    self._key,
            "format": "text",
        })
        url = f"{TRANSLATE_URL}?{params}"
        try:
            with urllib.request.urlopen(url, timeout=6) as resp:
                data = json.loads(resp.read())
            return data["data"]["translations"][0]["translatedText"]
        except Exception as e:
            logger.error("Translate API call failed: %s", e)
            return text
