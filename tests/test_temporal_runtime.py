import asyncio
import hashlib
import io
import tarfile
import urllib.error
from pathlib import Path

import pytest

from speekify.temporal_runtime import (
    RuntimeLease,
    TemporalDownloadSpec,
    _daemon_command,
    _runtime_environment,
    _wait_for_shutdown,
    ensure_local_runtime,
    ensure_temporal_binary,
    managed_temporal_binary,
    runtime_health,
    temporal_download_spec,
)


@pytest.mark.asyncio
async def test_runtime_reports_offline_first_download(tmp_path, monkeypatch) -> None:
    async def unavailable(*, timeout):
        raise RuntimeError("not running")

    monkeypatch.setattr("speekify.temporal_runtime.connect_local_client", unavailable)
    monkeypatch.setattr("speekify.temporal_runtime.find_temporal_binary", lambda: None)
    monkeypatch.setattr("speekify.temporal_runtime._local_port_is_open", lambda: False)
    monkeypatch.setattr(
        "speekify.temporal_runtime.ensure_temporal_binary",
        lambda data_dir: (_ for _ in ()).throw(RuntimeError("works offline")),
    )

    with pytest.raises(RuntimeError, match="works offline"):
        await ensure_local_runtime(tmp_path)


def test_runtime_health_detects_stale_pid(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "state.json").write_text(
        '{"pid": 99999999, "address": "127.0.0.1:7233"}',
        encoding="utf-8",
    )

    health = runtime_health(tmp_path)

    assert health == {"running": False, "stale": True}


def test_daemon_command_uses_module_for_python_install(tmp_path, monkeypatch) -> None:
    monkeypatch.delattr("speekify.temporal_runtime.sys.frozen", raising=False)

    command = _daemon_command(tmp_path)

    assert command[1:3] == ["-m", "speekify"]
    assert command[-4:] == ["_runtime", "daemon", "--data-dir", str(tmp_path)]


def test_daemon_command_uses_frozen_executable_directly(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("speekify.temporal_runtime.sys.frozen", True, raising=False)

    command = _daemon_command(tmp_path)

    assert command[1:] == ["_runtime", "daemon", "--data-dir", str(tmp_path)]


def test_temporal_download_spec_supports_current_macos(monkeypatch) -> None:
    monkeypatch.setattr("speekify.temporal_runtime.platform.system", lambda: "Darwin")
    monkeypatch.setattr("speekify.temporal_runtime.platform.machine", lambda: "arm64")

    spec = temporal_download_spec()

    assert spec.asset_name == "temporal_cli_1.8.1_darwin_arm64.tar.gz"
    assert len(spec.sha256) == 64
    assert spec.url.startswith("https://github.com/temporalio/cli/releases/download/v1.8.1/")


def test_temporal_download_is_verified_installed_and_reused(tmp_path, monkeypatch) -> None:
    archive = _temporal_archive(b"verified temporal binary")
    digest = hashlib.sha256(archive).hexdigest()
    calls = 0

    def fake_urlopen(request, *, timeout):
        nonlocal calls
        calls += 1
        assert request.full_url == "https://github.com/temporalio/cli/releases/download/v1.8.1/test.tar.gz"
        assert timeout == 60
        return _DownloadResponse(archive)

    monkeypatch.setattr("speekify.temporal_runtime.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr(
        "speekify.temporal_runtime.temporal_download_spec",
        lambda: TemporalDownloadSpec("test.tar.gz", digest),
    )
    monkeypatch.setattr("speekify.temporal_runtime.shutil.which", lambda name: None)

    installed = ensure_temporal_binary(tmp_path)
    reused = ensure_temporal_binary(tmp_path)

    assert installed == managed_temporal_binary(tmp_path)
    assert installed.read_bytes() == b"verified temporal binary"
    assert installed.stat().st_mode & 0o111
    assert (installed.parent / "install.json").is_file()
    assert reused == installed
    assert calls == 1


def test_temporal_download_rejects_wrong_checksum(tmp_path, monkeypatch) -> None:
    archive = _temporal_archive(b"tampered")
    monkeypatch.setattr(
        "speekify.temporal_runtime.urllib.request.urlopen",
        lambda request, timeout: _DownloadResponse(archive),
    )
    monkeypatch.setattr(
        "speekify.temporal_runtime.temporal_download_spec",
        lambda: TemporalDownloadSpec("test.tar.gz", "0" * 64),
    )
    monkeypatch.setattr("speekify.temporal_runtime.shutil.which", lambda name: None)

    with pytest.raises(RuntimeError, match="SHA-256"):
        ensure_temporal_binary(tmp_path)

    assert not managed_temporal_binary(tmp_path).exists()


def test_temporal_download_reports_offline_error(tmp_path, monkeypatch) -> None:
    def offline(request, *, timeout):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr("speekify.temporal_runtime.urllib.request.urlopen", offline)
    monkeypatch.setattr(
        "speekify.temporal_runtime.temporal_download_spec",
        lambda: TemporalDownloadSpec("test.tar.gz", "0" * 64),
    )
    monkeypatch.setattr("speekify.temporal_runtime.shutil.which", lambda name: None)

    with pytest.raises(RuntimeError, match="once downloaded, generation works offline"):
        ensure_temporal_binary(tmp_path)


def test_runtime_environment_disables_telemetry(monkeypatch) -> None:
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "otlp")

    environment = _runtime_environment()

    assert "OTEL_TRACES_EXPORTER" not in environment
    assert environment["DO_NOT_TRACK"] == "1"
    assert environment["TEMPORAL_CLI_DISABLE_TELEMETRY"] == "1"


