"""
services/validator.py — Input validation and sanitization.
"""

import re
import html


MAX_MSG_LEN = 500
ALLOWED_LANGUAGES = {
    "en", "hi", "ta", "te", "kn", "ml", "bn", "mr", "gu", "pa", "or", "ur"
}


def sanitize(text: str) -> str:
    """Strip HTML tags and escape special characters."""
    clean = re.sub(r"<[^>]+>", "", text)
    return html.escape(clean.strip())


def validate_chat_request(data: dict | None) -> str | None:
    """Return error string or None if valid."""
    if not data or not isinstance(data, dict):
        return "Invalid JSON body"

    message = data.get("message", "")
    if not isinstance(message, str) or not message.strip():
        return "Message cannot be empty"

    if len(message) > MAX_MSG_LEN:
        return f"Message too long (max {MAX_MSG_LEN} characters)"

    context = data.get("context", [])
    if not isinstance(context, list):
        return "context must be an array"

    if len(context) > 20:
        return "context too long (max 20 messages)"

    language = data.get("language", "en")
    if language not in ALLOWED_LANGUAGES:
        return f"Unsupported language '{language}'"

    return None
