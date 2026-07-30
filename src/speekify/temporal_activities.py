from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from temporalio import activity
from temporalio.exceptions import ApplicationError

from speekify.application import build_generation_request
from speekify.dependencies import build_dependencies
from speekify.job_store import (
    append_diagnostic_event,
    atomic_write_json,
    deterministic_output_path,
    ensure_data_layout,
    finalize_diagnostic_report,
    job_dir,
    read_json,
    redact_text,
    sha256_file,
)
from speekify.logging_utils import configure_logger
from speekify.temporal_models import (
    DiagnosticReportInputV1,
    DiagnosticReportRefV1,
    FailureEnvelopeV1,
    GenerationWorkflowInputV1,
    GenerationWorkflowResultV1,
    PreparedSourceRefV1,
    SynthesisActivityInputV1,
    fingerprint,
)
from speekify.workflow import generate_audio, resolve_content


def _activity_context() -> tuple[str, int]:
    try:
        info = activity.info()
    except RuntimeError:
        return ("activity", 1)
    return (info.activity_id, info.attempt)


def _heartbeat(stage: str) -> None:
    try:
        activity.heartbeat({"stage": stage})
    except RuntimeError:
        pass


def _logger(data_dir: Path) -> logging.Logger:
    return configure_logger(data_dir / "runtime" / "worker.log")[0]


def _failure(
    exc: Exception,
    *,
    data_dir: Path,
    job_id: str,
    stage: str,
    retryable: bool,
) -> ApplicationError:
    activity_id, attempt = _activity_context()
    message = redact_text(str(exc).strip() or exc.__class__.__name__)
    journal = append_diagnostic_event(
        data_dir,
        job_id,
        activity_id=activity_id,
        attempt=attempt,
        event={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": "error",
            "code": exc.__class__.__name__,
            "stage": stage,
            "message": message,
            "retryable": retryable,
        },
    )
    envelope = FailureEnvelopeV1(
        code=exc.__class__.__name__,
        category="transient" if retryable else "validation",
        stage=stage,
        retryable=retryable,
        message=message,
        journal_path=str(journal),
    )
    return ApplicationError(
        message,
        envelope,
        type=envelope.code,
        non_retryable=not retryable,
    )


