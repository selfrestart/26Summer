# P1-P3 Configuration

Core configuration is contained in `pyproject.toml`; P1/P3 integrations are
optional and activate only when their extra is installed. Runtime credentials
are read from process environment variables and, for the CLI only, a `.env`
file in the current working directory.

| Configuration | P1 behavior |
|---|---|
| Python | 3.11-3.13 supported; `.python-version` selects 3.13 locally |
| Dependencies | `uv.lock` is authoritative for development and CI |
| PDF | Install `uv sync --extra pdf`; uses PyMuPDF lazily |
| arXiv | Install `uv sync --extra arxiv`; client supports search/fetch/download |
| LLM | Install `uv sync --extra openai`; use an OpenAI-compatible endpoint |
| Model | `OPENAI_MODEL` (default `gpt-4o`) or `DEEPSEEK_MODEL` (default `deepseek-chat`) |
| Endpoint | `OPENAI_BASE_URL` or `DEEPSEEK_BASE_URL` (default `https://api.deepseek.com`) |
| Credentials | `OPENAI_API_KEY` or `DEEPSEEK_API_KEY` for remote endpoints; local compatible endpoints may run without a key |
| Formatting and lint | Ruff, targeting the minimum supported Python 3.11 |
| Type checking | mypy strict mode |
| Tests | pytest with branch coverage and a 65% minimum |
| Documentation | MkDocs Material |
| P3 Docker image | `REPROFORGE_P3_PYTHON_CPU_IMAGE`; exact reviewed `repository@sha256:...` only |

## Configuration precedence

For the CLI, the effective value is resolved in this order:

```text
explicit OpenAIProvider(...) argument
    > existing process environment variable
    > current-directory .env
    > provider/CLI default
```

`load_dotenv(..., override=False)` means a `.env` value never overwrites a
value already exported by the shell. `OPENAI_API_KEY` takes precedence over
`DEEPSEEK_API_KEY`; when OpenAI is absent, native DeepSeek variables are used.

## Provider scenarios

| Scenario | Required variables | Effective endpoint/model |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `OPENAI_BASE_URL` or SDK default; `OPENAI_MODEL` or `gpt-4o` |
| DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_BASE_URL` or `https://api.deepseek.com`; `DEEPSEEK_MODEL` or `deepseek-chat` |
| Local Ollama/vLLM | `OPENAI_BASE_URL`, `OPENAI_MODEL` | no key; only local/private endpoints are accepted by CLI |
| Python-only custom provider | inject `BaseProvider` | Provider decides its own configuration |

Do not set both provider keys casually: the CLI intentionally selects the
OpenAI branch first. To test DeepSeek deterministically, unset
`OPENAI_API_KEY` in the current process before running the command.

## `.env` example

```dotenv
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

Keep `.env` local. Use `.env.example` as the shareable template and rotate a
credential immediately if it is pasted into an issue, log, commit, or chat.

## Reserved configuration by phase

The deterministic examples and tests inject a fake provider and need no API
key. Variables in `.env.example` are staged as follows:

| Variables | Phase | Purpose |
|-----------|-------|---------|
| `EXECUTION_BACKEND` | P3 | CLI/config default naming; generated bundles support `dryrun`/`docker`, local subprocess is fixture-only |
| `REPROFORGE_P3_PYTHON_CPU_IMAGE` | P3 | Exact reviewed Docker image digest; backend never pulls mutable tags automatically |
| `MLFLOW_*` | Deferred | MLflow is not the P3 source of truth; current records use `ExperimentRun` JSON |
| `CHROMA_*`, `NEO4J_*` | P5 | Rebuildable semantic and graph indexes, including explicit image references |
| `SERVER_*`, CORS settings | P6 | FastAPI jobs/SSE service |
| `OTEL_*`, `EVALUATION_*` | P8 | Telemetry, benchmarks, cost and release gates |

Setting a variable does not by itself transfer P3's acceptance evidence to a new
runtime. Installing the Docker extra or setting an image digest still requires a
running daemon, a locally present reviewed image, and rerunning the real security smoke. Later services
also require their code, tests, adapters, migrations, user entry point, and phase gate.

Future local services use conservative defaults: P6 binds to `127.0.0.1` with one
worker and CORS disabled; `compose.future.yml` binds database/telemetry ports to
loopback and requires an explicit `NEO4J_PASSWORD`. P7 is still required before
remote or multi-tenant exposure. It also requires explicit `NEO4J_IMAGE`,
`CHROMA_IMAGE`, and `JAEGER_IMAGE` references rather than silently using
`latest`. P5/P8 readiness reviews must record compatible versions and digests;
P7 production gates require digest pinning, SBOMs, and image-policy checks.
