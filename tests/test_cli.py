from __future__ import annotations

from io import StringIO
import re

from speekify.__main__ import main
from speekify.extract import ExtractedContent
from speekify.tts import PreparedText, SynthesisArtifact
from speekify.workflow import GenerationResult


def _normalize_console_output(text: str) -> str:
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    return " ".join(text.split())


def test_main_without_input_requires_source(monkeypatch, capsys) -> None:
    class FakeTtyStdin(StringIO):
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr("sys.stdin", FakeTtyStdin(""))

    try:
        main([])
    except SystemExit as exc:
        stderr = capsys.readouterr().err
        assert exc.code == 2
        assert "text source, URL, or stdin" in stderr
    else:
        raise AssertionError("main() should exit when no source or stdin is provided")


def test_main_generates_from_cli_text_into_current_directory(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    async def fake_generate_audio(request, **_: object) -> GenerationResult:
        assert request.source_text == "Hello from the CLI"
        assert request.output_dir == tmp_path
        assert request.language_code == "fr"
        assert request.voice == "M5"
        assert request.speed == 0.98
        assert request.steps == 10
        assert request.silence_duration == 0.25
        output_path = tmp_path / "hello-from-the-cli-20260528-120000.wav"
        return GenerationResult(
            output_path=output_path,
            artifact=SynthesisArtifact(
                wav="wav",
                duration_seconds=1.5,
                batch_count=1,
                prepared_text=PreparedText(
                    original_text=request.source_text,
                    text=request.source_text,
                    reformatted=False,
                    removed_characters=(),
                    removed_character_count=0,
                ),
            ),
            content=ExtractedContent(text=request.source_text),
        )

    monkeypatch.setattr("speekify.__main__.generate_audio", fake_generate_audio)
    monkeypatch.setattr("speekify.__main__._build_synthesizer", object)
    monkeypatch.setattr("speekify.__main__._build_translator", object)

    exit_code = main(["Hello", "from", "the", "CLI"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert str(tmp_path / "hello-from-the-cli-20260528-120000.wav") in stdout
    assert "1.50s" in stdout


def test_main_passes_explicit_language_code(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    async def fake_generate_audio(request, **_: object) -> GenerationResult:
        assert request.language_code == "fr"
        return GenerationResult(
            output_path=tmp_path / "fr.wav",
            artifact=SynthesisArtifact(
                wav="wav",
                duration_seconds=0.5,
                batch_count=1,
                prepared_text=PreparedText(
                    original_text=request.source_text,
                    text=request.source_text,
                    reformatted=False,
                    removed_characters=(),
                    removed_character_count=0,
                ),
            ),
            content=ExtractedContent(text=request.source_text),
        )

    monkeypatch.setattr("speekify.__main__.generate_audio", fake_generate_audio)
    monkeypatch.setattr("speekify.__main__._build_synthesizer", object)
    monkeypatch.setattr("speekify.__main__._build_translator", object)

    exit_code = main(["--lang", "fr", "Hello"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert str(tmp_path / "fr.wav") in stdout


def test_main_passes_supertonic_generation_options(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    voice_style_path = tmp_path / "voice.json"
    voice_style_path.write_text("{}", encoding="utf-8")

    async def fake_generate_audio(request, **_: object) -> GenerationResult:
        assert request.voice_style_path == voice_style_path
        assert request.max_chunk_length == 240
        assert request.silence_duration == 0.2
        return GenerationResult(
            output_path=tmp_path / "options.wav",
            artifact=SynthesisArtifact(
                wav="wav",
                duration_seconds=0.5,
                batch_count=1,
                prepared_text=PreparedText(
                    original_text=request.source_text,
                    text=request.source_text,
                    reformatted=False,
                    removed_characters=(),
                    removed_character_count=0,
                ),
            ),
            content=ExtractedContent(text=request.source_text),
        )

    monkeypatch.setattr("speekify.__main__.generate_audio", fake_generate_audio)
    monkeypatch.setattr("speekify.__main__._build_synthesizer", object)
    monkeypatch.setattr("speekify.__main__._build_translator", object)

    exit_code = main([
        "--custom-style-path",
        str(voice_style_path),
        "--max-chunk-length",
        "240",
        "--silence-duration",
        "0.2",
        "Hello",
    ])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert str(tmp_path / "options.wav") in stdout


def test_main_enables_emotion_tagging_by_default(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    fake_tagger = object()

    def fake_build_tagger(tagging_config: object) -> object:
        assert getattr(tagging_config, "enabled") is True
        assert getattr(tagging_config, "use_sentiment") is True
        assert getattr(tagging_config, "enable_sigh") is True
        return fake_tagger

    async def fake_generate_audio(request, **kwargs: object) -> GenerationResult:
        assert request.tagging_config.enabled is True
        assert request.tagging_config.use_sentiment is True
        assert request.tagging_config.enable_sigh is True
        assert kwargs["tagger"] is fake_tagger
        return GenerationResult(
            output_path=tmp_path / "emotion-tags.wav",
            artifact=SynthesisArtifact(
                wav="wav",
                duration_seconds=0.5,
                batch_count=1,
                prepared_text=PreparedText(
                    original_text=request.source_text,
                    text=request.source_text,
                    reformatted=False,
                    removed_characters=(),
                    removed_character_count=0,
                ),
            ),
            content=ExtractedContent(text=request.source_text),
        )

    monkeypatch.setattr("speekify.__main__.generate_audio", fake_generate_audio)
    monkeypatch.setattr("speekify.__main__._build_synthesizer", object)
    monkeypatch.setattr("speekify.__main__._build_translator", object)
    monkeypatch.setattr("speekify.__main__._build_tagger", fake_build_tagger)

    exit_code = main(["Hello"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert str(tmp_path / "emotion-tags.wav") in stdout


def test_main_can_keep_simple_tag_rules_without_emotion(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    fake_tagger = object()

    def fake_build_tagger(tagging_config: object) -> object:
        assert getattr(tagging_config, "enabled") is True
        assert getattr(tagging_config, "use_sentiment") is False
        assert getattr(tagging_config, "enable_sigh") is False
        return fake_tagger

    async def fake_generate_audio(request, **kwargs: object) -> GenerationResult:
        assert request.tagging_config.enabled is True
        assert request.tagging_config.use_sentiment is False
        assert request.tagging_config.enable_sigh is False
        assert kwargs["tagger"] is fake_tagger
        return GenerationResult(
            output_path=tmp_path / "simple-tags.wav",
            artifact=SynthesisArtifact(
                wav="wav",
                duration_seconds=0.5,
                batch_count=1,
                prepared_text=PreparedText(
                    original_text=request.source_text,
                    text=request.source_text,
                    reformatted=False,
                    removed_characters=(),
                    removed_character_count=0,
                ),
            ),
            content=ExtractedContent(text=request.source_text),
        )

    monkeypatch.setattr("speekify.__main__.generate_audio", fake_generate_audio)
    monkeypatch.setattr("speekify.__main__._build_synthesizer", object)
    monkeypatch.setattr("speekify.__main__._build_translator", object)
    monkeypatch.setattr("speekify.__main__._build_tagger", fake_build_tagger)

    exit_code = main(["--no-tag-sentiment", "--no-tag-sigh", "Hello"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert str(tmp_path / "simple-tags.wav") in stdout


def test_main_passes_disabled_tagging_config(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    fake_tagger = object()

    def fake_build_tagger(tagging_config: object) -> object:
        assert getattr(tagging_config, "enabled") is False
        assert getattr(tagging_config, "use_sentiment") is False
        assert getattr(tagging_config, "enable_sigh") is False
        return fake_tagger

    async def fake_generate_audio(request, **kwargs: object) -> GenerationResult:
        assert request.tagging_config.enabled is False
        assert kwargs["tagger"] is fake_tagger
        return GenerationResult(
            output_path=tmp_path / "no-tags.wav",
            artifact=SynthesisArtifact(
                wav="wav",
                duration_seconds=0.5,
                batch_count=1,
                prepared_text=PreparedText(
                    original_text=request.source_text,
                    text=request.source_text,
                    reformatted=False,
                    removed_characters=(),
                    removed_character_count=0,
                ),
            ),
            content=ExtractedContent(text=request.source_text),
        )

    monkeypatch.setattr("speekify.__main__.generate_audio", fake_generate_audio)
    monkeypatch.setattr("speekify.__main__._build_synthesizer", object)
    monkeypatch.setattr("speekify.__main__._build_translator", object)
    monkeypatch.setattr("speekify.__main__._build_tagger", fake_build_tagger)

    exit_code = main(["--no-tags", "Hello"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert str(tmp_path / "no-tags.wav") in stdout


def test_main_does_not_warn_for_batching_or_reformatting(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    async def fake_generate_audio(request, **_: object) -> GenerationResult:
        return GenerationResult(
            output_path=tmp_path / "batched.wav",
            artifact=SynthesisArtifact(
                wav="wav",
                duration_seconds=3.0,
                batch_count=3,
                prepared_text=PreparedText(
                    original_text=request.source_text,
                    text="Hello from Speekify.",
                    reformatted=True,
                    removed_characters=(),
                    removed_character_count=0,
                ),
            ),
            content=ExtractedContent(text=request.source_text),
        )

    monkeypatch.setattr("speekify.__main__.generate_audio", fake_generate_audio)
    monkeypatch.setattr("speekify.__main__._build_synthesizer", object)
    monkeypatch.setattr("speekify.__main__._build_translator", object)

    exit_code = main(["Hello", "from", "Speekify"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert "Batches" in stdout
    assert "3" in stdout
    assert "Attention" not in stdout
    assert "Warning" not in stdout


def test_main_rejects_invalid_language_code(capsys) -> None:
    try:
        main(["--lang", "en-US", "Hello"])
    except SystemExit as exc:
        stderr = capsys.readouterr().err
        assert exc.code == 2
        assert "supported by Supertonic" in stderr
        assert "na" in stderr
    else:
        raise AssertionError("main() should exit for an invalid language code")


def test_main_prints_hint_for_unsupported_characters(monkeypatch, capsys) -> None:
    async def fake_generate_audio(*_: object, **__: object) -> GenerationResult:
        raise ValueError("Text contains characters unsupported by Supertonic: '世'")

    monkeypatch.setattr("speekify.__main__.generate_audio", fake_generate_audio)
    monkeypatch.setattr("speekify.__main__._build_synthesizer", object)
    monkeypatch.setattr("speekify.__main__._build_translator", object)

    exit_code = main(["Hello", "世"])
    stderr = capsys.readouterr().err

    assert exit_code == 1
    assert "Remove or replace" in stderr
    assert "Log file:" not in stderr


def test_main_verbose_prints_log_path_on_error(monkeypatch, capsys) -> None:
    async def fake_generate_audio(*_: object, **__: object) -> GenerationResult:
        raise RuntimeError("Model failed to load")

    monkeypatch.setattr("speekify.__main__.generate_audio", fake_generate_audio)
    monkeypatch.setattr("speekify.__main__._build_synthesizer", object)
    monkeypatch.setattr("speekify.__main__._build_translator", object)

    exit_code = main(["--verbose", "Hello"])
    stderr = capsys.readouterr().err

    assert exit_code == 1
    assert "Model failed to load" in stderr
    assert "Log file:" in stderr
    assert "logs/speekify.log" in stderr


def test_main_writes_generation_errors_to_default_log(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    async def fake_generate_audio(*_: object, **__: object) -> GenerationResult:
        raise RuntimeError("Model failed to load")

    monkeypatch.setattr("speekify.__main__.generate_audio", fake_generate_audio)
    monkeypatch.setattr("speekify.__main__._build_synthesizer", object)
    monkeypatch.setattr("speekify.__main__._build_translator", object)

    exit_code = main(["Hello"])
    capsys.readouterr()

    content = (tmp_path / "logs" / "speekify.log").read_text(encoding="utf-8")
    assert exit_code == 1
    assert "Logger configured" in content
    assert "CLI generation failed" in content
    assert "RuntimeError: Model failed to load" in content


def test_main_help_lists_supported_languages(capsys) -> None:
    try:
        main(["--help"])
    except SystemExit as exc:
        stdout = _normalize_console_output(capsys.readouterr().out)
        assert exc.code == 0
        assert "Supported languages:" in stdout
        assert "en, ko, ja" in stdout
        assert "speekify --lang fr" in stdout
    else:
        raise AssertionError("main() should exit after printing help")


def test_main_reads_stdin_when_available(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    async def fake_generate_audio(request, **_: object) -> GenerationResult:
        assert request.source_text == "Hello via stdin"
        return GenerationResult(
            output_path=tmp_path / "stdin.wav",
            artifact=SynthesisArtifact(
                wav="wav",
                duration_seconds=0.8,
                batch_count=1,
                prepared_text=PreparedText(
                    original_text=request.source_text,
                    text=request.source_text,
                    reformatted=False,
                    removed_characters=(),
                    removed_character_count=0,
                ),
            ),
            content=ExtractedContent(text=request.source_text),
        )

    class FakeStdin(StringIO):
        def isatty(self) -> bool:
            return False

    monkeypatch.setattr("speekify.__main__.generate_audio", fake_generate_audio)
    monkeypatch.setattr("speekify.__main__._build_synthesizer", object)
    monkeypatch.setattr("speekify.__main__._build_translator", object)
    monkeypatch.setattr("sys.stdin", FakeStdin("Hello via stdin"))

    exit_code = main([])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert str(tmp_path / "stdin.wav") in stdout


def test_main_setup_warms_supertonic_translation_and_sentiment(monkeypatch, capsys) -> None:
    warmed: list[tuple[bool, bool]] = []

    def fake_warm_up_models(**kwargs: object) -> None:
        warmed.append((bool(kwargs["include_translation"]), bool(kwargs["include_sentiment"])))

    monkeypatch.setattr("speekify.__main__._build_synthesizer", object)
    monkeypatch.setattr("speekify.__main__._build_translator", object)
    monkeypatch.setattr("speekify.__main__._build_sentiment_analyzer", object)
    monkeypatch.setattr("speekify.__main__._warm_up_models", fake_warm_up_models)

    exit_code = main(["setup"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert warmed == [(True, True)]
    assert "Supertonic model ready." in stdout
    assert "Translation model ready." in stdout
    assert "Emotion model ready." in stdout


def test_main_setup_can_skip_translation(monkeypatch, capsys) -> None:
    warmed: list[tuple[bool, bool]] = []

    def fake_warm_up_models(**kwargs: object) -> None:
        warmed.append((bool(kwargs["include_translation"]), bool(kwargs["include_sentiment"])))

    monkeypatch.setattr("speekify.__main__._build_synthesizer", object)
    monkeypatch.setattr("speekify.__main__._build_translator", object)
    monkeypatch.setattr("speekify.__main__._build_sentiment_analyzer", object)
    monkeypatch.setattr("speekify.__main__._warm_up_models", fake_warm_up_models)

    exit_code = main(["setup", "--skip-translation"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert warmed == [(False, True)]
    assert "Translation model skipped." in stdout
    assert "Emotion model ready." in stdout


def test_main_setup_can_skip_sentiment(monkeypatch, capsys) -> None:
    warmed: list[tuple[bool, bool]] = []

    def fake_warm_up_models(**kwargs: object) -> None:
        warmed.append((bool(kwargs["include_translation"]), bool(kwargs["include_sentiment"])))

    monkeypatch.setattr("speekify.__main__._build_synthesizer", object)
    monkeypatch.setattr("speekify.__main__._build_translator", object)
    monkeypatch.setattr("speekify.__main__._build_sentiment_analyzer", object)
    monkeypatch.setattr("speekify.__main__._warm_up_models", fake_warm_up_models)

    exit_code = main(["setup", "--skip-sentiment"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert warmed == [(True, False)]
    assert "Translation model ready." in stdout
    assert "Emotion model skipped." in stdout