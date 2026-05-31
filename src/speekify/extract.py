from __future__ import annotations

import httpx

from speekify.config import MIN_URL_TEXT_LENGTH
from speekify.extract_common import (
    DEFAULT_FETCH_HEADERS,
    ExtractedContent,
    is_single_url_input,
    logger,
    normalize_text,
    validate_url,
)
from speekify.extractors import (
    build_medium_feed_url,
    extract_from_html,
    extract_medium_article_from_feed,
    extract_medium_article_from_graphql,
    extract_x_status_from_oembed,
    extract_youtube_transcript,
    looks_like_x_status_url,
    looks_like_youtube_url,
    should_retry_with_medium_feed,
)
from speekify.extractors import youtube as _youtube_provider


_extract_youtube_info = _youtube_provider._extract_youtube_info
_extract_text_from_timed_subtitle_text = (
    _youtube_provider.extract_text_from_timed_subtitle_text
)
_extract_text_from_youtube_json3 = _youtube_provider.extract_text_from_youtube_json3


async def extract_url(url: str, min_chars: int = MIN_URL_TEXT_LENGTH) -> ExtractedContent:
    validated_url = validate_url(url)
    if looks_like_youtube_url(validated_url):
        return await extract_youtube_transcript(validated_url, min_chars=min_chars)

    should_attempt_medium_fallback = False
    direct_error: httpx.HTTPError | None = None
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        if looks_like_x_status_url(validated_url):
            extracted = await extract_x_status_from_oembed(
                client,
                validated_url,
                min_chars=min_chars,
            )
            if extracted is not None:
                return extracted

        try:
            response = await client.get(validated_url, headers=DEFAULT_FETCH_HEADERS)
            response.raise_for_status()
            extracted = extract_from_html(response.text, min_chars=min_chars)
            if extracted is not None:
                return extracted
        except httpx.HTTPStatusError as exc:
            direct_error = exc
            should_attempt_medium_fallback = should_retry_with_medium_feed(
                validated_url,
                exc.response,
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
                build_medium_feed_url(validated_url),
            )
            try:
                extracted = await extract_medium_article_from_feed(
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
                extracted = await extract_medium_article_from_graphql(
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


__all__ = [
    "ExtractedContent",
    "extract_url",
    "is_single_url_input",
    "normalize_text",
    "validate_url",
    "_extract_text_from_timed_subtitle_text",
    "_extract_text_from_youtube_json3",
    "_extract_youtube_info",
]