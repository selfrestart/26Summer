"""P3 reproduction schemas — code bundles, experiments, and runs.

Defines versioned Pydantic models for auditable code generation and
sandboxed experiment execution.  P3 only reports structural facts and
observed metrics; it does not judge whether a paper was reproduced.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC
from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

# ---------------------------------------------------------------------------
# Schema version constants
# ---------------------------------------------------------------------------

BUNDLE_SCHEMA_VERSION = "p3.bundle.v1"
EXPERIMENT_SCHEMA_VERSION = "p3.experiment.v1"
RUN_SCHEMA_VERSION = "p3.run.v1"

# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------

_FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("absolute", re.compile(r"^/")),
    ("drive-letter", re.compile(r"^[a-zA-Z]:")),
    ("unc", re.compile(r"^\\\\")),
    ("nul-byte", re.compile(r"\x00")),
    ("parent-traversal", re.compile(r"(?:^|/|\\)\.\.")),
]

_MANIFEST_PATH = "reproforge-manifest.json"
_SECRET_NAME_RE = re.compile(r"(?:key|token|secret|password|credential|auth)", re.IGNORECASE)


def _validate_relative_path(path: str, *, field_name: str = "path") -> str:
    """Reject absolute, UNC, drive-letter, NUL, and ``..`` paths.

    Returns the normalized POSIX version on success.
    """
    cleaned = path.replace("\\", "/")
    if not cleaned or cleaned.strip() != cleaned:
        raise ValueError(f"{field_name} must be a non-empty, non-blank relative path")
    for kind, pat in _FORBIDDEN_PATTERNS:
        if pat.search(cleaned):
            raise ValueError(f"{field_name} contains {kind} pattern: {path!r}")
    normalized = str(PurePosixPath(cleaned))
    if normalized == ".":
        raise ValueError(f"{field_name} must not be '.'")
    if normalized == "..":
        raise ValueError(f"{field_name} must not be '..'")
    return normalized


def validate_bundle_path(path: str) -> str:
    """Public entry-point for bundle path validation."""
    return _validate_relative_path(path, field_name="bundle path")


def _is_case_collision(paths: list[str]) -> bool:
    """Return True when paths would collide on a case-insensitive filesystem."""
    folded = [p.casefold() for p in paths]
    return len(set(folded)) != len(paths)


# ---------------------------------------------------------------------------
# Hash helpers
# ---------------------------------------------------------------------------


def _sha256(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def canonical_json(obj: Any) -> str:
    """Sort keys, no indentation, ASCII-encoded, for deterministic hashing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


# ---------------------------------------------------------------------------
# Bundle models
# ---------------------------------------------------------------------------


class GeneratedFile(BaseModel):
    """A single file inside a reproduction bundle."""

    path: str = ""
    content: str = ""
    language: str = ""
    purpose: str = Field(default="source", pattern=r"^(source|test|config|doc|data|script)$")
    evidence_ids: list[str] = Field(default_factory=list)
    content_hash: str = ""
    is_entrypoint: bool = False

    model_config = ConfigDict(extra="forbid")

    @field_validator("path")
    @classmethod
    def _check_path(cls, v: str) -> str:
        return _validate_relative_path(v)

    @field_validator("content")
    @classmethod
    def _normalise_content(cls, v: str) -> str:
        if "\x00" in v:
            raise ValueError("generated file content must not contain NUL")
        return v.replace("\r\n", "\n").replace("\r", "\n")

    @model_validator(mode="after")
    def _ensure_hash(self) -> GeneratedFile:
        expected = _sha256(self.content)
        if self.content_hash and self.content_hash != expected:
            raise ValueError(f"content_hash mismatch for {self.path!r}")
        self.content_hash = expected
        return self


