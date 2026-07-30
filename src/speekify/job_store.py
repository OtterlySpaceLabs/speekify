from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from speekify.naming import slugify_title
from speekify.temporal_models import DiagnosticReportInputV1, DiagnosticReportRefV1

DATA_DIR_ENV_VAR = "SPEEKIFY_DATA_DIR"
MAX_REPORT_BYTES = 256_000
_SECRET_PATTERN = re.compile(
    r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+|"
    r"((?:api[_-]?key|token|password|cookie)\s*[=:]\s*)[^\s,;]+"
)


def default_data_dir() -> Path:
    configured = os.environ.get(DATA_DIR_ENV_VAR, "").strip()
    if configured:
        return Path(configured).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Speekify"
    xdg_data = os.environ.get("XDG_DATA_HOME", "").strip()
    return (Path(xdg_data).expanduser() if xdg_data else Path.home() / ".local" / "share") / (
        "speekify"
    )


def ensure_data_layout(data_dir: Path | None = None) -> Path:
    root = (data_dir or default_data_dir()).expanduser()
    for path in (
        root,
        root / "runtime",
        root / "bin",
        root / "temporal",
        root / "jobs",
        root / "batches",
        root / "reports",
    ):
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def job_dir(data_dir: Path, job_id: str) -> Path:
    path = data_dir / "jobs" / job_id
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def batch_dir(data_dir: Path, batch_id: str) -> Path:
    path = data_dir / "batches" / batch_id
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def atomic_write_json(path: Path, payload: object) -> None:
    serializable = asdict(payload) if hasattr(payload, "__dataclass_fields__") else payload
    atomic_write_text(
        path,
        json.dumps(serializable, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    pending = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with pending.open("w", encoding="utf-8") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(pending, 0o600)
    os.replace(pending, path)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid object in {path}")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def deterministic_output_path(
    output_dir: Path,
    title: str,
    submitted_at: str,
    job_id: str,
) -> Path:
    instant = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
    timestamp = instant.strftime("%Y%m%d-%H%M%S")
    stem = f"{slugify_title(title)}-{timestamp}-{job_id[-10:]}"
    return output_dir.expanduser() / f"{stem}.wav"


def redact_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "[redacted-url]"
    if parsed.scheme not in {"http", "https"}:
        return value
    hostname = parsed.hostname or ""
    netloc = hostname
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))


def redact_text(value: object, *, limit: int = 1000) -> str:
    text = str(value)
    text = re.sub(r"https?://[^\s)>\]]+", lambda match: redact_url(match.group(0)), text)

    def replace_secret(match: re.Match[str]) -> str:
        prefix = match.group(1) or match.group(2) or ""
        return f"{prefix}[REDACTED]"

    text = _SECRET_PATTERN.sub(replace_secret, text)
    return text if len(text) <= limit else f"{text[:limit]}… [truncated]"


def append_diagnostic_event(
    data_dir: Path,
    job_id: str,
    *,
    activity_id: str,
    attempt: int,
    event: dict[str, object],
) -> Path:
    diagnostics_dir = job_dir(data_dir, job_id) / "diagnostics"
    diagnostics_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    safe_activity = re.sub(r"[^a-zA-Z0-9._-]+", "-", activity_id)[:80] or "activity"
    path = diagnostics_dir / f"{safe_activity}-{attempt}.jsonl"
    safe_event = {str(key): redact_text(value) for key, value in event.items()}
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(safe_event, ensure_ascii=False, sort_keys=True) + "\n")
    os.chmod(path, 0o600)
    return path


def finalize_diagnostic_report(payload: DiagnosticReportInputV1) -> DiagnosticReportRefV1:
    data_dir = ensure_data_layout(Path(payload.data_dir))
    lines = [
        "Speekify diagnostic report",
        f"Scope: {payload.scope}",
        f"Identifier: {payload.identifier}",
        f"Outcome: {payload.outcome}",
        f"Reason: {redact_text(payload.reason)}",
    ]
    if payload.source_display_name:
        lines.append(f"Source: {redact_text(payload.source_display_name)}")
    if payload.output_path:
        lines.append(f"Output: {redact_text(payload.output_path)}")
    if payload.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {redact_text(warning)}" for warning in payload.warnings)
    if payload.failures:
        lines.extend(["", "Failures:"])
        for failure in payload.failures:
            lines.append(
                f"- [{failure.code}] stage={failure.stage} retryable={failure.retryable}: "
                f"{redact_text(failure.message)}"
            )
    journal_paths = [Path(path) for path in payload.journal_paths if path]
    if not journal_paths and payload.scope == "generation":
        journal_paths = sorted((data_dir / "jobs" / payload.identifier / "diagnostics").glob("*.jsonl"))
    if journal_paths:
        lines.extend(["", "Activity events:"])
    for journal_path in journal_paths:
        if not journal_path.is_file():
            continue
        lines.append(f"-- {journal_path.name} --")
        lines.extend(redact_text(line, limit=4000) for line in journal_path.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines())
    report_text = "\n".join(lines).strip() + "\n"
    encoded = report_text.encode("utf-8")
    if len(encoded) > MAX_REPORT_BYTES:
        encoded = encoded[: MAX_REPORT_BYTES - 32] + b"\n[report truncated]\n"
        report_text = encoded.decode("utf-8", errors="ignore")
    report_path = data_dir / "reports" / f"{payload.scope}-{payload.identifier}.log"
    atomic_write_text(report_path, report_text)
    return DiagnosticReportRefV1(
        path=str(report_path),
        sha256=sha256_file(report_path),
        size_bytes=report_path.stat().st_size,
        reason=payload.reason,
    )
