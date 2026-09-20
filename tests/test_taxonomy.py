from datetime import datetime, timezone

from newsletter_sweep.config import Config, ProviderConfig, SourceConfig, TopicsConfig
from newsletter_sweep.sources import RawItem
from newsletter_sweep.taxonomy import UNCATEGORIZED, resolve_taxonomy, route_topic, sanitize_topic


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


def test_sanitize_topic_blocks_path_traversal():
    """A topic becomes a directory name (knowledge_path/<topic>/), so a
    raw ../ must never survive — whether it came from a user's own
    config.yaml or a model's learned-mode proposal (which is built from
    untrusted newsletter content and could be prompt-injected)."""
    assert sanitize_topic("../../etc") == "etc"
    assert sanitize_topic("../../../tmp/evil") == "tmp-evil"
    assert sanitize_topic("/etc/passwd") == "etc-passwd"
    assert sanitize_topic("....") is None
    assert sanitize_topic("") is None


def test_declared_topics_are_sanitized_before_becoming_dirs(tmp_path):
    config = _config(tmp_path, "declared", declared=["../../etc", "normal-topic"])
    result = resolve_taxonomy(config, items=[], router=None, interactive=False)
    assert result.topics == ["etc", "normal-topic"]
    assert ".." not in "".join(result.topics)


def test_proposed_topics_are_sanitized_before_seeding_folders(tmp_path):
    class _MaliciousRouter:
        def synthesize(self, **kwargs):
            # simulates a model whose output was steered by adversarial
            # content in a newsletter body toward an unsafe topic name
            return "../../../tmp/pwned\nlegit-topic"

    config = _config(tmp_path, "learned")
    items = [
        RawItem(source_name="s", title="x", url="https://x", body="...",
                published=datetime.now(timezone.utc))
    ]
    result = resolve_taxonomy(config, items=items, router=_MaliciousRouter(), interactive=False)

    assert result.topics == ["tmp-pwned", "legit-topic"]
    # nothing was created outside knowledge_path
    created = {p.name for p in config.knowledge_path.iterdir()}
    assert created == {"tmp-pwned", "legit-topic", UNCATEGORIZED}
    assert not (config.knowledge_path.parent / "tmp").exists()
