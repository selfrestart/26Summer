"""Optional dependency boundaries for P1 integrations."""

from __future__ import annotations

import builtins

import pytest

from repro_forge.paper.parser.arxiv_api import ArxivClient
from repro_forge.paper.parser.pdf_parser import PDFParser
from repro_forge.providers.openai_provider import OpenAIProvider


def _block_import(name: str):
    original = builtins.__import__

    def guarded_import(
        module_name: str,
        globals_: object | None = None,
        locals_: object | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if module_name == name:
            raise ImportError(f"blocked optional dependency: {name}")
        return original(module_name, globals_, locals_, fromlist, level)

    return guarded_import


def test_openai_provider_reports_missing_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builtins, "__import__", _block_import("openai"))

    with pytest.raises(ImportError, match="openai"):
        OpenAIProvider()


def test_pdf_parser_reports_missing_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builtins, "__import__", _block_import("fitz"))

    with pytest.raises(ImportError, match="pdf"):
        PDFParser().parse("missing.pdf")


def test_arxiv_client_reports_missing_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builtins, "__import__", _block_import("arxiv"))

    with pytest.raises(ImportError, match="arxiv"):
        ArxivClient()
