from __future__ import annotations

import asyncio
import fcntl
import hashlib
import os
import platform
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import timedelta
from importlib import metadata
from pathlib import Path

from temporalio.client import Client
from temporalio.worker import Worker

from speekify.job_store import (
    atomic_write_json,
    default_data_dir,
    ensure_data_layout,
    read_json,
)
from speekify.temporal_activities import (
    finalize_diagnostic_report_v1,
    prepare_source_v1,
    synthesize_and_persist_v1,
)
from speekify.temporal_workflows import (
    AUDIO_TASK_QUEUE,
    PREPARE_TASK_QUEUE,
    WORKFLOW_TASK_QUEUE,
    SpeekifyBatchWorkflowV1,
    SpeekifyGenerationWorkflowV1,
)

LOCAL_ADDRESS = "127.0.0.1:7233"
TEMPORAL_BINARY_ENV = "SPEEKIFY_TEMPORAL_BIN"
RUNTIME_START_TIMEOUT = 20.0
RUNTIME_IDLE_TIMEOUT_SECONDS = 5 * 60.0
RUNTIME_ACTIVITY_POLL_SECONDS = 5.0
TEMPORAL_CLI_VERSION = "1.8.1"
TEMPORAL_RELEASE_BASE_URL = (
    f"https://github.com/temporalio/cli/releases/download/v{TEMPORAL_CLI_VERSION}"
)
TEMPORAL_CHECKSUMS_URL = f"{TEMPORAL_RELEASE_BASE_URL}/checksums.txt"
MAX_TEMPORAL_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_TEMPORAL_BINARY_BYTES = 250 * 1024 * 1024


@dataclass(frozen=True)
class TemporalDownloadSpec:
    asset_name: str
    sha256: str

    @property
    def url(self) -> str:
        return f"{TEMPORAL_RELEASE_BASE_URL}/{self.asset_name}"


class RuntimeLease:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._path: Path | None = None
        self._stream = None

    async def __aenter__(self) -> RuntimeLease:
        root = ensure_data_layout(self._data_dir)
        self._path = root / "runtime" / "usage.lock"
        self._stream = self._path.open("a+")
        await asyncio.to_thread(
            fcntl.flock,
            self._stream.fileno(),
            fcntl.LOCK_SH,
        )
        os.utime(self._path, None)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if self._stream is None:
            return
        if self._path is not None:
            os.utime(self._path, None)
        fcntl.flock(self._stream.fileno(), fcntl.LOCK_UN)
        self._stream.close()
        self._stream = None


# Values copied from the official release's checksums.txt asset. Updating the
# version requires updating every URL-derived filename and checksum together.
TEMPORAL_DOWNLOADS = {
    ("darwin", "amd64"): TemporalDownloadSpec(
        "temporal_cli_1.8.1_darwin_amd64.tar.gz",
        "87fc25a703d473ba078a052e2e83fc62e985abf151466d92a8bbbeacfc317f06",
    ),
    ("darwin", "arm64"): TemporalDownloadSpec(
        "temporal_cli_1.8.1_darwin_arm64.tar.gz",
        "e942d2ba2634720293bded2a9061ac471a7fd44d883a6704b8d0ecb94995d6a6",
    ),
    ("linux", "amd64"): TemporalDownloadSpec(
        "temporal_cli_1.8.1_linux_amd64.tar.gz",
        "b94417b9a8760b30217f4b881dabce4b16a76a38b5e99e2eca3ce358b8030f06",
    ),
    ("linux", "arm64"): TemporalDownloadSpec(
        "temporal_cli_1.8.1_linux_arm64.tar.gz",
        "f622eba969aa58fdbe8a7b58feba7578b3fc935305079eb071d34bac12ffa5bb",
    ),
}


def find_temporal_binary(data_dir: Path | None = None) -> Path | None:
    configured = os.environ.get(TEMPORAL_BINARY_ENV, "").strip()
    if configured:
        path = Path(configured).expanduser()
        return path if _is_executable(path) else None
    managed = managed_temporal_binary(data_dir or default_data_dir())
    if _is_executable(managed):
        return managed
    discovered = shutil.which("temporal")
    return Path(discovered) if discovered else None


