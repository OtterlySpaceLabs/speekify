from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path


def slugify_title(title: str, max_length: int = 72) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    trimmed = slug[:max_length].rstrip("-")
    return trimmed or "speech"


def build_output_path(
    output_dir: Path,
    title: str,
    created_at: datetime | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = (created_at or datetime.now()).strftime("%Y%m%d-%H%M%S")
    stem = f"{slugify_title(title)}-{timestamp}"
    candidate = output_dir / f"{stem}.wav"
    suffix = 2
    while candidate.exists():
        candidate = output_dir / f"{stem}-{suffix}.wav"
        suffix += 1
    return candidate
