"""Provider interfaces and optional provider implementations."""

from typing import TYPE_CHECKING

from repro_forge.providers.base import BaseProvider
from repro_forge.providers.base import LLMRequest
from repro_forge.providers.base import LLMResponse
from repro_forge.providers.base import LLMToolCall

if TYPE_CHECKING:
    from repro_forge.providers.openai_provider import OpenAIProvider

__all__ = ["BaseProvider", "LLMRequest", "LLMResponse", "LLMToolCall", "OpenAIProvider"]


def __getattr__(name: str) -> object:
    if name == "OpenAIProvider":
        from repro_forge.providers.openai_provider import OpenAIProvider

        return OpenAIProvider
    raise AttributeError(name)
