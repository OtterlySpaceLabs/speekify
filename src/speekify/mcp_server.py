from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Literal

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
    VOICE_NAMES,
)
from speekify.logging_utils import configure_logger
from speekify.tagging import TaggingConfig
from speekify.workflow import GenerationRequest, GenerationResult, generate_audio

TransportName = Literal["stdio", "streamable-http"]


def generation_defaults() -> dict[str, object]:
    """Return MCP-friendly defaults and ranges for Speekify generation."""
    return {
        "language_code": DEFAULT_TTS_LANG,
        "voice": DEFAULT_VOICE,
        "speed": DEFAULT_SPEED,
        "steps": DEFAULT_STEPS,
        "silence_duration": DEFAULT_SILENCE_DURATION,
        "supported_languages": list(SUPPORTED_TTS_LANGUAGES),
        "voices": list(VOICE_NAMES),
        "speed_range": {"min": MIN_SPEED, "max": MAX_SPEED},
        "steps_range": {"min": MIN_STEPS, "max": MAX_STEPS},
    }


async def generate_wav(
    source: str,
    *,
    is_url_mode: bool = False,
    title: str = "",
    voice: str = DEFAULT_VOICE,
    custom_style_path: str | None = None,
    language_code: str = DEFAULT_TTS_LANG,
    speed: float = DEFAULT_SPEED,
    steps: int = DEFAULT_STEPS,
    max_chunk_length: int | None = None,
    silence_duration: float = DEFAULT_SILENCE_DURATION,
    output_dir: str | None = None,
    tags: bool = True,
    tag_sentiment: bool = True,
    tag_sigh: bool = True,
    verbose: bool = False,
) -> dict[str, object]:
    """Generate a local WAV file from text or URL content for MCP clients."""
    request = _build_request(
        source=source,
        is_url_mode=is_url_mode,
        title=title,
        voice=voice,
        custom_style_path=custom_style_path,
        language_code=language_code,
        speed=speed,
        steps=steps,
        max_chunk_length=max_chunk_length,
        silence_duration=silence_duration,
        output_dir=output_dir,
        tags=tags,
        tag_sentiment=tag_sentiment,
        tag_sigh=tag_sigh,
    )
    logger, log_path = configure_logger(verbose=verbose)
    generation = await _generate_with_dependencies(request, logger=logger)
    return _serialize_generation(generation, log_path=log_path)


def _build_request(
    *,
    source: str,
    is_url_mode: bool,
    title: str,
    voice: str,
    custom_style_path: str | None,
    language_code: str,
    speed: float,
    steps: int,
    max_chunk_length: int | None,
    silence_duration: float,
    output_dir: str | None,
    tags: bool,
    tag_sentiment: bool,
    tag_sigh: bool,
) -> GenerationRequest:
    normalized_voice = voice.strip().upper()
    if normalized_voice not in VOICE_NAMES:
        available = ", ".join(VOICE_NAMES)
        raise ValueError(f"Voice must be one of: {available}")

    normalized_language = language_code.strip().lower()
    if normalized_language not in SUPPORTED_TTS_LANGUAGES:
        available = ", ".join(SUPPORTED_TTS_LANGUAGES)
        raise ValueError(f"Language code must be one of: {available}")

    source_text = source.strip()
    if not source_text:
        raise ValueError("A text source or URL is required.")

    return GenerationRequest(
        source_text=source_text,
        voice=normalized_voice,
        voice_style_path=Path(custom_style_path).expanduser() if custom_style_path else None,
        language_code=normalized_language,
        speed=speed,
        steps=steps,
        max_chunk_length=max_chunk_length,
        silence_duration=silence_duration,
        title=title.strip(),
        is_url_mode=is_url_mode,
        output_dir=Path(output_dir).expanduser() if output_dir else Path.cwd(),
        tagging_config=TaggingConfig(
            enabled=tags,
            use_sentiment=tags and tag_sentiment,
            enable_sigh=tags and tag_sigh,
        ),
    )


