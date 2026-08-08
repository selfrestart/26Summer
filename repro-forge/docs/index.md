# ReproForge Documentation

Welcome to the ReproForge documentation. ReproForge is being built as a
multi-agent framework for computer-science paper reading and reproduction. The
current release includes the working P1/P2 paper and methodology system plus
the complete P3 bundle and constrained-execution slice. P4 verification and the
full platform remain roadmap targets.

!!! note "Current project status"

    P0, P1 and P2 are complete. P1 provides PDF/arXiv paper ingestion,
    token-aware chunking, the PaperReader agent, provider injection, and a
    `PaperPipeline`/CLI surface. P2 adds the `Methodologist`, `PaperEvidenceView`,
    `MethodAnalysis` and methodology CLI surface. P3 adds versioned reproduction
    bundles, fail-closed CodeForger generation, static validation, dry-run, and
    a maintainer-owned local fixture runner and digest-pinned Docker backend.
    The real Docker security smoke has passed. P4 verification, knowledge graph,
    API, and frontend remain roadmap work.

    See [P1 Design Rationale](P1-DESIGN-RATIONALE.md) for the decisions behind
    the implementation and [P1 Technical Reference](P1-TECHNICAL-REFERENCE.md)
    for APIs, commands, environment variables, failure modes, and verification.
    Developers continuing the implementation should also read the
    [P1 Implementation Guide](P1-IMPLEMENTATION-GUIDE.md).

    P2 is complete and produces a validated `MethodAnalysis` with source-bound
    evidence, explicit equation capture status, and raw reported-claim drafts.
    P3 consumes this contract and produces `ReproductionBundle` and
    `ExperimentRun`; knowledge-graph writes remain P5. See the
    [P2 technical reference](P2-TECHNICAL-REFERENCE.md) for the input contract
    and the [P3 technical reference](P3-TECHNICAL-REFERENCE.md) for the current
    execution boundary and Docker gate.

## What is ReproForge?

ReproForge addresses the **reproducibility crisis** in computer science. P1
implements paper reading, P2 adds evidence-grounded methodology analysis, and
P3 is implementing auditable code generation plus constrained experiment
execution. The six-agent pipeline described below remains partially implemented;
P4-P8 are roadmap work.

<div class="grid cards" markdown>

- :material-book-open-page-variant: **Paper Deep-Dive**

    ---

    Parse a PDF or download from arXiv, then get a structured note with TL;DR,
    contributions, methodology summary, findings, strengths, and questions.

    [:octicons-arrow-right-24: P1 quickstart](getting-started/quickstart.md)

- :material-flask-round-bottom: **Paper Reproduction (P3 Complete)**

    ---

    Generate versioned code bundles, validate them without execution, and run
    repository fixtures locally or execute offline in digest-pinned Docker. Automatic
    claim/metric comparison belongs to P4.

    [:octicons-arrow-right-24: Reproduce a paper](user-guide/reproduction.md)

- :material-graph: **Knowledge Graph (Roadmap)**

    ---

    Build and query a Neo4j graph of papers, methods, benchmarks, and their
    relationships. Trace method evolution paths across papers.

    [:octicons-arrow-right-24: Explore knowledge graph](architecture/knowledge-graph.md)

- :material-robot: **Agent System (P1-P3 Current)**

    ---

    Six specialized agents orchestrated via ReAct + Plan-Execute loops:
    PaperReader, Methodologist, MathChecker, CodeForger, Experimentor, Verifier.

    [:octicons-arrow-right-24: Architecture](architecture/overview.md)

- :material-cloud-braces: **MCP Protocol (Roadmap)**

    ---

    Full Model Context Protocol Server/Client implementation. Standardize
    access to arXiv, GitHub, PapersWithCode, and custom tools.

    [:octicons-arrow-right-24: MCP Integration](architecture/mcp-integration.md)

