"""Tests for PaperChunker."""

import pytest

from repro_forge.paper.chunker import PaperChunker
from repro_forge.paper.schemas import Paper
from repro_forge.paper.schemas import Section
from repro_forge.paper.schemas import SectionType


def _make_section(title: str, content: str, stype: SectionType | None = None) -> Section:
    return Section(
        title=title,
        content=content,
        section_type=stype or SectionType.UNKNOWN,
        token_count=len(content) // 4,
    )


class TestPaperChunker:
    def test_rejects_non_positive_token_budget(self) -> None:
        with pytest.raises(ValueError, match="max_tokens"):
            PaperChunker(max_tokens=0)

    def test_single_short_section(self) -> None:
        paper = Paper(
            sections=[
                _make_section("Intro", "Short introduction content."),
            ]
        )
        chunker = PaperChunker(max_tokens=1000)
        chunks = chunker.chunk(paper)
        assert len(chunks) == 1
        assert chunks[0].section_title == "Intro"
        assert "Short introduction" in chunks[0].text

    def test_multiple_short_sections_merged(self) -> None:
        paper = Paper(
            sections=[
                _make_section("A", "a" * 40),
                _make_section("B", "b" * 40),
            ]
        )
        chunker = PaperChunker(max_tokens=1000, min_tokens=1)
        chunks = chunker.chunk(paper)
        assert len(chunks) == 1
        assert "## A" in chunks[0].text
        assert "## B" in chunks[0].text

    def test_large_section_split(self) -> None:
        paper = Paper(
            sections=[
                _make_section("Long", "x" * 20000),
            ]
        )
        chunker = PaperChunker(max_tokens=1000)
        chunks = chunker.chunk(paper)
        assert len(chunks) > 1
        for c in chunks:
            assert c.section_title == "Long"

    def test_long_paragraph_split_preserves_content(self) -> None:
        content = "alpha " * 5000
        paper = Paper(sections=[_make_section("Long", content)])
        chunks = PaperChunker(max_tokens=100).chunk(paper)

        assert "alpha" in " ".join(chunk.text for chunk in chunks)
        assert sum(chunk.text.count("alpha") for chunk in chunks) == 5000
        assert all(chunk.token_count <= 100 for chunk in chunks)

    def test_mixed_sections(self) -> None:
        paper = Paper(
            sections=[
                _make_section("A", "a" * 40, SectionType.ABSTRACT),
                _make_section("B", "b" * 40, SectionType.METHOD),
            ]
        )
        chunker = PaperChunker(max_tokens=1000, min_tokens=1)
        chunks = chunker.chunk(paper)
        assert len(chunks) == 1

    def test_chunk_token_count(self) -> None:
        content = "hello " * 100
        paper = Paper(sections=[_make_section("Test", content)])
        chunker = PaperChunker(max_tokens=1000)
        chunks = chunker.chunk(paper)
        assert chunks[0].token_count > 0

    def test_empty_paper(self) -> None:
        paper = Paper(sections=[])
        chunker = PaperChunker()
        chunks = chunker.chunk(paper)
        assert chunks == []
