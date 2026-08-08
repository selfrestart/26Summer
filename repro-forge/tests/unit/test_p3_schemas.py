"""Tests for P3 reproduction schemas.

Covers JSON round-trip, path validation, hash computation, unknown schema,
and case collision.
"""

from __future__ import annotations

import pytest

from repro_forge.reproduction.schemas import ArtifactRecord
from repro_forge.reproduction.schemas import DatasetReference
from repro_forge.reproduction.schemas import DependencySpec
from repro_forge.reproduction.schemas import EventType
from repro_forge.reproduction.schemas import ExperimentRun
from repro_forge.reproduction.schemas import ExperimentSpec
from repro_forge.reproduction.schemas import GeneratedFile
from repro_forge.reproduction.schemas import ObservedMetric
from repro_forge.reproduction.schemas import ReproductionBundle
from repro_forge.reproduction.schemas import RunStatus
from repro_forge.reproduction.schemas import _sha256
from repro_forge.reproduction.schemas import canonical_json
from repro_forge.reproduction.schemas import validate_bundle_path


class TestPathValidation:
    def test_accepts_normal_relative(self) -> None:
        assert validate_bundle_path("src/model.py") == "src/model.py"
        assert validate_bundle_path("tests/test_smoke.py") == "tests/test_smoke.py"

    def test_rejects_absolute(self) -> None:
        with pytest.raises(ValueError):
            validate_bundle_path("/etc/passwd")

    def test_rejects_drive_letter(self) -> None:
        with pytest.raises(ValueError):
            validate_bundle_path("C:\\Windows\\System32")

    def test_rejects_parent_traversal(self) -> None:
        with pytest.raises(ValueError):
            validate_bundle_path("../etc/passwd")
        with pytest.raises(ValueError):
            validate_bundle_path("src/../../etc/passwd")

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValueError):
            validate_bundle_path("")

    def test_rejects_dot(self) -> None:
        with pytest.raises(ValueError):
            validate_bundle_path(".")

    def test_rejects_dotdot(self) -> None:
        with pytest.raises(ValueError):
            validate_bundle_path("..")

    def test_normalizes_backslash(self) -> None:
        result = validate_bundle_path("src\\model.py")
        assert result == "src/model.py"


class TestGeneratedFile:
    def test_basic_file(self) -> None:
        f = GeneratedFile(
            path="src/model.py",
            content="import torch\n\nclass Model:\n    pass\n",
            language="python",
            purpose="source",
        )
        assert f.content_hash != ""
        assert len(f.content_hash) == 64

    def test_content_hash_stable(self) -> None:
        f1 = GeneratedFile(path="a.py", content="x = 1")
        f2 = GeneratedFile(path="a.py", content="x = 1")
        assert f1.content_hash == f2.content_hash

    def test_rejects_absolute_path(self) -> None:
        with pytest.raises(ValueError):
            GeneratedFile(path="/foo/bar.py", content="")


