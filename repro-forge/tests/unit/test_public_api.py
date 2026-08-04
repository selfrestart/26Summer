"""Stable public import surface for the P1 paper-reading workflow."""

from repro_forge.agents import PaperReader
from repro_forge.paper import ArxivClient
from repro_forge.paper import Paper
from repro_forge.paper import PaperChunker
from repro_forge.paper import PaperPipeline
from repro_forge.paper import PDFParser
from repro_forge.providers import LLMToolCall
from repro_forge.providers import OpenAIProvider


def test_p1_public_exports_are_available() -> None:
    assert PaperReader.__name__ == "PaperReader"
    assert Paper.__name__ == "Paper"
    assert PaperChunker.__name__ == "PaperChunker"
    assert PaperPipeline.__name__ == "PaperPipeline"
    assert PDFParser.__name__ == "PDFParser"
    assert ArxivClient.__name__ == "ArxivClient"
    assert LLMToolCall.__name__ == "LLMToolCall"
    assert OpenAIProvider.__name__ == "OpenAIProvider"
