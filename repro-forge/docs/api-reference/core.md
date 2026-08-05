# Core API

P1 reuses the P0 runtime contracts rather than defining a second execution
model. The most important dependency direction is:

```text
TaskSpec → BaseAgent.run() → Thought → Action → Observation → TaskResult
                                      ↘ AgentTrace / TraceStep
```

## Runtime

::: repro_forge.core.base

## Types

::: repro_forge.core.types

## Provider contracts

::: repro_forge.providers.base

## Which type to use?

| Need | Type |
|---|---|
| Define a user task | `TaskSpec` |
| Configure an agent | `AgentConfig` |
| Represent model reasoning | `Thought` |
| Represent a tool decision | `Action` |
| Represent tool output/error | `Observation` |
| Inspect one run | `AgentTrace` / `TraceStep` |
| Return success/failure | `TaskResult` |
| Adapt an LLM backend | `BaseProvider` |

`BaseAgent.run()` catches exceptions and returns a failed `TaskResult`; the
streaming method intentionally re-raises execution errors after updating the
trace. Concrete agents should implement the five abstract hooks documented in
the generated API.

## P1 usage example

```python
from repro_forge.agents import PaperReader
from repro_forge.core.types import AgentConfig, AgentType

config = AgentConfig(
    agent_type=AgentType.PAPER_READER,
    model="deepseek-chat",
    max_steps=8,
    temperature=0.0,
)
reader = PaperReader(config=config, provider=provider)
note = await reader.read(paper)
print(reader.trace.step_count, note.total_tokens_used)
```
