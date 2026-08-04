"""arXiv API client for searching and downloading papers.

Provides async-friendly wrappers around the ``arxiv`` library for
querying metadata and fetching PDFs by arXiv ID.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from repro_forge.paper.schemas import PaperMetadata


def normalize_arxiv_id(raw_id: str) -> str:
    """Normalize modern or legacy arXiv references to an API identifier."""
    value = raw_id.strip().removeprefix("arXiv:").removeprefix("arxiv:")
    if "://" in value:
        path_parts = [part for part in urlparse(value).path.split("/") if part]
        if path_parts and path_parts[0].lower() in {"abs", "pdf"}:
            path_parts = path_parts[1:]
        value = "/".join(path_parts)
    if value.lower().endswith(".pdf"):
        value = value[:-4]
    return value.strip().strip("/")


class ArxivClient:
    """Client for interacting with the arXiv API.

    Supports searching by keyword, fetching paper metadata, and
    downloading PDFs.
    """

    def __init__(self) -> None:
        try:
            import arxiv
        except ImportError as exc:
            raise ImportError(
                "ArxivClient requires the optional 'arxiv' extra; "
                "install with `uv sync --extra arxiv`"
            ) from exc
        self._arxiv = arxiv
        self._client = arxiv.Client()

    def search(
        self,
        query: str,
        max_results: int = 10,
        sort_by: object | None = None,
    ) -> list[PaperMetadata]:
        """Search arXiv for papers matching a query.

        Args:
            query: Search query string (supports arXiv syntax).
            max_results: Maximum number of results to return.
            sort_by: Sorting criterion (e.g. ``arxiv.SortCriterion.Relevance``).

        Returns:
            A list of ``PaperMetadata`` for matching papers.
        """
        search = self._arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=sort_by or self._arxiv.SortCriterion.Relevance,
        )

        results: list[PaperMetadata] = []
        for result in self._client.results(search):
            results.append(self._result_to_metadata(result))
            if len(results) >= max_results:
                break
        return results

    def fetch_by_id(self, arxiv_id: str) -> PaperMetadata | None:
        """Fetch metadata for a specific arXiv paper by ID.

        Args:
            arxiv_id: The arXiv identifier (e.g. ``1706.03762`` or
                       ``arXiv:1706.03762``).

        Returns:
            ``PaperMetadata`` if found, ``None`` otherwise.
        """
        clean_id = self._clean_id(arxiv_id)
        search = self._arxiv.Search(id_list=[clean_id])
        try:
            result = next(self._client.results(search))
        except StopIteration:
            return None
        return self._result_to_metadata(result)

    def download_pdf(self, arxiv_id: str, output_dir: str | Path = ".") -> Path:
        """Download the PDF for a given arXiv paper.

        Args:
            arxiv_id: The arXiv identifier.
            output_dir: Directory to save the PDF into.

        Returns:
            Path to the downloaded PDF file.

        Raises:
            ValueError: If the paper could not be found.
        """
        clean_id = self._clean_id(arxiv_id)
        search = self._arxiv.Search(id_list=[clean_id])
        try:
            result = next(self._client.results(search))
        except StopIteration as err:
            raise ValueError(f"Paper not found: {arxiv_id}") from err

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = clean_id.replace("/", "_").replace("\\", "_") + ".pdf"
        target = out_dir / safe_filename
        result.download_pdf(dirpath=str(out_dir), filename=safe_filename)
        return target

    def _result_to_metadata(self, result: Any) -> PaperMetadata:
        """Convert an ``arxiv.Result`` to ``PaperMetadata``."""
        return PaperMetadata(
            title=result.title or "",
            authors=[a.name for a in result.authors],
            arxiv_id=self._clean_id(str(result.entry_id)),
            doi=result.doi or "",
            year=result.published.year if result.published else None,
            venue="arXiv",
            url=result.entry_id or "",
            abstract=result.summary or "",
        )

    @staticmethod
    def _clean_id(raw_id: str) -> str:
        """Normalize an arXiv ID to the canonical form (e.g. ``1706.03762``)."""
        return normalize_arxiv_id(raw_id)
