"""Tests for PaperEvidenceView."""

import hashlib

from repro_forge.paper.extractor.evidence import PaperEvidenceView
from repro_forge.paper.extractor.schemas import EvidenceRef
from repro_forge.paper.schemas import Paper
from repro_forge.paper.schemas import Section
from repro_forge.paper.schemas import SectionType


def _make_paper() -> Paper:
    return Paper(
        metadata={"title": "Test", "arxiv_id": "1234.5678"},
        sections=[
            Section(
                title="Abstract",
                content="We propose a novel method using deep learning.",
                section_type=SectionType.ABSTRACT,
            ),
            Section(
                title="Method",
                content="Our approach uses multi-head attention with 8 heads and dimension 512. The optimizer is Adam with lr=1e-4.",
                section_type=SectionType.METHOD,
            ),
            Section(
                title="Experiments",
                content="We achieve 94.5% accuracy on ImageNet with batch size 256.",
                section_type=SectionType.EXPERIMENTS,
            ),
        ],
        total_pages=5,
    )


class TestPaperEvidenceView:
    def test_source_hash_is_deterministic(self) -> None:
        p1 = _make_paper()
        p2 = _make_paper()
        view1 = PaperEvidenceView(p1)
        view2 = PaperEvidenceView(p2)
        assert view1.source_hash == view2.source_hash

    def test_source_hash_changes_with_content(self) -> None:
        p1 = _make_paper()
        p2 = _make_paper()
        p2.sections[0].content = "Different content."
        view1 = PaperEvidenceView(p1)
        view2 = PaperEvidenceView(p2)
        assert view1.source_hash != view2.source_hash

    def test_section_ids_stable(self) -> None:
        p1 = _make_paper()
        p2 = _make_paper()
        view1 = PaperEvidenceView(p1)
        view2 = PaperEvidenceView(p2)
        assert view1.section_ids == view2.section_ids

    def test_read_section_found(self) -> None:
        view = PaperEvidenceView(_make_paper())
        content = view.read_section("Method")
        assert "multi-head attention" in content
        assert "Adam" in content

    def test_read_section_chunk_zero_is_bounded(self) -> None:
        paper = _make_paper()
        paper.sections[1].content = "alpha " * 20
        view = PaperEvidenceView(paper, chunk_size=4)

        first = view.read_section("Method", chunk_index=0)
        second = view.read_section("Method", chunk_index=1)

        assert first != paper.sections[1].content
        assert len(first) <= 16
        assert second

    def test_read_section_rejects_negative_chunk_index(self) -> None:
        view = PaperEvidenceView(_make_paper())
        assert "out of range" in view.read_section("Method", chunk_index=-1).lower()

    def test_read_section_not_found(self) -> None:
        view = PaperEvidenceView(_make_paper())
        content = view.read_section("Nonexistent")
        assert "not found" in content.lower()

    def test_search_finds_query(self) -> None:
        view = PaperEvidenceView(_make_paper())
        results = view.search("attention")
        assert len(results) > 0
        assert any("attention" in r["snippet"].lower() for r in results)

    def test_search_no_match(self) -> None:
        view = PaperEvidenceView(_make_paper())
        results = view.search("blockchain")
        assert results == []

    def test_list_sections(self) -> None:
        view = PaperEvidenceView(_make_paper())
        result = view.list_sections()
        assert "Abstract" in result
        assert "Method" in result
        assert "Experiments" in result

    def test_lookup_is_case_insensitive_and_consistent(self) -> None:
        view = PaperEvidenceView(_make_paper())
        assert view.get_section_id("method") == view.get_section_id("Method")
        assert view.get_section_id("meth") == view.get_section_id("Method")

    def test_duplicate_titles_receive_unique_aliases(self) -> None:
        paper = _make_paper()
        paper.sections.append(
            Section(
                title="Method",
                content="A second method section with a unique detail.",
                section_type=SectionType.METHOD,
            )
        )
        view = PaperEvidenceView(paper)

        assert "Method [2]" in view.section_titles()
        assert view.get_section_id("Method") != view.get_section_id("Method [2]")
        assert "unique detail" in view.read_section("Method [2]")
        result = view.search("unique detail")[0]
        assert result["section_title"] == "Method [2]"
        assert result["section_id"] == view.get_section_id("Method [2]")

    def test_section_aliases_do_not_collide_with_literal_bracket_titles(self) -> None:
        paper = Paper(
            sections=[
                Section(title="Method [2]", content="literal title"),
                Section(title="Method", content="first method"),
                Section(title="Method", content="second method"),
            ]
        )
        view = PaperEvidenceView(paper)

        assert len(view.section_titles()) == 3
        assert len(set(view.section_titles())) == 3
        assert len(view.section_ids) == 3

    def test_normalize_quote_removes_line_breaks(self) -> None:
        result = PaperEvidenceView.normalize_quote("multi-\nhead\n  attention")
        assert "\n" not in result
        assert "multi-head" in result

    def test_verify_quote_location_true(self) -> None:
        view = PaperEvidenceView(_make_paper())
        assert view.verify_quote_location("multi-head attention", "Method")

    def test_verify_quote_location_false(self) -> None:
        view = PaperEvidenceView(_make_paper())
        assert not view.verify_quote_location("this does not exist anywhere", "Method")

    def test_verify_evidence_requires_all_provenance_fields(self) -> None:
        view = PaperEvidenceView(_make_paper())
        quote = "multi-head attention"
        valid = EvidenceRef(
            evidence_id="ev_method",
            paper_id="1234.5678",
            source_hash=view.source_hash,
            section_id=view.get_section_id("Method"),
            section_title="Method",
            quote=quote,
            quote_hash=hashlib.sha256(
                PaperEvidenceView.normalize_quote(quote).encode("utf-8")
            ).hexdigest()[:16],
        )
        assert view.verify_evidence(valid) == "verified"

        for field, value in (
            ("paper_id", "wrong-paper"),
            ("section_id", "wrong-section"),
            ("source_hash", "wrong-source"),
            ("quote_hash", "wrong-quote"),
        ):
            invalid = valid.model_copy(update={field: value})
            assert view.verify_evidence(invalid) == "unverified"

    def test_verify_evidence_rejects_missing_provenance(self) -> None:
        view = PaperEvidenceView(_make_paper())
        ref = EvidenceRef(section_title="Method", quote="multi-head attention")
        assert view.verify_evidence(ref) == "unverified"

    def test_source_hash_covers_content_after_first_500_characters(self) -> None:
        p1 = _make_paper()
        p2 = _make_paper()
        suffix = "x" * 600
        p1.sections[1].content += suffix
        p2.sections[1].content += suffix[:-1] + "y"
        assert PaperEvidenceView(p1).source_hash != PaperEvidenceView(p2).source_hash
