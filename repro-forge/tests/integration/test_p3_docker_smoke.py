"""Real P3 Docker security smoke, enabled only with a reviewed image digest."""

from __future__ import annotations

import os

import pytest

from repro_forge.reproduction.pipeline import ReproductionPipeline
from repro_forge.reproduction.schemas import ExperimentSpec
from repro_forge.reproduction.schemas import FailureCode
from repro_forge.reproduction.schemas import GeneratedFile
from repro_forge.reproduction.schemas import ReproductionBundle
from repro_forge.reproduction.schemas import ResourceLimits
from repro_forge.reproduction.schemas import RunStatus

pytestmark = pytest.mark.docker


def _assert_container_cleaned_up(run_id: str) -> None:
    import docker

    client = docker.from_env()
    try:
        containers = client.containers.list(
            all=True,
            filters={"label": f"reproforge.run_id={run_id}"},
        )
    finally:
        client.close()
    assert containers == []


async def test_registered_cpu_fixture_in_offline_docker() -> None:
    if not os.getenv("REPROFORGE_P3_PYTHON_CPU_IMAGE"):
        pytest.skip("REPROFORGE_P3_PYTHON_CPU_IMAGE is not configured")

    run = await ReproductionPipeline().run_registered_fixture(
        "p3-cpu-smoke",
        backend="docker",
    )

    assert run.status == RunStatus.SUCCESS, run.model_dump(mode="json")
    assert run.environment.image_digest.startswith("sha256:")
    assert [metric.name for metric in run.metrics] == ["cpu_smoke"]
    _assert_container_cleaned_up(run.run_id)


@pytest.mark.parametrize(
    ("fixture_id", "expected_status", "expected_failure", "expected_artifact"),
    [
        ("p3-cpu-smoke-fail", RunStatus.FAILED, FailureCode.NON_ZERO_EXIT, None),
        ("p3-cpu-smoke-timeout", RunStatus.TIMEOUT, FailureCode.TIMEOUT, None),
        ("p3-cpu-smoke-cleanup", RunStatus.SUCCESS, None, "cleanup-smoke.txt"),
    ],
)
async def test_real_docker_terminal_paths_cleanup(
    fixture_id,
    expected_status,
    expected_failure,
    expected_artifact,
) -> None:
    if not os.getenv("REPROFORGE_P3_PYTHON_CPU_IMAGE"):
        pytest.skip("REPROFORGE_P3_PYTHON_CPU_IMAGE is not configured")

    run = await ReproductionPipeline().run_registered_fixture(fixture_id, backend="docker")

    assert run.status == expected_status, run.model_dump(mode="json")
    assert run.failure_code == expected_failure
    if expected_artifact is not None:
        assert [artifact.path for artifact in run.artifacts] == [expected_artifact]
    _assert_container_cleaned_up(run.run_id)


async def test_real_docker_security_controls_are_effective(monkeypatch) -> None:
    if not os.getenv("REPROFORGE_P3_PYTHON_CPU_IMAGE"):
        pytest.skip("REPROFORGE_P3_PYTHON_CPU_IMAGE is not configured")

    monkeypatch.setenv("OPENAI_API_KEY", "must-not-enter-container")
    probe = r"""import json
import os
from pathlib import Path


def cannot_write(path: str) -> bool:
    try:
        Path(path).write_text("unsafe", encoding="utf-8")
    except OSError:
        return True
    return False


status = Path("/proc/self/status").read_text(encoding="utf-8")
status_fields = dict(
    line.split(":", 1) for line in status.splitlines() if ":" in line
)
memory_max = int(Path("/sys/fs/cgroup/memory.max").read_text().strip())
pids_max = int(Path("/sys/fs/cgroup/pids.max").read_text().strip())
cpu_quota, cpu_period = (
    int(value) for value in Path("/sys/fs/cgroup/cpu.max").read_text().split()
)
output_mount = next(
    line for line in Path("/proc/mounts").read_text().splitlines() if " /output " in line
)
output_fs = os.statvfs("/output")
output_bytes = output_fs.f_blocks * output_fs.f_frsize

checks = {
    "non_root": os.getuid() == 65532 and os.getgid() == 65532,
    "network_none": sorted(os.listdir("/sys/class/net")) == ["lo"],
    "no_new_privileges": status_fields["NoNewPrivs"].strip() == "1",
    "capabilities_dropped": int(status_fields["CapEff"].strip(), 16) == 0,
    "memory_limit": memory_max <= 128 * 1024 * 1024,
    "pid_limit": pids_max <= 32,
    "cpu_limit": cpu_quota / cpu_period <= 0.5,
    "output_tmpfs": output_mount.startswith("tmpfs /output tmpfs "),
    "output_size_limit": 0 < output_bytes <= 32 * 1024 * 1024,
    "bundle_read_only": cannot_write("/bundle/write-probe.txt"),
    "rootfs_read_only": cannot_write("/var/tmp/reproforge-rootfs-probe.txt"),
    "host_secrets_removed": "OPENAI_API_KEY" not in os.environ,
}

metrics_path = Path(os.environ["REPROFORGE_OUTPUT_DIR"]) / "reproforge-metrics.jsonl"
metrics_path.write_text(
    "".join(
        json.dumps({"name": f"security_{name}", "value": float(value)}) + "\n"
        for name, value in checks.items()
    ),
    encoding="utf-8",
)
print(json.dumps(checks, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 3)
"""
    bundle = ReproductionBundle(
        paper_id="p3-docker-security-smoke",
        files=[
            GeneratedFile(
                path="security_probe.py",
                content=probe,
                language="python",
                purpose="source",
                is_entrypoint=True,
            ),
            GeneratedFile(
                path="tests/test_smoke.py",
                content="def test_security_probe_bundle():\n    assert True\n",
                language="python",
                purpose="test",
            ),
        ],
        experiments=[
            ExperimentSpec(
                experiment_name="docker-security-controls",
                entrypoint=["python", "security_probe.py"],
                environment_lock={"python": "3.13.14"},
                resource_limits=ResourceLimits(
                    cpu=0.5,
                    memory_mb=128,
                    pids=32,
                    disk_mb=32,
                    log_bytes=8192,
                    artifact_bytes=1024 * 1024,
                ),
                timeout_seconds=20,
            )
        ],
    )

    run = await ReproductionPipeline().execute(bundle, backend="docker")

    assert run.status == RunStatus.SUCCESS, run.model_dump(mode="json")
    assert run.environment.image_digest.startswith("sha256:")
    assert run.environment.code_hash == bundle.manifest_hash
    assert run.metrics
    assert all(metric.value == 1.0 for metric in run.metrics), run.stdout_tail
    _assert_container_cleaned_up(run.run_id)
