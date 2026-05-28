from __future__ import annotations

from io import StringIO

from speekify.__main__ import main
from speekify.extract import ExtractedContent
from speekify.tts import PreparedText, SynthesisArtifact
from speekify.workflow import GenerationResult


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
        assert request.language_code == "en"
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


def test_main_help_lists_supported_languages(capsys) -> None:
    try:
        main(["--help"])
    except SystemExit as exc:
        stdout = capsys.readouterr().out
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


def test_main_setup_warms_supertonic_and_translation(monkeypatch, capsys) -> None:
    warmed: list[bool] = []

    def fake_warm_up_models(**kwargs: object) -> None:
        warmed.append(bool(kwargs["include_translation"]))

    monkeypatch.setattr("speekify.__main__._build_synthesizer", object)
    monkeypatch.setattr("speekify.__main__._build_translator", object)
    monkeypatch.setattr("speekify.__main__._warm_up_models", fake_warm_up_models)

    exit_code = main(["setup"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert warmed == [True]
    assert "Supertonic model ready." in stdout
    assert "Translation model ready." in stdout


def test_main_setup_can_skip_translation(monkeypatch, capsys) -> None:
    warmed: list[bool] = []

    def fake_warm_up_models(**kwargs: object) -> None:
        warmed.append(bool(kwargs["include_translation"]))

    monkeypatch.setattr("speekify.__main__._build_synthesizer", object)
    monkeypatch.setattr("speekify.__main__._build_translator", object)
    monkeypatch.setattr("speekify.__main__._warm_up_models", fake_warm_up_models)

    exit_code = main(["setup", "--skip-translation"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert warmed == [False]
    assert "Translation model skipped." in stdout