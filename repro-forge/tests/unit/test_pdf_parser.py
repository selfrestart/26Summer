"""PDF parser behavior with a fake PyMuPDF module."""

from __future__ import annotations

import sys
import types

from repro_forge.paper.parser.pdf_parser import PDFParser
from repro_forge.paper.schemas import SectionType


def test_pdf_parser_tracks_section_page_ranges(tmp_path, monkeypatch) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"placeholder")

    class Page:
        def __init__(self, text: str) -> None:
            self.text = text

        def get_text(self) -> str:
            return self.text

    class Document:
        def __init__(self) -> None:
            self.metadata = {"title": "Page test", "author": "Author"}
            self.pages = [
                Page("Abstract\nThis is abstract text."),
                Page("Method\nThis is method text."),
            ]

        def __iter__(self):
            return iter(self.pages)

        def __len__(self) -> int:
            return len(self.pages)

        def close(self) -> None:
            return

    monkeypatch.setitem(sys.modules, "fitz", types.SimpleNamespace(open=lambda _: Document()))

    paper = PDFParser().parse(pdf_path)

    assert [section.section_type for section in paper.sections] == [
        SectionType.ABSTRACT,
        SectionType.METHOD,
    ]
    assert paper.sections[0].page_start == 1
    assert paper.sections[0].page_end == 1
    assert paper.sections[1].page_start == 2
    assert paper.sections[1].page_end == 2


def test_pdf_parser_does_not_treat_a_sentence_as_a_section_heading() -> None:
    parser = PDFParser()

    assert parser._match_heading("Results show consistent improvements on every dataset.") is None
    assert parser._match_heading("Results") == SectionType.RESULTS


def test_pdf_parser_recognizes_decimal_section_headings() -> None:
    parser = PDFParser()

    assert parser._match_heading("2.1 Method") == SectionType.METHOD
    assert parser._match_heading("3.1 Experimental Setup") == SectionType.EXPERIMENTS
