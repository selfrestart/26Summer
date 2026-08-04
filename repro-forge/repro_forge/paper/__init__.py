"""Public paper-domain API for the P1 reading workflow."""

from typing import TYPE_CHECKING

from repro_forge.paper.chunker import PaperChunker
from repro_forge.paper.schemas import Contribution
from repro_forge.paper.schemas import KeyFinding
from repro_forge.paper.schemas import Paper
from repro_forge.paper.schemas import PaperChunk
from repro_forge.paper.schemas import PaperMetadata
from repro_forge.paper.schemas import PaperNote
from repro_forge.paper.schemas import Section
from repro_forge.paper.schemas import SectionType

if TYPE_CHECKING:
    from repro_forge.paper.parser.arxiv_api import ArxivClient
    from repro_forge.paper.parser.pdf_parser import PDFParser
    from repro_forge.paper.pipeline import PaperPipeline

__all__ = [
    "ArxivClient",
    "Contribution",
    "KeyFinding",
    "PDFParser",
    "Paper",
    "PaperChunk",
    "PaperChunker",
    "PaperMetadata",
    "PaperNote",
    "PaperPipeline",
    "Section",
    "SectionType",
]


def __getattr__(name: str) -> object:
    if name == "ArxivClient":
        from repro_forge.paper.parser.arxiv_api import ArxivClient

        return ArxivClient
    if name == "PDFParser":
        from repro_forge.paper.parser.pdf_parser import PDFParser

        return PDFParser
    if name == "PaperPipeline":
        from repro_forge.paper.pipeline import PaperPipeline

        return PaperPipeline
    raise AttributeError(name)