class DependencySpec(BaseModel):
    """A declared dependency with optional locking and evidence."""

    name: str = ""
    version: str | None = None
    source: str = Field(default="pypi", pattern=r"^(pypi|conda|system|git|wheelhouse)$")
    locked: bool = False
    evidence_id: str = ""
    extras: list[str] = Field(default_factory=list)
    import_name: str = ""

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("dependency name must not be empty")
        return v.strip()

    @model_validator(mode="after")
    def _locked_dependency_has_version(self) -> DependencySpec:
        if self.locked and not self.version:
            raise ValueError("locked dependencies must include a version")
        return self


class DatasetReference(BaseModel):
    """A dataset that an experiment reads or produces."""

    name: str = ""
    source_url: str = ""
    license_info: str = ""
    checksum: str = ""
    split_info: str = ""
    expected_directory: str = ""
    redistributable: bool = False
    evidence_id: str = ""

    model_config = ConfigDict(extra="forbid")

    @field_validator("expected_directory")
    @classmethod
    def _check_dir(cls, v: str) -> str:
        if v:
            return _validate_relative_path(v, field_name="expected_directory")
        return v


# ---------------------------------------------------------------------------
# Experiment specs
# ---------------------------------------------------------------------------


class ResourceLimits(BaseModel):
    """Validated resource limits shared by local policy and Docker execution."""

    cpu: float = Field(default=1.0, gt=0, le=64)
    memory_mb: int = Field(default=512, ge=64, le=262144)
    pids: int = Field(default=100, ge=8, le=4096)
    disk_mb: int = Field(default=256, ge=16, le=10240)
    log_bytes: int = Field(default=65536, ge=1024, le=16 * 1024 * 1024)
    artifact_bytes: int = Field(default=16 * 1024 * 1024, ge=1024, le=1024 * 1024 * 1024)

    model_config = ConfigDict(extra="forbid", frozen=True)


