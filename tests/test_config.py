import pytest

from newsletter_sweep.config import Config, ConfigError


def test_missing_config_file_raises_with_fix(tmp_path):
    with pytest.raises(ConfigError, match="init"):
        Config.load(tmp_path / "config.yaml")


def test_no_sources_raises(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("sinks: []\n")
    with pytest.raises(ConfigError, match="No sources"):
        Config.load(path)


def test_declared_topics_mode_requires_a_list(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        "topics:\n  mode: declared\n  declared: []\n"
        "sources:\n  - type: rss\n    feeds: []\n"
    )
    with pytest.raises(ConfigError, match="declared"):
        Config.load(path)


def test_minimal_valid_config_loads(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        "sources:\n  - type: rss\n    feeds: []\n"
    )
    config = Config.load(path)
    assert config.sources[0].type == "rss"
    assert config.sinks[0].type == "markdown"  # default sink
    assert config.dry_run is True  # default is safe


def test_paths_resolve_relative_to_config_file(tmp_path):
    subdir = tmp_path / "sub"
    subdir.mkdir()
    path = subdir / "config.yaml"
    path.write_text(
        "knowledge_path: ./kb\nsources:\n  - type: rss\n    feeds: []\n"
    )
    config = Config.load(path)
    assert config.knowledge_path == subdir / "kb"
