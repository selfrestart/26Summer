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
section, and searching paper text.

## `Methodologist`

`Methodologist` is the P2 ReAct agent that extracts evidence-grounded
methodology from a `Paper`, optionally using a `PaperNote` as context hints:

```python
from repro_forge.agents import Methodologist
from repro_forge.paper.extractor import PaperEvidenceView

view = PaperEvidenceView(paper)
methodologist = Methodologist(provider=my_provider)
analysis = await methodologist.analyze(view, paper_note=note)  # note optional
```

`analyze()` returns a validated `MethodAnalysis`. Evidence-bearing method,
configuration, evaluation, and reported-claim fields carry an `EvidenceRef`
(source_hash, section_id, quote, status) so downstream reproduction inputs trace
back to the original paper. Schema/evidence errors trigger one repair attempt;
a second failure raises `RuntimeError` instead of producing a fake analysis.
The constructor requires a provider and raises `ValueError` immediately when it
is omitted.

### Methodologist configuration defaults

| Field | Default |
|---|---|
| `agent_type` | `methodologist` |
| `model` | Injected provider model unless explicitly set in `AgentConfig` |
| `max_steps` | `15` |
| `temperature` | `0.0` |

### Methodologist tools

| Tool | Purpose |
|---|---|
| `list_sections` | View all section titles |
| `read_section(title, chunk_index=0)` | Read bounded original text |
| `search_paper(query)` | Locate hyperparameters/metrics/formulas |
| `get_paper_note` | Get P1 reading-note context hints |

Parallel native tool calls are fully answered before another assistant request,
including when a batch reaches the configured action-step boundary.

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
