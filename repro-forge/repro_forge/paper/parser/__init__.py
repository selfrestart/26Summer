"""Paper source parsers, loaded lazily because their dependencies are optional."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from repro_forge.paper.parser.arxiv_api import ArxivClient
    from repro_forge.paper.parser.pdf_parser import PDFParser

__all__ = ["ArxivClient", "PDFParser"]


def __getattr__(name: str) -> object:
    if name == "ArxivClient":
        from repro_forge.paper.parser.arxiv_api import ArxivClient

        return ArxivClient
    if name == "PDFParser":
        from repro_forge.paper.parser.pdf_parser import PDFParser

        return PDFParser
    raise AttributeError(name)