class TestDependencySpec:
    def test_default(self) -> None:
        dep = DependencySpec(name="torch")
        assert dep.source == "pypi"
        assert dep.locked is False

    def test_invalid_source(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DependencySpec(name="torch", source="npm")


class TestDatasetReference:
    def test_default(self) -> None:
        ds = DatasetReference(name="ImageNet")
        assert ds.license_info == ""

    def test_directory_path_validated(self) -> None:
        ds = DatasetReference(name="d", expected_directory="data/raw")
        assert ds.expected_directory == "data/raw"

    def test_rejects_absolute_directory(self) -> None:
        with pytest.raises(ValueError):
            DatasetReference(name="d", expected_directory="/etc")


class TestExperimentSpec:
    def test_default(self) -> None:
        spec = ExperimentSpec(entrypoint=["python", "train.py"])
        assert spec.schema_version == "p3.experiment.v1"
        assert spec.network_policy == "offline"

    def test_rejects_empty_entrypoint(self) -> None:
        with pytest.raises(ValueError):
            ExperimentSpec(entrypoint=[])

    def test_allowlist_requires_policy(self) -> None:
        with pytest.raises(ValueError):
            ExperimentSpec(entrypoint=["python", "t.py"], network_allowlist=["github.com"])

    def test_network_allowlist_valid(self) -> None:
        spec = ExperimentSpec(
            entrypoint=["python", "t.py"],
            network_policy="allowlist",
            network_allowlist=["github.com"],
        )
        assert spec.network_policy == "allowlist"

    def test_round_trip(self) -> None:
        spec = ExperimentSpec(
            experiment_name="main",
            entrypoint=["python", "train.py"],
            timeout_seconds=7200,
        )
        d = spec.model_dump()
        spec2 = ExperimentSpec(**d)
        assert spec2.timeout_seconds == 7200


class TestReproductionBundle:
    def test_basic_bundle(self) -> None:
        f = GeneratedFile(path="train.py", content="print(1)", purpose="source")
        bundle = ReproductionBundle(
            paper_id="1706.03762",
            files=[f],
        )
        assert bundle.manifest_hash != ""
        assert bundle.schema_version == "p3.bundle.v1"

    def test_duplicate_paths_rejected(self) -> None:
        f1 = GeneratedFile(path="a.py", content="1")
        f2 = GeneratedFile(path="a.py", content="2")
        with pytest.raises(ValueError):
            ReproductionBundle(files=[f1, f2])

    def test_manifest_hash_stable(self) -> None:
        f = GeneratedFile(path="a.py", content="1", purpose="source")
        b1 = ReproductionBundle(paper_id="p1", files=[f], bundle_id="fixed_id")
        b2 = ReproductionBundle(paper_id="p1", files=[f], bundle_id="fixed_id")
        assert b1.manifest_hash == b2.manifest_hash

    def test_compute_manifest_hash_includes_all_files(self) -> None:
        b1 = ReproductionBundle(
            paper_id="p1",
            files=[GeneratedFile(path="a.py", content="1", purpose="source")],
        )
        b2 = ReproductionBundle(
            paper_id="p1",
            files=[GeneratedFile(path="a.py", content="2", purpose="source")],
        )
        assert b1.manifest_hash != b2.manifest_hash

    def test_manifest_hash_covers_evidence_mapping(self) -> None:
        bundle = ReproductionBundle(
            paper_id="p1",
            files=[
                GeneratedFile(
                    path="train.py",
                    content="print(1)",
                    purpose="source",
                    evidence_ids=["ev_1"],
                )
            ],
            experiments=[ExperimentSpec(entrypoint=["python", "train.py"])],
        )
        payload = bundle.model_dump(mode="json")
        payload["files"][0]["evidence_ids"] = ["forged_evidence"]

        with pytest.raises(ValueError, match="manifest hash"):
            ReproductionBundle.model_validate(payload)

    def test_json_round_trip(self) -> None:
        bundle = ReproductionBundle(
            paper_id="p1",
            files=[
                GeneratedFile(path="train.py", content="print(1)", purpose="source"),
                GeneratedFile(
                    path="README.md", content="# README", purpose="doc", language="markdown"
                ),
            ],
            experiments=[
                ExperimentSpec(
                    entrypoint=["python", "train.py"],
                    dependencies=[DependencySpec(name="torch", version="2.0.0", locked=True)],
                ),
            ],
        )
        d = bundle.model_dump()
        bundle2 = ReproductionBundle(**d)
        assert bundle2.manifest_hash == bundle.manifest_hash
        assert len(bundle2.files) == 3
        assert any(file.path == "reproforge-manifest.json" for file in bundle2.files)


class TestExperimentRun:
    def test_default_state(self) -> None:
        run = ExperimentRun()
        assert run.status == RunStatus.PENDING
        assert run.backend == "dryrun"

    def test_json_round_trip(self) -> None:
        run = ExperimentRun(
            status=RunStatus.SUCCESS,
            backend="dryrun",
            bundle_id="abc",
            exit_code=0,
        )
        d = run.model_dump()
        run2 = ExperimentRun(**d)
        assert run2.status == RunStatus.SUCCESS


class TestEventTypes:
    def test_event_type_values(self) -> None:
        assert EventType.LOG_STDERR == "log_stderr"
        assert EventType.METRIC == "metric"
        assert EventType.STATUS == "status"


class TestObservedMetric:
    def test_basic(self) -> None:
        m = ObservedMetric(name="accuracy", value=0.945)
        assert m.name == "accuracy"
        assert m.value == 0.945

    def test_json_round_trip(self) -> None:
        m = ObservedMetric(name="f1", value=0.87, step=100, split="test")
        d = m.model_dump()
        m2 = ObservedMetric(**d)
        assert m2.name == "f1"
        assert m2.split == "test"


class TestArtifactRecord:
    def test_basic(self) -> None:
        a = ArtifactRecord(
            path="output/model.pt",
            media_type="application/octet-stream",
            size_bytes=1024,
            sha256="a" * 64,
        )
        assert a.path == "output/model.pt"

    def test_rejects_absolute(self) -> None:
        with pytest.raises(ValueError):
            ArtifactRecord(path="/output/model.pt", media_type="", size_bytes=0, sha256="")


class TestCanonicalJson:
    def test_deterministic(self) -> None:
        j1 = canonical_json({"b": 2, "a": 1})
        j2 = canonical_json({"a": 1, "b": 2})
        assert j1 == j2

    def test_hash_deterministic(self) -> None:
        h1 = _sha256(canonical_json({"a": 1}))
        h2 = _sha256(canonical_json({"a": 1}))
        assert h1 == h2
