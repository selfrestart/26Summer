# Agents API

## `PaperReader`

`PaperReader` is the P1 ReAct agent that consumes a `Paper` and returns a
validated `PaperNote`. Inject a `BaseProvider` to keep the runtime testable:

```python
from repro_forge.agents import PaperReader

reader = PaperReader(provider=my_provider)
note = await reader.read(paper)
```

The reader exposes deterministic local tools for listing sections, reading a
section, and searching paper text. P2 agents such as `Methodologist` are not
implemented yet.

## Configuration defaults

When no `AgentConfig` is provided, `PaperReader` uses:

| Field | Default |
|---|---|
| `agent_type` | `paper_reader` |
| `model` | Provider model, otherwise `gpt-4o` |
| `max_steps` | `12` |
| `temperature` | `0.0` |
| chunk budget | `4000` estimated tokens |

The agent's `max_steps` is still capped by the `TaskSpec.max_steps` passed to
the P0 runtime. A long paper may therefore need a larger budget, but increasing
it also increases latency and model cost.

## Output contract

`read()` returns a Pydantic `PaperNote`, not raw model text. It adds source
metadata (`title`, `paper_id`, `arxiv_id`), the ordered `reading_trace`, and
the accumulated provider token usage after finalization. Inspect
`reader.trace.steps` when you need per-step thoughts, actions, observations or
usage.

## Tool error behavior

Malformed tool arguments return an error `Observation` and a `role=tool`
message. The model can correct the call on a later step. Unknown sections and
out-of-range chunk indexes include available titles/ranges; they are not
silently converted to the first section.
