import pytest

from newsletter_sweep.profile import MissingProfileError, load_profile, write_profile


def test_missing_profile_raises(tmp_path):
    with pytest.raises(MissingProfileError):
        load_profile(tmp_path / "applies_to_me.md")


def test_placeholder_profile_raises(tmp_path):
    path = tmp_path / "applies_to_me.md"
    write_profile(path, "TODO: fill this in later")
    with pytest.raises(MissingProfileError):
        load_profile(path)


def test_too_short_profile_raises(tmp_path):
    path = tmp_path / "applies_to_me.md"
    write_profile(path, "hi")
    with pytest.raises(MissingProfileError):
        load_profile(path)


def test_real_profile_loads(tmp_path):
    path = tmp_path / "applies_to_me.md"
    text = "I'm a product manager with a security background, trying to get better at AI evals."
    write_profile(path, text)
    assert load_profile(path) == text


def test_pipeline_refuses_without_profile(tmp_path, monkeypatch):
    """The hard-requirement gate must fire from run_sweep, not just profile.py."""
    from newsletter_sweep.config import Config, ProviderConfig, TopicsConfig, SourceConfig
    from newsletter_sweep.pipeline import run_sweep

    config = Config(
        knowledge_path=tmp_path / "knowledge",
        profile_path=tmp_path / "applies_to_me.md",  # deliberately absent
        state_path=tmp_path / "state.json",
        provider=ProviderConfig(),
        topics=TopicsConfig(mode="declared", declared=["general"]),
        sources=[SourceConfig(type="rss", options={"feeds": []})],
        sinks=[],
        relevance_themes=["anything"],
        dry_run=True,
    )
    with pytest.raises(MissingProfileError):
        run_sweep(config)
