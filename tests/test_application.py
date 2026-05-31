from __future__ import annotations

import asyncio
import logging

from speekify.application import (
    build_generation_request,
    build_runtime_dependencies,
    build_tagging_config,
    run_generation,
    run_inspection,
)
from speekify.dependencies import GenerationDependencies, GenerationDependencyFactories
from speekify.extract import ExtractedContent
from speekify.tagging import TaggingConfig
from speekify.tts import PreparedText, SynthesisArtifact
from speekify.workflow import GenerationInspection, GenerationResult


def test_build_runtime_dependencies_uses_injected_factories() -> None:
    synthesizer = object()
    translator = object()
    sentiment_analyzer = object()
    tagger = object()

    factories = GenerationDependencyFactories(
        synthesizer_factory=lambda: synthesizer,
        translator_factory=lambda: translator,
        sentiment_analyzer_factory=lambda: sentiment_analyzer,
    )

    def fake_tagger_factory(tagging_config: TaggingConfig) -> object:
        assert tagging_config.enabled is True
        assert tagging_config.use_sentiment is True
        assert tagging_config.enable_sigh is False
        return tagger

    dependencies = build_runtime_dependencies(
        build_tagging_config(enabled=True, use_sentiment=True, enable_sigh=False),
        dependency_mode="fresh",
        factories=factories,
        tagger_factory=fake_tagger_factory,
    )

    assert dependencies.synthesizer is synthesizer
    assert dependencies.translator is translator
    assert dependencies.tagger is tagger


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
        feed_base_url="https://audio.example.com/speekify/",
        tags=True,
        tag_sentiment=False,
        tag_sigh=True,
        use_user_config=False,
    )

    assert request.source_text == "Bonjour le monde"
    assert request.title == "Recap"
    assert request.voice == "M1"
    assert request.language_code == "fr"
    assert request.output_dir == tmp_path
    assert request.feed_base_url == "https://audio.example.com/speekify"
    assert request.tagging_config.enabled is True
    assert request.tagging_config.use_sentiment is False
    assert request.tagging_config.enable_sigh is True


def test_run_generation_uses_custom_dependency_builder(monkeypatch, tmp_path) -> None:
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
        feed_base_url="",
        tags=True,
        tag_sentiment=True,
        tag_sigh=True,
        use_user_config=False,
    )
    logger = logging.getLogger("test-run-generation")
    synthesizer = object()
    translator = object()
    tagger = object()

    def dependency_builder(tagging_config: TaggingConfig) -> GenerationDependencies:
        assert tagging_config == request.tagging_config
        return GenerationDependencies(
            synthesizer=synthesizer,
            translator=translator,
            tagger=tagger,
        )

    result = asyncio.run(
        run_generation(
            request,
            logger=logger,
            dependency_builder=dependency_builder,
        )
    )

    assert result is expected_result
    assert captured["request"] is request
    assert captured["synthesizer"] is synthesizer
    assert captured["translator"] is translator
    assert captured["tagger"] is tagger
    assert captured["logger"] is logger


def test_run_inspection_uses_custom_dependency_builder(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}
    expected_result = GenerationInspection(
        output_path=tmp_path / "preview.wav",
        feed_path=tmp_path / "speekify-feed.xml",
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
        feed_base_url="",
        tags=True,
        tag_sentiment=False,
        tag_sigh=False,
        use_user_config=False,
    )
    logger = logging.getLogger("test-run-inspection")
    translator = object()
    tagger = object()

    def dependency_builder(tagging_config: TaggingConfig) -> GenerationDependencies:
        assert tagging_config == request.tagging_config
        return GenerationDependencies(
            synthesizer=object(),
            translator=translator,
            tagger=tagger,
        )

    result = asyncio.run(
        run_inspection(
            request,
            logger=logger,
            dependency_builder=dependency_builder,
        )
    )

    assert result is expected_result
    assert captured["request"] is request
    assert captured["translator"] is translator
    assert captured["tagger"] is tagger
    assert captured["logger"] is logger