from __future__ import annotations

import asyncio
import importlib.util
import logging
import os
import platform
import sys
from collections.abc import Callable, Sequence
from importlib import metadata
from pathlib import Path
from typing import Annotated, Any

import click
import typer

from speekify import application
from speekify.cli_rendering import (
    format_status as _format_status,
    render_cli_error as _render_cli_error,
    render_doctor_report as _render_doctor_report,
    render_generation_success as _render_generation_success,
    render_inspection_success as _render_inspection_success,
    render_runtime_error as _render_runtime_error,
    render_setup_success as _render_setup_success,
)
from speekify.config import (
    DEFAULT_SILENCE_DURATION,
    DEFAULT_SPEED,
    DEFAULT_STEPS,
    DEFAULT_TTS_LANG,
    DEFAULT_VOICE,
    MAX_SPEED,
    MAX_STEPS,
    MIN_SPEED,
    MIN_STEPS,
    SUPPORTED_TTS_LANGUAGES,
    UNKNOWN_TTS_LANGUAGE,
)
from speekify.console import console
from speekify.logging_utils import configure_logger
from speekify.user_config import UserConfig, load_user_config
from speekify.validation import normalize_language_code, normalize_voice_name

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}
PACKAGE_NAME = "speekify"


def _build_cli_epilog() -> str:
    examples = [
        "Examples:",
        '  speekify "Hello world"',
        '  speekify --lang fr "Hello world"',
        "  speekify --lang ja https://example.com/article",
        '  speekify --dry-run "Hello world"',
        '  speekify inspect "Hello world"',
        "  printf 'Hello from stdin' | speekify",
        "",
        "Maintenance:",
        "  speekify --version",
        "  speekify -v",
        "  speekify --doctor",
        "  speekify setup",
        "  speekify setup --help",
        "",
        f"Supported languages: {', '.join(SUPPORTED_TTS_LANGUAGES)}",
        f"Use {UNKNOWN_TTS_LANGUAGE} for language-agnostic synthesis if needed.",
    ]
    return "\n".join(examples)


GENERATION_HELP = (
    "Generate a local WAV file from text, stdin, a readable URL, or a .txt/.md/.pdf file.\n\n"
    + _build_cli_epilog()
)
SETUP_HELP = "Download and warm up the models used by Speekify."
INSPECT_HELP = "Preview extraction, translation, tagging, and output naming without synthesis."


def _parse_language_code(value: str) -> str:
    try:
        return normalize_language_code(value)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _parse_voice_name(value: str) -> str:
    try:
        return normalize_voice_name(value)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


