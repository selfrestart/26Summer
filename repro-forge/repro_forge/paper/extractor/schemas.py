"""Methodology extraction schemas for P2.

Defines evidence-grounded data models for algorithm extraction,
architecture analysis, training recipe capture, and reproducibility
gap identification from academic papers.

Each key field carries an ``EvidenceStatus`` and ``EvidenceRef``
so that every claim can be traced back to the source paper.
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator

# ---------------------------------------------------------------------------
# Evidence primitives
# ---------------------------------------------------------------------------


class EvidenceStatus(StrEnum):
    """Status of a piece of evidence relative to the source paper."""

    VERIFIED = "verified"
    INFERRED = "inferred"
    CONFLICTING = "conflicting"
    NOT_REPORTED = "not_reported"
    UNVERIFIED = "unverified"


class EquationParseStatus(StrEnum):
    """How well a formula was captured from the paper."""

    CAPTURED = "captured"
    PARTIAL = "partial"
    NOT_AVAILABLE = "not_available"


class EvidenceRef(BaseModel):
    """A reference linking a claim back to a specific location in the paper."""

    evidence_id: str = ""
    paper_id: str = ""
    source_hash: str = ""
    section_id: str = ""
    section_title: str = ""
    page_start: int | None = None
    page_end: int | None = None
    quote: str = ""
    quote_hash: str = ""
    chunk_index: int | None = None
    status: EvidenceStatus = EvidenceStatus.UNVERIFIED
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class EvidenceValue(BaseModel):
    """A configuration value paired with its evidence status and source."""

    value: Any = None
    raw_text: str = ""
    status: EvidenceStatus = EvidenceStatus.UNVERIFIED
    evidence: EvidenceRef = Field(default_factory=EvidenceRef)
    notes: str = ""

    @classmethod
    def not_reported(cls, key: str) -> EvidenceValue:
        return cls(
            value=None,
            raw_text="",
            status=EvidenceStatus.NOT_REPORTED,
            notes=f"{key} not reported in paper",
        )

    @classmethod
    def reported(cls, value: Any, evidence: EvidenceRef, raw_text: str = "") -> EvidenceValue:
        return cls(
            value=value, raw_text=raw_text, status=EvidenceStatus.VERIFIED, evidence=evidence
        )


# ---------------------------------------------------------------------------
# Algorithm extraction
# ---------------------------------------------------------------------------


class EquationEvidence(BaseModel):
    """Structured capture of a mathematical expression from the paper."""

    equation_id: str = ""
    label: str | None = None
    raw_text: str = ""
    normalized_text: str = ""
    parse_status: EquationParseStatus = EquationParseStatus.NOT_AVAILABLE
    symbol_hints: dict[str, str] = Field(default_factory=dict)
    evidence: EvidenceRef = Field(default_factory=EvidenceRef)


class AlgorithmStep(BaseModel):
    """A single step within an algorithm or method."""

    order: int = 1
    description: str = ""
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    equations: list[str] = Field(default_factory=list)
    evidence: EvidenceRef = Field(default_factory=EvidenceRef)


class AlgorithmSpec(BaseModel):
    """A complete algorithm or method extracted from the paper."""

    name: str = ""
    purpose: str = ""
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    steps: list[AlgorithmStep] = Field(default_factory=list)
    pseudocode: str = ""
    assumptions: list[str] = Field(default_factory=list)
    complexity_notes: EvidenceValue = Field(
        default_factory=lambda: EvidenceValue.not_reported("complexity")
    )
    evidence: EvidenceRef = Field(default_factory=EvidenceRef)


# ---------------------------------------------------------------------------
# Architecture extraction
# ---------------------------------------------------------------------------


class ArchitectureComponent(BaseModel):
    """A component of the model architecture."""

    name: str = ""
    component_type: str = ""
    description: str = ""
    input_shape: str = ""
    output_shape: str = ""
    parameters: dict[str, EvidenceValue] = Field(default_factory=dict)
    evidence: EvidenceRef = Field(default_factory=EvidenceRef)


# ---------------------------------------------------------------------------
# Training recipe
# ---------------------------------------------------------------------------


class TrainingRecipe(BaseModel):
    """Captured training configuration with per-field evidence."""

    datasets: list[EvidenceValue] = Field(default_factory=list)
    preprocessing: list[EvidenceValue] = Field(default_factory=list)
    objective: EvidenceValue = Field(
        default_factory=lambda: EvidenceValue.not_reported("objective")
    )
    optimizer: EvidenceValue = Field(
        default_factory=lambda: EvidenceValue.not_reported("optimizer")
    )
    learning_rate: EvidenceValue = Field(
        default_factory=lambda: EvidenceValue.not_reported("learning_rate")
    )
    learning_rate_schedule: EvidenceValue = Field(
        default_factory=lambda: EvidenceValue.not_reported("lr_schedule")
    )
    batch_size: EvidenceValue = Field(
        default_factory=lambda: EvidenceValue.not_reported("batch_size")
    )
    epochs: EvidenceValue = Field(default_factory=lambda: EvidenceValue.not_reported("epochs"))
    weight_decay: EvidenceValue = Field(
        default_factory=lambda: EvidenceValue.not_reported("weight_decay")
    )
    optimizer_kwargs: dict[str, EvidenceValue] = Field(default_factory=dict)
    initialization: EvidenceValue = Field(
        default_factory=lambda: EvidenceValue.not_reported("initialization")
    )
    regularization: EvidenceValue = Field(
        default_factory=lambda: EvidenceValue.not_reported("regularization")
    )
    hardware: EvidenceValue = Field(default_factory=lambda: EvidenceValue.not_reported("hardware"))
    precision: EvidenceValue = Field(
        default_factory=lambda: EvidenceValue.not_reported("precision")
    )
    random_seed: EvidenceValue = Field(default_factory=lambda: EvidenceValue.not_reported("seed"))
    reported_but_ambiguous: dict[str, EvidenceValue] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Evaluation protocol
# ---------------------------------------------------------------------------


class ReportedClaimDraft(BaseModel):
    """A claimed metric or result extracted from the paper (draft for P4)."""

    claim_id: str = ""
    dataset: str = ""
    split: str = ""
    metric_name: str = ""
    reported_value: str = ""
    raw_text: str = ""
    unit: str = ""
    scale: str = ""
    direction: str = ""
    aggregation: str = ""
    evaluation_setting: str = ""
    baseline: str = ""
    uncertainty: str = ""
    status: EvidenceStatus = EvidenceStatus.UNVERIFIED
    evidence: EvidenceRef = Field(default_factory=EvidenceRef)
    evidence_overrides: dict[str, EvidenceRef] = Field(default_factory=dict)
    notes: str = ""


class EvaluationProtocol(BaseModel):
    """How the paper evaluates its methods."""

    datasets: list[EvidenceValue] = Field(default_factory=list)
    splits: list[EvidenceValue] = Field(default_factory=list)
    metrics: list[EvidenceValue] = Field(default_factory=list)
    baselines: list[EvidenceValue] = Field(default_factory=list)
    evaluation_procedure: str = ""
    reported_claims: list[ReportedClaimDraft] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Reproducibility gaps
# ---------------------------------------------------------------------------


class ReproducibilityGap(BaseModel):
    """A specific barrier to reproducing the paper's results."""

    category: str = ""
    description: str = ""
    impact: str = ""
    related_sections: list[str] = Field(default_factory=list)
    suggested_resolution: str = ""


