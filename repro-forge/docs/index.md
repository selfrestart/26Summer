# ReproForge Documentation

Welcome to the ReproForge documentation. ReproForge is being built as a
multi-agent framework for computer-science paper reading and reproduction. The
current release is a working P1 paper-reading system; the full reproduction
platform remains the roadmap target.

!!! note "Current project status"

    P0 and P1 are implemented. P1 provides PDF/arXiv paper ingestion,
    token-aware chunking, the PaperReader agent, provider injection, and a
    `PaperPipeline`/CLI surface. Method extraction, reproduction execution,
    knowledge graph, API, and frontend remain roadmap work.

    See [P1 Design Rationale](P1-DESIGN-RATIONALE.md) for the decisions behind
    the implementation and [P1 Technical Reference](P1-TECHNICAL-REFERENCE.md)
    for APIs, commands, environment variables, failure modes, and verification.
    Developers continuing the implementation should also read the
    [P1 Implementation Guide](P1-IMPLEMENTATION-GUIDE.md).

## What is ReproForge?

ReproForge addresses the **reproducibility crisis** in computer science. P1
implements the first vertical slice: turn a local PDF or arXiv paper into a
structured, traceable `PaperNote`. The six-agent pipeline described below is
the target architecture, not the current executable surface.

<div class="grid cards" markdown>

- :material-book-open-page-variant: **Paper Deep-Dive**

    ---

    Parse a PDF or download from arXiv, then get a structured note with TL;DR,
    contributions, methodology summary, findings, strengths, and questions.

    [:octicons-arrow-right-24: P1 quickstart](getting-started/quickstart.md)

- :material-flask-round-bottom: **Paper Reproduction (Roadmap)**

    ---

    From algorithm to code to verified results. Generated code runs in
    Docker sandboxes with automatic metric comparison against claimed results.

    [:octicons-arrow-right-24: Reproduce a paper](user-guide/reproduction.md)

- :material-graph: **Knowledge Graph (Roadmap)**

    ---

    Build and query a Neo4j graph of papers, methods, benchmarks, and their
    relationships. Trace method evolution paths across papers.

    [:octicons-arrow-right-24: Explore knowledge graph](architecture/knowledge-graph.md)

- :material-robot: **Multi-Agent System (P1: PaperReader only)**

    ---

    Six specialized agents orchestrated via ReAct + Plan-Execute loops:
    PaperReader, Methodologist, MathChecker, CodeForger, Experimentor, Verifier.

    [:octicons-arrow-right-24: Architecture](architecture/overview.md)

- :material-cloud-braces: **MCP Protocol (Roadmap)**

    ---

    Full Model Context Protocol Server/Client implementation. Standardize
    access to arXiv, GitHub, PapersWithCode, and custom tools.

    [:octicons-arrow-right-24: MCP Integration](architecture/mcp-integration.md)

- :material-shield-check: **Safety & Guardrails (Roadmap)**

    ---

    Input/output validation, code security review, plagiarism detection, and
    result plausibility checks to ensure responsible agent behavior.

    [:octicons-arrow-right-24: Security](architecture/reproduction-pipeline.md)

</div>

## Current P1 Data Flow

```mermaid
flowchart LR
    INPUT[PDF or arXiv] --> PARSE[PDFParser / ArxivClient]
    PARSE --> PAPER[Paper + Section]
    PAPER --> CHUNK[PaperChunker]
    CHUNK --> READER[PaperReader]
    READER --> NOTE[PaperNote JSON]
    READER --> TRACE[Trace + token usage]
```

## Target Architecture Concepts

The following concepts explain the planned end state. Only the P1 components
identified in the status table are implemented today.

ReproForge is built around five core abstractions:

### 1. Agents

Each agent is a specialist. Together they form a pipeline:

```mermaid
graph LR
    PR[PaperReader] --> MT[Methodologist]
    MT --> CF[CodeForger]
    CF --> EX[Experimentor]
    EX --> VF[Verifier]
    PR -.-> MC[MathChecker]
    MC -.-> VF
```

### 2. Memory

Three-tier memory architecture:

| Tier | Storage | Purpose |
|------|---------|---------|
| Working | Agent context window | Current conversation & active reasoning |
| Episodic | ChromaDB vector store | Past paper analyses & experiment history |
| Semantic | Neo4j knowledge graph | Cross-paper method relationships & benchmarks |

### 3. Tools

Agents use tools to interact with the world. All tools are standardized via
the MCP (Model Context Protocol) and can be:

- **Built-in**: arXiv search, GitHub code search, PDF parsing, code execution
- **MCP-hosted**: Any MCP-compatible server can provide tools
- **Custom**: User-defined tools via a simple decorator API

### 4. Pipeline

The reproduction pipeline is a directed workflow:

```
Paper → Algorithm Extraction → Code Generation → Docker Execution → Verification → Report
```

### 5. Evaluation

Built-in benchmarks measure agent performance:

- Paper Q&A accuracy
- Algorithm extraction precision
- Generated code correctness
- Reproduction fidelity score

## Project Status

| Phase | Status |
|-------|--------|
| P0 (Core and infrastructure) | ✅ Complete |
| P1 (PaperReader) | ✅ Complete |
| P2 (Methodologist) | 📋 Planned |
| P3 (CodeForger + Execution) | 📋 Planned |
| P4 (Verifier) | 📋 Planned |
| P5 (Knowledge Graph + Survey) | 📋 Planned |
| P6 (MCP + API + Frontend) | 📋 Planned |
| P7 (Guardrails) | 📋 Planned |
| P8 (Evaluation + Observability) | 📋 Planned |

[View the full roadmap on GitHub :octicons-arrow-right-24:](https://github.com/selfrestart/26Summer/tree/main/repro-forge#roadmap)

## Community

- :material-github: [GitHub](https://github.com/selfrestart/26Summer/tree/main/repro-forge)
- :material-forum: [Discussions](https://github.com/selfrestart/26Summer/discussions)
