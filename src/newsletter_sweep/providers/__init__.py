from ..config import ProviderConfig
from .anthropic_provider import AnthropicProvider
from .base import ModelRouter, Provider, ProviderError
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider

PROVIDER_REGISTRY: dict[str, type[Provider]] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
}


def build_router(config: ProviderConfig) -> ModelRouter:
    try:
        cls = PROVIDER_REGISTRY[config.name]
    except KeyError:
        raise ValueError(
            f"Unknown provider '{config.name}'. Available: {', '.join(PROVIDER_REGISTRY)}."
        )
    provider = cls(api_key=config.api_key(), base_url=config.base_url)
    return ModelRouter(
        provider=provider, triage_model=config.triage_model, synthesis_model=config.synthesis_model
    )


__all__ = ["Provider", "ProviderError", "ModelRouter", "PROVIDER_REGISTRY", "build_router"]
