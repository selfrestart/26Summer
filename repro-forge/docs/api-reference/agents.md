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
