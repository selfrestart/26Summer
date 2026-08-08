"""Fail-closed Docker backend for P3 sandboxed experiment execution."""

from __future__ import annotations

import asyncio
import hashlib
import io
import mimetypes
import shutil
import tarfile
import tempfile
from contextlib import suppress
from datetime import UTC
from datetime import datetime
from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import Any

from repro_forge.reproduction.experiment.runtime_profiles import resolve_runtime_profile
from repro_forge.reproduction.schemas import ArtifactRecord
from repro_forge.reproduction.schemas import EnvironmentSnapshot
from repro_forge.reproduction.schemas import EventType
from repro_forge.reproduction.schemas import ExperimentEvent
from repro_forge.reproduction.schemas import ExperimentRun
from repro_forge.reproduction.schemas import ExperimentSpec
from repro_forge.reproduction.schemas import FailureCode
from repro_forge.reproduction.schemas import ObservedMetric
from repro_forge.reproduction.schemas import ResourceLimits
from repro_forge.reproduction.schemas import RunStatus
from repro_forge.reproduction.schemas import validate_bundle_path

if TYPE_CHECKING:
    from repro_forge.reproduction.schemas import FixtureSpec
    from repro_forge.reproduction.schemas import ReproductionBundle

_METRICS_FILE = "reproforge-metrics.jsonl"
_CONTAINER_USER = "65532:65532"
_OUTPUT_COLLECTOR_SCRIPT = r"""
import os
import stat
import sys
import tarfile

root = "/output"
budget = int(sys.argv[1])
count = 0
total = 0
with tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as archive:
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        safe_directories = []
        for name in directories:
            path = os.path.join(current, name)
            if not stat.S_ISDIR(os.lstat(path).st_mode):
                raise RuntimeError(f"unsafe output directory: {path}")
            safe_directories.append(name)
        directories[:] = safe_directories
        for name in files:
            path = os.path.join(current, name)
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(path, flags)
            with os.fdopen(descriptor, "rb", closefd=True) as handle:
                metadata = os.fstat(handle.fileno())
                if not stat.S_ISREG(metadata.st_mode):
                    raise RuntimeError(f"unsafe output file: {path}")
                count += 1
                if count > 1024:
                    raise RuntimeError("output file count exceeded 1024")
                total += metadata.st_size
                if total > budget:
                    raise RuntimeError(f"output content exceeded {budget} bytes")
                relative = os.path.relpath(path, root).replace(os.sep, "/")
                info = tarfile.TarInfo(f"output/{relative}")
                info.size = metadata.st_size
                archive.addfile(info, handle)
"""


class _ArtifactLimitError(RuntimeError):
    pass


def _artifact_allowed(path: str, allowlist: list[str]) -> bool:
    return any(path == rule or path.startswith(f"{rule.rstrip('/')}/") for rule in allowlist)


def _append_bounded(tail: bytearray, chunk: bytes, limit: int) -> None:
    tail.extend(chunk)
    if len(tail) > limit:
        del tail[: len(tail) - limit]


def _execute_bounded(
    api: Any,
    container_id: str,
    command: list[str],
    limit: int,
) -> tuple[int, str, str, bool]:
    """Run declared argv via Docker exec while the container tmpfs stays mounted."""
    created = api.exec_create(
        container_id,
        cmd=command,
        stdout=True,
        stderr=True,
        stdin=False,
        tty=False,
        privileged=False,
        user=_CONTAINER_USER,
        workdir="/bundle",
    )
    exec_id = str(created["Id"])
    stdout_tail = bytearray()
    stderr_tail = bytearray()
    stdout_total = 0
    stderr_total = 0
    stream = api.exec_start(exec_id, detach=False, tty=False, stream=True, demux=True)
    for item in stream:
        if isinstance(item, tuple):
            stdout_chunk, stderr_chunk = item
        else:
            stdout_chunk, stderr_chunk = item, None
        if stdout_chunk:
            chunk = bytes(stdout_chunk)
            stdout_total += len(chunk)
            _append_bounded(stdout_tail, chunk, limit)
        if stderr_chunk:
            chunk = bytes(stderr_chunk)
            stderr_total += len(chunk)
            _append_bounded(stderr_tail, chunk, limit)

    inspected = api.exec_inspect(exec_id)
    exit_code = inspected.get("ExitCode")
    if exit_code is None:
        raise RuntimeError("Docker exec finished without an exit code")
    return (
        int(exit_code),
        stdout_tail.decode("utf-8", errors="replace"),
        stderr_tail.decode("utf-8", errors="replace"),
        stdout_total > limit or stderr_total > limit,
    )


