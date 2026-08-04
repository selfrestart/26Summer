# P1 Paper Reading Implementation Plan

> **For agentic workers:** Execute this plan task-by-task with tests first and fresh verification after each behavior change.

**Goal:** Deliver a usable P1 paper-reading workflow that parses local PDFs or arXiv papers, chunks content, runs `PaperReader` with an injected or OpenAI-compatible provider, and exposes stable public imports and CLI usage.

**Architecture:** Keep P0 core abstractions unchanged as the lower layer. Add a small `PaperPipeline` orchestration layer over `PDFParser`, `ArxivClient`, `PaperChunker`, and `PaperReader`; optional third-party packages are imported lazily and produce actionable installation errors. Preserve dependency injection so tests and offline users can use a deterministic provider.

**Tech Stack:** Python 3.11+, Pydantic, pytest/pytest-asyncio, PyMuPDF (optional `pdf` extra), arxiv (optional `arxiv` extra), OpenAI SDK (optional `openai` extra), Ruff, mypy, uv.

---

### Task 1: Define the P1 public surface with failing tests

**Files:**
- Create: `tests/unit/test_public_api.py`
- Create: `tests/unit/test_pipeline.py`
- Modify: `tests/unit/test_chunker.py`

- [x] **Step 1: Write failing public-import and pipeline tests**

  Assert that `PaperReader`, `PaperPipeline`, `PDFParser`, `ArxivClient`, `OpenAIProvider`, and paper schemas are importable from their package namespaces. Add a fake provider test that calls `PaperPipeline.read(paper)` and returns a `PaperNote`. Add a regression test proving an overlong paragraph chunk retains its content and stays within the configured token budget.

- [x] **Step 2: Run the focused tests and verify they fail for missing exports/orchestration or incorrect chunk content**

  Run `uv run pytest tests/unit/test_public_api.py tests/unit/test_pipeline.py tests/unit/test_chunker.py -q` from `repro-forge`. Expected failures include missing `PaperPipeline`/exports and the long-paragraph content assertion.

### Task 2: Complete the paper domain exports and chunking contract

**Files:**
- Modify: `repro_forge/paper/__init__.py`
- Modify: `repro_forge/paper/chunker.py`
- Modify: `repro_forge/paper/parser/__init__.py`

- [x] **Step 1: Export schemas, `PaperChunker`, `PDFParser`, and `ArxivClient`**

  Keep imports lightweight; importing the parser namespace must not require PyMuPDF or arxiv to be installed.

- [x] **Step 2: Fix long-paragraph splitting**

  Include each sliced paragraph in the generated `PaperChunk.text`, preserve section headings, and calculate a positive bounded token count for every chunk. Validate constructor arguments (`max_tokens > 0`, `min_tokens >= 0`) with `ValueError`.

- [x] **Step 3: Run the focused tests and verify green**

  Run `uv run pytest tests/unit/test_public_api.py tests/unit/test_chunker.py -q`.

### Task 3: Make optional providers and parsers installable without breaking the core package

**Files:**
- Modify: `repro_forge/providers/openai_provider.py`
- Modify: `repro_forge/providers/__init__.py`
- Modify: `repro_forge/paper/parser/pdf_parser.py`
- Modify: `repro_forge/paper/parser/arxiv_api.py`

- [x] **Step 1: Add failing optional-dependency behavior tests**

  Test that constructing `OpenAIProvider` without the OpenAI extra raises an error naming `openai`; test that PDF parsing without PyMuPDF raises an error naming `pdf`; test that constructing `ArxivClient` without arxiv raises an error naming `arxiv`. Use monkeypatching so the tests are deterministic even when extras are installed.

- [x] **Step 2: Implement lazy imports and actionable errors**

  Move optional imports into constructors/methods, export `OpenAIProvider`, and keep core imports usable without optional extras. The OpenAI provider must accept `api_key`, `base_url`, and model configuration and preserve the existing unified request/response contract.

- [x] **Step 3: Run focused optional-dependency tests and the full existing suite**

  Run `uv run pytest tests/unit/test_public_api.py tests/unit/test_optional_dependencies.py tests -q` and confirm no P0 regression.

### Task 4: Implement the P1 `PaperPipeline` and PaperReader lifecycle fixes

**Files:**
- Create: `repro_forge/paper/pipeline.py`
- Modify: `repro_forge/paper/__init__.py`
- Modify: `repro_forge/agents/paper_reader.py`
- Modify: `tests/unit/test_pipeline.py`

- [x] **Step 1: Add tests for local-PDF parsing delegation, arXiv lookup/download delegation, provider injection, and repeated reads**

  Use fake parser/client/provider objects. Verify `PaperReader` stores the current paper, resets per-run conversation/sections, and returns independent traces and notes across repeated reads.

- [x] **Step 2: Implement `PaperPipeline`**

  Provide `parse_pdf(path)`, `search_arxiv(query, max_results)`, `fetch_arxiv(arxiv_id)`, `download_arxiv(arxiv_id, output_dir)`, and async `read(paper)`/`read_pdf(path)` methods. Require an explicit provider or construct `OpenAIProvider` only when requested; keep parser/client injectable for tests.

- [x] **Step 3: Fix PaperReader state and provider validation**

  Set `_paper` before running, clear all run-local state in `setup`, reject a missing provider with a clear error, and preserve trace metadata from provider responses where available.

- [x] **Step 4: Run pipeline tests and full tests**

  Run `uv run pytest tests/unit/test_pipeline.py tests/unit/test_paper_reader.py tests/integration/test_read_pipeline.py -q` followed by `uv run pytest -q`.

### Task 5: Expose the workflow through package metadata, CLI, examples, and docs

**Files:**
- Modify: `repro_forge/cli.py`
- Modify: `repro_forge/agents/__init__.py`
- Modify: `repro_forge/__init__.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `docs/getting-started/quickstart.md`
- Modify: `docs/getting-started/installation.md`
- Create: `examples/p1_read_paper.py`

- [x] **Step 1: Add CLI smoke tests before implementation**

  Test `repro-forge --version`, `repro-forge capabilities`, and a help screen without API keys. Keep actual LLM/PDF execution in the Python API and examples so CLI tests remain deterministic.

- [x] **Step 2: Implement CLI commands and package exports**

  Add `--version`, `capabilities`, and `read-json` for reading a serialized `Paper` with a deterministic/no-network provider only when explicitly supplied by the caller. Export P1 classes from stable namespaces and update optional dependency groups/documentation.

- [x] **Step 3: Update examples and documentation**

  Replace the P1 “planned/not runnable” wording with a precise P1 quickstart, while keeping P2+ APIs explicitly planned. Document optional extras, fake-provider offline run, real PDF requirements, and provider configuration.

- [x] **Step 4: Run CLI and docs checks**

  Run the CLI smoke tests and `uv run mkdocs build --clean -f docs/mkdocs.yml`.

### Task 6: Final P1 verification

**Files:**
- Modify: `docs/P0-TECHNICAL-REFERENCE.md` only if its P1 status table is stale

- [x] **Step 1: Run quality checks**

  Run `uv run ruff format --check repro_forge tests`, `uv run ruff check repro_forge tests`, `uv run mypy repro_forge`, `uv run pytest -q`, and `uv build`.

- [x] **Step 2: Run an installed-package smoke test**

  Build and install the wheel in a temporary virtual environment, then verify public imports and `repro-forge --version` from outside the source tree.

- [x] **Step 3: Report any environment-only blockers separately**

  If Docker or external arXiv/OpenAI access is unavailable, record that limitation without claiming the corresponding external integration was verified.
