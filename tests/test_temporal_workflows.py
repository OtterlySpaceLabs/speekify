from pathlib import Path
import os

import pytest
from temporalio import activity
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from speekify.temporal_models import (
    DiagnosticReportInputV1,
    DiagnosticReportRefV1,
    BatchWorkflowInputV1,
    GenerationOptionsV1,
    GenerationWorkflowInputV1,
    GenerationWorkflowResultV1,
    PreparedSourceRefV1,
    SourceSpecV1,
    SynthesisActivityInputV1,
)
from speekify.temporal_workflows import (
    AUDIO_TASK_QUEUE,
    PREPARE_TASK_QUEUE,
    WORKFLOW_TASK_QUEUE,
    SpeekifyBatchWorkflowV1,
    SpeekifyGenerationWorkflowV1,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("SPEEKIFY_RUN_TEMPORAL_TESTS") != "1",
    reason="Set SPEEKIFY_RUN_TEMPORAL_TESTS=1 to run the downloaded Temporal test server.",
)


@activity.defn(name="speekify.prepare_source.v1")
async def fake_prepare(payload: GenerationWorkflowInputV1) -> PreparedSourceRefV1:
    return PreparedSourceRefV1(
        job_id=payload.job_id,
        request_fingerprint=payload.request_fingerprint,
        artifact_path="/tmp/prepared.json",
        artifact_sha256="hash",
        artifact_size=10,
        title="Hello",
        language_code="en",
        source_mode="text",
        output_path="/tmp/hello.wav",
        text_length=5,
    )


@activity.defn(name="speekify.synthesize_and_persist.v1")
async def fake_synthesize(payload: SynthesisActivityInputV1) -> GenerationWorkflowResultV1:
    request = payload.request
    if request.source.value == "fail":
        raise ApplicationError("expected failure", non_retryable=True)
    return GenerationWorkflowResultV1(
        job_id=request.job_id,
        workflow_id=request.workflow_id,
        request_fingerprint=request.request_fingerprint,
        output_path="/tmp/hello.wav",
        output_sha256="hash",
        output_size=8,
        title="Hello",
        language_code="en",
        text_length=5,
        duration_seconds=1.0,
        batch_count=1,
    )


@activity.defn(name="speekify.finalize_diagnostic_report.v1")
async def fake_diagnostic(payload: DiagnosticReportInputV1) -> DiagnosticReportRefV1:
    return DiagnosticReportRefV1("/tmp/report.log", "hash", 10, payload.reason)


def _payload(tmp_path: Path, *, verbose: bool = False) -> GenerationWorkflowInputV1:
    return GenerationWorkflowInputV1(
        job_id="job-workflow",
        workflow_id="speekify-generation-job-workflow",
        request_fingerprint="fingerprint",
        source=SourceSpecV1("source", "text", "Hello", "Hello"),
        options=GenerationOptionsV1("M5", "en", 1.0, 10, str(tmp_path)),
        submitted_at="2026-07-30T12:00:00+00:00",
        data_dir=str(tmp_path),
        verbose=verbose,
    )


@pytest.mark.asyncio
async def test_generation_workflow_runs_two_business_activities(tmp_path) -> None:
    async with await WorkflowEnvironment.start_time_skipping() as environment:
        async with (
            Worker(
                environment.client,
                task_queue=WORKFLOW_TASK_QUEUE,
                workflows=[SpeekifyGenerationWorkflowV1],
            ),
            Worker(
                environment.client,
                task_queue=PREPARE_TASK_QUEUE,
                activities=[fake_prepare, fake_diagnostic],
            ),
            Worker(
                environment.client,
                task_queue=AUDIO_TASK_QUEUE,
                activities=[fake_synthesize],
            ),
        ):
            result = await environment.client.execute_workflow(
                SpeekifyGenerationWorkflowV1.run,
                _payload(tmp_path),
                id="workflow-test",
                task_queue=WORKFLOW_TASK_QUEUE,
            )

    assert result.output_path == "/tmp/hello.wav"
    assert not result.diagnostic_report_path


@pytest.mark.asyncio
async def test_generation_workflow_creates_diagnostic_when_verbose(tmp_path) -> None:
    async with await WorkflowEnvironment.start_time_skipping() as environment:
        async with (
            Worker(
                environment.client,
                task_queue=WORKFLOW_TASK_QUEUE,
                workflows=[SpeekifyGenerationWorkflowV1],
            ),
            Worker(
                environment.client,
                task_queue=PREPARE_TASK_QUEUE,
                activities=[fake_prepare, fake_diagnostic],
            ),
            Worker(
                environment.client,
                task_queue=AUDIO_TASK_QUEUE,
                activities=[fake_synthesize],
            ),
        ):
            result = await environment.client.execute_workflow(
                SpeekifyGenerationWorkflowV1.run,
                _payload(tmp_path, verbose=True),
                id="workflow-verbose-test",
                task_queue=WORKFLOW_TASK_QUEUE,
            )

    assert result.diagnostic_report_path == "/tmp/report.log"


@pytest.mark.asyncio
async def test_batch_workflow_keeps_partial_results(tmp_path) -> None:
    ok = _payload(tmp_path)
    failed = GenerationWorkflowInputV1(
        **{
            **ok.__dict__,
            "job_id": "job-failed",
            "workflow_id": "speekify-generation-job-failed",
            "source": SourceSpecV1("failed-source", "text", "fail", "Failure"),
        }
    )
    payload = BatchWorkflowInputV1(
        batch_id="batch-1",
        workflow_id="speekify-batch-batch-1",
        manifest_sha256="manifest",
        items=[ok, failed],
        data_dir=str(tmp_path),
        submitted_at="2026-07-30T12:00:00+00:00",
    )
    async with await WorkflowEnvironment.start_time_skipping() as environment:
        async with (
            Worker(
                environment.client,
                task_queue=WORKFLOW_TASK_QUEUE,
                workflows=[SpeekifyGenerationWorkflowV1, SpeekifyBatchWorkflowV1],
            ),
            Worker(
                environment.client,
                task_queue=PREPARE_TASK_QUEUE,
                activities=[fake_prepare, fake_diagnostic],
            ),
            Worker(
                environment.client,
                task_queue=AUDIO_TASK_QUEUE,
                activities=[fake_synthesize],
            ),
        ):
            result = await environment.client.execute_workflow(
                SpeekifyBatchWorkflowV1.run,
                payload,
                id="batch-workflow-test",
                task_queue=WORKFLOW_TASK_QUEUE,
            )

    assert result.completed_count == 1
    assert result.failed_count == 1
    assert [item.status for item in result.items] == ["completed", "failed"]
    assert result.items[1].diagnostic_report_path.endswith(
        "/reports/generation-job-failed.log"
    )
    assert result.diagnostic_report_path == "/tmp/report.log"
