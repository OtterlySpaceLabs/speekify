from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, RadioButton, RadioSet, Select, TextArea

from speekify.config import (
    DEFAULT_LANG,
    DEFAULT_SILENCE_DURATION,
    DEFAULT_SPEED,
    DEFAULT_STEPS,
    DEFAULT_VOICE,
    MAX_SPEED,
    MAX_STEPS,
    MIN_SPEED,
    MIN_STEPS,
    OUTPUT_DIR,
    VOICE_NAMES,
)
from speekify.extract import ExtractedContent, extract_url, is_single_url_input, normalize_text
from speekify.logging_utils import configure_logger
from speekify.naming import build_output_path
from speekify.tts import SynthesisArtifact, SupertonicSynthesizer
from speekify.translation import HuggingFaceTranslator


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
            source_text = self.query_one("#content", TextArea).text
            voice = str(self.query_one("#voice", Select).value)
            title_input = self.query_one("#title", Input).value.strip()
            speed = float(self.query_one("#speed", Input).value.strip())
            steps = int(self.query_one("#steps", Input).value.strip())
            is_url_mode = self.query_one("#mode-url", RadioButton).value

            self.logger.info(
                "Generation started mode=%s voice=%s steps=%s speed=%s title_supplied=%s text_length=%s",
                "url" if is_url_mode else "text",
                voice,
                steps,
                speed,
                bool(title_input),
                len(source_text.strip()),
            )

            if not MIN_SPEED <= speed <= MAX_SPEED:
                raise ValueError(f"La vitesse doit etre comprise entre {MIN_SPEED} et {MAX_SPEED}.")
            if not MIN_STEPS <= steps <= MAX_STEPS:
                raise ValueError(
                    f"Le nombre de steps doit etre compris entre {MIN_STEPS} et {MAX_STEPS}."
                )

            content = await self._resolve_content(source_text, is_url_mode)
            status.update("preparing text")
            prepared_text = await asyncio.to_thread(self.synthesizer.prepare_text, content.text)
            self.logger.info(
                "Prepared text original_length=%s cleaned_length=%s reformatted=%s removed_count=%s removed_chars=%s",
                len(prepared_text.original_text),
                len(prepared_text.text),
                prepared_text.reformatted,
                prepared_text.removed_character_count,
                prepared_text.removed_characters,
            )

            output_title = title_input or content.best_title()
            output_path = build_output_path(self.output_dir, output_title)
            self.logger.info(
                "Prepared output title=%r path=%s normalized_text_length=%s",
                output_title,
                output_path,
                len(prepared_text.text),
            )

            status.update("loading model")
            await asyncio.to_thread(lambda: self.synthesizer.engine)
            self.logger.info("Model loaded")
            status.update("synthesizing")
            artifact = await asyncio.to_thread(
                self.synthesizer.synthesize_prepared_text,
                prepared_text=prepared_text,
                voice=voice,
                lang=DEFAULT_LANG,
                steps=steps,
                speed=speed,
                silence_duration=DEFAULT_SILENCE_DURATION,
            )
            self.logger.info(
                "Synthesis finished duration=%.2fs batch_count=%s",
                artifact.duration_seconds,
                artifact.batch_count,
            )
            status.update("saving")
            await asyncio.to_thread(self.synthesizer.save_audio, artifact.wav, output_path)
            self.logger.info("Audio saved path=%s", output_path)
        except Exception as exc:
            status.update("error")
            self.logger.exception("Generation failed")
            result.update(self._format_error_message(exc))
            return

        status.update("done")
        result.update(self._format_success_message(output_path, artifact))

    async def _resolve_content(self, raw_input: str, is_url_mode: bool) -> ExtractedContent:
        should_extract_url = is_url_mode or is_single_url_input(raw_input)

        if should_extract_url:
            self.query_one("#status", Label).update("extracting URL")
            extracted = await extract_url(raw_input)
            self.logger.info(
                "URL extracted title=%r text_length=%s autodetected=%s",
                extracted.title,
                len(extracted.text),
                not is_url_mode,
            )
            return await self._translate_content_if_needed(extracted)

        normalized_text = normalize_text(raw_input)
        if not normalized_text:
            raise ValueError("Le texte ne peut pas etre vide.")
        self.logger.info("Text normalized text_length=%s", len(normalized_text))
        return await self._translate_content_if_needed(ExtractedContent(text=normalized_text))

    async def _translate_content_if_needed(self, content: ExtractedContent) -> ExtractedContent:
        self.query_one("#status", Label).update("checking language")
        translation = await asyncio.to_thread(self.translator.maybe_translate_to_french, content.text)
        self.logger.info(
            "Translation checked source_language=%r translated=%s original_length=%s translated_length=%s",
            translation.source_language,
            translation.translated,
            len(content.text),
            len(translation.text),
        )

        if not translation.translated:
            return content

        self.query_one("#status", Label).update("translating to French")
        return ExtractedContent(text=translation.text, title=content.title)

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
