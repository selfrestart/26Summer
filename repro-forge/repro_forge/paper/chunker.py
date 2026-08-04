"""Token-aware paper chunking that respects section boundaries.

Splits a ``Paper`` into ``PaperChunk`` segments for agent consumption,
ensuring each chunk stays within a token budget while maintaining
semantic coherence (sections are never split across chunks unless
absolutely necessary).
"""

from __future__ import annotations

from repro_forge.paper.schemas import Paper
from repro_forge.paper.schemas import PaperChunk
from repro_forge.paper.schemas import Section
from repro_forge.paper.schemas import SectionType


class PaperChunker:
    """Splits a Paper into token-bounded chunks for agent processing.

    Chunking strategy:
    1. Try to keep each complete section as a single chunk.
    2. If a section exceeds ``max_tokens``, split it at paragraph boundaries.
    3. Merge consecutive small sections into one chunk to reduce overhead.
    """

    def __init__(self, max_tokens: int = 4000, min_tokens: int = 500) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero")
        if min_tokens < 0:
            raise ValueError("min_tokens must not be negative")
        self.max_tokens = max_tokens
        self.min_tokens = min_tokens

    def chunk(self, paper: Paper) -> list[PaperChunk]:
        """Split a paper into token-bounded chunks.

        Args:
            paper: The parsed ``Paper`` to chunk.

        Returns:
            A list of ``PaperChunk`` objects ready for agent consumption.
        """
        chunks: list[PaperChunk] = []
        chunk_index = 0

        buffer_text: list[str] = []
        buffer_title = ""
        sections_to_process = [section for section in paper.sections if section.content.strip()]
        if not sections_to_process:
            return []

        buffer_type = sections_to_process[0].section_type
        buffer_tokens = 0

        for section in sections_to_process:
            sec_tokens = max(section.token_count, self._estimate_tokens(section.content))

            # Small section — merge into buffer
            if buffer_tokens + sec_tokens <= self.max_tokens:
                if buffer_text:
                    buffer_text.append("")
                buffer_text.append(f"## {section.title}")
                buffer_text.append(section.content)
                if not buffer_tokens:
                    buffer_title = section.title
                    buffer_type = section.section_type
                buffer_tokens += sec_tokens
                continue

            # Flush buffer before adding large section
            if buffer_text:
                chunks.append(
                    self._make_chunk(
                        "\n".join(buffer_text),
                        buffer_title,
                        buffer_type,
                        chunk_index,
                        buffer_tokens,
                    )
                )
                chunk_index += 1
                buffer_text = []
                buffer_tokens = 0

            # Large section — split or keep whole
            if sec_tokens <= self.max_tokens:
                chunks.append(
                    self._make_chunk(
                        f"## {section.title}\n{section.content}",
                        section.title,
                        section.section_type,
                        chunk_index,
                        sec_tokens,
                    )
                )
                chunk_index += 1
            else:
                for sub_chunk in self._split_long_section(section, chunk_index):
                    chunks.append(sub_chunk)
                    chunk_index += 1

        if buffer_text:
            chunks.append(
                self._make_chunk(
                    "\n".join(buffer_text),
                    buffer_title,
                    buffer_type,
                    chunk_index,
                    buffer_tokens,
                )
            )

        return chunks

    def _split_long_section(self, section: Section, start_index: int) -> list[PaperChunk]:
        """Split an over-long section at paragraph boundaries."""
        paragraphs = section.content.split("\n\n")
        chunks: list[PaperChunk] = []
        buffer: list[str] = []
        buffer_tokens = 0
        chunk_index = start_index

        for para in paragraphs:
            if not para.strip():
                continue
            para_tokens = self._estimate_tokens(para)

            if para_tokens > self.max_tokens:
                # Single huge paragraph — force-split by fixed character count
                if buffer:
                    chunks.append(
                        self._make_chunk(
                            "\n\n".join(buffer),
                            section.title,
                            section.section_type,
                            chunk_index,
                            buffer_tokens,
                        )
                    )
                    chunk_index += 1
                    buffer = []
                    buffer_tokens = 0
                start = 0
                while start < len(para):
                    end = min(len(para), start + self.max_tokens * 4)
                    if end < len(para):
                        boundary = para.rfind(" ", start, end)
                        if boundary > start:
                            end = boundary
                    sub = para[start:end]
                    sub_tokens = max(1, (len(sub) + 3) // 4)
                    chunks.append(
                        self._make_chunk(
                            f"## {section.title} (continued)\n{sub}",
                            section.title,
                            section.section_type,
                            chunk_index,
                            sub_tokens,
                        )
                    )
                    chunk_index += 1
                    start = end
                    while start < len(para) and para[start].isspace():
                        start += 1
                continue

            if buffer_tokens + para_tokens > self.max_tokens and buffer:
                chunks.append(
                    self._make_chunk(
                        f"## {section.title} (continued)\n" + "\n\n".join(buffer),
                        section.title,
                        section.section_type,
                        chunk_index,
                        buffer_tokens,
                    )
                )
                chunk_index += 1
                buffer = []
                buffer_tokens = 0
            buffer.append(para)
            buffer_tokens += para_tokens

        if buffer:
            chunks.append(
                self._make_chunk(
                    f"## {section.title} (continued)\n" + "\n\n".join(buffer),
                    section.title,
                    section.section_type,
                    chunk_index,
                    buffer_tokens,
                )
            )

        return chunks

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Return a positive, conservative estimate for non-empty text."""
        if not text:
            return 0
        return max(1, (len(text) + 3) // 4)

    def _make_chunk(
        self,
        text: str,
        section_title: str,
        section_type: SectionType,
        chunk_index: int,
        token_count: int,
    ) -> PaperChunk:
        return PaperChunk(
            text=text.strip(),
            section_title=section_title,
            section_type=section_type,
            chunk_index=chunk_index,
            token_count=token_count,
        )
