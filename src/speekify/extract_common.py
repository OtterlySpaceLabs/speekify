from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from speekify.logging_utils import LOGGER_NAME

logger = logging.getLogger(LOGGER_NAME)

DEFAULT_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,fr-FR;q=0.8,fr;q=0.7",
}


@dataclass(frozen=True)
class ExtractedContent:
    text: str
    title: str = ""

    def best_title(self) -> str:
        if self.title.strip():
            return self.title.strip()
        first_sentence = re.split(r"[.!?\n]", self.text.strip(), maxsplit=1)[0]
        return first_sentence.strip() or "speech"


def normalize_text(text: str) -> str:
    collapsed_lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.strip().splitlines()]
    normalized_lines: list[str] = []
    previous_blank = False
    for line in collapsed_lines:
        is_blank = not line
        if is_blank and previous_blank:
            continue
        normalized_lines.append(line)
        previous_blank = is_blank
    return "\n".join(normalized_lines).strip()


def validate_url(url: str) -> str:
    candidate = url.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("L'URL doit commencer par http:// ou https://.")
    return candidate


def is_single_url_input(text: str) -> bool:
    candidate = text.strip()
    if not candidate or any(char.isspace() for char in candidate):
        return False

    try:
        validate_url(candidate)
    except ValueError:
        return False

    return True


DOCUMENT_SUFFIXES = {".txt", ".md", ".text", ".pdf"}


def is_document_path_input(text: str) -> bool:
    candidate = text.strip()
    if not candidate or "\n" in candidate:
        return False
    try:
        path = Path(candidate).expanduser()
    except (OSError, ValueError):
        return False
    return path.suffix.lower() in DOCUMENT_SUFFIXES and path.is_file()


def read_document(path: Path) -> ExtractedContent:
    path = path.expanduser()
    if path.suffix.lower() == ".pdf":
        text = _read_pdf_text(path)
    else:
        text = path.read_text(encoding="utf-8", errors="replace")
    normalized = normalize_text(text)
    if not normalized:
        raise ValueError(f"Aucun texte lisible trouvé dans le fichier : {path}")
    return ExtractedContent(text=normalized, title=path.stem)


def _read_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise ValueError(
            "La lecture de PDF nécessite le paquet 'pypdf' (pip install pypdf)."
        ) from exc
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)