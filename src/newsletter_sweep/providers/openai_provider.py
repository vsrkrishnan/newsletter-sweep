"""OpenAI provider (also works for any OpenAI-compatible endpoint via
provider.base_url — e.g. Together, Groq, a local vLLM server).

STATUS: not yet verified against the live API, but the two known
portability hazards are handled: (1) the token-limit parameter changed
across model generations — older models take `max_tokens`, newer ones
require `max_completion_tokens` and reject `max_tokens` with a 400 — so
this tries the modern one first and falls back only on that specific
error; (2) JSON output uses the native response_format mode when the
caller asks for JSON, rather than trusting the prompt alone.
"""
from __future__ import annotations

import requests

from .base import Provider, ProviderError

API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(Provider):
    def complete(
        self, *, model: str, system: str, prompt: str, max_tokens: int, json_mode: bool = False
    ) -> str:
        if not self.api_key:
            raise ProviderError(
                "No OpenAI API key found. Paste it into the .env file next to "
                "config.yaml as OPENAI_API_KEY=... (or export it in your shell). "
                "The variable name is set by provider.api_key_env in config.yaml."
            )

        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        if json_mode:
            # Requires the word "json" to appear in the messages, which the
            # triage prompt already satisfies. Makes valid JSON the API's job.
            body["response_format"] = {"type": "json_object"}

        # Try the modern token parameter first; fall back only on the specific
        # 400 that means this model wanted the other one.
        for token_param in ("max_completion_tokens", "max_tokens"):
            attempt = dict(body, **{token_param: max_tokens})
            resp = requests.post(
                self.base_url or API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "content-type": "application/json",
                },
                json=attempt,
                timeout=60,
            )
            if resp.status_code == 200:
                return self._extract(resp.json())
            if resp.status_code == 400 and _is_token_param_error(resp.text, token_param):
                continue  # wrong token param for this model — try the other
            raise ProviderError(f"OpenAI API error {resp.status_code}: {resp.text[:500]}")

        raise ProviderError(
            "OpenAI API rejected both max_completion_tokens and max_tokens for "
            f"model {model!r}. Check the model name in config.yaml."
        )

    @staticmethod
    def _extract(data: dict) -> str:
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"Unexpected OpenAI response shape: {data}") from exc


def _is_token_param_error(body_text: str, token_param: str) -> bool:
    lowered = body_text.lower()
    return "max_tokens" in lowered or "max_completion_tokens" in lowered
