from __future__ import annotations

from speekify import dependencies
from speekify.dependencies import build_dependencies
from speekify.tagging import TaggingConfig


class FakeSentimentAnalyzer:
    def analyze(self, document):
        return ()


def _clear_caches() -> None:
    dependencies._cached_synthesizer.cache_clear()
    dependencies._cached_translator.cache_clear()
    dependencies._cached_sentiment_analyzer.cache_clear()


def test_build_dependencies_cached_reuses_heavy_dependencies(monkeypatch) -> None:
    synthesizers: list[object] = []
    translators: list[object] = []
    sentiment_analyzers: list[FakeSentimentAnalyzer] = []

    monkeypatch.setattr(
        "speekify.dependencies.build_synthesizer",
        lambda: synthesizers.append(object()) or synthesizers[-1],
    )
    monkeypatch.setattr(
        "speekify.dependencies.build_translator",
        lambda: translators.append(object()) or translators[-1],
    )
    monkeypatch.setattr(
        "speekify.dependencies.build_sentiment_analyzer",
        lambda: sentiment_analyzers.append(FakeSentimentAnalyzer()) or sentiment_analyzers[-1],
    )
    _clear_caches()

    first = build_dependencies(TaggingConfig(use_sentiment=True), cached=True)
    second = build_dependencies(TaggingConfig(use_sentiment=True), cached=True)
    rules_only = build_dependencies(TaggingConfig(use_sentiment=False), cached=True)

    assert first.synthesizer is second.synthesizer is rules_only.synthesizer
    assert first.translator is second.translator is rules_only.translator
    assert first.tagger.sentiment_analyzer is second.tagger.sentiment_analyzer
    assert len(synthesizers) == 1
    assert len(translators) == 1
    assert len(sentiment_analyzers) == 1


def test_build_dependencies_fresh_builds_each_call(monkeypatch) -> None:
    sentiment_calls = 0

    def build_sentiment_analyzer() -> FakeSentimentAnalyzer:
        nonlocal sentiment_calls
        sentiment_calls += 1
        return FakeSentimentAnalyzer()

    monkeypatch.setattr("speekify.dependencies.build_synthesizer", object)
    monkeypatch.setattr("speekify.dependencies.build_translator", object)
    monkeypatch.setattr("speekify.dependencies.build_sentiment_analyzer", build_sentiment_analyzer)

    first = build_dependencies(TaggingConfig(use_sentiment=False))
    second = build_dependencies(TaggingConfig(use_sentiment=False))

    assert first.synthesizer is not second.synthesizer
    assert sentiment_calls == 0

    with_sentiment = build_dependencies(TaggingConfig(use_sentiment=True))
    assert sentiment_calls == 1
    assert isinstance(with_sentiment.tagger.sentiment_analyzer, FakeSentimentAnalyzer)
