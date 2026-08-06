"""Example: Read a paper using the PaperReader agent.

This demo uses a built-in sample paper (the Transformer paper abstract)
and a fake LLM provider to demonstrate the full reading pipeline.
No API keys or PDF files required.

Usage:
    uv run python examples/read_paper.py

To use a real PDF and LLM through the P1 CLI:
    1. Install optional deps: uv sync --extra pdf --extra openai --group dev
    2. Set OPENAI_API_KEY or DEEPSEEK_API_KEY in .env
    3. Run: uv run repro-forge read-pdf path/to/paper.pdf --output note.json
"""

from __future__ import annotations

import asyncio

from repro_forge.agents.paper_reader import PaperReader
from repro_forge.core.types import AgentConfig
from repro_forge.core.types import AgentType
from repro_forge.paper.schemas import Paper
from repro_forge.paper.schemas import PaperMetadata
from repro_forge.paper.schemas import Section
from repro_forge.paper.schemas import SectionType
from repro_forge.providers.base import BaseProvider
from repro_forge.providers.base import LLMRequest
from repro_forge.providers.base import LLMResponse


class ExampleProvider(BaseProvider):
    """Deterministic provider kept in the example so installed wheels work."""

    def __init__(self, responses: list[str]) -> None:
        super().__init__(model="example")
        self.responses = responses
        self.index = 0

    async def generate(self, request: LLMRequest) -> LLMResponse:
        del request
        content = self.responses[min(self.index, len(self.responses) - 1)]
        self.index += 1
        return LLMResponse(content=content, model=self.model)

    async def generate_stream(self, request: LLMRequest):  # type: ignore[override]
        response = await self.generate(request)
        for word in response.content.split():
            yield word + " "

    @property
    def provider_name(self) -> str:
        return "example"


SAMPLE_PAPER = Paper(
    metadata=PaperMetadata(
        title="Attention Is All You Need",
        authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
        arxiv_id="1706.03762",
        year=2017,
    ),
    sections=[
        Section(
            title="Abstract",
            content=(
                "The dominant sequence transduction models are based on "
                "complex recurrent or convolutional neural networks that "
                "include an encoder and a decoder. The best performing models "
                "also connect the encoder and decoder through an attention "
                "mechanism. We propose a new simple network architecture, "
                "the Transformer, based solely on attention mechanisms, "
                "dispensing with recurrence and convolutions entirely."
            ),
            section_type=SectionType.ABSTRACT,
            token_count=50,
        ),
        Section(
            title="Introduction",
            content=(
                "Recurrent neural networks, long short-term memory and "
                "gated recurrent neural networks in particular, have been "
                "firmly established as state of the art approaches in "
                "sequence modeling and transduction problems."
            ),
            section_type=SectionType.INTRODUCTION,
            token_count=35,
        ),
        Section(
            title="Model Architecture",
            content=(
                "Most competitive neural sequence transduction models "
                "have an encoder-decoder structure. Here, the encoder maps "
                "an input sequence of symbol representations to a sequence "
                "of continuous representations. Given this, the decoder "
                "then generates an output sequence one element at a time."
            ),
            section_type=SectionType.METHOD,
            token_count=40,
        ),
        Section(
            title="Experiments",
            content=(
                "We trained on the WMT 2014 English-German dataset "
                "consisting of about 4.5 million sentence pairs. Sentences "
                "were encoded using byte-pair encoding. Our big transformer "
                "model achieves 28.4 BLEU, outperforming the best previously "
                "reported models by more than 2.0 BLEU."
            ),
            section_type=SectionType.EXPERIMENTS,
            token_count=45,
        ),
        Section(
            title="Conclusion",
            content=(
                "In this work, we presented the Transformer, the first "
                "sequence transduction model based entirely on attention, "
                "replacing the recurrent layers most commonly used in "
                "encoder-decoder architectures with multi-headed self-attention."
            ),
            section_type=SectionType.CONCLUSION,
            token_count=30,
        ),
    ],
    total_pages=11,
    total_tokens=200,
)

