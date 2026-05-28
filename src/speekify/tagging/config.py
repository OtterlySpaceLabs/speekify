from __future__ import annotations

from dataclasses import dataclass

CARDIFF_SENTIMENT_MODEL_NAME = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
SUPERTONE_BREATH_TAG = "<breath>"
SUPERTONE_SIGH_TAG = "<sigh>"


@dataclass(frozen=True)
class TaggingConfig:
    enabled: bool = True
    use_sentiment: bool = False
    enable_sigh: bool = False
    fail_open_on_sentiment_error: bool = True
    min_text_chars_for_tags: int = 700
    min_sentence_chars_for_breath: int = 180
    min_paragraph_chars_for_breath: int = 420
    min_chars_after_tag: int = 140
    min_chars_between_tags: int = 520
    breath_chars_per_tag: int = 900
    max_breaths_per_paragraph: int = 1
    max_sighs: int = 1
    negative_sigh_threshold: float = 0.92
    sentiment_confidence_threshold: float = 0.85