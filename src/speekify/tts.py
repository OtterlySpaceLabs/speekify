from __future__ import annotations

from dataclasses import dataclass
import inspect
from pathlib import Path
from typing import Any

import numpy as np

from speekify.config import MODEL_NAME, SUPPORTED_TTS_LANGUAGES

try:
    from supertonic import TTS
    from supertonic.config import (
        DEFAULT_MAX_CHUNK_LENGTH,
        DEFAULT_MAX_CHUNK_LENGTH_KO,
        MAX_TEXT_LENGTH as SUPERTONIC_MAX_TEXT_LENGTH,
    )
    from supertonic.utils import chunk_text as supertonic_chunk_text
except ImportError:  # pragma: no cover - exercised only when dependency is absent.
    TTS = None  # type: ignore[assignment]
    DEFAULT_MAX_CHUNK_LENGTH = 300
    DEFAULT_MAX_CHUNK_LENGTH_KO = 120
    SUPERTONIC_MAX_TEXT_LENGTH = 100_000
    supertonic_chunk_text = None


@dataclass(frozen=True)
class PreparedText:
    original_text: str
    text: str
    reformatted: bool
    removed_characters: tuple[str, ...]
    removed_character_count: int

    @property
    def changed(self) -> bool:
        return self.reformatted or self.removed_character_count > 0

    def summary_notes(self) -> list[str]:
        notes: list[str] = []
        if self.removed_character_count:
            preview = ", ".join(repr(char) for char in self.removed_characters[:6])
            suffix = ", ..." if len(self.removed_characters) > 6 else ""
            notes.append(
                f"{self.removed_character_count} character(s) removed: {preview}{suffix}"
            )
        return notes


@dataclass(frozen=True)
class SynthesisArtifact:
    wav: Any
    duration_seconds: float
    batch_count: int
    prepared_text: PreparedText

    def summary_notes(self) -> list[str]:
        return self.prepared_text.summary_notes()


