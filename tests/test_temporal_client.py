from __future__ import annotations

from pathlib import Path

import pytest

from speekify import temporal_client


class RecordingLease:
    held = False
    entered_paths: list[Path] = []

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    async def __aenter__(self):
        type(self).held = True
        type(self).entered_paths.append(self.data_dir)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        type(self).held = False


@pytest.fixture(autouse=True)
def reset_recording_lease() -> None:
    RecordingLease.held = False
    RecordingLease.entered_paths = []


@pytest.mark.asyncio
async def test_generation_holds_runtime_lease_for_the_whole_request(
    tmp_path,
    monkeypatch,
) -> None:
    expected = object()

    async def run_under_lease(request, **kwargs):
        assert RecordingLease.held
        assert kwargs["data_dir"] == tmp_path
        return expected

    monkeypatch.setattr(temporal_client, "RuntimeLease", RecordingLease)
    monkeypatch.setattr(temporal_client, "_run_temporal_generation", run_under_lease)

    result = await temporal_client.run_temporal_generation(object(), data_dir=tmp_path)

    assert result is expected
    assert RecordingLease.entered_paths == [tmp_path]
    assert not RecordingLease.held


@pytest.mark.asyncio
async def test_batch_holds_runtime_lease_for_the_whole_request(
    tmp_path,
    monkeypatch,
) -> None:
    expected = object()

    async def run_under_lease(expanded, **kwargs):
        assert RecordingLease.held
        assert kwargs["data_dir"] == tmp_path
        return expected

    monkeypatch.setattr(temporal_client, "RuntimeLease", RecordingLease)
    monkeypatch.setattr(temporal_client, "_run_temporal_batch", run_under_lease)

    result = await temporal_client.run_temporal_batch(
        object(),
        options=object(),
        data_dir=tmp_path,
    )

    assert result is expected
    assert RecordingLease.entered_paths == [tmp_path]
    assert not RecordingLease.held
