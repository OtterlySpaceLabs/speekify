from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import Annotated, Any

import click
import typer
from rich import box
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from speekify.config import (
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
    VOICE_NAMES,
)
from speekify.console import console, error_console
from speekify.logging_utils import configure_logger

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _build_cli_epilog() -> str:
    examples = [
        "Examples:",
        '  speekify "Hello world"',
        '  speekify --lang fr "Hello world"',
        '  speekify --lang ja https://example.com/article',
        "  printf 'Hello from stdin' | speekify",
        "  speekify setup --help",
        "",
        f"Supported languages: {', '.join(SUPPORTED_TTS_LANGUAGES)}",
        f"Use {UNKNOWN_TTS_LANGUAGE} for language-agnostic synthesis if needed.",
    ]
    return "\n".join(examples)


GENERATION_HELP = (
    "Generate a local WAV file from text, stdin, or a readable URL.\n\n" + _build_cli_epilog()
)
SETUP_HELP = "Download and warm up the models used by Speekify."


def _parse_language_code(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in SUPPORTED_TTS_LANGUAGES:
        available = ", ".join(SUPPORTED_TTS_LANGUAGES)
        raise typer.BadParameter(
            "Language code must be supported by Supertonic. "
            f"Available values: {available}"
        )
    return normalized


def _parse_voice_name(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in VOICE_NAMES:
        available = ", ".join(VOICE_NAMES)
        raise typer.BadParameter(f"Voice must be one of: {available}")
    return normalized


SourceArgument = Annotated[
    list[str] | None,
    typer.Argument(
        metavar="SOURCE...",
        help="Text to synthesize or a single URL to extract. Omit only when using stdin.",
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
OutputDirOption = Annotated[
    Path | None,
    typer.Option("--output-dir", help="Directory where the WAV file is written."),
]
VerboseOption = Annotated[
    bool,
    typer.Option("--verbose", help="Show technical diagnostics such as log file paths."),
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
        "--tag-sentiment",
        help="Use optional CardiffNLP sentiment signals when placing speech tags.",
    ),
]
TagSighOption = Annotated[
    bool,
    typer.Option(
        "--tag-sigh",
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


@generation_app.command(help=GENERATION_HELP)
def generation_command(
    source: SourceArgument = None,
    url: UrlOption = False,
    title: TitleOption = "",
    voice: VoiceOption = DEFAULT_VOICE,
    language_code: LanguageOption = DEFAULT_TTS_LANG,
    speed: SpeedOption = DEFAULT_SPEED,
    steps: StepsOption = DEFAULT_STEPS,
    output_dir: OutputDirOption = None,
    tags: TagsOption = True,
    tag_sentiment: TagSentimentOption = False,
    tag_sigh: TagSighOption = False,
    verbose: VerboseOption = False,
) -> int:
    return _run_generation(
        source=source,
        is_url_mode=url,
        title=title,
        voice=voice,
        language_code=language_code,
        speed=speed,
        steps=steps,
        output_dir=output_dir,
        tags=tags,
        tag_sentiment=tag_sentiment,
        tag_sigh=tag_sigh,
        verbose=verbose,
    )


@setup_app.command(help=SETUP_HELP)
def setup_command(
    skip_translation: SkipTranslationOption = False,
    verbose: VerboseOption = False,
) -> int:
    return _run_setup(skip_translation=skip_translation, verbose=verbose)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "setup":
        return _invoke_typer(setup_app, argv[1:], prog_name="speekify setup")
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
    language_code: str,
    speed: float,
    steps: int,
    output_dir: Path | None,
    tags: bool,
    tag_sentiment: bool,
    tag_sigh: bool,
    verbose: bool,
) -> int:
    source_text = _read_source(source)
    if source_text is None:
        raise click.UsageError("A text source, URL, or stdin is required.")

    logger, log_path = configure_logger(verbose=verbose)
    synthesizer = _build_synthesizer()
    translator = _build_translator()
    tagging_config = _build_tagging_config(
        enabled=tags,
        use_sentiment=tag_sentiment,
        enable_sigh=tag_sigh,
    )
    tagger = _build_tagger(tagging_config)

    try:
        with console.status(_format_status("starting"), spinner="dots") as status:

            def update_status(message: str) -> None:
                status.update(_format_status(message))

            generation = asyncio.run(
                generate_audio(
                    _build_generation_request(
                        source_text=source_text,
                        voice=voice,
                        language_code=language_code,
                        speed=speed,
                        steps=steps,
                        title=title.strip(),
                        is_url_mode=is_url_mode,
                        output_dir=output_dir or Path.cwd(),
                        tagging_config=tagging_config,
                    ),
                    synthesizer=synthesizer,
                    translator=translator,
                    tagger=tagger,
                    logger=logger,
                    status_callback=update_status,
                )
            )
    except Exception as exc:
        logger.exception("CLI generation failed")
        _render_runtime_error(exc, log_path=log_path, verbose=verbose)
        return 1

    _render_generation_success(generation, log_path=log_path if verbose else None)
    return 0


def _run_setup(*, skip_translation: bool, verbose: bool) -> int:
    logger, log_path = configure_logger(verbose=verbose)
    synthesizer = _build_synthesizer()
    translator = _build_translator()
    include_translation = not skip_translation

    try:
        _warm_up_models(
            synthesizer=synthesizer,
            translator=translator,
            include_translation=include_translation,
            logger=logger,
        )
    except Exception as exc:
        logger.exception("CLI setup failed")
        _render_runtime_error(exc, log_path=log_path, verbose=verbose)
        return 1

    _render_setup_success(include_translation=include_translation, log_path=log_path if verbose else None)
    return 0


def _build_synthesizer() -> object:
    from speekify.tts import SupertonicSynthesizer

    return SupertonicSynthesizer()


def _build_translator() -> object:
    from speekify.translation import HuggingFaceTranslator

    return HuggingFaceTranslator()


def _build_tagging_config(*, enabled: bool, use_sentiment: bool, enable_sigh: bool) -> object:
    from speekify.tagging import TaggingConfig

    return TaggingConfig(
        enabled=enabled,
        use_sentiment=enabled and use_sentiment,
        enable_sigh=enabled and enable_sigh,
    )


def _build_tagger(tagging_config: object) -> object:
    from speekify.tagging import SupertoneTagger
    from speekify.tagging.cardiff import CardiffSentimentAnalyzer

    sentiment_analyzer = None
    if getattr(tagging_config, "use_sentiment", False):
        sentiment_analyzer = CardiffSentimentAnalyzer()
    return SupertoneTagger(config=tagging_config, sentiment_analyzer=sentiment_analyzer)


def _build_generation_request(**kwargs: Any) -> object:
    from speekify.workflow import GenerationRequest

    return GenerationRequest(**kwargs)


def generate_audio(*args: Any, **kwargs: Any) -> Awaitable[Any]:
    from speekify.workflow import generate_audio as run_generate_audio

    return run_generate_audio(*args, **kwargs)


def _warm_up_models(
    *,
    synthesizer: object,
    translator: object,
    include_translation: bool,
    logger: logging.Logger,
) -> None:
    logger.info("Warmup started include_translation=%s", include_translation)
    warmups: list[tuple[str, Callable[[], object]]] = [
        ("Supertonic model", lambda: getattr(synthesizer, "engine")),
    ]
    if include_translation:
        warmups.append(("Translation model", lambda: getattr(translator, "backend")))

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task_id = progress.add_task("Preparing models", total=len(warmups))
        for label, load_model in warmups:
            progress.update(task_id, description=label)
            load_model()
            progress.advance(task_id)

    logger.info("Warmup finished include_translation=%s", include_translation)


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


def _format_status(message: str) -> str:
    labels = {
        "starting": "Preparing Speekify",
        "extracting URL": "Extracting readable page text",
        "checking language": "Checking input language",
        "translating to French": "Translating to French",
        "preparing text": "Preparing text",
        "annotating text": "Adding speech cues",
        "loading model": "Loading speech model",
        "synthesizing": "Generating speech",
        "saving": "Saving WAV file",
    }
    return f"[cyan]{labels.get(message, message.capitalize())}...[/cyan]"


def _format_error_message(error: Exception, *, log_path: Path | None = None) -> str:
    message = str(error).strip() or error.__class__.__name__
    if "unsupported by Supertonic" in message:
        message = f"{message}. Remove or replace these characters, then run Speekify again."
    elif "Text cannot be empty" in message:
        message = "The input text is empty. Provide text, a URL, or piped stdin."

    if log_path is not None:
        message = f"{message}\nLog file: {log_path}"
    return message


def _render_cli_error(error: click.exceptions.ClickException) -> None:
    error_console.print(
        Panel(
            error.format_message(),
            title="Error",
            title_align="left",
            border_style="red",
            box=box.ROUNDED,
        )
    )


def _render_runtime_error(error: Exception, *, log_path: Path, verbose: bool) -> None:
    error_console.print(
        Panel(
            _format_error_message(error, log_path=log_path if verbose else None),
            title="Error",
            title_align="left",
            border_style="red",
            box=box.ROUNDED,
        )
    )


def _render_generation_success(generation: Any, *, log_path: Path | None) -> None:
    table = Table(show_header=False, box=box.SIMPLE, expand=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("File", str(generation.output_path))
    table.add_row("Duration", f"{generation.artifact.duration_seconds:.2f}s")
    table.add_row("Batches", str(generation.artifact.batch_count))
    if log_path is not None:
        table.add_row("Log", str(log_path))

    console.print(
        Panel(
            table,
            title="Audio ready",
            title_align="left",
            border_style="green",
            box=box.ROUNDED,
        )
    )
    console.print(
        f"Saved: {generation.output_path}",
        style="green",
        no_wrap=True,
        overflow="ignore",
        crop=False,
    )
    console.print(f"Duration: {generation.artifact.duration_seconds:.2f}s", style="green")
    _render_warnings(generation.artifact.summary_notes())


def _render_setup_success(*, include_translation: bool, log_path: Path | None) -> None:
    table = Table(show_header=False, box=box.SIMPLE, expand=False)
    table.add_column("Model", style="bold")
    table.add_column("Status")
    table.add_row("Supertonic model", "ready")
    table.add_row("Translation model", "ready" if include_translation else "skipped")
    if log_path is not None:
        table.add_row("Log", str(log_path))

    console.print(
        Panel(
            table,
            title="Setup complete",
            title_align="left",
            border_style="green",
            box=box.ROUNDED,
        )
    )
    console.print("Supertonic model ready.", style="green")
    if include_translation:
        console.print("Translation model ready.", style="green")
    else:
        console.print("Translation model skipped.", style="yellow")


def _render_warnings(notes: Sequence[str]) -> None:
    if not notes:
        return

    warning_table = Table(show_header=False, box=box.SIMPLE, expand=False)
    warning_table.add_column("Kind", style="yellow")
    warning_table.add_column("Message")
    for note in notes:
        warning_table.add_row("Warning", note)

    console.print(
        Panel(
            warning_table,
            title="Attention",
            title_align="left",
            border_style="yellow",
            box=box.ROUNDED,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
