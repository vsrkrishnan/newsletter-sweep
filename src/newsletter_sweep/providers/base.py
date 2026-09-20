"""Provider interface — one call shape, three backends.

Implemented over each provider's plain HTTP API (via `requests`) rather than
the vendor SDKs, so switching providers never means installing a new
dependency — the whole point of "any LLM provider."
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderError(Exception):
    """Raised uniformly regardless of backend, so callers don't need to
    know which SDK/HTTP client is underneath."""


class Provider(ABC):
    def __init__(self, api_key: str | None, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    def complete(
        self, *, model: str, system: str, prompt: str, max_tokens: int, json_mode: bool = False
    ) -> str:
        """A single synchronous text completion. When `json_mode` is True the
        caller wants a JSON object back and the provider should use its native
        structured-output mode if it has one (OpenAI response_format, Ollama
        format:json) rather than relying on the prompt alone — this is what
        makes smaller/open models route reliably instead of dropping items
        whenever they pad their reply with prose. Providers without such a
        mode (Anthropic) can ignore the flag; the prompt already asks for JSON.
        """
        raise NotImplementedError


@dataclass
class ModelRouter:
    """Binds a Provider to the two model slots. This is what the rest of
    the codebase calls — never Provider.complete() directly — so the
    triage/synthesis cost split (see module docstring in providers/base.py
    at the top of this file) is enforced in one place.

    The JSON/prose split is fixed here too: triage() always wants a JSON
    object, synthesize() always wants prose. That's why json_mode can be
    hard-wired per method instead of pushed onto every call site.
    """
    provider: Provider
    triage_model: str
    synthesis_model: str

    def triage(self, *, system: str, prompt: str, max_tokens: int = 512) -> str:
        return self.provider.complete(
            model=self.triage_model, system=system, prompt=prompt,
            max_tokens=max_tokens, json_mode=True,
        )

    def synthesize(self, *, system: str, prompt: str, max_tokens: int = 1024) -> str:
        return self.provider.complete(
            model=self.synthesis_model, system=system, prompt=prompt,
            max_tokens=max_tokens, json_mode=False,
        )
