# P1 Quick Start

P1 provides a local paper-reading workflow: `PaperPipeline` parses a PDF,
chunks its sections, and sends the structured paper to `PaperReader`.

## Offline deterministic run

The repository example uses a fake provider and needs no API key:

```bash
uv run python examples/read_paper.py
```

The same workflow is available from Python with any `BaseProvider`:

```python
from repro_forge.paper import PaperPipeline

pipeline = PaperPipeline(provider=my_provider)
note = await pipeline.read_pdf("paper.pdf")
print(note.title)
print(note.summary())
```

## Real PDF and OpenAI-compatible provider

Install the optional integrations and configure the provider:

```bash
uv sync --locked --extra pdf --extra openai --group dev
$env:OPENAI_API_KEY = "..."       # PowerShell
# export OPENAI_API_KEY=...       # Bash
uv run repro-forge read-pdf paper.pdf --output note.json
```

`OPENAI_BASE_URL` can point to a compatible service such as DeepSeek, Qwen,
vLLM, or Ollama. `OPENAI_MODEL` selects the model and defaults to `gpt-4o`.

With a native DeepSeek key, no OpenAI variables are required:

```powershell
$env:DEEPSEEK_API_KEY = "..."
uv run repro-forge read-pdf paper.pdf --output note.json
```

The CLI defaults to `https://api.deepseek.com` and `deepseek-chat`; override
them with `DEEPSEEK_BASE_URL` and `DEEPSEEK_MODEL` when needed. It loads these
values from `.env` in the current working directory without overriding variables
that are already present in the process environment.

Keyless local OpenAI-compatible servers are also supported. For example:

```powershell
$env:OPENAI_BASE_URL = "http://localhost:11434/v1"
$env:OPENAI_MODEL = "llama3"
uv run repro-forge read-pdf paper.pdf --output note.json
```

## arXiv source

The Python API exposes `search_arxiv`, `fetch_arxiv`, `download_arxiv`, and
`read_arxiv` for a download-parse-read flow.
Install the separate extra before using those methods:

```bash
uv sync --locked --extra arxiv --group dev
```

P2 method extraction, knowledge-graph writes, and full reproduction remain
planned and are not part of P1.
