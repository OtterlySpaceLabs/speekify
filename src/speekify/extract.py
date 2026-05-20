from __future__ import annotations

import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import httpx
import trafilatura

from speekify.config import MIN_URL_TEXT_LENGTH

DEFAULT_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,fr-FR;q=0.8,fr;q=0.7",
}


@dataclass(frozen=True)
class ExtractedContent:
    text: str
    title: str = ""

    def best_title(self) -> str:
        if self.title.strip():
            return self.title.strip()
        first_sentence = re.split(r"[.!?\n]", self.text.strip(), maxsplit=1)[0]
        return first_sentence.strip() or "speech"


def normalize_text(text: str) -> str:
    collapsed_lines = [
        re.sub(r"[ \t]+", " ", line).strip() for line in text.strip().splitlines()
    ]
    normalized_lines: list[str] = []
    previous_blank = False
    for line in collapsed_lines:
        is_blank = not line
        if is_blank and previous_blank:
            continue
        normalized_lines.append(line)
        previous_blank = is_blank
    return "\n".join(normalized_lines).strip()


def validate_url(url: str) -> str:
    candidate = url.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("L'URL doit commencer par http:// ou https://.")
    return candidate


def is_single_url_input(text: str) -> bool:
    candidate = text.strip()
    if not candidate or any(char.isspace() for char in candidate):
        return False

    try:
        validate_url(candidate)
    except ValueError:
        return False

    return True


async def extract_url(url: str, min_chars: int = MIN_URL_TEXT_LENGTH) -> ExtractedContent:
    validated_url = validate_url(url)
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        direct_error: httpx.HTTPError | None = None
        try:
            response = await client.get(validated_url, headers=DEFAULT_FETCH_HEADERS)
            response.raise_for_status()
            extracted = _extract_from_html(response.text, min_chars=min_chars)
            if extracted is not None:
                return extracted
        except httpx.HTTPStatusError as exc:
            direct_error = exc
            if not _should_retry_with_medium_feed(validated_url, exc.response):
                raise
        except httpx.HTTPError as exc:
            direct_error = exc

        if _is_medium_article_url(validated_url):
            extracted = await _extract_medium_article_from_feed(
                client,
                validated_url,
                min_chars=min_chars,
            )
            if extracted is not None:
                return extracted

    if direct_error is not None:
        raise direct_error
    raise ValueError("Le contenu lisible extrait de cette URL est trop court.")


def _extract_from_html(html_text: str, min_chars: int) -> ExtractedContent | None:
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


def _should_retry_with_medium_feed(url: str, response: httpx.Response) -> bool:
    return _is_medium_article_url(url) and response.status_code in {401, 403, 429}


def _is_medium_article_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path_segments = [segment for segment in parsed.path.split("/") if segment]
    return host.endswith("medium.com") and len(path_segments) >= 2


async def _extract_medium_article_from_feed(
    client: httpx.AsyncClient,
    article_url: str,
    min_chars: int,
) -> ExtractedContent | None:
    feed_url = _build_medium_feed_url(article_url)
    if feed_url is None:
        return None

    response = await client.get(feed_url, headers=DEFAULT_FETCH_HEADERS)
    response.raise_for_status()
    return _extract_medium_article_from_feed_xml(response.text, article_url, min_chars=min_chars)


def _build_medium_feed_url(article_url: str) -> str | None:
    parsed = urlparse(article_url)
    path_segments = [segment for segment in parsed.path.split("/") if segment]
    if len(path_segments) < 2:
        return None

    publication_or_author = path_segments[0]
    if publication_or_author == "p":
        return None

    return f"{parsed.scheme}://{parsed.netloc}/feed/{publication_or_author}"


def _extract_medium_article_from_feed_xml(
    xml_text: str,
    article_url: str,
    min_chars: int,
) -> ExtractedContent | None:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None

    article_id = _extract_medium_article_id(article_url)
    article_path = urlparse(article_url).path.rstrip("/")
    content_tag = "{http://purl.org/rss/1.0/modules/content/}encoded"

    for item in root.findall("./channel/item"):
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or "").strip()
        if article_id:
            if article_id not in link and article_id not in guid:
                continue
        elif urlparse(link).path.rstrip("/") != article_path:
            continue

        title = html.unescape((item.findtext("title") or "").strip())
        encoded_html = item.findtext(content_tag) or ""
        text = _extract_text_from_html_fragment(encoded_html)
        if len(text) >= min_chars:
            return ExtractedContent(text=text, title=title)

    return None


def _extract_medium_article_id(article_url: str) -> str | None:
    path = urlparse(article_url).path.rstrip("/")
    match = re.search(r"([0-9a-f]{12})$", path, flags=re.IGNORECASE)
    return match.group(1).lower() if match else None


def _extract_text_from_html_fragment(fragment: str) -> str:
    parser = _HTMLFragmentToTextParser()
    parser.feed(fragment)
    parser.close()
    return normalize_text("".join(parser.parts))


class _HTMLFragmentToTextParser(HTMLParser):
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
