"""Tests for the BaseAgent lifecycle and FakeAgent test utility."""

import pytest

from repro_forge.core.types import AgentState
from repro_forge.core.types import TaskSpec
from tests.conftest import FakeAgent
from tests.conftest import FakeLLMProvider


class TestFakeAgent:
    @pytest.mark.asyncio
    async def test_run_completes_all_steps(self, sample_task: TaskSpec) -> None:
        agent = FakeAgent(max_steps=3)
        result = await agent.run(sample_task)

        assert result.status == "success"
        assert len(agent.actions) == 3
        assert agent.actions == ["step_0", "step_1", "step_2"]
        assert agent.state == AgentState.DONE
        assert len(agent.trace.steps) == 3

    @pytest.mark.asyncio
    async def test_run_single_step(self, sample_task: TaskSpec) -> None:
        agent = FakeAgent(max_steps=1)
        result = await agent.run(sample_task)

        assert result.status == "success"
        assert len(agent.actions) == 1

    @pytest.mark.asyncio
    async def test_run_exception_handling(self, sample_task: TaskSpec) -> None:
        agent = FakeAgent(max_steps=3)

        async def _failing_think(task: TaskSpec) -> None:
            raise RuntimeError("test error")

        agent.think = _failing_think  # type: ignore[assignment]

        result = await agent.run(sample_task)
        assert result.status == "failed"
        assert result.error_message == "test error"
        assert agent.state == AgentState.ERROR
        assert agent.trace.final_state == AgentState.ERROR

    @pytest.mark.asyncio
    async def test_trace_population(self, sample_task: TaskSpec) -> None:
        agent = FakeAgent(max_steps=2)
        await agent.run(sample_task)

        trace = agent.trace
        assert len(trace.steps) == 2
        for i, step in enumerate(trace.steps):
            assert step.step_index == i
            assert step.thought is not None
            assert step.action is not None
            assert step.observation is not None


class TestFakeLLMProvider:
    @pytest.mark.asyncio
    async def test_generate_cycles_responses(self) -> None:
        provider = FakeLLMProvider(responses=["a", "b", "c"])

        from repro_forge.providers.base import LLMRequest

        r1 = await provider.generate(LLMRequest(messages=[]))
        r2 = await provider.generate(LLMRequest(messages=[]))
        r3 = await provider.generate(LLMRequest(messages=[]))
        r4 = await provider.generate(LLMRequest(messages=[]))

        assert r1.content == "a"
        assert r2.content == "b"
        assert r3.content == "c"
        assert r4.content == "a"  # wraps around

    @pytest.mark.asyncio
    async def test_request_tracking(self) -> None:
        provider = FakeLLMProvider(responses=["ok"])

        from repro_forge.providers.base import LLMRequest

        await provider.generate(LLMRequest(messages=[]))

        assert provider.request_count == 1
        assert provider.last_request is not None
