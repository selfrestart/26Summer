"""Read-only evidence layer for methodology extraction.

Provides ``PaperEvidenceView`` that wraps a parsed ``Paper`` and gives
deterministic source hashing, section ID generation, and reusable
read/search utilities for both PaperReader and Methodologist.
"""

from __future__ import annotations

import hashlib
import re

from repro_forge.paper.schemas import Paper
from repro_forge.paper.schemas import Section


class PaperEvidenceView:
    """Read-only view of a paper for evidence-grounded extraction.

    Wraps a ``Paper`` and provides:
    - Deterministic ``source_hash`` from canonical content
    - Stable ``section_id`` per section
    - Chunk-aware section reading
    - Quote normalization and verification
    """

    def __init__(self, paper: Paper, chunk_size: int = 4000) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        self._paper = paper
        self._chunk_size = chunk_size
        self._source_hash = self._compute_source_hash()
        self._section_aliases = self._build_section_aliases()
        self._section_ids = self._build_section_ids()

    # ------------------------------------------------------------------
    # Public read methods
    # ------------------------------------------------------------------

    @property
    def paper(self) -> Paper:
        return self._paper

    @property
    def source_hash(self) -> str:
        return self._source_hash

    @property
    def section_ids(self) -> dict[str, str]:
        return dict(self._section_ids)

    def section_titles(self) -> list[str]:
        return list(self._section_aliases)

    def read_section(self, title: str, chunk_index: int = 0) -> str:
        resolved = self._resolve_section(title)
        if resolved is None:
            return f"Section '{title}' not found. Available: " + ", ".join(self._section_aliases)

        _, section, _ = resolved
        chunks = self._split_long_content(section.content, self._chunk_size * 4)
        if chunk_index < 0 or chunk_index >= len(chunks):
            return f"Chunk {chunk_index} out of range, max chunk: {len(chunks) - 1}"
        return chunks[chunk_index]

    def search(self, query: str) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        query_lower = query.lower().strip()
        if not query_lower:
            return results
        for index, section in enumerate(self._paper.sections):
            if query_lower in section.content.lower():
                alias = self._section_aliases[index]
                results.append(
                    {
                        "section_title": alias,
                        "section_id": self._section_ids[alias],
                        "snippet": self._extract_snippet(section.content, query),
                    }
                )
        return results

    def list_sections(self) -> str:
        titles = self._section_aliases
        return "Sections:\n" + "\n".join(f"  - {t}" for t in titles)

    def get_section_id(self, title: str) -> str:
        resolved = self._resolve_section(title)
        if resolved is None:
            return ""
        _, _, alias = resolved
        return self._section_ids[alias]

    def find_quote_chunk(self, quote: str, section_title: str) -> int | None:
        """Return the bounded chunk containing a quote, when one can be found."""
        resolved = self._resolve_section(section_title)
        normalized_quote = self.normalize_quote(quote)
        if resolved is None or not normalized_quote:
            return None
        _, section, _ = resolved
        chunks = self._split_long_content(section.content, self._chunk_size * 4)
        for index, chunk in enumerate(chunks):
            if normalized_quote in self.normalize_quote(chunk):
                return index
        return None

    # ------------------------------------------------------------------
    # Quote normalization and verification
    # ------------------------------------------------------------------

    @staticmethod
    def normalize_quote(quote: str) -> str:
        text = quote.strip()
        text = re.sub(r"-\n\s*", "-", text)
        text = re.sub(r"\n\s*", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def verify_quote_location(self, quote: str, section_title: str) -> bool:
        norm_quote = self.normalize_quote(quote)
        content = self._find_section_raw(section_title)
        if not content:
            return False
        norm_content = self.normalize_quote(content)
        return norm_quote in norm_content

    def verify_evidence(self, evidence_ref: object) -> str:
        from repro_forge.paper.extractor.schemas import EvidenceRef
        from repro_forge.paper.extractor.schemas import EvidenceStatus

        if not isinstance(evidence_ref, EvidenceRef):
            return EvidenceStatus.UNVERIFIED.value

        if not evidence_ref.quote:
            return EvidenceStatus.UNVERIFIED.value

        paper_id = self._paper.metadata.arxiv_id
        if evidence_ref.paper_id != paper_id:
            return EvidenceStatus.UNVERIFIED.value

        if evidence_ref.source_hash != self._source_hash:
            return EvidenceStatus.UNVERIFIED.value

        expected_section_id = self.get_section_id(evidence_ref.section_title)
        if not expected_section_id or evidence_ref.section_id != expected_section_id:
            return EvidenceStatus.UNVERIFIED.value

        normalized_quote = self.normalize_quote(evidence_ref.quote)
        expected_quote_hash = hashlib.sha256(normalized_quote.encode("utf-8")).hexdigest()[:16]
        if evidence_ref.quote_hash != expected_quote_hash:
            return EvidenceStatus.UNVERIFIED.value

        found = self.verify_quote_location(evidence_ref.quote, evidence_ref.section_title)
        return EvidenceStatus.VERIFIED.value if found else EvidenceStatus.UNVERIFIED.value

    # ------------------------------------------------------------------
    # Hashing and ID generation
    # ------------------------------------------------------------------

    def _compute_source_hash(self) -> str:
        """Generate deterministic hash from canonical Paper content."""
        canonical = "\n".join(
            f"{s.title.strip()}:{self.normalize_quote(s.content)}" for s in self._paper.sections
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    def _build_section_ids(self) -> dict[str, str]:
        ids: dict[str, str] = {}
        for i, (section, alias) in enumerate(
            zip(self._paper.sections, self._section_aliases, strict=True)
        ):
            key = f"{i}:{section.title.strip()}:{self.normalize_quote(section.content)}"
            hash_digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
            ids[alias] = f"sec_{i:02d}_{hash_digest}"
        return ids

    def _build_section_aliases(self) -> list[str]:
        aliases: list[str] = []
        occurrences: dict[str, int] = {}
        used_aliases: set[str] = set()
        for section in self._paper.sections:
            normalized = section.title.casefold().strip()
            occurrences[normalized] = occurrences.get(normalized, 0) + 1
            occurrence = occurrences[normalized]
            alias = section.title if occurrence == 1 else f"{section.title} [{occurrence}]"
            suffix = occurrence
            while alias.casefold() in used_aliases:
                suffix += 1
                alias = f"{section.title} [{suffix}]"
            aliases.append(alias)
            used_aliases.add(alias.casefold())
        return aliases

    def _resolve_section(self, title: str) -> tuple[int, Section, str] | None:
        query = title.casefold().strip()
        if not query:
            return None

        for index, alias in enumerate(self._section_aliases):
            if query == alias.casefold():
                return index, self._paper.sections[index], alias
        for index, section in enumerate(self._paper.sections):
            if query == section.title.casefold().strip():
                return index, section, self._section_aliases[index]
        for index, (section, alias) in enumerate(
            zip(self._paper.sections, self._section_aliases, strict=True)
        ):
            if query in alias.casefold() or query in section.title.casefold():
                return index, section, alias
        return None

    def _find_section_raw(self, title: str) -> str:
        resolved = self._resolve_section(title)
        return resolved[1].content if resolved is not None else ""

    @staticmethod
    def _split_long_content(content: str, max_chars: int = 4000 * 4) -> list[str]:
        if len(content) <= max_chars:
            return [content]
        chunks: list[str] = []
        for i in range(0, len(content), max_chars):
            chunks.append(content[i : i + max_chars])
        return chunks

    @staticmethod
    def _extract_snippet(text: str, query: str, context: int = 200) -> str:
        idx = text.lower().find(query.lower())
        if idx < 0:
            return text[:context] + "..."
        start = max(0, idx - context // 2)
        end = min(len(text), idx + len(query) + context // 2)
        snippet = text[start:end]
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        return f"{prefix}{snippet}{suffix}"
