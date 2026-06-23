from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable

from speekify.config import (
    DEFAULT_TRANSLATION_TARGET_LANG,
    DEFAULT_SILENCE_DURATION,
    MAX_SPEED,
    MAX_STEPS,
    MIN_SPEED,
    MIN_STEPS,
)
from speekify.extract import ExtractedContent, extract_url, is_single_url_input, normalize_text
from speekify.extract_common import is_document_path_input, read_document
from speekify.naming import build_output_path
from speekify.tagging import SupertoneTagger, TaggingConfig
from speekify.multilingual import load_english_lexicon
from speekify.tts import PreparedText, SynthesisArtifact, SupertonicSynthesizer
from speekify.translation import HuggingFaceTranslator

StatusCallback = Callable[[str], None]


@dataclass(frozen=True)
class GenerationRequest:
    source_text: str
    voice: str
    language_code: str
    speed: float
    steps: int
    voice_style_path: Path | None = None
    max_chunk_length: int | None = None
    silence_duration: float = DEFAULT_SILENCE_DURATION
    english_islands: bool = True
    english_lexicon_path: Path | None = None
    tagging_config: TaggingConfig = field(default_factory=TaggingConfig)
    title: str = ""
    is_url_mode: bool = False
    output_dir: Path = Path.cwd()


@dataclass(frozen=True)
class GenerationResult:
    output_path: Path
    artifact: SynthesisArtifact
    content: ExtractedContent


@dataclass(frozen=True)
class GenerationInspection:
    output_path: Path
    title: str
    content: ExtractedContent
    prepared_text: PreparedText
    source_mode: str
    tag_counts: dict[str, int] = field(default_factory=dict)
    sentiment_used: bool = False
    english_lexicon_terms: int = 0


def _update_status(status_callback: StatusCallback | None, message: str) -> None:
    if status_callback is not None:
        status_callback(message)


async def resolve_content(
    raw_input: str,
    *,
    is_url_mode: bool,
    target_language: str,
    translator: HuggingFaceTranslator,
    logger: logging.Logger,
    status_callback: StatusCallback | None = None,
) -> ExtractedContent:
    should_extract_url = is_url_mode or is_single_url_input(raw_input)

    if should_extract_url:
        _update_status(status_callback, "extracting URL")
        extracted = await extract_url(raw_input)
        logger.info(
            "URL extracted title=%r text_length=%s autodetected=%s",
            extracted.title,
            len(extracted.text),
            not is_url_mode,
        )
        return await translate_content_if_needed(
            extracted,
            target_language=target_language,
            translator=translator,
            logger=logger,
            status_callback=status_callback,
        )

    if not is_url_mode and is_document_path_input(raw_input):
        _update_status(status_callback, "reading file")
        content = await asyncio.to_thread(read_document, Path(raw_input.strip()))
        logger.info("File read path=%s text_length=%s", raw_input.strip(), len(content.text))
        return await translate_content_if_needed(
            content,
            target_language=target_language,
            translator=translator,
            logger=logger,
            status_callback=status_callback,
        )

    normalized_text = normalize_text(raw_input)
    if not normalized_text:
        raise ValueError("Text cannot be empty.")
    logger.info("Text normalized text_length=%s", len(normalized_text))
    return await translate_content_if_needed(
        ExtractedContent(text=normalized_text),
        target_language=target_language,
        translator=translator,
        logger=logger,
        status_callback=status_callback,
    )


async def translate_content_if_needed(
    content: ExtractedContent,
    *,
    target_language: str,
    translator: HuggingFaceTranslator,
    logger: logging.Logger,
    status_callback: StatusCallback | None = None,
) -> ExtractedContent:
    if target_language != DEFAULT_TRANSLATION_TARGET_LANG:
        logger.info("Translation skipped target_language=%r", target_language)
        return content

    _update_status(status_callback, "checking language")
    translation = await asyncio.to_thread(translator.maybe_translate_to_french, content.text)
    logger.info(
        "Translation checked source_language=%r translated=%s original_length=%s translated_length=%s",
        translation.source_language,
        translation.translated,
        len(content.text),
        len(translation.text),
    )

    if not translation.translated:
        return content

    _update_status(status_callback, "translating to French")
    return ExtractedContent(text=translation.text, title=content.title)


