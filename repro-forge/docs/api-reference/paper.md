# Paper API

P1 的论文领域 API 位于 `repro_forge.paper`。这些对象是 parser、chunker、
PaperReader 和 pipeline 之间的稳定数据边界。

## Schemas

::: repro_forge.paper.schemas

## Chunking

::: repro_forge.paper.chunker

## Pipeline

::: repro_forge.paper.pipeline

## Parsers

### PDF

::: repro_forge.paper.parser.pdf_parser

### arXiv

::: repro_forge.paper.parser.arxiv_api

### Import guidance

`PDFParser` 和 `ArxivClient` 使用惰性可选依赖。只导入 schema 或
`PaperChunker` 不需要安装 PDF/arXiv extra；真正调用 parser/client 时才会
检查对应 SDK。
