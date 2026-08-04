"""OpenAI-compatible provider response normalization tests."""

from __future__ import annotations

import sys
from types import ModuleType
from types import SimpleNamespace

import pytest

from repro_forge.providers.base import LLMRequest
from repro_forge.providers.base import LLMResponse
from repro_forge.providers.base import LLMToolCall
from repro_forge.providers.openai_provider import OpenAIProvider


class FakeCompletions:
    def __init__(self, response: object) -> None:
        self.response = response

    async def create(self, **kwargs: object) -> object:
        del kwargs
        return self.response


def _install_fake_openai(monkeypatch: pytest.MonkeyPatch, response: object) -> None:
    client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions(response)))
    module = ModuleType("openai")
    module.AsyncOpenAI = lambda **kwargs: client  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", module)


def test_llm_response_preserves_legacy_positional_raw_argument() -> None:
    raw_response = object()

    response = LLMResponse("content", "model", "stop", {}, raw_response)

    assert response.raw is raw_response
    assert response.tool_calls == []


def test_provider_uses_deepseek_environment_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str | None] = {}
    client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions(object())))
    module = ModuleType("openai")

    def fake_async_openai(**kwargs: str | None) -> object:
        captured.update(kwargs)
        return client

    module.AsyncOpenAI = fake_async_openai  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", module)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-env-key")
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)

    provider = OpenAIProvider()

    assert provider.model == "deepseek-chat"
    assert captured == {
        "api_key": "deepseek-env-key",
        "base_url": "https://api.deepseek.com",
    }


def test_provider_prefers_openai_environment_over_deepseek(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str | None] = {}
    client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions(object())))
    module = ModuleType("openai")

    def fake_async_openai(**kwargs: str | None) -> object:
        captured.update(kwargs)
        return client

    module.AsyncOpenAI = fake_async_openai  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", module)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-env-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openai.example/v1")
    monkeypatch.setenv("OPENAI_MODEL", "openai-env-model")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-env-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://deepseek.example/v1")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-env-model")

    provider = OpenAIProvider()

    assert provider.model == "openai-env-model"
    assert captured == {
        "api_key": "openai-env-key",
        "base_url": "https://openai.example/v1",
    }


def test_provider_explicit_arguments_override_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str | None] = {}
    client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions(object())))
    module = ModuleType("openai")

    def fake_async_openai(**kwargs: str | None) -> object:
        captured.update(kwargs)
        return client

    module.AsyncOpenAI = fake_async_openai  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", module)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-env-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openai.example/v1")
    monkeypatch.setenv("OPENAI_MODEL", "openai-env-model")

    provider = OpenAIProvider(
        api_key="explicit-key",
        base_url="http://localhost:11434/v1",
        model="explicit-model",
    )

    assert provider.model == "explicit-model"
    assert captured == {
        "api_key": "explicit-key",
        "base_url": "http://localhost:11434/v1",
    }


def test_provider_allows_keyless_explicit_compatible_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str | None] = {}
    client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions(object())))
    module = ModuleType("openai")

    def fake_async_openai(**kwargs: str | None) -> object:
        captured.update(kwargs)
        return client

    module.AsyncOpenAI = fake_async_openai  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", module)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    provider = OpenAIProvider(base_url="http://localhost:11434/v1", model="llama3")

    assert provider.model == "llama3"
    assert captured == {
        "api_key": "sk-placeholder",
        "base_url": "http://localhost:11434/v1",
    }


def test_provider_rejects_missing_credentials_for_default_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = ModuleType("openai")
    module.AsyncOpenAI = lambda **kwargs: object()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", module)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)

    with pytest.raises(ValueError, match="API key"):
        OpenAIProvider()


@pytest.mark.asyncio
async def test_generate_normalizes_native_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    native_call = SimpleNamespace(
        id="call_read_method",
        function=SimpleNamespace(
            name="read_section",
            arguments='{"section_title": "Method"}',
        ),
    )
    response = SimpleNamespace(
        model="gpt-test",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=None, tool_calls=[native_call]),
                finish_reason="tool_calls",
            )
        ],
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=4, total_tokens=16),
    )
    _install_fake_openai(monkeypatch, response)
    provider = OpenAIProvider(api_key="test-key", model="gpt-test")

    result = await provider.generate(LLMRequest(messages=[], model="gpt-test"))

    assert result.tool_calls == [
        LLMToolCall(
            call_id="call_read_method",
            name="read_section",
            arguments={"section_title": "Method"},
        )
    ]
    assert result.usage["total_tokens"] == 16


@pytest.mark.asyncio
async def test_generate_uses_empty_arguments_for_invalid_tool_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native_call = SimpleNamespace(
        id="call_invalid",
        function=SimpleNamespace(name="search_paper", arguments="not-json"),
    )
    response = SimpleNamespace(
        model="gpt-test",
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=None, tool_calls=[native_call]),
                finish_reason="tool_calls",
            )
        ],
        usage=None,
    )
    _install_fake_openai(monkeypatch, response)
    provider = OpenAIProvider(api_key="test-key", model="gpt-test")

    result = await provider.generate(LLMRequest(messages=[], model="gpt-test"))

    assert result.tool_calls[0].arguments == {}


@pytest.mark.asyncio
async def test_generate_stream_forwards_stop_sequences(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeStream:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    class CapturingCompletions:
        async def create(self, **kwargs: object) -> FakeStream:
            captured.update(kwargs)
            return FakeStream()

    client = SimpleNamespace(chat=SimpleNamespace(completions=CapturingCompletions()))
    module = ModuleType("openai")
    module.AsyncOpenAI = lambda **kwargs: client  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", module)
    provider = OpenAIProvider(api_key="test-key", model="gpt-test")
    request = LLMRequest(
        messages=[{"role": "user", "content": "test"}],
        model="gpt-test",
        stop_sequences=["STOP"],
    )

    chunks = [chunk async for chunk in provider.generate_stream(request)]

    assert chunks == []
    assert captured["stop"] == ["STOP"]
