from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache


def build_synthesizer() -> object:
    from speekify.tts import SupertonicSynthesizer

    return SupertonicSynthesizer()


def build_translator() -> object:
    from speekify.translation import HuggingFaceTranslator

    return HuggingFaceTranslator()


@dataclass(frozen=True)
class GenerationDependencies:
    synthesizer: object
    translator: object


# ponytail: lru_cache memoizes the heavy model loads so the long-lived MCP server
# reuses them across calls; call <fn>.cache_clear() if a fresh load is ever needed.
@lru_cache(maxsize=1)
def _cached_synthesizer() -> object:
    return build_synthesizer()


@lru_cache(maxsize=1)
def _cached_translator() -> object:
    return build_translator()


def build_dependencies(*, cached: bool = False) -> GenerationDependencies:
    return GenerationDependencies(
        synthesizer=_cached_synthesizer() if cached else build_synthesizer(),
        translator=_cached_translator() if cached else build_translator(),
    )
