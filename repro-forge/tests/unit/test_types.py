"""Tests for the core type system."""

from repro_forge.core.types import Action
from repro_forge.core.types import AgentConfig
from repro_forge.core.types import AgentType
from repro_forge.core.types import Message
from repro_forge.core.types import MessageRole
from repro_forge.core.types import Observation
from repro_forge.core.types import TaskResult
from repro_forge.core.types import TaskSpec
from repro_forge.core.types import Thought
from repro_forge.core.types import TraceStep
from repro_forge.core.types import new_id


class TestIdentifiers:
    def test_new_id_default(self) -> None:
        uid = new_id()
        assert len(uid) == 12
        assert uid.isalnum()

    def test_new_id_with_prefix(self) -> None:
        uid = new_id("task")
        assert uid.startswith("task_")
        assert len(uid) == 17  # "task_" + 12 hex chars

    def test_new_id_uniqueness(self) -> None:
        ids = {new_id() for _ in range(100)}
        assert len(ids) == 100


class TestMessage:
    def test_create_message(self) -> None:
        msg = Message(role=MessageRole.USER, content="hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "hello"
        assert msg.id.startswith("msg_")

    def test_message_content_coercion(self) -> None:
        msg = Message(role=MessageRole.SYSTEM, content=None)  # type: ignore[arg-type]
        assert msg.content == ""


class TestThought:
    def test_create_thought(self) -> None:
        t = Thought(content="I should search for papers")
        assert t.confidence == 1.0
        assert t.references == []

    def test_thought_with_references(self) -> None:
        t = Thought(
            content="Based on prior work",
            confidence=0.8,
            references=["arXiv:1234.5678"],
        )
        assert len(t.references) == 1
        assert t.confidence == 0.8


class TestAction:
    def test_create_action(self) -> None:
        a = Action(tool_name="search", tool_input={"query": "attention"})
        assert a.tool_name == "search"
        assert a.tool_input["query"] == "attention"
        assert a.id.startswith("act_")


class TestObservation:
    def test_create_observation(self) -> None:
        obs = Observation(action_id="act_abc", content="found 5 papers")
        assert obs.is_error is False
        assert obs.summary == "found 5 papers"

    def test_observation_error(self) -> None:
        obs = Observation(action_id="act_abc", content="", error="timeout")
        assert obs.is_error is True
        assert obs.summary.startswith("[ERROR]")


class TestTraceStep:
    def test_empty_step(self) -> None:
        step = TraceStep(step_index=0)
        assert step.step_index == 0
        assert step.thought is None
        assert step.action is None
        assert step.observation is None


class TestTaskSpec:
    def test_create_task(self) -> None:
        task = TaskSpec(title="test", description="desc")
        assert task.id.startswith("task_")
        assert task.max_steps == 15
        assert task.deadline_seconds is None


class TestTaskResult:
    def test_success_result(self) -> None:
        result = TaskResult(
            task_id="task_123",
            status="success",
            output={"key": "value"},
        )
        assert result.status == "success"
        assert result.error_message is None

    def test_failure_result(self) -> None:
        result = TaskResult(
            task_id="task_123",
            status="failed",
            error_message="something went wrong",
        )
        assert result.status == "failed"
        assert result.error_message == "something went wrong"


class TestAgentConfig:
    def test_default_config(self) -> None:
        config = AgentConfig(agent_type=AgentType.PAPER_READER)
        assert config.agent_type == AgentType.PAPER_READER
        assert config.model == "gpt-4o"
        assert config.temperature == 0.0
        assert config.max_steps == 15
