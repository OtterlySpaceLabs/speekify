from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from speekify.temporal_activities import (
        finalize_diagnostic_report_v1,
        prepare_source_v1,
        synthesize_and_persist_v1,
    )
    from speekify.temporal_models import (
        BatchItemResultV1,
        BatchStatusV1,
        BatchWorkflowInputV1,
        BatchWorkflowResultV1,
        DiagnosticReportInputV1,
        FailureEnvelopeV1,
        GenerationStatusV1,
        GenerationWorkflowInputV1,
        GenerationWorkflowResultV1,
        SynthesisActivityInputV1,
    )

WORKFLOW_TASK_QUEUE = "speekify-workflows"
PREPARE_TASK_QUEUE = "speekify-prepare"
AUDIO_TASK_QUEUE = "speekify-audio"

PREPARE_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2,
    maximum_interval=timedelta(minutes=2),
    maximum_attempts=4,
)
AUDIO_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    backoff_coefficient=2,
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=3,
)
DIAGNOSTIC_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=10),
    maximum_attempts=3,
)


@workflow.defn(name="speekify.generate.v1")
class SpeekifyGenerationWorkflowV1:
    def __init__(self) -> None:
        self._status = GenerationStatusV1("queued", "starting", 0)

    @workflow.query(name="generation_status")
    def generation_status(self) -> GenerationStatusV1:
        return self._status

    @workflow.run
    async def run(self, payload: GenerationWorkflowInputV1) -> GenerationWorkflowResultV1:
        try:
            self._status = GenerationStatusV1("preparing", "preparing source", 0)
            prepared = await workflow.execute_activity(
                prepare_source_v1,
                payload,
                task_queue=PREPARE_TASK_QUEUE,
                start_to_close_timeout=timedelta(minutes=30),
                schedule_to_close_timeout=timedelta(hours=2),
                heartbeat_timeout=timedelta(minutes=2),
                retry_policy=PREPARE_RETRY_POLICY,
            )
            self._status = GenerationStatusV1("prepared", "loading audio model", 1)
            self._status = GenerationStatusV1("synthesizing", "generating speech", 1)
            result = await workflow.execute_activity(
                synthesize_and_persist_v1,
                SynthesisActivityInputV1(payload, prepared),
                task_queue=AUDIO_TASK_QUEUE,
                start_to_close_timeout=timedelta(hours=6),
                schedule_to_close_timeout=timedelta(hours=12),
                heartbeat_timeout=timedelta(minutes=2),
                retry_policy=AUDIO_RETRY_POLICY,
            )
            report_path = ""
            if payload.verbose or result.warnings or result.reused_audio or result.reused_preparation:
                self._status = GenerationStatusV1("diagnostics", "preparing diagnostics", 2)
                reason = "verbose" if payload.verbose else "significant warning"
                report = await workflow.execute_activity(
                    finalize_diagnostic_report_v1,
                    DiagnosticReportInputV1(
                        scope="generation",
                        identifier=payload.job_id,
                        data_dir=payload.data_dir,
                        reason=reason,
                        outcome="completed",
                        source_display_name=payload.source.display_name,
                        output_path=result.output_path,
                        warnings=result.warnings,
                    ),
                    task_queue=PREPARE_TASK_QUEUE,
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=DIAGNOSTIC_RETRY_POLICY,
                )
                report_path = report.path
                result = replace(result, diagnostic_report_path=report.path)
            self._status = GenerationStatusV1(
                "completed",
                "audio ready",
                2,
                diagnostic_report_path=report_path,
            )
            return result
        except asyncio.CancelledError:
            self._status = GenerationStatusV1("cancelling", "cancelling", 0)
            raise
        except Exception as exc:
            self._status = GenerationStatusV1("diagnostics", "preparing diagnostics", 0)
            report_path = ""
            try:
                report = await workflow.execute_activity(
                    finalize_diagnostic_report_v1,
                    DiagnosticReportInputV1(
                        scope="generation",
                        identifier=payload.job_id,
                        data_dir=payload.data_dir,
                        reason="failure",
                        outcome="failed",
                        source_display_name=payload.source.display_name,
                        failures=[
                            FailureEnvelopeV1(
                                code=exc.__class__.__name__,
                                category="workflow",
                                stage=self._status.state,
                                retryable=False,
                                message="Audio generation failed.",
                            )
                        ],
                    ),
                    task_queue=PREPARE_TASK_QUEUE,
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=DIAGNOSTIC_RETRY_POLICY,
                )
                report_path = report.path
            except Exception:
                workflow.logger.exception("Diagnostic report creation failed")
            self._status = GenerationStatusV1(
                "failed",
                "generation failed",
                0,
                diagnostic_report_path=report_path,
            )
            raise ApplicationError(
                "Audio generation failed.",
                report_path,
                type="GenerationFailed",
                non_retryable=True,
            ) from exc


