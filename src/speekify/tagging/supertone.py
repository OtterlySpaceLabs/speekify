from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Mapping

from speekify.tagging.config import TaggingConfig
from speekify.tagging.policy import TagInsertion, TaggingPolicy
from speekify.tagging.sentiment import NullSentimentAnalyzer, SentimentAnalyzer
from speekify.tagging.text import TextPreprocessor


@dataclass(frozen=True)
class TaggingResult:
    original_text: str
    text: str
    insertions: tuple[TagInsertion, ...] = ()
    sentiment_used: bool = False
    tag_counts: Mapping[str, int] = field(default_factory=dict)

    @property
    def changed(self) -> bool:
        return self.text != self.original_text


class SupertoneTagger:
    def __init__(
        self,
        *,
        config: TaggingConfig | None = None,
        preprocessor: TextPreprocessor | None = None,
        policy: TaggingPolicy | None = None,
        sentiment_analyzer: SentimentAnalyzer | None = None,
    ) -> None:
        self.config = config or TaggingConfig()
        self.preprocessor = preprocessor or TextPreprocessor()
        self.policy = policy or TaggingPolicy(self.config)
        self.sentiment_analyzer = sentiment_analyzer or NullSentimentAnalyzer()

    def tag(self, text: str, *, language_code: str) -> TaggingResult:
        if not self.config.enabled:
            return TaggingResult(original_text=text, text=text)

        document = self.preprocessor.process(text, language_code=language_code)
        sentiments = ()
        sentiment_used = False
        if self.config.use_sentiment:
            try:
                sentiments = self.sentiment_analyzer.analyze(document)
                sentiment_used = bool(sentiments)
            except Exception:
                if not self.config.fail_open_on_sentiment_error:
                    raise

        insertions = self.policy.plan(document, sentiments)
        tagged_text = _apply_insertions(text, insertions)
        return TaggingResult(
            original_text=text,
            text=tagged_text,
            insertions=insertions,
            sentiment_used=sentiment_used,
            tag_counts=Counter(insertion.tag for insertion in insertions),
        )


def _apply_insertions(text: str, insertions: tuple[TagInsertion, ...]) -> str:
    tagged = text
    for insertion in sorted(insertions, key=lambda item: item.index, reverse=True):
        tagged = f"{tagged[: insertion.index]} {insertion.tag}{tagged[insertion.index :]}"
    return tagged