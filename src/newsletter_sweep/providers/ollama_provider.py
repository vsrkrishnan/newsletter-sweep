"""Local-model provider — no API key, runs entirely on the user's machine
(assuming an Ollama daemon is running). This is what makes the tool usable
with zero cloud dependency and zero cost per run, at the price of triage
quality — documented plainly rather than left implicit.

STATUS: implemented but not yet verified end to end. The main thing to
watch is that smaller local models often ignore "respond with ONLY JSON"
and wrap or prose-pad their output; triage.py tolerates a code-fence
wrapper but not arbitrary preamble, so a very small model may need a
sturdier prompt or a larger model to route reliably.
"""
from __future__ import annotations

import requests

from .base import Provider, ProviderError

DEFAULT_BASE_URL = "http://localhost:11434/api/chat"


class OllamaProvider(Provider):
    def complete(self, *, model: str, system: str, prompt: str, max_tokens: int) -> str:
        resp = requests.post(
            self.base_url or DEFAULT_BASE_URL,
            json={
                "model": model,
                "stream": False,
                "options": {"num_predict": max_tokens},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=120,
        )
        if resp.status_code != 200:
            raise ProviderError(
                f"Ollama error {resp.status_code}: {resp.text[:500]} "
                "(is `ollama serve` running, and is the model pulled?)"
            )
        data = resp.json()
        try:
            return data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise ProviderError(f"Unexpected Ollama response shape: {data}") from exc
