"""Orchestration for the P1 paper parsing and reading workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from repro_forge.agents.paper_reader import PaperReader
from repro_forge.paper.parser.arxiv_api import normalize_arxiv_id
from repro_forge.paper.parser.pdf_parser import PDFParser
from repro_forge.paper.schemas import Paper
from repro_forge.paper.schemas import PaperMetadata
from repro_forge.paper.schemas import PaperNote
from repro_forge.providers.base import BaseProvider


class ArxivProvider(Protocol):
    """Protocol for the optional arXiv client."""

    def search(self, query: str, max_results: int = 10) -> list[PaperMetadata]:
        """Search arXiv metadata."""

    def fetch_by_id(self, arxiv_id: str) -> PaperMetadata | None:
        """Fetch one arXiv record."""

    def download_pdf(self, arxiv_id: str, output_dir: str | Path = ".") -> Path:
        """Download one arXiv PDF."""


class PaperParser(Protocol):
    """Protocol implemented by local paper parsers."""

    def parse(self, file_path: str | Path) -> Paper:
        """Parse a local paper into the domain model."""


class PaperPipeline:
    """Compose source parsing, chunking, and PaperReader execution.

    The provider is deliberately injected. This keeps offline runs and tests
    deterministic and prevents accidentally making a billable network call.
    """

    def __init__(
        self,
        provider: BaseProvider | None = None,
        parser: PaperParser | None = None,
        arxiv_client: ArxivProvider | None = None,
        reader: PaperReader | None = None,
    ) -> None:
        self.provider = provider
        self.parser = parser or PDFParser()
        self.arxiv_client = arxiv_client
        self._reader = reader

    @property
    def reader(self) -> PaperReader:
        """Return the configured reader, failing before an LLM call if absent."""
        if self._reader is None:
            if self.provider is None:
                raise ValueError(
                    "PaperPipeline requires a provider or reader; "
                    "inject a BaseProvider before reading"
                )
            self._reader = PaperReader(provider=self.provider)
        return self._reader

    def parse_pdf(self, file_path: str | Path) -> Paper:
        """Parse a local PDF using the configured parser."""
        return self.parser.parse(file_path)

    def search_arxiv(self, query: str, max_results: int = 10) -> list[PaperMetadata]:
        """Search arXiv metadata, importing the optional client on demand."""
        return self._get_arxiv_client().search(query, max_results=max_results)

    def fetch_arxiv(self, arxiv_id: str) -> PaperMetadata | None:
        """Fetch metadata for one arXiv identifier."""
        return self._get_arxiv_client().fetch_by_id(self._normalize_arxiv_id(arxiv_id))

    def download_arxiv(self, arxiv_id: str, output_dir: str | Path = ".") -> Path:
        """Download an arXiv PDF and return its local path."""
        return self._get_arxiv_client().download_pdf(self._normalize_arxiv_id(arxiv_id), output_dir)

    async def read(self, paper: Paper) -> PaperNote:
        """Read a parsed paper with the configured PaperReader."""
        return await self.reader.read(paper)

    async def read_pdf(self, file_path: str | Path) -> PaperNote:
        """Parse and read a local PDF."""
        return await self.read(self.parse_pdf(file_path))

    async def read_arxiv(self, arxiv_id: str, output_dir: str | Path = ".") -> PaperNote:
        """Download an arXiv PDF, parse it, and return a reading note."""
        pdf_path = self.download_arxiv(arxiv_id, output_dir)
        return await self.read_pdf(pdf_path)

    def _get_arxiv_client(self) -> ArxivProvider:
        if self.arxiv_client is None:
            from repro_forge.paper.parser.arxiv_api import ArxivClient

            self.arxiv_client = ArxivClient()
        return self.arxiv_client

    @staticmethod
    def _normalize_arxiv_id(value: str) -> str:
        """Normalize an arXiv URL or prefixed identifier."""
        return normalize_arxiv_id(value)