@pytest.mark.asyncio
async def test_runtime_waits_for_generation_lease_before_idle_shutdown(
    tmp_path,
    monkeypatch,
) -> None:
    root = tmp_path
    runtime_dir = root / "runtime"
    runtime_dir.mkdir(parents=True)
    usage_path = runtime_dir / "usage.lock"
    usage_stream = usage_path.open("a+")
    monkeypatch.setattr(
        "speekify.temporal_runtime._has_active_workflows",
        _constant_workflow_state(False),
    )

    async with RuntimeLease(root):
        waiter = _shutdown_waiter(
            usage_path,
            usage_stream,
            idle_timeout=0.02,
            poll_interval=0.002,
        )
        task = asyncio.create_task(waiter)
        await asyncio.sleep(0.04)
        assert not task.done()

    assert await task == "five minutes idle"
    usage_stream.close()


@pytest.mark.asyncio
async def test_runtime_defers_shutdown_signal_until_client_lease_is_released(
    tmp_path,
    monkeypatch,
) -> None:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)
    usage_path = runtime_dir / "usage.lock"
    usage_stream = usage_path.open("a+")
    stop_event = asyncio.Event()
    stop_event.set()
    monkeypatch.setattr(
        "speekify.temporal_runtime._has_active_workflows",
        _constant_workflow_state(False),
    )

    async with RuntimeLease(tmp_path):
        task = asyncio.create_task(
            _shutdown_waiter(
                usage_path,
                usage_stream,
                idle_timeout=0.02,
                poll_interval=0.002,
                stop_event=stop_event,
            )
        )
        await asyncio.sleep(0.02)
        assert not task.done()

    assert await task == "shutdown requested"
    usage_stream.close()


@pytest.mark.asyncio
async def test_runtime_waits_while_temporal_reports_active_workflow(
    tmp_path,
    monkeypatch,
) -> None:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)
    usage_path = runtime_dir / "usage.lock"
    usage_stream = usage_path.open("a+")
    active = True

    async def workflow_state(_client):
        return active

    monkeypatch.setattr(
        "speekify.temporal_runtime._has_active_workflows",
        workflow_state,
    )
    task = asyncio.create_task(
        _shutdown_waiter(
            usage_path,
            usage_stream,
            idle_timeout=0.02,
            poll_interval=0.002,
        )
    )
    await asyncio.sleep(0.04)
    assert not task.done()

    active = False
    assert await task == "five minutes idle"
    usage_stream.close()


@pytest.mark.asyncio
async def test_runtime_fails_safe_when_workflow_visibility_is_unavailable(
    tmp_path,
    monkeypatch,
) -> None:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)
    usage_path = runtime_dir / "usage.lock"
    usage_stream = usage_path.open("a+")
    visible = False

    async def workflow_state(_client):
        return False if visible else None

    monkeypatch.setattr(
        "speekify.temporal_runtime._has_active_workflows",
        workflow_state,
    )
    task = asyncio.create_task(
        _shutdown_waiter(
            usage_path,
            usage_stream,
            idle_timeout=0.02,
            poll_interval=0.002,
        )
    )
    await asyncio.sleep(0.04)
    assert not task.done()

    visible = True
    assert await task == "five minutes idle"
    usage_stream.close()


def _constant_workflow_state(value):
    async def workflow_state(_client):
        return value

    return workflow_state


def _shutdown_waiter(
    usage_path: Path,
    usage_stream,
    *,
    idle_timeout: float,
    poll_interval: float,
    stop_event: asyncio.Event | None = None,
):
    class RunningServer:
        @staticmethod
        def poll():
            return None

    return _wait_for_shutdown(
        object(),
        RunningServer(),
        stop_event or asyncio.Event(),
        usage_lock_path=usage_path,
        usage_lock_stream=usage_stream,
        idle_timeout=idle_timeout,
        poll_interval=poll_interval,
    )


class _DownloadResponse(io.BytesIO):
    headers: dict[str, str] = {}


def _temporal_archive(binary: bytes) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        member = tarfile.TarInfo("temporal")
        member.size = len(binary)
        member.mode = 0o755
        archive.addfile(member, io.BytesIO(binary))
    return stream.getvalue()
