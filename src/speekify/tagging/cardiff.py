from __future__ import annotations

from typing import Any

from speekify.tagging.config import CARDIFF_SENTIMENT_MODEL_NAME
from speekify.tagging.sentiment import SentimentResult
from speekify.tagging.text import TextDocument


class CardiffSentimentAnalyzer:
    def __init__(
        self,
        model_name: str = CARDIFF_SENTIMENT_MODEL_NAME,
        *,
        batch_size: int = 8,
        max_length: int = 256,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length
        self._backend: tuple[Any, Any, Any, str] | None = None

    def analyze(self, document: TextDocument) -> tuple[SentimentResult, ...]:
        sentences = [sentence.slice(document.text) for sentence in document.sentences]
        if not sentences:
            return ()

        torch, tokenizer, model, device = self.backend
        results: list[SentimentResult] = []
        labels = _labels_from_model(model)

        for offset in range(0, len(sentences), self.batch_size):
            batch = sentences[offset : offset + self.batch_size]
            inputs = tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.max_length,
            )
            inputs = {name: value.to(device) for name, value in inputs.items()}

            with torch.no_grad():
                logits = model(**inputs).logits
            probabilities = torch.softmax(logits, dim=-1).detach().cpu().tolist()

            for index, sentence_scores in enumerate(probabilities):
                score_map = {
                    _normalize_label(labels.get(label_index, str(label_index))): float(score)
                    for label_index, score in enumerate(sentence_scores)
                }
                label = max(score_map, key=score_map.get)
                results.append(
                    SentimentResult(
                        sentence_index=offset + index,
                        label=label,
                        confidence=score_map[label],
                        scores=score_map,
                    )
                )

        return tuple(results)

    @property
    def backend(self) -> tuple[Any, Any, Any, str]:
        if self._backend is None:
            self._backend = self._build_backend()
        return self._backend

    def _build_backend(self) -> tuple[Any, Any, Any, str]:
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            from transformers.utils import logging as transformers_logging
        except ImportError as exc:  # pragma: no cover - exercised only without deps.
            raise RuntimeError("Sentiment analysis is not available without transformers.") from exc

        transformers_logging.disable_progress_bar()
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        model.to(device)
        model.eval()
        return torch, tokenizer, model, device


def _labels_from_model(model: Any) -> dict[int, str]:
    id_to_label = getattr(getattr(model, "config", None), "id2label", None)
    if isinstance(id_to_label, dict):
        return {int(index): str(label) for index, label in id_to_label.items()}
    return {0: "negative", 1: "neutral", 2: "positive"}


def _normalize_label(label: str) -> str:
    normalized = label.strip().lower()
    if normalized in {"label_0", "0"}:
        return "negative"
    if normalized in {"label_1", "1"}:
        return "neutral"
    if normalized in {"label_2", "2"}:
        return "positive"
    return normalized