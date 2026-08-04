"""Multi-provider LLM abstraction layer.

Supports OpenAI, Anthropic, and OpenAI-compatible providers (DeepSeek,
Qwen, vLLM, Ollama, etc.) through a unified async interface.
"""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Literal


@dataclass
class LLMToolCall:
    """Provider-neutral representation of a native LLM tool call."""

    call_id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Unified response from any LLM provider."""

    content: str
    model: str
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    raw: Any = None
    tool_calls: list[LLMToolCall] = field(default_factory=list)


@dataclass
class LLMRequest:
    """Unified request to any LLM provider."""

    messages: list[dict[str, Any]]
    model: str = "gpt-4o"
    temperature: float = 0.0
    max_tokens: int = 4096
    tools: list[dict[str, Any]] | None = None
    tool_choice: Literal["auto", "none"] | None = None
    stop_sequences: list[str] | None = None


class BaseProvider(ABC):
    """Abstract base for LLM providers.

    Each provider implementation adapts its native API to this
    interface, enabling hot-swappable model backends.
    """

    def __init__(self, model: str = "gpt-4o", **kwargs: Any) -> None:
        self.model = model
        self.kwargs = kwargs

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Send a chat completion request.

        Args:
            request: The unified request object.

        Returns:
            A unified response containing the generated text.
        """

    @abstractmethod
    async def generate_stream(self, request: LLMRequest) -> Any:  # AsyncIterator[str]
        """Send a streaming chat completion request.

        Args:
            request: The unified request object.

        Yields:
            Text chunks as they arrive from the provider.
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""

    async def count_tokens(self, text: str) -> int:
        """Estimate token count for the given text.

        Default implementation provides a rough estimate. Override for
        provider-specific tokenizers.

        Args:
            text: Input text to count tokens for.

        Returns:
            Approximate token count.
        """
        return len(text) // 4  # rough estimate
