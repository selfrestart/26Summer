"""Tests for paper data models."""

from repro_forge.paper.schemas import Contribution
from repro_forge.paper.schemas import KeyFinding
from repro_forge.paper.schemas import Paper
from repro_forge.paper.schemas import PaperChunk
from repro_forge.paper.schemas import PaperMetadata
from repro_forge.paper.schemas import PaperNote
from repro_forge.paper.schemas import Section
from repro_forge.paper.schemas import SectionType


class TestSection:
    def test_create_section(self) -> None:
        s = Section(title="Introduction", content="This paper proposes...")
        assert s.title == "Introduction"
        assert s.section_type == SectionType.UNKNOWN
        assert s.token_count == 0

    def test_section_type_assignment(self) -> None:
        s = Section(
            title="Abstract",
            content="...",
            section_type=SectionType.ABSTRACT,
        )
        assert s.section_type == SectionType.ABSTRACT
        assert repr(s) == "Section(title='Abstract', type=abstract)"


class TestPaperMetadata:
    def test_default_metadata(self) -> None:
        m = PaperMetadata()
        assert m.title == ""
        assert m.authors == []
        assert m.arxiv_id == ""


class TestPaper:
    def test_empty_paper(self) -> None:
        p = Paper()
        assert p.total_pages == 0
        assert p.total_tokens == 0
        assert p.section_titles == []
        assert p.abstract_section is None
        assert p.method_sections == []

    def test_section_titles(self) -> None:
        p = Paper(
            sections=[
                Section(title="Abstract", content="...", section_type=SectionType.ABSTRACT),
                Section(title="Method", content="...", section_type=SectionType.METHOD),
            ]
        )
        assert p.section_titles == ["Abstract", "Method"]
        assert p.abstract_section is not None
        assert p.abstract_section.title == "Abstract"
        assert len(p.method_sections) == 1

    def test_total_tokens(self) -> None:
        p = Paper(
            sections=[
                Section(title="Intro", content="hello world", token_count=10),
                Section(title="Method", content="longer content here", token_count=20),
            ]
        )
        p.total_tokens = sum(s.token_count for s in p.sections)
        assert p.total_tokens == 30


class TestPaperChunk:
    def test_create_chunk(self) -> None:
        c = PaperChunk(
            text="chunk content",
            section_title="Method",
            section_type=SectionType.METHOD,
            chunk_index=0,
            token_count=100,
        )
        assert c.chunk_index == 0
        assert c.section_type == SectionType.METHOD


class TestPaperNote:
    def test_empty_note(self) -> None:
        n = PaperNote()
        assert n.tldr == ""
        assert n.contributions == []
        assert n.summary() == ""

    def test_full_note(self) -> None:
        n = PaperNote(
            arxiv_id="1706.03762",
            title="Attention Is All You Need",
            tldr="Proposes Transformer architecture for sequence transduction.",
            contributions=[
                Contribution(description="Self-attention mechanism"),
                Contribution(description="Multi-head attention", confidence=0.9),
            ],
            methodology_summary="Encoder-decoder with attention.",
            key_findings=[
                KeyFinding(
                    description="Achieved SOTA on WMT 2014",
                    metric_name="BLEU",
                    metric_value="28.4",
                    dataset="WMT 2014 En-De",
                ),
            ],
            strengths=["Parallelizable", "Captures long-range dependencies"],
            weaknesses=["Quadratic complexity in sequence length"],
            questions=["Can attention replace all recurrent architectures?"],
            reading_trace=["Abstract", "Introduction", "Method", "Experiments"],
        )
        assert "Transformer" in n.tldr
        assert len(n.contributions) == 2
        assert n.contributions[1].confidence == 0.9
        assert n.key_findings[0].metric_value == "28.4"
        assert "Quadratic" in n.weaknesses[0]
        assert "reading_trace" in n.model_dump()

    def test_summary_compact(self) -> None:
        n = PaperNote(
            tldr="A novel approach to image classification.",
            contributions=[
                Contribution(description="Residual connections"),
            ],
            key_findings=[
                KeyFinding(
                    description="Achieved SOTA", metric_name="Accuracy", metric_value="94.5%"
                ),
            ],
        )
        s = n.summary()
        assert "A novel approach" in s
        assert "Residual connections" in s
        assert "Accuracy=94.5%" in s