def _parse_output_archive(archive_bytes: bytes, limit: int) -> dict[str, bytes]:
    buffer = io.BytesIO(archive_bytes)
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=buffer, mode="r:*") as archive:
        for member in archive.getmembers():
            parts = PurePosixPath(member.name).parts
            if not parts or parts[0] != "output":
                raise _ArtifactLimitError(
                    f"archive member is outside the output root: {member.name}"
                )
            if member.isdir():
                if len(parts) > 1:
                    try:
                        validate_bundle_path(PurePosixPath(*parts[1:]).as_posix())
                    except ValueError as exc:
                        raise _ArtifactLimitError(
                            f"unsafe archive member path: {member.name}"
                        ) from exc
                continue
            if not member.isfile() or member.issym() or member.islnk():
                raise _ArtifactLimitError(f"unsafe archive member: {member.name}")
            try:
                relative = validate_bundle_path(PurePosixPath(*parts[1:]).as_posix())
            except ValueError as exc:
                raise _ArtifactLimitError(f"unsafe archive member path: {member.name}") from exc
            extracted = archive.extractfile(member)
            if extracted is None:
                raise _ArtifactLimitError(f"could not read archive member: {member.name}")
            content = extracted.read(limit + 1)
            if len(content) > limit:
                raise _ArtifactLimitError(f"artifact exceeded {limit} bytes: {relative}")
            files[relative] = content
    return files


def _collect_output_archive(api: Any, container_id: str, limit: int) -> dict[str, bytes]:
    """Collect a bounded archive through a trusted exec while tmpfs is mounted."""
    created = api.exec_create(
        container_id,
        cmd=["python", "-I", "-c", _OUTPUT_COLLECTOR_SCRIPT, str(limit)],
        stdout=True,
        stderr=True,
        stdin=False,
        tty=False,
        privileged=False,
        user=_CONTAINER_USER,
        workdir="/bundle",
    )
    exec_id = str(created["Id"])
    buffer = io.BytesIO()
    stderr_tail = bytearray()
    stream_limit = limit + 2 * 1024 * 1024
    stream = api.exec_start(exec_id, detach=False, tty=False, stream=True, demux=True)
    for item in stream:
        if isinstance(item, tuple):
            stdout_chunk, stderr_chunk = item
        else:
            stdout_chunk, stderr_chunk = item, None
        if stdout_chunk:
            buffer.write(bytes(stdout_chunk))
            if buffer.tell() > stream_limit:
                raise _ArtifactLimitError(f"output archive exceeded {stream_limit} bytes")
        if stderr_chunk:
            _append_bounded(stderr_tail, bytes(stderr_chunk), 4096)

    inspected = api.exec_inspect(exec_id)
    if inspected.get("ExitCode") != 0:
        detail = stderr_tail.decode("utf-8", errors="replace")
        raise _ArtifactLimitError(f"output collector failed: {detail}")
    return _parse_output_archive(buffer.getvalue(), limit)


def _blocked_run(
    *,
    bundle_id: str,
    failure_code: FailureCode,
    message: str,
) -> ExperimentRun:
    run = ExperimentRun(
        bundle_id=bundle_id,
        backend="docker",
        status=RunStatus.BLOCKED,
        failure_code=failure_code,
        finished_at=datetime.now(UTC).isoformat(),
    )
    run.events = [
        ExperimentEvent(
            sequence=1,
            run_id=run.run_id,
            event_type=EventType.ERROR,
            payload={"error": message},
        )
    ]
    return run


