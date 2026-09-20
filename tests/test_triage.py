from datetime import datetime, timezone

from newsletter_sweep.config import Config, ProviderConfig, SourceConfig, TopicsConfig
from newsletter_sweep.sources import RawItem
from newsletter_sweep.state import State
from newsletter_sweep.taxonomy import TaxonomyResult
from newsletter_sweep.triage import triage_items


class _ScriptedRouter:
    """Returns queued responses in order — lets a test control exactly what
    the "LLM" says without any network call."""

    def __init__(self, triage_responses, synth_responses=None):
        self._triage = list(triage_responses)
        self._synth = list(synth_responses or [])

    def triage(self, **kwargs):
        return self._triage.pop(0)

    def synthesize(self, **kwargs):
        return self._synth.pop(0) if self._synth else "applies because X"


def _item(title="Title", url="https://x.com/1", body="body text"):
    return RawItem(source_name="Test Source", title=title, url=url,
                    published=datetime.now(timezone.utc), body=body)


def _config(tmp_path):
    return Config(
        knowledge_path=tmp_path / "knowledge", profile_path=tmp_path / "p.md",
        state_path=tmp_path / "s.json", provider=ProviderConfig(),
        topics=TopicsConfig(mode="declared", declared=["general"]),
        sources=[SourceConfig(type="rss", options={})], sinks=[],
        relevance_themes=["stuff I care about"],
    )


def test_relevant_item_is_kept_with_applies_to_me(tmp_path):
    router = _ScriptedRouter(
        triage_responses=['{"relevant": true, "reason": "on topic", "topic": "general"}'],
        synth_responses=["This directly changes how you'd approach X."],
    )
    state = State.load_or_init(tmp_path / "s.json")
    taxonomy = TaxonomyResult(topics=["general"], proposed=False)

    run = triage_items([_item()], _config(tmp_path), "my profile", state, router, taxonomy)

    assert len(run.kept) == 1
    assert run.kept[0].applies_to_me == "This directly changes how you'd approach X."
    assert run.kept[0].topic == "general"
    assert len(run.skipped) == 0


def test_irrelevant_item_is_skipped_and_no_synthesis_call_needed(tmp_path):
    router = _ScriptedRouter(
        triage_responses=['{"relevant": false, "reason": "off topic", "topic": ""}'],
    )
    state = State.load_or_init(tmp_path / "s.json")
    taxonomy = TaxonomyResult(topics=["general"], proposed=False)

    run = triage_items([_item()], _config(tmp_path), "my profile", state, router, taxonomy)

    assert len(run.kept) == 0
    assert run.skipped[0][1] == "off topic"


def test_already_seen_item_skips_llm_entirely(tmp_path):
    router = _ScriptedRouter(triage_responses=[])  # would raise IndexError if called
    state = State.load_or_init(tmp_path / "s.json")
    state.mark_seen("https://x.com/1", "Title body text"[:200])
    taxonomy = TaxonomyResult(topics=["general"], proposed=False)

    run = triage_items([_item()], _config(tmp_path), "my profile", state, router, taxonomy)

    assert len(run.kept) == 0
    assert "duplicate" in run.skipped[0][1]


def test_malformed_llm_response_is_skipped_not_fatal(tmp_path):
    router = _ScriptedRouter(triage_responses=["not json at all"])
    state = State.load_or_init(tmp_path / "s.json")
    taxonomy = TaxonomyResult(topics=["general"], proposed=False)

    run = triage_items([_item()], _config(tmp_path), "my profile", state, router, taxonomy)

    assert len(run.kept) == 0
    assert "malformed" in run.skipped[0][1]


def test_provider_error_is_fatal_not_skipped_per_item(tmp_path):
    """A broken provider (bad key, unreachable endpoint) fails identically
    on every item — it must abort the run, not silently skip 20 items in
    a row with duplicate warnings while burning API calls."""
    import pytest

    from newsletter_sweep.providers import ProviderError

    class _BrokenRouter:
        def triage(self, **kwargs):
            raise ProviderError("no API key")

    state = State.load_or_init(tmp_path / "s.json")
    taxonomy = TaxonomyResult(topics=["general"], proposed=False)
    items = [_item(url="https://x.com/1"), _item(url="https://x.com/2")]

    with pytest.raises(ProviderError):
        triage_items(items, _config(tmp_path), "my profile", state, _BrokenRouter(), taxonomy)


def test_kept_item_marks_state_seen(tmp_path):
    router = _ScriptedRouter(
        triage_responses=['{"relevant": true, "reason": "r", "topic": "general"}'],
    )
    state = State.load_or_init(tmp_path / "s.json")
    taxonomy = TaxonomyResult(topics=["general"], proposed=False)

    triage_items([_item()], _config(tmp_path), "my profile", state, router, taxonomy)

    assert "https://x.com/1" in state.seen_urls