SourceArgument = Annotated[
    list[str] | None,
    typer.Argument(
        metavar="SOURCE...",
        help="Text, a single URL, or a path to a .txt/.md/.pdf file. Omit only when using stdin.",
        show_default=False,
    ),
]
UrlOption = Annotated[
    bool,
    typer.Option("--url", help="Force URL extraction mode even if the source looks like text."),
]
TitleOption = Annotated[
    str,
    typer.Option("--title", help="Output file title without extension."),
]
VoiceOption = Annotated[
    str,
    typer.Option("--voice", callback=_parse_voice_name, help="Supertonic voice: M1-M5 or F1-F5."),
]
CustomStylePathOption = Annotated[
    Path | None,
    typer.Option(
        "--custom-style-path",
        help="Path to a Supertonic voice-style JSON file. Overrides --voice.",
    ),
]
LanguageOption = Annotated[
    str,
    typer.Option(
        "--lang",
        callback=_parse_language_code,
        help="Supertonic ISO 639-1 language code, for example en, fr, ja, or na.",
    ),
]
SpeedOption = Annotated[
    float,
    typer.Option(
        "--speed",
        min=MIN_SPEED,
        max=MAX_SPEED,
        help=f"Playback speed multiplier ({MIN_SPEED}-{MAX_SPEED}).",
    ),
]
StepsOption = Annotated[
    int,
    typer.Option(
        "--steps",
        min=MIN_STEPS,
        max=MAX_STEPS,
        help=f"Synthesis steps ({MIN_STEPS}-{MAX_STEPS}). Higher can improve quality.",
    ),
]
MaxChunkLengthOption = Annotated[
    int | None,
    typer.Option(
        "--max-chunk-length",
        min=10,
        help="Maximum characters per internal Supertonic chunk. Defaults to language auto.",
    ),
]
SilenceDurationOption = Annotated[
    float,
    typer.Option(
        "--silence-duration",
        min=0.0,
        help="Silence between Supertonic chunks in seconds.",
    ),
]
EnglishIslandsOption = Annotated[
    bool,
    typer.Option(
        "--english-islands/--no-english-islands",
        help="Pronounce known English tech terms as English islands when --lang fr.",
    ),
]
EnglishLexiconPathOption = Annotated[
    Path | None,
    typer.Option(
        "--english-lexicon-path",
        help="Optional newline-delimited lexicon of English terms for French synthesis.",
    ),
]
OutputDirOption = Annotated[
    Path | None,
    typer.Option("--output-dir", help="Directory where the WAV file is written."),
]
VerboseOption = Annotated[
    bool,
    typer.Option("--verbose", help="Show technical diagnostics such as log file paths."),
]
DryRunOption = Annotated[
    bool,
    typer.Option("--dry-run", help="Preview the generation plan without loading the speech model."),
]
TagsOption = Annotated[
    bool,
    typer.Option(
        "--tags/--no-tags",
        help="Add sparse Supertonic inline speech tags such as <breath>.",
    ),
]
TagSentimentOption = Annotated[
    bool,
    typer.Option(
        "--tag-sentiment/--no-tag-sentiment",
        help="Use CardiffNLP sentiment signals when placing speech tags.",
    ),
]
TagSighOption = Annotated[
    bool,
    typer.Option(
        "--tag-sigh/--no-tag-sigh",
        help="Allow very rare <sigh> tags when sentiment and rules strongly agree.",
    ),
]
SkipTranslationOption = Annotated[
    bool,
    typer.Option(
        "--skip-translation",
        help="Do not warm up the English-to-French translation model.",
    ),
]
SkipSentimentOption = Annotated[
    bool,
    typer.Option(
        "--skip-sentiment",
        help="Do not warm up the CardiffNLP emotion/sentiment model.",
    ),
]

generation_app = typer.Typer(
    add_completion=False,
    context_settings=CONTEXT_SETTINGS,
    no_args_is_help=False,
    rich_markup_mode="rich",
)
setup_app = typer.Typer(
    add_completion=False,
    context_settings=CONTEXT_SETTINGS,
    no_args_is_help=False,
    rich_markup_mode="rich",
)
inspect_app = typer.Typer(
    add_completion=False,
    context_settings=CONTEXT_SETTINGS,
    no_args_is_help=False,
    rich_markup_mode="rich",
)


@generation_app.command(help=GENERATION_HELP)
def generation_command(
    source: SourceArgument = None,
    url: UrlOption = False,
    title: TitleOption = "",
    voice: VoiceOption = DEFAULT_VOICE,
    custom_style_path: CustomStylePathOption = None,
    language_code: LanguageOption = DEFAULT_TTS_LANG,
    speed: SpeedOption = DEFAULT_SPEED,
    steps: StepsOption = DEFAULT_STEPS,
    max_chunk_length: MaxChunkLengthOption = None,
    silence_duration: SilenceDurationOption = DEFAULT_SILENCE_DURATION,
    english_islands: EnglishIslandsOption = True,
    english_lexicon_path: EnglishLexiconPathOption = None,
    output_dir: OutputDirOption = None,
    tags: TagsOption = True,
    tag_sentiment: TagSentimentOption = True,
    tag_sigh: TagSighOption = True,
    dry_run: DryRunOption = False,
    verbose: VerboseOption = False,
) -> int:
    if dry_run:
        return _run_inspection(
            source=source,
            is_url_mode=url,
            title=title,
            voice=voice,
            custom_style_path=custom_style_path,
            language_code=language_code,
            speed=speed,
            steps=steps,
            max_chunk_length=max_chunk_length,
            silence_duration=silence_duration,
            english_islands=english_islands,
            english_lexicon_path=english_lexicon_path,
            output_dir=output_dir,
            tags=tags,
            tag_sentiment=tag_sentiment,
            tag_sigh=tag_sigh,
            verbose=verbose,
        )
    return _run_generation(
        source=source,
        is_url_mode=url,
        title=title,
        voice=voice,
        custom_style_path=custom_style_path,
        language_code=language_code,
        speed=speed,
        steps=steps,
        max_chunk_length=max_chunk_length,
        silence_duration=silence_duration,
        english_islands=english_islands,
        english_lexicon_path=english_lexicon_path,
        output_dir=output_dir,
        tags=tags,
        tag_sentiment=tag_sentiment,
        tag_sigh=tag_sigh,
        verbose=verbose,
    )


