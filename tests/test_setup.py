from newsletter_sweep.setup import run_init


def test_init_creates_all_files_noninteractive(tmp_path):
    run_init(tmp_path, interactive=False)
    assert (tmp_path / "config.yaml").exists()
    assert (tmp_path / "applies_to_me.md").exists()
    assert (tmp_path / ".env").exists()
    assert (tmp_path / ".gitignore").exists()


def test_init_env_names_the_right_key_for_default_provider(tmp_path):
    run_init(tmp_path, interactive=False)  # default provider is anthropic
    assert "ANTHROPIC_API_KEY=" in (tmp_path / ".env").read_text()


def test_init_gitignore_protects_secrets(tmp_path):
    """A user who commits their sweep dir for the Actions workflow must not
    leak their .env."""
    run_init(tmp_path, interactive=False)
    gitignore = (tmp_path / ".gitignore").read_text()
    assert ".env" in gitignore
    assert ".newsletter-sweep/" in gitignore


def test_init_is_idempotent_on_existing_setup(tmp_path):
    run_init(tmp_path, interactive=False)
    env_before = (tmp_path / ".env").read_text()
    # a second run must not overwrite a .env the user has already filled in
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=already-set\n")
    run_init(tmp_path, interactive=False)
    assert (tmp_path / ".env").read_text() == "ANTHROPIC_API_KEY=already-set\n"
    assert env_before  # sanity
