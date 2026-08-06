"""Tests for the repro-forge CLI (P2 analyze commands)."""

import json

import pytest

from repro_forge.cli import _is_local_endpoint
from repro_forge.cli import main
from tests.conftest import FakeLLMProvider

FAKE_ANALYSIS = json.dumps(
    {
        "problem_statement": "Image classification.",
        "algorithms": [
            {
                "name": "TestModel",
                "purpose": "Classification",
                "steps": [],
                "assumptions": [],
                "evidence": {"section_title": "Method", "quote": "Our model"},
            },
        ],
        "architecture": [],
        "training_recipe": {},
        "evaluation_protocol": {},
        "equations": [],
        "reproducibility_gaps": [],
        "assumptions": [],
    }
)


@pytest.fixture
def fake_cli_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeLLMProvider(responses=[f"DONE\n{FAKE_ANALYSIS}"])
    monkeypatch.setattr("repro_forge.cli._provider", lambda: provider)


class TestCLI:
    def test_keyless_endpoint_only_allows_explicit_local_addresses(self) -> None:
        assert _is_local_endpoint("http://localhost:11434/v1")
        assert _is_local_endpoint("http://127.0.0.1:8000/v1")
        assert _is_local_endpoint("http://192.168.1.10:8000/v1")
        assert not _is_local_endpoint("http://evil:8000/v1")
        assert not _is_local_endpoint("https://api.example.com/v1")

    def test_help_shows_p2_commands(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit):
            main(["--help"])
        output = capsys.readouterr().out
        assert "analyze-pdf" in output
        assert "analyze-json" in output
        assert "read-pdf" in output

    def test_capabilities(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = main(["capabilities"])
        output = capsys.readouterr().out
        assert rc == 0
        assert "P1 capabilities" in output
        assert "P2 capabilities" in output
        assert "methodology" in output

    def test_unknown_command_exits_nonzero(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["not-a-command"])
        assert exc_info.value.code != 0

    def test_analyze_json_produces_analysis(
        self,
        tmp_path,
        capsys: pytest.CaptureFixture[str],
        fake_cli_provider: None,
    ) -> None:
        paper_file = tmp_path / "paper.json"
        paper_file.write_text(
            json.dumps(
                {
                    "metadata": {"title": "Test", "arxiv_id": "1234.5678"},
                    "sections": [
                        {
                            "title": "Method",
                            "content": "Our model uses Adam.",
                            "section_type": "method",
                        },
                    ],
                    "total_pages": 1,
                }
            ),
            encoding="utf-8",
        )

        rc = main(["analyze-json", str(paper_file)])
        assert rc == 0
        output = capsys.readouterr().out
        assert "problem_statement" in output
        assert "TestModel" in output

    def test_analyze_json_with_output_file(
        self,
        tmp_path,
        fake_cli_provider: None,
    ) -> None:
        paper_file = tmp_path / "paper.json"
        paper_file.write_text(
            json.dumps(
                {
                    "metadata": {"title": "Test", "arxiv_id": "1234.5678"},
                    "sections": [],
                    "total_pages": 0,
                }
            ),
            encoding="utf-8",
        )
        out_file = tmp_path / "analysis.json"

        rc = main(["analyze-json", str(paper_file), "--output", str(out_file)])
        assert rc == 0
        assert out_file.exists()
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert data["algorithms"][0]["name"] == "TestModel"
