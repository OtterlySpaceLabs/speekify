from __future__ import annotations

from urllib.parse import urlparse

from speekify.config import SUPPORTED_TTS_LANGUAGES, VOICE_NAMES


def normalize_voice_name(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in VOICE_NAMES:
        available = ", ".join(VOICE_NAMES)
        raise ValueError(f"Voice must be one of: {available}")
    return normalized


def normalize_language_code(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in SUPPORTED_TTS_LANGUAGES:
        available = ", ".join(SUPPORTED_TTS_LANGUAGES)
        raise ValueError(
            "Language code must be one of the values supported by Supertonic: "
            f"{available}"
        )
    return normalized


def normalize_source_text(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("A text source or URL is required.")
    return normalized


def normalize_feed_base_url(feed_base_url: str) -> str:
    candidate = feed_base_url.strip().rstrip("/")
    if not candidate:
        return ""
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Feed base URL must be an http:// or https:// URL.")
    return candidate