async def generate_audio(
    request: GenerationRequest,
    *,
    synthesizer: SupertonicSynthesizer,
    translator: HuggingFaceTranslator,
    tagger: SupertoneTagger | None = None,
    logger: logging.Logger,
    status_callback: StatusCallback | None = None,
) -> GenerationResult:
    logger.info(
        "Generation started mode=%s voice=%s custom_style=%s language=%s steps=%s speed=%s max_chunk_length=%s silence_duration=%s title_supplied=%s text_length=%s",
        "url" if request.is_url_mode else "text",
        request.voice,
        bool(request.voice_style_path),
        request.language_code,
        request.steps,
        request.speed,
        request.max_chunk_length,
        request.silence_duration,
        bool(request.title),
        len(request.source_text.strip()),
    )

    _validate_generation_request(request)
    english_lexicon_terms = await _load_english_lexicon_terms(request, logger=logger)

    content = await resolve_content(
        request.source_text,
        is_url_mode=request.is_url_mode,
        target_language=request.language_code,
        translator=translator,
        logger=logger,
        status_callback=status_callback,
    )
    _update_status(status_callback, "preparing text")
    prepared_text = await asyncio.to_thread(synthesizer.prepare_text, content.text)
    logger.info(
        "Prepared text original_length=%s cleaned_length=%s reformatted=%s removed_count=%s removed_chars=%s",
        len(prepared_text.original_text),
        len(prepared_text.text),
        prepared_text.reformatted,
        prepared_text.removed_character_count,
        prepared_text.removed_characters,
    )

    if request.tagging_config.enabled:
        _update_status(status_callback, "annotating text")
        active_tagger = tagger or SupertoneTagger(config=request.tagging_config)
        tagging_result = await asyncio.to_thread(
            active_tagger.tag,
            prepared_text.text,
            language_code=request.language_code,
        )
        logger.info(
            "Speech tags checked changed=%s counts=%s sentiment_used=%s",
            tagging_result.changed,
            dict(tagging_result.tag_counts),
            tagging_result.sentiment_used,
        )
        if tagging_result.changed:
            prepared_text = replace(
                prepared_text,
                text=tagging_result.text,
                reformatted=True,
            )

    output_title = request.title or content.best_title()
    output_path = build_output_path(request.output_dir, output_title)
    logger.info(
        "Prepared output title=%r path=%s normalized_text_length=%s",
        output_title,
        output_path,
        len(prepared_text.text),
    )

    _update_status(status_callback, "loading model")
    await asyncio.to_thread(lambda: synthesizer.engine)
    logger.info("Model loaded")

    _update_status(status_callback, "synthesizing")
    artifact = await asyncio.to_thread(
        synthesizer.synthesize_prepared_text,
        prepared_text=prepared_text,
        voice=request.voice,
        voice_style_path=request.voice_style_path,
        lang=request.language_code,
        steps=request.steps,
        speed=request.speed,
        silence_duration=request.silence_duration,
        max_chunk_length=request.max_chunk_length,
        detect_english_islands=request.english_islands,
        english_lexicon_terms=english_lexicon_terms,
    )
    logger.info(
        "Synthesis finished duration=%.2fs batch_count=%s language_segments=%s",
        artifact.duration_seconds,
        artifact.batch_count,
        [(segment.lang, segment.text) for segment in artifact.language_segments],
    )

    _update_status(status_callback, "saving")
    await asyncio.to_thread(synthesizer.save_audio, artifact.wav, output_path)
    logger.info("Audio saved path=%s", output_path)

    return GenerationResult(
        output_path=output_path,
        artifact=artifact,
        content=content,
    )


