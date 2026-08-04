"""PDF parser for academic papers using PyMuPDF (fitz).

Extracts text with layout-aware section detection and produces
a structured ``Paper`` object.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from typing import ClassVar

from repro_forge.paper.schemas import Paper
from repro_forge.paper.schemas import PaperMetadata
from repro_forge.paper.schemas import Section
from repro_forge.paper.schemas import SectionType


class PDFParser:
    """Parses academic paper PDFs into structured ``Paper`` objects.

    Uses PyMuPDF for fast, high-quality text extraction. Detects
    section boundaries via common heading patterns found in CS papers.
    """

    # Common section heading patterns in CS papers (case-insensitive)
    _SECTION_PATTERNS: ClassVar[list[tuple[str, SectionType]]] = [
        (r"^\d*\.?\s*abstract\b", SectionType.ABSTRACT),
        (r"^\d*\.?\s*introduction\b", SectionType.INTRODUCTION),
        (
            r"^\d*\.?\s*(related\s+work|background|previous\s+work|literature\s+review)\b",
            SectionType.RELATED_WORK,
        ),
        (
            r"^\d*\.?\s*(method|approach|model|architecture|framework|proposed)\b",
            SectionType.METHOD,
        ),
        (r"^\d*\.?\s*(experiments?|evaluation|implementation|setup)\b", SectionType.EXPERIMENTS),
        (r"^\d*\.?\s*(results?|findings?|performance)\b", SectionType.RESULTS),
        (r"^\d*\.?\s*(discussion|analysis)\b", SectionType.DISCUSSION),
        (r"^\d*\.?\s*(conclusion|summary|future\s+work)\b", SectionType.CONCLUSION),
        (r"^\d*\.?\s*(appendix|supplementary)", SectionType.APPENDIX),
        (r"^\d*\.?\s*references?\b", SectionType.REFERENCES),
    ]

    def __init__(self) -> None:
        self._patterns: list[tuple[re.Pattern[str], SectionType]] = [
            (re.compile(pat, re.IGNORECASE), stype) for pat, stype in self._SECTION_PATTERNS
        ]

    def parse(self, file_path: str | Path) -> Paper:
        """Parse a PDF file into a structured Paper object.

        Args:
            file_path: Path to a PDF file.

        Returns:
            A ``Paper`` with metadata and structured sections.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file is not a valid PDF.
        """
        try:
            import fitz
        except ImportError as exc:
            raise ImportError(
                "PDFParser requires the optional 'pdf' extra; install with `uv sync --extra pdf`"
            ) from exc

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        doc = fitz.open(str(path))
        try:
            metadata = self._extract_metadata(doc, path)
            full_text, pages_text = self._extract_text(doc)
            sections = self._detect_sections(pages_text)

            paper = Paper(
                metadata=metadata,
                sections=sections,
                raw_text=full_text,
                total_pages=len(doc),
                source=str(path.absolute()),
            )
            paper.total_tokens = sum(s.token_count for s in sections)
            return paper
        finally:
            doc.close()

    def _extract_metadata(self, doc: Any, path: Path) -> PaperMetadata:
        """Extract bibliographic metadata from PDF info dict and filename."""
        df = getattr(doc, "metadata", None) or {}
        title = str(df.get("title", ""))
        authors_str = str(df.get("author", ""))
        authors = [a.strip() for a in authors_str.split(";") if a.strip()] if authors_str else []

        return PaperMetadata(
            title=title,
            authors=authors,
            url=str(path.absolute()),
        )

    def _extract_text(self, doc: Any) -> tuple[str, list[str]]:
        """Extract raw text from all pages.

        Returns:
            A tuple of (full_text, list_of_page_texts).
        """
        pages: list[str] = []
        for page in doc:
            text = page.get_text()
            pages.append(text)
        return "\n".join(pages), pages

    def _detect_sections(self, pages_text: list[str]) -> list[Section]:
        """Detect section boundaries by scanning for heading patterns.

        Algorithm: Walk through the text line by line. When a line matches
        a section heading pattern, start a new section. All subsequent lines
        belong to that section until the next heading is detected.
        """
        lines: list[tuple[str, int]] = []
        for page_number, page_text in enumerate(pages_text, start=1):
            lines.extend((line, page_number) for line in page_text.split("\n"))
        sections: list[Section] = []
        current_title = "Preamble"
        current_type = SectionType.UNKNOWN
        current_lines: list[str] = []
        current_start_page = 1
        current_end_page = 1

        for line, page_number in lines:
            matched_type = self._match_heading(line)
            if matched_type is not None:
                if current_lines:
                    text = "\n".join(current_lines).strip()
                    if text:
                        sections.append(
                            self._make_section(
                                current_title,
                                text,
                                current_type,
                                current_start_page,
                                current_end_page,
                            )
                        )
                current_title = line.strip()
                current_type = matched_type
                current_lines = []
                current_start_page = page_number
                current_end_page = page_number
            else:
                current_end_page = page_number
                current_lines.append(line)

        if current_lines:
            text = "\n".join(current_lines).strip()
            if text:
                sections.append(
                    self._make_section(
                        current_title,
                        text,
                        current_type,
                        current_start_page,
                        current_end_page,
                    )
                )

        return sections

    def _match_heading(self, line: str) -> SectionType | None:
        """Check if a line matches any known section heading pattern."""
        stripped = line.strip()
        if len(stripped) > 60:
            return None
        if stripped.endswith((".", "?", "!", ";")):
            return None
        for pattern, stype in self._patterns:
            if pattern.match(stripped):
                return stype
        return None

    def _make_section(
        self,
        title: str,
        content: str,
        section_type: SectionType,
        start_page: int,
        total_pages: int,
    ) -> Section:
        token_count = len(content) // 4
        return Section(
            title=title,
            content=content,
            section_type=section_type,
            page_start=start_page,
            page_end=total_pages,
            token_count=token_count,
        )
