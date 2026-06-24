import logging

import pytest
import httpx

from speekify.extract import (
    ExtractedContent,
    extract_url,
    is_single_url_input,
    normalize_text,
    validate_url,
)
from speekify.extractors.youtube import (
    extract_text_from_timed_subtitle_text,
    extract_text_from_youtube_json3,
)


@pytest.fixture(autouse=True)
def reset_speekify_logger() -> None:
    speekify_logger = logging.getLogger("speekify")
    original_handlers = speekify_logger.handlers[:]
    original_level = speekify_logger.level
    original_propagate = speekify_logger.propagate

    speekify_logger.handlers = []
    speekify_logger.setLevel(logging.NOTSET)
    speekify_logger.propagate = True

    yield

    speekify_logger.handlers = original_handlers
    speekify_logger.setLevel(original_level)
    speekify_logger.propagate = original_propagate


def test_normalize_text_strips_repeated_blank_lines() -> None:
    raw = "  Bonjour   le monde\n\n\nCeci est   un test.  "
    assert normalize_text(raw) == "Bonjour le monde\n\nCeci est un test."


def test_validate_url_accepts_http_and_https() -> None:
    assert validate_url("https://example.com/article") == "https://example.com/article"
    assert validate_url("http://example.com/article") == "http://example.com/article"


def test_validate_url_rejects_other_schemes() -> None:
    with pytest.raises(ValueError, match="http"):
        validate_url("file:///tmp/a.html")


def test_is_single_url_input_accepts_a_single_url() -> None:
    assert is_single_url_input(" https://example.com/article ")


def test_is_single_url_input_rejects_mixed_text_and_url() -> None:
    assert not is_single_url_input("Lis https://example.com/article")


def test_extracted_content_title_fallback() -> None:
    content = ExtractedContent(text="Bonjour le monde. Ceci est un texte long.", title="")
    assert content.best_title() == "Bonjour le monde"


@pytest.mark.asyncio
async def test_extract_url_uses_youtube_english_transcript(monkeypatch) -> None:
    video_url = "https://www.youtube.com/watch?v=eSP7PLTXNy8"
    transcript_url = "https://example.com/transcript.json3"

    def fake_extract_youtube_info(url: str) -> dict[str, object]:
        assert url == video_url
        return {
            "title": "Build a proactive agent workflow with Claude Code",
            "subtitles": {
                "en": [
                    {"ext": "vtt", "url": "https://example.com/transcript.vtt"},
                    {"ext": "json3", "url": transcript_url},
                ]
            },
        }

    class FakeAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            return None

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
            request = httpx.Request("GET", url, headers=headers)
            assert url == transcript_url
            return httpx.Response(
                200,
                request=request,
                json={
                    "events": [
                        {"segs": [{"utf8": "First transcript sentence."}]},
                        {"segs": [{"utf8": "Second transcript sentence with enough text."}]},
                    ]
                },
            )

    monkeypatch.setattr("speekify.extractors.youtube._extract_youtube_info", fake_extract_youtube_info)
    monkeypatch.setattr("speekify.extractors.youtube.httpx.AsyncClient", FakeAsyncClient)

    content = await extract_url(video_url, min_chars=40)

    assert content.title == "Build a proactive agent workflow with Claude Code"
    assert content.text == "First transcript sentence. Second transcript sentence with enough text."


@pytest.mark.asyncio
async def test_extract_url_uses_x_oembed_for_status(monkeypatch) -> None:
    status_url = "https://x.com/w1nklerr/status/2060057563991884060"

    class FakeAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            return None

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
            request = httpx.Request("GET", url, headers=headers)
            assert url.startswith("https://publish.x.com/oembed?")
            return httpx.Response(
                200,
                request=request,
                json={
                    "author_name": "winkle.",
                    "html": (
                        "<blockquote><p>An English article summary with enough readable text "
                        "to satisfy extraction.</p>&mdash; winkle. (@w1nklerr) "
                        '<a href="https://twitter.com/w1nklerr/status/2060057563991884060">'
                        "May 28, 2026</a></blockquote>"
                    ),
                },
            )

    monkeypatch.setattr("speekify.extract.httpx.AsyncClient", FakeAsyncClient)

    content = await extract_url(status_url, min_chars=40)

    assert content.title == "X post by winkle."
    assert (
        content.text
        == "An English article summary with enough readable text to satisfy extraction."
    )


