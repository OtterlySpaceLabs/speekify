from __future__ import annotations

import asyncio
import html
import json
import logging
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlencode, urlparse
from xml.etree import ElementTree as ET

import httpx
import trafilatura
import yt_dlp

from speekify.config import MIN_URL_TEXT_LENGTH
from speekify.logging_utils import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)

DEFAULT_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,fr-FR;q=0.8,fr;q=0.7",
}

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
X_HOSTS = {"x.com", "www.x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com"}
YOUTUBE_TRANSCRIPT_LANG_PREFIXES = ("en",)
YOUTUBE_SUBTITLE_FORMAT_PRIORITY = ("json3", "vtt", "srv3", "ttml", "srt")

MEDIUM_GRAPHQL_HEADERS = {
    **DEFAULT_FETCH_HEADERS,
    "Accept": "*/*",
    "Content-Type": "application/json",
    "Origin": "https://medium.com",
    "Referer": "https://medium.com/",
}

MEDIUM_POST_BY_ID_QUERY = (
    "query PostByIdBody($id: ID!) { "
    "post(id: $id) { "
    "id title content { bodyModel { paragraphs { text type __typename } __typename } __typename } __typename "
    "} "
    "}"
)


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
    collapsed_lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.strip().splitlines()]
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
    if _looks_like_youtube_url(validated_url):
        return await _extract_youtube_transcript(validated_url, min_chars=min_chars)

    should_attempt_medium_fallback = False
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        if _looks_like_x_status_url(validated_url):
            extracted = await _extract_x_status_from_oembed(
                client,
                validated_url,
                min_chars=min_chars,
            )
            if extracted is not None:
                return extracted

        direct_error: httpx.HTTPError | None = None
        try:
            response = await client.get(validated_url, headers=DEFAULT_FETCH_HEADERS)
            response.raise_for_status()
            extracted = _extract_from_html(response.text, min_chars=min_chars)
            if extracted is not None:
                return extracted
        except httpx.HTTPStatusError as exc:
            direct_error = exc
            should_attempt_medium_fallback = _should_retry_with_medium_feed(
                validated_url, exc.response
            )
            if not should_attempt_medium_fallback:
                raise
        except httpx.HTTPError as exc:
            direct_error = exc

        if should_attempt_medium_fallback:
            logger.info(
                "Medium feed fallback triggered url=%s status_code=%s feed_url=%s",
                validated_url,
                getattr(getattr(direct_error, "response", None), "status_code", None),
                _build_medium_feed_url(validated_url),
            )
            try:
                extracted = await _extract_medium_article_from_feed(
                    client,
                    validated_url,
                    min_chars=min_chars,
                )
            except httpx.HTTPError:
                extracted = None
            if extracted is not None:
                return extracted

            logger.info("Medium GraphQL fallback triggered url=%s", validated_url)
            try:
                extracted = await _extract_medium_article_from_graphql(
                    client,
                    validated_url,
                    min_chars=min_chars,
                )
            except httpx.HTTPError:
                extracted = None
            if extracted is not None:
                return extracted

    if direct_error is not None:
        raise direct_error
    raise ValueError("Le contenu lisible extrait de cette URL est trop court.")


def _looks_like_youtube_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    return host in YOUTUBE_HOSTS or host.endswith(".youtube.com")


def _looks_like_x_status_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host not in X_HOSTS:
        return False
    return re.search(r"/(?:[^/]+/status|i/article)/\d+", parsed.path) is not None


