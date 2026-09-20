from datetime import datetime, timedelta, timezone

from newsletter_sweep.state import State, fingerprint


def test_load_or_init_no_file_uses_lookback(tmp_path):
    path = tmp_path / "state.json"
    before = datetime.now(timezone.utc) - timedelta(days=7, minutes=1)
    state = State.load_or_init(path, first_run_lookback_days=7)
    after = datetime.now(timezone.utc) - timedelta(days=6, minutes=59)
    assert before <= state.last_processed <= after
    assert state.seen_urls == set()
    assert state.seen_ideas == set()


def test_save_and_reload_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    state = State.load_or_init(path)
    state.mark_seen("https://example.com/a", "Some Idea Title")
    state.save(path)

    reloaded = State.load_or_init(path)
    assert "https://example.com/a" in reloaded.seen_urls
    assert reloaded.is_duplicate("https://example.com/a", "irrelevant text")


def test_dedup_by_url(tmp_path):
    state = State.load_or_init(tmp_path / "state.json")
    state.mark_seen("https://example.com/a", "Idea A")
    assert state.is_duplicate("https://example.com/a", "totally different idea")
    assert not state.is_duplicate("https://example.com/b", "totally different idea")


def test_dedup_by_idea_fingerprint_survives_url_change(tmp_path):
    state = State.load_or_init(tmp_path / "state.json")
    state.mark_seen("https://a.com/x", "The rise of agentic coding tools in 2026")
    # same idea, different URL (e.g. two newsletters covering the same story)
    assert state.is_duplicate(
        "https://b.com/y", "The rise of agentic coding tools in 2026 — a recap"
    )


def test_fingerprint_is_case_and_punctuation_insensitive():
    a = fingerprint("The Rise of Agentic Coding Tools!")
    b = fingerprint("the rise of agentic coding tools")
    assert a == b
