from __future__ import annotations

import html
from html.parser import HTMLParser

import trafilatura

from speekify.extract_common import ExtractedContent, normalize_text


def extract_from_html(html_text: str, min_chars: int) -> ExtractedContent | None:
    metadata = trafilatura.extract_metadata(html_text)
    extracted_text = trafilatura.extract(
        html_text,
        include_comments=False,
        include_tables=False,
        favor_recall=True,
    )
    text = normalize_text(extracted_text or "")
    if len(text) < min_chars:
        return None

    title = metadata.title if metadata and metadata.title else ""
    return ExtractedContent(text=text, title=title)


def extract_text_from_html_fragment(fragment: str) -> str:
    parser = HTMLFragmentToTextParser()
    parser.feed(fragment)
    parser.close()
    return normalize_text("".join(parser.parts))


class HTMLFragmentToTextParser(HTMLParser):
    BLOCK_TAGS = {
        "article",
        "blockquote",
        "div",
        "figcaption",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "pre",
        "section",
    }

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "li" or tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(html.unescape(data))