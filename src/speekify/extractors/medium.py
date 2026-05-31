from __future__ import annotations

import html
import re
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import httpx

from speekify.extract_common import DEFAULT_FETCH_HEADERS, ExtractedContent, normalize_text
from speekify.extractors.html import extract_text_from_html_fragment

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


def should_retry_with_medium_feed(url: str, response: httpx.Response) -> bool:
    return looks_like_medium_article_url(url) and response.status_code in {401, 403, 429}


def looks_like_medium_article_url(url: str) -> bool:
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

    return extract_medium_article_id(url) is not None


async def extract_medium_article_from_feed(
    client: httpx.AsyncClient,
    article_url: str,
    min_chars: int,
) -> ExtractedContent | None:
    feed_url = build_medium_feed_url(article_url)
    if feed_url is None:
        return None

    response = await client.get(feed_url, headers=DEFAULT_FETCH_HEADERS)
    response.raise_for_status()
    return extract_medium_article_from_feed_xml(response.text, article_url, min_chars=min_chars)


async def extract_medium_article_from_graphql(
    client: httpx.AsyncClient,
    article_url: str,
    min_chars: int,
) -> ExtractedContent | None:
    article_id = extract_medium_article_id(article_url)
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
    return extract_medium_article_from_graphql_payload(response.json(), min_chars=min_chars)


def extract_medium_article_from_graphql_payload(
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


def build_medium_feed_url(article_url: str) -> str | None:
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


def extract_medium_article_from_feed_xml(
    xml_text: str,
    article_url: str,
    min_chars: int,
) -> ExtractedContent | None:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None

    article_id = extract_medium_article_id(article_url)
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
        text = extract_text_from_html_fragment(encoded_html)
        if len(text) >= min_chars:
            return ExtractedContent(text=text, title=title)

    return None


def extract_medium_article_id(article_url: str) -> str | None:
    path = urlparse(article_url).path.rstrip("/")
    match = re.search(r"([0-9a-f]{12})$", path, flags=re.IGNORECASE)
    return match.group(1).lower() if match else None