"""Tests for the P1 paper-reading orchestration layer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repro_forge.paper import Paper
from repro_forge.paper import PaperMetadata
from repro_forge.paper import PaperPipeline
from repro_forge.paper import Section
from repro_forge.paper import SectionType
from repro_forge.providers.base import BaseProvider
from repro_forge.providers.base import LLMRequest
from repro_forge.providers.base import LLMResponse


class FakeProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__(model="fake")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        del request
        payload = {
            "tldr": "A tested paper-reading result.",
            "contributions": [],
            "methodology_summary": "",
            "key_findings": [],
            "strengths": [],
            "weaknesses": [],
            "questions": [],
        }
        return LLMResponse(content="DONE\n" + json.dumps(payload), model=self.model)

    async def generate_stream(self, request: LLMRequest):
        del request
        yield "DONE"

    @property
    def provider_name(self) -> str:
        return "fake"


def make_paper() -> Paper:
    return Paper(
        metadata=PaperMetadata(title="Pipeline paper", arxiv_id="1234.5678"),
        sections=[
            Section(
                title="Abstract",
                content="A short abstract for the pipeline.",
                section_type=SectionType.ABSTRACT,
            )
        ],
    )


class FakeParser:
    def __init__(self, paper: Paper) -> None:
        self.paper = paper
        self.paths: list[str] = []

    def parse(self, path: str | Path) -> Paper:
        self.paths.append(str(path))
        return self.paper


@pytest.mark.asyncio
async def test_read_arxiv_downloads_parses_and_reads(tmp_path) -> None:
    class FakeArxiv:
        def download_pdf(self, arxiv_id: str, output_dir: str | Path = ".") -> Path:
            return Path(output_dir) / f"{arxiv_id}.pdf"

    parser = FakeParser(make_paper())
    pipeline = PaperPipeline(
        parser=parser,
        arxiv_client=FakeArxiv(),
        provider=FakeProvider(),
    )

    note = await pipeline.read_arxiv("arXiv:1234.5678", tmp_path)

    assert parser.paths == [str(tmp_path / "1234.5678.pdf")]
    assert note.paper_id == "1234.5678"


def test_pipeline_delegates_arxiv_operations() -> None:
    class FakeArxiv:
        def search(self, query: str, max_results: int = 10) -> list[PaperMetadata]:
            return [PaperMetadata(title=query)] * max_results

        def fetch_by_id(self, arxiv_id: str) -> PaperMetadata:
            return PaperMetadata(arxiv_id=arxiv_id)

        def download_pdf(self, arxiv_id: str, output_dir: str | Path = ".") -> Path:
            return Path(output_dir) / f"{arxiv_id}.pdf"

    pipeline = PaperPipeline(arxiv_client=FakeArxiv())

    assert len(pipeline.search_arxiv("attention", max_results=2)) == 2
    assert pipeline.fetch_arxiv("1234.5678").arxiv_id == "1234.5678"
    assert pipeline.download_arxiv("1234.5678", "downloads") == Path("downloads/1234.5678.pdf")


@pytest.mark.parametrize(
    ("raw_id", "expected"),
    [
        ("https://arxiv.org/abs/1706.03762v2", "1706.03762v2"),
        ("https://arxiv.org/pdf/1706.03762.pdf", "1706.03762"),
        ("https://arxiv.org/abs/hep-th/9901001v3", "hep-th/9901001v3"),
    ],
)
def test_pipeline_normalizes_arxiv_url_before_delegation(
    raw_id: str,
    expected: str,
) -> None:
    class FakeArxiv:
        def fetch_by_id(self, arxiv_id: str) -> PaperMetadata:
            return PaperMetadata(arxiv_id=arxiv_id)

    pipeline = PaperPipeline(arxiv_client=FakeArxiv())

    assert pipeline.fetch_arxiv(raw_id).arxiv_id == expected


@pytest.mark.asyncio
async def test_read_delegates_to_paper_reader_and_returns_note() -> None:
    pipeline = PaperPipeline(provider=FakeProvider())

    note = await pipeline.read(make_paper())

    assert note.title == "Pipeline paper"
    assert note.tldr == "A tested paper-reading result."


@pytest.mark.asyncio
async def test_read_pdf_parses_then_reads() -> None:
    parser = FakeParser(make_paper())
    pipeline = PaperPipeline(parser=parser, provider=FakeProvider())

    note = await pipeline.read_pdf("paper.pdf")

    assert parser.paths == ["paper.pdf"]
    assert note.paper_id == "1234.5678"


def test_pipeline_requires_a_provider_for_reading() -> None:
    pipeline = PaperPipeline()

    with pytest.raises(ValueError, match="provider"):
        _ = pipeline.reader
