"""Tests for P3 dry-run and local-subprocess backends."""

from __future__ import annotations

from repro_forge.reproduction.schemas import ExperimentSpec
from repro_forge.reproduction.schemas import GeneratedFile
from repro_forge.reproduction.schemas import ReproductionBundle
from repro_forge.reproduction.schemas import RunStatus


def _valid_bundle() -> ReproductionBundle:
    return ReproductionBundle(
        paper_id="test",
        files=[
            GeneratedFile(
                path="train.py",
                content="import os\nprint('hello')\n",
                purpose="source",
                is_entrypoint=True,
            ),
            GeneratedFile(
                path="tests/test_train.py",
                content="def test(): pass\n",
                purpose="test",
            ),
        ],
        experiments=[ExperimentSpec(entrypoint=["python", "train.py"])],
    )


class TestDryRunBackend:
    async def test_dryrun_succeeds_valid_bundle(self) -> None:
        from repro_forge.reproduction.experiment.dryrun import dryrun_execute

        bundle = _valid_bundle()
        run = await dryrun_execute(bundle, bundle.experiments[0])
        assert run.status == RunStatus.SUCCESS
        assert run.backend == "dryrun"

    async def test_dryrun_fails_invalid_bundle(self) -> None:
        from repro_forge.reproduction.experiment.dryrun import dryrun_execute

        bundle = ReproductionBundle(
            paper_id="test",
            files=[GeneratedFile(path="bad.py", content="if True print('x')\n")],
            experiments=[ExperimentSpec(entrypoint=["python", "bad.py"])],
        )
        run = await dryrun_execute(bundle, bundle.experiments[0])
        assert run.status == RunStatus.FAILED

    async def test_dryrun_generates_events(self) -> None:
        from repro_forge.reproduction.experiment.dryrun import dryrun_execute

        bundle = _valid_bundle()
        run = await dryrun_execute(bundle, bundle.experiments[0])
        assert len(run.events) > 0

    async def test_dryrun_cleans_up(self) -> None:
        from repro_forge.reproduction.experiment.dryrun import dryrun_execute

        bundle = _valid_bundle()
        run = await dryrun_execute(bundle, bundle.experiments[0])
        assert any("cleaned_up" in str(e.payload) for e in run.events)


class TestLocalSubprocessBackend:
    def test_success_fixture(self) -> None:
        from repro_forge.reproduction.fixtures import P3_CPU_SMOKE_SUCCESS

        fixture = P3_CPU_SMOKE_SUCCESS
        assert fixture.fixture_id == "p3-cpu-smoke"
        assert fixture.expected_exit == 0

    def test_fail_fixture(self) -> None:
        from repro_forge.reproduction.fixtures import P3_CPU_SMOKE_FAIL

        fixture = P3_CPU_SMOKE_FAIL
        assert fixture.expected_exit == 1

    def test_timeout_fixture(self) -> None:
        from repro_forge.reproduction.fixtures import P3_CPU_SMOKE_TIMEOUT

        fixture = P3_CPU_SMOKE_TIMEOUT
        assert fixture.timeout_seconds == 2

    def test_large_output_fixture(self) -> None:
        from repro_forge.reproduction.fixtures import P3_CPU_SMOKE_LARGE_OUTPUT

        fixture = P3_CPU_SMOKE_LARGE_OUTPUT
        assert fixture.expected_exit == 0

    def test_cleanup_fixture(self) -> None:
        from repro_forge.reproduction.fixtures import P3_CPU_SMOKE_CLEANUP

        fixture = P3_CPU_SMOKE_CLEANUP
        assert fixture.expected_exit == 0

    def test_fixture_registry(self) -> None:
        from repro_forge.reproduction.fixtures import get_fixture
        from repro_forge.reproduction.fixtures import list_fixtures

        fixture_ids = list_fixtures()
        assert "p3-cpu-smoke" in fixture_ids
        assert "p3-cpu-smoke-fail" in fixture_ids
        assert get_fixture("p3-cpu-smoke") is not None
        assert get_fixture("nonexistent") is None

    def test_fixture_hashes_computed(self) -> None:
        from repro_forge.reproduction.fixtures import P3_CPU_SMOKE_SUCCESS

        assert P3_CPU_SMOKE_SUCCESS.sha256 != ""

    async def test_fixture_success_run(self) -> None:
        from repro_forge.reproduction.experiment.local import subprocess_execute_fixture

        run = await subprocess_execute_fixture("p3-cpu-smoke", timeout_seconds=10)
        assert run.status == RunStatus.SUCCESS
        assert run.exit_code == 0

    async def test_fixture_nonzero_exit(self) -> None:
        from repro_forge.reproduction.experiment.local import subprocess_execute_fixture

        run = await subprocess_execute_fixture("p3-cpu-smoke-fail", timeout_seconds=10)
        assert run.status == RunStatus.FAILED
        assert run.exit_code == 1

    async def test_fixture_timeout(self) -> None:
        from repro_forge.reproduction.experiment.local import subprocess_execute_fixture

        run = await subprocess_execute_fixture("p3-cpu-smoke-timeout", timeout_seconds=2)
        assert run.status == RunStatus.TIMEOUT

    async def test_fixture_large_output_truncated(self) -> None:
        from repro_forge.reproduction.experiment.local import subprocess_execute_fixture

        run = await subprocess_execute_fixture("p3-cpu-smoke-large-output", timeout_seconds=10)
        assert run.log_truncated

    async def test_fixture_cleanup_removes_temp(self) -> None:
        from repro_forge.reproduction.experiment.local import subprocess_execute_fixture

        run = await subprocess_execute_fixture("p3-cpu-smoke-cleanup", timeout_seconds=10)
        assert run.status == RunStatus.SUCCESS

    async def test_local_refuses_unknown_fixture(self) -> None:
        from repro_forge.reproduction.experiment.experimentor import Experimentor

        e = Experimentor()
        run = await e.run_registered_fixture("nonexistent")
        assert run.backend == "local-subprocess"
        assert run.status == RunStatus.BLOCKED
        assert run.exit_code is None

    async def test_local_refuses_caller_supplied_fixture_object(self, tmp_path) -> None:
        from repro_forge.reproduction.experiment.experimentor import Experimentor
        from repro_forge.reproduction.schemas import FixtureSpec

        marker = tmp_path / "executed.txt"
        fixture = FixtureSpec(
            fixture_id="caller-controlled",
            description="must never execute on the host",
            code=f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n",
        )
        run = await Experimentor().run_registered_fixture(fixture)  # type: ignore[arg-type]
        assert run.status == RunStatus.BLOCKED
        assert not marker.exists()

    async def test_local_fixture_does_not_write_to_caller_cwd(self, tmp_path, monkeypatch) -> None:
        from repro_forge.reproduction.experiment.local import subprocess_execute_fixture

        monkeypatch.chdir(tmp_path)
        run = await subprocess_execute_fixture("p3-cpu-smoke", timeout_seconds=10)
        assert run.status == RunStatus.SUCCESS
        assert not (tmp_path / "reproforge-metrics.jsonl").exists()


