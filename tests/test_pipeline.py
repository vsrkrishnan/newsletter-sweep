"""End-to-end pipeline test with every network-touching piece faked out:
no real RSS fetch, no real LLM call. Verifies the whole run_sweep() wiring
actually connects — the individual pieces are covered in their own test
files.
"""
from datetime import datetime, timezone

from newsletter_sweep.config import Config, ProviderConfig, SourceConfig, SinkConfig, TopicsConfig
from newsletter_sweep.profile import write_profile
from newsletter_sweep.sources import RawItem
from newsletter_sweep.sources.base import Source


class _FakeSource(Source):
    def fetch_since(self, watermark):
        return [
            RawItem(source_name="Fake Feed", title="A relevant item",
                     url="https://x.com/1", published=datetime.now(timezone.utc),
                     body="content about the reader's stated interest"),
        ]


class _FakeRouter:
    def triage(self, **kwargs):
        return '{"relevant": true, "reason": "matches profile", "topic": "general"}'

    def synthesize(self, **kwargs):
        return "This applies to you because it matches your stated focus."


def test_full_dry_run_end_to_end(tmp_path, monkeypatch):
    from newsletter_sweep import pipeline as pipeline_mod

    write_profile(tmp_path / "applies_to_me.md",
                  "I'm testing this tool and want to see it work end to end.")

    config = Config(
        knowledge_path=tmp_path / "knowledge",
        profile_path=tmp_path / "applies_to_me.md",
        state_path=tmp_path / ".state" / "state.json",
        provider=ProviderConfig(),
        topics=TopicsConfig(mode="declared", declared=["general"]),
        sources=[SourceConfig(type="rss", options={})],
        sinks=[SinkConfig(type="markdown", options={})],
        relevance_themes=["anything relevant"],
        dry_run=True,
    )

    monkeypatch.setattr(pipeline_mod, "build_source", lambda t, o: _FakeSource(o))
    monkeypatch.setattr(pipeline_mod, "build_router", lambda cfg: _FakeRouter())

    result = pipeline_mod.run_sweep(config, interactive=False)

    assert result.dry_run is True
    assert result.kept == 1
    assert result.skipped == 0
    assert not config.knowledge_path.exists()  # dry-run touched nothing
    assert not config.state_path.exists()      # state not persisted on dry-run
    assert "A relevant item" in result.digest_markdown


def test_live_run_persists_state_and_writes_files(tmp_path, monkeypatch):
    from newsletter_sweep import pipeline as pipeline_mod

    write_profile(tmp_path / "applies_to_me.md",
                  "I'm testing this tool and want to see it work end to end.")

    config = Config(
        knowledge_path=tmp_path / "knowledge",
        profile_path=tmp_path / "applies_to_me.md",
        state_path=tmp_path / ".state" / "state.json",
        provider=ProviderConfig(),
        topics=TopicsConfig(mode="declared", declared=["general"]),
        sources=[SourceConfig(type="rss", options={})],
        sinks=[SinkConfig(type="markdown", options={})],
        relevance_themes=["anything relevant"],
        dry_run=False,
    )

    monkeypatch.setattr(pipeline_mod, "build_source", lambda t, o: _FakeSource(o))
    monkeypatch.setattr(pipeline_mod, "build_router", lambda cfg: _FakeRouter())

    result = pipeline_mod.run_sweep(config, interactive=False)

    assert result.kept == 1
    written = [p for p in (config.knowledge_path / "general").glob("*.md") if p.name != "index.md"]
    assert len(written) == 1
    assert config.state_path.exists()
