from __future__ import annotations

import asyncio

import pytest

from speekify.application import build_generation_request
from speekify.extract import ExtractedContent
from speekify.mcp_server import (
    create_mcp_server,
    generate_batch_wav,
    generate_wav,
    generation_defaults,
)
from speekify.temporal_models import (
    BatchItemResultV1,
    BatchWorkflowResultV1,
    GenerationWorkflowResultV1,
)
from speekify.tts import PreparedText, SynthesisArtifact
from speekify.workflow import GenerationResult


@pytest.fixture(autouse=True)
def local_data_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SPEEKIFY_DATA_DIR", str(tmp_path / "speekify-data"))


def test_generation_defaults_are_mcp_serializable() -> None:
    defaults = generation_defaults()

    assert defaults["language_code"] == "auto"
    assert defaults["voice"] == "M5"
    assert defaults["english_islands"] is True
    assert "fr" in defaults["supported_languages"]
    assert "M5" in defaults["voices"]
    assert defaults["speed_range"] == {"min": 0.7, "max": 2.0}
    assert defaults["steps_range"] == {"min": 1, "max": 100}


def test_generation_request_normalizes_and_validates_options(tmp_path) -> None:
    request = build_generation_request(
        source_text="  Bonjour le monde  ",
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
    )

    assert request.source_text == "Bonjour le monde"
    assert request.title == "Recap du jour"
    assert request.voice == "M1"
    assert request.language_code == "fr"
    assert request.english_islands is False
    assert request.english_lexicon_path == tmp_path / "english.txt"
    assert request.output_dir == tmp_path


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("voice", "robot", "Voice must be one of"),
        ("language_code", "xx", "Language code must be one of"),
        ("source_text", "   ", "A text source or URL is required"),
    ],
)
def test_generation_request_rejects_invalid_mcp_inputs(field: str, value: str, message: str) -> None:
    kwargs = {
        "source_text": "Bonjour",
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
    }
    kwargs[field] = value

    with pytest.raises(ValueError, match=message):
        build_generation_request(**kwargs)


def test_generate_wav_returns_structured_mcp_payload(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SPEEKIFY_DATA_DIR", str(tmp_path / "data"))
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
    assert str(result["log_path"]).endswith("data/runtime/speekify.log")


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


def test_generate_wav_prefers_durable_text_length(tmp_path, monkeypatch) -> None:
    async def fake_generate_with_dependencies(request, *, logger):
        output_path = request.output_dir / "durable.wav"
        output_path.write_text("wav", encoding="utf-8")
        return GenerationResult(
            output_path=output_path,
            artifact=SynthesisArtifact(
                wav=None,
                duration_seconds=1.0,
                batch_count=1,
                prepared_text=PreparedText("", "", False, (), 0),
            ),
            content=ExtractedContent(text="", title="Durable title"),
            text_length=123,
        )

    monkeypatch.setattr(
        "speekify.mcp_server._generate_with_dependencies",
        fake_generate_with_dependencies,
    )

    result = asyncio.run(generate_wav("Private input", output_dir=str(tmp_path)))

    assert result["title"] == "Durable title"
    assert result["text_length"] == 123


def test_generation_request_can_use_user_config_defaults(tmp_path, monkeypatch) -> None:
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
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SPEEKIFY_CONFIG", str(config_path))

    request = build_generation_request(
        source_text="Bonjour",
        is_url_mode=False,
        title="",
        voice="M5",
        custom_style_path=None,
        language_code="auto",
        speed=0.98,
        steps=10,
        max_chunk_length=None,
        silence_duration=0.25,
        english_islands=True,
        english_lexicon_path=None,
        output_dir=None,
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


def test_create_mcp_server_registers_fastmcp_instance() -> None:
    server = create_mcp_server()

    assert server.name == "Speekify"


def test_generate_batch_wav_returns_itemized_payload(tmp_path, monkeypatch) -> None:
    async def fake_run_batch(sources, **kwargs):
        generation = GenerationWorkflowResultV1(
            job_id="job",
            workflow_id="workflow",
            request_fingerprint="fingerprint",
            output_path=str(tmp_path / "one.wav"),
            output_sha256="hash",
            output_size=8,
            title="One",
            language_code="en",
            text_length=3,
            duration_seconds=1.0,
            batch_count=1,
        )
        return BatchWorkflowResultV1(
            batch_id="batch",
            workflow_id="batch-workflow",
            items=[
                BatchItemResultV1(
                    index=0,
                    source_id="source",
                    display_name="one.txt",
                    status="completed",
                    generation=generation,
                )
            ],
            completed_count=1,
            failed_count=0,
            cancelled_count=0,
        )

    monkeypatch.setattr("speekify.mcp_server.run_batch", fake_run_batch)
    result = asyncio.run(generate_batch_wav(["one.txt"], output_dir=str(tmp_path)))

    assert result["completed_count"] == 1
    assert result["items"][0]["output_path"] == str(tmp_path / "one.wav")
