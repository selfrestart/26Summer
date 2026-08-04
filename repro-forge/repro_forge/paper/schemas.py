"""Data models for academic papers and reading notes.

Defines the structured representation of parsed papers (``Paper``,
``Section``) and the output of the PaperReader agent (``PaperNote``).
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel
from pydantic import Field


class SectionType(StrEnum):
    """Common section categories in CS papers."""

    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    RELATED_WORK = "related_work"
    METHOD = "method"
    EXPERIMENTS = "experiments"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    APPENDIX = "appendix"
    REFERENCES = "references"
    UNKNOWN = "unknown"


class Section(BaseModel):
    """A single section of a paper."""

    title: str
    content: str
    section_type: SectionType = SectionType.UNKNOWN
    page_start: int = 0
    page_end: int = 0
    token_count: int = 0

    def __repr__(self) -> str:
        return f"Section(title={self.title!r}, type={self.section_type.value})"


class PaperMetadata(BaseModel):
    """Bibliographic metadata for a paper."""

    title: str = ""
    authors: list[str] = Field(default_factory=list)
    arxiv_id: str = ""
    doi: str = ""
    year: int | None = None
    venue: str = ""
    url: str = ""
    abstract: str = ""


class Paper(BaseModel):
    """A parsed academic paper with metadata and structured sections."""

    metadata: PaperMetadata = Field(default_factory=PaperMetadata)
    sections: list[Section] = Field(default_factory=list)
    raw_text: str = ""
    total_pages: int = 0
    total_tokens: int = 0
    source: str = ""

    @property
    def abstract_section(self) -> Section | None:
        for sec in self.sections:
            if sec.section_type == SectionType.ABSTRACT:
                return sec
        return None

    @property
    def method_sections(self) -> list[Section]:
        return [s for s in self.sections if s.section_type == SectionType.METHOD]

    @property
    def section_titles(self) -> list[str]:
        return [s.title for s in self.sections]


class PaperChunk(BaseModel):
    """A token-bounded chunk of paper content for agent consumption."""

    text: str
    section_title: str
    section_type: SectionType
    chunk_index: int
    token_count: int


class Contribution(BaseModel):
    """A claimed contribution extracted from the paper."""

    description: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    supporting_sections: list[str] = Field(default_factory=list)


class KeyFinding(BaseModel):
    """A key experimental result or finding."""

    description: str
    metric_name: str = ""
    metric_value: str = ""
    dataset: str = ""


class PaperNote(BaseModel):
    """Structured output of the PaperReader agent.

    This is the final deliverable after an agent has read a paper.
    """

    paper_id: str = ""
    arxiv_id: str = ""
    title: str = ""

    tldr: str = ""
    contributions: list[Contribution] = Field(default_factory=list)
    methodology_summary: str = ""
    key_findings: list[KeyFinding] = Field(default_factory=list)
    section_notes: dict[str, str] = Field(default_factory=dict)

    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)

    reading_trace: list[str] = Field(default_factory=list)
    total_tokens_used: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    def summary(self) -> str:
        """A compact one-paragraph summary for quick reference."""
        parts: list[str] = []
        if self.tldr:
            parts.append(self.tldr)
        if self.contributions:
            parts.append(
                "Contributions: " + "; ".join(c.description for c in self.contributions[:3])
            )
        if self.key_findings:
            parts.append(
                "Key results: "
                + "; ".join(f"{k.metric_name}={k.metric_value}" for k in self.key_findings[:3])
            )
        return " | ".join(parts)
