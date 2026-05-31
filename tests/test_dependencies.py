from __future__ import annotations

from speekify.dependencies import (
    CachedGenerationDependencyFactory,
    GenerationDependencyFactories,
    build_generation_dependencies,
)
from speekify.tagging import TaggingConfig


class FakeSentimentAnalyzer:
    def analyze(self, document):
        return ()


def test_cached_generation_dependency_factory_reuses_heavy_dependencies() -> None:
    synthesizers: list[object] = []
    translators: list[object] = []
    sentiment_analyzers: list[FakeSentimentAnalyzer] = []

    def build_synthesizer() -> object:
        synthesizer = object()
        synthesizers.append(synthesizer)
        return synthesizer

    def build_translator() -> object:
        translator = object()
        translators.append(translator)
        return translator

    def build_sentiment_analyzer() -> FakeSentimentAnalyzer:
        sentiment_analyzer = FakeSentimentAnalyzer()
        sentiment_analyzers.append(sentiment_analyzer)
        return sentiment_analyzer

    cache = CachedGenerationDependencyFactory(
        GenerationDependencyFactories(
            synthesizer_factory=build_synthesizer,
            translator_factory=build_translator,
            sentiment_analyzer_factory=build_sentiment_analyzer,
        )
    )

    first = cache.build(TaggingConfig(use_sentiment=True))
    second = cache.build(TaggingConfig(use_sentiment=True))
    rules_only = cache.build(TaggingConfig(use_sentiment=False))

    assert first.synthesizer is second.synthesizer is rules_only.synthesizer
    assert first.translator is second.translator is rules_only.translator
    assert first.tagger.sentiment_analyzer is second.tagger.sentiment_analyzer
    assert len(synthesizers) == 1
    assert len(translators) == 1
    assert len(sentiment_analyzers) == 1


def test_build_generation_dependencies_accepts_custom_tagger_factory() -> None:
    fake_tagger = object()
    sentiment_calls = 0

    def build_sentiment_analyzer() -> FakeSentimentAnalyzer:
        nonlocal sentiment_calls
        sentiment_calls += 1
        return FakeSentimentAnalyzer()

    dependencies = build_generation_dependencies(
        TaggingConfig(use_sentiment=True),
        factories=GenerationDependencyFactories(
            synthesizer_factory=object,
            translator_factory=object,
            sentiment_analyzer_factory=build_sentiment_analyzer,
        ),
        tagger_factory=lambda tagging_config: fake_tagger,
    )

    assert dependencies.tagger is fake_tagger
    assert sentiment_calls == 0