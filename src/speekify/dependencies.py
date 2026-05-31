from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from speekify.tagging import SentimentAnalyzer, SupertoneTagger, TaggingConfig


def build_synthesizer() -> object:
    from speekify.tts import SupertonicSynthesizer

    return SupertonicSynthesizer()


def build_translator() -> object:
    from speekify.translation import HuggingFaceTranslator

    return HuggingFaceTranslator()


def build_sentiment_analyzer() -> SentimentAnalyzer:
    from speekify.tagging.cardiff import CardiffSentimentAnalyzer

    return CardiffSentimentAnalyzer()


def build_tagger(
    tagging_config: TaggingConfig,
    *,
    sentiment_analyzer: SentimentAnalyzer | None = None,
) -> SupertoneTagger:
    return SupertoneTagger(config=tagging_config, sentiment_analyzer=sentiment_analyzer)


@dataclass(frozen=True)
class GenerationDependencies:
    synthesizer: object
    translator: object
    tagger: object


@dataclass(frozen=True)
class GenerationDependencyFactories:
    synthesizer_factory: Callable[[], object] = build_synthesizer
    translator_factory: Callable[[], object] = build_translator
    sentiment_analyzer_factory: Callable[[], SentimentAnalyzer] = build_sentiment_analyzer


def build_generation_dependencies(
    tagging_config: TaggingConfig,
    *,
    factories: GenerationDependencyFactories | None = None,
    tagger_factory: Callable[[TaggingConfig], object] | None = None,
) -> GenerationDependencies:
    active_factories = factories or GenerationDependencyFactories()
    if tagger_factory is not None:
        tagger = tagger_factory(tagging_config)
    else:
        sentiment_analyzer = None
        if tagging_config.use_sentiment:
            sentiment_analyzer = active_factories.sentiment_analyzer_factory()
        tagger = build_tagger(tagging_config, sentiment_analyzer=sentiment_analyzer)
    return GenerationDependencies(
        synthesizer=active_factories.synthesizer_factory(),
        translator=active_factories.translator_factory(),
        tagger=tagger,
    )


class CachedGenerationDependencyFactory:
    def __init__(self, factories: GenerationDependencyFactories | None = None) -> None:
        self._factories = factories or GenerationDependencyFactories()
        self._synthesizer: object | None = None
        self._translator: object | None = None
        self._sentiment_analyzer: SentimentAnalyzer | None = None

    def build(self, tagging_config: TaggingConfig) -> GenerationDependencies:
        if self._synthesizer is None:
            self._synthesizer = self._factories.synthesizer_factory()
        if self._translator is None:
            self._translator = self._factories.translator_factory()

        sentiment_analyzer = None
        if tagging_config.use_sentiment:
            if self._sentiment_analyzer is None:
                self._sentiment_analyzer = self._factories.sentiment_analyzer_factory()
            sentiment_analyzer = self._sentiment_analyzer

        return GenerationDependencies(
            synthesizer=self._synthesizer,
            translator=self._translator,
            tagger=build_tagger(tagging_config, sentiment_analyzer=sentiment_analyzer),
        )

