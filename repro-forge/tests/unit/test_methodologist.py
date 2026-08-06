"""Tests for Methodologist agent using FakeLLMProvider."""

import json

import pytest

from repro_forge.agents.methodologist import Methodologist
from repro_forge.core.types import AgentConfig
from repro_forge.core.types import AgentType
from repro_forge.paper.extractor.evidence import PaperEvidenceView
from repro_forge.paper.extractor.schemas import EvidenceStatus
from repro_forge.paper.schemas import Paper
from repro_forge.paper.schemas import PaperNote
from repro_forge.paper.schemas import Section
from repro_forge.paper.schemas import SectionType
from repro_forge.providers.base import BaseProvider
from repro_forge.providers.base import LLMRequest
from repro_forge.providers.base import LLMResponse
from repro_forge.providers.base import LLMToolCall
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
                content="Our model uses 3 convolutional layers with 64, 128, 256 filters. We use Adam with lr=0.001, batch_size=32, and train for 100 epochs.",
                section_type=SectionType.METHOD,
            ),
            Section(
                title="Experiments",
                content="TestModel achieves 94.5% accuracy on CIFAR-10.",
                section_type=SectionType.EXPERIMENTS,
            ),
        ],
        total_pages=5,
    )


FAKE_DONE_JSON = json.dumps(
    {
        "problem_statement": "Image classification with small convolutional networks.",
        "algorithms": [
            {
                "name": "TestModel",
                "purpose": "Image classification",
                "steps": [
                    {
                        "order": 1,
                        "description": "3 conv layers with increasing filters",
                        "evidence": {
                            "section_title": "Method",
                            "quote": "3 convolutional layers with 64, 128, 256 filters",
                        },
                    },
                ],
                "assumptions": ["Input size is 32x32"],
                "evidence": {
                    "section_title": "Method",
                    "quote": "We propose TestModel for image classification",
                },
            }
        ],
        "architecture": [
            {
                "name": "Conv1",
                "component_type": "convolution",
                "description": "64 filters",
                "parameters": {},
                "evidence": {"section_title": "Method", "quote": "64 filters"},
            },
        ],
        "training_recipe": {
            "learning_rate": {
                "value": 0.001,
                "raw_text": "lr=0.001",
                "status": "verified",
                "evidence": {"section_title": "Method", "quote": "Adam with lr=0.001"},
            },
            "batch_size": {
                "value": 32,
                "raw_text": "batch_size=32",
                "status": "verified",
                "evidence": {"section_title": "Method", "quote": "batch_size=32"},
            },
            "epochs": {
                "value": 100,
                "raw_text": "100 epochs",
                "status": "verified",
                "evidence": {"section_title": "Method", "quote": "train for 100 epochs"},
            },
            "optimizer": {
                "value": "Adam",
                "raw_text": "Adam",
                "status": "verified",
                "evidence": {"section_title": "Method", "quote": "Adam with lr=0.001"},
            },
        },
        "evaluation_protocol": {
            "datasets": [{"value": "CIFAR-10", "status": "verified"}],
            "metrics": [{"value": "Accuracy", "status": "verified"}],
            "reported_claims": [
                {
                    "dataset": "CIFAR-10",
                    "metric_name": "Accuracy",
                    "reported_value": "94.5",
                    "status": "verified",
                    "evidence": {
                        "section_title": "Experiments",
                        "quote": "94.5% accuracy on CIFAR-10",
                    },
                },
            ],
        },
        "equations": [],
        "reproducibility_gaps": [],
        "assumptions": [],
    }
)


