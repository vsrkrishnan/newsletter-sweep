from __future__ import annotations

import requests

from .base import Provider, ProviderError

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


class AnthropicProvider(Provider):
    def complete(
        self, *, model: str, system: str, prompt: str, max_tokens: int, json_mode: bool = False
    ) -> str:
        # json_mode is accepted for interface parity but not needed: the
        # Messages API has no response_format switch, and Claude reliably
        # honors the "respond with ONLY a JSON object" instruction in the
        # triage prompt, which the lenient parser then handles.
        if not self.api_key:
            raise ProviderError(
                "No Anthropic API key found. Paste it into the .env file next to "
                "config.yaml as ANTHROPIC_API_KEY=... (or export it in your shell). "
                "The variable name is set by provider.api_key_env in config.yaml."
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
