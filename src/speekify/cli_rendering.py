from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import click
from rich import box
from rich.panel import Panel
from rich.table import Table

from speekify.console import console, error_console

DOCTOR_REMEDIATION = "Run `speekify setup` to download or repair the local models."


def format_status(message: str) -> str:
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
        "writing metadata": "Writing metadata and podcast feed",
        "building preview": "Building preview",
    }
    return f"[cyan]{labels.get(message, message.capitalize())}...[/cyan]"


def format_error_message(error: Exception, *, log_path: Path | None = None) -> str:
    message = str(error).strip() or error.__class__.__name__
    if "unsupported by Supertonic" in message:
        message = f"{message}. Remove or replace these characters, then run Speekify again."
    elif "Text cannot be empty" in message:
        message = "The input text is empty. Provide text, a URL, or piped stdin."

    if log_path is not None:
        message = f"{message}\nLog file: {log_path}"
    return message


def render_cli_error(error: click.exceptions.ClickException) -> None:
    error_console.print(
        Panel(
            error.format_message(),
            title="Error",
            title_align="left",
            border_style="red",
            box=box.ROUNDED,
        )
    )


def render_runtime_error(error: Exception, *, log_path: Path, verbose: bool) -> None:
    error_console.print(
        Panel(
            format_error_message(error, log_path=log_path if verbose else None),
            title="Error",
            title_align="left",
            border_style="red",
            box=box.ROUNDED,
        )
    )


def render_generation_success(generation: Any, *, log_path: Path | None) -> None:
    table = Table(show_header=False, box=box.SIMPLE, expand=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("File", str(generation.output_path))
    if getattr(generation, "metadata_path", None) is not None:
        table.add_row("Metadata", str(generation.metadata_path))
    if getattr(generation, "feed_path", None) is not None:
        table.add_row("Podcast feed", str(generation.feed_path))
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
    if getattr(generation, "metadata_path", None) is not None:
        console.print(f"Metadata: {generation.metadata_path}", style="green")
    if getattr(generation, "feed_path", None) is not None:
        console.print(f"Podcast feed: {generation.feed_path}", style="green")
    console.print(f"Duration: {generation.artifact.duration_seconds:.2f}s", style="green")
    render_warnings(generation.artifact.summary_notes())


def render_inspection_success(inspection: Any, *, log_path: Path | None) -> None:
    table = Table(show_header=False, box=box.SIMPLE, expand=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Mode", inspection.source_mode)
    table.add_row("Title", inspection.title)
    table.add_row("Planned file", str(inspection.output_path))
    table.add_row("Planned feed", str(inspection.feed_path))
    table.add_row("Text characters", str(len(inspection.content.text)))
    table.add_row("Prepared characters", str(len(inspection.prepared_text.text)))
    if inspection.tag_counts:
        table.add_row(
            "Tags",
            ", ".join(f"{tag}: {count}" for tag, count in sorted(inspection.tag_counts.items())),
        )
    else:
        table.add_row("Tags", "none")
    table.add_row("Sentiment", "used" if inspection.sentiment_used else "not used")
    if inspection.english_lexicon_terms:
        table.add_row("English lexicon", str(inspection.english_lexicon_terms))
    if log_path is not None:
        table.add_row("Log", str(log_path))

    console.print(
        Panel(
            table,
            title="Inspection ready",
            title_align="left",
            border_style="green",
            box=box.ROUNDED,
        )
    )
    console.print(f"Planned: {inspection.output_path}", style="green")
    console.print(f"Podcast feed: {inspection.feed_path}", style="green")
    render_warnings(inspection.prepared_text.summary_notes())


def render_setup_success(
    *,
    include_translation: bool,
    include_sentiment: bool,
    log_path: Path | None,
) -> None:
    table = Table(show_header=False, box=box.SIMPLE, expand=False)
    table.add_column("Model", style="bold")
    table.add_column("Status")
    table.add_row("Supertonic model", "ready")
    table.add_row("Translation model", "ready" if include_translation else "skipped")
    table.add_row("Emotion model", "ready" if include_sentiment else "skipped")
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
    console.print("Translation model ready." if include_translation else "Translation model skipped.", style="green" if include_translation else "yellow")
    console.print("Emotion model ready." if include_sentiment else "Emotion model skipped.", style="green" if include_sentiment else "yellow")


def render_doctor_report(report: Sequence[tuple[str, str, str]]) -> None:
    table = Table(show_header=False, box=box.SIMPLE, expand=False)
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Value")

    has_errors = False
    for label, value, status in report:
        if status == "error":
            has_errors = True
        style = "green" if status == "ok" else "red"
        table.add_row(label, f"[{style}]{status}[/{style}]", value)

    console.print(
        Panel(
            table,
            title="Doctor",
            title_align="left",
            border_style="green" if not has_errors else "yellow",
            box=box.ROUNDED,
        )
    )
    if has_errors:
        error_console.print("Doctor found one or more problems.", style="yellow")
        error_console.print(DOCTOR_REMEDIATION, style="yellow")
    else:
        console.print("Doctor checks passed.", style="green")


def render_feed_status(
    inspection: Any,
    *,
    title: str,
    feed_path: Path,
    log_path: Path | None,
) -> None:
    table = Table(show_header=False, box=box.SIMPLE, expand=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Output directory", str(inspection.output_dir))
    table.add_row("Feed", str(feed_path))
    table.add_row("Entries", str(inspection.entry_count))
    table.add_row("Invalid metadata", str(len(inspection.invalid_metadata_paths)))
    table.add_row("Missing audio", str(len(inspection.missing_audio_paths)))
    if log_path is not None:
        table.add_row("Log", str(log_path))

    console.print(
        Panel(
            table,
            title=title,
            title_align="left",
            border_style="green" if inspection.ok else "yellow",
            box=box.ROUNDED,
        )
    )
    for path in inspection.invalid_metadata_paths[:5]:
        error_console.print(f"Invalid metadata: {path}", style="yellow")
    for path in inspection.missing_audio_paths[:5]:
        error_console.print(f"Missing audio: {path}", style="yellow")


def render_warnings(notes: Sequence[str]) -> None:
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