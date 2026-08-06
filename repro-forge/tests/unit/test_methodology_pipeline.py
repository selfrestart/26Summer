"""Tests for MethodologyPipeline composition."""

import json

import pytest

from repro_forge.agents.methodologist import Methodologist
from repro_forge.core.types import AgentConfig
from repro_forge.core.types import AgentType
from repro_forge.paper.extractor import MethodAnalysis
from repro_forge.paper.extractor import MethodologyPipeline
from repro_forge.paper.schemas import Paper
from repro_forge.paper.schemas import PaperNote
from repro_forge.paper.schemas import Section
from repro_forge.paper.schemas import SectionType
from tests.conftest import FakeLLMProvider


def _make_paper() -> Paper:
    return Paper(
        metadata={"title": "Test Model", "arxiv_id": "1234.5678"},
        sections=[
            Section(
                title="Abstract",
                content="We propose TestModel for image classification.",
                section_type=SectionType.ABSTRACT,
            ),
            Section(
                title="Method",
                content="Our model uses Adam with lr=0.001, batch_size=32.",
                section_type=SectionType.METHOD,
            ),
            Section(
                title="Experiments",
                content="TestModel achieves 94.5% accuracy on CIFAR-10.",
                section_type=SectionType.EXPERIMENTS,
            ),
        ],
        total_pages=3,
    )


FAKE_ANALYSIS_JSON = json.dumps(
    {
        "problem_statement": "Image classification with small conv nets.",
        "algorithms": [
            {
                "name": "TestModel",
                "purpose": "Image classification",
                "steps": [],
                "assumptions": [],
                "evidence": {"section_title": "Method", "quote": "Our model uses Adam"},
            },
        ],
        "architecture": [],
        "training_recipe": {
            "learning_rate": {
                "value": 0.001,
                "status": "verified",
                "evidence": {"section_title": "Method", "quote": "lr=0.001"},
            },
        },
        "evaluation_protocol": {
            "reported_claims": [
                {
                    "dataset": "CIFAR-10",
                    "metric_name": "Accuracy",
                    "reported_value": "94.5",
                    "status": "verified",
                }
            ],
        },
        "equations": [],
        "reproducibility_gaps": [],
        "assumptions": [],
    }
)


class TestMethodologyPipeline:
    @pytest.mark.asyncio
    async def test_analyze_parsed_paper(self) -> None:
        provider = FakeLLMProvider(responses=[f"DONE\n{FAKE_ANALYSIS_JSON}"])
        methodologist = Methodologist(
            config=AgentConfig(agent_type=AgentType.METHODOLOGIST, max_steps=5),
            provider=provider,
        )
        pipeline = MethodologyPipeline(methodologist=methodologist)
        analysis = await pipeline.analyze(_make_paper())

        assert isinstance(analysis, MethodAnalysis)
        assert analysis.paper_id == "1234.5678"
        assert analysis.algorithms[0].name == "TestModel"

    @pytest.mark.asyncio
    async def test_analyze_with_paper_note(self) -> None:
        provider = FakeLLMProvider(responses=[f"DONE\n{FAKE_ANALYSIS_JSON}"])
        methodologist = Methodologist(
            config=AgentConfig(agent_type=AgentType.METHODOLOGIST, max_steps=5),
            provider=provider,
        )
        pipeline = MethodologyPipeline(methodologist=methodologist)
        note = PaperNote(tldr="A simple CNN baseline.")
        analysis = await pipeline.analyze(_make_paper(), paper_note=note)
        assert analysis.problem_statement != ""

    @pytest.mark.asyncio
    async def test_analyze_pdf_without_read_first(self) -> None:
        provider = FakeLLMProvider(responses=[f"DONE\n{FAKE_ANALYSIS_JSON}"])
        methodologist = Methodologist(
            config=AgentConfig(agent_type=AgentType.METHODOLOGIST, max_steps=5),
            provider=provider,
        )
        pipeline = MethodologyPipeline(methodologist=methodologist)

        class _FakeParser:
            def parse(self, path):
                return _make_paper()

        pipeline.paper_pipeline.parser = _FakeParser()  # type: ignore[assignment]
        analysis = await pipeline.analyze_pdf("fake.pdf", read_first=False)
        assert analysis.paper_id == "1234.5678"

    @pytest.mark.asyncio
    async def test_missing_methodologist_raises(self) -> None:
        pipeline = MethodologyPipeline(provider=None)
        with pytest.raises(ValueError, match="requires a provider"):
            await pipeline.analyze(_make_paper())
