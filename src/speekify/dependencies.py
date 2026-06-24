from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

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


# ponytail: lru_cache memoizes the heavy model loads so the long-lived MCP server
# reuses them across calls; call <fn>.cache_clear() if a fresh load is ever needed.
@lru_cache(maxsize=1)
def _cached_synthesizer() -> object:
    return build_synthesizer()


@lru_cache(maxsize=1)
def _cached_translator() -> object:
    return build_translator()


@lru_cache(maxsize=1)
def _cached_sentiment_analyzer() -> SentimentAnalyzer:
    return build_sentiment_analyzer()


def build_dependencies(
    tagging_config: TaggingConfig,
    *,
    cached: bool = False,
) -> GenerationDependencies:
    synthesizer = _cached_synthesizer() if cached else build_synthesizer()
    translator = _cached_translator() if cached else build_translator()
    sentiment_analyzer = None
    if tagging_config.use_sentiment:
        sentiment_analyzer = (
            _cached_sentiment_analyzer() if cached else build_sentiment_analyzer()
        )
    return GenerationDependencies(
        synthesizer=synthesizer,
        translator=translator,
        tagger=build_tagger(tagging_config, sentiment_analyzer=sentiment_analyzer),
    )
