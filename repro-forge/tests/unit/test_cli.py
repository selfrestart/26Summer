"""CLI smoke tests that do not require optional integrations or API keys."""

import pytest

import repro_forge.cli as cli
import repro_forge.providers as providers
from repro_forge.cli import main


def test_version_command(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    assert "repro-forge 0.1.0" in capsys.readouterr().out


def test_capabilities_command(capsys) -> None:
    assert main(["capabilities"]) == 0
    output = capsys.readouterr().out
    assert "paper-reading" in output
    assert "pdf" in output
    assert "arxiv" in output


def test_help_command(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    assert "read-pdf" in capsys.readouterr().out


def test_provider_uses_deepseek_defaults_when_openai_key_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str | None] = {}
    sentinel = object()

    def fake_provider(**kwargs: str | None) -> object:
        captured.update(kwargs)
        return sentinel

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-test-key")
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    monkeypatch.setattr(providers, "OpenAIProvider", fake_provider)

    provider = cli._provider()

    assert provider is sentinel
    assert captured == {
        "api_key": "deepseek-test-key",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    }


def test_provider_loads_deepseek_credentials_from_dotenv(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str | None] = {}

    def fake_provider(**kwargs: str | None) -> object:
        captured.update(kwargs)
        return object()

    (tmp_path / ".env").write_text(
        "DEEPSEEK_API_KEY=dotenv-key\nDEEPSEEK_MODEL=deepseek-chat\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    monkeypatch.setattr(providers, "OpenAIProvider", fake_provider)

    cli._provider()

    assert captured["api_key"] == "dotenv-key"
    assert captured["model"] == "deepseek-chat"


def test_provider_allows_a_keyless_openai_compatible_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str | None] = {}

    def fake_provider(**kwargs: str | None) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("OPENAI_MODEL", "llama3")
    monkeypatch.setattr(providers, "OpenAIProvider", fake_provider)

    cli._provider()

    assert captured == {
        "api_key": None,
        "base_url": "http://localhost:11434/v1",
        "model": "llama3",
    }