@inspect_app.command(help=INSPECT_HELP)
def inspect_command(
    source: SourceArgument = None,
    url: UrlOption = False,
    title: TitleOption = "",
    voice: VoiceOption = DEFAULT_VOICE,
    custom_style_path: CustomStylePathOption = None,
    language_code: LanguageOption = DEFAULT_TTS_LANG,
    speed: SpeedOption = DEFAULT_SPEED,
    steps: StepsOption = DEFAULT_STEPS,
    max_chunk_length: MaxChunkLengthOption = None,
    silence_duration: SilenceDurationOption = DEFAULT_SILENCE_DURATION,
    english_islands: EnglishIslandsOption = True,
    english_lexicon_path: EnglishLexiconPathOption = None,
    output_dir: OutputDirOption = None,
    tags: TagsOption = True,
    tag_sentiment: TagSentimentOption = True,
    tag_sigh: TagSighOption = True,
    verbose: VerboseOption = False,
) -> int:
    return _run_inspection(
        source=source,
        is_url_mode=url,
        title=title,
        voice=voice,
        custom_style_path=custom_style_path,
        language_code=language_code,
        speed=speed,
        steps=steps,
        max_chunk_length=max_chunk_length,
        silence_duration=silence_duration,
        english_islands=english_islands,
        english_lexicon_path=english_lexicon_path,
        output_dir=output_dir,
        tags=tags,
        tag_sentiment=tag_sentiment,
        tag_sigh=tag_sigh,
        verbose=verbose,
    )


@setup_app.command(help=SETUP_HELP)
def setup_command(
    skip_translation: SkipTranslationOption = False,
    skip_sentiment: SkipSentimentOption = False,
    verbose: VerboseOption = False,
) -> int:
    return _run_setup(
        skip_translation=skip_translation,
        skip_sentiment=skip_sentiment,
        verbose=verbose,
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) == 1 and argv[0] in {"--version", "-v"}:
        console.print(_get_version())
        return 0
    if len(argv) == 1 and argv[0] == "--doctor":
        return _run_doctor()
    if argv and argv[0] == "setup":
        return _invoke_typer(setup_app, argv[1:], prog_name="speekify setup")
    if argv and argv[0] == "inspect":
        return _invoke_typer(inspect_app, argv[1:], prog_name="speekify inspect")
    return _invoke_typer(generation_app, argv, prog_name="speekify")


def _invoke_typer(app: typer.Typer, argv: list[str], *, prog_name: str) -> int:
    help_requested = any(arg in {"-h", "--help"} for arg in argv)
    try:
        result = app(args=argv, prog_name=prog_name, standalone_mode=False)
    except click.exceptions.Exit as exc:
        raise SystemExit(exc.exit_code) from exc
    except click.exceptions.UsageError as exc:
        _render_cli_error(exc)
        raise SystemExit(exc.exit_code) from exc
    except click.exceptions.ClickException as exc:
        _render_cli_error(exc)
        raise SystemExit(exc.exit_code) from exc

    if help_requested:
        raise SystemExit(0)
    return result if isinstance(result, int) else 0


