# Installation

ReproForge supports Python 3.11, 3.12, and 3.13 and uses
[uv](https://docs.astral.sh/uv/) for locked dependency management.

```bash
git clone https://github.com/selfrestart/26Summer.git
cd 26Summer/repro-forge
uv sync --locked --group dev
```

The core package, P0 runtime, schemas, chunker, and deterministic tests work
without external services. Install only the P1 integrations you need:

```bash
uv sync --locked --extra pdf --group dev       # PyMuPDF local PDF parsing
uv sync --locked --extra arxiv --group dev     # arXiv search/download
uv sync --locked --extra openai --group dev    # OpenAI-compatible LLM API
```

Verify the installation:

```bash
uv run python -c "from repro_forge.paper import PaperPipeline; print(PaperPipeline)"
uv run repro-forge --version
uv run repro-forge capabilities
uv run pytest -q
```

Optional integrations are imported lazily. If an extra is missing, the error
names the exact extra and installation command instead of breaking core
imports.
