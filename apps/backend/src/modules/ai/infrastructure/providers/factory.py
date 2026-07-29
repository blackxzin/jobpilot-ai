"""LLM Provider Factory — creates the right provider based on configuration."""
from __future__ import annotations

from modules.ai.domain.llm_provider import LLMProvider
from modules.ai.infrastructure.llm_providers.openai_provider import OpenAIProvider
from modules.ai.infrastructure.llm_providers.anthropic_provider import AnthropicProvider
from modules.ai.infrastructure.llm_providers.ollama_provider import OllamaProvider
from modules.ai.infrastructure.llm_providers.openrouter_provider import OpenRouterProvider
from modules.ai.infrastructure.llm_providers.gemini_provider import GeminiProvider
from modules.ai.infrastructure.llm_providers.nvidia_nim_provider import NvidiaNimProvider


class LLMProviderFactory:
    """Factory that creates LLM provider instances based on configuration.

    Usage:
        provider = LLMProviderFactory.create(config)
        result = await provider.generate("Hello")
    """

    _REGISTRY: dict[str, type[LLMProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
        "openrouter": OpenRouterProvider,
        "gemini": GeminiProvider,
        "nvidia_nim": NvidiaNimProvider,
    }

    @classmethod
    def register(cls, name: str, provider_class: type[LLMProvider]) -> None:
        """Register a custom provider at runtime."""
        cls._REGISTRY[name.lower()] = provider_class

    @classmethod
    def create(cls, provider_name: str, api_key: str = "", base_url: str = "", model: str = "") -> LLMProvider:
        """Create a provider instance from configuration.

        Args:
            provider_name: One of the registered provider names.
            api_key: API key for the provider (overrides env/default).
            base_url: Custom base URL (for self-hosted or NIM).
            model: Model identifier (e.g., "gpt-4o", "claude-sonnet-4").

        Returns:
            An LLMProvider instance.

        Raises:
            ValueError: If the provider name is unknown.
        """
        name = provider_name.lower()
        provider_cls = cls._REGISTRY.get(name)
        if provider_cls is None:
            raise ValueError(
                f"Unknown LLM provider: '{provider_name}'. "
                f"Available: {list(cls._REGISTRY.keys())}"
            )

        # Map constructor params based on provider type
        if name == "openai":
            return provider_cls(api_key=api_key or None, model=model or "gpt-4o", base_url=base_url or None)
        if name == "anthropic":
            return provider_cls(api_key=api_key or None, model=model or "claude-sonnet-4-20250514")
        if name == "ollama":
            return provider_cls(base_url=base_url or None, model=model or "llama3.1")
        if name == "openrouter":
            return provider_cls(api_key=api_key or None, model=model or "openai/gpt-4o")
        if name == "gemini":
            return provider_cls(api_key=api_key or None, model=model or "gemini-2.0-flash")
        if name == "nvidia_nim":
            return provider_cls(api_key=api_key or None, model=model or "nvidia/llama-3.3-70b-instruct", base_url=base_url or None)

        # Fallback (should never reach here)
        return provider_cls(api_key=api_key or None)

    @classmethod
    def list_providers(cls) -> list[str]:
        """Return all registered provider names."""
        return list(cls._REGISTRY.keys())