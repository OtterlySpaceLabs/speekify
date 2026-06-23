from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from speekify.config import (
    DEFAULT_SILENCE_DURATION,
    DEFAULT_SPEED,
    DEFAULT_STEPS,
    DEFAULT_TTS_LANG,
    DEFAULT_VOICE,
)
from speekify.dependencies import (
    CachedGenerationDependencyFactory,
    GenerationDependencies,
    GenerationDependencyFactories,
    build_generation_dependencies,
)
from speekify.tagging import TaggingConfig
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

DependencyMode = Literal["fresh", "cached"]
DependencyBuilder = Callable[[TaggingConfig], GenerationDependencies]
TaggerFactory = Callable[[TaggingConfig], object]

_DEPENDENCY_CACHE = CachedGenerationDependencyFactory()
_GENERATION_LOCK: asyncio.Lock | None = None


def build_tagging_config(*, enabled: bool, use_sentiment: bool, enable_sigh: bool) -> TaggingConfig:
    return TaggingConfig(
        enabled=enabled,
        use_sentiment=enabled and use_sentiment,
        enable_sigh=enabled and enable_sigh,
    )


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
    tags: bool,
    tag_sentiment: bool,
    tag_sigh: bool,
    use_user_config: bool = True,
) -> GenerationRequest:
    user_config = load_user_config() if use_user_config else UserConfig()
    voice = config_value(voice, DEFAULT_VOICE, user_config.voice)
    custom_style_path = config_value(custom_style_path, None, user_config.custom_style_path)
    language_code = config_value(language_code, DEFAULT_TTS_LANG, user_config.language_code)
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
    tags = config_value(tags, True, user_config.tags)
    tag_sentiment = config_value(tag_sentiment, True, user_config.tag_sentiment)
    tag_sigh = config_value(tag_sigh, True, user_config.tag_sigh)

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
        tagging_config=build_tagging_config(
            enabled=tags,
            use_sentiment=tag_sentiment,
            enable_sigh=tag_sigh,
        ),
    )


async def run_generation(
    request: GenerationRequest,
    *,
    logger: logging.Logger,
    status_callback: Callable[[str], None] | None = None,
    dependency_mode: DependencyMode = "fresh",
    dependency_builder: DependencyBuilder | None = None,
) -> GenerationResult:
    dependencies = _resolve_dependencies(
        request.tagging_config,
        dependency_mode=dependency_mode,
        dependency_builder=dependency_builder,
    )
    if dependency_mode == "cached":
        async with _generation_lock():
            return await generate_audio(
                request,
                synthesizer=dependencies.synthesizer,
                translator=dependencies.translator,
                tagger=dependencies.tagger,
                logger=logger,
                status_callback=status_callback,
            )

    return await generate_audio(
        request,
        synthesizer=dependencies.synthesizer,
        translator=dependencies.translator,
        tagger=dependencies.tagger,
        logger=logger,
        status_callback=status_callback,
    )


async def run_inspection(
    request: GenerationRequest,
    *,
    logger: logging.Logger,
    status_callback: Callable[[str], None] | None = None,
    dependency_mode: DependencyMode = "fresh",
    dependency_builder: DependencyBuilder | None = None,
) -> GenerationInspection:
    dependencies = _resolve_dependencies(
        request.tagging_config,
        dependency_mode=dependency_mode,
        dependency_builder=dependency_builder,
    )
    return await inspect_generation(
        request,
        translator=dependencies.translator,
        tagger=dependencies.tagger,
        logger=logger,
        status_callback=status_callback,
    )


def _expand_path(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    return Path(value).expanduser()


def build_runtime_dependencies(
    tagging_config: TaggingConfig,
    *,
    dependency_mode: DependencyMode = "fresh",
    factories: GenerationDependencyFactories | None = None,
    tagger_factory: TaggerFactory | None = None,
) -> GenerationDependencies:
    if dependency_mode == "cached" and factories is None and tagger_factory is None:
        return _DEPENDENCY_CACHE.build(tagging_config)
    return build_generation_dependencies(
        tagging_config,
        factories=factories,
        tagger_factory=tagger_factory,
    )


def _resolve_dependencies(
    tagging_config: TaggingConfig,
    *,
    dependency_mode: DependencyMode,
    dependency_builder: DependencyBuilder | None,
) -> GenerationDependencies:
    if dependency_builder is not None:
        return dependency_builder(tagging_config)
    return build_runtime_dependencies(tagging_config, dependency_mode=dependency_mode)


def _generation_lock() -> asyncio.Lock:
    global _GENERATION_LOCK
    if _GENERATION_LOCK is None:
        _GENERATION_LOCK = asyncio.Lock()
    return _GENERATION_LOCK