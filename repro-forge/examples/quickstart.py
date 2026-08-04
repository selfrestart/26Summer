"""Quickstart example for ReproForge.

This script demonstrates the basic usage of the ReproForge type system
and agent framework. It runs without any LLM API keys by using the
FakeLLMProvider from the test suite.

Usage:
    uv run python examples/quickstart.py
"""

from __future__ import annotations

import asyncio

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


class EchoProvider(BaseProvider):
    """Minimal provider that echoes the last user message."""

    def __init__(self) -> None:
        super().__init__(model="echo")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        last = request.messages[-1] if request.messages else {}
        content = last.get("content", "no content")
        return LLMResponse(content=str(content), model=self.model)

    async def generate_stream(self, request: LLMRequest):  # type: ignore[override]
        response = await self.generate(request)
        for word in response.content.split():
            yield word + " "

    @property
    def provider_name(self) -> str:
        return "echo"


async def main() -> None:
    print("=== ReproForge Quickstart ===\n")

    # 1. Create a task
    task = TaskSpec(
        title="Demo task",
        description="A minimal demonstration of the type system.",
    )
    print(f"Task created: {task.id}")
    print(f"  Title: {task.title}")
    print(f"  Max steps: {task.max_steps}")

    # 2. Create an agent config
    config = AgentConfig(
        agent_type=AgentType.PAPER_READER,
        model="echo",
        max_steps=5,
    )
    print(f"\nAgent config: {config.agent_type.value}")
    print(f"  Model: {config.model}")
    print(f"  Max steps: {config.max_steps}")

    # 3. Simulate a ReAct cycle
    print("\n--- Simulating ReAct cycle ---")
    thought = Thought(content="I should read the abstract first.")
    print(f"  Thought: {thought.content}")

    action = Action(
        tool_name="read_section",
        tool_input={"section": "abstract"},
        reasoning="The abstract summarizes the paper.",
    )
    print(f"  Action: {action.tool_name}({action.tool_input})")

    observation = Observation(
        action_id=action.id,
        content="This paper proposes a novel attention mechanism...",
    )
    print(f"  Observation: {observation.summary}")

    # 4. Test the EchoProvider
    print("\n--- Testing EchoProvider ---")
    provider = EchoProvider()
    response = await provider.generate(
        LLMRequest(messages=[{"role": "user", "content": "Hello, ReproForge!"}])
    )
    print("  Request: Hello, ReproForge!")
    print(f"  Response: {response.content}")

    # 5. Create a task result
    result = TaskResult(
        task_id=task.id,
        status="success",
        output={"summary": "Demo completed successfully."},
    )
    print("\n--- Result ---")
    print(f"  Task ID: {result.task_id}")
    print(f"  Status: {result.status}")
    print(f"  Output: {result.output}")

    print("\n=== Quickstart complete ===")


if __name__ == "__main__":
    asyncio.run(main())
