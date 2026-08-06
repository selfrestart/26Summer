"""Tests for P2 methodology extraction schemas.

Validates JSON round-trip, missing/conflicting evidence status,
and that golden fixtures remain deterministic.
"""

import json
from pathlib import Path

from repro_forge.paper.extractor.schemas import AlgorithmSpec
from repro_forge.paper.extractor.schemas import AlgorithmStep
from repro_forge.paper.extractor.schemas import EquationEvidence
from repro_forge.paper.extractor.schemas import EquationParseStatus
from repro_forge.paper.extractor.schemas import EvaluationProtocol
from repro_forge.paper.extractor.schemas import EvidenceRef
from repro_forge.paper.extractor.schemas import EvidenceStatus
from repro_forge.paper.extractor.schemas import EvidenceValue
from repro_forge.paper.extractor.schemas import MethodAnalysis
from repro_forge.paper.extractor.schemas import ReportedClaimDraft
from repro_forge.paper.extractor.schemas import ReproducibilityGap
from repro_forge.paper.extractor.schemas import TrainingRecipe


def _make_evidence(
    section_title: str = "Section 3",
    quote: str = "We use Adam with lr=1e-4",
    status: EvidenceStatus = EvidenceStatus.VERIFIED,
) -> EvidenceRef:
    return EvidenceRef(
        evidence_id="ev_001",
        paper_id="1706.03762",
        source_hash="abc123",
        section_id="sec_3",
        section_title=section_title,
        page_start=5,
        quote=quote,
        quote_hash=str(hash(quote)),
        status=status,
    )


class TestEvidenceRef:
    def test_round_trip(self) -> None:
        ref = _make_evidence()
        d = ref.model_dump()
        ref2 = EvidenceRef(**d)
        assert ref2.quote == ref.quote
        assert ref2.page_start == 5
        assert ref2.status == EvidenceStatus.VERIFIED

    def test_default_values(self) -> None:
        ref = EvidenceRef()
        assert ref.evidence_id == ""
        assert ref.status == EvidenceStatus.UNVERIFIED
        assert ref.page_start is None
        assert ref.confidence == 1.0

    def test_page_none_round_trip(self) -> None:
        ref = EvidenceRef(page_start=None, page_end=None)
        d = ref.model_dump()
        assert d["page_start"] is None
        assert d["page_end"] is None
        ref2 = EvidenceRef(**d)
        assert ref2.page_start is None


class TestEvidenceValue:
    def test_verified_value(self) -> None:
        ev = EvidenceRef(
            evidence_id="ev_001",
            quote="batch_size=64",
            status=EvidenceStatus.VERIFIED,
        )
        v = EvidenceValue(
            value=64,
            raw_text="batch_size=64",
            status=EvidenceStatus.VERIFIED,
            evidence=ev,
        )
        assert v.value == 64
        assert v.status == EvidenceStatus.VERIFIED

    def test_not_reported(self) -> None:
        v = EvidenceValue.not_reported("learning_rate")
        assert v.value is None
        assert v.status == EvidenceStatus.NOT_REPORTED
        assert "learning_rate" in v.notes

    def test_reported_factory(self) -> None:
        ev = _make_evidence(quote="lr=0.001")
        v = EvidenceValue.reported(0.001, ev, "lr=0.001")
        assert v.status == EvidenceStatus.VERIFIED
        assert v.value == 0.001


class TestEquationEvidence:
    def test_captured_equation(self) -> None:
        eq = EquationEvidence(
            equation_id="eq_001",
            label="(1)",
            raw_text="\\text{Attention}(Q,K,V) = \\text{softmax}(\\frac{QK^T}{\\sqrt{d_k}})V",
            parse_status=EquationParseStatus.CAPTURED,
            evidence=_make_evidence(quote="Attention(Q,K,V) = ..."),
        )
        assert eq.parse_status == EquationParseStatus.CAPTURED
        assert eq.label == "(1)"

    def test_not_available_equation(self) -> None:
        eq = EquationEvidence(
            equation_id="eq_002",
            parse_status=EquationParseStatus.NOT_AVAILABLE,
        )
        assert eq.raw_text == ""
        assert eq.parse_status == EquationParseStatus.NOT_AVAILABLE


class TestAlgorithmSpec:
    def test_minimal_algorithm(self) -> None:
        algo = AlgorithmSpec(
            name="Transformer",
            steps=[
                AlgorithmStep(
                    order=1,
                    description="Compute multi-head self-attention",
                    evidence=_make_evidence(quote="MultiHead(Q,K,V) = ..."),
                ),
                AlgorithmStep(
                    order=2,
                    description="Apply position-wise feed-forward network",
                    evidence=_make_evidence(quote="FFN(x) = ..."),
                ),
            ],
            evidence=_make_evidence(quote="The Transformer follows..."),
        )
        assert len(algo.steps) == 2
        assert algo.steps[0].order == 1

    def test_round_trip(self) -> None:
        algo = AlgorithmSpec(
            name="Test Algo",
            steps=[AlgorithmStep(order=1, description="Step 1")],
        )
        d = algo.model_dump()
        algo2 = AlgorithmSpec(**d)
        assert algo2.name == "Test Algo"
        assert algo2.steps[0].description == "Step 1"