async def _extract_youtube_transcript(url: str, min_chars: int) -> ExtractedContent:
    logger.info("YouTube transcript extraction triggered url=%s", url)
    info = await asyncio.to_thread(_extract_youtube_info, url)
    transcript_source = _select_youtube_transcript_source(info)
    if transcript_source is None:
        raise ValueError("Aucun transcript anglais disponible pour cette vidéo YouTube.")

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(transcript_source["url"], headers=DEFAULT_FETCH_HEADERS)
        response.raise_for_status()

    text = _extract_text_from_youtube_subtitles(response.text, transcript_source.get("ext", ""))
    if len(text) < min_chars:
        raise ValueError("Le transcript anglais extrait de cette vidéo YouTube est trop court.")

    title = info.get("title", "")
    if not isinstance(title, str):
        title = ""
    return ExtractedContent(text=text, title=title)


def _extract_youtube_info(url: str) -> dict[str, object]:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict):
        raise ValueError("Impossible de lire les métadonnées de cette vidéo YouTube.")
    return info


def _select_youtube_transcript_source(info: dict[str, object]) -> dict[str, str] | None:
    for source_group_name in ("subtitles", "automatic_captions"):
        source_group = info.get(source_group_name, {})
        if not isinstance(source_group, dict):
            continue
        candidates = _select_youtube_language_tracks(source_group)
        selected = _select_preferred_youtube_track(candidates)
        if selected is not None:
            return selected
    return None


def _select_youtube_language_tracks(source_group: dict[object, object]) -> list[dict[str, str]]:
    for lang, tracks in source_group.items():
        if not isinstance(lang, str) or not lang.lower().startswith(
            YOUTUBE_TRANSCRIPT_LANG_PREFIXES
        ):
            continue
        if not isinstance(tracks, list):
            continue
        normalized_tracks: list[dict[str, str]] = []
        for track in tracks:
            if not isinstance(track, dict):
                continue
            url = track.get("url", "")
            if not isinstance(url, str) or not url:
                continue
            ext = track.get("ext", "")
            normalized_tracks.append({"url": url, "ext": ext if isinstance(ext, str) else ""})
        if normalized_tracks:
            return normalized_tracks
    return []


def _select_preferred_youtube_track(tracks: list[dict[str, str]]) -> dict[str, str] | None:
    if not tracks:
        return None
    for preferred_ext in YOUTUBE_SUBTITLE_FORMAT_PRIORITY:
        for track in tracks:
            if track.get("ext") == preferred_ext:
                return track
    return tracks[0]


def _extract_text_from_youtube_subtitles(subtitle_text: str, subtitle_ext: str) -> str:
    if subtitle_ext == "json3" or subtitle_text.lstrip().startswith("{"):
        return _extract_text_from_youtube_json3(subtitle_text)
    return _extract_text_from_timed_subtitle_text(subtitle_text)


def _extract_text_from_youtube_json3(subtitle_text: str) -> str:
    try:
        payload = json.loads(subtitle_text)
    except json.JSONDecodeError:
        return ""

    events = payload.get("events", [])
    if not isinstance(events, list):
        return ""

    text_parts: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        segments = event.get("segs", [])
        if not isinstance(segments, list):
            continue
        segment_text = "".join(
            segment.get("utf8", "")
            for segment in segments
            if isinstance(segment, dict) and isinstance(segment.get("utf8", ""), str)
        )
        stripped_segment_text = segment_text.strip()
        if stripped_segment_text:
            text_parts.append(stripped_segment_text)
    return normalize_text(" ".join(text_parts))


def _extract_text_from_timed_subtitle_text(subtitle_text: str) -> str:
    text_parts: list[str] = []
    previous_text = ""
    for raw_line in subtitle_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.upper() == "WEBVTT" or line.startswith(("Kind:", "Language:")):
            continue
        if "-->" in line or re.fullmatch(r"\d+", line):
            continue
        cleaned_line = re.sub(r"<[^>]+>", "", line)
        cleaned_line = html.unescape(cleaned_line).strip()
        if cleaned_line and cleaned_line != previous_text:
            text_parts.append(cleaned_line)
            previous_text = cleaned_line
    return normalize_text(" ".join(text_parts))