def managed_temporal_binary(data_dir: Path) -> Path:
    return data_dir / "bin" / "temporal" / TEMPORAL_CLI_VERSION / "temporal"


def ensure_temporal_binary(data_dir: Path) -> Path:
    data_dir = ensure_data_layout(data_dir)
    existing = find_temporal_binary(data_dir)
    if existing is not None:
        return existing
    spec = temporal_download_spec()
    lock_path = data_dir / "runtime" / "temporal-install.lock"
    with lock_path.open("a+") as lock_stream:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX)
        existing = find_temporal_binary(data_dir)
        if existing is not None:
            return existing
        return _download_temporal_binary(data_dir, spec)


def temporal_download_spec() -> TemporalDownloadSpec:
    system = platform.system().lower()
    machine = platform.machine().lower()
    machine = {"x86_64": "amd64", "aarch64": "arm64"}.get(machine, machine)
    try:
        return TEMPORAL_DOWNLOADS[(system, machine)]
    except KeyError as exc:
        raise RuntimeError(
            "Speekify cannot provision its local reliability runtime on "
            f"{system}/{machine}. Supported pip platforms are macOS and Linux "
            "on arm64 or amd64."
        ) from exc


def _download_temporal_binary(
    data_dir: Path,
    spec: TemporalDownloadSpec,
) -> Path:
    runtime_dir = data_dir / "runtime"
    target = managed_temporal_binary(data_dir)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    archive_fd, archive_name = tempfile.mkstemp(
        prefix="temporal-",
        suffix=".tar.gz",
        dir=runtime_dir,
    )
    os.close(archive_fd)
    archive_path = Path(archive_name)
    pending = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        _download_archive(spec, archive_path)
        with tarfile.open(archive_path, mode="r:gz") as archive:
            members = [
                member
                for member in archive.getmembers()
                if member.isfile() and Path(member.name).name == "temporal"
            ]
            if len(members) != 1:
                raise RuntimeError(
                    "The verified Temporal archive did not contain exactly one executable."
                )
            if members[0].size > MAX_TEMPORAL_BINARY_BYTES:
                raise RuntimeError("The Temporal executable exceeds the permitted size.")
            extracted = archive.extractfile(members[0])
            if extracted is None:
                raise RuntimeError("The Temporal executable could not be read.")
            binary_hash = hashlib.sha256()
            with pending.open("wb") as output:
                while chunk := extracted.read(1024 * 1024):
                    output.write(chunk)
                    binary_hash.update(chunk)
                output.flush()
                os.fsync(output.fileno())
        os.chmod(pending, 0o700)
        os.replace(pending, target)
        atomic_write_json(
            target.parent / "install.json",
            {
                "version": TEMPORAL_CLI_VERSION,
                "source_url": spec.url,
                "checksums_url": TEMPORAL_CHECKSUMS_URL,
                "archive_sha256": spec.sha256,
                "binary_sha256": binary_hash.hexdigest(),
                "telemetry": "disabled",
            },
        )
        return target
    finally:
        archive_path.unlink(missing_ok=True)
        pending.unlink(missing_ok=True)


def _download_archive(spec: TemporalDownloadSpec, destination: Path) -> None:
    request = urllib.request.Request(
        spec.url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": f"Speekify/{_package_version()}",
        },
    )
    digest = hashlib.sha256()
    downloaded = 0
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_TEMPORAL_ARCHIVE_BYTES:
                raise RuntimeError("The Temporal download exceeds the permitted size.")
            with destination.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    downloaded += len(chunk)
                    if downloaded > MAX_TEMPORAL_ARCHIVE_BYTES:
                        raise RuntimeError("The Temporal download exceeds the permitted size.")
                    output.write(chunk)
                    digest.update(chunk)
                output.flush()
                os.fsync(output.fileno())
    except (OSError, urllib.error.URLError) as exc:
        raise RuntimeError(
            "Speekify could not download its pinned local reliability runtime "
            f"(Temporal CLI {TEMPORAL_CLI_VERSION}). Check the internet connection "
            "and retry; once downloaded, generation works offline. No manual "
            f"installation is required. Details: {exc}"
        ) from exc
    if downloaded == 0:
        raise RuntimeError("The Temporal runtime download was empty.")
    actual = digest.hexdigest()
    if actual != spec.sha256:
        raise RuntimeError(
            "The Temporal runtime download failed its SHA-256 integrity check; "
            "the file was discarded."
        )


