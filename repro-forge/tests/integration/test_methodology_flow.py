"""Integration test for the P2 methodology extraction flow."""

import json

import pytest

from repro_forge.agents.methodologist import Methodologist
from repro_forge.core.types import AgentConfig
from repro_forge.core.types import AgentType
from repro_forge.paper.extractor import MethodAnalysis
from repro_forge.paper.extractor import MethodologyPipeline
from repro_forge.paper.schemas import Paper
from repro_forge.paper.schemas import Section
from repro_forge.paper.schemas import SectionType
from tests.conftest import FakeLLMProvider


def _make_transformer_paper() -> Paper:
    return Paper(
        metadata={"title": "Attention Is All You Need", "arxiv_id": "1706.03762"},
        sections=[
            Section(
                title="Abstract",
                content="We propose the Transformer, based solely on attention mechanisms.",
                section_type=SectionType.ABSTRACT,
            ),
            Section(
                title="Model Architecture",
                content="The encoder is composed of 6 identical layers with multi-head self-attention. We use 8 heads, dimension 512, Adam optimizer with lr=0.0001.",
                section_type=SectionType.METHOD,
            ),
            Section(
                title="Experiments",
                content="We achieve 28.4 BLEU on WMT 2014 En-De translation.",
                section_type=SectionType.EXPERIMENTS,
            ),
        ],
        total_pages=11,
    )


FAKE_FLOW_JSON = json.dumps(
    {
        "problem_statement": "Sequence transduction without recurrence.",
        "algorithms": [
            {
                "name": "Transformer",
                "purpose": "Sequence transduction",
                "steps": [
                    {
                        "order": 1,
                        "description": "Multi-head self-attention",
                        "evidence": {
                            "section_title": "Model Architecture",
                            "quote": "multi-head self-attention",
                        },
                    },
                ],
                "assumptions": [],
                "evidence": {
                    "section_title": "Abstract",
                    "quote": "based solely on attention mechanisms",
                },
            },
        ],
        "architecture": [],
        "training_recipe": {
            "optimizer": {"value": "Adam", "status": "verified"},
            "learning_rate": {"value": 0.0001, "status": "verified"},
        },
        "evaluation_protocol": {
            "reported_claims": [
                {
                    "dataset": "WMT 2014 En-De",
                    "metric_name": "BLEU",
                    "reported_value": "28.4",
                    "status": "verified",
                    "evidence": {"section_title": "Experiments", "quote": "28.4 BLEU"},
                },
            ],
        },
        "equations": [],
        "reproducibility_gaps": [],
        "assumptions": [],
    }
)


class TestMethodologyFlow:
    @pytest.mark.asyncio
    async def test_end_to_end_flow(self) -> None:
        provider = FakeLLMProvider(
            responses=[
                "Let me list the sections.",
                "Let me read the model architecture section.",
                "Let me search for hyperparameters.",
                "Let me read the experiments section.",
                f"DONE\n{FAKE_FLOW_JSON}",
            ]
        )
        methodologist = Methodologist(
            config=AgentConfig(agent_type=AgentType.METHODOLOGIST, max_steps=10),
            provider=provider,
        )
        pipeline = MethodologyPipeline(methodologist=methodologist)

        analysis = await pipeline.analyze(_make_transformer_paper())

        assert isinstance(analysis, MethodAnalysis)
        assert analysis.paper_id == "1706.03762"
        assert analysis.algorithms[0].name == "Transformer"
        assert analysis.algorithms[0].steps[0].evidence.section_title == "Model Architecture"
        assert analysis.training_recipe.optimizer.value == "Adam"
        assert analysis.training_recipe.learning_rate.value == 0.0001
        claim = analysis.evaluation_protocol.reported_claims[0]
        assert claim.reported_value == "28.4"
        assert claim.evidence.quote == "28.4 BLEU"
        assert claim.evidence.source_hash != ""  # source hash filled by view

    @pytest.mark.asyncio
    async def test_analysis_round_trips_to_json(self) -> None:
        provider = FakeLLMProvider(responses=[f"DONE\n{FAKE_FLOW_JSON}"])
        methodologist = Methodologist(
            config=AgentConfig(agent_type=AgentType.METHODOLOGIST, max_steps=5),
            provider=provider,
        )
        pipeline = MethodologyPipeline(methodologist=methodologist)

        analysis = await pipeline.analyze(_make_transformer_paper())
        data = analysis.model_dump(mode="json")
        analysis2 = MethodAnalysis(**data)
        assert analysis2.algorithms[0].name == "Transformer"
        assert analysis2.evaluation_protocol.reported_claims[0].reported_value == "28.4"
