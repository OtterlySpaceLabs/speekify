from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from speekify.extract import ExtractedContent
from speekify.translation import TranslationResult
from speekify.tts import PreparedText, SynthesisArtifact
from speekify.workflow import GenerationRequest, generate_audio, resolve_content


class NoopTranslator:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def maybe_translate_to_french(self, text: str) -> TranslationResult:
        self.calls.append(text)
        return TranslationResult(
            text=text,
            translated=False,
            source_language="fr",
            target_language="fr",
            original_text=text,
        )


class FrenchTranslator:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def maybe_translate_to_french(self, text: str) -> TranslationResult:
        self.calls.append(text)
        return TranslationResult(
            text="Bonjour tout le monde.",
            translated=True,
            source_language="en",
            target_language="fr",
            original_text=text,
        )


class PermissiveSuccessSynthesizer:
    @property
    def engine(self) -> str:
        return "ready"

    def prepare_text(self, text: str) -> PreparedText:
        return PreparedText(
            original_text=text,
            text="Bonjour monde.",
            reformatted=True,
            removed_characters=("😀",),
            removed_character_count=1,
        )

    def synthesize_prepared_text(
        self,
        *,
        prepared_text: PreparedText,
        voice: str,
        lang: str,
        steps: int,
        speed: float,
        silence_duration: float,
    ) -> SynthesisArtifact:
        assert voice == "M1"
        assert lang == "fr"
        assert steps == 8
        assert speed == 1.05
        assert silence_duration == 0.3
        return SynthesisArtifact(
            wav="wav",
            duration_seconds=2.5,
            batch_count=3,
            prepared_text=prepared_text,
        )

    def save_audio(self, wav: object, output_path: Path) -> None:
        output_path.write_text(str(wav), encoding="utf-8")


def test_resolve_content_autodetects_single_url_input(monkeypatch) -> None:
    captured: dict[str, str] = {}
    statuses: list[str] = []

    async def fake_extract_url(url: str) -> ExtractedContent:
        captured["url"] = url
        return ExtractedContent(text="Contenu extrait", title="Article")

    monkeypatch.setattr("speekify.workflow.extract_url", fake_extract_url)

    content = asyncio.run(
        resolve_content(
            " https://www.faketech.fr/p/le-gros-mytho-danthropic ",
            is_url_mode=False,
            target_language="fr",
            translator=NoopTranslator(),
            logger=logging.getLogger("speekify.tests.workflow"),
            status_callback=statuses.append,
        )
    )

    assert captured["url"] == " https://www.faketech.fr/p/le-gros-mytho-danthropic "
    assert content == ExtractedContent(text="Contenu extrait", title="Article")
    assert statuses == ["extracting URL", "checking language"]


def test_resolve_content_translates_english_text_to_french() -> None:
    translator = FrenchTranslator()
    statuses: list[str] = []

    content = asyncio.run(
        resolve_content(
            "Hello everyone.",
            is_url_mode=False,
            target_language="fr",
            translator=translator,
            logger=logging.getLogger("speekify.tests.workflow"),
            status_callback=statuses.append,
        )
    )

    assert content == ExtractedContent(text="Bonjour tout le monde.")
    assert translator.calls == ["Hello everyone."]
    assert statuses == ["checking language", "translating to French"]


def test_generate_audio_returns_cleanup_and_batch_summary(tmp_path) -> None:
    statuses: list[str] = []

    result = asyncio.run(
        generate_audio(
            GenerationRequest(
                source_text="Bonjour 😀 monde",
                voice="M1",
                language_code="fr",
                speed=1.05,
                steps=8,
                output_dir=tmp_path,
            ),
            synthesizer=PermissiveSuccessSynthesizer(),
            translator=NoopTranslator(),
            logger=logging.getLogger("speekify.tests.workflow"),
            status_callback=statuses.append,
        )
    )

    assert result.output_path.read_text(encoding="utf-8") == "wav"
    assert result.artifact.duration_seconds == 2.5
    assert result.artifact.summary_notes() == [
        "batch auto: 3",
        "text reformatted automatically",
        "1 character(s) removed: '😀'",
    ]
    assert statuses == [
        "checking language",
        "preparing text",
        "loading model",
        "synthesizing",
        "saving",
    ]