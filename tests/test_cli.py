from __future__ import annotations

from io import StringIO
import re

from speekify.__main__ import _build_doctor_report, main
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

    async def fake_run_generation(request, **_: object) -> GenerationResult:
        assert request.source_text == "Hello from the CLI"
        assert request.output_dir == tmp_path
        assert request.language_code == "auto"
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

    monkeypatch.setattr("speekify.application.run_generation", fake_run_generation)

    exit_code = main(["Hello", "from", "the", "CLI"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert str(tmp_path / "hello-from-the-cli-20260528-120000.wav") in stdout
    assert "1.50s" in stdout


def test_main_passes_explicit_language_code(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    async def fake_run_generation(request, **_: object) -> GenerationResult:
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

    monkeypatch.setattr("speekify.application.run_generation", fake_run_generation)

    exit_code = main(["--lang", "fr", "Hello"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert str(tmp_path / "fr.wav") in stdout


def test_main_passes_supertonic_generation_options(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    voice_style_path = tmp_path / "voice.json"
    voice_style_path.write_text("{}", encoding="utf-8")

    async def fake_run_generation(request, **_: object) -> GenerationResult:
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

    monkeypatch.setattr("speekify.application.run_generation", fake_run_generation)

    exit_code = main(
        [
            "--custom-style-path",
            str(voice_style_path),
            "--max-chunk-length",
            "240",
            "--silence-duration",
            "0.2",
            "Hello",
        ]
    )
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert str(tmp_path / "options.wav") in stdout


def test_main_does_not_warn_for_batching_or_reformatting(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    async def fake_run_generation(request, **_: object) -> GenerationResult:
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

    monkeypatch.setattr("speekify.application.run_generation", fake_run_generation)

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
    async def fake_run_generation(*_: object, **__: object) -> GenerationResult:
        raise ValueError("Text contains characters unsupported by Supertonic: '世'")

    monkeypatch.setattr("speekify.application.run_generation", fake_run_generation)

    exit_code = main(["Hello", "世"])
    stderr = capsys.readouterr().err

    assert exit_code == 1
    assert "Remove or replace" in stderr
    assert "Log file:" not in stderr


def test_main_verbose_prints_log_path_on_error(monkeypatch, capsys) -> None:
    async def fake_run_generation(*_: object, **__: object) -> GenerationResult:
        raise RuntimeError("Model failed to load")

    monkeypatch.setattr("speekify.application.run_generation", fake_run_generation)

    exit_code = main(["--verbose", "Hello"])
    stderr = capsys.readouterr().err

    assert exit_code == 1
    assert "Model failed to load" in stderr
    assert "Log file:" in stderr
    assert "logs/speekify.log" in stderr


def test_main_writes_generation_errors_to_default_log(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    async def fake_run_generation(*_: object, **__: object) -> GenerationResult:
        raise RuntimeError("Model failed to load")

    monkeypatch.setattr("speekify.application.run_generation", fake_run_generation)

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
        assert "Maintenance:" in stdout
        assert "speekify --version" in stdout
        assert "speekify --doctor" in stdout
    else:
        raise AssertionError("main() should exit after printing help")


def test_main_reads_stdin_when_available(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    async def fake_run_generation(request, **_: object) -> GenerationResult:
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

    monkeypatch.setattr("speekify.application.run_generation", fake_run_generation)
    monkeypatch.setattr("sys.stdin", FakeStdin("Hello via stdin"))

    exit_code = main([])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert str(tmp_path / "stdin.wav") in stdout


def test_main_dry_run_renders_inspection(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    async def fake_run_inspection(request, **_: object):
        from speekify.tts import PreparedText
        from speekify.workflow import GenerationInspection

        assert request.source_text == "Hello preview"
        return GenerationInspection(
            output_path=tmp_path / "hello-preview.wav",
            title="Hello preview",
            content=ExtractedContent(text="Hello preview"),
            prepared_text=PreparedText(
                original_text="Hello preview",
                text="Hello preview",
                reformatted=False,
                removed_characters=(),
                removed_character_count=0,
            ),
            source_mode="text",
        )

    monkeypatch.setattr("speekify.application.run_inspection", fake_run_inspection)

    exit_code = main(["--dry-run", "Hello", "preview"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert "Inspection ready" in stdout
    assert "hello-preview.wav" in stdout


def test_main_uses_user_config_defaults(tmp_path, monkeypatch, capsys) -> None:
    config_path = tmp_path / "config.toml"
    output_dir = tmp_path / "configured-output"
    config_path.write_text(
        "\n".join(
            [
                "[generation]",
                'voice = "F4"',
                'language_code = "en"',
                "speed = 1.3",
                "steps = 24",
                f'output_dir = "{output_dir}"',
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SPEEKIFY_CONFIG", str(config_path))

    async def fake_run_generation(request, **_: object) -> GenerationResult:
        assert request.voice == "F4"
        assert request.language_code == "en"
        assert request.speed == 1.3
        assert request.steps == 24
        assert request.output_dir == output_dir
        return GenerationResult(
            output_path=output_dir / "configured.wav",
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

    monkeypatch.setattr("speekify.application.run_generation", fake_run_generation)

    exit_code = main(["Hello"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert str(output_dir / "configured.wav") in stdout


def test_main_prints_version(monkeypatch, capsys) -> None:
    monkeypatch.setattr("speekify.__main__._get_version", lambda: "9.9.9")

    exit_code = main(["--version"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert "9.9.9" in stdout


def test_main_short_version_flag_prints_version(monkeypatch, capsys) -> None:
    monkeypatch.setattr("speekify.__main__._get_version", lambda: "9.9.9")

    exit_code = main(["-v"])
    stdout = capsys.readouterr().out

    assert exit_code == 0
    assert "9.9.9" in stdout


def test_main_doctor_reports_runtime(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "speekify.__main__._build_doctor_report",
        lambda: [
            ("Version", "0.0.3", "ok"),
            ("Python", "3.11.9", "ok"),
            ("Supertonic model", "ready", "ok"),
            ("Dependency supertonic", "available", "ok"),
        ],
    )

    exit_code = main(["--doctor"])
    stdout = _normalize_console_output(capsys.readouterr().out)

    assert exit_code == 0
    assert "Doctor" in stdout
    assert "Version" in stdout
    assert "0.0.3" in stdout
    assert "Doctor checks passed." in stdout


def test_main_doctor_fails_when_dependency_is_missing(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "speekify.__main__._build_doctor_report",
        lambda: [("Dependency supertonic", "missing", "error")],
    )

    exit_code = main(["--doctor"])
    captured = capsys.readouterr()
    stdout = _normalize_console_output(captured.out)
    stderr = _normalize_console_output(captured.err)

    assert exit_code == 1
    assert "Dependency supertonic" in stdout
    assert "missing" in stdout
    assert "Doctor found one or more problems." in stderr
    assert "speekify setup" in stderr


def test_build_doctor_report_checks_dependencies_and_models(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "speekify.__main__.configure_logger",
        lambda verbose=False: (object(), tmp_path / "logs" / "speekify.log"),
    )
    monkeypatch.setattr(
        "speekify.__main__._doctor_runtime_report",
        lambda log_path: [("Log path", str(log_path), "ok")],
    )
    monkeypatch.setattr(
        "speekify.__main__._doctor_dependencies",
        lambda: (("supertonic", "Dependency supertonic"),),
    )
    monkeypatch.setattr(
        "speekify.__main__._check_dependency",
        lambda module_name, *, label: (label, f"checked {module_name}", "ok"),
    )
    monkeypatch.setattr(
        "speekify.__main__._doctor_model_checks",
        lambda: (("Supertonic model", lambda: "engine"), ("Translation model", lambda: "backend")),
    )
    monkeypatch.setattr(
        "speekify.__main__._check_model_load",
        lambda label, *, load_model, logger: (label, str(load_model()), "ok"),
    )

    report = _build_doctor_report()

    assert report == [
        ("Log path", str(tmp_path / "logs" / "speekify.log"), "ok"),
        ("Dependency supertonic", "checked supertonic", "ok"),
        ("Supertonic model", "engine", "ok"),
        ("Translation model", "backend", "ok"),
    ]


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