@pytest.mark.asyncio
async def test_extract_url_rejects_x_url_when_oembed_fails(monkeypatch) -> None:
    article_url = "https://x.com/w1nklerr/article/2060057563991884060"
    requested_urls: list[str] = []

    class FakeAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            return None

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
            requested_urls.append(url)
            request = httpx.Request("GET", url, headers=headers)
            if url.startswith("https://publish.x.com/oembed?"):
                response = httpx.Response(404, request=request)
                raise httpx.HTTPStatusError("not found", request=request, response=response)
            return httpx.Response(
                200,
                request=request,
                text=(
                    "<html><body><p>We’ve detected that JavaScript is disabled in this "
                    "browser. Please enable JavaScript or switch to a supported browser "
                    "to continue using x.com.</p></body></html>"
                ),
            )

    monkeypatch.setattr("speekify.extract.httpx.AsyncClient", FakeAsyncClient)

    with pytest.raises(ValueError, match="post X"):
        await extract_url(article_url, min_chars=40)

    assert all(url.startswith("https://publish.x.com/oembed?") for url in requested_urls)


@pytest.mark.asyncio
async def test_extract_url_rejects_x_status_when_oembed_text_is_too_short(monkeypatch) -> None:
    status_url = "https://x.com/w1nklerr/status/2060057563991884060"

    class FakeAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            return None

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
            request = httpx.Request("GET", url, headers=headers)
            assert url.startswith("https://publish.x.com/oembed?")
            return httpx.Response(
                200,
                request=request,
                json={"author_name": "winkle.", "html": "<blockquote><p>Short.</p></blockquote>"},
            )

    monkeypatch.setattr("speekify.extract.httpx.AsyncClient", FakeAsyncClient)

    with pytest.raises(ValueError, match="post X"):
        await extract_url(status_url, min_chars=40)


def test_extract_text_from_youtube_json3_joins_segments() -> None:
    assert (
        extract_text_from_youtube_json3(
            '{"events": [{"segs": [{"utf8": "Hello "}, {"utf8": "world."}]}]}'
        )
        == "Hello world."
    )


def test_extract_text_from_timed_subtitle_text_strips_cues() -> None:
    subtitle_text = """WEBVTT

00:00:00.000 --> 00:00:01.000
<v Speaker>Hello &amp; welcome.</v>

00:00:01.000 --> 00:00:02.000
Hello &amp; welcome.

00:00:02.000 --> 00:00:03.000
Next line.
"""

    assert extract_text_from_timed_subtitle_text(subtitle_text) == "Hello & welcome. Next line."