async def _generate_with_dependencies(
    request: GenerationRequest,
    *,
    logger: logging.Logger,
) -> GenerationResult:
    import asyncio

    if not hasattr(_generate_with_dependencies, "_lock"):
        from speekify.translation import HuggingFaceTranslator
        from speekify.tts import SupertonicSynthesizer

        _generate_with_dependencies._lock = asyncio.Lock()  # type: ignore[attr-defined]
        _generate_with_dependencies._translator = HuggingFaceTranslator()  # type: ignore[attr-defined]
        _generate_with_dependencies._synthesizer = SupertonicSynthesizer()  # type: ignore[attr-defined]
        _generate_with_dependencies._sentiment_analyzer = None  # type: ignore[attr-defined]

    from speekify.tagging import SupertoneTagger
    from speekify.tagging.cardiff import CardiffSentimentAnalyzer

    sentiment_analyzer = None
    if request.tagging_config.use_sentiment:
        cached = getattr(_generate_with_dependencies, "_sentiment_analyzer", None)
        if cached is None:
            cached = CardiffSentimentAnalyzer()
            _generate_with_dependencies._sentiment_analyzer = cached  # type: ignore[attr-defined]
        sentiment_analyzer = cached

    tagger = SupertoneTagger(config=request.tagging_config, sentiment_analyzer=sentiment_analyzer)

    async with _generate_with_dependencies._lock:  # type: ignore[attr-defined]
        return await generate_audio(
            request,
            synthesizer=_generate_with_dependencies._synthesizer,  # type: ignore[attr-defined]
            translator=_generate_with_dependencies._translator,  # type: ignore[attr-defined]
            tagger=tagger,
            logger=logger,
        )


def _serialize_generation(generation: GenerationResult, *, log_path: Path) -> dict[str, object]:
    output_path = generation.output_path.resolve()
    return {
        "output_path": str(output_path),
        "output_uri": output_path.as_uri(),
        "duration_seconds": generation.artifact.duration_seconds,
        "batch_count": generation.artifact.batch_count,
        "title": generation.content.best_title(),
        "text_length": len(generation.content.text),
        "warnings": generation.artifact.summary_notes(),
        "log_path": str(log_path.resolve()),
    }


def create_mcp_server() -> Any:
    """Create the Speekify MCP server with generation tools and prompts."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(name="Speekify")

    @mcp.tool(name="speekify_generate_wav")
    async def speekify_generate_wav(
        source: str,
        is_url_mode: bool = False,
        title: str = "",
        voice: str = DEFAULT_VOICE,
        custom_style_path: str | None = None,
        language_code: str = DEFAULT_TTS_LANG,
        speed: float = DEFAULT_SPEED,
        steps: int = DEFAULT_STEPS,
        max_chunk_length: int | None = None,
        silence_duration: float = DEFAULT_SILENCE_DURATION,
        output_dir: str | None = None,
        tags: bool = True,
        tag_sentiment: bool = True,
        tag_sigh: bool = True,
    ) -> dict[str, object]:
        """Convert inline text or readable URL content to a local WAV file."""
        return await generate_wav(
            source,
            is_url_mode=is_url_mode,
            title=title,
            voice=voice,
            custom_style_path=custom_style_path,
            language_code=language_code,
            speed=speed,
            steps=steps,
            max_chunk_length=max_chunk_length,
            silence_duration=silence_duration,
            output_dir=output_dir,
            tags=tags,
            tag_sentiment=tag_sentiment,
            tag_sigh=tag_sigh,
        )

    @mcp.tool(name="speekify_generation_defaults")
    def speekify_generation_defaults() -> dict[str, object]:
        """Return supported voices, languages, and default generation settings."""
        return generation_defaults()

    @mcp.prompt(name="news_recap_to_audio")
    def news_recap_to_audio() -> str:
        """Guide an assistant to summarize sources before calling Speekify."""
        return (
            "Check the requested news sources, summarize the key facts with source URLs, "
            "then call speekify_generate_wav once per source URL and once for the final recap. "
            "Use concise titles so the generated WAV filenames stay readable."
        )

    return mcp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Speekify MCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport to use. Defaults to stdio for local AI clients.",
    )
    args = parser.parse_args(argv)
    create_mcp_server().run(transport=args.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
