<div align="center">

# 🔬 ReproForge

**Automated Paper Reading, Methodology Analysis & Reproduction for CS Research**

[![CI](https://github.com/selfrestart/26Summer/actions/workflows/ci.yml/badge.svg)](https://github.com/selfrestart/26Summer/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/repro-forge.svg)](https://pypi.org/project/repro-forge/)
[![Python](https://img.shields.io/pypi/pyversions/repro-forge.svg)](https://pypi.org/project/repro-forge/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-GitHub-blue)](https://github.com/selfrestart/26Summer/tree/main/repro-forge/docs)
[![Discord](https://img.shields.io/discord/1234567890?color=5865F2&label=discord)](https://discord.gg/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

---

## What is ReproForge?

ReproForge is a multi-agent framework that automates the end-to-end pipeline of reading, understanding, and reproducing computer science research papers. It equips researchers and engineers with **six specialized AI agents** that collaborate to:

1. **Read** — parse PDFs into structured notes with layered summaries
2. **Analyze** — extract algorithms, architectures, and mathematical derivations
3. **Verify** — cross-check formula consistency and derivation gaps
4. **Implement** — generate clean, runnable PyTorch/TensorFlow reproduction code
5. **Execute** — run experiments in Docker sandboxes with MLflow tracking
6. **Validate** — compare reproduced metrics against claimed results

---

## Key Features

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

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) — fast Python package manager (auto-manages Python 3.11+ via `.python-version`)
- An LLM API key (OpenAI, Anthropic, or any OpenAI-compatible endpoint)

### Installation

```bash
# Clone and one-command setup
git clone https://github.com/selfrestart/26Summer.git
cd 26Summer/repro-forge
make setup          # venv + deps + pre-commit hooks

# Or manually:
uv venv && uv sync --all-extras

# For pip users:
pip install -e ".[all]"
```

### Environment Setup

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 5-Minute Quickstart

```python
from repro_forge.paper import PaperPipeline
from repro_forge.agents import PaperReader, Methodologist
from repro_forge.providers import OpenAIProvider

# 1. Parse a paper and get structured insights
pipeline = PaperPipeline()
paper = await pipeline.parse("path/to/paper.pdf")

# 2. Get a multi-level reading note
reader = PaperReader(provider=OpenAIProvider())
notes = await reader.read(paper)
print(notes.tldr)       # 3-sentence summary
print(notes.mehodology) # Detailed method analysis

# 3. Extract algorithms and architecture
methodologist = Methodologist(provider=OpenAIProvider())
insights = await methodologist.analyze(paper)
for algo in insights.algorithms:
    print(f"Algorithm: {algo.name}")
    print(f"Input: {algo.input}")
    print(f"Steps: {algo.pseudocode}")
    print(f"Output: {algo.output}")
```

### Run a Full Reproduction

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

## Roadmap

| Phase | Status | Content |
|-------|--------|---------|
| P0 | 🚧 In Progress | Project infrastructure, CI/CD, docs skeleton |
| P1 | 📋 Planned | Core runtime, PaperReader agent, PDF pipeline |
| P2 | 📋 Planned | Methodologist, algorithm extraction, KG writes |
| P3 | 📋 Planned | CodeForger, Docker sandbox execution |
| P4 | 📋 Planned | MathChecker, Verifier, reproduction reports |
| P5 | 📋 Planned | Knowledge graph, SurveyScribe |
| P6 | 📋 Planned | MCP protocol, FastAPI server, React frontend |
| P7 | 📋 Planned | Guardrails: code review, plagiarism detection |
| P8 | 📋 Planned | Evaluation benchmarks, observability |

See our [public project board](https://github.com/orgs/repro-forge/projects/1) for details.

---

## Community

- 💬 [Discord](https://discord.gg/) — Real-time discussion & office hours
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
