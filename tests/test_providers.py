"""Provider request-shaping tests. These fake the HTTP layer (no network)
and assert the request body each provider builds — enough to lock in the
portability fixes (JSON mode, OpenAI's token-param fallback) without a live
API key."""
from __future__ import annotations

import json

import pytest

from newsletter_sweep.providers.anthropic_provider import AnthropicProvider
from newsletter_sweep.providers.base import ModelRouter
from newsletter_sweep.providers.ollama_provider import OllamaProvider
from newsletter_sweep.providers.openai_provider import OpenAIProvider


class _Resp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def test_router_requests_json_for_triage_prose_for_synthesis(monkeypatch):
    """The JSON/prose split must be driven by which router method is called,
    not hardcoded in the provider (synthesis returns prose and must NOT ask
    for json_object)."""
    seen = []

    class _Spy(OpenAIProvider):
        pass

    def fake_post(url, headers=None, json=None, timeout=None):
        seen.append(json)
        return _Resp(200, {"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr("newsletter_sweep.providers.openai_provider.requests.post", fake_post)
    router = ModelRouter(_Spy(api_key="k"), triage_model="m1", synthesis_model="m2")

    router.triage(system="s", prompt="give me json")
    router.synthesize(system="s", prompt="write prose")

    assert seen[0].get("response_format") == {"type": "json_object"}  # triage
    assert "response_format" not in seen[1]                            # synthesis


def test_openai_falls_back_from_max_completion_tokens_to_max_tokens(monkeypatch):
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        if "max_completion_tokens" in json:
            return _Resp(400, {"error": {"message": "Unsupported parameter: 'max_completion_tokens'. Use 'max_tokens'."}})
        return _Resp(200, {"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr("newsletter_sweep.providers.openai_provider.requests.post", fake_post)
    out = OpenAIProvider(api_key="k").complete(
        model="gpt-4o-mini", system="s", prompt="p", max_tokens=100
    )
    assert out == "ok"
    assert "max_completion_tokens" in calls[0]  # tried modern first
    assert "max_tokens" in calls[1]             # fell back to legacy


def test_openai_non_token_400_is_not_retried(monkeypatch):
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        return _Resp(400, {"error": {"message": "invalid model"}})

    monkeypatch.setattr("newsletter_sweep.providers.openai_provider.requests.post", fake_post)
    with pytest.raises(Exception, match="OpenAI API error 400"):
        OpenAIProvider(api_key="k").complete(model="bad", system="s", prompt="p", max_tokens=100)
    assert len(calls) == 1  # a non-token error must not trigger the fallback loop


def test_ollama_sets_format_json_only_in_json_mode(monkeypatch):
    seen = []

    def fake_post(url, json=None, timeout=None):
        seen.append(json)
        return _Resp(200, {"message": {"content": "ok"}})

    monkeypatch.setattr("newsletter_sweep.providers.ollama_provider.requests.post", fake_post)
    prov = OllamaProvider(api_key=None)
    prov.complete(model="llama3.2", system="s", prompt="p", max_tokens=100, json_mode=True)
    prov.complete(model="llama3.2", system="s", prompt="p", max_tokens=100, json_mode=False)

    assert seen[0].get("format") == "json"
    assert "format" not in seen[1]


def test_anthropic_accepts_json_mode_without_changing_body(monkeypatch):
    seen = []

    def fake_post(url, headers=None, json=None, timeout=None):
        seen.append(json)
        return _Resp(200, {"content": [{"type": "text", "text": "ok"}]})

    monkeypatch.setattr("newsletter_sweep.providers.anthropic_provider.requests.post", fake_post)
    out = AnthropicProvider(api_key="k").complete(
        model="claude", system="s", prompt="p", max_tokens=100, json_mode=True
    )
    assert out == "ok"
    assert "response_format" not in seen[0]  # Anthropic ignores json_mode