def _run_generation(
    *,
    source: Sequence[str] | None,
    is_url_mode: bool,
    title: str,
    voice: str,
    custom_style_path: Path | None,
    language_code: str,
    speed: float,
    steps: int,
    max_chunk_length: int | None,
    silence_duration: float,
    english_islands: bool,
    english_lexicon_path: Path | None,
    output_dir: Path | None,
    tags: bool,
    tag_sentiment: bool,
    tag_sigh: bool,
    verbose: bool,
) -> int:
    source_text = _read_source(source)
    if source_text is None:
        raise click.UsageError("A text source, URL, or stdin is required.")

    options = _apply_user_config_options(
        voice=voice,
        custom_style_path=custom_style_path,
        language_code=language_code,
        speed=speed,
        steps=steps,
        max_chunk_length=max_chunk_length,
        silence_duration=silence_duration,
        english_islands=english_islands,
        english_lexicon_path=english_lexicon_path,
        output_dir=output_dir,
        tags=tags,
        tag_sentiment=tag_sentiment,
        tag_sigh=tag_sigh,
    )
    logger, log_path = configure_logger(verbose=verbose)
    request = _build_cli_request(
        source_text=source_text,
        is_url_mode=is_url_mode,
        title=title,
        options=options,
    )

    try:
        with console.status(_format_status("starting"), spinner="dots") as status:

            def update_status(message: str) -> None:
                status.update(_format_status(message))

            generation = asyncio.run(
                application.run_generation(
                    request,
                    logger=logger,
                    status_callback=update_status,
                    dependency_builder=_build_generation_dependencies,
                )
            )
    except Exception as exc:
        logger.exception("CLI generation failed")
        _render_runtime_error(exc, log_path=log_path, verbose=verbose)
        return 1

    _render_generation_success(generation, log_path=log_path if verbose else None)
    return 0


def _run_inspection(
    *,
    source: Sequence[str] | None,
    is_url_mode: bool,
    title: str,
    voice: str,
    custom_style_path: Path | None,
    language_code: str,
    speed: float,
    steps: int,
    max_chunk_length: int | None,
    silence_duration: float,
    english_islands: bool,
    english_lexicon_path: Path | None,
    output_dir: Path | None,
    tags: bool,
    tag_sentiment: bool,
    tag_sigh: bool,
    verbose: bool,
) -> int:
    source_text = _read_source(source)
    if source_text is None:
        raise click.UsageError("A text source, URL, or stdin is required.")

    options = _apply_user_config_options(
        voice=voice,
        custom_style_path=custom_style_path,
        language_code=language_code,
        speed=speed,
        steps=steps,
        max_chunk_length=max_chunk_length,
        silence_duration=silence_duration,
        english_islands=english_islands,
        english_lexicon_path=english_lexicon_path,
        output_dir=output_dir,
        tags=tags,
        tag_sentiment=tag_sentiment,
        tag_sigh=tag_sigh,
    )
    logger, log_path = configure_logger(verbose=verbose)
    request = _build_cli_request(
        source_text=source_text,
        is_url_mode=is_url_mode,
        title=title,
        options=options,
    )

    try:
        with console.status(_format_status("starting"), spinner="dots") as status:

            def update_status(message: str) -> None:
                status.update(_format_status(message))

            inspection = asyncio.run(
                application.run_inspection(
                    request,
                    logger=logger,
                    status_callback=update_status,
                    dependency_builder=_build_generation_dependencies,
                )
            )
    except Exception as exc:
        logger.exception("CLI inspection failed")
        _render_runtime_error(exc, log_path=log_path, verbose=verbose)
        return 1

    _render_inspection_success(inspection, log_path=log_path if verbose else None)
    return 0