async def docker_execute(
    bundle: ReproductionBundle | FixtureSpec,
    experiment: ExperimentSpec | None = None,
    *,
    fixture: FixtureSpec | None = None,
) -> ExperimentRun:
    """Execute generated code only inside a configured, digest-pinned sandbox image."""
    bundle_id = getattr(bundle, "bundle_id", "")
    if fixture is not None:
        experiment = ExperimentSpec(
            experiment_name=f"fixture:{fixture.fixture_id}",
            entrypoint=["python", "fixture.py"],
            timeout_seconds=fixture.timeout_seconds,
            artifact_allowlist=["cleanup-smoke.txt"],
        )
    if experiment is None:
        return _blocked_run(
            bundle_id=bundle_id,
            failure_code=FailureCode.PATH_VALIDATION,
            message="experiment specification is required",
        )
    if experiment.network_policy != "offline" or experiment.network_allowlist:
        return _blocked_run(
            bundle_id=bundle_id,
            failure_code=FailureCode.NETWORK_DENIED,
            message="P3 Docker execution only supports offline network policy",
        )
    if any(
        not dependency.locked or not dependency.version for dependency in experiment.dependencies
    ):
        return _blocked_run(
            bundle_id=bundle_id,
            failure_code=FailureCode.SECURITY_VIOLATION,
            message="Docker execution requires fully locked dependencies",
        )
    if experiment.unresolved:
        return _blocked_run(
            bundle_id=bundle_id,
            failure_code=FailureCode.SECURITY_VIOLATION,
            message="Docker execution is blocked while experiment fields remain unresolved",
        )

    profile = resolve_runtime_profile(experiment.runtime_profile)
    if profile is None:
        return _blocked_run(
            bundle_id=bundle_id,
            failure_code=FailureCode.IMAGE_PULL_FAILED,
            message="runtime profile is not configured with an exact reviewed image digest",
        )

    try:
        import docker
    except ImportError:
        return _blocked_run(
            bundle_id=bundle_id,
            failure_code=FailureCode.DOCKER_UNAVAILABLE,
            message="docker optional dependency is not installed",
        )

    run = ExperimentRun(
        bundle_id=bundle_id,
        backend="docker",
        status=RunStatus.RUNNING,
        started_at=datetime.now(UTC).isoformat(),
    )
    events: list[ExperimentEvent] = []
    sequence = 0

    def event(event_type: EventType, payload: dict[str, object] | None = None) -> None:
        nonlocal sequence
        sequence += 1
        events.append(
            ExperimentEvent(
                sequence=sequence,
                run_id=run.run_id,
                event_type=event_type,
                payload=payload or {},
            )
        )

    client: Any = None
    container: Any = None
    work_dir: Path | None = None
    limits: ResourceLimits = experiment.resource_limits
    cancelled = False

    try:
        client = docker.from_env()
        await asyncio.to_thread(client.ping)
        try:
            image = await asyncio.to_thread(client.images.get, profile.image)
        except Exception:
            return _blocked_run(
                bundle_id=bundle_id,
                failure_code=FailureCode.IMAGE_PULL_FAILED,
                message="reviewed runtime image is not present locally; automatic pulls are disabled",
            )

        work_dir = Path(tempfile.mkdtemp(prefix="reproforge_docker_"))
        source_dir = work_dir / "bundle"
        source_dir.mkdir()
        if fixture is not None:
            (source_dir / "fixture.py").write_text(
                fixture.code,
                encoding="utf-8",
                newline="\n",
            )
            code_hash = fixture.sha256
        else:
            for generated_file in bundle.files:  # type: ignore[union-attr]
                destination = source_dir / generated_file.path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(
                    generated_file.content,
                    encoding="utf-8",
                    newline="\n",
                )
            code_hash = bundle.manifest_hash  # type: ignore[union-attr]

        event(EventType.STATUS, {"status": "starting", "runtime_profile": profile.name})
        container = await asyncio.to_thread(
            client.containers.run,
            image=profile.image,
            command=["python", "-I", "-c", "import time; time.sleep(31536000)"],
            working_dir="/bundle",
            detach=True,
            remove=False,
            user=_CONTAINER_USER,
            environment={
                "REPROFORGE_RUN_ID": run.run_id,
                "REPROFORGE_OUTPUT_DIR": "/output",
                "PYTHONIOENCODING": "utf-8",
            },
            labels={
                "reproforge.component": "p3-experiment",
                "reproforge.run_id": run.run_id,
            },
            volumes={str(source_dir): {"bind": "/bundle", "mode": "ro"}},
            tmpfs={
                "/tmp": "rw,noexec,nosuid,nodev,size=64m,uid=65532,gid=65532,mode=0770",
                "/output": (
                    f"rw,noexec,nosuid,nodev,size={limits.disk_mb}m,uid=65532,gid=65532,mode=0770"
                ),
            },
            mem_limit=f"{limits.memory_mb}m",
            nano_cpus=int(limits.cpu * 1_000_000_000),
            pids_limit=limits.pids,
            network_mode="none",
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            read_only=True,
            init=True,
        )

        try:
            execution_completed = True
            exit_code, stdout, stderr, logs_truncated = await asyncio.wait_for(
                asyncio.to_thread(
                    _execute_bounded,
                    client.api,
                    container.id,
                    list(experiment.entrypoint),
                    limits.log_bytes,
                ),
                timeout=experiment.timeout_seconds,
            )
        except TimeoutError:
            execution_completed = False
            await asyncio.to_thread(container.kill)
            run.status = RunStatus.TIMEOUT
            run.failure_code = FailureCode.TIMEOUT
            event(EventType.STATUS, {"status": "timeout"})
            exit_code = 124
            stdout = ""
            stderr = ""
            logs_truncated = False
        except asyncio.CancelledError:
            execution_completed = False
            cancelled = True
            with suppress(Exception):
                await asyncio.to_thread(container.kill)
            run.status = RunStatus.CANCELLED
            run.failure_code = FailureCode.CANCELLED
            event(EventType.STATUS, {"status": "cancelled"})
            exit_code = 130
            stdout = ""
            stderr = ""
            logs_truncated = False

        run.exit_code = exit_code
        if run.status == RunStatus.RUNNING:
            if run.exit_code == 0:
                run.status = RunStatus.SUCCESS
                event(EventType.STATUS, {"status": "success"})
            elif run.exit_code == 137:
                run.status = RunStatus.FAILED
                run.failure_code = FailureCode.RESOURCE_EXHAUSTED
                event(EventType.STATUS, {"status": "resource_exhausted"})
            else:
                run.status = RunStatus.FAILED
                run.failure_code = FailureCode.NON_ZERO_EXIT
                event(EventType.STATUS, {"status": "failed"})

        run.stdout_tail = stdout[-4096:]
        run.stderr_tail = stderr[-4096:]
        run.log_truncated = logs_truncated
        if run.stdout_tail:
            event(EventType.LOG_STDOUT, {"tail": run.stdout_tail})
        if run.stderr_tail:
            event(EventType.LOG_STDERR, {"tail": run.stderr_tail})
        if run.log_truncated:
            event(EventType.TRUNCATION, {"kind": "log", "limit_bytes": limits.log_bytes})

        output_files = (
            await asyncio.to_thread(
                _collect_output_archive,
                client.api,
                container.id,
                limits.artifact_bytes + 1024 * 1024,
            )
            if execution_completed
            else {}
        )
        metrics_content = output_files.pop(_METRICS_FILE, b"")
        if metrics_content:
            for line_number, line in enumerate(
                metrics_content.decode("utf-8", errors="strict").splitlines(), start=1
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

        total_artifact_bytes = 0
        for relative_path, content in sorted(output_files.items()):
            if not _artifact_allowed(relative_path, experiment.artifact_allowlist):
                event(EventType.ERROR, {"error": "artifact not allowlisted", "path": relative_path})
                continue
            total_artifact_bytes += len(content)
            if total_artifact_bytes > limits.artifact_bytes:
                raise _ArtifactLimitError("artifact byte budget exceeded")
            record = ArtifactRecord(
                path=relative_path,
                media_type=mimetypes.guess_type(relative_path)[0] or "application/octet-stream",
                size_bytes=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                producer_step="experiment",
            )
            run.artifacts.append(record)
            event(EventType.ARTIFACT, record.model_dump(mode="json"))

        run.environment = EnvironmentSnapshot(
            python_version=experiment.environment_lock.get("python", ""),
            os="linux",
            packages={
                dependency.name: dependency.version or "" for dependency in experiment.dependencies
            },
            code_hash=code_hash,
            image_digest=getattr(image, "id", profile.image),
        )

    except _ArtifactLimitError as exc:
        event(EventType.ERROR, {"error": str(exc)})
        run.status = RunStatus.FAILED
        run.failure_code = FailureCode.ARTIFACT_REJECTED
    except UnicodeDecodeError as exc:
        event(EventType.ERROR, {"error": f"metrics file is not UTF-8: {exc}"})
        run.status = RunStatus.FAILED
        run.failure_code = FailureCode.METRIC_PARSE_ERROR
    except Exception as exc:
        event(EventType.ERROR, {"error": str(exc)})
        run.status = RunStatus.FAILED
        run.failure_code = FailureCode.DOCKER_UNAVAILABLE
    finally:
        if container is not None:
            with suppress(Exception):
                await asyncio.to_thread(container.remove, force=True)
        if client is not None:
            with suppress(Exception):
                await asyncio.to_thread(client.close)
        if work_dir is not None:
            with suppress(OSError):
                shutil.rmtree(work_dir)
        if events:
            event(EventType.STATUS, {"status": "cleaned_up"})

    run.events = events
    run.finished_at = datetime.now(UTC).isoformat()
    if cancelled:
        return run
    return run
