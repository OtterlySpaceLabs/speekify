from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from pathlib import Path

from speekify.config import (
    AUTO_TTS_LANGUAGE,
    DEFAULT_SILENCE_DURATION,
    DEFAULT_SPEED,
    DEFAULT_STEPS,
    DEFAULT_VOICE,
)
from speekify.dependencies import build_dependencies
from speekify.user_config import UserConfig, config_value, load_user_config
from speekify.validation import (
    normalize_language_code,
    normalize_source_text,
    normalize_voice_name,
)
from speekify.workflow import (
    GenerationInspection,
    GenerationRequest,
    GenerationResult,
    generate_audio,
    inspect_generation,
)

_GENERATION_LOCK: asyncio.Lock | None = None


def build_generation_request(
    *,
    source_text: str,
    is_url_mode: bool,
    title: str,
    voice: str,
    custom_style_path: str | Path | None,
    language_code: str,
    speed: float,
    steps: int,
    max_chunk_length: int | None,
    silence_duration: float,
    english_islands: bool,
    english_lexicon_path: str | Path | None,
    output_dir: str | Path | None,
    use_user_config: bool = True,
) -> GenerationRequest:
    user_config = load_user_config() if use_user_config else UserConfig()
    voice = config_value(voice, DEFAULT_VOICE, user_config.voice)
    custom_style_path = config_value(custom_style_path, None, user_config.custom_style_path)
    language_code = config_value(language_code, AUTO_TTS_LANGUAGE, user_config.language_code)
    speed = config_value(speed, DEFAULT_SPEED, user_config.speed)
    steps = config_value(steps, DEFAULT_STEPS, user_config.steps)
    max_chunk_length = config_value(max_chunk_length, None, user_config.max_chunk_length)
    silence_duration = config_value(
        silence_duration,
        DEFAULT_SILENCE_DURATION,
        user_config.silence_duration,
    )
    english_islands = config_value(english_islands, True, user_config.english_islands)
    english_lexicon_path = config_value(
        english_lexicon_path,
        None,
        user_config.english_lexicon_path,
    )
    output_dir = config_value(output_dir, None, user_config.output_dir)

    return GenerationRequest(
        source_text=normalize_source_text(source_text),
        voice=normalize_voice_name(voice),
        voice_style_path=_expand_path(custom_style_path),
        language_code=normalize_language_code(language_code),
        speed=speed,
        steps=steps,
        max_chunk_length=max_chunk_length,
        silence_duration=silence_duration,
        english_islands=english_islands,
        english_lexicon_path=_expand_path(english_lexicon_path),
        title=title.strip(),
        is_url_mode=is_url_mode,
        output_dir=_expand_path(output_dir) or Path.cwd(),
    )


async def run_generation(
    request: GenerationRequest,
    *,
    logger: logging.Logger,
    status_callback: Callable[[str], None] | None = None,
    cached: bool = False,
) -> GenerationResult:
    dependencies = build_dependencies(cached=cached)
    # ponytail: cached mode shares one set of models across MCP calls; serialize them.
    lock = _generation_lock() if cached else contextlib.nullcontext()
    async with lock:
        return await generate_audio(
            request,
            synthesizer=dependencies.synthesizer,
            translator=dependencies.translator,
            logger=logger,
            status_callback=status_callback,
        )


async def run_inspection(
    request: GenerationRequest,
    *,
    logger: logging.Logger,
    status_callback: Callable[[str], None] | None = None,
    cached: bool = False,
) -> GenerationInspection:
    dependencies = build_dependencies(cached=cached)
    return await inspect_generation(
        request,
        translator=dependencies.translator,
        logger=logger,
        status_callback=status_callback,
    )


def _expand_path(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    return Path(value).expanduser()


def _generation_lock() -> asyncio.Lock:
    global _GENERATION_LOCK
    if _GENERATION_LOCK is None:
        _GENERATION_LOCK = asyncio.Lock()
    return _GENERATION_LOCK