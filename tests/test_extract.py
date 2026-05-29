import logging

import pytest
import httpx

from speekify.extract import ExtractedContent, extract_url, is_single_url_input, normalize_text, validate_url


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
