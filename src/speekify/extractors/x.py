from __future__ import annotations

import re
from urllib.parse import urlencode, urlparse

import httpx

from speekify.extract_common import DEFAULT_FETCH_HEADERS, ExtractedContent, logger, normalize_text
from speekify.extractors.html import extract_text_from_html_fragment

X_HOSTS = {"x.com", "www.x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com"}


def looks_like_x_status_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host not in X_HOSTS:
        return False
    return re.search(r"/(?:[^/]+/(?:status|article)|i/article)/\d+", parsed.path) is not None


async def extract_x_status_from_oembed(
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

    text = extract_text_from_html_fragment(rendered_html)
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