class TestTrainingRecipe:
    def test_default_all_not_reported(self) -> None:
        recipe = TrainingRecipe()
        assert recipe.learning_rate.status == EvidenceStatus.NOT_REPORTED
        assert recipe.batch_size.status == EvidenceStatus.NOT_REPORTED
        assert recipe.epochs.status == EvidenceStatus.NOT_REPORTED


class TestReportedClaimDraft:
    def test_claim_with_unit_missing(self) -> None:
        claim = ReportedClaimDraft(
            claim_id="c_001",
            dataset="ImageNet",
            metric_name="Top-1 Accuracy",
            reported_value="94.5",
            status=EvidenceStatus.VERIFIED,
            evidence=_make_evidence(quote="94.5% top-1 accuracy"),
        )
        assert claim.unit == ""
        assert claim.split == ""

    def test_claim_not_reported_is_reflected(self) -> None:
        claim = ReportedClaimDraft(
            claim_id="c_002",
            metric_name="FID",
            status=EvidenceStatus.NOT_REPORTED,
            notes="FID not mentioned in experiments section",
        )
        assert claim.status == EvidenceStatus.NOT_REPORTED


class TestReproducibilityGap:
    def test_gap_creation(self) -> None:
        gap = ReproducibilityGap(
            category="config",
            description="Learning rate schedule not specified",
            impact="Cannot reproduce exact training dynamics",
            related_sections=["Section 4.1"],
            suggested_resolution="Check supplementary or contact authors",
        )
        assert gap.category == "config"