def _is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


async def connect_local_client(*, timeout: float = 2.0) -> Client:
    return await asyncio.wait_for(Client.connect(LOCAL_ADDRESS), timeout=timeout)


async def ensure_local_runtime(data_dir: Path) -> Client:
    ensure_data_layout(data_dir)
    health = runtime_health(data_dir)
    if health.get("running"):
        try:
            return await connect_local_client(timeout=0.8)
        except Exception:
            pass
    elif _local_port_is_open():
        raise RuntimeError(
            f"Port {LOCAL_ADDRESS} is already used by another local process. "
            "Stop that process or configure another Temporal port."
        )
    await asyncio.to_thread(ensure_temporal_binary, data_dir)
    runtime_log = data_dir / "runtime" / "daemon.log"
    with runtime_log.open("a", encoding="utf-8") as stream:
        subprocess.Popen(
            _daemon_command(data_dir),
            stdin=subprocess.DEVNULL,
            stdout=stream,
            stderr=stream,
            start_new_session=True,
            close_fds=True,
        )
    deadline = asyncio.get_running_loop().time() + RUNTIME_START_TIMEOUT
    last_error: Exception | None = None
    while asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(0.25)
        try:
            return await connect_local_client(timeout=0.8)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(
        "Speekify could not start its local reliability engine. "
        f"See {runtime_log} for details."
    ) from last_error


async def run_daemon(data_dir: Path) -> int:
    data_dir = ensure_data_layout(data_dir)
    lock_path = data_dir / "runtime" / "daemon.lock"
    lock_stream = lock_path.open("a+")
    try:
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return 0
    usage_lock_path = data_dir / "runtime" / "usage.lock"
    usage_lock_stream = usage_lock_path.open("a+")
    temporal_binary = ensure_temporal_binary(data_dir)
    temporal_log_path = data_dir / "runtime" / "temporal.log"
    temporal_log = temporal_log_path.open("a", encoding="utf-8")
    server = subprocess.Popen(
        [
            str(temporal_binary),
            "server",
            "start-dev",
            "--ip",
            "127.0.0.1",
            "--port",
            "7233",
            "--headless",
            "--db-filename",
            str(data_dir / "temporal" / "temporal.db"),
        ],
        stdin=subprocess.DEVNULL,
        stdout=temporal_log,
        stderr=temporal_log,
        close_fds=True,
        env=_runtime_environment(),
    )
    state_path = data_dir / "runtime" / "state.json"
    atomic_write_json(
        state_path,
        {
            "pid": os.getpid(),
            "server_pid": server.pid,
            "address": LOCAL_ADDRESS,
            "version": _package_version(),
        },
    )
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)
    try:
        client = await _wait_for_server(server)
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(
                Worker(
                    client,
                    task_queue=WORKFLOW_TASK_QUEUE,
                    workflows=[SpeekifyGenerationWorkflowV1, SpeekifyBatchWorkflowV1],
                    graceful_shutdown_timeout=timedelta(seconds=10),
                )
            )
            await stack.enter_async_context(
                Worker(
                    client,
                    task_queue=PREPARE_TASK_QUEUE,
                    activities=[prepare_source_v1, finalize_diagnostic_report_v1],
                    max_concurrent_activities=2,
                    graceful_shutdown_timeout=timedelta(seconds=10),
                )
            )
            await stack.enter_async_context(
                Worker(
                    client,
                    task_queue=AUDIO_TASK_QUEUE,
                    activities=[synthesize_and_persist_v1],
                    max_concurrent_activities=1,
                    graceful_shutdown_timeout=timedelta(seconds=30),
                )
            )
            shutdown_reason = await _wait_for_shutdown(
                client,
                server,
                stop_event,
                usage_lock_path=usage_lock_path,
                usage_lock_stream=usage_lock_stream,
            )
            print(
                f"Speekify local runtime stopping: {shutdown_reason}.",
                flush=True,
            )
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                await asyncio.wait_for(asyncio.to_thread(server.wait), timeout=10)
            except TimeoutError:
                server.kill()
        temporal_log.close()
        state_path.unlink(missing_ok=True)
        # Release singleton ownership before allowing a waiting client lease to
        # proceed. Otherwise that client can spawn a replacement daemon while
        # this process still owns daemon.lock, and the replacement exits early.
        fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)
        lock_stream.close()
        fcntl.flock(usage_lock_stream.fileno(), fcntl.LOCK_UN)
        usage_lock_stream.close()
    return 0


