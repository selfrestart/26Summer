# P0 Quick Start

The current release provides typed task and Agent configuration models plus the
abstract runtime contracts used by future specialized Agents.

```python
from repro_forge.core.types import AgentConfig
from repro_forge.core.types import AgentType
from repro_forge.core.types import TaskSpec

config = AgentConfig(
    agent_type=AgentType.PAPER_READER,
    model="example-model",
    max_steps=5,
)
task = TaskSpec(
    title="Inspect a paper",
    description="P0 type-system example",
    max_steps=3,
)

print(config.agent_id)
print(task.id)
```

`BaseAgent` and `BaseProvider` are abstract contracts. Concrete paper readers,
LLM providers, and reproduction pipelines are planned for later phases.

Run the P0 verification suite with:

```bash
make check
make docs
make docker-run
```
