from __future__ import annotations

from typing import Any

from packages.domain.config import get_settings

from .mock_provider import MockProvider
from .providers import ModelProvider


def get_provider(provider_name: str | None = None, **kwargs: Any) -> ModelProvider:
    return create_provider(provider_name, **kwargs)


def create_provider(
    provider_name: str | None = None,
    model_profile: str | None = None,
    **kwargs: Any,
) -> ModelProvider:
    settings = get_settings()

    provider = provider_name or settings.default_model_provider
    _ = model_profile or settings.model_profile  # Used by providers internally

    if provider == "mock":
        return MockProvider()

    if provider == "openrouter":
        from .openrouter_provider import OpenRouterProvider

        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY not configured")
        return OpenRouterProvider(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            model=settings.openrouter_model,
        )

    if provider == "ollama":
        from .ollama_provider import OllamaProvider

        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )

    raise ValueError(f"Unknown provider: {provider}")


class ProviderRegistry:
    _instances: dict[str, ModelProvider] = {}

    @classmethod
    def get(cls, provider_name: str | None = None, **kwargs: Any) -> ModelProvider:
        key = provider_name or "default"
        if key not in cls._instances:
            cls._instances[key] = create_provider(provider_name, **kwargs)
        return cls._instances[key]

    @classmethod
    async def close_all(cls) -> None:
        for provider in cls._instances.values():
            if hasattr(provider, "close"):
                await provider.close()
        cls._instances.clear()
