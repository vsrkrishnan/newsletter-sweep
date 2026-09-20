from datetime import datetime, timezone

from newsletter_sweep.config import Config, ProviderConfig, SourceConfig, TopicsConfig
from newsletter_sweep.sources import RawItem
from newsletter_sweep.taxonomy import UNCATEGORIZED, resolve_taxonomy, route_topic


def _config(tmp_path, mode, declared=None):
    return Config(
        knowledge_path=tmp_path / "knowledge",
        profile_path=tmp_path / "applies_to_me.md",
        state_path=tmp_path / "state.json",
        provider=ProviderConfig(),
        topics=TopicsConfig(mode=mode, declared=declared or []),
        sources=[SourceConfig(type="rss", options={})],
        sinks=[],
        relevance_themes=[],
    )


def test_declared_mode_uses_config_topics(tmp_path):
    config = _config(tmp_path, "declared", declared=["biotech", "policy"])
    result = resolve_taxonomy(config, items=[], router=None, interactive=False)
    assert result.topics == ["biotech", "policy"]
    assert result.proposed is False


def test_learned_mode_reads_existing_folders(tmp_path):
    config = _config(tmp_path, "learned")
    (config.knowledge_path / "football").mkdir(parents=True)
    (config.knowledge_path / "finance").mkdir(parents=True)
    (config.knowledge_path / UNCATEGORIZED).mkdir(parents=True)  # must be excluded

    result = resolve_taxonomy(config, items=[], router=None, interactive=False)
    assert result.topics == ["finance", "football"]
    assert result.proposed is False


def test_learned_mode_empty_and_no_items_defers(tmp_path):
    config = _config(tmp_path, "learned")
    result = resolve_taxonomy(config, items=[], router=None, interactive=False)
    assert result.topics == []
    assert result.proposed is False


class _FakeRouter:
    def synthesize(self, **kwargs):
        return "biotech\nclimate-policy\nspace-industry"


def test_learned_mode_proposes_from_first_batch_noninteractive(tmp_path):
    config = _config(tmp_path, "learned")
    items = [
        RawItem(source_name="s", title="CRISPR breakthrough", url="https://x", body="...",
                published=datetime.now(timezone.utc))
    ]
    result = resolve_taxonomy(config, items=items, router=_FakeRouter(), interactive=False)
    assert result.topics == ["biotech", "climate-policy", "space-industry"]
    assert result.proposed is True  # must be flagged for user review, never silently locked in
    assert (config.knowledge_path / "biotech").is_dir()
    assert (config.knowledge_path / UNCATEGORIZED).is_dir()


def test_route_topic_falls_back_to_uncategorized():
    assert route_topic("random-guess", ["real-topic"]) == UNCATEGORIZED
    assert route_topic("Real-Topic", ["real-topic"]) == "real-topic"
    assert route_topic("anything", []) == UNCATEGORIZED
