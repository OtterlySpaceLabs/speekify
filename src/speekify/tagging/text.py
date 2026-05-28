from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TextSpan:
    start: int
    end: int

    def slice(self, text: str) -> str:
        return text[self.start : self.end]

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass(frozen=True)
class ParagraphSpan(TextSpan):
    index: int


@dataclass(frozen=True)
class SentenceSpan(TextSpan):
    index: int
    paragraph_index: int


@dataclass(frozen=True)
class TextDocument:
    text: str
    language_code: str
    paragraphs: tuple[ParagraphSpan, ...]
    sentences: tuple[SentenceSpan, ...]


class TextPreprocessor:
    def process(self, text: str, *, language_code: str) -> TextDocument:
        paragraphs = tuple(_paragraph_spans(text))
        sentences = tuple(_sentence_spans(text, paragraphs))
        return TextDocument(
            text=text,
            language_code=language_code.strip().lower(),
            paragraphs=paragraphs,
            sentences=sentences,
        )


def _paragraph_spans(text: str) -> list[ParagraphSpan]:
    spans: list[ParagraphSpan] = []
    for match in re.finditer(r"\S[\s\S]*?(?=\n\s*\n|\Z)", text):
        start, end = _trim_span(text, match.start(), match.end())
        if start < end:
            spans.append(ParagraphSpan(start=start, end=end, index=len(spans)))
    return spans


def _sentence_spans(text: str, paragraphs: tuple[ParagraphSpan, ...]) -> list[SentenceSpan]:
    sentences: list[SentenceSpan] = []
    for paragraph in paragraphs:
        paragraph_text = paragraph.slice(text)
        local_start = 0
        for match in re.finditer(r"[.!?…]+[\"')\]]*(?=\s|\Z)", paragraph_text):
            start, end = _trim_span(
                paragraph_text,
                local_start,
                match.end(),
            )
            if start < end:
                sentences.append(
                    SentenceSpan(
                        start=paragraph.start + start,
                        end=paragraph.start + end,
                        index=len(sentences),
                        paragraph_index=paragraph.index,
                    )
                )
            local_start = _next_non_space(paragraph_text, match.end())

        start, end = _trim_span(paragraph_text, local_start, len(paragraph_text))
        if start < end:
            sentences.append(
                SentenceSpan(
                    start=paragraph.start + start,
                    end=paragraph.start + end,
                    index=len(sentences),
                    paragraph_index=paragraph.index,
                )
            )
    return sentences


def _trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _next_non_space(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    return index