@workflow.defn(name="speekify.batch.v1")
class SpeekifyBatchWorkflowV1:
    def __init__(self) -> None:
        self._status = BatchStatusV1("queued", 0, 0, 0, 0)

    @workflow.query(name="batch_status")
    def batch_status(self) -> BatchStatusV1:
        return self._status

    @workflow.run
    async def run(self, payload: BatchWorkflowInputV1) -> BatchWorkflowResultV1:
        total = len(payload.items)
        self._status = BatchStatusV1("running", total, 0, 0, 0)
        semaphore = asyncio.Semaphore(max(1, payload.max_parallel_items))
        results: list[BatchItemResultV1 | None] = [None] * total

        async def run_item(index: int, item: GenerationWorkflowInputV1) -> None:
            async with semaphore:
                self._status = replace(
                    self._status,
                    preparing_or_running=self._status.preparing_or_running + 1,
                    current_item=item.source.display_name,
                )
                try:
                    generation = await workflow.execute_child_workflow(
                        SpeekifyGenerationWorkflowV1.run,
                        item,
                        id=item.workflow_id,
                        task_queue=WORKFLOW_TASK_QUEUE,
                    )
                    results[index] = BatchItemResultV1(
                        index=index,
                        source_id=item.source.source_id,
                        display_name=item.source.display_name,
                        status="completed",
                        generation=generation,
                        diagnostic_report_path=generation.diagnostic_report_path,
                    )
                    self._status = replace(self._status, completed=self._status.completed + 1)
                except asyncio.CancelledError:
                    results[index] = BatchItemResultV1(
                        index=index,
                        source_id=item.source.source_id,
                        display_name=item.source.display_name,
                        status="cancelled",
                    )
                    raise
                except Exception:
                    item_report_path = (
                        f"{payload.data_dir}/reports/generation-{item.job_id}.log"
                    )
                    results[index] = BatchItemResultV1(
                        index=index,
                        source_id=item.source.source_id,
                        display_name=item.source.display_name,
                        status="failed",
                        error_code="GenerationFailed",
                        error_message="Audio generation failed.",
                        diagnostic_report_path=item_report_path,
                    )
                    self._status = replace(self._status, failed=self._status.failed + 1)
                finally:
                    self._status = replace(
                        self._status,
                        preparing_or_running=max(0, self._status.preparing_or_running - 1),
                    )

        await asyncio.gather(*(run_item(index, item) for index, item in enumerate(payload.items)))
        completed_items = [item for item in results if item is not None]
        failed = sum(item.status == "failed" for item in completed_items)
        cancelled = sum(item.status == "cancelled" for item in completed_items)
        report_path = ""
        if failed or payload.verbose:
            failed_items = [item for item in completed_items if item.status == "failed"]
            report = await workflow.execute_activity(
                finalize_diagnostic_report_v1,
                DiagnosticReportInputV1(
                    scope="batch",
                    identifier=payload.batch_id,
                    data_dir=payload.data_dir,
                    reason="partial failure" if failed else "verbose",
                    outcome="failed" if failed else "completed",
                    warnings=[
                        f"{failed} item(s) failed",
                        f"{len(completed_items) - failed - cancelled} item(s) completed",
                        *[
                            f"{item.display_name}: failed; details in "
                            f"{item.diagnostic_report_path}"
                            for item in failed_items
                        ],
                    ],
                    journal_paths=[
                        item.diagnostic_report_path
                        for item in failed_items
                        if item.diagnostic_report_path
                    ],
                ),
                task_queue=PREPARE_TASK_QUEUE,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=DIAGNOSTIC_RETRY_POLICY,
            )
            report_path = report.path
        self._status = BatchStatusV1(
            "completed",
            total,
            0,
            sum(item.status == "completed" for item in completed_items),
            failed,
        )
        return BatchWorkflowResultV1(
            batch_id=payload.batch_id,
            workflow_id=payload.workflow_id,
            items=completed_items,
            completed_count=sum(item.status == "completed" for item in completed_items),
            failed_count=failed,
            cancelled_count=cancelled,
            diagnostic_report_path=report_path,
        )
