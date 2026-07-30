from __future__ import annotations

import asyncio
import uuid
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from temporalio.client import Client

from speekify.batch import ExpandedBatch, source_spec
from speekify.extract import ExtractedContent
from speekify.job_store import (
    atomic_write_json,
    atomic_write_text,
    batch_dir,
    default_data_dir,
    ensure_data_layout,
    job_dir,
    redact_url,
    read_json,
)
from speekify.temporal_models import (
    BatchStatusV1,
    BatchWorkflowInputV1,
    BatchWorkflowResultV1,
    GenerationOptionsV1,
    GenerationStatusV1,
    GenerationWorkflowInputV1,
    GenerationWorkflowResultV1,
    SourceSpecV1,
    fingerprint,
)
from speekify.temporal_runtime import RuntimeLease, ensure_local_runtime
from speekify.temporal_workflows import (
    WORKFLOW_TASK_QUEUE,
    SpeekifyBatchWorkflowV1,
    SpeekifyGenerationWorkflowV1,
)
from speekify.tts import PreparedText, SynthesisArtifact
from speekify.workflow import GenerationRequest, GenerationResult

StatusCallback = Callable[[str], None]


class ReliableGenerationError(RuntimeError):
    def __init__(self, message: str, *, diagnostic_report_path: Path | None = None) -> None:
        super().__init__(message)
        self.diagnostic_report_path = diagnostic_report_path


async def run_temporal_generation(
    request: GenerationRequest,
    *,
    status_callback: StatusCallback | None = None,
    verbose: bool = False,
    client: Client | None = None,
    data_dir: Path | None = None,
) -> GenerationResult:
    root = ensure_data_layout(data_dir or default_data_dir())
    async with RuntimeLease(root):
        return await _run_temporal_generation(
            request,
            status_callback=status_callback,
            verbose=verbose,
            client=client,
            data_dir=root,
        )


async def _run_temporal_generation(
    request: GenerationRequest,
    *,
    status_callback: StatusCallback | None,
    verbose: bool,
    client: Client | None,
    data_dir: Path,
) -> GenerationResult:
    root = ensure_data_layout(data_dir)
    if status_callback:
        status_callback("starting local engine")
    temporal_client = client or await ensure_local_runtime(root)
    payload = build_workflow_input(request, data_dir=root, verbose=verbose)
    existing = _find_unacknowledged_request(root, payload.request_fingerprint)
    if existing is not None:
        _discard_provisional_source(root, payload)
        payload = existing
    directory = job_dir(root, payload.job_id)
    result_path = directory / "result.json"
    if existing is not None and result_path.is_file():
        result = GenerationWorkflowResultV1(**read_json(result_path))
        atomic_write_text(directory / "client.acknowledged", result.completed_at or "completed")
        return generation_result_to_core(result)
    if existing is not None:
        handle = temporal_client.get_workflow_handle(
            payload.workflow_id,
            result_type=GenerationWorkflowResultV1,
        )
    else:
        atomic_write_json(directory / "request.json", payload)
        handle = await temporal_client.start_workflow(
            SpeekifyGenerationWorkflowV1.run,
            payload,
            id=payload.workflow_id,
            task_queue=WORKFLOW_TASK_QUEUE,
        )
    result_task = asyncio.create_task(handle.result())
    try:
        await _poll_generation_progress(handle, result_task, status_callback)
        result: GenerationWorkflowResultV1 = await result_task
    except asyncio.CancelledError:
        await handle.cancel()
        raise
    except Exception as exc:
        report_path = root / "reports" / f"generation-{payload.job_id}.log"
        atomic_write_text(directory / "client.acknowledged", "failed")
        raise ReliableGenerationError(
            str(exc).strip() or "Audio generation failed.",
            diagnostic_report_path=report_path if report_path.is_file() else None,
        ) from exc
    atomic_write_text(directory / "client.acknowledged", result.completed_at or "completed")
    return generation_result_to_core(result)


