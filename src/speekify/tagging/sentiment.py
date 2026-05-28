from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol

from speekify.tagging.text import TextDocument


@dataclass(frozen=True)
class SentimentResult:
    sentence_index: int
    label: str
    confidence: float
    scores: Mapping[str, float] = field(default_factory=dict)


class SentimentAnalyzer(Protocol):
    def analyze(self, document: TextDocument) -> tuple[SentimentResult, ...]: ...


class NullSentimentAnalyzer:
    def analyze(self, document: TextDocument) -> tuple[SentimentResult, ...]:
        return ()