class ExperimentSpec(BaseModel):
    """Immutable specification for a single experiment."""

    schema_version: str = EXPERIMENT_SCHEMA_VERSION
    experiment_name: str = ""
    entrypoint: list[str] = Field(default_factory=list)
    datasets: list[DatasetReference] = Field(default_factory=list)
    dependencies: list[DependencySpec] = Field(default_factory=list)
    environment_lock: dict[str, str] = Field(default_factory=dict)
    network_policy: str = Field(default="offline", pattern=r"^(offline|allowlist)$")
    network_allowlist: list[str] = Field(default_factory=list)
    resource_limits: ResourceLimits = Field(default_factory=ResourceLimits)
    timeout_seconds: int = Field(default=3600, gt=0)
    random_seed: int = 42
    runtime_profile: str = Field(default="python-cpu", pattern=r"^[a-z0-9][a-z0-9._-]*$")
    artifact_allowlist: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("schema_version")
    @classmethod
    def _check_schema_version(cls, v: str) -> str:
        if v != EXPERIMENT_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {EXPERIMENT_SCHEMA_VERSION}")
        return v

    @field_validator("entrypoint")
    @classmethod
    def _check_entrypoint(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("entrypoint must be a non-empty argv list")
        for arg in v:
            if not arg or "\x00" in arg:
                raise ValueError(f"entrypoint argv contains NUL: {arg!r}")
        return v

    @field_validator("artifact_allowlist")
    @classmethod
    def _check_artifact_allowlist(cls, v: list[str]) -> list[str]:
        return [_validate_relative_path(path, field_name="artifact_allowlist") for path in v]

    @field_validator("environment_lock")
    @classmethod
    def _check_environment_lock(cls, v: dict[str, str]) -> dict[str, str]:
        forbidden = [name for name in v if _SECRET_NAME_RE.search(name)]
        if forbidden:
            raise ValueError(f"environment_lock contains secret-like names: {forbidden}")
        return v

    @model_validator(mode="after")
    def _network_allowlist_only_when_policy_allowlist(self) -> ExperimentSpec:
        if self.network_policy == "offline" and self.network_allowlist:
            raise ValueError("network_allowlist must be empty when network_policy is 'offline'")
        return self


class ReproductionBundle(BaseModel):
    """A complete, versioned reproduction bundle generated from a MethodAnalysis."""

    schema_version: str = BUNDLE_SCHEMA_VERSION
    bundle_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    paper_id: str = ""
    method_analysis_hash: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    files: list[GeneratedFile] = Field(default_factory=list)
    experiments: list[ExperimentSpec] = Field(default_factory=list)
    source_evidence_ids: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    risk_warnings: list[str] = Field(default_factory=list)
    generation_trace: list[str] = Field(default_factory=list)
    manifest_hash: str = ""

    model_config = ConfigDict(extra="forbid")

    @field_validator("schema_version")
    @classmethod
    def _check_schema_version(cls, v: str) -> str:
        if v != BUNDLE_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {BUNDLE_SCHEMA_VERSION}")
        return v

    @field_validator("files")
    @classmethod
    def _check_paths_unique(cls, v: list[GeneratedFile]) -> list[GeneratedFile]:
        seen: set[str] = set()
        for f in v:
            if f.path in seen:
                raise ValueError(f"Duplicate file path in bundle: {f.path!r}")
            seen.add(f.path)
        if _is_case_collision([f.path for f in v]):
            raise ValueError("Case collision detected among bundle file paths")
        return v

    def manifest_document(self) -> dict[str, Any]:
        """Return the canonical on-disk manifest, excluding the manifest file itself."""
        source_files = [f for f in self.files if f.path != _MANIFEST_PATH]
        return {
            "schema_version": self.schema_version,
            "bundle_id": self.bundle_id,
            "paper_id": self.paper_id,
            "method_analysis_hash": self.method_analysis_hash,
            "files": [
                f.model_dump(mode="json") for f in sorted(source_files, key=lambda x: x.path)
            ],
            "experiments": [e.model_dump(mode="json") for e in self.experiments],
            "source_evidence_ids": sorted(set(self.source_evidence_ids)),
            "assumptions": self.assumptions,
            "unresolved": self.unresolved,
            "risk_warnings": self.risk_warnings,
            "generation_trace": self.generation_trace,
        }

    def compute_manifest_hash(self) -> str:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "bundle_id": self.bundle_id,
            "paper_id": self.paper_id,
            "method_analysis_hash": self.method_analysis_hash,
            "files": [f.model_dump(mode="json") for f in sorted(self.files, key=lambda x: x.path)],
            "experiments": [e.model_dump(mode="json") for e in self.experiments],
            "source_evidence_ids": sorted(set(self.source_evidence_ids)),
            "assumptions": self.assumptions,
            "unresolved": self.unresolved,
            "risk_warnings": self.risk_warnings,
            "generation_trace": self.generation_trace,
        }
        return _sha256(canonical_json(payload))

    @model_validator(mode="after")
    def _ensure_manifest_hash(self) -> ReproductionBundle:
        manifest_candidates = [f for f in self.files if f.path.casefold() == _MANIFEST_PATH]
        if len(manifest_candidates) > 1:
            raise ValueError("bundle contains multiple manifest files")
        if manifest_candidates and manifest_candidates[0].path != _MANIFEST_PATH:
            raise ValueError("manifest path has a case collision")

        if not manifest_candidates:
            manifest_file = GeneratedFile(
                path=_MANIFEST_PATH,
                content=canonical_json(self.manifest_document()) + "\n",
                language="json",
                purpose="config",
            )
            self.files.append(manifest_file)

        expected = self.compute_manifest_hash()
        if self.manifest_hash and self.manifest_hash != expected:
            raise ValueError("manifest hash mismatch")
        self.manifest_hash = expected

        manifest = next(f for f in self.files if f.path == _MANIFEST_PATH)
        expected_document = canonical_json(self.manifest_document()) + "\n"
        if manifest.content != expected_document:
            raise ValueError("manifest file does not match bundle metadata")
        return self


# ---------------------------------------------------------------------------
# Execution entities
# ---------------------------------------------------------------------------