async def _extract_x_status_from_oembed(
    client: httpx.AsyncClient,
    status_url: str,
    min_chars: int,
) -> ExtractedContent | None:
    oembed_url = "https://publish.x.com/oembed?" + urlencode(
        {"url": status_url, "omit_script": "true", "dnt": "true"}
    )
    try:
        response = await client.get(oembed_url, headers=DEFAULT_FETCH_HEADERS)
        response.raise_for_status()
    except httpx.HTTPError:
        logger.info("X oEmbed extraction failed url=%s", status_url, exc_info=True)
        return None

    payload = response.json()
    if not isinstance(payload, dict):
        return None
    rendered_html = payload.get("html", "")
    if not isinstance(rendered_html, str):
        return None

    text = _extract_text_from_html_fragment(rendered_html)
    text = _strip_x_embed_footer(text)
    if len(text) < min_chars:
        return None

    author_name = payload.get("author_name", "")
    title = f"X post by {author_name}" if isinstance(author_name, str) and author_name else "X post"
    return ExtractedContent(text=text, title=title)


def _strip_x_embed_footer(text: str) -> str:
    lines = []
    for line in normalize_text(text).splitlines():
        stripped_line = line.strip()
        if stripped_line.startswith("—"):
            continue
        lines.append(stripped_line)
    return normalize_text("\n".join(lines))


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
    return _looks_like_medium_article_url(url) and response.status_code in {401, 403, 429}


def _looks_like_medium_article_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path_segments = [segment for segment in parsed.path.split("/") if segment]
    if host.endswith("medium.com") and len(path_segments) >= 2:
        return True

    if len(path_segments) != 1:
        return False

    publication_or_author = path_segments[0].lower()
    if publication_or_author in {"feed", "tag", "topics", "search", "about", "p"}:
        return False

    return _extract_medium_article_id(url) is not None


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


async def _extract_medium_article_from_graphql(
    client: httpx.AsyncClient,
    article_url: str,
    min_chars: int,
) -> ExtractedContent | None:
    article_id = _extract_medium_article_id(article_url)
    if article_id is None:
        return None

    response = await client.post(
        "https://medium.com/_/graphql",
        headers=MEDIUM_GRAPHQL_HEADERS,
        json={
            "operationName": "PostByIdBody",
            "query": MEDIUM_POST_BY_ID_QUERY,
            "variables": {"id": article_id},
        },
    )
    response.raise_for_status()
    return _extract_medium_article_from_graphql_payload(response.json(), min_chars=min_chars)


def _extract_medium_article_from_graphql_payload(
    payload: dict[str, object],
    min_chars: int,
) -> ExtractedContent | None:
    post = payload.get("data", {})
    if not isinstance(post, dict):
        return None

    post_data = post.get("post", {})
    if not isinstance(post_data, dict):
        return None

    content = post_data.get("content", {})
    if not isinstance(content, dict):
        return None

    body_model = content.get("bodyModel", {})
    if not isinstance(body_model, dict):
        return None

    paragraphs = body_model.get("paragraphs", [])
    if not isinstance(paragraphs, list):
        return None

    text_parts: list[str] = []
    for paragraph in paragraphs:
        if not isinstance(paragraph, dict):
            continue
        text = paragraph.get("text", "")
        if not isinstance(text, str):
            continue
        stripped_text = text.strip()
        if stripped_text:
            text_parts.append(stripped_text)

    text = normalize_text("\n\n".join(text_parts))
    if len(text) < min_chars:
        return None

    title = post_data.get("title", "")
    if not isinstance(title, str):
        title = ""
    return ExtractedContent(text=text, title=title)


def _build_medium_feed_url(article_url: str) -> str | None:
    parsed = urlparse(article_url)
    path_segments = [segment for segment in parsed.path.split("/") if segment]
    if not path_segments:
        return None

    if not parsed.netloc.lower().endswith("medium.com"):
        return f"{parsed.scheme}://{parsed.netloc}/feed/"

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