@pytest.mark.asyncio
async def test_extract_url_uses_medium_feed_fallback_on_blocked_article(monkeypatch) -> None:
    article_url = (
        "https://medium.com/leboncoin-tech-blog/"
        "beyond-the-hype-how-a-custom-multimodal-transformer-beat-our-fine-tuned-llm-b6cfac4140cd"
    )
    feed_url = "https://medium.com/feed/leboncoin-tech-blog"
    feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
  <channel>
    <item>
      <title><![CDATA[Article Medium]]></title>
      <link><![CDATA[https://medium.com/leboncoin-tech-blog/beyond-the-hype-how-a-custom-multimodal-transformer-beat-our-fine-tuned-llm-b6cfac4140cd?source=rss]]></link>
      <guid isPermaLink="false">https://medium.com/p/b6cfac4140cd</guid>
      <content:encoded><![CDATA[
        <p><strong>Intro</strong> with <a href="https://example.com">link</a>.</p>
        <p>Second paragraph with enough text to satisfy the minimum length.</p>
      ]]></content:encoded>
    </item>
  </channel>
</rss>
"""

    class FakeAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            return None

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
            request = httpx.Request("GET", url, headers=headers)
            if url == article_url:
                return httpx.Response(403, request=request, text="forbidden")
            if url == feed_url:
                return httpx.Response(200, request=request, text=feed_xml)
            raise AssertionError(f"unexpected URL {url}")

    monkeypatch.setattr("speekify.extract.httpx.AsyncClient", FakeAsyncClient)

    content = await extract_url(article_url, min_chars=40)

    assert content.title == "Article Medium"
    assert content.text == (
        "Intro with link.\n\nSecond paragraph with enough text to satisfy the minimum length."
    )


@pytest.mark.asyncio
async def test_extract_url_uses_medium_feed_fallback_on_custom_domain(monkeypatch, caplog) -> None:
    article_url = (
        "https://uxdesign.cc/"
        "designing-with-claude-code-and-codex-cli-building-ai-driven-workflows-powered-by-code-connect-ui-f10c136ec11f"
    )
    feed_url = "https://uxdesign.cc/feed/"
    feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
  <channel>
    <item>
      <title><![CDATA[Custom Medium Domain]]></title>
      <link><![CDATA[https://uxdesign.cc/designing-with-claude-code-and-codex-cli-building-ai-driven-workflows-powered-by-code-connect-ui-f10c136ec11f?source=rss]]></link>
      <guid isPermaLink="false">https://medium.com/p/f10c136ec11f</guid>
      <content:encoded><![CDATA[
        <p>Custom domain intro paragraph.</p>
        <p>Another paragraph with enough content to exceed the minimum length.</p>
      ]]></content:encoded>
    </item>
  </channel>
</rss>
"""

    class FakeAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            return None

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
            request = httpx.Request("GET", url, headers=headers)
            if url == article_url:
                return httpx.Response(403, request=request, text="forbidden")
            if url == feed_url:
                return httpx.Response(200, request=request, text=feed_xml)
            raise AssertionError(f"unexpected URL {url}")

    monkeypatch.setattr("speekify.extract.httpx.AsyncClient", FakeAsyncClient)
    caplog.set_level(logging.INFO, logger="speekify")

    content = await extract_url(article_url, min_chars=40)

    assert content.title == "Custom Medium Domain"
    assert content.text == (
        "Custom domain intro paragraph.\n\nAnother paragraph with enough content to exceed the minimum length."
    )
    assert any(
        record.message.startswith("Medium feed fallback triggered url=https://uxdesign.cc/")
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_extract_url_uses_medium_graphql_fallback_when_feed_misses_article(
    monkeypatch,
    caplog,
) -> None:
    article_url = (
        "https://uxdesign.cc/"
        "designing-with-claude-code-and-codex-cli-building-ai-driven-workflows-powered-by-code-connect-ui-f10c136ec11f"
    )
    feed_url = "https://uxdesign.cc/feed/"
    feed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
  <channel>
    <item>
      <title><![CDATA[Another article]]></title>
      <link><![CDATA[https://uxdesign.cc/another-article-deadbeefcafe?source=rss]]></link>
      <guid isPermaLink="false">https://medium.com/p/deadbeefcafe</guid>
      <content:encoded><![CDATA[
        <p>This is not the requested article.</p>
      ]]></content:encoded>
    </item>
  </channel>
</rss>
"""
    graphql_payload = {
        "data": {
            "post": {
                "id": "f10c136ec11f",
                "title": "GraphQL Medium Article",
                "content": {
                    "bodyModel": {
                        "paragraphs": [
                            {"text": "", "type": "IMG", "__typename": "Paragraph"},
                            {
                                "text": "GraphQL intro paragraph.",
                                "type": "P",
                                "__typename": "Paragraph",
                            },
                            {
                                "text": "Another paragraph with enough content to exceed the minimum length.",
                                "type": "P",
                                "__typename": "Paragraph",
                            },
                        ]
                    }
                },
            }
        }
    }

    class FakeAsyncClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            return None

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
            request = httpx.Request("GET", url, headers=headers)
            if url == article_url:
                return httpx.Response(403, request=request, text="forbidden")
            if url == feed_url:
                return httpx.Response(200, request=request, text=feed_xml)
            raise AssertionError(f"unexpected GET URL {url}")

        async def post(
            self,
            url: str,
            headers: dict[str, str] | None = None,
            json: dict[str, object] | None = None,
        ) -> httpx.Response:
            request = httpx.Request("POST", url, headers=headers, json=json)
            if url != "https://medium.com/_/graphql":
                raise AssertionError(f"unexpected POST URL {url}")
            return httpx.Response(200, request=request, json=graphql_payload)

    monkeypatch.setattr("speekify.extract.httpx.AsyncClient", FakeAsyncClient)
    caplog.set_level(logging.INFO, logger="speekify")

    content = await extract_url(article_url, min_chars=40)

    assert content.title == "GraphQL Medium Article"
    assert content.text == (
        "GraphQL intro paragraph.\n\nAnother paragraph with enough content to exceed the minimum length."
    )
    assert any(
        record.message.startswith("Medium GraphQL fallback triggered url=https://uxdesign.cc/")
        for record in caplog.records
    )
