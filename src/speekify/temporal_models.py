from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field


SCHEMA_VERSION = 1


@dataclass(frozen=True)
class SourceSpecV1:
    source_id: str
    kind: str
    value: str
    display_name: str
    payload_path: str = ""
    payload_sha256: str = ""
    content_sha256: str = ""
    size_bytes: int = 0
    mtime_ns: int = 0
    origin_directory: str = ""
    relative_path: str = ""


@dataclass(frozen=True)
class GenerationOptionsV1:
    voice: str
    language_code: str
    speed: float
    steps: int
    output_dir: str
    voice_style_path: str = ""
    max_chunk_length: int | None = None
    silence_duration: float = 0.25
    english_islands: bool = True
    english_lexicon_path: str = ""
    title: str = ""


@dataclass(frozen=True)
class GenerationWorkflowInputV1:
    job_id: str
    workflow_id: str
    request_fingerprint: str
    source: SourceSpecV1
    options: GenerationOptionsV1
    submitted_at: str
    data_dir: str
    schema_version: int = SCHEMA_VERSION
    batch_id: str = ""
    item_index: int = -1
    verbose: bool = False


@dataclass(frozen=True)
class PreparedSourceRefV1:
    job_id: str
    request_fingerprint: str
    artifact_path: str
    artifact_sha256: str
    artifact_size: int
    title: str
    language_code: str
    source_mode: str
    output_path: str
    text_length: int
    warnings: list[str] = field(default_factory=list)
    reused: bool = False


@dataclass(frozen=True)
class SynthesisActivityInputV1:
    request: GenerationWorkflowInputV1
    prepared: PreparedSourceRefV1


@dataclass(frozen=True)
class DiagnosticReportRefV1:
    path: str
    sha256: str
    size_bytes: int
    reason: str


@dataclass(frozen=True)
class GenerationWorkflowResultV1:
    job_id: str
    workflow_id: str
    request_fingerprint: str
    output_path: str
    output_sha256: str
    output_size: int
    title: str
    language_code: str
    text_length: int
    duration_seconds: float
    batch_count: int
    warnings: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""
    receipt_path: str = ""
    diagnostic_report_path: str = ""
    reused_preparation: bool = False
    reused_audio: bool = False


@dataclass(frozen=True)
class GenerationStatusV1:
    state: str
    message: str
    completed_steps: int
    total_steps: int = 2
    diagnostic_report_path: str = ""


@dataclass(frozen=True)
class BatchWorkflowInputV1:
    batch_id: str
    workflow_id: str
    manifest_sha256: str
    items: list[GenerationWorkflowInputV1]
    data_dir: str
    submitted_at: str
    schema_version: int = SCHEMA_VERSION
    verbose: bool = False
    max_parallel_items: int = 4


@dataclass(frozen=True)
class BatchItemResultV1:
    index: int
    source_id: str
    display_name: str
    status: str
    generation: GenerationWorkflowResultV1 | None = None
    error_code: str = ""
    error_message: str = ""
    diagnostic_report_path: str = ""


@dataclass(frozen=True)
class BatchWorkflowResultV1:
    batch_id: str
    workflow_id: str
    items: list[BatchItemResultV1]
    completed_count: int
    failed_count: int
    cancelled_count: int
    diagnostic_report_path: str = ""


@dataclass(frozen=True)
class BatchStatusV1:
    state: str
    total: int
    preparing_or_running: int
    completed: int
    failed: int
    current_item: str = ""


@dataclass(frozen=True)
class FailureEnvelopeV1:
    code: str
    category: str
    stage: str
    retryable: bool
    message: str
    journal_path: str = ""


@dataclass(frozen=True)
class DiagnosticReportInputV1:
    scope: str
    identifier: str
    data_dir: str
    reason: str
    outcome: str
    source_display_name: str = ""
    output_path: str = ""
    warnings: list[str] = field(default_factory=list)
    failures: list[FailureEnvelopeV1] = field(default_factory=list)
    journal_paths: list[str] = field(default_factory=list)


def canonical_json(value: object) -> str:
    payload = asdict(value) if hasattr(value, "__dataclass_fields__") else value
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
