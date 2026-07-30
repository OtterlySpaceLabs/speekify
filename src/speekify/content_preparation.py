from __future__ import annotations

import html
import re
from html.parser import HTMLParser

from markdown_it import MarkdownIt
from markdown_it.token import Token

from speekify.extract_common import normalize_text

_MARKDOWN = MarkdownIt("commonmark", {"html": True}).enable("table")

_EMOJI_BASE_RANGES = (
    "\u2300-\u23ff"
    "\u2600-\u27bf"
    "\u2b00-\u2bff"
    "\U0001f000-\U0001faff"
)
_EMOJI_CLUSTER = re.compile(
    rf"[{_EMOJI_BASE_RANGES}]"
    rf"[\ufe0f\U0001f3fb-\U0001f3ff]*"
    rf"(?:\u200d[{_EMOJI_BASE_RANGES}]"
    rf"[\ufe0f\U0001f3fb-\U0001f3ff]*)*"
)
_EMOJI_BEFORE_PUNCTUATION = re.compile(
    rf"[ \t]*(?:{_EMOJI_CLUSTER.pattern})[ \t]*(?=[.,;:!?])"
)
_EMOJI_TAGS = re.compile(r"[\U000e0020-\U000e007f]")

_BLOCK_END_TOKENS = {
    "blockquote_close",
    "heading_close",
    "paragraph_close",
}
_LIST_END_TOKENS = {
    "bullet_list_close",
    "list_item_close",
    "ordered_list_close",
}


def prepare_content_for_speech(text: str) -> str:
    """Convert extracted source content into text that is useful when spoken."""
    rendered = _render_markdown(_MARKDOWN.parse(_strip_yaml_front_matter(text)))
    without_markers = _strip_residual_markdown_markers(rendered)
    prepared = normalize_text(_strip_decorative_emoji(without_markers))
    if not prepared:
        raise ValueError("The content no longer contains text suitable for speech.")
    return prepared


def _strip_decorative_emoji(text: str) -> str:
    text = _EMOJI_BEFORE_PUNCTUATION.sub(_replace_emoji_before_punctuation, text)
    text = _EMOJI_CLUSTER.sub(" ", text)
    text = _EMOJI_TAGS.sub("", text)
    return text.replace("\ufe0f", "").replace("\u20e3", "")


def _replace_emoji_before_punctuation(match: re.Match[str]) -> str:
    punctuation = match.string[match.end()]
    return " " if punctuation in ";:!?" else ""


def _strip_yaml_front_matter(text: str) -> str:
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return text

    closing_index = next(
        (
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() in {"---", "..."}
        ),
        None,
    )
    if closing_index is None:
        return text

    metadata_lines = lines[1:closing_index]
    if not any(re.match(r"^[A-Za-z_][\w-]*\s*:", line) for line in metadata_lines):
        return text
    return "\n".join(lines[closing_index + 1 :])


def _render_markdown(tokens: list[Token]) -> str:
    parts: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.type in {"code_block", "fence"}:
            index += 1
            continue
        if token.type == "table_open":
            table_end = _find_closing_token(tokens, index, "table_open", "table_close")
            parts.append(_render_markdown_table(tokens[index + 1 : table_end]))
            parts.append("\n\n")
            index = table_end + 1
            continue
        if token.type == "inline":
            parts.append(_render_inline_tokens(token.children or []))
        elif token.type == "html_block":
            parts.append(_html_to_speech(token.content))
        elif token.type in _BLOCK_END_TOKENS:
            parts.append("\n\n")
        elif token.type in _LIST_END_TOKENS:
            parts.append("\n")
        elif token.type == "hr":
            parts.append("\n\n")
        index += 1
    return "".join(parts)


def _render_inline_tokens(tokens: list[Token]) -> str:
    fragments: list[str] = []
    for token in tokens:
        if token.type == "image":
            continue
        if token.type == "html_inline":
            fragments.append(token.content)
        elif token.type in {"hardbreak", "softbreak"}:
            fragments.append("<br>")
        elif token.type in {"text", "code_inline"}:
            fragments.append(html.escape(token.content))
        elif token.children:
            fragments.append(html.escape(_render_inline_tokens(token.children)))
    return _html_to_speech("".join(fragments))


def _find_closing_token(
    tokens: list[Token],
    start: int,
    opening_type: str,
    closing_type: str,
) -> int:
    depth = 0
    for index in range(start, len(tokens)):
        if tokens[index].type == opening_type:
            depth += 1
        elif tokens[index].type == closing_type:
            depth -= 1
            if depth == 0:
                return index
    return len(tokens) - 1


def _render_markdown_table(tokens: list[Token]) -> str:
    rows: list[list[str]] = []
    header_rows: list[bool] = []
    row: list[str] | None = None
    cell_parts: list[str] | None = None
    cell_is_header = False
    row_has_header = False

    for token in tokens:
        if token.type == "tr_open":
            row = []
            row_has_header = False
        elif token.type in {"th_open", "td_open"}:
            cell_parts = []
            cell_is_header = token.type == "th_open"
        elif token.type == "inline" and cell_parts is not None:
            cell_parts.append(_render_inline_tokens(token.children or []))
        elif token.type in {"th_close", "td_close"} and row is not None:
            row.append(normalize_text("".join(cell_parts or [])))
            row_has_header = row_has_header or cell_is_header
            cell_parts = None
        elif token.type == "tr_close" and row is not None:
            rows.append(row)
            header_rows.append(row_has_header)
            row = None

    return _format_table_for_speech(rows, header_rows)


