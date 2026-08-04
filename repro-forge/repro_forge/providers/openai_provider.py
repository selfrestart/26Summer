"""OpenAI-compatible LLM provider.

Supports OpenAI, DeepSeek, Qwen, vLLM, Ollama, and any service that
exposes an OpenAI-compatible chat completion API.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from typing import Any

from repro_forge.providers.base import BaseProvider
from repro_forge.providers.base import LLMRequest
from repro_forge.providers.base import LLMResponse
from repro_forge.providers.base import LLMToolCall


class OpenAIProvider(BaseProvider):
    """Provider for OpenAI and OpenAI-compatible APIs.

    Works with any service that implements the ``/v1/chat/completions``
    endpoint, including DeepSeek, Qwen, vLLM, and Ollama.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError(
                "OpenAIProvider requires the optional 'openai' extra; "
                "install with `uv sync --extra openai`"
            ) from exc

        openai_api_key = os.getenv("OPENAI_API_KEY")
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        resolved_api_key = api_key or openai_api_key or deepseek_api_key

        resolved_base_url: str | None
        if base_url is not None:
            resolved_base_url = base_url
        elif api_key is not None:
            resolved_base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL")
        elif openai_api_key:
            resolved_base_url = os.getenv("OPENAI_BASE_URL")
        elif deepseek_api_key:
            resolved_base_url = os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
        else:
            resolved_base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL")

        if model is not None:
            resolved_model = model
        elif api_key is not None:
            resolved_model = os.getenv("OPENAI_MODEL") or os.getenv("DEEPSEEK_MODEL") or "gpt-4o"
        elif openai_api_key:
            resolved_model = os.getenv("OPENAI_MODEL") or "gpt-4o"
        elif deepseek_api_key:
            resolved_model = os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"
        else:
            resolved_model = os.getenv("OPENAI_MODEL") or os.getenv("DEEPSEEK_MODEL") or "gpt-4o"

        if resolved_api_key is None:
            if resolved_base_url is None:
                raise ValueError(
                    "An API key is required unless a keyless OpenAI-compatible "
                    "base_url is configured"
                )
            resolved_api_key = "sk-placeholder"

        super().__init__(model=resolved_model, **kwargs)
        # The SDK has provider-specific TypedDict unions; the project keeps a
        # deliberately smaller OpenAI-compatible wire model at this boundary.
        self._client: Any = AsyncOpenAI(
            api_key=resolved_api_key,
            base_url=resolved_base_url,
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        response = await self._client.chat.completions.create(
            model=request.model or self.model,
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            tools=request.tools,
            tool_choice=request.tool_choice,
            stop=request.stop_sequences,
        )
        choice = response.choices[0]
        tool_calls: list[LLMToolCall] = []
        for native_call in getattr(choice.message, "tool_calls", None) or []:
            raw_arguments = native_call.function.arguments or "{}"
            try:
                parsed_arguments: Any = json.loads(raw_arguments)
            except (json.JSONDecodeError, TypeError):
                parsed_arguments = {}
            arguments: dict[str, Any] = (
                parsed_arguments if isinstance(parsed_arguments, dict) else {}
            )
            tool_calls.append(
                LLMToolCall(
                    call_id=native_call.id,
                    name=native_call.function.name,
                    arguments=arguments,
                )
            )
        return LLMResponse(
            content=choice.message.content or "",
            model=response.model,
            finish_reason=choice.finish_reason or "stop",
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            tool_calls=tool_calls,
            raw=response,
        )

    async def generate_stream(self, request: LLMRequest) -> AsyncIterator[str]:  # type: ignore[override]
        stream = await self._client.chat.completions.create(
            model=request.model or self.model,
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            tools=request.tools,
            tool_choice=request.tool_choice,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    @property
    def provider_name(self) -> str:
        return "openai"
