"""Tests for PaperReader agent using FakeLLMProvider."""

import json

import pytest

from repro_forge.agents.paper_reader import PaperReader
from repro_forge.core.types import Action
from repro_forge.core.types import AgentConfig
from repro_forge.core.types import AgentType
from repro_forge.core.types import TaskSpec
from repro_forge.paper.chunker import PaperChunker
from repro_forge.paper.schemas import Paper
from repro_forge.paper.schemas import PaperNote
from repro_forge.paper.schemas import Section
from repro_forge.paper.schemas import SectionType
from repro_forge.providers.base import BaseProvider
from repro_forge.providers.base import LLMRequest
from repro_forge.providers.base import LLMResponse
from repro_forge.providers.base import LLMToolCall
from tests.conftest import FakeLLMProvider


def _make_test_paper() -> Paper:
    return Paper(
        metadata={"title": "Test Paper", "arxiv_id": "1234.5678"},
        sections=[
            Section(
                title="Abstract",
                content="We propose a novel attention method for better results.",
                section_type=SectionType.ABSTRACT,
                token_count=20,
            ),
            Section(
                title="Introduction",
                content="Deep learning has achieved great success. However, there remain challenges.",
                section_type=SectionType.INTRODUCTION,
                token_count=20,
            ),
            Section(
                title="Method",
                content="Our method uses multi-head attention with residual connections and layer normalization.",
                section_type=SectionType.METHOD,
                token_count=20,
            ),
            Section(
                title="Experiments",
                content="We evaluate on ImageNet achieving 94.5% top-1 accuracy beating previous SOTA.",
                section_type=SectionType.EXPERIMENTS,
                token_count=20,
            ),
            Section(
                title="Conclusion",
                content="We have shown that our method outperforms existing approaches.",
                section_type=SectionType.CONCLUSION,
                token_count=20,
            ),
        ],
        total_pages=5,
        total_tokens=100,
    )


FAKE_TLDR = json.dumps(
    {
        "tldr": "This paper proposes a novel attention mechanism that achieves SOTA on ImageNet classification.",
        "contributions": [
            {
                "description": "Novel multi-head attention variant",
                "supporting_sections": ["Method"],
            },
            {
                "description": "Residual connections with layer norm",
                "supporting_sections": ["Method"],
            },
        ],
        "methodology_summary": "Multi-head attention with residual connections and layer normalization.",
        "key_findings": [
            {
                "description": "Achieves SOTA on ImageNet",
                "metric_name": "Accuracy",
                "metric_value": "94.5%",
                "dataset": "ImageNet",
            },
        ],
        "strengths": ["Novel architecture", "Strong empirical results"],
        "weaknesses": ["Computational cost not analyzed"],
        "questions": ["How does it scale to larger datasets?"],
    }
)


def _setup_reader(provider: BaseProvider, paper: Paper, max_steps: int = 5) -> PaperReader:
    reader = PaperReader(
        config=AgentConfig(agent_type=AgentType.PAPER_READER, max_steps=max_steps),
        provider=provider,
    )
    chunker = PaperChunker(max_tokens=4000)
    reader._chunks = chunker.chunk(paper)
    reader._paper = paper
    return reader


class NativeToolProvider(BaseProvider):
    def __init__(self, responses: list[LLMResponse]) -> None:
        super().__init__(model="provider-model")
        self._responses = responses
        self.requests: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return self._responses.pop(0)

    async def generate_stream(self, request: LLMRequest):
        del request
        yield ""

    @property
    def provider_name(self) -> str:
        return "native-tool-fake"


