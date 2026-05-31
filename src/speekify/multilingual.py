from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


DEFAULT_FRENCH_ENGLISH_LEXICON: tuple[str, ...] = (
    "AI",
    "API",
    "LLM",
    "LLM powered app",
    "prompt engineering",
    "machine learning",
    "deep learning",
    "open source",
    "fine-tuning",
    "benchmark",
    "backend",
    "dataset",
    "embedding",
    "frontend",
    "inference",
    "prompt",
    "token",
    "workflow",
)


@dataclass(frozen=True)
class LanguageSegment:
    text: str
    lang: str


def load_english_lexicon(path: Path) -> tuple[str, ...]:
    terms: list[str] = []
    for line in path.expanduser().read_text(encoding="utf-8").splitlines():
        term = line.strip()
        if term and not term.startswith("#"):
            terms.append(term)
    return tuple(terms)


class FrenchEnglishIslandSegmenter:
    def __init__(self, english_terms: tuple[str, ...] | None = None) -> None:
        terms = english_terms if english_terms is not None else DEFAULT_FRENCH_ENGLISH_LEXICON
        self._patterns = tuple(self._compile_patterns(terms))

    def segment(
        self, text: str, *, default_lang: str = "fr", english_lang: str = "en"
    ) -> tuple[LanguageSegment, ...]:
        if default_lang != "fr" or not self._patterns:
            return (LanguageSegment(text=text, lang=default_lang),)

        matches = self._find_non_overlapping_matches(text)
        if not matches:
            return (LanguageSegment(text=text, lang=default_lang),)

        segments: list[LanguageSegment] = []
        cursor = 0
        for start, end in matches:
            if cursor < start:
                self._append_segment(segments, text[cursor:start], default_lang)
            self._append_segment(segments, text[start:end], english_lang)
            cursor = end
        if cursor < len(text):
            self._append_segment(segments, text[cursor:], default_lang)
        return tuple(segment for segment in segments if segment.text)

    def _find_non_overlapping_matches(self, text: str) -> list[tuple[int, int]]:
        candidates: list[tuple[int, int]] = []
        for pattern in self._patterns:
            candidates.extend((match.start(), match.end()) for match in pattern.finditer(text))

        candidates.sort(key=lambda span: (span[0], -(span[1] - span[0])))
        selected: list[tuple[int, int]] = []
        occupied_until = -1
        for start, end in candidates:
            if start < occupied_until:
                continue
            selected.append((start, end))
            occupied_until = end
        return selected

    def _compile_patterns(self, terms: tuple[str, ...]) -> list[re.Pattern[str]]:
        deduped_terms = sorted(
            {term.strip() for term in terms if term.strip()}, key=len, reverse=True
        )
        patterns: list[re.Pattern[str]] = []
        for term in deduped_terms:
            escaped = re.escape(term).replace(r"\ ", r"\s+")
            flags = 0 if self._is_uppercase_acronym(term) else re.IGNORECASE
            patterns.append(re.compile(rf"(?<![\w]){escaped}(?![\w])", flags))
        return patterns

    def _is_uppercase_acronym(self, term: str) -> bool:
        return term.isupper() and term.isalpha() and len(term) <= 6

    def _append_segment(self, segments: list[LanguageSegment], text: str, lang: str) -> None:
        if not text:
            return
        if segments and segments[-1].lang == lang:
            previous = segments[-1]
            segments[-1] = LanguageSegment(text=f"{previous.text}{text}", lang=lang)
            return
        segments.append(LanguageSegment(text=text, lang=lang))