@activity.defn(name="speekify.prepare_source.v1")
async def prepare_source_v1(payload: GenerationWorkflowInputV1) -> PreparedSourceRefV1:
    data_dir = ensure_data_layout(Path(payload.data_dir))
    directory = job_dir(data_dir, payload.job_id)
    artifact_path = directory / "prepared.json"
    if artifact_path.is_file():
        existing = read_json(artifact_path)
        if existing.get("request_fingerprint") != payload.request_fingerprint:
            raise ApplicationError(
                "The job identifier conflicts with another request.",
                type="JobConflict",
                non_retryable=True,
            )
        return PreparedSourceRefV1(
            job_id=payload.job_id,
            request_fingerprint=payload.request_fingerprint,
            artifact_path=str(artifact_path),
            artifact_sha256=sha256_file(artifact_path),
            artifact_size=artifact_path.stat().st_size,
            title=str(existing["title"]),
            language_code=str(existing["language_code"]),
            source_mode=str(existing["source_mode"]),
            output_path=str(existing["output_path"]),
            text_length=len(str(existing["text"])),
            warnings=list(existing.get("warnings", [])),
            reused=True,
        )

    logger = _logger(data_dir)
    try:
        _heartbeat("validating")
        source_value = _resolve_source_value(payload.source)
        if payload.source.kind == "file":
            source_path = Path(source_value)
            stat = source_path.stat()
            if stat.st_size != payload.source.size_bytes or sha256_file(source_path) != (
                payload.source.content_sha256
            ):
                raise ValueError(f"Source file changed after submission: {source_path}")

        request = build_generation_request(
            source_text=source_value,
            is_url_mode=payload.source.kind == "url",
            title=payload.options.title,
            voice=payload.options.voice,
            custom_style_path=payload.options.voice_style_path or None,
            language_code=payload.options.language_code,
            speed=payload.options.speed,
            steps=payload.options.steps,
            max_chunk_length=payload.options.max_chunk_length,
            silence_duration=payload.options.silence_duration,
            english_islands=payload.options.english_islands,
            english_lexicon_path=payload.options.english_lexicon_path or None,
            output_dir=payload.options.output_dir,
            use_user_config=False,
        )
        dependencies = build_dependencies(cached=True)

        def status(message: str) -> None:
            _heartbeat(message)

        resolved = await resolve_content(
            request.source_text,
            is_url_mode=request.is_url_mode,
            requested_language=request.language_code,
            translator=dependencies.translator,
            logger=logger,
            status_callback=status,
        )
        title = request.title or resolved.content.best_title()
        output_path = deterministic_output_path(
            Path(payload.options.output_dir),
            title,
            payload.submitted_at,
            payload.job_id,
        )
        artifact = {
            "schema_version": payload.schema_version,
            "job_id": payload.job_id,
            "request_fingerprint": payload.request_fingerprint,
            "text": resolved.content.text,
            "title": title,
            "language_code": resolved.language_code,
            "source_mode": payload.source.kind,
            "output_path": str(output_path),
            "warnings": [],
        }
        _heartbeat("persisting")
        atomic_write_json(directory / "request.json", payload)
        atomic_write_json(artifact_path, artifact)
        activity_id, attempt = _activity_context()
        append_diagnostic_event(
            data_dir,
            payload.job_id,
            activity_id=activity_id,
            attempt=attempt,
            event={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "severity": "info",
                "code": "source_prepared",
                "stage": "preparing",
                "text_length": len(resolved.content.text),
                "source_kind": payload.source.kind,
            },
        )
        return PreparedSourceRefV1(
            job_id=payload.job_id,
            request_fingerprint=payload.request_fingerprint,
            artifact_path=str(artifact_path),
            artifact_sha256=sha256_file(artifact_path),
            artifact_size=artifact_path.stat().st_size,
            title=title,
            language_code=resolved.language_code,
            source_mode=payload.source.kind,
            output_path=str(output_path),
            text_length=len(resolved.content.text),
        )
    except ApplicationError:
        raise
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise _failure(
            exc,
            data_dir=data_dir,
            job_id=payload.job_id,
            stage="preparing",
            retryable=False,
        ) from exc
    except Exception as exc:
        raise _failure(
            exc,
            data_dir=data_dir,
            job_id=payload.job_id,
            stage="preparing",
            retryable=True,
        ) from exc


