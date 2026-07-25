"""Core agent runtime abstractions.

This module provides the base agent class and execution loop primitives
that all specialized agents inherit from.
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from collections.abc import AsyncIterator

from repro_forge.core.types import Action
from repro_forge.core.types import AgentConfig
from repro_forge.core.types import AgentState
from repro_forge.core.types import AgentTrace
from repro_forge.core.types import AgentType
from repro_forge.core.types import Observation
from repro_forge.core.types import TaskResult
from repro_forge.core.types import TaskSpec
from repro_forge.core.types import TaskStatus
from repro_forge.core.types import Thought
from repro_forge.core.types import TraceStep
from repro_forge.providers.base import BaseProvider


class BaseAgent(ABC):
    """Abstract base for all agents in the ReproForge framework.

    Each specialized agent (PaperReader, Methodologist, CodeForger, etc.)
    inherits from this class and implements the agent-specific reasoning
    and action logic.

    The agent follows a ReAct-inspired loop: Think → Act → Observe → (repeat).
    """

    def __init__(
        self,
        config: AgentConfig,
        provider: BaseProvider,
    ) -> None:
        self.config = config
        self.provider = provider
        self._state = AgentState.IDLE
        self._trace = AgentTrace(
            agent_id=config.agent_id,
            agent_type=config.agent_type,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def trace(self) -> AgentTrace:
        return self._trace

    @property
    def agent_type(self) -> AgentType:
        return self.config.agent_type

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def setup(self) -> None:
        """Initialize resources before execution. Override in subclasses."""
        self._state = AgentState.IDLE

    async def teardown(self) -> None:
        """Release resources after execution. Override in subclasses."""
        return

    # ------------------------------------------------------------------
    # Core loop
    # ------------------------------------------------------------------

    async def run(self, task: TaskSpec) -> TaskResult:
        """Execute a task synchronously (non-streaming).

        Orchestrates the full think-act-observe loop until the task
        completes, fails, or exceeds the step budget.

        Args:
            task: The task specification to execute.

        Returns:
            A TaskResult containing the output, status, and execution trace.
        """
        await self.setup()
        self._state = AgentState.THINKING
        step_index = 0

        try:
            while step_index < self.config.max_steps:
                # Think
                thought = await self.think(task)
                step = TraceStep(
                    step_index=step_index,
                    thought=thought,
                )

                # Act
                self._state = AgentState.ACTING
                action = await self.act(thought)
                step.action = action

                # Observe
                self._state = AgentState.OBSERVING
                observation = await self.observe(action)
                step.observation = observation

                self._trace.steps.append(step)
                step_index += 1

                # Decide whether to continue
                if await self.should_stop(observation):
                    self._state = AgentState.DONE
                    break

            result = await self.finalize(task)
            self._trace.final_state = self._state
            return result

        except Exception as exc:
            self._state = AgentState.ERROR
            self._trace.final_state = self._state
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error_message=str(exc),
                trace=self._trace,
            )
        finally:
            await self.teardown()

    # ------------------------------------------------------------------
    # Abstract methods — subclasses MUST implement
    # ------------------------------------------------------------------

    @abstractmethod
    async def think(self, task: TaskSpec) -> Thought:
        """Produce the next reasoning step."""

    @abstractmethod
    async def act(self, thought: Thought) -> Action:
        """Decide what action to take based on reasoning."""

    @abstractmethod
    async def observe(self, action: Action) -> Observation:
        """Execute the action and collect the observation."""

    @abstractmethod
    async def should_stop(self, observation: Observation) -> bool:
        """Determine whether the execution loop should terminate."""

    @abstractmethod
    async def finalize(self, task: TaskSpec) -> TaskResult:
        """Produce the final result after the loop completes."""

    # ------------------------------------------------------------------
    # Streaming variant (optional override)
    # ------------------------------------------------------------------

    async def stream(self, task: TaskSpec) -> AsyncIterator[TraceStep]:
        """Execute a task with streaming step-by-step output.

        Yields each TraceStep as it completes. The default implementation
        wraps :meth:`run` but subclasses can override for true streaming.
        """
        await self.setup()
        self._state = AgentState.THINKING

        for step_index in range(self.config.max_steps):
            step = TraceStep(step_index=step_index)

            step.thought = await self.think(task)
            self._state = AgentState.ACTING

            step.action = await self.act(step.thought)
            self._state = AgentState.OBSERVING

            step.observation = await self.observe(step.action)
            self._trace.steps.append(step)
            yield step

            if await self.should_stop(step.observation):
                self._state = AgentState.DONE
                break

        await self.teardown()
