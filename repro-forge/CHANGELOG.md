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

---

## [0.1.0] - Unreleased

### Added
- Initial project scaffold
- Core runtime skeleton

[Unreleased]: https://github.com/selfrestart/26Summer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/selfrestart/26Summer/releases/tag/v0.1.0
