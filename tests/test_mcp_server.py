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
    assert defaults["english_islands"] is True
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
        english_islands=False,
        english_lexicon_path=str(tmp_path / "english.txt"),
        output_dir=str(tmp_path),
        tags=True,
        tag_sentiment=False,
        tag_sigh=True,
    )

    assert request.source_text == "Bonjour le monde"
    assert request.title == "Recap du jour"
    assert request.voice == "M1"
    assert request.language_code == "fr"
    assert request.english_islands is False
    assert request.english_lexicon_path == tmp_path / "english.txt"
    assert request.output_dir == tmp_path
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
        "english_islands": True,
        "english_lexicon_path": None,
        "output_dir": None,
        "tags": True,
        "tag_sentiment": True,
        "tag_sigh": True,
    }
    kwargs[field] = value

    with pytest.raises(ValueError, match=message):
        _build_request(**kwargs)


def test_generate_wav_returns_structured_mcp_payload(tmp_path, monkeypatch) -> None:
    async def fake_generate_with_dependencies(request, *, logger):
        output_path = request.output_dir / "recap.wav"
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
            content=ExtractedContent(text="Bonjour.", title="Recap"),
        )

    monkeypatch.setattr("speekify.mcp_server._generate_with_dependencies", fake_generate_with_dependencies)

    result = asyncio.run(
        generate_wav(
            "Bonjour.",
            title="Recap",
            voice="m5",
            language_code="FR",
            output_dir=str(tmp_path),
        )
    )

    assert result["output_path"] == str((tmp_path / "recap.wav").resolve())
    assert result["output_uri"] == (tmp_path / "recap.wav").resolve().as_uri()
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


def test_build_request_can_use_user_config_defaults(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.toml"
    lexicon_path = tmp_path / "lexicon.txt"
    output_dir = tmp_path / "audio"
    config_path.write_text(
        "\n".join(
            [
                "[generation]",
                'voice = "F1"',
                'language_code = "en"',
                "speed = 1.2",
                "steps = 22",
                "max_chunk_length = 180",
                "silence_duration = 0.4",
                "english_islands = false",
                f'english_lexicon_path = "{lexicon_path}"',
                f'output_dir = "{output_dir}"',
                "tags = false",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SPEEKIFY_CONFIG", str(config_path))

    request = _build_request(
        source="Bonjour",
        is_url_mode=False,
        title="",
        voice="M5",
        custom_style_path=None,
        language_code="fr",
        speed=0.98,
        steps=10,
        max_chunk_length=None,
        silence_duration=0.25,
        english_islands=True,
        english_lexicon_path=None,
        output_dir=None,
        tags=True,
        tag_sentiment=True,
        tag_sigh=True,
    )

    assert request.voice == "F1"
    assert request.language_code == "en"
    assert request.speed == 1.2
    assert request.steps == 22
    assert request.max_chunk_length == 180
    assert request.silence_duration == 0.4
    assert request.english_islands is False
    assert request.english_lexicon_path == lexicon_path
    assert request.output_dir == output_dir
    assert request.tagging_config.enabled is False


def test_create_mcp_server_registers_fastmcp_instance() -> None:
    server = create_mcp_server()

    assert server.name == "Speekify"
