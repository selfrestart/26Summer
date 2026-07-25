.PHONY: help venv sync install install-dev clean lint format typecheck test test-cov docs serve pre-commit-all docker-build docker-run

.DEFAULT_GOAL := help

VENV_DIR := .venv

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

venv: ## Create virtual environment via uv (auto-picks .python-version)
	uv venv

sync: ## Install core deps + dev tools (fast, for daily development)
	uv sync --group dev

sync-all: ## Install ALL optional extras (heavy: chromadb, neo4j, mlflow, etc.)
	uv sync --all-extras --group dev

sync-minimal: ## Install only core deps (no extras, no dev tools)
	uv sync

install: ## Install core dependencies only
	uv pip install -e .

install-dev: ## Install with all optional + dev dependencies
	uv pip install -e ".[all,dev]"

clean: ## Remove build artifacts, caches, and venv
	@rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/ .venv/
	@rm -rf htmlcov/ .coverage coverage.xml
	@rm -rf site/

lint: ## Run ruff linter
	uv run ruff check repro_forge/ tests/

format: ## Run ruff formatter
	uv run ruff format repro_forge/ tests/
	uv run ruff check --fix repro_forge/ tests/

format-check: ## Check formatting without writing
	uv run ruff format --check repro_forge/ tests/

typecheck: ## Run mypy type checking
	uv run mypy repro_forge/

test: ## Run unit + integration tests
	uv run pytest tests/unit tests/integration -v --no-header

test-cov: ## Run tests with coverage report
	uv run pytest tests/unit tests/integration -v --no-header --cov=repro_forge --cov-report=term-missing --cov-report=html

test-e2e: ## Run end-to-end tests (requires services)
	uv run pytest tests/e2e -v --no-header

test-all: ## Run all tests including slow
	uv run pytest -v --no-header

check: format-check lint typecheck test ## Run all checks: format, lint, typecheck, test
	@echo "[OK] All checks passed"

pre-commit-all: ## Run pre-commit on all files
	uv run pre-commit run --all-files

docs: ## Build documentation
	uv run mkdocs build --clean -f docs/mkdocs.yml

docs-serve: ## Serve documentation locally
	uv run mkdocs serve -f docs/mkdocs.yml

docker-build: ## Build the P0 package image
	docker build -t repro-forge:p0 .

docker-run: docker-build ## Run the P0 CLI from the package image
	docker run --rm repro-forge:p0

ci: ## Simulate CI pipeline locally
	@echo "=== Format Check ==="
	uv run ruff format --check repro_forge/ tests/
	@echo "=== Lint ==="
	uv run ruff check repro_forge/ tests/
	@echo "=== Type Check ==="
	uv run mypy repro_forge/
	@echo "=== Unit Tests ==="
	uv run pytest tests/unit -v --no-header
	@echo "=== Integration Tests ==="
	uv run pytest tests/integration -v --no-header
	@echo "[OK] CI pipeline passed"

setup: ## Full first-time setup: venv + core deps + dev tools + pre-commit hooks
	uv venv
	uv sync --group dev
	uv run pre-commit install
	@echo ""
	@echo "Setup complete! Run 'cp .env.example .env' and edit your API keys."
	@echo "Then run 'make check' to verify everything works."
	@echo "Use 'make sync-all' when you need all optional features (chromadb, neo4j, etc.)."