class SupertonicSynthesizer:
    def __init__(self, engine: Any | None = None) -> None:
        self._engine = engine

    @property
    def engine(self) -> Any:
        if self._engine is None:
            if TTS is None:
                raise RuntimeError(
                    "The supertonic package is not available. Reinstall Speekify with all dependencies."
                )
            self._engine = TTS(model=MODEL_NAME)
        return self._engine

    def prepare_text(self, text: str) -> PreparedText:
        original_text = text.strip()
        if not original_text:
            raise ValueError("Text cannot be empty.")

        prepared_text = self._preprocess_text(original_text)
        is_valid, unsupported = self._validate_text(prepared_text)

        removed_characters: tuple[str, ...] = ()
        removed_character_count = 0

        if not is_valid:
            removed_characters = tuple(sorted(set(unsupported)))
            removed_character_count = sum(
                1 for char in prepared_text if char in set(removed_characters)
            )
            prepared_text = "".join(
                char for char in prepared_text if char not in set(removed_characters)
            )
            prepared_text = self._preprocess_text(prepared_text)

            is_valid, remaining_unsupported = self._validate_text(prepared_text)
            if not is_valid:
                remaining_display = ", ".join(repr(char) for char in remaining_unsupported[:20])
                if len(remaining_unsupported) > 20:
                    remaining_display += ", ..."
                raise ValueError(
                    "Automatic cleanup was not enough. Unsupported characters remaining: "
                    f"{remaining_display}"
                )

        if not prepared_text.strip():
            raise ValueError(
                "The text no longer contains usable content after automatic cleanup."
            )

        return PreparedText(
            original_text=original_text,
            text=prepared_text,
            reformatted=prepared_text != original_text,
            removed_characters=removed_characters,
            removed_character_count=removed_character_count,
        )

    def split_text_into_batches(
        self,
        text: str,
        max_batch_length: int = SUPERTONIC_MAX_TEXT_LENGTH,
        preferred_chunk_length: int | None = None,
    ) -> list[str]:
        if max_batch_length < 10:
            raise ValueError("Maximum batch size must be at least 10 characters.")

        split_limit = max_batch_length
        if preferred_chunk_length is not None:
            split_limit = min(split_limit, preferred_chunk_length)

        if supertonic_chunk_text is not None:
            initial_batches = supertonic_chunk_text(text, split_limit)
        else:  # pragma: no cover - fallback only used without supertonic installed.
            initial_batches = [text]

        batches: list[str] = []
        for batch in initial_batches:
            batches.extend(self._split_overlong_batch(batch, split_limit))

        return [batch for batch in batches if batch.strip()]

    def synthesize_to_file(
        self,
        *,
        text: str,
        output_path: Path,
        voice: str,
        lang: str,
        steps: int,
        speed: float,
        silence_duration: float,
        max_batch_length: int = SUPERTONIC_MAX_TEXT_LENGTH,
    ) -> SynthesisArtifact:
        prepared_text = self.prepare_text(text)
        artifact = self.synthesize_prepared_text(
            prepared_text=prepared_text,
            voice=voice,
            lang=lang,
            steps=steps,
            speed=speed,
            silence_duration=silence_duration,
            max_batch_length=max_batch_length,
        )
        self.save_audio(artifact.wav, output_path)
        return artifact

    def synthesize(
        self,
        *,
        text: str,
        voice: str,
        lang: str,
        steps: int,
        speed: float,
        silence_duration: float,
        max_batch_length: int = SUPERTONIC_MAX_TEXT_LENGTH,
    ) -> tuple[Any, float]:
        artifact = self.synthesize_prepared_text(
            prepared_text=self.prepare_text(text),
            voice=voice,
            lang=lang,
            steps=steps,
            speed=speed,
            silence_duration=silence_duration,
            max_batch_length=max_batch_length,
        )
        return artifact.wav, artifact.duration_seconds

    def synthesize_prepared_text(
        self,
        *,
        prepared_text: PreparedText,
        voice: str,
        lang: str,
        steps: int,
        speed: float,
        silence_duration: float,
        max_batch_length: int = SUPERTONIC_MAX_TEXT_LENGTH,
    ) -> SynthesisArtifact:
        normalized_lang = self.validate_language_code(lang)
        engine = self.engine
        style = engine.get_voice_style(voice)
        max_chunk_length = self._default_chunk_length(normalized_lang)
        accepts_max_chunk_length = self._engine_accepts_max_chunk_length(engine)
        batches = self.split_text_into_batches(
            prepared_text.text,
            max_batch_length=max_batch_length,
            preferred_chunk_length=max_chunk_length,
        )

        wav_list: list[np.ndarray] = []
        duration_seconds = 0.0

        for batch in batches:
            synthesize_kwargs = {
                "voice_style": style,
                "lang": normalized_lang,
                "total_steps": steps,
                "speed": speed,
                "silence_duration": silence_duration,
            }
            if accepts_max_chunk_length:
                synthesize_kwargs["max_chunk_length"] = max_chunk_length
            wav, duration = engine.synthesize(batch, **synthesize_kwargs)
            wav_list.append(wav)
            duration_seconds += self._duration_to_float(duration)

        merged_wav = self._merge_batches(
            wav_list,
            silence_duration=silence_duration,
            sample_rate=int(getattr(engine, "sample_rate", 24_000)),
        )
        duration_seconds += silence_duration * max(0, len(wav_list) - 1)

        return SynthesisArtifact(
            wav=merged_wav,
            duration_seconds=duration_seconds,
            batch_count=len(wav_list),
            prepared_text=prepared_text,
        )

    def validate_language_code(self, lang: str) -> str:
        normalized = lang.strip().lower()
        if normalized not in SUPPORTED_TTS_LANGUAGES:
            supported = ", ".join(SUPPORTED_TTS_LANGUAGES)
            raise ValueError(
                f"Unsupported TTS language: {lang!r}. Available languages: {supported}"
            )
        return normalized

    def save_audio(self, wav: Any, output_path: Path) -> None:
        self.engine.save_audio(wav, str(output_path))

    def _preprocess_text(self, text: str) -> str:
        text_processor = self._text_processor
        if text_processor is not None and hasattr(text_processor, "_preprocess_text"):
            return str(text_processor._preprocess_text(text)).strip()
        return text.strip()

    def _validate_text(self, text: str) -> tuple[bool, list[str]]:
        text_processor = self._text_processor
        if text_processor is not None and hasattr(text_processor, "validate_text"):
            return text_processor.validate_text(text)
        return True, []

    @property
    def _text_processor(self) -> Any | None:
        return getattr(getattr(self.engine, "model", None), "text_processor", None)

    def _default_chunk_length(self, lang: str) -> int:
        if lang == "ko":
            return DEFAULT_MAX_CHUNK_LENGTH_KO
        return DEFAULT_MAX_CHUNK_LENGTH

    def _engine_accepts_max_chunk_length(self, engine: Any | None = None) -> bool:
        synthesize = getattr(engine or self.engine, "synthesize")
        return "max_chunk_length" in inspect.signature(synthesize).parameters

    def _split_overlong_batch(self, text: str, max_batch_length: int) -> list[str]:
        remaining = text.strip()
        if len(remaining) <= max_batch_length:
            return [remaining]

        batches: list[str] = []
        while len(remaining) > max_batch_length:
            split_at = max(remaining.rfind("\n", 0, max_batch_length), remaining.rfind(" ", 0, max_batch_length))
            if split_at <= 0:
                split_at = max_batch_length
            candidate = remaining[:split_at].strip()
            if candidate:
                batches.append(candidate)
            remaining = remaining[split_at:].strip()

        if remaining:
            batches.append(remaining)
        return batches

    def _merge_batches(
        self,
        wav_list: list[np.ndarray],
        silence_duration: float,
        sample_rate: int = 24_000,
    ) -> np.ndarray:
        if not wav_list:
            raise RuntimeError("No audio was generated.")
        if len(wav_list) == 1:
            return wav_list[0]

        silence = np.zeros((1, int(silence_duration * sample_rate)), dtype=wav_list[0].dtype)
        arrays_to_concat: list[np.ndarray] = []
        for index, wav in enumerate(wav_list):
            arrays_to_concat.append(wav)
            if index < len(wav_list) - 1:
                arrays_to_concat.append(silence)
        return np.concatenate(arrays_to_concat, axis=1)

    def _duration_to_float(self, duration: Any) -> float:
        if isinstance(duration, np.ndarray):
            return float(duration[0])
        if isinstance(duration, (list, tuple)):
            return float(duration[0])
        return float(duration)
