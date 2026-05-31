from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree as ET

from speekify.extract import ExtractedContent, is_single_url_input
from speekify.tts import SynthesisArtifact
from speekify.validation import normalize_feed_base_url

METADATA_SCHEMA = "https://otterly.space/speekify/metadata/v1"
RSS_FEED_FILENAME = "speekify-feed.xml"
AUDIO_MIME_TYPE = "audio/wav"
RSS_VERSION = "2.0"
ITUNES_NAMESPACE = "http://www.itunes.com/dtds/podcast-1.0.dtd"

ET.register_namespace("itunes", ITUNES_NAMESPACE)


@dataclass(frozen=True)
class GenerationMetadata:
    metadata_path: Path
    feed_path: Path


@dataclass(frozen=True)
class GenerationMetadataRequest:
    output_path: Path
    title: str
    content: ExtractedContent
    source_text: str
    voice: str
    voice_style_path: Path | None
    language_code: str
    speed: float
    steps: int
    max_chunk_length: int | None
    silence_duration: float
    artifact: SynthesisArtifact
    feed_base_url: str = ""
    created_at: datetime | None = None


def write_generation_metadata(request: GenerationMetadataRequest) -> GenerationMetadata:
    timestamp = _utc_timestamp(request.created_at)
    normalized_feed_base_url = normalize_feed_base_url(request.feed_base_url)
    metadata_path = request.output_path.with_suffix(".json")
    feed_path = request.output_path.parent / RSS_FEED_FILENAME
    payload = _build_metadata_payload(
        output_path=request.output_path,
        title=request.title,
        content=request.content,
        source_text=request.source_text,
        voice=request.voice,
        voice_style_path=request.voice_style_path,
        language_code=request.language_code,
        speed=request.speed,
        steps=request.steps,
        max_chunk_length=request.max_chunk_length,
        silence_duration=request.silence_duration,
        artifact=request.artifact,
        feed_base_url=normalized_feed_base_url,
        created_at=timestamp,
    )
    metadata_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    rebuild_podcast_feed(
        request.output_path.parent,
        feed_base_url=normalized_feed_base_url,
        created_at=timestamp,
    )
    return GenerationMetadata(metadata_path=metadata_path, feed_path=feed_path)


def rebuild_podcast_feed(
    output_dir: Path,
    *,
    feed_base_url: str = "",
    created_at: datetime | None = None,
) -> Path:
    normalized_feed_base_url = normalize_feed_base_url(feed_base_url)
    output_dir.mkdir(parents=True, exist_ok=True)
    feed_path = output_dir / RSS_FEED_FILENAME
    entries = _load_metadata_entries(output_dir)
    root = ET.Element("rss", {"version": RSS_VERSION})
    channel = ET.SubElement(root, "channel")
    ET.SubElement(channel, "title").text = "Speekify Personal Podcast"
    ET.SubElement(
        channel, "description"
    ).text = "Local Speekify narrations generated on this device."
    ET.SubElement(channel, "link").text = normalized_feed_base_url or output_dir.resolve().as_uri()
    ET.SubElement(channel, "language").text = _feed_language(entries)
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(
        _utc_timestamp(created_at), usegmt=True
    )
    ET.SubElement(channel, f"{{{ITUNES_NAMESPACE}}}author").text = "Speekify"
    ET.SubElement(channel, f"{{{ITUNES_NAMESPACE}}}explicit").text = "false"

    for entry in entries:
        _append_feed_item(
            channel,
            entry,
            output_dir=output_dir,
            feed_base_url=normalized_feed_base_url,
        )

    _indent(root)
    ET.ElementTree(root).write(feed_path, encoding="utf-8", xml_declaration=True)
    return feed_path


def _build_metadata_payload(
    *,
    output_path: Path,
    title: str,
    content: ExtractedContent,
    source_text: str,
    voice: str,
    voice_style_path: Path | None,
    language_code: str,
    speed: float,
    steps: int,
    max_chunk_length: int | None,
    silence_duration: float,
    artifact: SynthesisArtifact,
    feed_base_url: str,
    created_at: datetime,
) -> dict[str, object]:
    audio_size = output_path.stat().st_size if output_path.exists() else 0
    source_url = source_text.strip() if is_single_url_input(source_text) else ""
    display_title = title.strip() or content.best_title()
    enclosure_url = _media_url(
        output_path.name, feed_base_url, fallback_uri=output_path.resolve().as_uri()
    )
    return {
        "$schema": METADATA_SCHEMA,
        "title": display_title,
        "created_at": created_at.isoformat().replace("+00:00", "Z"),
        "audio": {
            "file": output_path.name,
            "path": str(output_path),
            "uri": output_path.resolve().as_uri(),
            "mime_type": AUDIO_MIME_TYPE,
            "size_bytes": audio_size,
            "duration_seconds": artifact.duration_seconds,
        },
        "source": {
            "mode": "url" if source_url else "text",
            "url": source_url,
            "extracted_title": content.title,
            "text_characters": len(content.text),
        },
        "synthesis": {
            "language_code": language_code,
            "voice": voice,
            "voice_style_path": str(voice_style_path) if voice_style_path is not None else "",
            "speed": speed,
            "steps": steps,
            "silence_duration": silence_duration,
            "max_chunk_length": max_chunk_length,
            "batch_count": artifact.batch_count,
        },
        "podcast": {
            "guid": output_path.resolve().as_uri(),
            "enclosure_url": enclosure_url,
            "local_enclosure_uri": output_path.resolve().as_uri(),
            "enclosure_type": AUDIO_MIME_TYPE,
            "feed_file": RSS_FEED_FILENAME,
            "feed_url": _media_url(RSS_FEED_FILENAME, feed_base_url, fallback_uri=""),
        },
    }


