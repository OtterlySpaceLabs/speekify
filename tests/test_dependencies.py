from __future__ import annotations

from speekify import dependencies
from speekify.dependencies import build_dependencies


def _clear_caches() -> None:
    dependencies._cached_synthesizer.cache_clear()
    dependencies._cached_translator.cache_clear()


def test_build_dependencies_cached_reuses_heavy_dependencies(monkeypatch) -> None:
    synthesizers: list[object] = []
    translators: list[object] = []

    monkeypatch.setattr(
        "speekify.dependencies.build_synthesizer",
        lambda: synthesizers.append(object()) or synthesizers[-1],
    )
    monkeypatch.setattr(
        "speekify.dependencies.build_translator",
        lambda: translators.append(object()) or translators[-1],
    )
    _clear_caches()

    first = build_dependencies(cached=True)
    second = build_dependencies(cached=True)

    assert first.synthesizer is second.synthesizer
    assert first.translator is second.translator
    assert len(synthesizers) == 1
    assert len(translators) == 1


def test_build_dependencies_fresh_builds_each_call(monkeypatch) -> None:
    monkeypatch.setattr("speekify.dependencies.build_synthesizer", object)
    monkeypatch.setattr("speekify.dependencies.build_translator", object)

    first = build_dependencies()
    second = build_dependencies()

    assert first.synthesizer is not second.synthesizer
    assert first.translator is not second.translator
