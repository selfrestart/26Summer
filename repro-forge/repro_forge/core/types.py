"""Core type definitions for the ReproForge agent framework.

This module defines the fundamental data structures used throughout the system:
messages exchanged between agents, actions they can take, observations they
receive, and the metadata that tracks their execution.
"""

from __future__ import annotations

import uuid
from datetime import UTC
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------

AgentId = str
TaskId = str
ToolId = str
MemoryId = str
RunId = str


def new_id(prefix: str = "") -> str:
    """Generate a unique short identifier with an optional prefix."""
    uid = uuid.uuid4().hex[:12]
    return f"{prefix}_{uid}" if prefix else uid


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class MessageRole(StrEnum):
    """Roles in the agent conversation loop."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    AGENT = "agent"


class AgentState(StrEnum):
    """Lifecycle states of an agent."""

    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    WAITING = "waiting"
    DONE = "done"
    ERROR = "error"


class AgentType(StrEnum):
    """Registered agent variants."""

    PAPER_READER = "paper_reader"
    METHODOLOGIST = "methodologist"
    MATH_CHECKER = "math_checker"
    CODE_FORGER = "code_forger"
    EXPERIMENTOR = "experimentor"
    VERIFIER = "verifier"
    SURVEY_SCRIBE = "survey_scribe"


class TaskStatus(StrEnum):
    """Status of a task in the pipeline."""

    PENDING = "pending"
    DELEGATED = "delegated"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


class FunctionCall(BaseModel):
    """A tool/function call requested by the agent."""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    call_id: str = Field(default_factory=lambda: new_id("call"))


class FunctionResult(BaseModel):
    """Result returned by a tool/function execution."""

    call_id: str
    name: str
    content: str
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    """A single message in the agent's conversation. Compatible with the
    OpenAI-style message format for seamless provider interchange."""

    role: MessageRole
    content: str | list[dict[str, Any]]
    name: str | None = None
    function_call: FunctionCall | None = None
    tool_calls: list[FunctionCall] | None = None
    tool_call_id: str | None = None
    id: str = Field(default_factory=lambda: new_id("msg"))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("content", mode="before")
    @classmethod
    def _coerce_content(cls, v: object) -> str | list[dict[str, Any]]:
        if v is None:
            return ""
        return v  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Actions & Observations (ReAct loop primitives)
# ---------------------------------------------------------------------------


class Thought(BaseModel):
    """The agent's reasoning step before taking action."""

    content: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    references: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Action(BaseModel):
    """An action the agent has decided to take."""

    tool_name: str
    tool_input: dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""
    id: str = Field(default_factory=lambda: new_id("act"))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Observation(BaseModel):
    """The result observed after executing an action."""

    action_id: str
    content: str
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_error(self) -> bool:
        return self.error is not None

    @property
    def summary(self) -> str:
        """Brief summary for logging."""
        if self.error:
            return f"[ERROR] {self.error[:120]}"
        return self.content[:120].replace("\n", " ")


# ---------------------------------------------------------------------------
# Traces & Logs
# ---------------------------------------------------------------------------


class TraceStep(BaseModel):
    """A single step in the agent's execution trace (for observability)."""

    step_index: int
    thought: Thought | None = None
    action: Action | None = None
    observation: Observation | None = None
    token_usage: dict[str, int] = Field(default_factory=dict)
    latency_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentTrace(BaseModel):
    """Full execution trace for a single agent run."""

    run_id: str = Field(default_factory=lambda: new_id("run"))
    agent_id: AgentId
    agent_type: AgentType
    steps: list[TraceStep] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    final_state: AgentState = AgentState.IDLE
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    @property
    def elapsed_ms(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds() * 1000

    @property
    def step_count(self) -> int:
        return len(self.steps)


# ---------------------------------------------------------------------------
# Task / Pipeline metadata
# ---------------------------------------------------------------------------


class TaskSpec(BaseModel):
    """Specification of a task to be executed by an agent or team."""

    id: str = Field(default_factory=lambda: new_id("task"))
    title: str
    description: str
    input: dict[str, Any] = Field(default_factory=dict)
    agent_type: AgentType | None = None
    parent_task_id: str | None = None
    deadline_seconds: float | None = None
    max_steps: int = 15
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskResult(BaseModel):
    """Result of a completed or failed task."""

    task_id: str
    status: TaskStatus
    output: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    trace: AgentTrace | None = None
    subtask_results: list[TaskResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class AgentConfig(BaseModel):
    """Configuration for an agent instance."""

    agent_id: AgentId = Field(default_factory=lambda: new_id("agent"))
    agent_type: AgentType
    model: str = "gpt-4o"
    system_prompt: str = ""
    max_steps: int = 15
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    tools: list[str] = Field(default_factory=list)
    memory_ids: list[MemoryId] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineConfig(BaseModel):
    """Configuration for a multi-agent execution pipeline."""

    name: str
    description: str = ""
    agents: list[AgentConfig] = Field(default_factory=list)
    max_total_steps: int = 50
    timeout_seconds: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
