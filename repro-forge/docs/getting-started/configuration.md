# P1 Configuration

Core configuration is contained in `pyproject.toml`; P1 integrations are
optional and activate only when their extra is installed.

| Configuration | P1 behavior |
|---|---|
| Python | 3.11-3.13 supported; `.python-version` selects 3.13 locally |
| Dependencies | `uv.lock` is authoritative for development and CI |
| PDF | Install `uv sync --extra pdf`; uses PyMuPDF lazily |
| arXiv | Install `uv sync --extra arxiv`; client supports search/fetch/download |
| LLM | Install `uv sync --extra openai`; use an OpenAI-compatible endpoint |
| Model | `OPENAI_MODEL` (default `gpt-4o`) or `DEEPSEEK_MODEL` (default `deepseek-chat`) |
| Endpoint | `OPENAI_BASE_URL` or `DEEPSEEK_BASE_URL` (default `https://api.deepseek.com`) |
| Credentials | `OPENAI_API_KEY` or `DEEPSEEK_API_KEY`, required only for real LLM calls |
| Formatting and lint | Ruff, targeting the minimum supported Python 3.11 |
| Type checking | mypy strict mode |
| Tests | pytest with branch coverage and a 65% minimum |
| Documentation | MkDocs Material |

The deterministic examples and tests inject a fake provider and need no API
key. P2+ storage, execution, observability, API, and knowledge-graph settings
remain reserved for later phases.