class EventType(StrEnum):
    LOG_STDERR = "log_stderr"
    LOG_STDOUT = "log_stdout"
    METRIC = "metric"
    ARTIFACT = "artifact"
    STATUS = "status"
    TRUNCATION = "truncation"
    ERROR = "error"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class FailureCode(StrEnum):
    NON_ZERO_EXIT = "non_zero_exit"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    NETWORK_DENIED = "network_denied"
    IMAGE_PULL_FAILED = "image_pull_failed"
    BUILD_FAILED = "build_failed"
    DOCKER_UNAVAILABLE = "docker_unavailable"
    SECURITY_VIOLATION = "security_violation"
    ARTIFACT_REJECTED = "artifact_rejected"
    METRIC_PARSE_ERROR = "metric_parse_error"
    PATH_VALIDATION = "path_validation"
    CANCELLED = "cancelled"


class ExperimentEvent(BaseModel):
    """A timestamped event emitted during experiment execution."""

    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    sequence: int = 0
    run_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    event_type: EventType = EventType.STATUS
    payload: dict[str, Any] = Field(default_factory=dict)


class ObservedMetric(BaseModel):
    """A structured metric collected from ``/output/reproforge-metrics.jsonl``."""

    name: str = Field(min_length=1)
    value: float = 0.0
    unit: str = ""
    step: int = 0
    split: str = ""
    aggregation: str = ""
    seed: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactRecord(BaseModel):
    """An output artifact that was collected from the experiment sandbox."""

    path: str = ""
    media_type: str = ""
    size_bytes: int = Field(default=0, ge=0)
    sha256: str = Field(default="", pattern=r"^(?:[0-9a-f]{64})?$")
    producer_step: str = ""

    @field_validator("path")
    @classmethod
    def _check_path(cls, v: str) -> str:
        return _validate_relative_path(v)


class EnvironmentSnapshot(BaseModel):
    """Captured environment at the start of the experiment."""

    python_version: str = ""
    os: str = ""
    packages: dict[str, str] = Field(default_factory=dict)
    hardware: dict[str, str] = Field(default_factory=dict)
    code_hash: str = ""
    image_digest: str = ""


class ExperimentRun(BaseModel):
    """The complete record of a single experiment execution."""

    schema_version: str = RUN_SCHEMA_VERSION
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    bundle_id: str = ""
    experiment_index: int = 0
    backend: str = Field(default="dryrun")
    status: RunStatus = RunStatus.PENDING
    failure_code: FailureCode | None = None
    exit_code: int | None = None
    started_at: str = ""
    finished_at: str = ""
    environment: EnvironmentSnapshot = Field(default_factory=EnvironmentSnapshot)
    events: list[ExperimentEvent] = Field(default_factory=list)
    metrics: list[ObservedMetric] = Field(default_factory=list)
    artifacts: list[ArtifactRecord] = Field(default_factory=list)
    stderr_tail: str = ""
    stdout_tail: str = ""
    log_truncated: bool = False

    @field_validator("schema_version")
    @classmethod
    def _check_schema_version(cls, v: str) -> str:
        if v != RUN_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {RUN_SCHEMA_VERSION}")
        return v


# ---------------------------------------------------------------------------
# Registered fixture (for runner verification, not user-facing)
# ---------------------------------------------------------------------------


class FixtureSpec(BaseModel):
    """A registered inline fixture for runner verification."""

    fixture_id: str = ""
    description: str = ""
    code: str = ""
    sha256: str = ""
    expected_exit: int = 0
    timeout_seconds: int = 30

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="before")
    @classmethod
    def _populate_sha256(cls, value: Any) -> Any:
        if isinstance(value, dict) and not value.get("sha256"):
            data = dict(value)
            data["sha256"] = _sha256(str(data.get("code", "")))
            return data
        return value

    @model_validator(mode="after")
    def _ensure_sha256(self) -> FixtureSpec:
        if not self.fixture_id or not self.code:
            raise ValueError("fixture_id and code are required")
        if self.sha256 != _sha256(self.code):
            raise ValueError("fixture sha256 mismatch")
        return self