class TestMethodologist:
    def test_provider_is_required(self) -> None:
        with pytest.raises(ValueError, match="requires a provider"):
            Methodologist()

    @pytest.mark.asyncio
    async def test_full_analysis(self) -> None:
        provider = FakeLLMProvider(
            responses=[
                "Let me list sections.",
                "Let me read the method section.",
                "Let me search for hyperparameters.",
                "Let me read the experiments.",
                f"DONE\n{FAKE_DONE_JSON}",
            ]
        )
        methodologist = Methodologist(
            config=AgentConfig(agent_type=AgentType.METHODOLOGIST, max_steps=10),
            provider=provider,
        )
        view = PaperEvidenceView(_make_paper())
        analysis = await methodologist.analyze(view)

        assert analysis.paper_id == "1234.5678"
        assert "image classification" in analysis.problem_statement.lower()
        assert len(analysis.algorithms) == 1
        assert analysis.algorithms[0].name == "TestModel"
        assert analysis.training_recipe.learning_rate.status.value == "verified"
        assert analysis.training_recipe.batch_size.value == 32
        assert analysis.training_recipe.epochs.value == 100
        assert analysis.evaluation_protocol.reported_claims[0].reported_value == "94.5"

    @pytest.mark.asyncio
    async def test_done_triggers_finalize(self) -> None:
        provider = FakeLLMProvider(
            responses=[
                f"DONE\n{FAKE_DONE_JSON}",
            ]
        )
        methodologist = Methodologist(
            config=AgentConfig(agent_type=AgentType.METHODOLOGIST, max_steps=5),
            provider=provider,
        )
        view = PaperEvidenceView(_make_paper())
        analysis = await methodologist.analyze(view)
        assert analysis.paper_id != ""

    @pytest.mark.asyncio
    async def test_invalid_json_repairs_once(self) -> None:
        provider = FakeLLMProvider(
            responses=[
                "DONE\n{not valid json!!!",
                f"DONE\n{FAKE_DONE_JSON}",
            ]
        )
        methodologist = Methodologist(
            config=AgentConfig(agent_type=AgentType.METHODOLOGIST, max_steps=10),
            provider=provider,
        )
        view = PaperEvidenceView(_make_paper())
        analysis = await methodologist.analyze(view)
        assert analysis.algorithms[0].name == "TestModel"
        assert analysis.extraction_trace == ["0:finalize:ok", "1:finalize:ok"]

    @pytest.mark.asyncio
    async def test_failed_analysis_raises(self) -> None:
        provider = FakeLLMProvider(
            responses=[
                "Let me think about this.",
                "Still thinking...",
                "Hmm.",
                "Let me read the abstract.",
            ]
        )
        methodologist = Methodologist(
            config=AgentConfig(agent_type=AgentType.METHODOLOGIST, max_steps=3),
            provider=provider,
        )
        view = PaperEvidenceView(_make_paper())
        with pytest.raises(RuntimeError):
            await methodologist.analyze(view)

    @pytest.mark.asyncio
    async def test_evidence_metadata_populated(self) -> None:
        provider = FakeLLMProvider(
            responses=[
                f"DONE\n{FAKE_DONE_JSON}",
            ]
        )
        methodologist = Methodologist(
            config=AgentConfig(agent_type=AgentType.METHODOLOGIST, max_steps=5),
            provider=provider,
        )
        view = PaperEvidenceView(_make_paper())
        analysis = await methodologist.analyze(view)

        assert analysis.algorithms[0].evidence.source_hash == view.source_hash
        assert analysis.algorithms[0].evidence.paper_id == "1234.5678"
        assert analysis.algorithms[0].evidence.section_id != ""

    @pytest.mark.asyncio
    async def test_provider_model_is_inherited_from_default_config(self) -> None:
        provider = FakeLLMProvider(responses=[f"DONE\n{FAKE_DONE_JSON}"])
        methodologist = Methodologist(
            config=AgentConfig(agent_type=AgentType.METHODOLOGIST, max_steps=5),
            provider=provider,
        )
        assert methodologist.config.model == provider.model

    @pytest.mark.asyncio
    async def test_explicit_model_is_not_overridden(self) -> None:
        provider = FakeLLMProvider(responses=[f"DONE\n{FAKE_DONE_JSON}"])
        methodologist = Methodologist(
            config=AgentConfig(
                agent_type=AgentType.METHODOLOGIST,
                model="gpt-4o",
                max_steps=5,
            ),
            provider=provider,
        )
        assert methodologist.config.model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_paper_note_hint_is_added_once(self) -> None:
        provider = FakeLLMProvider(responses=["Let me list sections.", f"DONE\n{FAKE_DONE_JSON}"])
        methodologist = Methodologist(provider=provider)
        await methodologist.analyze(
            PaperEvidenceView(_make_paper()),
            paper_note=PaperNote(tldr="A compact reading note."),
        )

        hints = [
            message
            for message in methodologist._conversation
            if "P1 PaperNote available" in str(message.get("content", ""))
        ]
        assert len(hints) == 1

    @pytest.mark.asyncio
    async def test_nested_claim_validation_triggers_repair(self) -> None:
        invalid = json.loads(FAKE_DONE_JSON)
        invalid["evaluation_protocol"]["reported_claims"][0]["dataset"] = ""
        provider = FakeLLMProvider(
            responses=[
                "DONE\n" + json.dumps(invalid),
                f"DONE\n{FAKE_DONE_JSON}",
            ]
        )

        analysis = await Methodologist(provider=provider).analyze(PaperEvidenceView(_make_paper()))

        assert provider.request_count == 2
        assert analysis.evaluation_protocol.reported_claims[0].dataset == "CIFAR-10"

    @pytest.mark.asyncio
    async def test_schema_type_error_triggers_repair(self) -> None:
        invalid = json.loads(FAKE_DONE_JSON)
        invalid["algorithms"] = "not-a-list"
        provider = FakeLLMProvider(
            responses=[
                "DONE\n" + json.dumps(invalid),
                f"DONE\n{FAKE_DONE_JSON}",
            ]
        )

        analysis = await Methodologist(provider=provider).analyze(PaperEvidenceView(_make_paper()))

        assert provider.request_count == 2
        assert analysis.algorithms[0].name == "TestModel"

    @pytest.mark.asyncio
    async def test_analysis_includes_sanitized_extraction_trace(self) -> None:
        provider = FakeLLMProvider(responses=[f"DONE\n{FAKE_DONE_JSON}"])
        analysis = await Methodologist(provider=provider).analyze(PaperEvidenceView(_make_paper()))

        assert analysis.extraction_trace == ["0:finalize:ok"]

    def test_metadata_population_only_touches_evidence_fields(self) -> None:
        methodologist = Methodologist(provider=FakeLLMProvider())
        methodologist._view = PaperEvidenceView(_make_paper())
        data: dict[str, object] = {
            "metadata": {"section_title": "Method", "quote": "not evidence"},
            "algorithm": {"evidence": {"section_title": "Method", "quote": "64 filters"}},
        }

        methodologist._populate_evidence_metadata(data)

        metadata = data["metadata"]
        algorithm = data["algorithm"]
        assert isinstance(metadata, dict)
        assert isinstance(algorithm, dict)
        assert "source_hash" not in metadata
        assert algorithm["evidence"]["source_hash"] == methodologist._view.source_hash

    @pytest.mark.asyncio
    async def test_native_tool_call_round_trip(self) -> None:
        class NativeToolProvider(BaseProvider):
            def __init__(self) -> None:
                super().__init__(model="deepseek-v4-flash")
                self.requests: list[LLMRequest] = []
                self.index = 0

            async def generate(self, request: LLMRequest) -> LLMResponse:
                self.requests.append(request)
                self.index += 1
                if self.index == 1:
                    return LLMResponse(
                        content="",
                        model=self.model,
                        tool_calls=[
                            LLMToolCall(call_id="call_1", name="list_sections", arguments={})
                        ],
                        usage={"total_tokens": 7},
                    )
                return LLMResponse(
                    content=f"DONE\n{FAKE_DONE_JSON}",
                    model=self.model,
                    usage={"total_tokens": 11},
                )

            async def generate_stream(self, request: LLMRequest):
                yield ""

            @property
            def provider_name(self) -> str:
                return "native-tool-test"

        provider = NativeToolProvider()
        methodologist = Methodologist(provider=provider)
        analysis = await methodologist.analyze(PaperEvidenceView(_make_paper()))

        assert analysis.paper_id == "1234.5678"
        assert analysis.total_tokens_used == 18
        assert len(provider.requests) == 2
        second_messages = provider.requests[1].messages
        assistant = next(message for message in second_messages if message["role"] == "assistant")
        tool = next(message for message in second_messages if message["role"] == "tool")
        assert assistant["tool_calls"][0]["id"] == "call_1"
        assert tool["tool_call_id"] == "call_1"

    @pytest.mark.asyncio
    async def test_parallel_tool_calls_are_drained_at_step_boundary(self) -> None:
        class ParallelToolProvider(BaseProvider):
            def __init__(self) -> None:
                super().__init__(model="deepseek-chat")
                self.index = 0

            async def generate(self, request: LLMRequest) -> LLMResponse:
                self.index += 1
                if self.index == 1:
                    return LLMResponse(
                        content="",
                        model=self.model,
                        tool_calls=[
                            LLMToolCall(call_id="call_1", name="list_sections", arguments={}),
                            LLMToolCall(
                                call_id="call_2",
                                name="read_section",
                                arguments={"section_title": "Method"},
                            ),
                        ],
                    )
                return LLMResponse(content=f"DONE\n{FAKE_DONE_JSON}", model=self.model)

            async def generate_stream(self, request: LLMRequest):
                yield ""

            @property
            def provider_name(self) -> str:
                return "parallel-tool-test"

        provider = ParallelToolProvider()
        methodologist = Methodologist(
            config=AgentConfig(agent_type=AgentType.METHODOLOGIST, max_steps=1),
            provider=provider,
        )

        analysis = await methodologist.analyze(PaperEvidenceView(_make_paper()))

        assert analysis.algorithms[0].name == "TestModel"
        assert provider.index == 2
        assert not methodologist._repair_attempted
        roles = [message["role"] for message in methodologist._conversation]
        assert roles == ["system", "user", "assistant", "tool", "tool", "assistant"]

    @pytest.mark.asyncio
    async def test_declared_inferred_status_is_not_upgraded(self) -> None:
        output = json.loads(FAKE_DONE_JSON)
        output["algorithms"][0]["evidence"]["status"] = "inferred"
        provider = FakeLLMProvider(responses=["DONE\n" + json.dumps(output)])
        analysis = await Methodologist(provider=provider).analyze(PaperEvidenceView(_make_paper()))
        assert analysis.algorithms[0].evidence.status == EvidenceStatus.INFERRED

    @pytest.mark.asyncio
    async def test_parent_status_matches_non_verified_evidence(self) -> None:
        output = json.loads(FAKE_DONE_JSON)
        output["training_recipe"]["optimizer"]["evidence"]["status"] = "inferred"
        provider = FakeLLMProvider(responses=["DONE\n" + json.dumps(output)])

        analysis = await Methodologist(provider=provider).analyze(PaperEvidenceView(_make_paper()))

        assert analysis.training_recipe.optimizer.evidence.status == EvidenceStatus.INFERRED
        assert analysis.training_recipe.optimizer.status == EvidenceStatus.INFERRED

    @pytest.mark.asyncio
    async def test_verified_value_without_evidence_is_downgraded(self) -> None:
        output = json.loads(FAKE_DONE_JSON)
        output["training_recipe"]["optimizer"] = {
            "value": "Adam",
            "status": "verified",
        }
        provider = FakeLLMProvider(responses=["DONE\n" + json.dumps(output)])
        analysis = await Methodologist(provider=provider).analyze(PaperEvidenceView(_make_paper()))
        assert analysis.training_recipe.optimizer.status == EvidenceStatus.UNVERIFIED

    @pytest.mark.asyncio
    async def test_parent_status_follows_invalid_nested_evidence(self) -> None:
        output = json.loads(FAKE_DONE_JSON)
        output["training_recipe"]["optimizer"]["evidence"]["quote"] = "not in paper"
        provider = FakeLLMProvider(responses=["DONE\n" + json.dumps(output)])
        analysis = await Methodologist(provider=provider).analyze(PaperEvidenceView(_make_paper()))
        assert analysis.training_recipe.optimizer.status == EvidenceStatus.UNVERIFIED
        assert analysis.training_recipe.optimizer.evidence.status == EvidenceStatus.UNVERIFIED

    @pytest.mark.asyncio
    async def test_captured_equation_without_source_quote_is_downgraded(self) -> None:
        output = json.loads(FAKE_DONE_JSON)
        output["equations"] = [
            {
                "equation_id": "eq_1",
                "raw_text": "y = Wx + b",
                "parse_status": "captured",
            }
        ]
        provider = FakeLLMProvider(responses=["DONE\n" + json.dumps(output)])

        analysis = await Methodologist(provider=provider).analyze(PaperEvidenceView(_make_paper()))

        assert analysis.equations[0].parse_status.value == "partial"