class TestExperimentor:
    def test_experimentor_api(self) -> None:
        from repro_forge.reproduction.experiment.experimentor import Experimentor

        e = Experimentor()
        assert e is not None

    async def test_invalid_backend_blocked(self) -> None:
        from repro_forge.reproduction.experiment.experimentor import Experimentor

        e = Experimentor()
        run = await e.execute(ReproductionBundle(), backend="invalid")
        assert run.status == RunStatus.BLOCKED

    async def test_dryrun_through_experimentor(self) -> None:
        from repro_forge.reproduction.experiment.experimentor import Experimentor

        bundle = _valid_bundle()
        e = Experimentor()
        run = await e.execute(bundle, backend="dryrun")
        assert run.status == RunStatus.SUCCESS


class TestDockerBackend:
    def test_output_archive_rejects_symlink_member(self) -> None:
        import io
        import tarfile

        import pytest

        from repro_forge.reproduction.experiment.docker import _ArtifactLimitError
        from repro_forge.reproduction.experiment.docker import _parse_output_archive

        archive_buffer = io.BytesIO()
        with tarfile.open(fileobj=archive_buffer, mode="w") as archive:
            link = tarfile.TarInfo("output/link")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/passwd"
            archive.addfile(link)

        with pytest.raises(_ArtifactLimitError, match="unsafe archive member"):
            _parse_output_archive(archive_buffer.getvalue(), 1024)

    def test_output_archive_rejects_parent_traversal(self) -> None:
        import io
        import tarfile

        import pytest

        from repro_forge.reproduction.experiment.docker import _ArtifactLimitError
        from repro_forge.reproduction.experiment.docker import _parse_output_archive

        archive_buffer = io.BytesIO()
        with tarfile.open(fileobj=archive_buffer, mode="w") as archive:
            content = b"escape"
            escaped = tarfile.TarInfo("output/../escape.txt")
            escaped.size = len(content)
            archive.addfile(escaped, io.BytesIO(content))

        with pytest.raises(_ArtifactLimitError, match="unsafe archive member path"):
            _parse_output_archive(archive_buffer.getvalue(), 1024)

    def test_output_collector_failure_is_artifact_rejection(self) -> None:
        import pytest

        from repro_forge.reproduction.experiment.docker import _ArtifactLimitError
        from repro_forge.reproduction.experiment.docker import _collect_output_archive

        class FakeAPI:
            def exec_create(self, container_id, **kwargs):
                assert container_id == "container-1"
                assert kwargs["cmd"][:3] == ["python", "-I", "-c"]
                return {"Id": "collector-1"}

            def exec_start(self, exec_id, **kwargs):
                assert exec_id == "collector-1"
                assert kwargs["demux"] is True
                return iter([(None, b"unsafe output file")])

            def exec_inspect(self, exec_id):
                assert exec_id == "collector-1"
                return {"ExitCode": 1}

        with pytest.raises(_ArtifactLimitError, match="output collector failed"):
            _collect_output_archive(FakeAPI(), "container-1", 1024)

    async def test_docker_unavailable_returns_error(self) -> None:
        from repro_forge.reproduction.experiment.docker import docker_execute

        bundle = _valid_bundle()
        run = await docker_execute(bundle, bundle.experiments[0])
        assert run.backend == "docker"
        assert run.failure_code in (
            "docker_unavailable",
            "image_pull_failed",
            "network_denied",
        )

    async def test_docker_blocks_non_offline_network(self) -> None:
        from repro_forge.reproduction.experiment.docker import docker_execute

        spec = ExperimentSpec(
            entrypoint=["python", "t.py"],
            network_policy="allowlist",
            network_allowlist=["github.com"],
        )
        run = await docker_execute(ReproductionBundle(), spec)
        assert run.status == RunStatus.BLOCKED

    async def test_docker_blocks_allowlist_in_offline(self) -> None:
        from repro_forge.reproduction.experiment.docker import docker_execute

        run = await docker_execute(ReproductionBundle(), None)
        assert run.backend == "docker"

    def test_experiment_rejects_caller_supplied_base_image(self) -> None:
        import pytest

        with pytest.raises(ValueError):
            ExperimentSpec(
                entrypoint=["python", "train.py"],
                base_image="attacker.example/image:latest",  # type: ignore[call-arg]
            )

    async def test_docker_uses_pinned_profile_and_declared_argv(self, monkeypatch) -> None:
        import io
        import tarfile

        import docker

        from repro_forge.reproduction.experiment.docker import docker_execute

        image_ref = "registry.example/python@sha256:" + "a" * 64
        monkeypatch.setenv("REPROFORGE_P3_PYTHON_CPU_IMAGE", image_ref)

        archive_buffer = io.BytesIO()
        with tarfile.open(fileobj=archive_buffer, mode="w") as archive:
            info = tarfile.TarInfo("output")
            info.type = tarfile.DIRTYPE
            archive.addfile(info)
            metric = b'{"name":"cpu_smoke","value":1.0}\n'
            metric_info = tarfile.TarInfo("output/reproforge-metrics.jsonl")
            metric_info.size = len(metric)
            archive.addfile(metric_info, io.BytesIO(metric))
        archive_bytes = archive_buffer.getvalue()

        class FakeImage:
            id = "sha256:" + "b" * 64

        class FakeContainer:
            id = "container-1"
            removed = False

            def remove(self, *, force):
                assert force
                self.removed = True

            def kill(self):
                return None

        class FakeImages:
            def get(self, requested):
                assert requested == image_ref
                return FakeImage()

        class FakeContainers:
            def __init__(self) -> None:
                self.kwargs = None
                self.container = FakeContainer()

            def run(self, **kwargs):
                self.kwargs = kwargs
                return self.container

        class FakeAPI:
            def __init__(self, container) -> None:
                self.container = container
                self.exec_calls = []

            def exec_create(self, container_id, **kwargs):
                assert container_id == "container-1"
                self.exec_calls.append(kwargs)
                return {"Id": f"exec-{len(self.exec_calls)}"}

            def exec_start(self, exec_id, **kwargs):
                assert not self.container.removed
                assert kwargs["demux"] is True
                if exec_id == "exec-1":
                    return iter([(b"training output\n", None)])
                assert exec_id == "exec-2"
                return iter([(archive_bytes, None)])

            def exec_inspect(self, exec_id):
                assert exec_id in ("exec-1", "exec-2")
                return {"ExitCode": 0}

        class FakeClient:
            def __init__(self) -> None:
                self.images = FakeImages()
                self.containers = FakeContainers()
                self.api = FakeAPI(self.containers.container)
                self.closed = False

            def ping(self):
                return True

            def close(self):
                self.closed = True

        client = FakeClient()
        monkeypatch.setattr(docker, "from_env", lambda: client)
        bundle = _valid_bundle()

        run = await docker_execute(bundle, bundle.experiments[0])

        assert run.status == RunStatus.SUCCESS
        assert client.containers.kwargs["command"][:3] == ["python", "-I", "-c"]
        assert client.api.exec_calls[0]["cmd"] == ["python", "train.py"]
        assert client.api.exec_calls[1]["cmd"][:3] == ["python", "-I", "-c"]
        assert client.containers.kwargs["working_dir"] == "/bundle"
        assert client.containers.kwargs["network_mode"] == "none"
        assert client.containers.kwargs["read_only"] is True
        assert "/output" in client.containers.kwargs["tmpfs"]
        assert [metric.name for metric in run.metrics] == ["cpu_smoke"]
        assert run.stdout_tail == "training output\n"
        assert client.containers.container.removed
        assert client.closed
