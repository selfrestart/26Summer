"""arXiv identifier normalization tests."""

import pytest

from repro_forge.paper.parser.arxiv_api import ArxivClient


@pytest.mark.parametrize(
    ("raw_id", "expected"),
    [
        ("https://arxiv.org/pdf/1706.03762.pdf", "1706.03762"),
        ("https://arxiv.org/abs/1706.03762", "1706.03762"),
        ("arXiv:1706.03762v7", "1706.03762v7"),
    ],
)
def test_clean_id_normalizes_common_arxiv_references(raw_id: str, expected: str) -> None:
    assert ArxivClient._clean_id(raw_id) == expected
