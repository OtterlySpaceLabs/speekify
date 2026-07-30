from pathlib import Path

import pytest
from temporalio.testing import ActivityEnvironment

from speekify.dependencies import GenerationDependencies
from speekify.extract import ExtractedContent
from speekify.temporal_activities import prepare_source_v1, synthesize_and_persist_v1
from speekify.job_store import atomic_write_json
from speekify.temporal_models import (
    GenerationOptionsV1,
    GenerationWorkflowInputV1,
    PreparedSourceRefV1,
    SourceSpecV1,
    SynthesisActivityInputV1,
    fingerprint,
)
from speekify.tts import PreparedText, SynthesisArtifact
from speekify.workflow import GenerationResult


def _payload(tmp_path: Path) -> GenerationWorkflowInputV1:
    options = GenerationOptionsV1(
        voice="M5",
        language_code="en",
        speed=1.0,
        steps=10,
        output_dir=str(tmp_path / "output"),
    )
    payload_path = tmp_path / "data" / "jobs" / "job-1" / "source.json"
    atomic_write_json(
        payload_path,
        {"schema_version": 1, "kind": "text", "value": "Hello world"},
    )
    return GenerationWorkflowInputV1(
        job_id="job-1",
        workflow_id="speekify-generation-job-1",
        request_fingerprint="fingerprint",
        source=SourceSpecV1(
            "source-1",
            "text",
            "",
            "inline text (11 characters)",
            payload_path=str(payload_path),
            payload_sha256=fingerprint({"kind": "text", "value": "Hello world"}),
        ),
        options=options,
        submitted_at="2026-07-30T12:00:00+00:00",
        data_dir=str(tmp_path / "data"),
    )


@pytest.mark.asyncio
async def test_prepare_source_persists_and_reuses_artifact(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "speekify.temporal_activities.build_dependencies",
        lambda cached=True: GenerationDependencies(synthesizer=object(), translator=object()),
    )
    environment = ActivityEnvironment()
    payload = _payload(tmp_path)

    first = await environment.run(prepare_source_v1, payload)
    second = await environment.run(prepare_source_v1, payload)

    assert Path(first.artifact_path).is_file()
    assert first.text_length == len("Hello world")
    assert not first.reused
    assert second.reused
    assert first.output_path == second.output_path


@pytest.mark.asyncio
async def test_synthesis_activity_publishes_wav_atomically(tmp_path, monkeypatch) -> None:
    payload = _payload(tmp_path)
    artifact_path = tmp_path / "data" / "jobs" / "job-1" / "prepared.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        '{"job_id":"job-1","language_code":"en","output_path":"x",'
        '"request_fingerprint":"fingerprint","schema_version":1,'
        '"source_mode":"text","text":"Hello world","title":"Hello","warnings":[]}',
        encoding="utf-8",
    )
    from speekify.job_store import sha256_file

    prepared = PreparedSourceRefV1(
        job_id="job-1",
        request_fingerprint="fingerprint",
        artifact_path=str(artifact_path),
        artifact_sha256=sha256_file(artifact_path),
        artifact_size=artifact_path.stat().st_size,
        title="Hello",
        language_code="en",
        source_mode="text",
        output_path=str(tmp_path / "output" / "hello.wav"),
        text_length=11,
    )

    async def fake_generate_audio(request, **kwargs):
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_path.write_bytes(b"RIFFfake")
        return GenerationResult(
            output_path=request.output_path,
            artifact=SynthesisArtifact(
                wav=None,
                duration_seconds=1.25,
                batch_count=1,
                prepared_text=PreparedText("Hello", "Hello", False, (), 0),
            ),
            content=ExtractedContent("Hello"),
        )

    monkeypatch.setattr(
        "speekify.temporal_activities.build_dependencies",
        lambda cached=True: GenerationDependencies(synthesizer=object(), translator=object()),
    )
    monkeypatch.setattr("speekify.temporal_activities.generate_audio", fake_generate_audio)
    environment = ActivityEnvironment()

    activity_input = SynthesisActivityInputV1(payload, prepared)
    result = await environment.run(synthesize_and_persist_v1, activity_input)
    reused = await environment.run(synthesize_and_persist_v1, activity_input)

    assert Path(result.output_path).read_bytes() == b"RIFFfake"
    assert Path(result.receipt_path).is_file()
    assert reused.reused_audio
