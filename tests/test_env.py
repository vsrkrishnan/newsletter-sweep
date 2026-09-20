import os

from newsletter_sweep.env import load_env_file


def test_missing_file_is_not_an_error(tmp_path):
    assert load_env_file(tmp_path / "nope.env") == 0


def test_loads_basic_pairs(tmp_path, monkeypatch):
    monkeypatch.delenv("MY_TEST_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("MY_TEST_KEY=abc123\n")
    loaded = load_env_file(env)
    assert loaded == 1
    assert os.environ["MY_TEST_KEY"] == "abc123"


def test_handles_export_prefix_comments_blanks_and_quotes(tmp_path, monkeypatch):
    for k in ("A_KEY", "B_KEY", "C_KEY"):
        monkeypatch.delenv(k, raising=False)
    env = tmp_path / ".env"
    env.write_text(
        "# a comment\n"
        "\n"
        "export A_KEY=plain\n"
        'B_KEY="double quoted"\n'
        "C_KEY='single quoted'\n"
    )
    load_env_file(env)
    assert os.environ["A_KEY"] == "plain"
    assert os.environ["B_KEY"] == "double quoted"
    assert os.environ["C_KEY"] == "single quoted"


def test_real_env_var_is_never_clobbered(tmp_path, monkeypatch):
    """A CI/cron run injects secrets as real env vars — a stray committed
    .env must never override them."""
    monkeypatch.setenv("PRECEDENCE_KEY", "from-real-env")
    env = tmp_path / ".env"
    env.write_text("PRECEDENCE_KEY=from-file\n")
    load_env_file(env)
    assert os.environ["PRECEDENCE_KEY"] == "from-real-env"


def test_config_load_reads_adjacent_env(tmp_path, monkeypatch):
    """End to end: the key in a .env next to config.yaml reaches the
    provider config without any shell export."""
    from newsletter_sweep.config import Config

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=sk-from-dotenv\n")
    (tmp_path / "config.yaml").write_text(
        "sources:\n  - type: rss\n    feeds: []\n"
    )
    config = Config.load(tmp_path / "config.yaml")
    assert config.provider.api_key() == "sk-from-dotenv"
