# Changelog

All notable changes to ReproForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Project infrastructure: `pyproject.toml`, pre-commit hooks, CI/CD workflows
- Core type system (`core/types.py`) with Message, Action, Observation primitives
- Base agent abstraction (`core/base.py`) with ReAct loop and streaming support
- Multi-provider LLM interface (`providers/base.py`)
- Community files: LICENSE, README, CONTRIBUTING, CODE_OF_CONDUCT, GOVERNANCE, SECURITY
- P1 paper reading: `PDFParser`, `ArxivClient`, `PaperChunker`, `PaperPipeline`, `PaperReader`, `OpenAIProvider`
- P2 methodology extraction: `MethodAnalysis`/`EvidenceRef`/`EquationEvidence`/`ReportedClaimDraft` schemas, `PaperEvidenceView`, `Methodologist`, `MethodologyPipeline`, `analyze-pdf`/`analyze-json` CLI
- P2 docs: design rationale, technical reference, methodology user guide
- P3 code generation: `CodeForger` agent with Plan-then-Execute workflow, evidence mapping, one-repair pass
- P3 schemas: `ReproductionBundle` (bundle.v1), `ExperimentSpec` (experiment.v1), `ExperimentRun` (run.v1), `GeneratedFile`, `DependencySpec`, `DatasetReference`, `ExperimentEvent`, `ObservedMetric`, `ArtifactRecord`, `FixtureSpec`
- P3 static validation: AST/compile checks, import vs dependency declaration, entrypoint existence, config format, test file existence, manifest integrity
- P3 backends: dry-run (no execution, materialize+validate), local-subprocess (registered fixtures only, env sanitisation, process-tree cleanup), Docker (non-root, offline, read-only rootfs, resource limits, cap_drop=ALL, no-new-privileges)
- P3 registered CPU fixtures: `p3-cpu-smoke`, `p3-cpu-smoke-fail`, `p3-cpu-smoke-timeout`, `p3-cpu-smoke-large-output`, `p3-cpu-smoke-cleanup`
- P3 pipeline: `ReproductionPipeline` (generate + execute), `Experimentor` (backend routing)
- P3 CLI: `generate-code`, `run-experiment`, `run-fixture` with atomic output and overwrite guard
- P3 real Docker security smoke: digest-pinned Python CPU image, non-root/offline/read-only controls, cgroup/tmpfs limits, terminal-path cleanup, structured metrics and artifacts

### Fixed
- Docker tmpfs output collection now runs through a bounded trusted collector while the container is alive; Docker archive APIs expose the underlying mount point and otherwise lose tmpfs contents

---

## [0.1.0] - Unreleased

### Added
- Initial project scaffold
- Core runtime skeleton

[Unreleased]: https://github.com/selfrestart/26Summer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/selfrestart/26Summer/releases/tag/v0.1.0
