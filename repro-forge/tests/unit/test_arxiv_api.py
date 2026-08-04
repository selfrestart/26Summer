"""arXiv identifier normalization tests."""

from types import SimpleNamespace

import pytest

from repro_forge.paper.parser.arxiv_api import ArxivClient


@pytest.mark.parametrize(
    ("raw_id", "expected"),
    [
        ("https://arxiv.org/pdf/1706.03762.pdf", "1706.03762"),
        ("https://arxiv.org/abs/1706.03762", "1706.03762"),
        ("https://arxiv.org/abs/hep-th/9901001v3", "hep-th/9901001v3"),
        ("arXiv:1706.03762v7", "1706.03762v7"),
    ],
)
def test_clean_id_normalizes_common_arxiv_references(raw_id: str, expected: str) -> None:
    assert ArxivClient._clean_id(raw_id) == expected


def test_download_pdf_uses_a_safe_filename_for_legacy_ids(tmp_path) -> None:
    captured: dict[str, str] = {}

    class Result:
        def download_pdf(self, *, dirpath: str, filename: str) -> None:
            captured.update(dirpath=dirpath, filename=filename)

    client = ArxivClient.__new__(ArxivClient)
    client._arxiv = SimpleNamespace(Search=lambda **kwargs: kwargs)
    client._client = SimpleNamespace(results=lambda search: iter([Result()]))

    path = client.download_pdf("hep-th/9901001", tmp_path)

    assert path == tmp_path / "hep-th_9901001.pdf"
    assert captured["filename"] == "hep-th_9901001.pdf"
