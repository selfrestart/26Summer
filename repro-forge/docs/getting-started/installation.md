# Installation

ReproForge supports Python 3.11, 3.12, and 3.13 and uses
[uv](https://docs.astral.sh/uv/) for locked dependency management. The
repository is an umbrella project: the Python package lives in
`26Summer/repro-forge`, while the GitHub repository is `selfrestart/26Summer`.

P0 supplies the runtime and quality tooling. P1 supplies the paper-reading
vertical slice. P2-P8 folders and services are not required for the installation
below and are not enabled by it.

```bash
git clone https://github.com/selfrestart/26Summer.git
cd 26Summer/repro-forge
uv sync --locked --group dev
```

On Windows PowerShell, run the same commands. If `uv` is not on PATH, install
it from the official documentation and restart the shell. Do not use a virtual
environment created by a different Python installation without first checking
that its interpreter is Python 3.11–3.13.

The core package, P0 runtime, schemas, chunker, and deterministic tests work
without external services. Install only the P1 integrations you need:

```bash
uv sync --locked --extra pdf --group dev       # PyMuPDF local PDF parsing
uv sync --locked --extra arxiv --group dev     # arXiv search/download
uv sync --locked --extra openai --group dev    # OpenAI-compatible LLM API
```

The extras are independent. Typical combinations are:

| Goal | Command |
|---|---|
| Offline schemas/tests | `uv sync --locked --group dev` |
| Read a local text PDF with a remote LLM | `uv sync --locked --extra pdf --extra openai --group dev` |
| Search/download arXiv papers | `uv sync --locked --extra arxiv --group dev` |
| Develop every declared integration | `uv sync --locked --extra all --group dev` |

`all` installs declared dependencies, but it does not make P2-P8 features
implemented. It only prepares the environment for future work.

Verify the installation:

```bash
uv run python -c "from repro_forge.paper import PaperPipeline; print(PaperPipeline)"
uv run repro-forge --version
uv run repro-forge capabilities
uv run pytest -q
```

Expected package-level checks are:

```powershell
uv run python -c "import repro_forge; print(repro_forge.__version__)"
uv run python -c "from repro_forge.paper import Paper, PaperChunker, PaperPipeline; print('P1 imports ok')"
uv run repro-forge capabilities
```

Optional integrations are imported lazily. If an extra is missing, the error
names the exact extra and installation command instead of breaking core
imports.

## Installation failure checklist

1. Confirm `uv --version` works in the current shell.
2. Confirm `uv python find` points to a supported interpreter.
3. Run `uv sync --locked` from `repro-forge`, not the umbrella root.
4. If a PDF/arXiv/provider import fails, install only the named extra.
5. Re-run `uv run ...` so the project environment, not global Python, is used.

The package import path is `repro_forge` (underscore); the distribution and
CLI names are `repro-forge` (hyphen). The umbrella GitHub repository remains
`26Summer`.
