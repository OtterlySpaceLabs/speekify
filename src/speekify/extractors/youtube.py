from __future__ import annotations

import asyncio
import html
import json
import re
from urllib.parse import urlparse

import httpx
import yt_dlp

from speekify.extract_common import DEFAULT_FETCH_HEADERS, ExtractedContent, logger, normalize_text

YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
YOUTUBE_TRANSCRIPT_LANG_PREFIXES = ("en",)
YOUTUBE_SUBTITLE_FORMAT_PRIORITY = ("json3", "vtt", "srv3", "ttml", "srt")


def looks_like_youtube_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    return host in YOUTUBE_HOSTS or host.endswith(".youtube.com")


async def extract_youtube_transcript(url: str, min_chars: int) -> ExtractedContent:
    logger.info("YouTube transcript extraction triggered url=%s", url)
    info = await asyncio.to_thread(_extract_youtube_info, url)
    transcript_source = _select_youtube_transcript_source(info)
    if transcript_source is None:
        raise ValueError("Aucun transcript anglais disponible pour cette vidéo YouTube.")

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        response = await client.get(transcript_source["url"], headers=DEFAULT_FETCH_HEADERS)
        response.raise_for_status()

    text = extract_text_from_youtube_subtitles(response.text, transcript_source.get("ext", ""))
    if len(text) < min_chars:
        raise ValueError("Le transcript anglais extrait de cette vidéo YouTube est trop court.")

    title = info.get("title", "")
    if not isinstance(title, str):
        title = ""
    return ExtractedContent(text=text, title=title)


def _extract_youtube_info(url: str) -> dict[str, object]:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict):
        raise ValueError("Impossible de lire les métadonnées de cette vidéo YouTube.")
    return info


def _select_youtube_transcript_source(info: dict[str, object]) -> dict[str, str] | None:
    for source_group_name in ("subtitles", "automatic_captions"):
        source_group = info.get(source_group_name, {})
        if not isinstance(source_group, dict):
            continue
        candidates = _select_youtube_language_tracks(source_group)
        selected = _select_preferred_youtube_track(candidates)
        if selected is not None:
            return selected
    return None


def _select_youtube_language_tracks(source_group: dict[object, object]) -> list[dict[str, str]]:
    for lang, tracks in source_group.items():
        if not isinstance(lang, str) or not lang.lower().startswith(
            YOUTUBE_TRANSCRIPT_LANG_PREFIXES
        ):
            continue
        if not isinstance(tracks, list):
            continue
        normalized_tracks: list[dict[str, str]] = []
        for track in tracks:
            if not isinstance(track, dict):
                continue
            url = track.get("url", "")
            if not isinstance(url, str) or not url:
                continue
            ext = track.get("ext", "")
            normalized_tracks.append({"url": url, "ext": ext if isinstance(ext, str) else ""})
        if normalized_tracks:
            return normalized_tracks
    return []


def _select_preferred_youtube_track(tracks: list[dict[str, str]]) -> dict[str, str] | None:
    if not tracks:
        return None
    for preferred_ext in YOUTUBE_SUBTITLE_FORMAT_PRIORITY:
        for track in tracks:
            if track.get("ext") == preferred_ext:
                return track
    return tracks[0]


def extract_text_from_youtube_subtitles(subtitle_text: str, subtitle_ext: str) -> str:
    if subtitle_ext == "json3" or subtitle_text.lstrip().startswith("{"):
        return extract_text_from_youtube_json3(subtitle_text)
    return extract_text_from_timed_subtitle_text(subtitle_text)


def extract_text_from_youtube_json3(subtitle_text: str) -> str:
    try:
        payload = json.loads(subtitle_text)
    except json.JSONDecodeError:
        return ""

    events = payload.get("events", [])
    if not isinstance(events, list):
        return ""

    text_parts: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        segments = event.get("segs", [])
        if not isinstance(segments, list):
            continue
        segment_text = "".join(
            segment.get("utf8", "")
            for segment in segments
            if isinstance(segment, dict) and isinstance(segment.get("utf8", ""), str)
        )
        stripped_segment_text = segment_text.strip()
        if stripped_segment_text:
            text_parts.append(stripped_segment_text)
    return normalize_text(" ".join(text_parts))


def extract_text_from_timed_subtitle_text(subtitle_text: str) -> str:
    text_parts: list[str] = []
    previous_text = ""
    for raw_line in subtitle_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.upper() == "WEBVTT" or line.startswith(("Kind:", "Language:")):
            continue
        if "-->" in line or re.fullmatch(r"\d+", line):
            continue
        cleaned_line = re.sub(r"<[^>]+>", "", line)
        cleaned_line = html.unescape(cleaned_line).strip()
        if cleaned_line and cleaned_line != previous_text:
            text_parts.append(cleaned_line)
            previous_text = cleaned_line
    return normalize_text(" ".join(text_parts))