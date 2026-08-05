<div align="center">

# 🔬 ReproForge

**Automated Paper Reading, Methodology Analysis & Reproduction for CS Research**

[![CI](https://github.com/selfrestart/26Summer/actions/workflows/ci.yml/badge.svg)](https://github.com/selfrestart/26Summer/actions/workflows/ci.yml)
[![Status](https://img.shields.io/badge/status-P1%20paper%20reading-green.svg)](#project-status)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-GitHub-blue)](https://github.com/selfrestart/26Summer/tree/main/repro-forge/docs)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

---

## What is ReproForge?

ReproForge aims to become a multi-agent framework for reading, understanding, and reproducing computer science research papers. The planned system uses **six specialized AI agents** that collaborate to:

1. **Read** — parse PDFs into structured notes with layered summaries
2. **Analyze** — extract algorithms, architectures, and mathematical derivations
3. **Verify** — cross-check formula consistency and derivation gaps
4. **Implement** — generate clean, runnable PyTorch/TensorFlow reproduction code
5. **Execute** — run experiments in Docker sandboxes with MLflow tracking
6. **Validate** — compare reproduced metrics against claimed results

---

## Key Features

> **Capability boundary:** the table below includes roadmap targets. P0 and P1
> are implemented; P1 covers local PDF/arXiv ingestion, token-aware chunking,
> the PaperReader agent, provider injection, and the `PaperPipeline`/CLI.

| Category | Feature |
|----------|---------|
| 📄 **Multi-Agent Pipeline** | Six specialized agents (Reader, Methodologist, MathChecker, CodeForger, Experimentor, Verifier) with ReAct + Plan-Execute hybrid execution |
| 🔬 **Reproduction Engine** | Paper → Algorithm Extraction → Code Generation → Docker Execution → Metric Verification, fully automated |
| 🧠 **Three-Tier Memory** | Working memory (context) → Episodic memory (vector store) → Semantic memory (knowledge graph) |
| 🌐 **MCP Protocol** | Full Model Context Protocol Server/Client implementation for standardized tool access |
| 📊 **Knowledge Graph** | Neo4j-powered paper-method-benchmark relationship graph with evolution path tracing |
| 📝 **Survey Generation** | Automated literature survey writing, driven by knowledge graph inference |
| 🔌 **Multi-Provider LLM** | OpenAI, Anthropic, DeepSeek, Qwen, Ollama, vLLM — all through a unified interface |
| 🚀 **Multi-Backend Execution** | Docker local / Google Colab GPU / Remote SSH / Dry-run preview |
| 🛡️ **Safety Guardrails** | Code security review, plagiarism detection, result plausibility checks |
| 📈 **Observability** | OpenTelemetry tracing, MLflow experiment tracking, cost monitoring |
| 🧪 **Evaluation Suite** | Built-in benchmarks with LLM-as-Judge auto-evaluation |

---

## P1 Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) — fast Python package manager (auto-manages Python 3.11+ via `.python-version`)
- No API key is required for the deterministic examples and test suite

### Installation

```bash
# Clone and one-command setup
git clone https://github.com/selfrestart/26Summer.git
cd 26Summer/repro-forge
uv sync --locked --group dev

# Verify the installed package and P1 capabilities
uv run repro-forge --version
uv run repro-forge capabilities
uv run pytest
uv run ruff check repro_forge tests
uv run mypy repro_forge
```

### Optional P1 Integrations

Install only the integrations you need:

```bash
uv sync --locked --extra pdf --group dev       # local PDF parsing
uv sync --locked --extra arxiv --group dev     # arXiv search/download
uv sync --locked --extra openai --group dev    # OpenAI-compatible LLM

# For real LLM-backed reading, set OPENAI_API_KEY or DEEPSEEK_API_KEY in .env
```

### 5-Minute Quickstart

### Read a paper with P1

```python
from dotenv import load_dotenv

from repro_forge.paper import PaperPipeline
from repro_forge.providers import OpenAIProvider

load_dotenv()

# 1. Parse a paper and get structured insights
pipeline = PaperPipeline(provider=OpenAIProvider())
note = await pipeline.read_pdf("path/to/paper.pdf")
print(note.tldr)
print(note.summary())
```

For an offline run, use `uv run python examples/read_paper.py`, which uses a
deterministic provider and does not require a PDF or API key.

### Run a Full Reproduction

> **Planned API:** reproduction is scheduled for P3/P4 and is not implemented
> in P0.

```python
from repro_forge.reproduction import ReproductionPipeline

pipeline = ReproductionPipeline(backend="dryrun")
report = await pipeline.reproduce(
    paper_path="path/to/paper.pdf",
    target_metrics={"accuracy": 94.5},
)
print(f"Reproduction Fidelity: {report.fidelity_score:.1f}/100")
print(f"Generated files: {report.output_dir}")
# Contains: model.py, train.py, config.yaml, requirements.txt, report.md
```

---

## Architecture

```
                         ┌──────────────────┐
        arXiv ID ──────► │   PaperPipeline  │
        / PDF            │  Parse & Extract  │
                         └────────┬─────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
   ┌──────────────┐      ┌──────────────┐       ┌──────────────┐
   │ PaperReader  │      │Methodologist │       │ MathChecker  │
   │ 分层导读 / 摘要 │ ───►│ 方法/算法提取  │ ───►  │ 数学校验      │
   └──────────────┘      └──────────────┘       └──────────────┘
          │                       │                       │
          │              ┌────────┴────────┐              │
          │              ▼                 ▼              │
          │      ┌──────────────┐  ┌──────────────┐      │
          │      │  CodeForger  │  │ Experimentor │      │
          │      │  代码生成      │─►│  实验执行      │      │
          │      └──────────────┘  └──────┬───────┘      │
          │                               │              │
          │                        ┌──────▼───────┐      │
          │                        │   Verifier   │◄─────┘
          │                        │  结果核验      │
          │                        └──────┬───────┘
          │                               │
          │                     ┌─────────▼─────────┐
          └────────────────────►│  Reproduction     │
                                │  Report           │
                                └───────────────────┘
```

---

## Documentation

Full documentation is available in the repository's [docs directory](https://github.com/selfrestart/26Summer/tree/main/repro-forge/docs).

- [Getting Started](docs/getting-started/installation.md)
- [User Guide](docs/user-guide/paper-reading.md)
- [Architecture](docs/architecture/overview.md)
- [API Reference](docs/api-reference/core.md)
- [Examples](docs/examples/paper-dive.md)

---

## Project Status

| Phase | Status | Content |
|-------|--------|---------|
| P0 | ✅ Complete | Core abstractions, tests, packaging, CI, docs build, Docker package image |
| P1 | ✅ Complete | PaperReader, PDF/arXiv parsers, chunker, provider boundary, pipeline, CLI |
| P2 | 📋 Planned | Methodologist, algorithm extraction, KG writes |
| P3 | 📋 Planned | CodeForger, Docker sandbox execution |
| P4 | 📋 Planned | MathChecker, Verifier, reproduction reports |
| P5 | 📋 Planned | Knowledge graph, SurveyScribe |
| P6 | 📋 Planned | MCP protocol, FastAPI server, React frontend |
| P7 | 📋 Planned | Guardrails: code review, plagiarism detection |
| P8 | 📋 Planned | Evaluation benchmarks, observability |

---

## Community

- 🗣 [GitHub Discussions](https://github.com/selfrestart/26Summer/discussions) — Q&A & feature proposals
- 🐛 [Issues](https://github.com/selfrestart/26Summer/issues) — Bug reports & tasks
- 📖 [Contributing Guide](CONTRIBUTING.md) — How to get involved

### Contributor Ladder

```
User → Contributor (any accepted PR) → Reviewer (3+ PRs)
                                      → Maintainer (2 months active)
                                      → PMC (core governance vote)
```

---

## Citation

If you use ReproForge in your research, please cite:

```bibtex
@software{reproforge2025,
  author = {ReproForge Contributors},
  title = {ReproForge: Automated Paper Reading \& Reproduction for CS Research},
  year = {2025},
  url = {https://github.com/selfrestart/26Summer/tree/main/repro-forge},
}
```

---

## License

This project is licensed under the Apache License 2.0 — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built with ❤️ by the ReproForge community</sub>
</div>
