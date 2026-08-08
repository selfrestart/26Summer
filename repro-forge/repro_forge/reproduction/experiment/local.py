"""Host subprocess backend for immutable, maintainer-owned fixtures only."""

from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from contextlib import suppress
from datetime import UTC
from datetime import datetime
from pathlib import Path

from repro_forge.reproduction.fixtures import get_fixture
from repro_forge.reproduction.schemas import ArtifactRecord
from repro_forge.reproduction.schemas import EventType
from repro_forge.reproduction.schemas import ExperimentEvent
from repro_forge.reproduction.schemas import ExperimentRun
from repro_forge.reproduction.schemas import FailureCode
from repro_forge.reproduction.schemas import ObservedMetric
from repro_forge.reproduction.schemas import RunStatus
from repro_forge.reproduction.schemas import _sha256

_FORBIDDEN_ENV_PATTERNS = ("key", "token", "secret", "password", "credential", "auth")
_IS_WINDOWS = sys.platform == "win32"
_LOG_LIMIT_BYTES = 4096
_LOG_TAIL_CHARS = 4096
_METRICS_FILE = "reproforge-metrics.jsonl"


def _sanitized_env() -> dict[str, str]:
    """Return the minimum environment needed to launch the project interpreter."""
    allowed: dict[str, str] = {}
    for key, value in os.environ.items():
        lower = key.lower()
        if any(forbidden in lower for forbidden in _FORBIDDEN_ENV_PATTERNS):
            continue
        if lower in ("path", "systemroot", "windir", "pathext"):
            allowed[key] = value
    allowed["PYTHONIOENCODING"] = "utf-8"
    return allowed


async def _read_bounded(
    stream: asyncio.StreamReader | None,
    limit: int,
) -> tuple[str, bool]:
    """Drain a subprocess stream without allowing unbounded memory growth."""
    if stream is None:
        return "", False
    tail = bytearray()
    total = 0
    while True:
        chunk = await stream.read(4096)
        if not chunk:
            break
        total += len(chunk)
        tail.extend(chunk)
        if len(tail) > limit:
            del tail[: len(tail) - limit]
    return tail.decode("utf-8", errors="replace"), total > limit