async def run_temporal_batch(
    expanded: ExpandedBatch,
    *,
    options: GenerationOptionsV1,
    status_callback: StatusCallback | None = None,
    verbose: bool = False,
    client: Client | None = None,
    data_dir: Path | None = None,
) -> BatchWorkflowResultV1:
    root = ensure_data_layout(data_dir or default_data_dir())
    async with RuntimeLease(root):
        return await _run_temporal_batch(
            expanded,
            options=options,
            status_callback=status_callback,
            verbose=verbose,
            client=client,
            data_dir=root,
        )


async def _run_temporal_batch(
    expanded: ExpandedBatch,
    *,
    options: GenerationOptionsV1,
    status_callback: StatusCallback | None,
    verbose: bool,
    client: Client | None,
    data_dir: Path,
) -> BatchWorkflowResultV1:
    root = ensure_data_layout(data_dir)
    if status_callback:
        status_callback("starting local engine")
    temporal_client = client or await ensure_local_runtime(root)
    batch_id = uuid.uuid4().hex
    submitted_at = datetime.now(timezone.utc).isoformat()
    items = [
        _workflow_input(
            spec=spec,
            options=options,
            submitted_at=submitted_at,
            data_dir=root,
            batch_id=batch_id,
            item_index=index,
            verbose=verbose,
        )
        for index, spec in enumerate(expanded.items)
    ]
    manifest_payload = {
        "schema_version": 1,
        "batch_id": batch_id,
        "submitted_at": submitted_at,
        "items": [asdict(item) for item in items],
        "warnings": expanded.warnings,
    }
    manifest_sha = fingerprint(manifest_payload)
    atomic_write_json(batch_dir(root, batch_id) / "manifest.json", manifest_payload)
    payload = BatchWorkflowInputV1(
        batch_id=batch_id,
        workflow_id=f"speekify-batch-{batch_id}",
        manifest_sha256=manifest_sha,
        items=items,
        data_dir=str(root),
        submitted_at=submitted_at,
        verbose=verbose,
    )
    handle = await temporal_client.start_workflow(
        SpeekifyBatchWorkflowV1.run,
        payload,
        id=payload.workflow_id,
        task_queue=WORKFLOW_TASK_QUEUE,
    )
    result_task = asyncio.create_task(handle.result())
    try:
        await _poll_batch_progress(handle, result_task, status_callback)
        result: BatchWorkflowResultV1 = await result_task
    except asyncio.CancelledError:
        await handle.cancel()
        raise
    atomic_write_json(batch_dir(root, batch_id) / "result.json", result)
    return result


def build_workflow_input(
    request: GenerationRequest,
    *,
    data_dir: Path,
    verbose: bool,
) -> GenerationWorkflowInputV1:
    if request.is_url_mode:
        spec = source_spec(request.source_text)
        if spec.kind != "url":
            raise ValueError("--url requires a valid http:// or https:// URL.")
    else:
        spec = source_spec(request.source_text)
    options = generation_options(request)
    return _workflow_input(
        spec=spec,
        options=options,
        submitted_at=datetime.now(timezone.utc).isoformat(),
        data_dir=data_dir,
        verbose=verbose,
    )


def generation_options(request: GenerationRequest) -> GenerationOptionsV1:
    return GenerationOptionsV1(
        voice=request.voice,
        language_code=request.language_code,
        speed=request.speed,
        steps=request.steps,
        output_dir=str(request.output_dir.resolve()),
        voice_style_path=str(request.voice_style_path or ""),
        max_chunk_length=request.max_chunk_length,
        silence_duration=request.silence_duration,
        english_islands=request.english_islands,
        english_lexicon_path=str(request.english_lexicon_path or ""),
        title=request.title,
    )


def generation_result_to_core(result: GenerationWorkflowResultV1) -> GenerationResult:
    prepared = PreparedText(
        original_text="",
        text="",
        reformatted=False,
        removed_characters=(),
        removed_character_count=0,
    )
    artifact = SynthesisArtifact(
        wav=None,
        duration_seconds=result.duration_seconds,
        batch_count=result.batch_count,
        prepared_text=prepared,
    )
    return GenerationResult(
        output_path=Path(result.output_path),
        artifact=artifact,
        content=ExtractedContent(text="", title=result.title),
        warnings=tuple(result.warnings),
        diagnostic_report_path=(
            Path(result.diagnostic_report_path) if result.diagnostic_report_path else None
        ),
        text_length=result.text_length,
    )


