# P1 Quick Start

P1 provides a local paper-reading workflow: `PaperPipeline` parses a PDF,
chunks its sections, and sends the structured paper to `PaperReader`. The
output is a reading note, not a reproducibility report.

## Choose a path

| You have | Start with |
|---|---|
| No API key or PDF | Offline deterministic run |
| A local text PDF and DeepSeek/OpenAI key | Real PDF path |
| An arXiv identifier | arXiv source path |
| A serialized `Paper` JSON | `read-json` in the CLI reference |

## Offline deterministic run

The repository example uses a fake provider and needs no API key:

```bash
uv run python examples/read_paper.py
```

The example uses the repository's `FakeLLMProvider`, so it is safe to run in a
network-isolated environment. It validates the domain model, chunking and
PaperReader lifecycle without claiming model quality.

The same workflow is available from Python with any `BaseProvider`:

```python
from repro_forge.paper import PaperPipeline

pipeline = PaperPipeline(provider=my_provider)
note = await pipeline.read_pdf("paper.pdf")
print(note.title)
print(note.summary())
```

The code is asynchronous because the Provider boundary is asynchronous. In a
script, wrap the call with `asyncio.run`; in a notebook, await it directly.

## Real PDF and OpenAI-compatible provider

Install the optional integrations and configure the provider:

```bash
uv sync --locked --extra pdf --extra openai --group dev
$env:OPENAI_API_KEY = "..."       # PowerShell
# export OPENAI_API_KEY=...       # Bash
uv run repro-forge read-pdf paper.pdf --output note.json
```

The `pdf` extra is required for parsing and the `openai` extra is required for
`OpenAIProvider`. A valid text PDF is required; scanned-image PDFs may produce
empty text because P1 has no OCR.

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

P2 evidence-grounded method extraction remains planned and is not part of P1.
Knowledge-graph writes remain P5, while code generation and experiment
execution begin in P3. See the [P2 Implementation Plan](../P2-IMPLEMENTATION-PLAN.md).

## Inspect the result

```powershell
Get-Content .\note.json -Encoding utf8 | Select-Object -First 60
```

Important fields are `tldr`, `contributions`, `methodology_summary`,
`key_findings`, `strengths`, `weaknesses`, `questions`, `reading_trace`, and
`total_tokens_used`. A successful command only proves that a note was
produced; factual correctness still requires human review against the source
paper.

## Next troubleshooting step

If the command fails, isolate the layer in this order:

1. `uv run repro-forge capabilities` — package/CLI installation;
2. `PDFParser().parse(path)` — file and text extraction;
3. Fake Provider + `PaperReader.read(paper)` — agent/tool behavior;
4. real Provider — credentials, endpoint, model, quota and network.

See [P1 Implementation Guide](../P1-IMPLEMENTATION-GUIDE.md) for the complete
decision tree.
