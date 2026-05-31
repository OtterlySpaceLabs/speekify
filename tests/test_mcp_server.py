from __future__ import annotations

import asyncio

import pytest

from speekify.extract import ExtractedContent
from speekify.mcp_server import _build_request, create_mcp_server, generate_wav, generation_defaults
from speekify.tts import PreparedText, SynthesisArtifact
from speekify.workflow import GenerationResult


def test_generation_defaults_are_mcp_serializable() -> None:
    defaults = generation_defaults()

    assert defaults["language_code"] == "fr"
    assert defaults["voice"] == "M5"
    assert "fr" in defaults["supported_languages"]
    assert "M5" in defaults["voices"]
    assert defaults["speed_range"] == {"min": 0.7, "max": 2.0}
    assert defaults["steps_range"] == {"min": 1, "max": 100}


def test_build_request_normalizes_and_validates_options(tmp_path) -> None:
    request = _build_request(
        source="  Bonjour le monde  ",
        is_url_mode=False,
        title="  Recap du jour  ",
        voice="m1",
        custom_style_path=None,
        language_code="FR",
        speed=1.0,
        steps=12,
        max_chunk_length=240,
        silence_duration=0.1,
        output_dir=str(tmp_path),
        feed_base_url="https://audio.example.com/speekify/",
        tags=True,
        tag_sentiment=False,
        tag_sigh=True,
    )

    assert request.source_text == "Bonjour le monde"
    assert request.title == "Recap du jour"
    assert request.voice == "M1"
    assert request.language_code == "fr"
    assert request.output_dir == tmp_path
    assert request.feed_base_url == "https://audio.example.com/speekify"
    assert request.tagging_config.enabled is True
    assert request.tagging_config.use_sentiment is False
    assert request.tagging_config.enable_sigh is True


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("voice", "robot", "Voice must be one of"),
        ("language_code", "xx", "Language code must be one of"),
        ("source", "   ", "A text source or URL is required"),
    ],
)
def test_build_request_rejects_invalid_mcp_inputs(field: str, value: str, message: str) -> None:
    kwargs = {
        "source": "Bonjour",
        "is_url_mode": False,
        "title": "",
        "voice": "M5",
        "custom_style_path": None,
        "language_code": "fr",
        "speed": 1.0,
        "steps": 10,
        "max_chunk_length": None,
        "silence_duration": 0.25,
        "output_dir": None,
        "feed_base_url": "",
        "tags": True,
        "tag_sentiment": True,
        "tag_sigh": True,
    }
    kwargs[field] = value

    with pytest.raises(ValueError, match=message):
        _build_request(**kwargs)


def test_generate_wav_returns_structured_mcp_payload(tmp_path, monkeypatch) -> None:
    captured_feed_base_url: list[str] = []

    async def fake_generate_with_dependencies(request, *, logger):
        captured_feed_base_url.append(request.feed_base_url)
        output_path = request.output_dir / "recap.wav"
        metadata_path = request.output_dir / "recap.json"
        feed_path = request.output_dir / "speekify-feed.xml"
        output_path.write_text("wav", encoding="utf-8")
        metadata_path.write_text("{}", encoding="utf-8")
        feed_path.write_text("<rss />", encoding="utf-8")
        return GenerationResult(
            output_path=output_path,
            artifact=SynthesisArtifact(
                wav="wav",
                duration_seconds=3.25,
                batch_count=2,
                prepared_text=PreparedText(
                    original_text=request.source_text,
                    text="Bonjour.",
                    reformatted=False,
                    removed_characters=(),
                    removed_character_count=0,
                ),
            ),
            content=ExtractedContent(text="Bonjour.", title="Recap"),
            metadata_path=metadata_path,
            feed_path=feed_path,
        )

    monkeypatch.setattr("speekify.mcp_server._generate_with_dependencies", fake_generate_with_dependencies)

    result = asyncio.run(
        generate_wav(
            "Bonjour.",
            title="Recap",
            voice="m5",
            language_code="FR",
            output_dir=str(tmp_path),
            feed_base_url="https://audio.example.com/speekify/",
        )
    )

    assert captured_feed_base_url == ["https://audio.example.com/speekify"]
    assert result["output_path"] == str((tmp_path / "recap.wav").resolve())
    assert result["output_uri"] == (tmp_path / "recap.wav").resolve().as_uri()
    assert result["metadata_path"] == str((tmp_path / "recap.json").resolve())
    assert result["metadata_uri"] == (tmp_path / "recap.json").resolve().as_uri()
    assert result["feed_path"] == str((tmp_path / "speekify-feed.xml").resolve())
    assert result["feed_uri"] == (tmp_path / "speekify-feed.xml").resolve().as_uri()
    assert result["duration_seconds"] == 3.25
    assert result["batch_count"] == 2
    assert result["title"] == "Recap"
    assert result["text_length"] == len("Bonjour.")
    assert result["warnings"] == []
    assert str(result["log_path"]).endswith("logs/speekify.log")


def test_generate_wav_returns_supplied_title_in_structured_payload(tmp_path, monkeypatch) -> None:
    async def fake_generate_with_dependencies(request, *, logger):
        output_path = request.output_dir / "custom-title.wav"
        output_path.write_text("wav", encoding="utf-8")
        return GenerationResult(
            output_path=output_path,
            artifact=SynthesisArtifact(
                wav="wav",
                duration_seconds=3.25,
                batch_count=2,
                prepared_text=PreparedText(
                    original_text=request.source_text,
                    text="Bonjour.",
                    reformatted=False,
                    removed_characters=(),
                    removed_character_count=0,
                ),
            ),
            content=ExtractedContent(text="Bonjour.", title="Extracted title"),
        )

    monkeypatch.setattr("speekify.mcp_server._generate_with_dependencies", fake_generate_with_dependencies)

    result = asyncio.run(
        generate_wav(
            "Bonjour.",
            title="Custom title",
            voice="m5",
            language_code="FR",
            output_dir=str(tmp_path),
        )
    )

    assert result["title"] == "Custom title"


def test_create_mcp_server_registers_fastmcp_instance() -> None:
    server = create_mcp_server()

    assert server.name == "Speekify"