async def _wait_for_server(server: subprocess.Popen[str]) -> Client:
    deadline = asyncio.get_running_loop().time() + RUNTIME_START_TIMEOUT
    last_error: Exception | None = None
    while asyncio.get_running_loop().time() < deadline:
        if server.poll() is not None:
            raise RuntimeError(f"Temporal local server exited with code {server.returncode}.")
        try:
            return await connect_local_client(timeout=0.8)
        except Exception as exc:
            last_error = exc
        await asyncio.sleep(0.25)
    raise RuntimeError("Temporal local server did not become ready.") from last_error


async def _wait_for_shutdown(
    client: Client,
    server: subprocess.Popen[str],
    stop_event: asyncio.Event,
    *,
    usage_lock_path: Path,
    usage_lock_stream,
    idle_timeout: float = RUNTIME_IDLE_TIMEOUT_SECONDS,
    poll_interval: float = RUNTIME_ACTIVITY_POLL_SECONDS,
) -> str:
    loop = asyncio.get_running_loop()
    idle_since = loop.time()
    last_usage_mtime = usage_lock_path.stat().st_mtime_ns
    while True:
        if server.poll() is not None:
            raise RuntimeError(f"Temporal local server exited with code {server.returncode}.")
        now = loop.time()
        usage_mtime = usage_lock_path.stat().st_mtime_ns
        if usage_mtime != last_usage_mtime:
            idle_since = now
            last_usage_mtime = usage_mtime
        if not _try_lock_exclusive(usage_lock_stream):
            idle_since = now
        else:
            active_workflows = await _has_active_workflows(client)
            if active_workflows is not False:
                idle_since = now
                _unlock(usage_lock_stream)
            elif stop_event.is_set():
                return "shutdown requested"
            elif now - idle_since >= idle_timeout:
                return "five minutes idle"
            else:
                _unlock(usage_lock_stream)
        await asyncio.sleep(poll_interval)


async def _has_active_workflows(client: Client) -> bool | None:
    try:
        executions = client.list_workflows(
            'ExecutionStatus = "Running"',
            limit=1,
            rpc_timeout=timedelta(seconds=3),
        )
        async for _ in executions:
            return True
        return False
    except Exception:
        # Fail safe: a temporary visibility failure must never stop active work.
        return None


def _try_lock_exclusive(stream) -> bool:
    try:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    return True


def _unlock(stream) -> None:
    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def runtime_health(data_dir: Path) -> dict[str, object]:
    state_path = data_dir / "runtime" / "state.json"
    if not state_path.is_file():
        return {"running": False}
    state = read_json(state_path)
    pid = int(state.get("pid", 0))
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return {"running": False, "stale": True}
    return {"running": True, **state}


def stop_runtime(data_dir: Path) -> bool:
    health = runtime_health(data_dir)
    if not health.get("running"):
        return False
    os.kill(int(health["pid"]), signal.SIGTERM)
    return True


def _package_version() -> str:
    try:
        return metadata.version("speekify")
    except metadata.PackageNotFoundError:
        return "unknown"


def _local_port_is_open() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(0.2)
        return connection.connect_ex(("127.0.0.1", 7233)) == 0


def _daemon_command(data_dir: Path) -> list[str]:
    command = [sys.executable]
    if not getattr(sys, "frozen", False):
        command.extend(["-m", "speekify"])
    command.extend(["_runtime", "daemon", "--data-dir", str(data_dir)])
    return command


def _runtime_environment() -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("OTEL_")
    }
    environment.update(
        {
            "DO_NOT_TRACK": "1",
            "TEMPORAL_CLI_DISABLE_TELEMETRY": "1",
            "TEMPORAL_CLI_DISABLE_NEWSFEED": "1",
        }
    )
    return environment
