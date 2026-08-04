"""Integration test for the PaperReader pipeline.

Tests the full flow from paper parsing (with built-in test data)
through chunking to agent reading and note production.
"""

import pytest

from repro_forge.agents.paper_reader import PaperReader
from repro_forge.core.types import AgentConfig
from repro_forge.core.types import AgentType
from repro_forge.paper.chunker import PaperChunker
from repro_forge.paper.schemas import Paper
from repro_forge.paper.schemas import PaperMetadata
from repro_forge.paper.schemas import PaperNote
from repro_forge.paper.schemas import Section
from repro_forge.paper.schemas import SectionType
from tests.conftest import FakeLLMProvider


def _make_sample_paper() -> Paper:
    return Paper(
        metadata=PaperMetadata(
            title="Attention Is All You Need",
            authors=["Ashish Vaswani", "Noam Shazeer"],
            arxiv_id="1706.03762",
            year=2017,
        ),
        sections=[
            Section(
                title="Abstract",
                content="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train.",
                section_type=SectionType.ABSTRACT,
                token_count=60,
            ),
            Section(
                title="Introduction",
                content="Recurrent neural networks have been the state of the art in sequence modeling and transduction problems. Attention mechanisms have become an integral part of compelling sequence modeling.",
                section_type=SectionType.INTRODUCTION,
                token_count=30,
            ),
            Section(
                title="Model Architecture",
                content="Most competitive neural sequence transduction models have an encoder-decoder structure. The encoder maps an input sequence to a sequence of continuous representations. The decoder generates an output sequence one element at a time.",
                section_type=SectionType.METHOD,
                token_count=40,
            ),
            Section(
                title="Experiments",
                content="We trained on the WMT 2014 English-German dataset consisting of about 4.5 million sentence pairs. Our model achieves 28.4 BLEU on English-to-German translation.",
                section_type=SectionType.EXPERIMENTS,
                token_count=40,
            ),
            Section(
                title="Conclusion",
                content="We presented the Transformer, the first sequence transduction model based entirely on attention. We plan to extend the Transformer to problems involving input and output modalities other than text.",
                section_type=SectionType.CONCLUSION,
                token_count=30,
            ),
        ],
        total_pages=11,
        total_tokens=200,
    )


class TestPaperReaderPipeline:
    @pytest.mark.asyncio
    async def test_chunking_produces_valid_chunks(self) -> None:
        paper = _make_sample_paper()
        chunker = PaperChunker(max_tokens=500)
        chunks = chunker.chunk(paper)

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.text
            assert chunk.section_title
            assert chunk.token_count > 0

    @pytest.mark.asyncio
    async def test_full_pipeline_with_fake_provider(self) -> None:
        provider = FakeLLMProvider(
            responses=[
                "Let me start by listing all sections.",
                "Let me read the abstract to understand the paper.",
                "Let me read the model architecture section.",
                'DONE\n{"tldr": "The Transformer paper proposes a novel architecture based entirely on attention mechanisms, replacing recurrence. It achieves SOTA on WMT 2014 translation tasks with 28.4 BLEU.", "contributions": [{"description": "Self-attention mechanism for sequence transduction", "supporting_sections": ["Model Architecture"]}, {"description": "Multi-head attention enabling different representation subspaces", "supporting_sections": ["Model Architecture"]}], "methodology_summary": "Encoder-decoder architecture using multi-head self-attention and position-wise feed-forward networks.", "key_findings": [{"description": "28.4 BLEU on WMT 2014 En-De", "metric_name": "BLEU", "metric_value": "28.4", "dataset": "WMT 2014 En-De"}], "strengths": ["No recurrence needed", "Highly parallelizable", "State-of-the-art results"], "weaknesses": [], "questions": []}',
            ]
        )

        reader = PaperReader(
            config=AgentConfig(agent_type=AgentType.PAPER_READER, max_steps=10),
            provider=provider,
        )

        paper = _make_sample_paper()
        note = await reader.read(paper)

        assert isinstance(note, PaperNote)
        assert note.title == "Attention Is All You Need"
        assert "Transformer" in note.tldr
        assert len(note.contributions) >= 1
        assert (
            note.contributions[0].description
            == "Self-attention mechanism for sequence transduction"
        )
        assert note.key_findings[0].metric_name == "BLEU"
        assert "recurrence" in note.strengths[0].lower()
        assert len(note.reading_trace) >= 1

    @pytest.mark.asyncio
    async def test_pipeline_records_correct_metadata(self) -> None:
        provider = FakeLLMProvider(
            responses=[
                'DONE\n{"tldr": "A transformer paper.", "contributions": [], "methodology_summary": "", "key_findings": [], "strengths": [], "weaknesses": [], "questions": []}',
            ]
        )
        reader = PaperReader(
            config=AgentConfig(agent_type=AgentType.PAPER_READER, max_steps=3),
            provider=provider,
        )

        paper = _make_sample_paper()
        note = await reader.read(paper)

        assert note.paper_id == "1706.03762"
        assert note.title == "Attention Is All You Need"
