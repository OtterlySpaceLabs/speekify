from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from speekify.config import MODEL_NAME

try:
    from supertonic import TTS
    from supertonic.config import MAX_TEXT_LENGTH as SUPERTONIC_MAX_TEXT_LENGTH
    from supertonic.utils import chunk_text as supertonic_chunk_text
except ImportError:  # pragma: no cover - exercised only when dependency is absent.
    TTS = None  # type: ignore[assignment]
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
        if self.reformatted:
            notes.append("texte reformate automatiquement")
        if self.removed_character_count:
            preview = ", ".join(repr(char) for char in self.removed_characters[:6])
            suffix = ", ..." if len(self.removed_characters) > 6 else ""
            notes.append(
                f"{self.removed_character_count} caractere(s) supprime(s): {preview}{suffix}"
            )
        return notes


@dataclass(frozen=True)
class SynthesisArtifact:
    wav: Any
    duration_seconds: float
    batch_count: int
    prepared_text: PreparedText

    def summary_notes(self) -> list[str]:
        notes: list[str] = []
        if self.batch_count > 1:
            notes.append(f"batch auto: {self.batch_count}")
        notes.extend(self.prepared_text.summary_notes())
        return notes


class SupertonicSynthesizer:
    def __init__(self, engine: Any | None = None) -> None:
        self._engine = engine

    @property
    def engine(self) -> Any:
        if self._engine is None:
            if TTS is None:
                raise RuntimeError(
                    "Le package supertonic n'est pas disponible. Lancez `uv sync`."
                )
            self._engine = TTS(model=MODEL_NAME)
        return self._engine

    def prepare_text(self, text: str) -> PreparedText:
        original_text = text.strip()
        if not original_text:
            raise ValueError("Le texte ne peut pas etre vide.")

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
                    "Le nettoyage automatique n'a pas suffi. Caracteres restants non supportes: "
                    f"{remaining_display}"
                )

        if not prepared_text.strip():
            raise ValueError(
                "Le texte ne contient plus de contenu exploitable apres nettoyage automatique."
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
    ) -> list[str]:
        if max_batch_length < 10:
            raise ValueError("La taille maximale d'un batch doit etre au moins 10 caracteres.")

        if len(text) <= max_batch_length:
            return [text]

        if supertonic_chunk_text is not None:
            initial_batches = supertonic_chunk_text(text, max_batch_length)
        else:  # pragma: no cover - fallback only used without supertonic installed.
            initial_batches = [text]

        batches: list[str] = []
        for batch in initial_batches:
            batches.extend(self._split_overlong_batch(batch, max_batch_length))

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
        style = self.engine.get_voice_style(voice)
        batches = self.split_text_into_batches(prepared_text.text, max_batch_length=max_batch_length)

        wav_list: list[np.ndarray] = []
        duration_seconds = 0.0

        for batch in batches:
            wav, duration = self.engine.synthesize(
                batch,
                voice_style=style,
                lang=lang,
                total_steps=steps,
                speed=speed,
                silence_duration=silence_duration,
            )
            wav_list.append(wav)
            duration_seconds += self._duration_to_float(duration)

        merged_wav = self._merge_batches(wav_list, silence_duration=silence_duration)
        duration_seconds += silence_duration * max(0, len(wav_list) - 1)

        return SynthesisArtifact(
            wav=merged_wav,
            duration_seconds=duration_seconds,
            batch_count=len(wav_list),
            prepared_text=prepared_text,
        )

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

    def _merge_batches(self, wav_list: list[np.ndarray], silence_duration: float) -> np.ndarray:
        if not wav_list:
            raise RuntimeError("Aucun audio n'a ete genere.")
        if len(wav_list) == 1:
            return wav_list[0]

        sample_rate = getattr(self.engine, "sample_rate", 24_000)
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