- :material-shield-check: **Execution Safety (P3 Current, P7 Roadmap)**

    ---

    P3 enforces path/manifest validation and a minimum Docker sandbox. P7 will
    add platform-wide identity, policy, audit, plagiarism, and output guardrails.

    [:octicons-arrow-right-24: Security](architecture/reproduction-pipeline.md)

</div>

## Current P1-P3 Data Flow

```mermaid
flowchart LR
    INPUT[PDF or arXiv] --> PARSE[PDFParser / ArxivClient]
    PARSE --> PAPER[Paper + Section]
    PAPER --> CHUNK[PaperChunker]
    CHUNK --> READER[PaperReader]
    READER --> NOTE[PaperNote JSON]
    READER --> TRACE[Trace + token usage]
    PAPER --> EVIDENCE[PaperEvidenceView]
    NOTE -. optional hint .-> METHOD[Methodologist]
    EVIDENCE --> METHOD
    METHOD --> ANALYSIS[MethodAnalysis JSON]
    ANALYSIS --> FORGER[CodeForger]
    FORGER --> BUNDLE[ReproductionBundle JSON]
    BUNDLE --> DRY[Dry-run / fixed fixture runner]
    BUNDLE -. reviewed digest + daemon .-> DOCKER[Docker backend]
    DRY --> RUN[ExperimentRun JSON]
    DOCKER --> RUN
```

## Target Architecture Concepts

The following concepts combine the current P1-P3 surface with the planned end
state. Use the status table to distinguish implemented and planned components.

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

### 2. Memory (P5 Planned)

Three-tier memory architecture:

| Tier | Storage | Purpose |
|------|---------|---------|
| Working | Agent context window | Current conversation & active reasoning |
| Episodic | ChromaDB vector store | Past paper analyses & experiment history |
| Semantic | Neo4j knowledge graph | Cross-paper method relationships & benchmarks |

### 3. Tools (P1-P3 Current, P4-P7 Planned Evolution)

P1 PaperReader owns three in-process read-only tools. Later phases expand the
tool surface only after their domain contracts are stable:

- **P2**: evidence lookup for methodology extraction (implemented by `PaperEvidenceView`)
- **P3**: static validation, dry-run, fixed fixture runner, and digest-controlled Docker execution
- **P4**: claim/metric and mathematical verification tools
- **P5**: artifact, vector, graph, and survey retrieval
- **P6**: MCP tools/resources backed by the shared application service
- **P7**: identity, policy, approval, and audit wrappers

### 4. Pipeline (P3 Current, P4 Planned)

The reproduction pipeline is a directed workflow:

```text
Paper -> MethodAnalysis -> Code Generation -> Docker Execution -> Verification -> Report
        P2 complete       P3 complete         P3 complete         P4 planned
```

### 5. Evaluation (P8 Planned)

Built-in benchmarks measure agent performance:

- Paper Q&A accuracy
- Algorithm extraction precision
- Generated code correctness
- Reproduction fidelity score

## Project Status

| Phase | Status |
|-------|--------|
| P0 (Core and infrastructure) | Complete |
| P1 (PaperReader) | Complete |
| P2 (Methodologist + evidence-grounded methodology extraction) | Complete |
| P3 (Auditable code + sandboxed experiments) | Complete |
| P4 (Math + claim/result verification) | Planned |
| P5 (Memory + knowledge graph + survey) | Planned |
| P6 (Application service + MCP + API + workbench) | Planned |
| P7 (Security + guardrails + governance) | Planned |
| P8 (Evaluation + observability + release gates) | Planned |

[Read the P0-P8 roadmap :octicons-arrow-right-24:](ROADMAP.md)

The roadmap is authoritative for the `Planned` -> `Ready` -> `In Progress` ->
`Complete` lifecycle, Definition of Ready, stage gates, and safe stopping
milestones. A planned document, empty namespace, optional dependency, or future
Compose service is not an implemented capability.

## Community

- :material-github: [GitHub](https://github.com/selfrestart/26Summer/tree/main/repro-forge)
- :material-forum: [Discussions](https://github.com/selfrestart/26Summer/discussions)
