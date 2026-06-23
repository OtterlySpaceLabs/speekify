from __future__ import annotations

from speekify.config import AUTO_TTS_LANGUAGE, SUPPORTED_TTS_LANGUAGES, VOICE_NAMES


def normalize_voice_name(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in VOICE_NAMES:
        available = ", ".join(VOICE_NAMES)
        raise ValueError(f"Voice must be one of: {available}")
    return normalized


def normalize_language_code(value: str) -> str:
    normalized = value.strip().lower()
    if normalized == AUTO_TTS_LANGUAGE:
        return normalized
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