def _run_setup(*, skip_translation: bool, skip_sentiment: bool, verbose: bool) -> int:
    logger, log_path = configure_logger(verbose=verbose)
    synthesizer = _build_synthesizer()
    translator = _build_translator()
    sentiment_analyzer = _build_sentiment_analyzer()
    include_translation = not skip_translation
    include_sentiment = not skip_sentiment

    try:
        _warm_up_models(
            synthesizer=synthesizer,
            translator=translator,
            sentiment_analyzer=sentiment_analyzer,
            include_translation=include_translation,
            include_sentiment=include_sentiment,
            logger=logger,
        )
    except Exception as exc:
        logger.exception("CLI setup failed")
        _render_runtime_error(exc, log_path=log_path, verbose=verbose)
        return 1

    _render_setup_success(
        include_translation=include_translation,
        include_sentiment=include_sentiment,
        log_path=log_path if verbose else None,
    )
    return 0


def _load_user_config() -> UserConfig:
    return load_user_config()


def _apply_user_config_options(**options: Any) -> dict[str, Any]:
    user_config = _load_user_config()
    configured_options = {
        "voice": user_config.voice,
        "custom_style_path": user_config.custom_style_path,
        "language_code": user_config.language_code,
        "speed": user_config.speed,
        "steps": user_config.steps,
        "max_chunk_length": user_config.max_chunk_length,
        "silence_duration": user_config.silence_duration,
        "english_islands": user_config.english_islands,
        "english_lexicon_path": user_config.english_lexicon_path,
        "output_dir": user_config.output_dir,
        "tags": user_config.tags,
        "tag_sentiment": user_config.tag_sentiment,
        "tag_sigh": user_config.tag_sigh,
    }
    return {
        name: _option_with_config(name, value, configured_options.get(name))
        for name, value in options.items()
    }


def _option_with_config(option_name: str, current_value: Any, configured_value: Any) -> Any:
    if configured_value is None:
        return current_value
    context = click.get_current_context(silent=True)
    if context is None:
        return configured_value if current_value is None else current_value
    source = context.get_parameter_source(option_name)
    if source == click.core.ParameterSource.DEFAULT:
        return configured_value
    return current_value


def _build_cli_request(
    *,
    source_text: str,
    is_url_mode: bool,
    title: str,
    options: dict[str, Any],
) -> object:
    return application.build_generation_request(
        source_text=source_text,
        is_url_mode=is_url_mode,
        title=title,
        voice=options["voice"],
        custom_style_path=options["custom_style_path"],
        language_code=options["language_code"],
        speed=options["speed"],
        steps=options["steps"],
        max_chunk_length=options["max_chunk_length"],
        silence_duration=options["silence_duration"],
        english_islands=options["english_islands"],
        english_lexicon_path=options["english_lexicon_path"],
        output_dir=options["output_dir"] or Path.cwd(),
        tags=options["tags"],
        tag_sentiment=options["tag_sentiment"],
        tag_sigh=options["tag_sigh"],
        use_user_config=False,
    )


def _run_doctor() -> int:
    report = _build_doctor_report()
    has_errors = any(status == "error" for _, _, status in report)
    _render_doctor_report(report)
    return 1 if has_errors else 0


def _get_version() -> str:
    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        return "unknown"


def _build_doctor_report() -> list[tuple[str, str, str]]:
    logger, log_path = configure_logger(verbose=False)
    report = _doctor_runtime_report(log_path)
    report.extend(
        _check_dependency(module_name, label=label) for module_name, label in _doctor_dependencies()
    )
    report.extend(
        _check_model_load(label, load_model=load_model, logger=logger)
        for label, load_model in _doctor_model_checks()
    )
    return report


def _doctor_runtime_report(log_path: Path) -> list[tuple[str, str, str]]:
    return [
        ("Version", _get_version(), "ok"),
        ("Python", sys.version.split()[0], "ok"),
        ("Executable", sys.executable, "ok"),
        ("Platform", platform.platform(), "ok"),
        ("Package", str(Path(__file__).resolve().parent), "ok"),
        _check_log_target(log_path),
    ]


def _doctor_dependencies() -> tuple[tuple[str, str], ...]:
    return (
        ("httpx", "Dependency httpx"),
        ("langdetect", "Dependency langdetect"),
        ("rich", "Dependency rich"),
        ("sacremoses", "Dependency sacremoses"),
        ("sentencepiece", "Dependency sentencepiece"),
        ("supertonic", "Dependency supertonic"),
        ("typer", "Dependency typer"),
        ("torch", "Dependency torch"),
        ("trafilatura", "Dependency trafilatura"),
        ("transformers", "Dependency transformers"),
    )


