# Contributing to ReproForge

Thank you for your interest in contributing! This document outlines the development workflow, coding standards, and review process.

---

## Getting Started

### Prerequisites

- Python 3.11+ (automatically managed by `uv` via `.python-version`)
- [uv](https://docs.astral.sh/uv/) - fast Python package manager
- Git

### One-Command Setup

```bash
# Fork & clone
git clone https://github.com/selfrestart/26Summer.git
cd 26Summer/repro-forge

# Full setup: venv + deps + pre-commit hooks
make setup

# Configure your API keys
cp .env.example .env
# Edit .env with your LLM provider keys
```

### Manual Setup (if not using uv)

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[all,dev]"
pre-commit install
cp .env.example .env
```

### Verify Setup

```bash
make check  # runs format-check, lint, typecheck, and tests
```

---

## Development Workflow

### Branch Naming

```
feat/<module>/<description>     e.g. feat/agents/add-verifier
fix/<module>/<description>      e.g. fix/pdf-parser/memory-leak
docs/<description>              e.g. docs/api-reference-update
refactor/<module>/<description> e.g. refactor/memory/retrieval-api
```

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body with detailed explanation]
[optional footer with issue references]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`

Examples:
```
feat(agents): implement Verifier agent with metric comparison
fix(tools): handle timeout in Docker sandbox execution
docs(examples): add reproduction pipeline tutorial
```

### Pull Request Process

1. Create a feature branch from `develop`
2. Write code + tests
3. Run `make check` locally to verify
4. Push and open a PR against `develop`
5. Fill in the PR template completely
6. Wait for CI checks to pass
7. Request review from a maintainer
8. Address review feedback
9. Maintainer merges after approval

### Code Review Checklist

- [ ] Tests cover new functionality
- [ ] Type annotations are complete
- [ ] Docstrings follow Google style
- [ ] No new linting or type-checking warnings
- [ ] Changelog entry added (if user-facing)
- [ ] Documentation updated (if applicable)

---

## Coding Standards

### Python Style

We use **ruff** for both linting and formatting. All code must pass:

```bash
ruff check repro_forge/ tests/
ruff format --check repro_forge/ tests/
```

Key rules:
- Line length: 100 characters
- Docstring style: Google
- Imports: alphabetically ordered, single-line
- Type annotations: required on all public interfaces (`disallow_untyped_defs = true`)

### Type Checking

We enforce strict mypy checking:

```bash
mypy repro_forge/
```

### Docstring Format

```python
def function_name(param1: str, param2: int) -> bool:
    """Short description of what the function does.

    Longer description providing context about the function's behavior,
    edge cases, and design rationale.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of the return value.

    Raises:
        ValueError: When param2 is negative.

    Example:
        >>> function_name("hello", 42)
        True
    """
```

---

## Testing

### Test Structure

| Layer | Directory | Command | Coverage Target |
|-------|-----------|---------|-----------------|
| Unit | `tests/unit/` | `pytest tests/unit/` | 鈮?90% |
| Integration | `tests/integration/` | `pytest tests/integration/` | 鈮?70% |
| End-to-end | `tests/e2e/` | `pytest tests/e2e/` | 鈮?50% |

### Writing Tests

- Use `pytest` fixtures for shared setup
- Mock LLM calls with `FakeLLMProvider` (defined in `tests/conftest.py`)
- Use `chromadb.Client(in_memory=True)` for vector store tests
- Tag slow tests with `@pytest.mark.slow`
- Tag tests requiring real LLM calls with `@pytest.mark.llm`

### Running Tests

```bash
# Unit tests only (fast, no LLM calls)
make test

# With coverage report
make test-cov

# Everything
make test-all
```

---

## Project Structure

See [ARCHITECTURE.md](docs/architecture/overview.md) for a detailed description of the codebase organization.

---

## Release Process

1. PRs accumulate on `develop`
2. When ready for release, a maintainer creates a release branch `release/vX.Y.Z`
3. Version is bumped in `pyproject.toml` and `repro_forge/__init__.py`
4. CHANGELOG.md is updated
5. PR from release branch 鈫?`main`
6. Tag `vX.Y.Z` is pushed, triggering the Release workflow
7. Package is published to PyPI automatically

---

## Community

- [GitHub Discussions](https://github.com/selfrestart/26Summer/discussions) - Q&A
- [Issue Tracker](https://github.com/selfrestart/26Summer/issues) - bugs and features

### Looking for Issues?

- [Good First Issues](https://github.com/selfrestart/26Summer/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
- [Help Wanted](https://github.com/selfrestart/26Summer/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22)

---

## Code of Conduct

This project adheres to the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to maintainers.

---

Thank you for contributing!
