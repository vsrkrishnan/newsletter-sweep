from __future__ import annotations

import requests

from .base import Provider, ProviderError

API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(Provider):
    def complete(self, *, model: str, system: str, prompt: str, max_tokens: int) -> str:
        if not self.api_key:
            raise ProviderError(
                "No OpenAI API key. Set the env var named by provider.api_key_env "
                "in config.yaml (default: OPENAI_API_KEY)."
            )
        resp = requests.post(
            self.base_url or API_URL,
            headers={"Authorization": f"Bearer {self.api_key}", "content-type": "application/json"},
            json={
                "model": model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        if resp.status_code != 200:
            raise ProviderError(f"OpenAI API error {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"Unexpected OpenAI response shape: {data}") from exc