def _doctor_model_checks() -> tuple[tuple[str, Callable[[], object]], ...]:
    return (
        ("Supertonic model", lambda: getattr(_build_synthesizer(), "engine")),
        ("Translation model", lambda: getattr(_build_translator(), "backend")),
        ("Emotion model", lambda: getattr(_build_sentiment_analyzer(), "backend")),
    )


def _check_log_target(log_path: Path) -> tuple[str, str, str]:
    target_dir = log_path.parent
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return ("Log path", f"unavailable ({exc})", "error")

    if not os_access_writable(target_dir):
        return ("Log path", f"not writable: {target_dir}", "error")
    return ("Log path", str(log_path), "ok")


def os_access_writable(path: Path) -> bool:
    return path.exists() and path.is_dir() and os.access(path, os.W_OK)


def _check_dependency(module_name: str, *, label: str) -> tuple[str, str, str]:
    module_spec = importlib.util.find_spec(module_name)
    if module_spec is None:
        return (label, "missing", "error")
    return (label, "available", "ok")


def _check_model_load(
    label: str,
    *,
    load_model: Callable[[], object],
    logger: logging.Logger,
) -> tuple[str, str, str]:
    try:
        load_model()
    except Exception as exc:
        logger.exception("Doctor check failed for %s", label)
        return (label, str(exc).strip() or exc.__class__.__name__, "error")
    return (label, "ready", "ok")


def _build_synthesizer() -> object:
    from speekify.tts import SupertonicSynthesizer

    return SupertonicSynthesizer()


def _build_translator() -> object:
    from speekify.translation import HuggingFaceTranslator

    return HuggingFaceTranslator()


def _build_sentiment_analyzer() -> object:
    from speekify.dependencies import build_sentiment_analyzer

    return build_sentiment_analyzer()


def _build_tagging_config(*, enabled: bool, use_sentiment: bool, enable_sigh: bool) -> object:
    return application.build_tagging_config(
        enabled=enabled,
        use_sentiment=use_sentiment,
        enable_sigh=enable_sigh,
    )


def _build_tagger(tagging_config: object) -> object:
    from speekify.dependencies import build_tagger

    sentiment_analyzer = None
    if getattr(tagging_config, "use_sentiment", False):
        sentiment_analyzer = _build_sentiment_analyzer()
    return build_tagger(tagging_config, sentiment_analyzer=sentiment_analyzer)


def _build_generation_dependencies(tagging_config: object) -> object:
    from speekify.dependencies import GenerationDependencyFactories

    return application.build_runtime_dependencies(
        tagging_config,
        dependency_mode="fresh",
        factories=GenerationDependencyFactories(
            synthesizer_factory=_build_synthesizer,
            translator_factory=_build_translator,
            sentiment_analyzer_factory=_build_sentiment_analyzer,
        ),
        tagger_factory=_build_tagger,
    )


def _warm_up_models(
    *,
    synthesizer: object,
    translator: object,
    sentiment_analyzer: object,
    include_translation: bool,
    include_sentiment: bool,
    logger: logging.Logger,
) -> None:
    from speekify.setup import warm_up_models

    warm_up_models(
        synthesizer=synthesizer,
        translator=translator,
        sentiment_analyzer=sentiment_analyzer,
        include_translation=include_translation,
        include_sentiment=include_sentiment,
        logger=logger,
    )


def _read_source(source_parts: Sequence[str] | None) -> str | None:
    inline_source = " ".join(source_parts or ()).strip()
    if inline_source:
        return inline_source

    try:
        is_tty = sys.stdin.isatty()
    except OSError:
        return None

    if not is_tty:
        try:
            piped_source = sys.stdin.read().strip()
        except OSError:
            return None
        return piped_source or None

    return None


if __name__ == "__main__":
    raise SystemExit(main())
