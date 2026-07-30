from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from speekify.extract import is_single_url_input
from speekify.extract_common import DOCUMENT_SUFFIXES
from speekify.job_store import redact_url, sha256_file
from speekify.temporal_models import SourceSpecV1

DEFAULT_MAX_BATCH_ITEMS = 1000
DEFAULT_MAX_FILE_SIZE = 50 * 1024 * 1024


@dataclass(frozen=True)
class ExpandedBatch:
    items: list[SourceSpecV1]
    warnings: list[str] = field(default_factory=list)


def source_spec(value: str) -> SourceSpecV1:
    candidate = value.strip()
    path = Path(candidate).expanduser()
    if path.exists():
        if path.is_symlink():
            raise ValueError(f"Symbolic links are not supported: {path}")
        if not path.is_file():
            raise ValueError(f"Expected a readable file: {path}")
        if path.suffix.lower() not in DOCUMENT_SUFFIXES:
            raise ValueError(f"Unsupported document type: {path.suffix or '(none)'}")
        return _file_spec(path.resolve())
    if path.suffix.lower() in DOCUMENT_SUFFIXES:
        raise ValueError(f"Document does not exist: {path}")
    if is_single_url_input(candidate):
        parsed = urlsplit(candidate)
        if parsed.username or parsed.password:
            raise ValueError("URLs containing embedded credentials are not supported.")
        source_id = hashlib.sha256(f"url:{candidate}".encode()).hexdigest()
        return SourceSpecV1(source_id, "url", candidate, redact_url(candidate))
    if not candidate:
        raise ValueError("Batch sources cannot be empty.")
    source_id = hashlib.sha256(f"text:{candidate}".encode()).hexdigest()
    display = f"inline text ({len(candidate)} characters)"
    return SourceSpecV1(source_id, "text", candidate, display)


def expand_batch_sources(
    values: list[str],
    *,
    max_items: int = DEFAULT_MAX_BATCH_ITEMS,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE,
) -> ExpandedBatch:
    items: list[SourceSpecV1] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        path = Path(raw_value).expanduser()
        candidates: list[SourceSpecV1]
        if path.exists() and path.is_dir():
            if path.is_symlink():
                raise ValueError(f"Symbolic links are not supported: {path}")
            root = path.resolve()
            candidates = []
            skipped = 0
            for child in sorted(root.rglob("*"), key=lambda item: str(item.relative_to(root))):
                if ".speekify" in child.parts or child.is_symlink() or not child.is_file():
                    if child.is_symlink():
                        skipped += 1
                    continue
                if child.suffix.lower() not in DOCUMENT_SUFFIXES:
                    skipped += 1
                    continue
                resolved = child.resolve()
                if not resolved.is_relative_to(root):
                    skipped += 1
                    continue
                spec = _file_spec(resolved, root=root)
                candidates.append(spec)
            if not candidates:
                raise ValueError(f"No supported documents found in directory: {path}")
            if skipped:
                warnings.append(f"{skipped} unsupported or symbolic entries skipped in {path}")
        else:
            candidates = [source_spec(raw_value)]
        for spec in candidates:
            if spec.kind == "file" and spec.size_bytes > max_file_size:
                raise ValueError(f"Document exceeds the {max_file_size}-byte limit: {spec.value}")
            if spec.source_id in seen:
                warnings.append(f"Duplicate source skipped: {spec.display_name}")
                continue
            seen.add(spec.source_id)
            items.append(spec)
            if len(items) > max_items:
                raise ValueError(f"Batch cannot contain more than {max_items} items.")
    if not items:
        raise ValueError("At least one batch source is required.")
    return ExpandedBatch(items, warnings)


def _file_spec(path: Path, *, root: Path | None = None) -> SourceSpecV1:
    stat = path.stat()
    digest = sha256_file(path)
    identity = hashlib.sha256(f"file:{path}:{digest}".encode()).hexdigest()
    return SourceSpecV1(
        source_id=identity,
        kind="file",
        value=str(path),
        display_name=path.name,
        content_sha256=digest,
        size_bytes=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        origin_directory=str(root or ""),
        relative_path=str(path.relative_to(root)) if root else "",
    )
