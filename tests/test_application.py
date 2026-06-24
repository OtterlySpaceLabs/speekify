from __future__ import annotations

import asyncio
import logging

from speekify.application import (
    build_generation_request,
    run_generation,
    run_inspection,
)
from speekify.dependencies import GenerationDependencies
from speekify.extract import ExtractedContent
from speekify.tts import PreparedText, SynthesisArtifact
from speekify.workflow import GenerationInspection, GenerationResult


def test_build_generation_request_normalizes_without_user_config(tmp_path) -> None:
    request = build_generation_request(
        source_text="  Bonjour le monde  ",
        is_url_mode=False,
        title="  Recap  ",
        voice="m1",
        custom_style_path=None,
        language_code="FR",
        speed=1.0,
        steps=12,
        max_chunk_length=200,
        silence_duration=0.1,
        english_islands=False,
        english_lexicon_path=str(tmp_path / "english.txt"),
        output_dir=str(tmp_path),
        use_user_config=False,
    )

    assert request.source_text == "Bonjour le monde"
    assert request.title == "Recap"
    assert request.voice == "M1"
    assert request.language_code == "fr"
    assert request.output_dir == tmp_path


def test_run_generation_uses_built_dependencies(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}
    expected_result = GenerationResult(
        output_path=tmp_path / "generated.wav",
        artifact=SynthesisArtifact(
            wav="wav",
            duration_seconds=0.5,
            batch_count=1,
            prepared_text=PreparedText(
                original_text="Bonjour",
                text="Bonjour",
                reformatted=False,
                removed_characters=(),
                removed_character_count=0,
            ),
        ),
        content=ExtractedContent(text="Bonjour"),
    )

    async def fake_generate_audio(request, **kwargs):
        captured["request"] = request
        captured.update(kwargs)
        return expected_result

    monkeypatch.setattr("speekify.application.generate_audio", fake_generate_audio)

    request = build_generation_request(
        source_text="Bonjour",
        is_url_mode=False,
        title="",
        voice="M5",
        custom_style_path=None,
        language_code="fr",
        speed=0.98,
        steps=10,
        max_chunk_length=None,
        silence_duration=0.25,
        english_islands=True,
        english_lexicon_path=None,
        output_dir=str(tmp_path),
        use_user_config=False,
    )
    logger = logging.getLogger("test-run-generation")
    synthesizer = object()
    translator = object()

    def fake_build_dependencies(*, cached: bool = False) -> GenerationDependencies:
        return GenerationDependencies(
            synthesizer=synthesizer,
            translator=translator,
        )

    monkeypatch.setattr("speekify.application.build_dependencies", fake_build_dependencies)

    result = asyncio.run(run_generation(request, logger=logger))

    assert result is expected_result
    assert captured["request"] is request
    assert captured["synthesizer"] is synthesizer
    assert captured["translator"] is translator
    assert captured["logger"] is logger


def test_run_inspection_uses_built_dependencies(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}
    expected_result = GenerationInspection(
        output_path=tmp_path / "preview.wav",
        title="Preview",
        content=ExtractedContent(text="Bonjour"),
        prepared_text=PreparedText(
            original_text="Bonjour",
            text="Bonjour",
            reformatted=False,
            removed_characters=(),
            removed_character_count=0,
        ),
        source_mode="text",
    )

    async def fake_inspect_generation(request, **kwargs):
        captured["request"] = request
        captured.update(kwargs)
        return expected_result

    monkeypatch.setattr("speekify.application.inspect_generation", fake_inspect_generation)

    request = build_generation_request(
        source_text="Bonjour",
        is_url_mode=False,
        title="Preview",
        voice="M5",
        custom_style_path=None,
        language_code="fr",
        speed=0.98,
        steps=10,
        max_chunk_length=None,
        silence_duration=0.25,
        english_islands=True,
        english_lexicon_path=None,
        output_dir=str(tmp_path),
        use_user_config=False,
    )
    logger = logging.getLogger("test-run-inspection")
    translator = object()

    def fake_build_dependencies(*, cached: bool = False) -> GenerationDependencies:
        return GenerationDependencies(
            synthesizer=object(),
            translator=translator,
        )

    monkeypatch.setattr("speekify.application.build_dependencies", fake_build_dependencies)

    result = asyncio.run(run_inspection(request, logger=logger))

    assert result is expected_result
    assert captured["request"] is request
    assert captured["translator"] is translator
    assert captured["logger"] is logger