def _media_url(file_name: str, feed_base_url: str, *, fallback_uri: str) -> str:
    if not feed_base_url:
        return fallback_uri
    return f"{feed_base_url}/{quote(file_name)}"


def _load_metadata_entries(output_dir: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for metadata_path in sorted(output_dir.glob("*.json")):
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("$schema") != METADATA_SCHEMA:
            continue
        audio = payload.get("audio")
        if not isinstance(audio, dict):
            continue
        audio_file = audio.get("file")
        if not isinstance(audio_file, str) or not (output_dir / audio_file).exists():
            continue
        entries.append(payload)
    return sorted(entries, key=_entry_sort_key, reverse=True)


def _entry_sort_key(entry: dict[str, object]) -> str:
    created_at = entry.get("created_at")
    return created_at if isinstance(created_at, str) else ""


def _append_feed_item(
    channel: ET.Element,
    entry: dict[str, object],
    *,
    output_dir: Path,
    feed_base_url: str,
) -> None:
    audio = entry.get("audio") if isinstance(entry.get("audio"), dict) else {}
    source = entry.get("source") if isinstance(entry.get("source"), dict) else {}
    podcast = entry.get("podcast") if isinstance(entry.get("podcast"), dict) else {}
    synthesis = entry.get("synthesis") if isinstance(entry.get("synthesis"), dict) else {}

    assert isinstance(audio, dict)
    assert isinstance(source, dict)
    assert isinstance(podcast, dict)
    assert isinstance(synthesis, dict)

    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = _string_value(entry.get("title"), "Untitled")
    ET.SubElement(item, "description").text = _description(source, synthesis)
    ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = _string_value(
        podcast.get("guid"), _string_value(audio.get("uri"), "")
    )
    created_at = _parse_timestamp(_string_value(entry.get("created_at"), ""))
    ET.SubElement(item, "pubDate").text = format_datetime(created_at, usegmt=True)
    audio_file = _string_value(audio.get("file"), "")
    local_uri = _string_value(audio.get("uri"), "")
    fallback_enclosure_url = _string_value(podcast.get("enclosure_url"), local_uri)
    if audio_file:
        fallback_enclosure_url = _media_url(
            audio_file,
            feed_base_url,
            fallback_uri=(output_dir / audio_file).resolve().as_uri(),
        )
    ET.SubElement(
        item,
        "enclosure",
        {
            "url": fallback_enclosure_url,
            "length": str(int(_number_value(audio.get("size_bytes"), 0))),
            "type": _string_value(podcast.get("enclosure_type"), AUDIO_MIME_TYPE),
        },
    )
    duration = _number_value(audio.get("duration_seconds"), 0)
    ET.SubElement(item, f"{{{ITUNES_NAMESPACE}}}duration").text = _format_duration(duration)


def _description(source: dict[object, object], synthesis: dict[object, object]) -> str:
    parts = [
        f"Language: {_string_value(synthesis.get('language_code'), 'unknown')}",
        f"Voice: {_string_value(synthesis.get('voice'), 'unknown')}",
    ]
    source_url = _string_value(source.get("url"), "")
    if source_url:
        parts.append(f"Source: {source_url}")
    return " | ".join(parts)


def _feed_language(entries: list[dict[str, object]]) -> str:
    for entry in entries:
        synthesis = entry.get("synthesis")
        if isinstance(synthesis, dict):
            language = synthesis.get("language_code")
            if isinstance(language, str) and language:
                return language
    return "fr"


def _format_duration(seconds: float) -> str:
    rounded = max(0, int(round(seconds)))
    hours, remainder = divmod(rounded, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _parse_timestamp(value: str) -> datetime:
    if not value:
        return _utc_timestamp(None)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return _utc_timestamp(None)


def _utc_timestamp(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _string_value(value: object, default: str) -> str:
    return value if isinstance(value, str) and value else default


def _number_value(value: object, default: float) -> float:
    if isinstance(value, int | float):
        return float(value)
    return default


def _indent(element: ET.Element, level: int = 0) -> None:
    indent_text = "\n" + level * "  "
    if len(element):
        if not element.text or not element.text.strip():
            element.text = indent_text + "  "
        for child in element:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent_text
    if level and (not element.tail or not element.tail.strip()):
        element.tail = indent_text