async def inspect_generation(
    request: GenerationRequest,
    *,
    translator: HuggingFaceTranslator,
    tagger: SupertoneTagger | None = None,
    logger: logging.Logger,
    status_callback: StatusCallback | None = None,
) -> GenerationInspection:
    logger.info(
        "Generation inspection started mode=%s voice=%s language=%s title_supplied=%s text_length=%s",
        "url" if request.is_url_mode else "text",
        request.voice,
        request.language_code,
        bool(request.title),
        len(request.source_text.strip()),
    )
    _validate_generation_request(request)
    english_lexicon_terms = await _load_english_lexicon_terms(request, logger=logger)

    content = await resolve_content(
        request.source_text,
        is_url_mode=request.is_url_mode,
        target_language=request.language_code,
        translator=translator,
        logger=logger,
        status_callback=status_callback,
    )
    _update_status(status_callback, "preparing text")
    normalized_text = normalize_text(content.text)
    prepared_text = PreparedText(
        original_text=content.text.strip(),
        text=normalized_text,
        reformatted=normalized_text != content.text.strip(),
        removed_characters=(),
        removed_character_count=0,
    )

    tag_counts: dict[str, int] = {}
    sentiment_used = False
    if request.tagging_config.enabled:
        _update_status(status_callback, "annotating text")
        active_tagger = tagger or SupertoneTagger(config=request.tagging_config)
        tagging_result = await asyncio.to_thread(
            active_tagger.tag,
            prepared_text.text,
            language_code=request.language_code,
        )
        tag_counts = dict(tagging_result.tag_counts)
        sentiment_used = tagging_result.sentiment_used
        if tagging_result.changed:
            prepared_text = replace(prepared_text, text=tagging_result.text, reformatted=True)

    output_title = request.title or content.best_title()
    output_path = build_output_path(request.output_dir, output_title)
    _update_status(status_callback, "building preview")
    logger.info(
        "Generation inspection finished title=%r path=%s normalized_text_length=%s",
        output_title,
        output_path,
        len(prepared_text.text),
    )
    return GenerationInspection(
        output_path=output_path,
        title=output_title,
        content=content,
        prepared_text=prepared_text,
        source_mode=_source_mode(request),
        tag_counts=tag_counts,
        sentiment_used=sentiment_used,
        english_lexicon_terms=len(english_lexicon_terms or ()),
    )


def _source_mode(request: GenerationRequest) -> str:
    if request.is_url_mode or is_single_url_input(request.source_text):
        return "url"
    if is_document_path_input(request.source_text):
        return "file"
    return "text"


def _validate_generation_request(request: GenerationRequest) -> None:
    if not MIN_SPEED <= request.speed <= MAX_SPEED:
        raise ValueError(f"Speed must be between {MIN_SPEED} and {MAX_SPEED}.")
    if not MIN_STEPS <= request.steps <= MAX_STEPS:
        raise ValueError(f"Steps must be between {MIN_STEPS} and {MAX_STEPS}.")
    if request.max_chunk_length is not None and request.max_chunk_length < 10:
        raise ValueError("Maximum chunk length must be at least 10 characters.")
    if request.silence_duration < 0:
        raise ValueError("Silence duration cannot be negative.")
    if request.voice_style_path is not None and not request.voice_style_path.expanduser().is_file():
        raise ValueError(f"Custom voice style file does not exist: {request.voice_style_path}")
    if (
        request.english_lexicon_path is not None
        and not request.english_lexicon_path.expanduser().is_file()
    ):
        raise ValueError(f"English lexicon file does not exist: {request.english_lexicon_path}")


async def _load_english_lexicon_terms(
    request: GenerationRequest,
    *,
    logger: logging.Logger,
) -> tuple[str, ...] | None:
    if request.english_lexicon_path is None:
        return None
    english_lexicon_terms = await asyncio.to_thread(
        load_english_lexicon,
        request.english_lexicon_path,
    )
    logger.info(
        "English lexicon loaded path=%s terms=%s",
        request.english_lexicon_path,
        len(english_lexicon_terms),
    )
    return english_lexicon_terms
