from __future__ import annotations

import logging
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, RadioButton, RadioSet, Select, TextArea

from speekify.config import (
    DEFAULT_TRANSLATION_TARGET_LANG,
    DEFAULT_SPEED,
    DEFAULT_STEPS,
    DEFAULT_VOICE,
    OUTPUT_DIR,
    VOICE_NAMES,
)
from speekify.extract import ExtractedContent
from speekify.logging_utils import configure_logger
from speekify.tts import SynthesisArtifact, SupertonicSynthesizer
from speekify.translation import HuggingFaceTranslator
from speekify.workflow import (
    GenerationRequest,
    generate_audio,
    resolve_content,
    translate_content_if_needed,
)


class SpeekifyApp(App[None]):
    CSS = """
    Screen {
        layout: vertical;
    }

    #main {
        height: 1fr;
        padding: 1 2;
    }

    #source-mode {
        height: auto;
        margin-bottom: 1;
    }

    #content {
        height: 1fr;
        min-height: 12;
    }

    #settings {
        height: auto;
        margin-top: 1;
    }

    .setting {
        width: 1fr;
        min-width: 20;
        margin-right: 1;
    }

    #actions {
        height: auto;
        margin-top: 1;
    }

    #status {
        margin-top: 1;
    }

    #result {
        margin-top: 1;
        color: $success;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+enter", "generate", "Generate"),
        ("ctrl+v", "paste", "Paste"),
    ]

    TITLE = "Speekify"
    SUB_TITLE = "French text and URL to WAV"

    def __init__(
        self,
        *,
        output_dir: Path = OUTPUT_DIR,
        log_path: Path | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        super().__init__()
        self.output_dir = output_dir
        self.synthesizer = SupertonicSynthesizer()
        self.translator = HuggingFaceTranslator()
        configured_logger, configured_log_path = configure_logger(log_path)
        self.logger = logger or configured_logger
        self.log_path = configured_log_path

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="main"):
            yield Label("Source mode")
            with RadioSet(id="source-mode"):
                yield RadioButton("Text", value=True, id="mode-text")
                yield RadioButton("URL", id="mode-url")
            yield TextArea(id="content")
            with Horizontal(id="settings"):
                yield Select(
                    [(voice, voice) for voice in VOICE_NAMES],
                    value=DEFAULT_VOICE,
                    prompt="Voice",
                    id="voice",
                    classes="setting",
                )
                yield Input(
                    value=str(DEFAULT_SPEED),
                    placeholder="Speed 0.7..2.0",
                    id="speed",
                    classes="setting",
                )
                yield Input(
                    value=str(DEFAULT_STEPS),
                    placeholder="Steps 1..100",
                    id="steps",
                    classes="setting",
                )
                yield Input(
                    placeholder="Output title (optional)",
                    id="title",
                    classes="setting",
                )
            with Horizontal(id="actions"):
                yield Button("Generate", id="generate", variant="primary")
            yield Label("idle", id="status")
            yield Label("", id="result")
        yield Footer()

    def action_generate(self) -> None:
        self.run_worker(self._generate(), exclusive=True)

    def action_paste(self) -> None:
        paste_action = getattr(self.focused, "action_paste", None)
        if callable(paste_action):
            paste_action()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "generate":
            self.action_generate()

    async def _generate(self) -> None:
        status = self.query_one("#status", Label)
        result = self.query_one("#result", Label)
        status.update("idle")
        result.update("")

        try:
            generation = await generate_audio(
                GenerationRequest(
                    source_text=self.query_one("#content", TextArea).text,
                    voice=str(self.query_one("#voice", Select).value),
                    language_code=DEFAULT_TRANSLATION_TARGET_LANG,
                    title=self.query_one("#title", Input).value.strip(),
                    speed=float(self.query_one("#speed", Input).value.strip()),
                    steps=int(self.query_one("#steps", Input).value.strip()),
                    is_url_mode=self.query_one("#mode-url", RadioButton).value,
                    output_dir=self.output_dir,
                ),
                synthesizer=self.synthesizer,
                translator=self.translator,
                logger=self.logger,
                status_callback=status.update,
            )
        except Exception as exc:
            status.update("error")
            self.logger.exception("Generation failed")
            result.update(self._format_error_message(exc))
            return

        status.update("done")
        result.update(self._format_success_message(generation.output_path, generation.artifact))

    async def _resolve_content(self, raw_input: str, is_url_mode: bool) -> ExtractedContent:
        return await resolve_content(
            raw_input,
            is_url_mode=is_url_mode,
            target_language=DEFAULT_TRANSLATION_TARGET_LANG,
            translator=self.translator,
            logger=self.logger,
            status_callback=self.query_one("#status", Label).update,
        )

    async def _translate_content_if_needed(self, content: ExtractedContent) -> ExtractedContent:
        return await translate_content_if_needed(
            content,
            target_language=DEFAULT_TRANSLATION_TARGET_LANG,
            translator=self.translator,
            logger=self.logger,
            status_callback=self.query_one("#status", Label).update,
        )

    def _format_error_message(self, error: Exception) -> str:
        message = str(error)
        if "caracteres non supportes par Supertonic" in message:
            return f"{message}. Supprime ou remplace ces caracteres. Voir {self.log_path}"
        return f"{message} (voir {self.log_path})"

    def _format_success_message(self, output_path: Path, artifact: SynthesisArtifact) -> str:
        lines = [str(output_path), f"{artifact.duration_seconds:.2f}s"]
        notes = artifact.summary_notes()
        if notes:
            lines.append("Auto: " + "; ".join(notes))
        return "\n".join(lines)
