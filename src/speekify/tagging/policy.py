from __future__ import annotations

from dataclasses import dataclass
import re

from speekify.tagging.config import SUPERTONE_BREATH_TAG, SUPERTONE_SIGH_TAG, TaggingConfig
from speekify.tagging.sentiment import SentimentResult
from speekify.tagging.text import SentenceSpan, TextDocument

SUPERTONE_TAG_RE = re.compile(r"<(?:breath|sigh)>", re.IGNORECASE)
SERIOUS_NEGATIVE_TERMS = {
    "crise",
    "décès",
    "guerre",
    "mort",
    "morts",
    "tragédie",
    "tragedy",
    "war",
    "dead",
    "death",
    "fatal",
    "crisis",
}


@dataclass(frozen=True)
class TagInsertion:
    index: int
    tag: str
    sentence_index: int
    reason: str


class TaggingPolicy:
    def __init__(self, config: TaggingConfig | None = None) -> None:
        self.config = config or TaggingConfig()

    def plan(
        self,
        document: TextDocument,
        sentiments: tuple[SentimentResult, ...] = (),
    ) -> tuple[TagInsertion, ...]:
        if not self.config.enabled or len(document.text) < self.config.min_text_chars_for_tags:
            return ()

        sentiment_by_sentence = {result.sentence_index: result for result in sentiments}
        existing_tags = tuple(SUPERTONE_TAG_RE.finditer(document.text))
        breath_budget = max(0, len(document.text) // self.config.breath_chars_per_tag)
        breath_budget -= sum(1 for tag in existing_tags if tag.group(0).lower() == SUPERTONE_BREATH_TAG)
        if breath_budget <= 0:
            return ()

        insertions: list[TagInsertion] = []
        paragraph_counts = dict.fromkeys((paragraph.index for paragraph in document.paragraphs), 0)
        last_inserted_at = -self.config.min_chars_between_tags
        sigh_count = sum(1 for tag in existing_tags if tag.group(0).lower() == SUPERTONE_SIGH_TAG)

        for sentence in document.sentences:
            if len(insertions) >= breath_budget + self.config.max_sighs:
                break
            if not self._can_insert_at(document, sentence, existing_tags, last_inserted_at):
                continue
            if paragraph_counts.get(sentence.paragraph_index, 0) >= self.config.max_breaths_per_paragraph:
                continue

            sentiment = sentiment_by_sentence.get(sentence.index)
            tag = self._choose_tag(document, sentence, sentiment, sigh_count=sigh_count)
            if tag is None:
                continue

            if tag == SUPERTONE_SIGH_TAG:
                sigh_count += 1
            else:
                if sum(1 for insertion in insertions if insertion.tag == SUPERTONE_BREATH_TAG) >= breath_budget:
                    continue
            insertions.append(
                TagInsertion(
                    index=sentence.end,
                    tag=tag,
                    sentence_index=sentence.index,
                    reason=self._reason_for_tag(document, sentence, tag, sentiment),
                )
            )
            paragraph_counts[sentence.paragraph_index] = paragraph_counts.get(
                sentence.paragraph_index,
                0,
            ) + 1
            last_inserted_at = sentence.end

        return tuple(insertions)

    def _can_insert_at(
        self,
        document: TextDocument,
        sentence: SentenceSpan,
        existing_tags: tuple[re.Match[str], ...],
        last_inserted_at: int,
    ) -> bool:
        if len(document.text) - sentence.end < self.config.min_chars_after_tag:
            return False
        if sentence.end - last_inserted_at < self.config.min_chars_between_tags:
            return False
        if not _ends_like_complete_sentence(sentence.slice(document.text)):
            return False
        return not any(abs(tag.start() - sentence.end) < self.config.min_chars_between_tags for tag in existing_tags)

    def _choose_tag(
        self,
        document: TextDocument,
        sentence: SentenceSpan,
        sentiment: SentimentResult | None,
        *,
        sigh_count: int,
    ) -> str | None:
        if self._should_sigh(document, sentence, sentiment, sigh_count=sigh_count):
            return SUPERTONE_SIGH_TAG
        if self._should_breathe(document, sentence):
            return SUPERTONE_BREATH_TAG
        return None

    def _should_breathe(self, document: TextDocument, sentence: SentenceSpan) -> bool:
        if sentence.length >= self.config.min_sentence_chars_for_breath:
            return True

        paragraph = document.paragraphs[sentence.paragraph_index]
        return sentence.end == paragraph.end and paragraph.length >= self.config.min_paragraph_chars_for_breath

    def _should_sigh(
        self,
        document: TextDocument,
        sentence: SentenceSpan,
        sentiment: SentimentResult | None,
        *,
        sigh_count: int,
    ) -> bool:
        if not self.config.enable_sigh or sigh_count >= self.config.max_sighs:
            return False
        if sentiment is None or sentiment.label != "negative":
            return False
        if sentiment.confidence < self.config.negative_sigh_threshold:
            return False
        lowered = sentence.slice(document.text).lower()
        return any(term in lowered for term in SERIOUS_NEGATIVE_TERMS)

    def _reason_for_tag(
        self,
        document: TextDocument,
        sentence: SentenceSpan,
        tag: str,
        sentiment: SentimentResult | None,
    ) -> str:
        if tag == SUPERTONE_SIGH_TAG:
            return "negative_sentiment"
        if sentence.length >= self.config.min_sentence_chars_for_breath:
            return "long_sentence"
        if sentiment is not None and sentiment.confidence >= self.config.sentiment_confidence_threshold:
            return f"sentiment_{sentiment.label}"
        return "paragraph_boundary"


def _ends_like_complete_sentence(text: str) -> bool:
    return text.rstrip().endswith((".", "!", "?", "…", '"', "'", ")", "]"))