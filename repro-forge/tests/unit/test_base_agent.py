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

    @pytest.mark.asyncio
    async def test_repeated_runs_receive_independent_traces(self, sample_task: TaskSpec) -> None:
        agent = FakeAgent(max_steps=1)

        first_result = await agent.run(sample_task)
        first_trace = first_result.trace
        second_result = await agent.run(sample_task)
        second_trace = second_result.trace

        assert first_trace is not None
        assert second_trace is not None
        assert first_trace.run_id != second_trace.run_id
        assert len(first_trace.steps) == 1
        assert len(second_trace.steps) == 1
        assert first_trace.end_time is not None
        assert second_trace.end_time is not None

    @pytest.mark.asyncio
    async def test_task_step_budget_limits_execution(self, sample_task: TaskSpec) -> None:
        agent = FakeAgent(max_steps=3)
        task = sample_task.model_copy(update={"max_steps": 1})

        await agent.run(task)

        assert len(agent.actions) == 1
        assert agent.state == AgentState.DONE

    @pytest.mark.asyncio
    async def test_each_think_step_reports_thinking_state(self, sample_task: TaskSpec) -> None:
        agent = FakeAgent(max_steps=2)
        original_think = agent.think
        observed_states: list[AgentState] = []

        async def _recording_think(task: TaskSpec):
            observed_states.append(agent.state)
            return await original_think(task)

        agent.think = _recording_think  # type: ignore[assignment]

        await agent.run(sample_task)

        assert observed_states == [AgentState.THINKING, AgentState.THINKING]

    @pytest.mark.asyncio
    async def test_stream_error_updates_trace_and_runs_teardown(
        self, sample_task: TaskSpec
    ) -> None:
        agent = FakeAgent(max_steps=2)
        teardown_called = False

        async def _failing_think(task: TaskSpec) -> None:
            raise RuntimeError("stream error")

        async def _tracking_teardown() -> None:
            nonlocal teardown_called
            teardown_called = True

        agent.think = _failing_think  # type: ignore[assignment]
        agent.teardown = _tracking_teardown  # type: ignore[method-assign]

        with pytest.raises(RuntimeError, match="stream error"):
            async for _ in agent.stream(sample_task):
                pass

        assert teardown_called
        assert agent.state == AgentState.ERROR
        assert agent.trace.final_state == AgentState.ERROR
        assert agent.trace.end_time is not None


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
