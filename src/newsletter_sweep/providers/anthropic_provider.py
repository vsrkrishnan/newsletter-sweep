from __future__ import annotations

import requests

from .base import Provider, ProviderError

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


class AnthropicProvider(Provider):
    def complete(self, *, model: str, system: str, prompt: str, max_tokens: int) -> str:
        if not self.api_key:
            raise ProviderError(
                "No Anthropic API key. Set the env var named by provider.api_key_env "
                "in config.yaml (default: ANTHROPIC_API_KEY)."
            )
        resp = requests.post(
            self.base_url or API_URL,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": API_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": model,
                "system": system,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        if resp.status_code != 200:
            raise ProviderError(f"Anthropic API error {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        try:
            return "".join(block["text"] for block in data["content"] if block["type"] == "text")
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"Unexpected Anthropic response shape: {data}") from exc
