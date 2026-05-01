"""
services/translate_service.py — Google Cloud Translation API v2.
Batch translation, retry logic, graceful fallback, and proper error handling.
"""

import logging
import json
import urllib.parse
import urllib.request
import urllib.error
import time
from typing import Optional

logger = logging.getLogger(__name__)

TRANSLATE_URL  = "https://translation.googleapis.com/language/translate/v2"
DETECT_URL     = "https://translation.googleapis.com/language/translate/v2/detect"

# Text fields per response type that should be translated
_TRANSLATABLE_FIELDS = ("title", "description", "task", "detail",
                        "label", "value", "option", "event", "summary")


class TranslateService:
    """
    Google Cloud Translation API (Basic / v2).
    Translates structured AI response dicts into any supported Indian language.
    Batch translates text fields in a single API call for efficiency.
    """

    def __init__(self, api_key: Optional[str]):
        self._key   = api_key
        self._ready = bool(api_key)
        if not api_key:
            logger.warning("GOOGLE_TRANSLATE_API_KEY not configured.")

    def is_ready(self) -> bool:
        return self._ready

    # ── Public API ────────────────────────────────────────────────────────────

    def translate_text(self, text: str, target: str) -> dict:
        """Translate a single text string."""
        if not self._ready:
            return {"translatedText": text, "warning": "Translate API not configured"}
        if target == "en":
            return {"translatedText": text}
        result = self._call_api_single(text, target)
        return {"translatedText": result}

    def translate_response(self, response: dict, target: str) -> dict:
        """
        Translate all user-visible text fields in a structured AI response.
        Uses batch translation to minimise API round-trips.
        """
        if not self._ready or target == "en":
            return response

        # Collect all (path, text) pairs that need translation
        translations: list[tuple] = []   # [(setter_fn, original_text), ...]

        def collect(obj, key, setter):
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                translations.append((setter, val))

        # Top-level fields
        collect(response, "title",   lambda v: response.__setitem__("title", v))
        collect(response, "summary", lambda v: response.__setitem__("summary", v))
        if response.get("tip"):
            collect(response, "tip", lambda v: response.__setitem__("tip", v))

        # Item fields
        for i, item in enumerate(response.get("items", [])):
            for field in _TRANSLATABLE_FIELDS:
                if field in item and isinstance(item[field], str) and item[field].strip():
                    # Capture i, field in closure
                    def make_setter(idx, f):
                        return lambda v: response["items"][idx].__setitem__(f, v)
                    translations.append((make_setter(i, field), item[field]))

        # Follow-ups
        for i, fu in enumerate(response.get("follow_ups", [])):
            if isinstance(fu, str) and fu.strip():
                def make_fu_setter(idx):
                    return lambda v: response["follow_ups"].__setitem__(idx, v)
                translations.append((make_fu_setter(i), fu))

        if not translations:
            return response

        # Batch translate all texts
        texts = [t[1] for t in translations]
        translated = self._call_api_batch(texts, target)

        # Apply back
        for (setter, _), translated_text in zip(translations, translated):
            try:
                setter(translated_text)
            except Exception as e:
                logger.debug("Setter error: %s", e)

        return response

    # ── Private ───────────────────────────────────────────────────────────────

    def _call_api_single(self, text: str, target: str) -> str:
        try:
            results = self._call_api_batch([text], target)
            return results[0] if results else text
        except Exception as e:
            logger.error("Translate API error in single: %s", e)
            return text

    def _call_api_batch(self, texts: list[str], target: str) -> list[str]:
        """
        Batch translate up to 128 strings in one API request.
        Returns translated strings in same order; falls back to originals on error.
        """
        if not texts:
            return []

        # Build query string with repeated 'q' params
        params = [("key", self._key), ("target", target), ("format", "text")]
        for t in texts:
            params.append(("q", t[:5000]))  # API max per string
        encoded = urllib.parse.urlencode(params)
        url = f"{TRANSLATE_URL}?{encoded}"

        for attempt in range(2):
            try:
                req = urllib.request.Request(
                    url, method="GET",
                    headers={"Accept": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read())

                translations = data.get("data", {}).get("translations", [])
                results = [t.get("translatedText", orig) for t, orig in zip(translations, texts)]
                # Pad if API returned fewer results than expected
                while len(results) < len(texts):
                    results.append(texts[len(results)])
                return results

            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="ignore")
                logger.error("Translate API HTTP %d: %s", e.code, body[:200])
                if e.code == 429 and attempt == 0:
                    time.sleep(1)
                    continue
                break
            except Exception as e:
                logger.error("Translate API error: %s", e)
                break

        return texts  # Return originals on failure
