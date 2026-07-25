# Installation

P0 supports Python 3.11, 3.12, and 3.13. The repository uses
[uv](https://docs.astral.sh/uv/) for locked dependency management.

```bash
git clone https://github.com/selfrestart/26Summer.git
cd 26Summer/repro-forge
uv sync --locked --group dev
```

Verify the installed package:

```bash
uv run python -c "import repro_forge; print(repro_forge.__version__)"
uv run repro-forge
```

P0 does not require an LLM API key or external database. Optional dependencies
for later phases should not be installed unless you are working on those phases.