@activity.defn(name="speekify.synthesize_and_persist.v1")
async def synthesize_and_persist_v1(
    payload: SynthesisActivityInputV1,
) -> GenerationWorkflowResultV1:
    request_payload, prepared_ref = payload.request, payload.prepared
    data_dir = ensure_data_layout(Path(request_payload.data_dir))
    directory = job_dir(data_dir, request_payload.job_id)
    result_path = directory / "result.json"
    if result_path.is_file():
        existing = read_json(result_path)
        result = GenerationWorkflowResultV1(**existing)
        return replace(result, reused_audio=True)

    final_path = Path(prepared_ref.output_path)
    pending_audio = directory / "audio.pending.wav"
    pending_result = directory / "result.pending.json"
    if final_path.is_file() and pending_result.is_file():
        existing = read_json(pending_result)
        if existing.get("output_sha256") == sha256_file(final_path):
            os.replace(pending_result, result_path)
            return replace(GenerationWorkflowResultV1(**existing), reused_audio=True)
    if pending_audio.is_file() and pending_result.is_file() and not final_path.exists():
        existing = read_json(pending_result)
        if existing.get("output_sha256") == sha256_file(pending_audio):
            final_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(pending_audio, final_path)
            os.replace(pending_result, result_path)
            return replace(GenerationWorkflowResultV1(**existing), reused_audio=True)

    logger = _logger(data_dir)
    heartbeat_task: asyncio.Task[None] | None = None
    try:
        if sha256_file(Path(prepared_ref.artifact_path)) != prepared_ref.artifact_sha256:
            raise ValueError("Prepared source integrity check failed.")
        prepared = read_json(Path(prepared_ref.artifact_path))
        request = build_generation_request(
            source_text=str(prepared["text"]),
            is_url_mode=False,
            title=str(prepared["title"]),
            voice=request_payload.options.voice,
            custom_style_path=request_payload.options.voice_style_path or None,
            language_code=str(prepared["language_code"]),
            speed=request_payload.options.speed,
            steps=request_payload.options.steps,
            max_chunk_length=request_payload.options.max_chunk_length,
            silence_duration=request_payload.options.silence_duration,
            english_islands=request_payload.options.english_islands,
            english_lexicon_path=request_payload.options.english_lexicon_path or None,
            output_dir=request_payload.options.output_dir,
            output_path=pending_audio,
            use_user_config=False,
        )
        dependencies = build_dependencies(cached=True)

        async def keep_heartbeat() -> None:
            while True:
                _heartbeat("synthesizing")
                await asyncio.sleep(20)

        heartbeat_task = asyncio.create_task(keep_heartbeat())
        generation = await generate_audio(
            request,
            synthesizer=dependencies.synthesizer,
            translator=dependencies.translator,
            logger=logger,
            status_callback=_heartbeat,
        )
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            heartbeat_task = None
        if not pending_audio.is_file():
            raise RuntimeError("The audio engine did not create the expected WAV file.")
        output_hash = sha256_file(pending_audio)
        warnings = generation.artifact.summary_notes()
        completed_at = datetime.now(timezone.utc).isoformat()
        result = GenerationWorkflowResultV1(
            job_id=request_payload.job_id,
            workflow_id=request_payload.workflow_id,
            request_fingerprint=request_payload.request_fingerprint,
            output_path=str(final_path),
            output_sha256=output_hash,
            output_size=pending_audio.stat().st_size,
            title=prepared_ref.title,
            language_code=prepared_ref.language_code,
            text_length=prepared_ref.text_length,
            duration_seconds=generation.artifact.duration_seconds,
            batch_count=generation.artifact.batch_count,
            warnings=warnings,
            started_at=request_payload.submitted_at,
            completed_at=completed_at,
            receipt_path=str(result_path),
            reused_preparation=prepared_ref.reused,
        )
        atomic_write_json(pending_result, result)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        if final_path.exists():
            raise ValueError(f"Refusing to overwrite an unrelated output file: {final_path}")
        os.replace(pending_audio, final_path)
        os.replace(pending_result, result_path)
        activity_id, attempt = _activity_context()
        append_diagnostic_event(
            data_dir,
            request_payload.job_id,
            activity_id=activity_id,
            attempt=attempt,
            event={
                "timestamp": completed_at,
                "severity": "info",
                "code": "audio_persisted",
                "stage": "persisting",
                "duration_seconds": result.duration_seconds,
                "batch_count": result.batch_count,
                "output_size": result.output_size,
            },
        )
        return result
    except ApplicationError:
        raise
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise _failure(
            exc,
            data_dir=data_dir,
            job_id=request_payload.job_id,
            stage="synthesizing",
            retryable=False,
        ) from exc
    except Exception as exc:
        raise _failure(
            exc,
            data_dir=data_dir,
            job_id=request_payload.job_id,
            stage="synthesizing",
            retryable=True,
        ) from exc
    finally:
        if heartbeat_task is not None:
            heartbeat_task.cancel()


@activity.defn(name="speekify.finalize_diagnostic_report.v1")
async def finalize_diagnostic_report_v1(
    payload: DiagnosticReportInputV1,
) -> DiagnosticReportRefV1:
    return await asyncio.to_thread(finalize_diagnostic_report, payload)


def _resolve_source_value(source) -> str:
    if not source.payload_path:
        raise ValueError("Local source payload reference is missing.")
    payload = read_json(Path(source.payload_path))
    if payload.get("kind") != source.kind:
        raise ValueError("Sensitive source payload type does not match the workflow request.")
    value = str(payload.get("value", ""))
    if fingerprint({"kind": source.kind, "value": value}) != source.payload_sha256:
        raise ValueError("Local source payload integrity check failed.")
    return value
