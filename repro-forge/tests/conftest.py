"""Shared test fixtures, mocks, and utilities for ReproForge tests.

This module provides:

- FakeLLMProvider: Deterministic mock for LLM calls (fast, no API needed)
- FakeAgent: Minimal agent implementation for testing the base class
- Common fixtures: temp directories, sample paper data, etc.
"""

from __future__ import annotations

from typing import Any

import pytest

from repro_forge.core.base import BaseAgent
from repro_forge.core.types import Action
from repro_forge.core.types import AgentConfig
from repro_forge.core.types import AgentType
from repro_forge.core.types import Observation
from repro_forge.core.types import TaskResult
from repro_forge.core.types import TaskSpec
from repro_forge.core.types import Thought
from repro_forge.providers.base import BaseProvider
from repro_forge.providers.base import LLMRequest
from repro_forge.providers.base import LLMResponse

# ---------------------------------------------------------------------------
# Fake Provider
# ---------------------------------------------------------------------------


class FakeLLMProvider(BaseProvider):
    """Deterministic mock provider that returns canned responses.

    Use this in unit tests to avoid real LLM API calls. You can pre-configure
    the responses via ``set_responses()`` or use the default echo behavior.
    """

    def __init__(self, responses: list[str] | None = None) -> None:
        super().__init__(model="fake-model")
        self._responses = responses or ["OK"]
        self._idx = 0
        self._requests: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self._requests.append(request)
        content = self._responses[self._idx % len(self._responses)]
        self._idx += 1
        return LLMResponse(
            content=content,
            model=self.model,
            finish_reason="stop",
            usage={
                "prompt_tokens": 10,
                "completion_tokens": len(content.split()),
                "total_tokens": 10 + len(content.split()),
            },
        )

    async def generate_stream(self, request: LLMRequest) -> Any:
        response = await self.generate(request)
        for chunk in response.content.split():
            yield chunk + " "

    @property
    def provider_name(self) -> str:
        return "fake"

    def set_responses(self, responses: list[str]) -> None:
        """Set the sequence of responses and reset the index."""
        self._responses = responses
        self._idx = 0

    @property
    def last_request(self) -> LLMRequest | None:
        """The most recent request, for assertions."""
        return self._requests[-1] if self._requests else None

    @property
    def request_count(self) -> int:
        return len(self._requests)


# ---------------------------------------------------------------------------
# Fake Agent
# ---------------------------------------------------------------------------


class FakeAgent(BaseAgent):
    """Minimal concrete agent for testing the BaseAgent lifecycle.

    Runs through a fixed number of steps and collects actions in a list
    for test assertions.
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        provider: BaseProvider | None = None,
        max_steps: int = 3,
    ) -> None:
        super().__init__(
            config=config or AgentConfig(agent_type=AgentType.PAPER_READER),
            provider=provider or FakeLLMProvider(),
        )
        self.config.max_steps = max_steps
        self.step_count = 0
        self.actions: list[str] = []

    async def think(self, task: TaskSpec) -> Thought:
        return Thought(content=f"think step {self.step_count}")

    async def act(self, thought: Thought) -> Action:
        action = Action(
            tool_name="test_tool",
            tool_input={"step": self.step_count},
            reasoning=thought.content,
        )
        self.actions.append(f"step_{self.step_count}")
        self.step_count += 1
        return action

    async def observe(self, action: Action) -> Observation:
        return Observation(
            action_id=action.id,
            content=f"observed step {action.tool_input.get('step', '?')}",
        )

    async def should_stop(self, observation: Observation) -> bool:
        return self.step_count >= self.config.max_steps

    async def finalize(self, task: TaskSpec) -> TaskResult:
        return TaskResult(
            task_id=task.id,
            status="success",
            output={"steps": self.actions},
            trace=self._trace,
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_provider() -> FakeLLMProvider:
    """A FakeLLMProvider with default responses."""
    return FakeLLMProvider(responses=["echo response"])


@pytest.fixture
def fake_agent(fake_provider: FakeLLMProvider) -> FakeAgent:
    """A FakeAgent with default 3-step configuration."""
    return FakeAgent(provider=fake_provider, max_steps=3)


@pytest.fixture
def sample_task() -> TaskSpec:
    """A minimal task for testing."""
    return TaskSpec(
        title="test task",
        description="A task used in tests",
        input={"key": "value"},
    )


@pytest.fixture
def sample_pdf_path(tmp_path: Any) -> str:
    """Path to a minimal PDF file for testing the paper pipeline.

    Note: this creates a placeholder; real PDF parsing tests require
    a valid PDF file or mock.
    """
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_text(
        """%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
190
%%EOF"""
    )
    return str(pdf_path)


@pytest.fixture
def simple_config() -> AgentConfig:
    """A minimal agent configuration for testing."""
    return AgentConfig(
        agent_type=AgentType.PAPER_READER,
        model="gpt-4o",
        max_steps=5,
    )
