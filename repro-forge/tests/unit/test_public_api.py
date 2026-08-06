"""Tests for P2 public API exports and import paths."""

from repro_forge.agents import Methodologist
from repro_forge.agents import PaperReader
from repro_forge.paper.extractor import EvidenceRef
from repro_forge.paper.extractor import EvidenceStatus
from repro_forge.paper.extractor import MethodAnalysis
from repro_forge.paper.extractor import MethodologyPipeline
from repro_forge.paper.extractor import PaperEvidenceView


class TestPublicExports:
    def test_agent_exports(self) -> None:
        assert Methodologist is not None
        assert PaperReader is not None

    def test_extractor_exports(self) -> None:
        assert MethodAnalysis is not None
        assert MethodologyPipeline is not None
        assert PaperEvidenceView is not None
        assert EvidenceRef is not None
        assert EvidenceStatus is not None

    def test_import_paths(self) -> None:
        from repro_forge.agents import methodologist
        from repro_forge.paper.extractor import evidence
        from repro_forge.paper.extractor import pipeline
        from repro_forge.paper.extractor import schemas

        assert methodologist.Methodologist is Methodologist
        assert evidence.PaperEvidenceView is PaperEvidenceView
        assert pipeline.MethodologyPipeline is MethodologyPipeline
        assert schemas.MethodAnalysis is MethodAnalysis
