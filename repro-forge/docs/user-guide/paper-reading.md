# Paper Reading

The P1 paper workflow has four stages and is the current implemented vertical
slice; it is not yet a full reproduction pipeline:

1. `PDFParser` converts a local PDF into `PaperMetadata`, page-aware
   `Section` objects, raw text, and token estimates.
2. `PaperChunker` keeps sections together where possible and splits oversized
   paragraphs at whitespace boundaries under a token budget.
3. `PaperReader` uses the P0 ReAct runtime and an injected `BaseProvider` to
   inspect sections and produce a `PaperNote` with trace and token usage.
4. `PaperPipeline` composes those stages and also exposes arXiv metadata and
   download helpers.

```python
from repro_forge.paper import PaperPipeline

pipeline = PaperPipeline(provider=my_provider)
note = await pipeline.read_pdf("papers/attention.pdf")
print(note.model_dump_json(indent=2))
```

For offline demos use `examples/read_paper.py`. Remote LLM calls require the
`openai` extra and either `OPENAI_API_KEY` or `DEEPSEEK_API_KEY`; keyless local
OpenAI-compatible endpoints can instead set `OPENAI_BASE_URL` and
`OPENAI_MODEL`. PDF and arXiv sources have independent optional extras. P2
methodologist/algorithm extraction, code generation, experiment execution,
and verification are intentionally not included. See the [P1 Technical
Reference](../P1-TECHNICAL-REFERENCE.md) for tool contracts and failure
behavior.
