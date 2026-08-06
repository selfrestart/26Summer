"""MethodologyPipeline — compose paper parsing with Methodologist.

P2 orchestration layer that combines the P1 paper pipeline with the
Methodologist agent. It accepts a parsed ``Paper``, a local PDF, or an
arXiv identifier and returns an evidence-grounded ``MethodAnalysis``.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from repro_forge.paper.extractor.evidence import PaperEvidenceView
from repro_forge.paper.extractor.schemas import MethodAnalysis
from repro_forge.paper.pipeline import PaperPipeline
from repro_forge.paper.schemas import Paper
from repro_forge.paper.schemas import PaperNote
from repro_forge.providers.base import BaseProvider

if TYPE_CHECKING:
    from repro_forge.agents.methodologist import Methodologist


class MethodologyPipeline:
    """Orchestrate P2 methodology extraction end to end.

    Composition is explicit: the P1 ``PaperPipeline`` handles parsing,
    and the Methodologist handles evidence-grounded extraction. The
    ``MethodologyPipeline`` is the composition root; it does not change
    P1's public API.
    """

    def __init__(
        self,
        paper_pipeline: PaperPipeline | None = None,
        methodologist: Methodologist | None = None,
        provider: BaseProvider | None = None,
    ) -> None:
        if paper_pipeline is None:
            paper_pipeline = PaperPipeline(provider=provider)
        if methodologist is None and provider is not None:
            from repro_forge.agents.methodologist import Methodologist

            methodologist = Methodologist(provider=provider)
        self.paper_pipeline = paper_pipeline
        self._methodologist = methodologist

    @property
    def methodologist(self) -> Methodologist:
        """Return the configured methodologist, failing before LLM use if absent."""
        if self._methodologist is None:
            raise ValueError(
                "MethodologyPipeline requires a provider or methodologist; "
                "inject a BaseProvider before analysis"
            )
        return self._methodologist

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze(
        self,
        paper: Paper,
        paper_note: PaperNote | None = None,
    ) -> MethodAnalysis:
        """Extract methodology from a parsed paper.

        Args:
            paper: A parsed ``Paper`` (evidence must come from here).
            paper_note: Optional P1 reading note used only as context hints.

        Returns:
            An evidence-grounded ``MethodAnalysis``.
        """
        view = PaperEvidenceView(paper)
        return await self.methodologist.analyze(view, paper_note)

    async def analyze_pdf(
        self,
        file_path: str | Path,
        read_first: bool = False,
    ) -> MethodAnalysis:
        """Parse a local PDF and extract methodology.

        Args:
            file_path: Path to a PDF file.
            read_first: If True, run P1 PaperReader first and pass its
                note as context. If False, skip reading and extract
                directly from the parsed paper.

        Returns:
            An evidence-grounded ``MethodAnalysis``.
        """
        paper = self.paper_pipeline.parse_pdf(file_path)
        note = await self._maybe_read_first(paper, read_first)
        return await self.analyze(paper, note)

    async def analyze_arxiv(
        self,
        arxiv_id: str,
        output_dir: str | Path = ".",
        read_first: bool = False,
    ) -> MethodAnalysis:
        """Download an arXiv paper, parse it, and extract methodology.

        Args:
            arxiv_id: arXiv identifier (e.g. ``1706.03762``).
            output_dir: Directory to download the PDF into.
            read_first: Whether to run P1 PaperReader first (see
                ``analyze_pdf``).

        Returns:
            An evidence-grounded ``MethodAnalysis``.
        """
        pdf_path = self.paper_pipeline.download_arxiv(arxiv_id, output_dir)
        return await self.analyze_pdf(pdf_path, read_first=read_first)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _maybe_read_first(
        self,
        paper: Paper,
        read_first: bool,
    ) -> PaperNote | None:
        if not read_first:
            return None
        return await self.paper_pipeline.read(paper)