async def _terminate_process_tree(process: asyncio.subprocess.Process) -> None:
    """Terminate the full process tree created for a fixture run."""
    if process.returncode is not None:
        return
    if _IS_WINDOWS:
        killer = await asyncio.create_subprocess_exec(
            "taskkill",
            "/PID",
            str(process.pid),
            "/T",
            "/F",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await killer.wait()
    else:
        killpg = os.killpg  # type: ignore[attr-defined]
        with suppress(ProcessLookupError):
            killpg(process.pid, signal.SIGTERM)
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
        except TimeoutError:
            with suppress(ProcessLookupError):
                killpg(process.pid, getattr(signal, "SIGKILL", 9))
    with suppress(ProcessLookupError):
        await process.wait()


def _blocked_fixture_run(fixture_id: object) -> ExperimentRun:
    return ExperimentRun(
        backend="local-subprocess",
        status=RunStatus.BLOCKED,
        failure_code=FailureCode.SECURITY_VIOLATION,
        events=[
            ExperimentEvent(
                sequence=1,
                event_type=EventType.ERROR,
                payload={"error": "fixture is not registered", "fixture_id": str(fixture_id)},
            )
        ],
        finished_at=datetime.now(UTC).isoformat(),
    )


async def subprocess_execute_fixture(
    fixture_id: str,
    *,
    timeout_seconds: int | None = None,
) -> ExperimentRun:
    """Resolve and run one immutable repository fixture by exact ID."""
    if not isinstance(fixture_id, str):
        return _blocked_fixture_run(fixture_id)
    fixture = get_fixture(fixture_id)
    if fixture is None or fixture.sha256 != _sha256(fixture.code):
        return _blocked_fixture_run(fixture_id)

    timeout = fixture.timeout_seconds if timeout_seconds is None else timeout_seconds
    run = ExperimentRun(
        backend="local-subprocess",
        status=RunStatus.RUNNING,
        started_at=datetime.now(UTC).isoformat(),
    )
    events: list[ExperimentEvent] = []
    seq = 0

    def event(event_type: EventType, payload: dict[str, object] | None = None) -> None:
        nonlocal seq
        seq += 1
        events.append(
            ExperimentEvent(
                sequence=seq,
                run_id=run.run_id,
                event_type=event_type,
                payload=payload or {},
            )
        )

    tmp_dir = Path(tempfile.mkdtemp(prefix="reproforge_local_"))
    output_dir = tmp_dir / "output"
    output_dir.mkdir()
    script_path = tmp_dir / "fixture.py"
    script_path.write_text(fixture.code, encoding="utf-8", newline="\n")
    env = _sanitized_env()
    env["REPROFORGE_OUTPUT_DIR"] = str(output_dir)
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if _IS_WINDOWS else 0
    process: asyncio.subprocess.Process | None = None
    stdout_task: asyncio.Task[tuple[str, bool]] | None = None
    stderr_task: asyncio.Task[tuple[str, bool]] | None = None

    try:
        event(EventType.STATUS, {"status": "starting", "fixture_id": fixture_id})
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            str(script_path),
            cwd=str(tmp_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            start_new_session=not _IS_WINDOWS,
            creationflags=creationflags,
        )
        stdout_task = asyncio.create_task(_read_bounded(process.stdout, _LOG_LIMIT_BYTES))
        stderr_task = asyncio.create_task(_read_bounded(process.stderr, _LOG_LIMIT_BYTES))

        try:
            await asyncio.wait_for(process.wait(), timeout=timeout)
        except TimeoutError:
            await _terminate_process_tree(process)
            run.status = RunStatus.TIMEOUT
            run.failure_code = FailureCode.TIMEOUT
            event(EventType.STATUS, {"status": "timeout"})
        except asyncio.CancelledError:
            await _terminate_process_tree(process)
            run.status = RunStatus.CANCELLED
            run.failure_code = FailureCode.CANCELLED
            event(EventType.STATUS, {"status": "cancelled"})
            raise

        stdout_data, stdout_truncated = await stdout_task
        stderr_data, stderr_truncated = await stderr_task
        run.stdout_tail = stdout_data[-_LOG_TAIL_CHARS:]
        run.stderr_tail = stderr_data[-_LOG_TAIL_CHARS:]
        run.log_truncated = stdout_truncated or stderr_truncated
        if run.stdout_tail:
            event(EventType.LOG_STDOUT, {"tail": run.stdout_tail})
        if run.stderr_tail:
            event(EventType.LOG_STDERR, {"tail": run.stderr_tail})
        if run.log_truncated:
            event(EventType.TRUNCATION, {"limit_bytes": _LOG_LIMIT_BYTES})

        if run.status == RunStatus.RUNNING:
            run.exit_code = process.returncode
            if process.returncode == 0:
                run.status = RunStatus.SUCCESS
                event(EventType.STATUS, {"status": "success"})
            else:
                run.status = RunStatus.FAILED
                run.failure_code = FailureCode.NON_ZERO_EXIT
                event(EventType.STATUS, {"status": "failed"})

        metrics_path = output_dir / _METRICS_FILE
        if metrics_path.is_file() and metrics_path.stat().st_size <= _LOG_LIMIT_BYTES:
            for line_number, line in enumerate(
                metrics_path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                try:
                    metric = ObservedMetric.model_validate_json(line)
                except ValueError as exc:
                    run.status = RunStatus.FAILED
                    run.failure_code = FailureCode.METRIC_PARSE_ERROR
                    event(
                        EventType.ERROR,
                        {"error": "invalid metric", "line": line_number, "detail": str(exc)},
                    )
                    break
                run.metrics.append(metric)
                event(EventType.METRIC, metric.model_dump(mode="json"))

        for path in output_dir.iterdir():
            if not path.is_file() or path.name == _METRICS_FILE:
                continue
            content = path.read_bytes()
            run.artifacts.append(
                ArtifactRecord(
                    path=path.name,
                    media_type="text/plain"
                    if path.suffix == ".txt"
                    else "application/octet-stream",
                    size_bytes=len(content),
                    sha256=hashlib.sha256(content).hexdigest(),
                    producer_step="fixture",
                )
            )
            event(EventType.ARTIFACT, {"path": path.name, "size_bytes": len(content)})

    except asyncio.CancelledError:
        raise
    except Exception as exc:
        if process is not None:
            await _terminate_process_tree(process)
        event(EventType.ERROR, {"error": str(exc)})
        run.status = RunStatus.FAILED
        run.failure_code = FailureCode.SECURITY_VIOLATION
    finally:
        if process is not None and process.returncode is None:
            await _terminate_process_tree(process)
        if stdout_task is not None and not stdout_task.done():
            stdout_task.cancel()
        if stderr_task is not None and not stderr_task.done():
            stderr_task.cancel()
        with suppress(OSError):
            shutil.rmtree(tmp_dir)
        event(EventType.STATUS, {"status": "cleaned_up"})

    run.events = events
    run.finished_at = datetime.now(UTC).isoformat()
    return run