FAKE_RESPONSES = [
    "Let me first list the sections to understand the paper structure.",
    "Let me read the abstract to get the high-level overview.",
    "Let me read the model architecture to understand the technical approach.",
    "Let me read the experiments section to see the results.",
    (
        "DONE\n"
        "{\n"
        '  "tldr": "This seminal paper introduces the Transformer architecture, a novel neural network that relies entirely on attention mechanisms rather than recurrence. It achieves 28.4 BLEU on WMT 2014 English-German translation, significantly outperforming previous state-of-the-art models while being more parallelizable.",\n'
        '  "contributions": [\n'
        '    {"description": "Self-attention mechanism replaces recurrence for sequence modeling", "supporting_sections": ["Model Architecture"]},\n'
        '    {"description": "Multi-head attention allows model to jointly attend to different representation subspaces", "supporting_sections": ["Model Architecture"]},\n'
        '    {"description": "Positional encodings inject sequence order information without recurrence", "supporting_sections": ["Model Architecture"]}\n'
        "  ],\n"
        '  "methodology_summary": "Encoder-decoder architecture using stacked multi-head self-attention layers and position-wise feed-forward networks, trained with Adam optimizer and label smoothing.",\n'
        '  "key_findings": [\n'
        '    {"description": "Big Transformer achieves 28.4 BLEU on WMT 2014 En-De translation", "metric_name": "BLEU", "metric_value": "28.4", "dataset": "WMT 2014 En-De"},\n'
        '    {"description": "Significantly faster training than RNN-based models", "metric_name": "Training time", "metric_value": "3.5 days on 8 P100 GPUs", "dataset": "WMT 2014 En-De"}\n'
        "  ],\n"
        '  "strengths": [\n'
        '    "Completely dispenses with recurrence",\n'
        '    "Highly parallelizable during training",\n'
        '    "Strong empirical results on multiple benchmarks",\n'
        '    "Attention mechanism provides interpretability"\n'
        "  ],\n"
        '  "weaknesses": [\n'
        '    "Quadratic complexity O(n^2) in sequence length",\n'
        '    "Performance on very long sequences may degrade without modifications"\n'
        "  ],\n"
        '  "questions": [\n'
        '    "How well does it generalize to tasks beyond NLP?",\n'
        '    "Can attention mechanisms fully replace convolution in vision tasks?"\n'
        "  ]\n"
        "}"
    ),
]


async def main() -> None:
    print("=" * 60)
    print("  ReproForge - PaperReader Demo")
    print("=" * 60)
    print()

    paper = SAMPLE_PAPER
    print(f"Paper: {paper.metadata.title}")
    print(f"Authors: {', '.join(paper.metadata.authors)}")
    print(f"arXiv: {paper.metadata.arxiv_id} ({paper.metadata.year})")
    print(f"Sections: {len(paper.sections)}")
    print()

    provider = ExampleProvider(responses=FAKE_RESPONSES)
    reader = PaperReader(
        config=AgentConfig(agent_type=AgentType.PAPER_READER, max_steps=10),
        provider=provider,
    )

    print("Reading paper...")
    note = await reader.read(paper)
    print()

    print("-" * 60)
    print("  TL;DR")
    print("-" * 60)
    print(note.tldr)
    print()

    print("-" * 60)
    print("  Contributions")
    print("-" * 60)
    for i, c in enumerate(note.contributions, 1):
        print(f"  {i}. {c.description}")
        if c.supporting_sections:
            print(f"     (supported by: {', '.join(c.supporting_sections)})")
    print()

    print("-" * 60)
    print("  Methodology Summary")
    print("-" * 60)
    print(f"  {note.methodology_summary}")
    print()

    print("-" * 60)
    print("  Key Findings")
    print("-" * 60)
    for k in note.key_findings:
        print(f"  [{k.dataset}] {k.metric_name}: {k.metric_value}")
        print(f"    {k.description}")
    print()

    print("-" * 60)
    print("  Strengths")
    print("-" * 60)
    for s in note.strengths:
        print(f"  + {s}")
    print()

    if note.weaknesses:
        print("-" * 60)
        print("  Weaknesses")
        print("-" * 60)
        for w in note.weaknesses:
            print(f"  - {w}")
        print()

    if note.questions:
        print("-" * 60)
        print("  Open Questions")
        print("-" * 60)
        for q in note.questions:
            print(f"  ? {q}")
        print()

    print("-" * 60)
    print("  Reading Trace")
    print("-" * 60)
    for i, sec in enumerate(note.reading_trace, 1):
        print(f"  {i}. {sec}")

    print()
    print(f"Total tokens used: {note.total_tokens_used}")
    print(f"Trace steps: {len(reader.trace.steps)}")
    print()
    print("=" * 60)
    print("  Demo complete. Use a real LLM for actual analysis.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
