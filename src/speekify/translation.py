from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from speekify.config import DEFAULT_LANG, TRANSLATION_CHUNK_SIZE, TRANSLATION_MODEL_NAME

try:
    from langdetect import LangDetectException, detect
except ImportError:  # pragma: no cover - optional runtime dependency in tests.
    LangDetectException = Exception
    detect = None


@dataclass(frozen=True)
class TranslationResult:
    text: str
    translated: bool
    source_language: str | None
    target_language: str = DEFAULT_LANG
    original_text: str | None = None

    @property
    def changed(self) -> bool:
        return self.translated and self.original_text is not None and self.original_text != self.text


def detect_language_code(text: str) -> str | None:
    candidate = text.strip()
    if len(candidate) < 20:
        return None

    if detect is not None:
        try:
            return str(detect(candidate))
        except LangDetectException:
            return None

    return _fallback_detect_language_code(candidate)


def should_translate_to_french(language_code: str | None) -> bool:
    return language_code == "en"


class HuggingFaceTranslator:
    def __init__(self, model_name: str = TRANSLATION_MODEL_NAME) -> None:
        self.model_name = model_name
        self._backend: tuple[Any, Any, Any, str] | None = None

    def maybe_translate_to_french(self, text: str) -> TranslationResult:
        source_language = detect_language_code(text)
        if not should_translate_to_french(source_language):
            return TranslationResult(
                text=text,
                translated=False,
                source_language=source_language,
                original_text=text,
            )

        translated_chunks = []
        for chunk in _split_text_for_translation(text, max_chars=TRANSLATION_CHUNK_SIZE):
            translated_chunks.append(self._translate_chunk(chunk))

        return TranslationResult(
            text=_normalize_translation_output("\n\n".join(translated_chunks)),
            translated=True,
            source_language=source_language,
            original_text=text,
        )

    @property
    def backend(self) -> tuple[Any, Any, Any, str]:
        if self._backend is None:
            self._backend = self._build_backend()
        return self._backend

    def _build_backend(self) -> tuple[Any, Any, Any, str]:
        try:
            import torch
            from transformers import MarianMTModel, MarianTokenizer
            from transformers.utils import logging as transformers_logging
        except ImportError as exc:  # pragma: no cover - only exercised when deps are missing.
            raise RuntimeError(
                "La traduction n'est pas disponible. Lancez `uv sync` pour installer langdetect, torch et transformers."
            ) from exc

        transformers_logging.disable_progress_bar()
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        tokenizer = MarianTokenizer.from_pretrained(self.model_name)
        model = MarianMTModel.from_pretrained(self.model_name)
        model.to(device)
        return torch, tokenizer, model, device

    def _translate_chunk(self, text: str) -> str:
        torch, tokenizer, model, device = self.backend
        inputs = tokenizer(text, return_tensors="pt", truncation=True)
        inputs = {name: value.to(device) for name, value in inputs.items()}

        with torch.no_grad():
            output_ids = model.generate(**inputs, max_new_tokens=512)

        return str(tokenizer.decode(output_ids[0], skip_special_tokens=True)).strip()


def _split_text_for_translation(text: str, max_chars: int) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    if not paragraphs:
        return [text.strip()]

    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
        if len(paragraph) <= max_chars:
            current = paragraph
            continue

        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        current = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            candidate = sentence if not current else f"{current} {sentence}"
            if len(candidate) <= max_chars:
                current = candidate
                continue
            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    return chunks or [text.strip()]


def _normalize_translation_output(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines()).strip()


def _fallback_detect_language_code(text: str) -> str | None:
    lowered = re.sub(r"[^a-zA-ZÀ-ÿ'\s]", " ", text.lower())
    tokens = {token for token in lowered.split() if token}
    english_markers = {"the", "and", "with", "this", "that", "from", "article", "explains"}
    french_markers = {"le", "la", "les", "avec", "dans", "est", "article", "bonjour"}

    english_score = len(tokens & english_markers)
    french_score = len(tokens & french_markers)

    if english_score > french_score:
        return "en"
    if french_score > english_score:
        return "fr"
    return None