class TestMethodAnalysis:
    GOLDEN_JSON = json.dumps(
        {
            "paper_id": "1706.03762",
            "title": "Attention Is All You Need",
            "problem_statement": "Sequence transduction without recurrence",
            "algorithms": [
                {
                    "name": "Transformer",
                    "purpose": "Sequence-to-sequence modeling",
                    "steps": [
                        {
                            "order": 1,
                            "description": "Self-attention",
                            "inputs": [],
                            "outputs": [],
                            "equations": [],
                            "evidence": {
                                "evidence_id": "ev_001",
                                "paper_id": "1706.03762",
                                "source_hash": "abc123",
                                "section_id": "sec_3",
                                "section_title": "Model Architecture",
                                "page_start": 5,
                                "page_end": None,
                                "quote": "MultiHead(Q,K,V) = Concat(head_1,...,head_h)W^O",
                                "quote_hash": "hash1",
                                "chunk_index": None,
                                "status": "verified",
                                "confidence": 1.0,
                            },
                        },
                    ],
                    "evidence": {
                        "evidence_id": "ev_002",
                        "paper_id": "1706.03762",
                        "source_hash": "abc123",
                        "section_id": "sec_3",
                        "section_title": "Model Architecture",
                        "page_start": 5,
                        "page_end": None,
                        "quote": "The Transformer follows the encoder-decoder structure",
                        "quote_hash": "hash2",
                        "chunk_index": None,
                        "status": "verified",
                        "confidence": 1.0,
                    },
                },
            ],
            "reported_claims": [
                {
                    "claim_id": "c_001",
                    "dataset": "WMT 2014 En-De",
                    "metric_name": "BLEU",
                    "reported_value": "28.4",
                    "status": "verified",
                },
            ],
            "evidence_coverage": 0.5,
        }
    )

    def test_golden_json_round_trip(self) -> None:
        data = json.loads(self.GOLDEN_JSON)
        analysis = MethodAnalysis(**data)
        assert analysis.paper_id == "1706.03762"
        assert len(analysis.algorithms) == 1
        assert (
            analysis.algorithms[0].steps[0].evidence.quote
            == "MultiHead(Q,K,V) = Concat(head_1,...,head_h)W^O"
        )
        assert analysis.algorithms[0].evidence.page_start == 5

        d = analysis.model_dump()
        analysis2 = MethodAnalysis(**d)
        assert analysis2.evidence_coverage == 0.5

    def test_minimal_analysis(self) -> None:
        analysis = MethodAnalysis(paper_id="test")
        assert analysis.paper_id == "test"
        assert analysis.algorithms == []
        assert analysis.evidence_coverage == 0.0

    def test_default_page_none_not_zero(self) -> None:
        analysis = MethodAnalysis(paper_id="test")
        d = analysis.model_dump()
        ev_ref_data = d.get("algorithms")
        assert ev_ref_data is not None
        ref = EvidenceRef()
        ref_d = ref.model_dump()
        assert ref_d["page_start"] is None

    def test_verified_claim_count(self) -> None:
        analysis = MethodAnalysis(
            evaluation_protocol={
                "reported_claims": [
                    ReportedClaimDraft(claim_id="c1", status=EvidenceStatus.VERIFIED),
                    ReportedClaimDraft(claim_id="c2", status=EvidenceStatus.INFERRED),
                    ReportedClaimDraft(claim_id="c3", status=EvidenceStatus.VERIFIED),
                ]
            },
        )
        assert analysis.verified_claim_count == 2

    def test_legacy_top_level_claims_migrate_to_evaluation_protocol(self) -> None:
        analysis = MethodAnalysis.model_validate(
            {
                "reported_claims": [
                    {
                        "claim_id": "legacy",
                        "dataset": "ImageNet",
                        "metric_name": "Accuracy",
                    }
                ]
            }
        )

        assert analysis.reported_claims[0].claim_id == "legacy"
        assert analysis.evaluation_protocol.reported_claims[0].claim_id == "legacy"
        assert "reported_claims" not in analysis.model_dump()

    def test_legacy_claims_merge_with_typed_evaluation_protocol(self) -> None:
        analysis = MethodAnalysis.model_validate(
            {
                "evaluation_protocol": EvaluationProtocol(
                    reported_claims=[ReportedClaimDraft(claim_id="nested")]
                ),
                "reported_claims": [ReportedClaimDraft(claim_id="legacy")],
            }
        )

        assert [claim.claim_id for claim in analysis.reported_claims] == ["nested", "legacy"]

    def test_gap_count(self) -> None:
        analysis = MethodAnalysis(
            reproducibility_gaps=[
                ReproducibilityGap(category="config"),
                ReproducibilityGap(category="data"),
                ReproducibilityGap(category="code"),
            ],
        )
        assert analysis.gap_count == 3
        assert analysis.algorithm_count == 0

    def test_p2_fixtures_preserve_failure_semantics(self) -> None:
        fixture_dir = Path(__file__).parents[1] / "fixtures" / "p2"

        complete = MethodAnalysis.model_validate_json(
            (fixture_dir / "methodology_complete.json").read_text(encoding="utf-8")
        )
        assert complete.algorithms[0].steps[0].description
        assert complete.evaluation_protocol.reported_claims[0].unit == "%"

        captured = MethodAnalysis.model_validate_json(
            (fixture_dir / "equation_captured.json").read_text(encoding="utf-8")
        )
        assert captured.equations[0].parse_status == EquationParseStatus.CAPTURED
        assert captured.equations[0].raw_text == "y = Wx + b"

        unavailable = MethodAnalysis.model_validate_json(
            (fixture_dir / "equation_not_available.json").read_text(encoding="utf-8")
        )
        assert unavailable.equations[0].parse_status == EquationParseStatus.NOT_AVAILABLE
        assert unavailable.equations[0].raw_text == ""
        assert unavailable.reproducibility_gaps

        claim = MethodAnalysis.model_validate_json(
            (fixture_dir / "claim_complete.json").read_text(encoding="utf-8")
        ).evaluation_protocol.reported_claims[0]
        assert claim.unit == "fraction"
        assert claim.split == "validation"

        incomplete_claim = MethodAnalysis.model_validate_json(
            (fixture_dir / "claim_missing_unit_split.json").read_text(encoding="utf-8")
        ).evaluation_protocol.reported_claims[0]
        assert incomplete_claim.reported_value == "94.5"
        assert incomplete_claim.raw_text == "score=94.5"
        assert incomplete_claim.unit == ""
        assert incomplete_claim.split == ""

    def test_evidence_coverage_is_recomputed_and_deduplicated(self) -> None:
        ref = EvidenceRef(evidence_id="same", quote="source")
        analysis = MethodAnalysis(
            algorithms=[AlgorithmSpec(name="A", evidence=ref)],
            assumptions=[EvidenceValue(value="same", evidence=ref)],
            evidence_coverage=0.0,
        )
        coverage = analysis.calculate_evidence_coverage()
        assert coverage == 1.0
        analysis.evidence_coverage = 0.25
        assert analysis.recalculate_evidence_coverage() == coverage

    def test_inferred_evidence_does_not_count_as_verified_coverage(self) -> None:
        ref = EvidenceRef(
            evidence_id="inferred",
            paper_id="paper",
            source_hash="source",
            section_id="section",
            section_title="Method",
            quote="The paper implies this.",
            status=EvidenceStatus.INFERRED,
        )
        analysis = MethodAnalysis(algorithms=[AlgorithmSpec(name="A", evidence=ref)])

        assert analysis.calculate_evidence_coverage() == 0.0