def _format_table_for_speech(rows: list[list[str]], header_rows: list[bool]) -> str:
    if not rows:
        return ""

    headers = rows[0] if header_rows and header_rows[0] else []
    data_rows = rows[1:] if headers else rows
    spoken_rows: list[str] = []
    for row in data_rows:
        cells: list[str] = []
        for index, value in enumerate(row):
            if not value:
                continue
            if index < len(headers) and headers[index]:
                cells.append(f"{headers[index]} : {value}")
            else:
                cells.append(value)
        if cells:
            spoken_rows.append(_as_sentence(" ; ".join(cells)))

    if spoken_rows:
        return "\n".join(spoken_rows)
    return _as_sentence(" ; ".join(cell for cell in rows[0] if cell))


def _as_sentence(text: str) -> str:
    text = text.strip()
    if text and text[-1] not in ".!?":
        return f"{text}."
    return text


def _html_to_speech(fragment: str) -> str:
    parser = _SpeechHTMLParser()
    parser.feed(fragment)
    parser.close()
    return normalize_text("".join(parser.parts))


def _strip_residual_markdown_markers(text: str) -> str:
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        line = re.sub(r"^\s{0,3}#{1,6}\s+", "", line)
        line = re.sub(r"^\s*>\s?", "", line)
        line = re.sub(r"^\s*(?:[-+*]|\d+[.)])\s+", "", line)
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


class _SpeechHTMLParser(HTMLParser):
    _SUPPRESSED_TAGS = {
        "audio",
        "canvas",
        "embed",
        "iframe",
        "map",
        "math",
        "noscript",
        "object",
        "picture",
        "portal",
        "pre",
        "script",
        "style",
        "svg",
        "template",
        "video",
    }
    _IGNORED_VOID_TAGS = {
        "area",
        "base",
        "col",
        "embed",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
    _VOID_TAGS = _IGNORED_VOID_TAGS | {"br", "hr"}
    _BLOCK_TAGS = {
        "address",
        "article",
        "aside",
        "blockquote",
        "dd",
        "details",
        "dialog",
        "div",
        "dl",
        "dt",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "section",
        "summary",
        "ul",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._suppressed_depth = 0
        self._table_rows: list[list[str]] | None = None
        self._table_header_rows: list[bool] = []
        self._table_row: list[str] | None = None
        self._table_cell_parts: list[str] | None = None
        self._table_cell_is_header = False
        self._table_row_has_header = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self._suppressed_depth:
            if tag not in self._VOID_TAGS:
                self._suppressed_depth += 1
            return
        if tag in self._SUPPRESSED_TAGS or _is_hidden(attrs):
            if tag not in self._VOID_TAGS:
                self._suppressed_depth = 1
            return
        if tag in self._IGNORED_VOID_TAGS:
            return
        if tag == "table":
            self._table_rows = []
            self._table_header_rows = []
            self.parts.append("\n\n")
        elif self._table_rows is not None:
            self._handle_table_start(tag)
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "hr" or tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._suppressed_depth:
            return
        self.handle_starttag(tag, attrs)
        if tag.lower() not in self._VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._suppressed_depth:
            self._suppressed_depth -= 1
            return
        if self._table_rows is not None:
            if tag == "table":
                self._finish_table()
            else:
                self._handle_table_end(tag)
            return
        if tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._suppressed_depth:
            return
        if self._table_cell_parts is not None:
            self._table_cell_parts.append(data)
        elif self._table_rows is None:
            self.parts.append(data)

    def _handle_table_start(self, tag: str) -> None:
        if tag == "tr":
            self._table_row = []
            self._table_row_has_header = False
        elif tag in {"th", "td"}:
            self._table_cell_parts = []
            self._table_cell_is_header = tag == "th"
        elif tag == "br" and self._table_cell_parts is not None:
            self._table_cell_parts.append(" ")

    def _handle_table_end(self, tag: str) -> None:
        if tag in {"th", "td"} and self._table_row is not None:
            self._table_row.append(normalize_text("".join(self._table_cell_parts or [])))
            self._table_row_has_header = (
                self._table_row_has_header or self._table_cell_is_header
            )
            self._table_cell_parts = None
        elif tag == "tr" and self._table_row is not None:
            self._table_rows.append(self._table_row)
            self._table_header_rows.append(self._table_row_has_header)
            self._table_row = None

    def _finish_table(self) -> None:
        assert self._table_rows is not None
        self.parts.append(_format_table_for_speech(self._table_rows, self._table_header_rows))
        self.parts.append("\n\n")
        self._table_rows = None
        self._table_header_rows = []
        self._table_row = None
        self._table_cell_parts = None


def _is_hidden(attrs: list[tuple[str, str | None]]) -> bool:
    normalized = {name.lower(): (value or "").lower() for name, value in attrs}
    return "hidden" in normalized or normalized.get("aria-hidden") == "true"


__all__ = ["prepare_content_for_speech"]
