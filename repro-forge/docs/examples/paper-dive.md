# P1 Paper Deep-Dive

This example is covered by the P1 reading workflow. Start with the
deterministic offline script:

```powershell
uv run python examples/read_paper.py
```

For a real PDF, install the optional integrations and configure an
OpenAI-compatible provider:

```powershell
uv sync --locked --extra pdf --extra openai --group dev
$env:DEEPSEEK_API_KEY = "..."
uv run repro-forge read-pdf paper.pdf --output note.json
```

The output is a `PaperNote` containing a TL;DR, contributions, methodology
summary, key findings, strengths, weaknesses, questions, reading trace, and
token usage. Method extraction is implemented in P2; reproduction generation,
execution, and verification are planned for P3-P4.