def _workflow_input(
    *,
    spec,
    options: GenerationOptionsV1,
    submitted_at: str,
    data_dir: Path,
    batch_id: str = "",
    item_index: int = -1,
    verbose: bool = False,
) -> GenerationWorkflowInputV1:
    job_id = uuid.uuid4().hex if not batch_id else f"{batch_id}-{item_index:04d}-{spec.source_id[:10]}"
    workflow_id = f"speekify-generation-{job_id}"
    request_fingerprint = fingerprint(
        {
            "schema_version": 1,
            "source": asdict(spec),
            "options": asdict(options),
        }
    )
    spec = _materialize_sensitive_source(spec, data_dir=data_dir, job_id=job_id)
    return GenerationWorkflowInputV1(
        job_id=job_id,
        workflow_id=workflow_id,
        request_fingerprint=request_fingerprint,
        source=spec,
        options=options,
        submitted_at=submitted_at,
        data_dir=str(data_dir),
        batch_id=batch_id,
        item_index=item_index,
        verbose=verbose,
    )


def _materialize_sensitive_source(
    spec: SourceSpecV1,
    *,
    data_dir: Path,
    job_id: str,
) -> SourceSpecV1:
    raw_value = spec.value
    payload_path = job_dir(data_dir, job_id) / "source.json"
    atomic_write_json(
        payload_path,
        {
            "schema_version": 1,
            "kind": spec.kind,
            "value": raw_value,
        },
    )
    if spec.kind == "url":
        safe_value = redact_url(raw_value)
    elif spec.kind == "file":
        safe_value = Path(raw_value).name
    else:
        safe_value = ""
    return replace(
        spec,
        value=safe_value,
        payload_path=str(payload_path),
        payload_sha256=fingerprint({"kind": spec.kind, "value": raw_value}),
    )


async def _poll_generation_progress(handle, result_task, callback: StatusCallback | None) -> None:
    previous = ""
    while not result_task.done():
        if callback:
            try:
                status: GenerationStatusV1 = await handle.query("generation_status")
                if status.message != previous:
                    callback(status.message)
                    previous = status.message
            except Exception:
                pass
        try:
            await asyncio.wait_for(asyncio.shield(result_task), timeout=0.4)
        except TimeoutError:
            pass


async def _poll_batch_progress(handle, result_task, callback: StatusCallback | None) -> None:
    previous = ""
    while not result_task.done():
        if callback:
            try:
                status: BatchStatusV1 = await handle.query("batch_status")
                message = (
                    f"batch {status.completed + status.failed}/{status.total}"
                    + (f": {status.current_item}" if status.current_item else "")
                )
                if message != previous:
                    callback(message)
                    previous = message
            except Exception:
                pass
        try:
            await asyncio.wait_for(asyncio.shield(result_task), timeout=0.4)
        except TimeoutError:
            pass


def _find_unacknowledged_request(
    data_dir: Path,
    request_fingerprint: str,
) -> GenerationWorkflowInputV1 | None:
    candidates: list[tuple[float, GenerationWorkflowInputV1]] = []
    for request_path in (data_dir / "jobs").glob("*/request.json"):
        if (request_path.parent / "client.acknowledged").exists():
            continue
        try:
            raw = read_json(request_path)
            if raw.get("request_fingerprint") != request_fingerprint:
                continue
            source = SourceSpecV1(**raw["source"])
            options = GenerationOptionsV1(**raw["options"])
            raw["source"] = source
            raw["options"] = options
            candidates.append((request_path.stat().st_mtime, GenerationWorkflowInputV1(**raw)))
        except (KeyError, TypeError, ValueError, OSError):
            continue
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def _discard_provisional_source(
    data_dir: Path,
    payload: GenerationWorkflowInputV1,
) -> None:
    directory = data_dir / "jobs" / payload.job_id
    (directory / "source.json").unlink(missing_ok=True)
    try:
        directory.rmdir()
    except OSError:
        pass
