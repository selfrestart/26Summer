"""Command-line interface for the P1 paper-reading workflow."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections.abc import Sequence
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from repro_forge import __version__
from repro_forge.paper.schemas import PaperNote
from repro_forge.providers.base import BaseProvider


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repro-forge",
        description="Parse and read computer-science papers with ReproForge P1.",
    )
    parser.add_argument("--version", action="version", version=f"repro-forge {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    capabilities = subparsers.add_parser("capabilities", help="Show implemented P1 capabilities")
    capabilities.set_defaults(handler=_capabilities)

    read_pdf = subparsers.add_parser("read-pdf", help="Parse and read a local PDF")
    read_pdf.add_argument("path", type=Path)
    read_pdf.add_argument("--output", type=Path, help="Write the note as JSON")
    read_pdf.set_defaults(handler=_read_pdf)

    read_json = subparsers.add_parser("read-json", help="Read a serialized Paper JSON file")
    read_json.add_argument("path", type=Path)
    read_json.add_argument("--output", type=Path, help="Write the note as JSON")
    read_json.set_defaults(handler=_read_json)
    return parser


def _capabilities(_args: argparse.Namespace) -> int:
    print("P1 capabilities:")
    print("  paper-reading: PaperPipeline + PaperReader")
    print("  pdf: local PDF parsing (optional 'pdf' extra)")
    print("  arxiv: search, metadata, and PDF download (optional 'arxiv' extra)")
    print("  providers: OpenAI-compatible async provider (optional 'openai' extra)")
    return 0


def _is_local_endpoint(base_url: str) -> bool:
    """Return whether a compatible endpoint is local enough to run without a key."""
    hostname = urlparse(base_url).hostname
    if not hostname:
        return False
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return True
    try:
        address = ip_address(hostname)
    except ValueError:
        return "." not in hostname
    return address.is_private or address.is_loopback


def _provider() -> BaseProvider:
    from repro_forge.providers import OpenAIProvider

    load_dotenv(Path.cwd() / ".env", override=False)
    openai_api_key = os.getenv("OPENAI_API_KEY")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    api_key: str | None
    if openai_api_key:
        api_key = openai_api_key
        base_url = os.getenv("OPENAI_BASE_URL")
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
    elif deepseek_api_key:
        api_key = deepseek_api_key
        base_url = os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
        model = os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"
    else:
        base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL")
        if not base_url or not _is_local_endpoint(base_url):
            raise SystemExit(
                "OPENAI_API_KEY or DEEPSEEK_API_KEY is required for remote LLM-backed reading"
            )
        api_key = None
        model = os.getenv("OPENAI_MODEL") or os.getenv("DEEPSEEK_MODEL") or "gpt-4o"
    return OpenAIProvider(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )


def _write_note(note: PaperNote, output: Path | None) -> None:
    payload = note.model_dump(mode="json")
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if output:
        output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


def _read_pdf(args: argparse.Namespace) -> int:
    from repro_forge.paper import PaperPipeline

    note = asyncio.run(PaperPipeline(provider=_provider()).read_pdf(args.path))
    _write_note(note, args.output)
    return 0


def _read_json(args: argparse.Namespace) -> int:
    from repro_forge.paper import Paper
    from repro_forge.paper import PaperPipeline

    paper = Paper.model_validate_json(args.path.read_text(encoding="utf-8"))
    note = asyncio.run(PaperPipeline(provider=_provider()).read(paper))
    _write_note(note, args.output)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``repro-forge`` CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", _capabilities)
    return int(handler(args))
