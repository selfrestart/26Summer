# Paper API

P1 的论文领域 API 位于 `repro_forge.paper`。这些对象是 parser、chunker、
PaperReader 和 pipeline 之间的稳定数据边界。

## Schemas

::: repro_forge.paper.schemas

## Chunking

::: repro_forge.paper.chunker

## Pipeline

::: repro_forge.paper.pipeline

## Methodology Extraction (P2)

P2 的证据化方法学抽取 API 位于 `repro_forge.paper.extractor`。

### Schemas

::: repro_forge.paper.extractor.schemas

### Evidence view

::: repro_forge.paper.extractor.evidence

### Methodology pipeline

::: repro_forge.paper.extractor.pipeline

`MethodologyPipeline` 组合 P1 `PaperPipeline` 与 `Methodologist`，支持
`analyze(paper)`、`analyze_pdf(path)` 和 `analyze_arxiv(id)` 三种入口，
统一返回 `MethodAnalysis`。

## Parsers

### PDF

::: repro_forge.paper.parser.pdf_parser

### arXiv

::: repro_forge.paper.parser.arxiv_api

### Import guidance

`PDFParser` 和 `ArxivClient` 使用惰性可选依赖。只导入 schema 或
`PaperChunker` 不需要安装 PDF/arXiv extra；真正调用 parser/client 时才会
检查对应 SDK。
