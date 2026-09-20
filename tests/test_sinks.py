from datetime import datetime, timezone

from newsletter_sweep.sinks.markdown_sink import MarkdownSink, slugify
from newsletter_sweep.sources import RawItem
from newsletter_sweep.triage import TriagedItem


def _item():
    raw = RawItem(source_name="Test Source", title="A Sharp Idea, Worth Filing",
                   url="https://x.com/1", published=datetime.now(timezone.utc), body="...")
    return TriagedItem(raw=raw, relevant_reason="because it's sharp",
                        applies_to_me="you should read this", topic="product-strategy")


def test_slugify_basic():
    assert slugify("A Sharp Idea, Worth Filing!") == "a-sharp-idea-worth-filing"


def test_dry_run_writes_nothing_to_disk(tmp_path):
    knowledge = tmp_path / "knowledge"
    sink = MarkdownSink({}, dry_run=True, knowledge_path=knowledge)
    result = sink.write_item(_item())
    assert result.startswith("[dry-run]")
    assert not knowledge.exists()


def test_live_run_writes_file_and_indexes(tmp_path):
    knowledge = tmp_path / "knowledge"
    sink = MarkdownSink({}, dry_run=False, knowledge_path=knowledge)
    result = sink.write_item(_item())

    target = knowledge / "product-strategy" / "a-sharp-idea-worth-filing.md"
    assert target.exists()
    assert "wrote" in result

    content = target.read_text()
    assert "you should read this" in content
    assert "https://x.com/1" in content

    topic_index = knowledge / "product-strategy" / "index.md"
    assert topic_index.exists()
    assert "A Sharp Idea, Worth Filing" in topic_index.read_text()

    master_index = knowledge / "index.md"
    assert master_index.exists()


def test_second_write_of_same_title_does_not_clobber(tmp_path):
    knowledge = tmp_path / "knowledge"
    sink = MarkdownSink({}, dry_run=False, knowledge_path=knowledge)
    sink.write_item(_item())
    target = knowledge / "product-strategy" / "a-sharp-idea-worth-filing.md"
    original_mtime = target.stat().st_mtime

    result = sink.write_item(_item())
    assert "skipped" in result
    assert target.stat().st_mtime == original_mtime