class TestPaperReader:
    def test_default_config_inherits_provider_model(self) -> None:
        provider = FakeLLMProvider()

        reader = PaperReader(provider=provider)

        assert reader.config.model == provider.model

    @pytest.mark.asyncio
    async def test_native_tool_call_preserves_call_id_in_conversation(self) -> None:
        provider = NativeToolProvider(
            responses=[
                LLMResponse(
                    content="",
                    model="provider-model",
                    finish_reason="tool_calls",
                    tool_calls=[
                        LLMToolCall(
                            call_id="call_read_method",
                            name="read_section",
                            arguments={"section_title": "Method"},
                        )
                    ],
                )
            ]
        )
        paper = _make_test_paper()
        reader = PaperReader(
            config=AgentConfig(agent_type=AgentType.PAPER_READER, max_steps=2),
            provider=provider,
        )
        reader._chunks = PaperChunker(max_tokens=4000).chunk(paper)
        reader._paper = paper
        await reader.setup()

        thought = await reader.think(TaskSpec(title="test", description="test"))
        assistant_message = reader._conversation[-1]
        action = await reader.act(thought)

        assert action.id == "call_read_method"
        assert action.tool_name == "read_section"
        assert action.tool_input == {"section_title": "Method"}
        assert assistant_message["tool_calls"] == [
            {
                "id": "call_read_method",
                "type": "function",
                "function": {
                    "name": "read_section",
                    "arguments": '{"section_title": "Method"}',
                },
            }
        ]

        await reader.observe(action)

        assert reader._conversation[-1]["tool_call_id"] == "call_read_method"

    @pytest.mark.asyncio
    async def test_multiple_native_tool_calls_run_before_the_next_provider_request(self) -> None:
        provider = NativeToolProvider(
            responses=[
                LLMResponse(
                    content="",
                    model="provider-model",
                    finish_reason="tool_calls",
                    tool_calls=[
                        LLMToolCall(
                            call_id="call_list",
                            name="list_sections",
                            arguments={},
                        ),
                        LLMToolCall(
                            call_id="call_read_method",
                            name="read_section",
                            arguments={"section_title": "Method"},
                        ),
                    ],
                ),
                LLMResponse(content="DONE\n" + FAKE_TLDR, model="provider-model"),
            ]
        )
        paper = _make_test_paper()
        reader = PaperReader(
            config=AgentConfig(agent_type=AgentType.PAPER_READER, max_steps=3),
            provider=provider,
        )
        reader._chunks = PaperChunker(max_tokens=4000).chunk(paper)
        reader._paper = paper
        task = TaskSpec(title="test", description="test")
        await reader.setup()

        first_thought = await reader.think(task)
        assistant_message = reader._conversation[-1]
        first_action = await reader.act(first_thought)
        await reader.observe(first_action)
        second_thought = await reader.think(task)
        second_action = await reader.act(second_thought)
        await reader.observe(second_action)

        assert len(provider.requests) == 1
        assert [first_action.id, second_action.id] == ["call_list", "call_read_method"]
        assert [call["id"] for call in assistant_message["tool_calls"]] == [
            "call_list",
            "call_read_method",
        ]
        assert [message["tool_call_id"] for message in reader._conversation[-2:]] == [
            "call_list",
            "call_read_method",
        ]

    @pytest.mark.asyncio
    async def test_text_tool_action_synthesizes_a_matching_assistant_tool_call(self) -> None:
        provider = FakeLLMProvider(responses=["Let me list the sections."])
        paper = _make_test_paper()
        reader = _setup_reader(provider, paper, max_steps=2)
        task = TaskSpec(title="test", description="test")
        await reader.setup()

        thought = await reader.think(task)
        action = await reader.act(thought)
        await reader.observe(action)
        await reader.think(task)

        assert provider.last_request is not None
        assistant_message, tool_message = provider.last_request.messages[-2:]
        assert assistant_message["tool_calls"][0]["id"] == action.id
        assert tool_message["tool_call_id"] == action.id

    @pytest.mark.asyncio
    async def test_native_read_section_requires_a_non_empty_title(self) -> None:
        provider = NativeToolProvider(
            responses=[
                LLMResponse(
                    content="",
                    model="provider-model",
                    finish_reason="tool_calls",
                    tool_calls=[
                        LLMToolCall(
                            call_id="call_missing_title",
                            name="read_section",
                            arguments={},
                        )
                    ],
                )
            ]
        )
        paper = _make_test_paper()
        reader = _setup_reader(provider, paper, max_steps=2)
        await reader.setup()

        thought = await reader.think(TaskSpec(title="test", description="test"))
        action = await reader.act(thought)
        observation = await reader.observe(action)

        assert observation.is_error
        assert "section_title" in (observation.error or "")
        assert reader._read_sections == []
        assert reader._conversation[-1]["role"] == "tool"
        assert reader._conversation[-1]["tool_call_id"] == "call_missing_title"

    @pytest.mark.asyncio
    async def test_unknown_native_tool_returns_a_matching_tool_error(self) -> None:
        provider = NativeToolProvider(
            responses=[
                LLMResponse(
                    content="",
                    model="provider-model",
                    finish_reason="tool_calls",
                    tool_calls=[
                        LLMToolCall(
                            call_id="call_unknown",
                            name="unknown_tool",
                            arguments={},
                        )
                    ],
                )
            ]
        )
        paper = _make_test_paper()
        reader = _setup_reader(provider, paper, max_steps=2)
        await reader.setup()

        thought = await reader.think(TaskSpec(title="test", description="test"))
        action = await reader.act(thought)
        observation = await reader.observe(action)

        assert observation.is_error
        assert "unknown_tool" in (observation.error or "")
        assert reader._conversation[-1]["role"] == "tool"
        assert reader._conversation[-1]["tool_call_id"] == "call_unknown"

    @pytest.mark.asyncio
    async def test_native_search_requires_a_non_empty_query(self) -> None:
        provider = NativeToolProvider(
            responses=[
                LLMResponse(
                    content="",
                    model="provider-model",
                    finish_reason="tool_calls",
                    tool_calls=[
                        LLMToolCall(
                            call_id="call_missing_query",
                            name="search_paper",
                            arguments={},
                        )
                    ],
                )
            ]
        )
        paper = _make_test_paper()
        reader = _setup_reader(provider, paper, max_steps=2)
        await reader.setup()

        thought = await reader.think(TaskSpec(title="test", description="test"))
        action = await reader.act(thought)
        observation = await reader.observe(action)

        assert observation.is_error
        assert "query" in (observation.error or "")
        assert reader._conversation[-1]["role"] == "tool"
        assert reader._conversation[-1]["tool_call_id"] == "call_missing_query"

    @pytest.mark.asyncio
    async def test_long_section_reads_one_token_bounded_chunk_at_a_time(self) -> None:
        content = "alpha " * 12000 + "tail-sentinel"
        paper = Paper(
            sections=[
                Section(
                    title="Method",
                    content=content,
                    section_type=SectionType.METHOD,
                    token_count=len(content) // 4,
                )
            ]
        )
        reader = _setup_reader(FakeLLMProvider(), paper, max_steps=2)
        await reader.setup()

        first = await reader.observe(
            Action(
                id="call_method_0",
                tool_name="read_section",
                tool_input={"section_title": "Method", "chunk_index": 0},
            )
        )
        second = await reader.observe(
            Action(
                id="call_method_1",
                tool_name="read_section",
                tool_input={"section_title": "Method", "chunk_index": 1},
            )
        )

        assert "chunk 1 of" in first.content.lower()
        assert "chunk 2 of" in second.content.lower()
        assert len(first.content) < len(content)
        assert len(second.content) < len(content)
        assert first.content != second.content

    @pytest.mark.asyncio
    async def test_read_section_rejects_an_out_of_range_chunk_index(self) -> None:
        paper = _make_test_paper()
        reader = _setup_reader(FakeLLMProvider(), paper, max_steps=2)
        await reader.setup()

        observation = await reader.observe(
            Action(
                id="call_bad_chunk",
                tool_name="read_section",
                tool_input={"section_title": "Method", "chunk_index": 99},
            )
        )

        assert observation.is_error
        assert "chunk_index" in (observation.error or "")
        assert reader._conversation[-1]["tool_call_id"] == "call_bad_chunk"

    @pytest.mark.asyncio
    async def test_list_sections_action(self) -> None:
        provider = FakeLLMProvider(
            responses=[
                "Let me first list the sections to understand the structure.",
            ]
        )
        paper = _make_test_paper()
        reader = _setup_reader(provider, paper, max_steps=2)

        task = TaskSpec(title="test", description="test")
        await reader.setup()

        thought = await reader.think(task)
        action = await reader.act(thought)
        assert action.tool_name == "list_sections"

        obs = await reader.observe(action)
        assert "Abstract" in obs.content
        assert "Method" in obs.content

    @pytest.mark.asyncio
    async def test_read_section_action(self) -> None:
        provider = FakeLLMProvider(
            responses=[
                "Let me read the method section.",
            ]
        )
        paper = _make_test_paper()
        reader = _setup_reader(provider, paper, max_steps=2)

        task = TaskSpec(title="test", description="test")
        await reader.setup()

        thought = await reader.think(task)
        action = await reader.act(thought)
        assert action.tool_name == "read_section"

        obs = await reader.observe(action)
        assert "multi-head attention" in obs.content.lower()
        assert action.tool_input.get("section_title", "").lower() in obs.content.lower()

    @pytest.mark.asyncio
    async def test_search_paper_action(self) -> None:
        provider = FakeLLMProvider(
            responses=[
                "Let me search for attention mechanism.",
            ]
        )
        paper = _make_test_paper()
        reader = _setup_reader(provider, paper, max_steps=2)

        task = TaskSpec(title="test", description="test")
        await reader.setup()

        thought = await reader.think(task)
        action = await reader.act(thought)
        assert action.tool_name == "search_paper"

        obs = await reader.observe(action)
        assert "attention" in obs.content.lower()

    @pytest.mark.asyncio
    async def test_done_triggers_finalize(self) -> None:
        provider = FakeLLMProvider(
            responses=[
                "DONE\n" + FAKE_TLDR,
            ]
        )
        paper = _make_test_paper()
        reader = _setup_reader(provider, paper, max_steps=5)

        task = TaskSpec(title="test", description="test")
        await reader.setup()

        thought = await reader.think(task)
        action = await reader.act(thought)
        assert action.tool_name == "finalize"
        assert "tldr" in str(action.tool_input)

    @pytest.mark.asyncio
    async def test_full_read_flow(self) -> None:
        provider = FakeLLMProvider(
            responses=[
                "Let me list the sections.",
                "Let me read the abstract.",
                "DONE\n" + FAKE_TLDR,
            ]
        )
        reader = PaperReader(
            config=AgentConfig(agent_type=AgentType.PAPER_READER, max_steps=5),
            provider=provider,
        )

        note = await reader.read(_make_test_paper())

        assert isinstance(note, PaperNote)
        assert note.title == "Test Paper"
        assert "attention" in note.tldr.lower()
        assert len(note.contributions) == 2
        assert note.contributions[0].description == "Novel multi-head attention variant"
        assert note.key_findings[0].metric_value == "94.5%"
        assert "Novel architecture" in note.strengths
        assert len(note.reading_trace) > 0

    @pytest.mark.asyncio
    async def test_empty_paper_raises(self) -> None:
        provider = FakeLLMProvider()
        reader = PaperReader(
            config=AgentConfig(agent_type=AgentType.PAPER_READER, max_steps=5),
            provider=provider,
        )
        empty_paper = Paper()
        with pytest.raises(ValueError, match="readable"):
            await reader.read(empty_paper)

    @pytest.mark.asyncio
    async def test_trace_records_steps(self) -> None:
        provider = FakeLLMProvider(
            responses=[
                "Let me list the sections.",
                "Let me read the abstract.",
                "DONE\n" + FAKE_TLDR,
            ]
        )
        reader = PaperReader(
            config=AgentConfig(agent_type=AgentType.PAPER_READER, max_steps=5),
            provider=provider,
        )

        await reader.read(_make_test_paper())

        assert len(reader.trace.steps) > 0
        assert reader.trace.final_state is not None

    @pytest.mark.asyncio
    async def test_read_sets_current_paper_and_resets_trace_state(self) -> None:
        provider = FakeLLMProvider(
            responses=[
                'DONE\n{"tldr": "First", "contributions": [], "methodology_summary": "", "key_findings": [], "strengths": [], "weaknesses": [], "questions": []}',
            ]
        )
        reader = PaperReader(
            config=AgentConfig(agent_type=AgentType.PAPER_READER, max_steps=3),
            provider=provider,
        )
        paper = _make_test_paper()

        first = await reader.read(paper)
        first_run_id = reader.trace.run_id
        second = await reader.read(paper)

        assert reader._paper is paper
        assert first.tldr == second.tldr == "First"
        assert first.arxiv_id == "1234.5678"
        assert reader.trace.run_id != first_run_id
        assert reader.trace.step_count == 1

    @pytest.mark.asyncio
    async def test_json_extraction_from_markdown(self) -> None:
        provider = FakeLLMProvider(
            responses=[
                "DONE\n```json\n" + FAKE_TLDR + "\n```",
            ]
        )
        reader = PaperReader(
            config=AgentConfig(agent_type=AgentType.PAPER_READER, max_steps=3),
            provider=provider,
        )

        note = await reader.read(_make_test_paper())
        assert note.tldr != ""
        assert len(note.contributions) == 2

    @pytest.mark.asyncio
    async def test_read_accumulates_provider_token_usage(self) -> None:
        response = "DONE\n" + FAKE_TLDR
        provider = FakeLLMProvider(responses=[response])
        reader = PaperReader(
            config=AgentConfig(agent_type=AgentType.PAPER_READER, max_steps=1),
            provider=provider,
        )

        note = await reader.read(_make_test_paper())

        expected_total = 10 + len(response.split())
        assert reader.trace.total_tokens == expected_total
        assert reader.trace.steps[0].token_usage == {
            "prompt_tokens": 10,
            "completion_tokens": len(response.split()),
            "total_tokens": expected_total,
        }
        assert note.total_tokens_used == expected_total

    @pytest.mark.asyncio
    async def test_step_exhaustion_forces_a_tool_free_final_summary(self) -> None:
        first_response = "Let me list the sections."
        final_response = "DONE\n" + FAKE_TLDR
        provider = FakeLLMProvider(responses=[first_response, final_response])
        reader = PaperReader(
            config=AgentConfig(agent_type=AgentType.PAPER_READER, max_steps=1),
            provider=provider,
        )

        note = await reader.read(_make_test_paper())

        assert note.tldr != "PaperReader did not produce a final analysis."
        assert "attention" in note.tldr.lower()
        assert provider.request_count == 2
        assert provider.last_request is not None
        assert provider.last_request.tools is None
        assert provider.last_request.tool_choice is None
        expected_total = 20 + len(first_response.split()) + len(final_response.split())
        assert note.total_tokens_used == expected_total

    @pytest.mark.asyncio
    async def test_forced_summary_closes_pending_parallel_tool_calls(self) -> None:
        provider = NativeToolProvider(
            responses=[
                LLMResponse(
                    content="",
                    model="provider-model",
                    finish_reason="tool_calls",
                    tool_calls=[
                        LLMToolCall(
                            call_id="call_list",
                            name="list_sections",
                            arguments={},
                        ),
                        LLMToolCall(
                            call_id="call_read_method",
                            name="read_section",
                            arguments={"section_title": "Method"},
                        ),
                    ],
                ),
                LLMResponse(content="DONE\n" + FAKE_TLDR, model="provider-model"),
            ]
        )
        reader = PaperReader(
            config=AgentConfig(agent_type=AgentType.PAPER_READER, max_steps=1),
            provider=provider,
        )

        note = await reader.read(_make_test_paper())

        final_messages = provider.requests[-1].messages
        tool_messages = [message for message in final_messages if message["role"] == "tool"]
        assert [message["tool_call_id"] for message in tool_messages] == [
            "call_list",
            "call_read_method",
        ]
        assert "step budget" in str(tool_messages[-1]["content"]).lower()
        assert reader.trace.step_count == 1
        assert "attention" in note.tldr.lower()

    @pytest.mark.asyncio
    async def test_search_result_uses_the_matching_section_title(self) -> None:
        reader = _setup_reader(FakeLLMProvider(), _make_test_paper())
        await reader.setup()

        observation = await reader.observe(
            Action(
                id="call_search_metric",
                tool_name="search_paper",
                tool_input={"query": "94.5%"},
            )
        )

        assert "[Experiments]" in observation.content
        assert "[Abstract]" not in observation.content

    @pytest.mark.asyncio
    async def test_unknown_section_returns_a_matching_tool_error(self) -> None:
        reader = _setup_reader(FakeLLMProvider(), _make_test_paper())
        await reader.setup()

        observation = await reader.observe(
            Action(
                id="call_missing_section",
                tool_name="read_section",
                tool_input={"section_title": "Limitations"},
            )
        )

        assert observation.is_error
        assert "not found" in (observation.error or "").lower()
        assert reader._conversation[-1]["tool_call_id"] == "call_missing_section"

    @pytest.mark.asyncio
    async def test_invalid_final_json_is_a_failed_task(self) -> None:
        provider = FakeLLMProvider(responses=["DONE\nnot-json"])
        reader = PaperReader(
            config=AgentConfig(agent_type=AgentType.PAPER_READER, max_steps=1),
            provider=provider,
        )

        with pytest.raises(RuntimeError, match="Invalid PaperNote JSON"):
            await reader.read(_make_test_paper())

    @pytest.mark.asyncio
    async def test_empty_final_object_is_not_published_as_a_note(self) -> None:
        provider = FakeLLMProvider(responses=["DONE\n{}"])
        reader = PaperReader(
            config=AgentConfig(agent_type=AgentType.PAPER_READER, max_steps=1),
            provider=provider,
        )

        with pytest.raises(RuntimeError, match="must not be empty"):
            await reader.read(_make_test_paper())
