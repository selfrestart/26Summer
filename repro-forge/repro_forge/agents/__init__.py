"""Specialized paper-reading and methodology-extraction agents."""

from repro_forge.agents.methodologist import Methodologist
from repro_forge.agents.paper_reader import PAPER_READER_SYSTEM_PROMPT
from repro_forge.agents.paper_reader import PAPER_READER_TOOLS
from repro_forge.agents.paper_reader import PaperReader

__all__ = [
    "PAPER_READER_SYSTEM_PROMPT",
    "PAPER_READER_TOOLS",
    "Methodologist",
    "PaperReader",
]
