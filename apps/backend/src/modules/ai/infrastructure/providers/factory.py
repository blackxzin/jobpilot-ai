"""LLM Provider Factory — creates the right provider based on configuration."""
from __future__ import annotations

from importlib import import_module

from modules.ai.domain.llm_provider import LLMProvider

# provider name -> (module path, class name, default model).
# Modules are imported lazily: importing every SDK up front costs startup time
# and emits third-party deprecation warnings for providers nobody is using.
_REGISTRY: dict[str, tuple[str, str, str]] = {
    "openai": ("openai_provider", "OpenAIProvider", "gpt-4o"),
    "anthropic": ("anthropic_provider", "AnthropicProvider", "claude-sonnet-4-20250514"),
    "gemini": ("gemini_provider", "GeminiProvider", "gemini-2.0-flash"),
    "ollama": ("ollama_provider", "OllamaProvider", "llama3.1"),
    "nvidia_nim": ("nvidia_nim_provider", "NvidiaNimProvider", "meta/llama-3.2-3b-instruct"),
    "openrouter": ("openrouter_provider", "OpenRouterProvider", "openai/gpt-4o"),
    "offline": ("offline_provider", "OfflineProvider", "offline-analyzer"),
}

_PACKAGE = "modules.ai.infrastructure.llm_providers"

# Providers that talk to a hosted API and are useless without credentials.
# Used to decide when to fall back to the offline analyzer.
KEY_REQUIRED_PROVIDERS = frozenset({"openai", "anthropic", "gemini", "nvidia_nim", "openrouter"})

# Providers whose constructor accepts a base_url override.
_ACCEPTS_BASE_URL = frozenset({"openai", "ollama", "nvidia_nim", "offline"})

_CUSTOM: dict[str, type[LLMProvider]] = {}


class LLMProviderFactory:
    """Factory that creates LLM provider instances based on configuration."""

    @classmethod
    def register(cls, name: str, provider_class: type[LLMProvider]) -> None:
        """Register a custom provider at runtime."""
        _CUSTOM[name.lower()] = provider_class

    @classmethod
    def create(
        cls, provider_name: str, api_key: str = "", base_url: str = "", model: str = ""
    ) -> LLMProvider:
        """Create a provider instance from configuration.

        Raises:
            ValueError: If the provider name is unknown.
        """
        name = (provider_name or "").lower()

        if name in _CUSTOM:
            return _CUSTOM[name](api_key=api_key or None, model=model or "", base_url=base_url or None)

        entry = _REGISTRY.get(name)
        if entry is None:
            raise ValueError(
                f"Unknown LLM provider: '{provider_name}'. Available: {sorted(_REGISTRY)}"
            )

        module_name, class_name, default_model = entry
        provider_cls = getattr(import_module(f"{_PACKAGE}.{module_name}"), class_name)

        kwargs: dict = {"model": model or default_model}
        # Ollama is self-hosted and takes no key; passing one would be ignored
        # at best and rejected at worst.
        if name != "ollama":
            kwargs["api_key"] = api_key or None
        if name in _ACCEPTS_BASE_URL:
            kwargs["base_url"] = base_url or None

        return provider_cls(**kwargs)

    @classmethod
    def create_with_fallback(
        cls, provider_name: str, api_key: str = "", base_url: str = "", model: str = ""
    ) -> LLMProvider:
        """Create a provider, falling back to the offline analyzer without a key.

        A hosted provider with no credentials fails on every call with a 502.
        Degrading to the local analyzer keeps matching, ATS scoring, cover
        letters and tailored resumes working on a fresh install.
        """
        name = (provider_name or "").lower()
        if name in KEY_REQUIRED_PROVIDERS and not api_key:
            return cls.create("offline")
        try:
            return cls.create(name, api_key=api_key, base_url=base_url, model=model)
        except ValueError:
            return cls.create("offline")

    @classmethod
    def list_providers(cls) -> list[str]:
        """Return all registered provider names."""
        return sorted({*_REGISTRY, *_CUSTOM})