# ---------------------------------------------------------------------------
# Top-level output
# ---------------------------------------------------------------------------


class MethodAnalysis(BaseModel):
    """The complete methodology analysis — P2's primary deliverable.

    This is the stable public interface that P3 (CodeForger) and P5
    (Knowledge Graph) will consume.
    """

    schema_version: str = "p2.v1"
    paper_id: str = ""
    title: str = ""
    problem_statement: str = ""

    algorithms: list[AlgorithmSpec] = Field(default_factory=list)
    architecture: list[ArchitectureComponent] = Field(default_factory=list)
    training_recipe: TrainingRecipe = Field(default_factory=TrainingRecipe)
    evaluation_protocol: EvaluationProtocol = Field(default_factory=EvaluationProtocol)

    equations: list[EquationEvidence] = Field(default_factory=list)
    assumptions: list[EvidenceValue] = Field(default_factory=list)
    reproducibility_gaps: list[ReproducibilityGap] = Field(default_factory=list)

    evidence_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    total_tokens_used: int = 0
    extraction_trace: list[str] = Field(default_factory=list)
    extracted_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_reported_claims(cls, value: Any) -> Any:
        """Canonicalize the former top-level claim list under evaluation_protocol."""
        if not isinstance(value, dict) or "reported_claims" not in value:
            return value

        data = dict(value)
        legacy_claims = data.pop("reported_claims") or []
        protocol_value = data.get("evaluation_protocol")
        if isinstance(protocol_value, EvaluationProtocol):
            protocol = protocol_value.model_dump()
        elif isinstance(protocol_value, dict):
            protocol = dict(protocol_value)
        else:
            protocol = {}
        if not isinstance(legacy_claims, list):
            protocol["reported_claims"] = legacy_claims
            data["evaluation_protocol"] = protocol
            return data
        nested_claims = list(protocol.get("reported_claims") or [])
        for claim in legacy_claims:
            if claim not in nested_claims:
                nested_claims.append(claim)
        protocol["reported_claims"] = nested_claims
        data["evaluation_protocol"] = protocol
        return data

    @property
    def reported_claims(self) -> list[ReportedClaimDraft]:
        """Compatibility view of claims stored in ``evaluation_protocol``."""
        return self.evaluation_protocol.reported_claims

    @property
    def verified_claim_count(self) -> int:
        return sum(
            1
            for claim in self.evaluation_protocol.reported_claims
            if claim.status == EvidenceStatus.VERIFIED
        )

    @property
    def gap_count(self) -> int:
        return len(self.reproducibility_gaps)

    @property
    def algorithm_count(self) -> int:
        return len(self.algorithms)

    @staticmethod
    def _evidence_key(ref: EvidenceRef) -> tuple[str, object]:
        """Return a stable key for de-duplicating the same evidence claim.

        ``evidence_overrides`` and the main evidence field can legitimately
        point to the same reference after JSON round-tripping, so object
        identity is not sufficient.  Empty IDs remain object-scoped to avoid
        collapsing all default placeholder references into one.
        """
        if ref.evidence_id:
            return ("id", ref.evidence_id)
        return ("object", id(ref))

    @staticmethod
    def _is_countable_evidence(ref: EvidenceRef) -> bool:
        """Ignore untouched placeholder refs created for not-reported fields."""
        return bool(
            ref.quote
            or ref.evidence_id
            or ref.paper_id
            or ref.source_hash
            or ref.section_id
            or ref.section_title
        )

    def _count_evidence_refs_with_quote(
        self, obj: Any, seen: set[tuple[str, object]] | None = None
    ) -> int:
        """Count unique verified references that contain a source quote."""
        if seen is None:
            seen = set()
        if isinstance(obj, EvidenceRef):
            key = self._evidence_key(obj)
            if key in seen:
                return 0
            seen.add(key)
            if not self._is_countable_evidence(obj):
                return 0
            if not obj.quote:
                return 0
            if obj.status == EvidenceStatus.VERIFIED:
                return 1
            # Preserve the historical standalone-schema behavior for refs
            # that have only an ID and quote (before a PaperEvidenceView can
            # verify them). Once provenance is present, non-verified refs are
            # deliberately excluded from coverage.
            legacy_unverified = (
                obj.status == EvidenceStatus.UNVERIFIED
                and not obj.paper_id
                and not obj.source_hash
                and not obj.section_id
                and not obj.section_title
            )
            return 1 if legacy_unverified else 0
        if isinstance(obj, BaseModel):
            total = 0
            for field_name in type(obj).model_fields:
                total += self._count_evidence_refs_with_quote(getattr(obj, field_name, None), seen)
            return total
        if isinstance(obj, list):
            return sum(self._count_evidence_refs_with_quote(item, seen) for item in obj)
        if isinstance(obj, dict):
            return sum(self._count_evidence_refs_with_quote(v, seen) for v in obj.values())
        return 0

    def _count_evidence_refs(self, obj: Any, seen: set[tuple[str, object]] | None = None) -> int:
        """Recursively count unique evidence references in the analysis."""
        if seen is None:
            seen = set()
        if isinstance(obj, EvidenceRef):
            key = self._evidence_key(obj)
            if key in seen:
                return 0
            seen.add(key)
            if not self._is_countable_evidence(obj):
                return 0
            return 1
        if isinstance(obj, BaseModel):
            return sum(
                self._count_evidence_refs(getattr(obj, field_name, None), seen)
                for field_name in type(obj).model_fields
            )
        if isinstance(obj, list):
            return sum(self._count_evidence_refs(item, seen) for item in obj)
        if isinstance(obj, dict):
            return sum(self._count_evidence_refs(value, seen) for value in obj.values())
        return 0

    def calculate_evidence_coverage(self) -> float:
        """Calculate quote coverage deterministically from the model graph."""
        total = self._count_evidence_refs(self)
        if total == 0:
            return 0.0
        return self._count_evidence_refs_with_quote(self) / total

    def recalculate_evidence_coverage(self) -> float:
        """Update and return the deterministic evidence coverage."""
        self.evidence_coverage = self.calculate_evidence_coverage()
        return self.evidence_coverage
