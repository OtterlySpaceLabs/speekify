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
from speekify.application import build_generation_request, run_generation
from speekify.logging_utils import configure_logger
from speekify.workflow import GenerationRequest, GenerationResult

TransportName = Literal["stdio", "streamable-http"]


def generation_defaults() -> dict[str, object]:
    """Return MCP-friendly defaults and ranges for Speekify generation."""
    return {
        "language_code": DEFAULT_TTS_LANG,
        "voice": DEFAULT_VOICE,
        "speed": DEFAULT_SPEED,
        "steps": DEFAULT_STEPS,
        "silence_duration": DEFAULT_SILENCE_DURATION,
        "english_islands": True,
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
    english_islands: bool = True,
    english_lexicon_path: str | None = None,
    output_dir: str | None = None,
    feed_base_url: str = "",
    tags: bool = True,
    tag_sentiment: bool = True,
    tag_sigh: bool = True,
    use_user_config: bool = True,
    verbose: bool = False,
) -> dict[str, object]:
    """Generate a local WAV file from text or URL content for MCP clients."""
    request = build_generation_request(
        source_text=source,
        is_url_mode=is_url_mode,
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
        feed_base_url=feed_base_url,
        tags=tags,
        tag_sentiment=tag_sentiment,
        tag_sigh=tag_sigh,
        use_user_config=use_user_config,
    )
    logger, log_path = configure_logger(verbose=verbose)
    generation = await _generate_with_dependencies(request, logger=logger)
    return _serialize_generation(request, generation, log_path=log_path)


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
    english_islands: bool = True,
    english_lexicon_path: str | None = None,
    output_dir: str | None,
    feed_base_url: str = "",
    tags: bool = True,
    tag_sentiment: bool = True,
    tag_sigh: bool = True,
    use_user_config: bool = True,
):
    return build_generation_request(
        source_text=source,
        is_url_mode=is_url_mode,
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
        feed_base_url=feed_base_url,
        tags=tags,
        tag_sentiment=tag_sentiment,
        tag_sigh=tag_sigh,
        use_user_config=use_user_config,
    )


async def _generate_with_dependencies(request, *, logger: logging.Logger) -> GenerationResult:
    return await run_generation(request, logger=logger, dependency_mode="cached")


def _serialize_generation(
    request: GenerationRequest,
    generation: GenerationResult,
    *,
    log_path: Path,
) -> dict[str, object]:
    output_path = generation.output_path.resolve()
    metadata_path = generation.metadata_path.resolve() if generation.metadata_path is not None else None
    feed_path = generation.feed_path.resolve() if generation.feed_path is not None else None
    return {
        "output_path": str(output_path),
        "output_uri": output_path.as_uri(),
        "metadata_path": str(metadata_path) if metadata_path is not None else "",
        "metadata_uri": metadata_path.as_uri() if metadata_path is not None else "",
        "feed_path": str(feed_path) if feed_path is not None else "",
        "feed_uri": feed_path.as_uri() if feed_path is not None else "",
        "duration_seconds": generation.artifact.duration_seconds,
        "batch_count": generation.artifact.batch_count,
        "title": request.title or generation.content.best_title(),
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
        english_islands: bool = True,
        english_lexicon_path: str | None = None,
        output_dir: str | None = None,
        feed_base_url: str = "",
        tags: bool = True,
        tag_sentiment: bool = True,
        tag_sigh: bool = True,
        use_user_config: bool = True,
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
            english_islands=english_islands,
            english_lexicon_path=english_lexicon_path,
            output_dir=output_dir,
            feed_base_url=feed_base_url,
            tags=tags,
            tag_sentiment=tag_sentiment,
            tag_sigh=tag_sigh,
            use_user_config=use_user_config,
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
